"""Record QDAS observations for an already completed migration step report.

This module does not launch a worker, execute a migration, apply a patch, or
authorize a side effect. A caller supplies an already captured bounded-process
report; this module records its QDAS event and references that event digest from
a migration AssuranceLedger record.

QDAS remains strictly observational: it records events, classifies failures
(symptom-only, never root-cause), and produces unconfirmed hypotheses. The two
ledger appends are separate operations, not one transaction. If the assurance
append does not return successfully after the QDAS append, a
MigrationEvidenceCommitError preserves the captured event and exact record
digests. Because the assurance append may have reached storage before an error
surfaced, callers must inspect both ledgers before retrying. The read-only
inspect_migration_evidence_link() operation classifies LINKED, orphaned,
dangling, conflicting, and missing references. The explicit
reconcile_migration_evidence_commit() operation can repair only a verified
ORPHANED_QDAS_EVENT using the exact payload preserved by the exception, under
a per-event exclusive lock. Neither operation makes the original two writes
atomic or provides automatic background recovery.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import copy
import os
import re
from typing import Any, Mapping, Sequence

from ..qdas.collector import QdasCaptureResult, record_execution_report
from ..qdas.events import ExecutionEvent
from ..qdas.ledger import QdasEventLedger
from .assurance import AssuranceLedger


_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class MigrationEvidenceCommitError(RuntimeError):
    """The QDAS append succeeded, but the assurance append did not return successfully.

    The assurance write may itself have reached durable storage before an error
    surfaced. Callers must inspect both ledgers before retrying; this exception
    preserves the QDAS evidence needed for that reconciliation.
    """

    def __init__(
        self,
        capture_result: QdasCaptureResult,
        assurance_fields: Mapping[str, Any],
    ) -> None:
        self.capture_result = capture_result
        self.event_digest = capture_result.event.event_digest
        self.qdas_record_digest = capture_result.ledger_record["record_digest"]
        self.assurance_fields = copy.deepcopy(dict(assurance_fields))
        super().__init__(
            "QDAS event %s was committed, but its migration assurance link failed"
            % self.event_digest
        )


def inspect_migration_evidence_link(
    event_digest: str,
    qdas_ledger: QdasEventLedger,
    assurance_ledger: AssuranceLedger,
) -> dict[str, Any]:
    """Read both verified ledgers and classify one migration evidence link.

    This is an inspection operation only: it never appends, repairs, or deletes
    evidence. It distinguishes an orphaned QDAS event from a missing event or a
    dangling/duplicate assurance reference.
    """
    if not isinstance(event_digest, str) or not _HEX_DIGEST.fullmatch(event_digest):
        raise ValueError("event_digest must be a lowercase SHA-256 digest")
    if not isinstance(qdas_ledger, QdasEventLedger):
        raise TypeError("qdas_ledger must be a QdasEventLedger")
    if not isinstance(assurance_ledger, AssuranceLedger):
        raise TypeError("assurance_ledger must be an AssuranceLedger")

    qdas_records = qdas_ledger.verify()
    assurance_records = assurance_ledger.read()
    qdas_matches = [
        record for record in qdas_records
        if record["event"]["event_digest"] == event_digest
    ]
    assurance_matches = [
        record for record in assurance_records
        if event_digest in record["evidence_ids"]
    ]

    if len(qdas_matches) > 1 or len(assurance_matches) > 1:
        status = "CONFLICT"
    elif not qdas_matches and assurance_matches:
        status = "ASSURANCE_REFERENCE_WITHOUT_QDAS_EVENT"
    elif qdas_matches and assurance_matches:
        status = "LINKED"
    elif qdas_matches:
        status = "ORPHANED_QDAS_EVENT"
    else:
        status = "NOT_FOUND"

    return {
        "schema": 1,
        "event_digest": event_digest,
        "status": status,
        "qdas_record_digest": (
            qdas_matches[0]["record_digest"] if len(qdas_matches) == 1 else None
        ),
        "assurance_record_digests": sorted(
            record["record_digest"] for record in assurance_matches
        ),
    }


def reconcile_migration_evidence_commit(
    error: MigrationEvidenceCommitError,
    qdas_ledger: QdasEventLedger,
    assurance_ledger: AssuranceLedger,
) -> dict[str, Any]:
    """Explicitly repair one known partial commit, or confirm it already linked.

    The exact assurance payload is taken from the original exception, not
    reconstructed from caller-supplied metadata. Only an ORPHANED_QDAS_EVENT
    may be repaired. A per-event exclusive lock serializes recovery attempts;
    the operation is idempotent after a successful append and always re-verifies
    both ledgers before reporting LINKED.
    """
    if not isinstance(error, MigrationEvidenceCommitError):
        raise TypeError("error must be a MigrationEvidenceCommitError")
    if not isinstance(qdas_ledger, QdasEventLedger):
        raise TypeError("qdas_ledger must be a QdasEventLedger")
    if not isinstance(assurance_ledger, AssuranceLedger):
        raise TypeError("assurance_ledger must be an AssuranceLedger")

    fields = copy.deepcopy(error.assurance_fields)
    evidence_ids = fields.get("evidence_ids")
    if not isinstance(evidence_ids, (list, tuple)) or error.event_digest not in evidence_ids:
        raise RuntimeError("recovery payload does not bind the original QDAS event")

    assurance_ledger.path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = assurance_ledger.path.with_name(
        assurance_ledger.path.name + ".reconcile-" + error.event_digest + ".lock"
    )
    lock_flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    lock_fd = None
    lock_identity = None
    try:
        try:
            lock_fd = os.open(lock_path, lock_flags, 0o600)
        except FileExistsError as exc:
            raise RuntimeError(
                "evidence reconciliation is already active or a stale lock requires inspection"
            ) from exc
        lock_info = os.fstat(lock_fd)
        lock_identity = (lock_info.st_dev, lock_info.st_ino)
        lock_payload = str(os.getpid()).encode("ascii")
        if os.write(lock_fd, lock_payload) != len(lock_payload):
            raise OSError("could not write the complete evidence reconciliation lock")
        os.fsync(lock_fd)

        current = inspect_migration_evidence_link(
            error.event_digest, qdas_ledger, assurance_ledger
        )
        if current["status"] == "LINKED":
            return current
        if current["status"] != "ORPHANED_QDAS_EVENT":
            raise RuntimeError(
                "refusing evidence repair from state %s" % current["status"]
            )

        try:
            assurance_ledger.append(fields)
        except Exception:
            # An append can report an error after replacement/fsync. Re-inspect
            # before deciding whether the operation actually committed.
            after_error = inspect_migration_evidence_link(
                error.event_digest, qdas_ledger, assurance_ledger
            )
            if after_error["status"] == "LINKED":
                return after_error
            raise

        repaired = inspect_migration_evidence_link(
            error.event_digest, qdas_ledger, assurance_ledger
        )
        if repaired["status"] != "LINKED":
            raise RuntimeError(
                "assurance append returned but evidence link is %s" % repaired["status"]
            )
        return repaired
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            try:
                current_lock = os.lstat(lock_path)
                if (current_lock.st_dev, current_lock.st_ino) == lock_identity:
                    lock_path.unlink()
            except FileNotFoundError:
                pass


def record_migration_step_with_qdas(
    report: Mapping[str, Any],
    project: str | Path,
    qdas_ledger: QdasEventLedger,
    assurance_ledger: AssuranceLedger,
    *,
    project_id: str,
    project_revision: str,
    workspace_id: str,
    event_kind: str,
    tool_name: str,
    tool_version: str,
    argv: Sequence[str],
    environment: Mapping[str, str],
    run_id: str,
    step_id: str,
    transition_id: str,
    source_identity: str,
    target_identity: str,
    plan_digest: str,
    pre_state_digest: str,
    worker_id: str,
    worker_version: str,
    worker_status: str,
    changed_files: Sequence[str],
    verdict: str,
    created_at: str,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    worker_manifest_digest: str | None = None,
    worker_qualification_id: str | None = None,
    worker_qualification_digest: str | None = None,
    diff_digest: str | None = None,
    post_state_digest: str | None = None,
    artifact_digest: str | None = None,
    commit_id: str | None = None,
    recovery_reference: str | None = None,
) -> tuple[QdasCaptureResult, dict[str, Any]]:
    """Record an already captured migration-step report in QDAS and assurance.

    This function does not execute or authorize the migration step. The caller
    supplies the process report and exact run/step/worker metadata. Returns the
    QDAS capture result and AssuranceLedger record. The QDAS event digest is
    bound into the assurance record's evidence_ids. The two appends are not
    atomic. If the assurance append does not return successfully, raises
    MigrationEvidenceCommitError with the QDAS capture and digests so callers
    can inspect both ledgers before retrying.
    """
    root = Path(project).expanduser().resolve(strict=True)
    started = datetime.now(timezone.utc) if started_at is None else started_at

    capture_result = record_execution_report(
        report,
        root,
        qdas_ledger,
        project_id=project_id,
        project_revision=project_revision,
        workspace_id=workspace_id,
        event_kind=event_kind,
        tool_name=tool_name,
        tool_version=tool_version,
        argv=argv,
        environment=environment,
        started_at=started,
        finished_at=finished_at,
    )

    event_digest = capture_result.event.event_digest
    evidence_ids = [event_digest]

    assurance_fields = {
        "run_id": run_id,
        "step_id": step_id,
        "transition_id": transition_id,
        "source_identity": source_identity,
        "target_identity": target_identity,
        "plan_digest": plan_digest,
        "pre_state_digest": pre_state_digest,
        "worker_id": worker_id,
        "worker_version": worker_version,
        "worker_status": worker_status,
        "changed_files": list(changed_files),
        "evidence_ids": evidence_ids,
        "verdict": verdict,
        "created_at": created_at,
        "worker_manifest_digest": worker_manifest_digest,
        "worker_qualification_id": worker_qualification_id,
        "worker_qualification_digest": worker_qualification_digest,
        "diff_digest": diff_digest,
        "post_state_digest": post_state_digest,
        "artifact_digest": artifact_digest,
        "commit_id": commit_id,
        "recovery_reference": recovery_reference,
    }
    try:
        assurance_record = assurance_ledger.append(assurance_fields)
    except Exception as exc:
        raise MigrationEvidenceCommitError(
            capture_result, assurance_fields
        ) from exc

    return capture_result, assurance_record


__all__ = [
    "MigrationEvidenceCommitError",
    "inspect_migration_evidence_link",
    "reconcile_migration_evidence_commit",
    "record_migration_step_with_qdas",
]

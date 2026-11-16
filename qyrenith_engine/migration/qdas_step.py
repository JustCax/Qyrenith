"""Record QDAS observations for an already completed migration step report.

This module does not launch a worker, execute a migration, apply a patch, or
authorize a side effect. A caller supplies an already captured bounded-process
report; this module records its QDAS event and references that event digest from
a migration AssuranceLedger record.

QDAS remains strictly observational: it records events, classifies failures
(symptom-only, never root-cause), and produces unconfirmed hypotheses. The two
ledger appends are separate operations, not one transaction. If the QDAS append
succeeds and the assurance append fails, the QDAS event remains without a
corresponding assurance record. Callers must treat that exception as a partial
evidence write requiring reconciliation; this module does not provide a
cross-ledger commit protocol or automatic orphan recovery.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..qdas.collector import QdasCaptureResult, record_execution_report
from ..qdas.events import ExecutionEvent
from ..qdas.ledger import QdasEventLedger
from .assurance import AssuranceLedger


class MigrationEvidenceCommitError(RuntimeError):
    """QDAS evidence was committed but its assurance linkage failed.

    The captured result and exact QDAS digests are retained so a caller can
    perform an explicit, independently reviewed reconciliation. This exception
    does not imply that the missing assurance record was repaired.
    """

    def __init__(self, capture_result: QdasCaptureResult) -> None:
        self.capture_result = capture_result
        self.event_digest = capture_result.event.event_digest
        self.qdas_record_digest = capture_result.ledger_record["record_digest"]
        super().__init__(
            "QDAS event %s was committed, but its migration assurance link failed"
            % self.event_digest
        )


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
    atomic: an assurance append failure leaves the committed QDAS event in
    place and requires caller-managed reconciliation.
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

    try:
        assurance_record = assurance_ledger.append(
            {
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
        )
    except Exception as exc:
        raise MigrationEvidenceCommitError(capture_result) from exc

    return capture_result, assurance_record


__all__ = ["MigrationEvidenceCommitError", "record_migration_step_with_qdas"]

"""Digest-bound, append-only repair evidence lineage.

This ledger records proposals and observed evidence only. Human review entries are
explicitly unauthenticated assertions; they never authorize process execution.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from datetime import datetime, timezone
from typing import Any

from .ledger import QdasEventLedger, QdasLedgerError
from .repair import RepairPlan
from .events import _canonical, _unique_pairs

_GENESIS = "0" * 64
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_KINDS = {"REPAIR_PLAN", "HUMAN_REVIEW", "PATCH", "REVERIFICATION", "REGRESSION", "FINAL_VERDICT"}
_MAX_BYTES = 16 * 1024 * 1024
_MAX_RECORDS = 100_000


class QdasLineageError(RuntimeError):
    """Repair evidence lineage is invalid, unsafe, or cannot be updated."""


def _text(value: Any, name: str, limit: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError(name + " must be non-empty bounded text")
    return value


def _digest(value: Any, name: str, length: int = 64) -> str:
    pattern = _HEX64 if length == 64 else _HEX32
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(name + " must be a lowercase SHA-256/UUID hex digest")
    return value


def _execution_scope_digest(event: dict[str, Any]) -> str:
    fields = (
        "event_id", "event_kind", "project_revision", "tool_name", "tool_version",
        "argv", "working_directory", "environment_digest", "execution_status",
        "exit_code", "stdout_digest", "stderr_digest",
    )
    return hashlib.sha256(_canonical({key: event[key] for key in fields})).hexdigest()


def _event_record(
    event_index: dict[tuple[str, str], dict[str, Any]],
    event_id: str,
    digest: str,
) -> dict[str, Any]:
    record = event_index.get((event_id, digest))
    if record is None:
        raise QdasLineageError("referenced execution event is absent or its record digest does not match")
    return record


def _new_lineage_index() -> dict[str, Any]:
    return {
        "records": {},
        "plans": {},
        "reviews": {},
        "patches": {},
        "patches_by_plan": {},
        "reverification": {},
        "regression": {},
        "verdicts": set(),
    }


def _index_lineage_record(index: dict[str, Any], record: dict[str, Any]) -> None:
    kind = record["kind"]
    payload = record["payload"]
    index["records"][record["record_digest"]] = record
    if kind == "REPAIR_PLAN":
        index["plans"][payload["plan_digest"]] = record
    elif kind == "HUMAN_REVIEW":
        index["reviews"][payload["plan_digest"]] = record
    elif kind == "PATCH":
        index["patches"][record["record_digest"]] = record
        index["patches_by_plan"][payload["plan_digest"]] = record
    elif kind == "REVERIFICATION":
        index["reverification"][payload["patch_record_digest"]] = record
    elif kind == "REGRESSION":
        index["regression"][payload["patch_record_digest"]] = record
    elif kind == "FINAL_VERDICT":
        index["verdicts"].add(payload["plan_digest"])


def _build_lineage_index(records: list[dict[str, Any]]) -> dict[str, Any]:
    index = _new_lineage_index()
    for record in records:
        _index_lineage_record(index, record)
    return index


class QdasEvidenceLineage:
    """Append-only repair lifecycle evidence, anchored to the execution event ledger."""

    def __init__(self, path: str | os.PathLike[str], event_ledger: QdasEventLedger) -> None:
        if not isinstance(event_ledger, QdasEventLedger):
            raise TypeError("event_ledger must be a QdasEventLedger")
        self.path = Path(path).expanduser().absolute()
        self.event_ledger = event_ledger

    def _check(self, create: bool) -> None:
        try:
            QdasEventLedger(self.path)._check_parent(create=create)
        except QdasLedgerError as exc:
            raise QdasLineageError("QDAS lineage parent path is unsafe") from exc
        parent = self.path.parent
        if not parent.exists():
            if not create:
                raise QdasLineageError("QDAS lineage directory does not exist")
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name != "nt":
                parent.chmod(0o700)
        info = parent.lstat()
        parent_attributes = getattr(info, "st_file_attributes", 0)
        if (
            not stat.S_ISDIR(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or parent_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise QdasLineageError("QDAS lineage parent must be a real non-reparse directory")
        if os.name != "nt" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise QdasLineageError("QDAS lineage directory must be owner-only")
        if self.path.exists() or self.path.is_symlink():
            item = self.path.lstat()
            item_attributes = getattr(item, "st_file_attributes", 0)
            if (
                stat.S_ISLNK(item.st_mode)
                or not stat.S_ISREG(item.st_mode)
                or item_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            ):
                raise QdasLineageError("QDAS lineage ledger must be a regular non-reparse file")
            if os.name != "nt" and (item.st_uid != os.getuid() or item.st_mode & 0o077):
                raise QdasLineageError("QDAS lineage ledger must be owner-only")

    @staticmethod
    def _validate_payload(
        kind: str,
        payload: dict[str, Any],
        lineage_index: dict[str, Any],
        event_index: dict[tuple[str, str], dict[str, Any]],
    ) -> None:
        if kind == "REPAIR_PLAN":
            required = {"event_id", "event_record_digest", "hypothesis_id", "plan_document", "plan_digest"}
            if set(payload) != required:
                raise ValueError("repair plan evidence fields are invalid")
            event_id = _digest(payload["event_id"], "event_id", 32)
            event_record = _event_record(event_index, event_id, _digest(payload["event_record_digest"], "event_record_digest"))
            hypothesis_id = _digest(payload["hypothesis_id"], "hypothesis_id", 32)
            hypotheses = event_record.get("hypotheses", [])
            matched_hypothesis = next(
                (item for item in hypotheses if item.get("hypothesis_id") == hypothesis_id),
                None,
            )
            if matched_hypothesis is None:
                raise ValueError("repair plan hypothesis is not present in the anchored event record")
            document = payload["plan_document"]
            plan = RepairPlan.from_document(document)
            if plan.event_id != event_id or plan.hypothesis_id != hypothesis_id:
                raise ValueError("repair plan document is not bound to the source event and hypothesis")
            if plan.failure_category != matched_hypothesis.get("failure_category"):
                raise ValueError("repair plan failure category does not match its persisted hypothesis")
            supplied = _digest(payload["plan_digest"], "plan_digest")
            if plan.plan_digest != supplied:
                raise ValueError("repair plan digest does not match its canonical document")
            if supplied in lineage_index["plans"]:
                raise ValueError("repair plan is already recorded")
            return
        if kind == "HUMAN_REVIEW":
            required = {"plan_digest", "decision", "reviewer_id", "reviewed_at", "note", "authentication_state"}
            if set(payload) != required:
                raise ValueError("human review evidence fields are invalid")
            plan_digest = _digest(payload["plan_digest"], "plan_digest")
            _text(payload["reviewer_id"], "reviewer_id", 256)
            reviewed_at = _text(payload["reviewed_at"], "reviewed_at", 64)
            try:
                parsed_review_time = datetime.fromisoformat(
                    reviewed_at[:-1] + "+00:00" if reviewed_at.endswith("Z") else reviewed_at
                )
            except ValueError as exc:
                raise ValueError("reviewed_at must be a canonical UTC ISO-8601 timestamp") from exc
            if (
                parsed_review_time.tzinfo is None
                or parsed_review_time.utcoffset() != timezone.utc.utcoffset(parsed_review_time)
                or parsed_review_time.isoformat().replace("+00:00", "Z") != reviewed_at
            ):
                raise ValueError("reviewed_at must be a canonical UTC ISO-8601 timestamp")
            if payload["decision"] not in {"APPROVE", "REJECT"}:
                raise ValueError("human review decision must be APPROVE or REJECT")
            if payload["authentication_state"] != "UNAUTHENTICATED_ASSERTION":
                raise ValueError("this API cannot authenticate human identity or approval")
            if payload["note"] is not None:
                _text(payload["note"], "note", 1024)
            if plan_digest not in lineage_index["plans"]:
                raise ValueError("human review references an unknown repair plan")
            if plan_digest in lineage_index["reviews"]:
                raise ValueError("repair plan already has a review decision")
            return
        if kind == "PATCH":
            required = {"plan_digest", "review_record_digest", "base_revision", "resulting_revision", "diff_digest", "changed_paths", "patch_applied"}
            if set(payload) != required:
                raise ValueError("patch evidence fields are invalid")
            plan_digest = _digest(payload["plan_digest"], "plan_digest")
            review_digest = _digest(payload["review_record_digest"], "review_record_digest")
            review = lineage_index["reviews"].get(plan_digest)
            if review is None or review["record_digest"] != review_digest or review["payload"]["decision"] != "APPROVE":
                raise ValueError("patch evidence requires a prior approving review for the same plan")
            plan_entry = lineage_index["plans"].get(plan_digest)
            if plan_entry is None:
                raise ValueError("patch evidence references an unknown repair plan")
            source_event = _event_record(
                event_index,
                plan_entry["payload"]["event_id"],
                plan_entry["payload"]["event_record_digest"],
            )["event"]
            for name in ("base_revision", "resulting_revision"):
                _text(payload[name], name, 256)
            if payload["base_revision"] != source_event["project_revision"]:
                raise ValueError("patch base revision does not match the repair plan source event")
            if payload["resulting_revision"] == payload["base_revision"]:
                raise ValueError("patch resulting revision must differ from its base revision")
            _digest(payload["diff_digest"], "diff_digest")
            paths = payload["changed_paths"]
            if not isinstance(paths, list) or not 1 <= len(paths) <= 256:
                raise ValueError("changed_paths must contain between 1 and 256 paths")
            for path in paths:
                if (
                    not isinstance(path, str) or not path or len(path) > 4096
                    or "\\" in path or "\x00" in path or path.startswith("/")
                    or re.match(r"^[A-Za-z]:", path)
                    or any(part in {"", ".", ".."} for part in path.split("/"))
                    or any(char in path for char in "*?[]")
                    or PurePosixPath(path).as_posix() != path
                ):
                    raise ValueError("changed_paths must use canonical safe project-relative paths")
            if paths != sorted(set(paths)):
                raise ValueError("changed_paths must be unique and sorted")
            planned_paths = set(plan_entry["payload"]["plan_document"]["affected_paths"])
            if not set(paths).issubset(planned_paths):
                raise ValueError("patch changed paths exceed the approved repair plan")
            if payload["patch_applied"] is not True:
                raise ValueError("PATCH evidence must describe an observed applied patch")
            if plan_digest in lineage_index["patches_by_plan"]:
                raise ValueError("repair plan already has patch evidence")
            return
        if kind in {"REVERIFICATION", "REGRESSION"}:
            required = {"patch_record_digest", "event_id", "event_record_digest", "scope_digest"}
            if set(payload) != required:
                raise ValueError(kind.lower() + " evidence fields are invalid")
            patch_digest = _digest(payload["patch_record_digest"], "patch_record_digest")
            patch = lineage_index["patches"].get(patch_digest)
            if patch is None:
                raise ValueError(kind.lower() + " evidence requires a prior patch record")
            event_id = _digest(payload["event_id"], "event_id", 32)
            event_record = _event_record(event_index, event_id, _digest(payload["event_record_digest"], "event_record_digest"))
            event = event_record["event"]
            if event["execution_status"] not in {"PASS", "FAIL", "ERROR", "BLOCKED"}:
                raise ValueError(kind.lower() + " evidence has an unsupported execution status")
            allowed_kinds = {"TEST"} if kind == "REGRESSION" else {"BUILD", "VERIFICATION"}
            if event["event_kind"] not in allowed_kinds:
                raise ValueError(kind.lower() + " evidence references an execution event of the wrong kind")
            patch_revision = patch["payload"]["resulting_revision"]
            if event["project_revision"] != patch_revision:
                raise ValueError(kind.lower() + " event revision does not match the observed patch revision")
            supplied_scope_digest = _digest(payload["scope_digest"], "scope_digest")
            if supplied_scope_digest != _execution_scope_digest(event):
                raise ValueError(kind.lower() + " scope digest does not match the referenced execution event")
            if patch_digest in lineage_index["reverification" if kind == "REVERIFICATION" else "regression"]:
                raise ValueError(kind.lower() + " evidence is already recorded for this patch")
            return
        if kind == "FINAL_VERDICT":
            required = {"plan_digest", "patch_record_digest", "reverification_record_digest", "regression_record_digest", "verdict", "rationale"}
            if set(payload) != required:
                raise ValueError("final verdict evidence fields are invalid")
            plan_digest = _digest(payload["plan_digest"], "plan_digest")
            refs = {}
            for field, expected_kind in (
                ("patch_record_digest", "PATCH"),
                ("reverification_record_digest", "REVERIFICATION"),
                ("regression_record_digest", "REGRESSION"),
            ):
                digest = _digest(payload[field], field)
                refs[field] = lineage_index["records"].get(digest)
                if refs[field] is not None and refs[field]["kind"] != expected_kind:
                    refs[field] = None
                if refs[field] is None:
                    raise ValueError("final verdict references missing " + expected_kind.lower() + " evidence")
            if refs["patch_record_digest"]["payload"]["plan_digest"] != plan_digest:
                raise ValueError("final verdict patch belongs to another plan")
            if refs["reverification_record_digest"]["payload"]["patch_record_digest"] != payload["patch_record_digest"]:
                raise ValueError("reverification evidence belongs to another patch")
            if refs["regression_record_digest"]["payload"]["patch_record_digest"] != payload["patch_record_digest"]:
                raise ValueError("regression evidence belongs to another patch")
            if payload["verdict"] not in {"PASS", "FAIL", "INCONCLUSIVE"}:
                raise ValueError("final verdict must be PASS, FAIL, or INCONCLUSIVE")
            reverification_event = _event_record(
                event_index,
                refs["reverification_record_digest"]["payload"]["event_id"],
                refs["reverification_record_digest"]["payload"]["event_record_digest"],
            )["event"]
            regression_event = _event_record(
                event_index,
                refs["regression_record_digest"]["payload"]["event_id"],
                refs["regression_record_digest"]["payload"]["event_record_digest"],
            )["event"]
            evidence_statuses = {
                reverification_event["execution_status"],
                regression_event["execution_status"],
            }
            if payload["verdict"] == "PASS" and evidence_statuses != {"PASS"}:
                raise ValueError("PASS verdict requires passing rebuild and regression evidence")
            if payload["verdict"] == "FAIL" and "FAIL" not in evidence_statuses:
                raise ValueError("FAIL verdict requires at least one failed verification event")
            if payload["verdict"] == "INCONCLUSIVE" and (
                "FAIL" in evidence_statuses or evidence_statuses == {"PASS"}
            ):
                raise ValueError("INCONCLUSIVE verdict requires blocked or errored verification evidence")
            if payload["verdict"] == "PASS":
                review = lineage_index["reviews"].get(plan_digest)
                if review is None or review["payload"]["decision"] != "APPROVE":
                    raise ValueError("PASS verdict requires an approving review record")
            _text(payload["rationale"], "rationale", 2048)
            if plan_digest in lineage_index["verdicts"]:
                raise ValueError("repair plan already has a final verdict")
            return
        raise ValueError("unsupported QDAS evidence kind")

    def _verified_event_index(self) -> dict[tuple[str, str], dict[str, Any]]:
        records = self.event_ledger.verify()
        return {
            (item["event"]["event_id"], item["record_digest"]): item
            for item in records
        }

    def verify(self) -> tuple[dict[str, Any], ...]:
        self._check(create=False)
        event_index = self._verified_event_index()
        with QdasEventLedger(self.path)._lock():
            return self._verify_unlocked(event_index)

    def _verify_unlocked(
        self,
        event_index: dict[tuple[str, str], dict[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        self._check(create=False)
        if not self.path.exists():
            return ()
        try:
            info = self.path.lstat()
            attributes = getattr(info, "st_file_attributes", 0)
            if (
                stat.S_ISLNK(info.st_mode)
                or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                or not stat.S_ISREG(info.st_mode)
            ):
                raise QdasLineageError("QDAS lineage ledger changed to an unsafe file type")
            if info.st_size > _MAX_BYTES:
                raise QdasLineageError("QDAS lineage ledger exceeds the 16 MiB limit")
            raw = self.path.read_bytes()
        except QdasLineageError:
            raise
        except OSError as exc:
            raise QdasLineageError("cannot read QDAS lineage ledger") from exc
        if raw and not raw.endswith(b"\n"):
            raise QdasLineageError("QDAS lineage ledger has an incomplete trailing record")
        records: list[dict[str, Any]] = []
        lineage_index = _new_lineage_index()
        previous = _GENESIS
        for sequence, line in enumerate(raw.splitlines(keepends=True), 1):
            if sequence > _MAX_RECORDS or len(line) > 128 * 1024:
                raise QdasLineageError("QDAS lineage record limit exceeded")
            try:
                record = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_pairs)
                if not isinstance(record, dict) or set(record) != {"schema", "sequence", "previous_digest", "kind", "payload", "record_digest"}:
                    raise ValueError("unexpected record fields")
                if type(record["schema"]) is not int or record["schema"] != 1 or type(record["sequence"]) is not int or record["sequence"] != sequence:
                    raise ValueError("invalid schema or sequence")
                if record["previous_digest"] != previous or record["kind"] not in _KINDS or not isinstance(record["payload"], dict):
                    raise ValueError("invalid lineage linkage")
                digest = hashlib.sha256(_canonical({key: value for key, value in record.items() if key != "record_digest"})).hexdigest()
                if digest != record["record_digest"] or _canonical(record) + b"\n" != line:
                    raise ValueError("lineage digest or canonical encoding mismatch")
                self._validate_payload(record["kind"], record["payload"], lineage_index, event_index)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError, QdasLedgerError, QdasLineageError) as exc:
                raise QdasLineageError("QDAS lineage record " + str(sequence) + " is invalid") from exc
            records.append(record)
            _index_lineage_record(lineage_index, record)
            previous = digest
        return tuple(records)

    def append(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if kind not in _KINDS or not isinstance(payload, dict):
            raise ValueError("unsupported QDAS evidence kind or payload")
        self._check(create=True)
        # Share the primary ledger's cross-platform lock implementation.
        with QdasEventLedger(self.path)._lock():
            event_index = self._verified_event_index()
            records = list(self._verify_unlocked(event_index))
            if len(records) >= _MAX_RECORDS:
                raise QdasLineageError("QDAS lineage ledger reached its record limit")
            lineage_index = _build_lineage_index(records)
            self._validate_payload(kind, payload, lineage_index, event_index)
            previous = records[-1]["record_digest"] if records else _GENESIS
            record = {
                "schema": 1,
                "sequence": len(records) + 1,
                "previous_digest": previous,
                "kind": kind,
                "payload": payload,
            }
            record["record_digest"] = hashlib.sha256(_canonical(record)).hexdigest()
            line = _canonical(record) + b"\n"
            current = self.path.stat().st_size if self.path.exists() else 0
            if current + len(line) > _MAX_BYTES or len(line) > 128 * 1024:
                raise QdasLineageError("QDAS lineage ledger size limit exceeded")
            append_flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
            out_fd = os.open(self.path, append_flags, 0o600)
            out_info = os.fstat(out_fd)
            if not stat.S_ISREG(out_info.st_mode):
                os.close(out_fd)
                raise QdasLineageError("QDAS lineage ledger must be a regular file")
            if os.name != "nt":
                os.fchmod(out_fd, 0o600)
            with os.fdopen(out_fd, "ab") as stream:
                written = stream.write(line)
                if written != len(line):
                    raise QdasLineageError("QDAS lineage append was incomplete")
                stream.flush()
                os.fsync(stream.fileno())
            return record


__all__ = ["QdasEvidenceLineage", "QdasLineageError"]

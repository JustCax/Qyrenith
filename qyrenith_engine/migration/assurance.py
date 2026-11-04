"""Tamper-evident, append-only migration step assurance ledger.

The ledger records observations and Qyrenith verdicts. It does not execute workers,
authorize project mutations, or provide cryptographic authenticity against an actor
who can replace the entire local ledger and its trust anchor.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile


_VERDICTS = {"PASS", "FAIL", "BLOCKED", "UNKNOWN", "NOT_RUN", "UNSUPPORTED", "ERROR"}
_WORKER_STATUSES = {"WORKED", "NO_CHANGE", "BLOCKED", "FAILED"}
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED = (
    "run_id", "step_id", "transition_id", "source_identity", "target_identity",
    "plan_digest", "pre_state_digest", "worker_id", "worker_version", "worker_status",
    "changed_files", "evidence_ids", "verdict", "created_at",
)
_OPTIONAL = {
    "worker_manifest_digest", "worker_qualification_id", "worker_qualification_digest",
    "diff_digest", "post_state_digest", "artifact_digest", "commit_id", "recovery_reference",
}
_COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_MAX_RECORDS = 100_000


class AssuranceLedgerError(RuntimeError):
    """The ledger is malformed, inconsistent, or cannot be safely updated."""


class LedgerLockedError(AssuranceLedgerError):
    """Another writer owns the ledger lock or a prior writer left a stale lock."""


def _canonical_bytes(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _require_text(value, field, max_length=8192):
    if not isinstance(value, str) or not value.strip():
        raise AssuranceLedgerError(f"{field} must be a non-empty string")
    if len(value) > max_length:
        raise AssuranceLedgerError(f"{field} exceeds the {max_length}-character limit")
    return value


def _require_digest(value, field, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise AssuranceLedgerError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _validate_relative_paths(paths):
    if not isinstance(paths, (list, tuple)):
        raise AssuranceLedgerError("changed_files must be a list of repository-relative paths")
    normalized = []
    for raw in paths:
        path = _require_text(raw, "changed_files entry")
        if len(path) > 4096:
            raise AssuranceLedgerError("changed-file path exceeds 4096 characters")
        parsed = PurePosixPath(path)
        if (
            parsed.is_absolute() or ".." in parsed.parts or path in {".", ""}
            or "\\" in path or ":" in path or parsed.as_posix() != path
        ):
            raise AssuranceLedgerError(f"unsafe changed-file path: {path}")
        normalized.append(path)
    if len(normalized) > 100000:
        raise AssuranceLedgerError("changed_files exceeds the per-record limit")
    if len(normalized) != len(set(normalized)):
        raise AssuranceLedgerError("changed_files must not contain duplicates")
    return sorted(normalized)


def _validate_timestamp(value):
    _require_text(value, "created_at", 64)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssuranceLedgerError("created_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AssuranceLedgerError("created_at must include a timezone")


def _normalize_payload(fields, sequence, previous_digest):
    if not isinstance(fields, dict):
        raise AssuranceLedgerError("record fields must be an object")
    if any(not isinstance(key, str) for key in fields):
        raise AssuranceLedgerError("record field names must be strings")
    missing = [name for name in _REQUIRED if name not in fields]
    if missing:
        raise AssuranceLedgerError("missing record fields: " + ", ".join(missing))
    unexpected = set(fields) - set(_REQUIRED) - _OPTIONAL
    if unexpected:
        raise AssuranceLedgerError("unexpected record fields: " + ", ".join(sorted(unexpected)))
    if not isinstance(fields["evidence_ids"], (list, tuple)):
        raise AssuranceLedgerError("evidence_ids must be a list or tuple")
    if len(fields["evidence_ids"]) > 10000:
        raise AssuranceLedgerError("evidence_ids exceeds the per-record limit")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise AssuranceLedgerError("sequence must be a positive integer")
    if previous_digest is not None:
        _require_digest(previous_digest, "previous_digest")

    record = {
        "schema": 1,
        "sequence": sequence,
        "run_id": _require_text(fields["run_id"], "run_id", 256),
        "step_id": _require_text(fields["step_id"], "step_id", 256),
        "transition_id": _require_text(fields["transition_id"], "transition_id", 256),
        "source_identity": _require_text(fields["source_identity"], "source_identity", 8192),
        "target_identity": _require_text(fields["target_identity"], "target_identity", 8192),
        "plan_digest": _require_digest(fields["plan_digest"], "plan_digest"),
        "pre_state_digest": _require_digest(fields["pre_state_digest"], "pre_state_digest"),
        "worker_id": _require_text(fields["worker_id"], "worker_id", 256),
        "worker_version": _require_text(fields["worker_version"], "worker_version", 128),
        "worker_manifest_digest": _require_digest(
            fields.get("worker_manifest_digest"), "worker_manifest_digest", optional=True
        ),
        "worker_qualification_id": (
            None if fields.get("worker_qualification_id") is None
            else _require_text(fields["worker_qualification_id"], "worker_qualification_id", 256)
        ),
        "worker_qualification_digest": _require_digest(
            fields.get("worker_qualification_digest"), "worker_qualification_digest", optional=True
        ),
        "worker_status": _require_text(fields["worker_status"], "worker_status", 256),
        "changed_files": _validate_relative_paths(fields["changed_files"]),
        "diff_digest": _require_digest(fields.get("diff_digest"), "diff_digest", optional=True),
        "evidence_ids": list(fields["evidence_ids"]),
        "verdict": _require_text(fields["verdict"], "verdict", 32),
        "post_state_digest": _require_digest(fields.get("post_state_digest"), "post_state_digest", optional=True),
        "artifact_digest": _require_digest(fields.get("artifact_digest"), "artifact_digest", optional=True),
        "commit_id": fields.get("commit_id"),
        "recovery_reference": (
            None if fields.get("recovery_reference") is None
            else _require_text(fields["recovery_reference"], "recovery_reference")
        ),
        "created_at": fields["created_at"],
        "previous_digest": previous_digest,
    }
    if record["verdict"] not in _VERDICTS:
        raise AssuranceLedgerError("verdict is not a supported Qyrenith verdict")
    if record["worker_status"] not in _WORKER_STATUSES:
        raise AssuranceLedgerError("worker_status is not a supported worker-protocol status")
    worker_provenance = (
        record["worker_manifest_digest"], record["worker_qualification_id"],
        record["worker_qualification_digest"],
    )
    if any(value is not None for value in worker_provenance) and not all(
        value is not None for value in worker_provenance
    ):
        raise AssuranceLedgerError("worker manifest and qualification provenance must be supplied together")
    if not isinstance(record["evidence_ids"], list) or any(
        not isinstance(item, str) or not item.strip() or len(item) > 256
        for item in record["evidence_ids"]
    ):
        raise AssuranceLedgerError("evidence_ids must contain non-empty strings")
    if len(record["evidence_ids"]) != len(set(record["evidence_ids"])):
        raise AssuranceLedgerError("evidence_ids must not contain duplicates")
    record["evidence_ids"] = sorted(record["evidence_ids"])
    for field in ("commit_id", "recovery_reference"):
        if record[field] is not None and (not isinstance(record[field], str) or not record[field].strip()):
            raise AssuranceLedgerError(f"{field} must be None or a non-empty string")
    if record["commit_id"] is not None and (
        not isinstance(record["commit_id"], str) or not _COMMIT.fullmatch(record["commit_id"])
    ):
        raise AssuranceLedgerError("commit_id must be a 40- or 64-character lowercase Git object identifier")
    _validate_timestamp(record["created_at"])

    # PASS is a Qyrenith decision, never a worker self-report. It requires the
    # independently collected transition, diff, post-state, evidence, and commit.
    if record["verdict"] == "PASS":
        required_for_pass = (
            record["changed_files"], record["diff_digest"], record["post_state_digest"],
            record["evidence_ids"], record["commit_id"],
            record["worker_manifest_digest"], record["worker_qualification_id"],
            record["worker_qualification_digest"],
        )
        if record["worker_status"] != "WORKED":
            raise AssuranceLedgerError("PASS requires a WORKED worker result")
        if not all(required_for_pass):
            raise AssuranceLedgerError(
                "PASS requires changed files, diff, post-state, evidence, commit, and qualified worker provenance"
            )
    return record


def _record_digest(record):
    return hashlib.sha256(_canonical_bytes(record)).hexdigest()


def verify_assurance_chain(records):
    """Validate sequence, previous-digest links, and every record digest."""
    if not isinstance(records, (list, tuple)) or len(records) > _MAX_RECORDS:
        raise AssuranceLedgerError("ledger record collection is invalid or exceeds the record limit")
    previous = None
    verified = []
    for expected_sequence, item in enumerate(records, start=1):
        if not isinstance(item, dict):
            raise AssuranceLedgerError("ledger entries must be objects")
        expected_keys = set(_REQUIRED) | _OPTIONAL | {
            "schema", "sequence", "previous_digest", "record_digest",
        }
        if set(item) != expected_keys:
            raise AssuranceLedgerError(f"unexpected or missing fields at sequence {expected_sequence}")
        if type(item.get("schema")) is not int or item.get("schema") != 1:
            raise AssuranceLedgerError(f"schema mismatch at sequence {expected_sequence}")
        if type(item.get("sequence")) is not int or item.get("sequence") != expected_sequence:
            raise AssuranceLedgerError(f"sequence mismatch at sequence {expected_sequence}")
        if item.get("previous_digest") != previous:
            raise AssuranceLedgerError(f"previous digest mismatch at sequence {expected_sequence}")
        supplied = item.get("record_digest")
        payload = {
            key: value for key, value in item.items()
            if key not in {"schema", "sequence", "previous_digest", "record_digest"}
        }
        normalized = _normalize_payload(payload, expected_sequence, previous)
        calculated = _record_digest(normalized)
        if supplied != calculated:
            raise AssuranceLedgerError(f"record digest mismatch at sequence {expected_sequence}")
        normalized["record_digest"] = calculated
        verified.append(normalized)
        previous = calculated
    return tuple(verified)


class AssuranceLedger:
    """Single-writer JSONL ledger with an atomic replacement and fail-closed lock."""

    def __init__(self, path, *, max_bytes=64 * 1024 * 1024, max_records=_MAX_RECORDS):
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1024:
            raise ValueError("max_bytes must be an integer of at least 1024")
        if not isinstance(max_records, int) or isinstance(max_records, bool) or not 1 <= max_records <= _MAX_RECORDS:
            raise ValueError(f"max_records must be between 1 and {_MAX_RECORDS}")
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.max_bytes = max_bytes
        self.max_records = max_records

    def read(self):
        if self.path.is_symlink():
            raise AssuranceLedgerError("ledger path must not be a symbolic link")
        if not self.path.exists():
            return ()
        try:
            if self.path.stat().st_size > self.max_bytes:
                raise AssuranceLedgerError("ledger exceeds the configured byte limit")
            raw_lines = self.path.read_text(encoding="utf-8").splitlines()
            if len(raw_lines) > self.max_records:
                raise AssuranceLedgerError("ledger exceeds the configured record limit")
            records = []
            for line_number, line in enumerate(raw_lines, start=1):
                if not line:
                    raise AssuranceLedgerError(f"ledger contains an empty line at {line_number}")
                item = json.loads(line, object_pairs_hook=_unique_json_object)
                if not isinstance(item, dict):
                    raise AssuranceLedgerError(f"ledger record {line_number} is not an object")
                if _canonical_bytes(item).decode("utf-8") != line:
                    raise AssuranceLedgerError(f"ledger record {line_number} is not canonical JSON")
                records.append(item)
        except AssuranceLedgerError:
            raise
        except (OSError, UnicodeError, ValueError) as exc:
            raise AssuranceLedgerError("ledger cannot be read as valid canonical JSONL") from exc
        if len(records) != len(raw_lines):
            raise AssuranceLedgerError("ledger contains empty or incomplete lines")
        return verify_assurance_chain(records)

    def append(self, fields):
        """Append one record. A stale lock intentionally blocks until inspected."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise AssuranceLedgerError("ledger path must not be a symbolic link")
        try:
            lock_fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise LedgerLockedError("ledger lock exists; inspect it before recovery") from exc
        lock_stat = os.fstat(lock_fd)
        try:
            lock_payload = str(os.getpid()).encode("ascii")
            if os.write(lock_fd, lock_payload) != len(lock_payload):
                raise AssuranceLedgerError("could not write the complete ledger lock owner")
            os.fsync(lock_fd)
            existing = self.read()
            if len(existing) >= self.max_records:
                raise AssuranceLedgerError("ledger reached the configured record limit")
            previous = existing[-1]["record_digest"] if existing else None
            payload = _normalize_payload(fields, len(existing) + 1, previous)
            payload["record_digest"] = _record_digest(payload)
            all_records = list(existing) + [payload]
            encoded = b"".join(_canonical_bytes(item) + b"\n" for item in all_records)
            if len(encoded) > self.max_bytes:
                raise AssuranceLedgerError("append would exceed the configured ledger byte limit")
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=str(self.path.parent), prefix=self.path.name + ".",
                    suffix=".tmp", delete=False,
                ) as handle:
                    temporary = handle.name
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
                if os.name != "nt":
                    directory_fd = os.open(
                        str(self.path.parent),
                        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                    )
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
            return payload
        finally:
            os.close(lock_fd)
            try:
                current_lock = os.lstat(self.lock_path)
                if (current_lock.st_dev, current_lock.st_ino) == (lock_stat.st_dev, lock_stat.st_ino):
                    self.lock_path.unlink()
            except FileNotFoundError:
                pass


__all__ = [
    "AssuranceLedger",
    "AssuranceLedgerError",
    "LedgerLockedError",
    "verify_assurance_chain",
]

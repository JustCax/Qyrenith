"""Append-only, hash-chained QDAS event and failure ledger."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time
from typing import Any

from .diagnosis import FailureHypothesis, FailureObservation
from .events import ExecutionEvent, FailureClassification, _canonical, _unique_pairs, classify_failure

_GENESIS = "0" * 64
_MAX_RECORDS = 100_000
_MAX_LEDGER_BYTES = 64 * 1024 * 1024
_MAX_LINE_BYTES = 320 * 1024
_HEX = re.compile(r"^[0-9a-f]{64}$")


class QdasLedgerError(RuntimeError):
    """The QDAS event ledger is malformed, unsafe, or cannot be updated."""


class QdasEventLedger:
    """Local append-only ledger; its hash chain detects edits but not whole-store replacement."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path).expanduser().absolute()
        if not self.path.name or self.path.name in {".", ".."}:
            raise ValueError("ledger path must identify a file")

    def _check_parent(self, *, create: bool) -> None:
        parent = self.path.parent
        self._check_ancestor_links(parent)
        if parent.exists() or parent.is_symlink():
            self._check_path(parent, directory=True)
        elif create:
            try:
                parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            except OSError as exc:
                raise QdasLedgerError("cannot create QDAS ledger directory") from exc
            if os.name != "nt":
                parent.chmod(0o700)
            self._check_path(parent, directory=True)
        else:
            raise QdasLedgerError("QDAS ledger directory does not exist")
        self._check_ancestor_links(parent)
        if os.name != "nt" and parent.stat().st_mode & 0o077:
            raise QdasLedgerError("QDAS ledger directory must be owner-only")

    @staticmethod
    def _check_ancestor_links(parent: Path) -> None:
        """Reject symlink/reparse traversal in every existing parent component."""
        for ancestor in reversed((parent, *parent.parents)):
            try:
                info = ancestor.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise QdasLedgerError("cannot inspect QDAS ledger ancestor") from exc
            if stat.S_ISLNK(info.st_mode):
                raise QdasLedgerError("QDAS ledger ancestor paths must not be symbolic links")
            attributes = getattr(info, "st_file_attributes", 0)
            if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise QdasLedgerError("QDAS ledger ancestor paths must not be reparse points")
            if not stat.S_ISDIR(info.st_mode):
                raise QdasLedgerError("QDAS ledger ancestor must be a directory")

    @staticmethod
    def _check_path(path: Path, *, directory: bool) -> os.stat_result:
        try:
            info = path.lstat()
        except OSError as exc:
            raise QdasLedgerError("cannot inspect QDAS ledger path") from exc
        if stat.S_ISLNK(info.st_mode):
            raise QdasLedgerError("QDAS ledger paths must not be symbolic links")
        attributes = getattr(info, "st_file_attributes", 0)
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise QdasLedgerError("QDAS ledger paths must not be reparse points")
        if directory and not stat.S_ISDIR(info.st_mode):
            raise QdasLedgerError("QDAS ledger parent must be a directory")
        if not directory and not stat.S_ISREG(info.st_mode):
            raise QdasLedgerError("QDAS ledger must be a regular file")
        if os.name != "nt":
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise QdasLedgerError("QDAS ledger must be owned by the current user and owner-only")
        return info

    def _lock(self, timeout: float = 5.0):
        ledger = self

        class Lock:
            def __init__(self) -> None:
                self.stream = None

            def __enter__(self):
                lock_path = ledger.path.with_name(ledger.path.name + ".lock")
                if lock_path.exists() or lock_path.is_symlink():
                    ledger._check_path(lock_path, directory=False)
                flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
                try:
                    descriptor = os.open(lock_path, flags, 0o600)
                except OSError as exc:
                    raise QdasLedgerError("cannot open QDAS ledger lock") from exc
                if os.name != "nt":
                    os.fchmod(descriptor, 0o600)
                self.stream = os.fdopen(descriptor, "r+b")
                deadline = time.monotonic() + timeout
                while True:
                    try:
                        if os.name == "nt":
                            import msvcrt
                            self.stream.seek(0, os.SEEK_END)
                            if self.stream.tell() == 0:
                                self.stream.write(b"\0")
                                self.stream.flush()
                            self.stream.seek(0)
                            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        return self
                    except OSError as exc:
                        if time.monotonic() >= deadline:
                            self.stream.close()
                            raise QdasLedgerError("timed out waiting for QDAS ledger lock") from exc
                        time.sleep(0.05)

            def __exit__(self, exc_type, exc, traceback):
                if self.stream is not None:
                    try:
                        if os.name == "nt":
                            import msvcrt
                            self.stream.seek(0)
                            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
                    finally:
                        self.stream.close()
                return False

        return Lock()

    @staticmethod
    def _parse_line(line: bytes, expected_sequence: int, previous_digest: str) -> dict[str, Any]:
        if not line or len(line) > _MAX_LINE_BYTES:
            raise QdasLedgerError("QDAS ledger record is empty or exceeds its size limit")
        try:
            source = line.decode("utf-8")
            record = json.loads(source, object_pairs_hook=_unique_pairs)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise QdasLedgerError("QDAS ledger contains invalid strict JSON") from exc
        fields = {
            "schema", "sequence", "previous_digest", "event",
            "classification", "record_digest",
        }
        allowed_fields = fields | {"hypotheses"}
        record_fields = frozenset(record) if isinstance(record, dict) else frozenset()
        if not isinstance(record, dict) or record_fields not in {frozenset(fields), frozenset(allowed_fields)}:
            raise QdasLedgerError("QDAS ledger record has missing or unexpected fields")
        if type(record["schema"]) is not int or record["schema"] != 1:
            raise QdasLedgerError("unsupported QDAS ledger schema")
        if type(record["sequence"]) is not int or record["sequence"] != expected_sequence:
            raise QdasLedgerError("QDAS ledger sequence is not contiguous")
        if record["previous_digest"] != previous_digest:
            raise QdasLedgerError("QDAS ledger previous digest does not match")
        payload = {key: value for key, value in record.items() if key != "record_digest"}
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        if not isinstance(record["record_digest"], str) or not _HEX.fullmatch(record["record_digest"]):
            raise QdasLedgerError("QDAS ledger record digest is invalid")
        if digest != record["record_digest"]:
            raise QdasLedgerError("QDAS ledger record digest mismatch")
        if _canonical(record) + b"\n" != line:
            raise QdasLedgerError("QDAS ledger record is not canonically serialized")
        try:
            event = ExecutionEvent.from_dict(record["event"])
            classification_data = record["classification"]
            classification = (
                None if classification_data is None
                else FailureClassification(**classification_data)
            )
        except (TypeError, ValueError) as exc:
            raise QdasLedgerError("QDAS ledger event or classification is invalid") from exc
        if classification is not None and classification.event_id != event.event_id:
            raise QdasLedgerError("QDAS classification belongs to another event")
        expected_classification = classify_failure(event)
        if (expected_classification is None) != (classification is None):
            raise QdasLedgerError("QDAS classification presence contradicts the native classifier")
        if classification is not None and expected_classification is not None:
            expected_fields = expected_classification.to_dict()
            actual_fields = classification.to_dict()
            expected_fields.pop("classification_id")
            actual_fields.pop("classification_id")
            if expected_fields != actual_fields:
                raise QdasLedgerError("QDAS classification does not match the native classifier")
        if (event.execution_status == "PASS") != (classification is None):
            raise QdasLedgerError("QDAS classification presence contradicts event status")
        if "hypotheses" in record:
            raw_hypotheses = record["hypotheses"]
            if not isinstance(raw_hypotheses, list) or len(raw_hypotheses) > 8:
                raise QdasLedgerError("QDAS hypotheses must be a bounded array")
            if event.execution_status == "PASS" and raw_hypotheses:
                raise QdasLedgerError("passing events cannot carry failure hypotheses")
            if event.execution_status != "PASS" and not raw_hypotheses:
                raise QdasLedgerError("failed events with persisted diagnosis require at least one hypothesis")
            for raw in raw_hypotheses:
                try:
                    if not isinstance(raw, dict):
                        raise ValueError("hypothesis must be an object")
                    supporting = tuple(FailureObservation(**item) for item in raw["supporting_evidence"])
                    contradicting = tuple(FailureObservation(**item) for item in raw["contradicting_evidence"])
                    hypothesis = FailureHypothesis(
                        hypothesis_id=raw["hypothesis_id"],
                        event_id=raw["event_id"],
                        failure_category=raw["failure_category"],
                        rule_id=raw["rule_id"],
                        statement=raw["statement"],
                        supporting_evidence=supporting,
                        contradicting_evidence=contradicting,
                        confidence=raw["confidence"],
                        confidence_rationale=raw["confidence_rationale"],
                        missing_evidence=tuple(raw["missing_evidence"]),
                        state=raw["state"],
                    )
                    expected_fields = {
                        "hypothesis_id", "event_id", "failure_category", "rule_id",
                        "statement", "supporting_evidence", "contradicting_evidence",
                        "confidence", "confidence_rationale", "missing_evidence", "state",
                    }
                    if set(raw) != expected_fields or hypothesis.to_dict() != raw:
                        raise ValueError("hypothesis fields are not canonical")
                    if hypothesis.event_id != event.event_id:
                        raise ValueError("hypothesis belongs to another event")
                    if classification is None or hypothesis.failure_category != classification.category:
                        raise ValueError("hypothesis category contradicts native classification")
                    all_observations = hypothesis.supporting_evidence + hypothesis.contradicting_evidence
                    for observation in all_observations:
                        if observation.event_id != event.event_id:
                            raise ValueError("observation belongs to another event")
                    observation_ids = sorted(item.observation_id for item in hypothesis.supporting_evidence)
                    if hypothesis.rule_id == "QDAS-ROOT-UNKNOWN-001":
                        expected_id = hashlib.sha256(
                            (event.event_id + event.stdout_digest + event.stderr_digest).encode("ascii")
                        ).hexdigest()[:32]
                    else:
                        expected_id = hashlib.sha256(_canonical({
                            "event_id": event.event_id,
                            "rule_id": hypothesis.rule_id,
                            "evidence_ids": observation_ids,
                        })).hexdigest()[:32]
                    if hypothesis.hypothesis_id != expected_id:
                        raise ValueError("hypothesis identity does not match its evidence")
                except (KeyError, TypeError, ValueError) as exc:
                    raise QdasLedgerError("QDAS ledger contains an invalid evidence-linked hypothesis") from exc
        return record

    def _verify_unlocked(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        info = self._check_path(self.path, directory=False)
        if info.st_size > _MAX_LEDGER_BYTES:
            raise QdasLedgerError("QDAS ledger exceeds the 64 MiB limit")
        try:
            data = self.path.read_bytes()
        except OSError as exc:
            raise QdasLedgerError("cannot read QDAS ledger") from exc
        if not data:
            return ()
        if not data.endswith(b"\n"):
            raise QdasLedgerError("QDAS ledger has an incomplete trailing record")
        lines = data.splitlines(keepends=True)
        if len(lines) > _MAX_RECORDS:
            raise QdasLedgerError("QDAS ledger exceeds the 100000-record limit")
        records = []
        previous = _GENESIS
        for sequence, line in enumerate(lines, start=1):
            record = self._parse_line(line, sequence, previous)
            records.append(record)
            previous = record["record_digest"]
        return tuple(records)

    def verify(self) -> tuple[dict[str, Any], ...]:
        self._check_parent(create=False)
        with self._lock():
            return self._verify_unlocked()

    def append(
        self,
        event: ExecutionEvent,
        classification: FailureClassification | None,
        hypotheses: tuple[FailureHypothesis, ...] | list[FailureHypothesis] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(event, ExecutionEvent):
            raise TypeError("event must be an ExecutionEvent")
        if classification is not None and not isinstance(classification, FailureClassification):
            raise TypeError("classification must be a FailureClassification or None")
        if hypotheses is not None and (
            not isinstance(hypotheses, (tuple, list))
            or len(hypotheses) > 8
            or any(not isinstance(item, FailureHypothesis) for item in hypotheses)
        ):
            raise TypeError("hypotheses must be a bounded sequence of FailureHypothesis values")
        if hypotheses is not None and any(item.event_id != event.event_id for item in hypotheses):
            raise ValueError("hypothesis belongs to a different execution event")
        if event.execution_status == "PASS" and hypotheses:
            raise ValueError("successful events cannot carry failure hypotheses")
        if event.execution_status != "PASS" and hypotheses is not None and not hypotheses:
            raise ValueError("failed events with persisted diagnosis require at least one hypothesis")
        if classification is not None and classification.event_id != event.event_id:
            raise ValueError("classification belongs to a different execution event")
        expected_classification = classify_failure(event)
        if (expected_classification is None) != (classification is None):
            raise ValueError("failed events require one classification from the native classifier")
        if classification is not None and expected_classification is not None:
            expected_fields = expected_classification.to_dict()
            actual_fields = classification.to_dict()
            expected_fields.pop("classification_id")
            actual_fields.pop("classification_id")
            if expected_fields != actual_fields:
                raise ValueError("classification does not match the native Qyrenith classifier")
        if (event.execution_status == "PASS") != (classification is None):
            raise ValueError("PASS events require no classification; failed events require one")
        self._check_parent(create=True)
        with self._lock():
            existing = self._verify_unlocked()
            if len(existing) >= _MAX_RECORDS:
                raise QdasLedgerError("QDAS ledger reached its record limit")
            if any(item["event"]["event_id"] == event.event_id for item in existing):
                raise QdasLedgerError("execution event has already been recorded")
            previous = existing[-1]["record_digest"] if existing else _GENESIS
            payload = {
                "schema": 1,
                "sequence": len(existing) + 1,
                "previous_digest": previous,
                "event": event.to_dict(),
                "classification": classification.to_dict() if classification else None,
            }
            if hypotheses is not None:
                payload["hypotheses"] = [item.to_dict() for item in hypotheses]
            record = {
                **payload,
                "record_digest": hashlib.sha256(_canonical(payload)).hexdigest(),
            }
            line = _canonical(record) + b"\n"
            if len(line) > _MAX_LINE_BYTES:
                raise QdasLedgerError("QDAS ledger record exceeds its size limit")
            current_size = self.path.stat().st_size if self.path.exists() else 0
            if current_size + len(line) > _MAX_LEDGER_BYTES:
                raise QdasLedgerError("QDAS ledger would exceed the 64 MiB limit")
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(self.path, flags, 0o600)
                if os.name != "nt":
                    os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "ab") as stream:
                    stream.write(line)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise QdasLedgerError("cannot append QDAS ledger record") from exc
            self._verify_unlocked()
            return record


def verify_qdas_ledger(path: str | os.PathLike[str]) -> tuple[dict[str, Any], ...]:
    return QdasEventLedger(path).verify()


__all__ = ["QdasEventLedger", "QdasLedgerError", "verify_qdas_ledger"]

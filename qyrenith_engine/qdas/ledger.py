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
        if os.name != "nt" and parent.stat().st_mode & 0o077:
            raise QdasLedgerError("QDAS ledger directory must be owner-only")

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
        if not isinstance(record, dict) or set(record) != fields:
            raise QdasLedgerError("QDAS ledger record has missing or unexpected fields")
        if type(record["schema"]) is not int or record["schema"] != 1:
            raise QdasLedgerError("unsupported QDAS ledger schema")
        if type(record["sequence"]) is not int or record["sequence"] != expected_sequence:
            raise QdasLedgerError("QDAS ledger sequence is not contiguous")
        if record["previous_digest"] != previous_digest:
            raise QdasLedgerError("QDAS ledger previous digest does not match")
        payload = {key: record[key] for key in fields if key != "record_digest"}
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
        return record

    def verify(self) -> tuple[dict[str, Any], ...]:
        self._check_parent(create=False)
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

    def append(
        self,
        event: ExecutionEvent,
        classification: FailureClassification | None,
    ) -> dict[str, Any]:
        if not isinstance(event, ExecutionEvent):
            raise TypeError("event must be an ExecutionEvent")
        if classification is not None and not isinstance(classification, FailureClassification):
            raise TypeError("classification must be a FailureClassification or None")
        if classification is not None and classification.event_id != event.event_id:
            raise ValueError("classification belongs to a different execution event")
        expected_classification = classify_failure(event)
        if (expected_classification is None) != (classification is None):
            raise ValueError("classification presence contradicts the native classifier")
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
            existing = self.verify()
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
            self.verify()
            return record


def verify_qdas_ledger(path: str | os.PathLike[str]) -> tuple[dict[str, Any], ...]:
    return QdasEventLedger(path).verify()


__all__ = ["QdasEventLedger", "QdasLedgerError", "verify_qdas_ledger"]

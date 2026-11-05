"""Owner-scoped, integrity-protected trust decisions outside project workspaces.

The store protects against repository-controlled trust injection and accidental
corruption. It does not protect against malicious code already running as the
same OS user, and its HMAC is not publisher identity or remote attestation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import time
import uuid
from typing import Any

_SCHEMA = 1
_MAX_STORE_BYTES = 4 * 1024 * 1024
_MAX_EVENTS = 100_000
_MAX_TEXT = 1024
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_KINDS = {
    "KNOWLEDGE_CATALOG",
    "WORKER_MANIFEST",
    "WORKER_QUALIFICATION",
    "EXECUTION_POLICY",
    "APPROVAL_NONCE",
}
_DECISIONS = {"TRUST", "REVOKE", "CONSUME"}


class TrustStoreError(RuntimeError):
    """The owner trust store is missing, unsafe, corrupt, or inconsistent."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _timestamp(value: datetime, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise TrustStoreError(f"{field} must be a bounded UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TrustStoreError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrustStoreError(f"{field} must include a timezone")
    normalized = parsed.astimezone(timezone.utc)
    if _timestamp(normalized, field) != value:
        raise TrustStoreError(f"{field} must use canonical UTC seconds")
    return normalized


def default_trust_store_path() -> Path:
    """Return the per-user configuration path, never a project-relative path."""
    if os.name == "nt":
        root = os.environ.get("APPDATA")
        base = Path(root).expanduser() if root else Path.home() / "AppData" / "Roaming"
    else:
        root = os.environ.get("XDG_CONFIG_HOME")
        base = Path(root).expanduser() if root else Path.home() / ".config"
    if not base.is_absolute():
        raise TrustStoreError("user configuration directory must be an absolute path")
    return base / "Qyrenith" / "trust-store.json"


def _reject_reparse_or_symlink(path: Path, *, directory: bool) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise TrustStoreError(f"cannot inspect trust-store path: {path.name}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise TrustStoreError(f"trust-store path must not be a symbolic link: {path.name}")
    attributes = getattr(info, "st_file_attributes", 0)
    if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        raise TrustStoreError(f"trust-store path must not be a reparse point: {path.name}")
    if directory and not stat.S_ISDIR(info.st_mode):
        raise TrustStoreError("trust-store parent must be a directory")
    if not directory and not stat.S_ISREG(info.st_mode):
        raise TrustStoreError("trust-store files must be regular files")
    if os.name != "nt":
        if info.st_uid != os.getuid():
            raise TrustStoreError("trust-store path is not owned by the current user")
        if info.st_mode & 0o077:
            raise TrustStoreError("trust-store permissions expose data beyond the owner")
    return info


def _reject_git_worktree_path(directory: Path) -> None:
    current = directory.resolve(strict=True)
    while True:
        marker = current / ".git"
        if marker.exists() or marker.is_symlink():
            raise TrustStoreError("owner trust store must not be placed inside a Git worktree")
        if current.parent == current:
            break
        current = current.parent


def _ensure_private_directory(directory: Path, *, create: bool) -> None:
    if directory.exists() or directory.is_symlink():
        _reject_reparse_or_symlink(directory, directory=True)
    elif create:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        _reject_reparse_or_symlink(directory, directory=True)
    else:
        raise TrustStoreError("trust-store directory does not exist")
    if os.name != "nt":
        try:
            directory.chmod(0o700)
        except OSError as exc:
            raise TrustStoreError("cannot secure trust-store directory permissions") from exc
        _reject_reparse_or_symlink(directory, directory=True)
        if directory.stat().st_mode & 0o077:
            raise TrustStoreError("trust-store directory must be owner-only")


def _write_exclusive(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        raise
    except OSError as exc:
        raise TrustStoreError(f"cannot create trust-store file: {path.name}") from exc
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


@dataclass(frozen=True)
class TrustDecision:
    sequence: int
    event_id: str
    subject_kind: str
    subject_digest: str
    decision: str
    reviewed_by: str
    reviewed_at: str
    expires_at: str | None
    rationale: str

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("trust decision sequence must be positive")
        if not isinstance(self.event_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.event_id):
            raise ValueError("trust decision event_id must be a UUID hex value")
        if self.subject_kind not in _KINDS:
            raise ValueError("unsupported trust subject kind")
        if not isinstance(self.subject_digest, str) or not _DIGEST.fullmatch(self.subject_digest):
            raise ValueError("subject_digest must use sha256:<64 lowercase hex>")
        if self.subject_kind == "APPROVAL_NONCE":
            if self.decision != "CONSUME" or self.expires_at is not None:
                raise ValueError("approval nonce events must use CONSUME without expiry")
        elif self.decision not in {"TRUST", "REVOKE"}:
            raise ValueError("trust decisions must use TRUST or REVOKE")
        for field, value in (("reviewed_by", self.reviewed_by), ("rationale", self.rationale)):
            if not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT:
                raise ValueError(f"{field} must be non-empty bounded text")
        _parse_timestamp(self.reviewed_at, "reviewed_at")
        if self.expires_at is not None:
            expiry = _parse_timestamp(self.expires_at, "expires_at")
            if expiry <= _parse_timestamp(self.reviewed_at, "reviewed_at"):
                raise ValueError("trust decision expiry must follow review time")
        if self.decision in {"REVOKE", "CONSUME"} and self.expires_at is not None:
            raise ValueError("revocation and nonce-consumption events cannot expire")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "subject_kind": self.subject_kind,
            "subject_digest": self.subject_digest,
            "decision": self.decision,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "expires_at": self.expires_at,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, value: object) -> "TrustDecision":
        fields = {
            "sequence", "event_id", "subject_kind", "subject_digest", "decision",
            "reviewed_by", "reviewed_at", "expires_at", "rationale",
        }
        if not isinstance(value, dict) or set(value) != fields:
            raise TrustStoreError("trust decision has missing or unexpected fields")
        return cls(**value)


class OwnerTrustStore:
    """Append-only owner trust decisions with canonical HMAC integrity protection."""

    def __init__(self, path: Path, key: bytes, document: dict[str, Any]) -> None:
        self.path = path
        self._key = key
        self._document = document

    @classmethod
    def open(
        cls, path: str | Path | None = None, *, create: bool = False
    ) -> "OwnerTrustStore":
        target = Path(path) if path is not None else default_trust_store_path()
        target = target.expanduser().absolute()
        if not target.name or target.name in {".", ".."}:
            raise TrustStoreError("trust-store filename is invalid")
        _ensure_private_directory(target.parent, create=create)
        _reject_git_worktree_path(target.parent)
        if os.name == "nt":
            profile = Path.home().resolve(strict=True)
            profile_store_root = target.parent.parent.resolve(strict=True)
            try:
                profile_store_root.relative_to(profile)
            except ValueError as exc:
                raise TrustStoreError(
                    "default Windows trust store must remain inside the current user profile"
                ) from exc
            _reject_reparse_or_symlink(profile_store_root, directory=True)
        key_path = target.with_name(target.name + ".key")
        store_exists = target.exists() or target.is_symlink()
        key_exists = key_path.exists() or key_path.is_symlink()
        if store_exists:
            _reject_reparse_or_symlink(target, directory=False)
        if key_exists:
            _reject_reparse_or_symlink(key_path, directory=False)
        if not store_exists and not key_exists:
            if not create:
                raise TrustStoreError("owner trust store is not initialized")
            key = secrets.token_bytes(32)
            try:
                _write_exclusive(key_path, key)
            except FileExistsError as exc:
                raise TrustStoreError("trust-store key appeared during initialization") from exc
            payload = cls._new_document(key)
            try:
                _write_exclusive(target, _canonical(payload) + b"\n")
            except Exception:
                try:
                    key_path.unlink()
                except OSError:
                    pass
                raise
            return cls(target, key, payload)
        if not store_exists or not key_exists:
            raise TrustStoreError("trust store and integrity key must exist together")
        key_info = _reject_reparse_or_symlink(key_path, directory=False)
        store_info = _reject_reparse_or_symlink(target, directory=False)
        if key_info.st_size != 32:
            raise TrustStoreError("trust-store integrity key must contain exactly 32 bytes")
        if store_info.st_size > _MAX_STORE_BYTES:
            raise TrustStoreError("trust store exceeds the 4 MiB limit")
        try:
            key = key_path.read_bytes()
            source = target.read_bytes()
        except OSError as exc:
            raise TrustStoreError("cannot read owner trust store") from exc
        if len(key) != 32:
            raise TrustStoreError("trust-store integrity key must contain exactly 32 bytes")
        document = cls._parse_document(source, key)
        return cls(target, key, document)

    @staticmethod
    def _new_document(key: bytes) -> dict[str, Any]:
        payload = {
            "schema": _SCHEMA,
            "store_id": uuid.uuid4().hex,
            "generation": 0,
            "events": [],
        }
        return {**payload, "hmac_sha256": hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()}

    @staticmethod
    def _parse_document(source: bytes, key: bytes) -> dict[str, Any]:
        if len(source) > _MAX_STORE_BYTES:
            raise TrustStoreError("trust store exceeds the 4 MiB limit")
        try:
            text = source.decode("utf-8")
            document = json.loads(
                text,
                object_pairs_hook=OwnerTrustStore._unique_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    TrustStoreError(f"invalid JSON constant: {value}")
                ),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TrustStoreError) as exc:
            raise TrustStoreError("trust store is not valid strict UTF-8 JSON") from exc
        expected = {"schema", "store_id", "generation", "events", "hmac_sha256"}
        if not isinstance(document, dict) or set(document) != expected:
            raise TrustStoreError("trust store has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != _SCHEMA:
            raise TrustStoreError("unsupported trust-store schema")
        if not isinstance(document["store_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", document["store_id"]):
            raise TrustStoreError("trust-store identity is invalid")
        if type(document["generation"]) is not int or not 0 <= document["generation"] <= _MAX_EVENTS:
            raise TrustStoreError("trust-store generation is invalid")
        if not isinstance(document["events"], list) or len(document["events"]) != document["generation"]:
            raise TrustStoreError("trust-store event count does not match generation")
        try:
            events = tuple(TrustDecision.from_dict(item) for item in document["events"])
        except (TypeError, ValueError, TrustStoreError) as exc:
            raise TrustStoreError("trust store contains an invalid decision event") from exc
        if tuple(item.sequence for item in events) != tuple(range(1, len(events) + 1)):
            raise TrustStoreError("trust-store event sequence is not contiguous")
        if len({item.event_id for item in events}) != len(events):
            raise TrustStoreError("trust-store event IDs must be unique")
        payload = {key_name: document[key_name] for key_name in ("schema", "store_id", "generation", "events")}
        expected_mac = hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()
        if not isinstance(document["hmac_sha256"], str) or not hmac.compare_digest(expected_mac, document["hmac_sha256"]):
            raise TrustStoreError("trust-store integrity verification failed")
        if source not in {_canonical(document), _canonical(document) + b"\n"}:
            raise TrustStoreError("trust store is not canonically serialized")
        return document

    @staticmethod
    def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise TrustStoreError(f"duplicate trust-store JSON key: {key}")
            result[key] = value
        return result

    @property
    def store_id(self) -> str:
        return self._document["store_id"]

    @property
    def generation(self) -> int:
        return self._document["generation"]

    def decisions(self) -> tuple[TrustDecision, ...]:
        with self._locked():
            self._document = self._reload_locked()
            return tuple(TrustDecision.from_dict(item) for item in self._document["events"])

    def _locked(self):
        class Lock:
            def __init__(self, path: Path) -> None:
                self.path = path
                self.stream = None

            def __enter__(self):
                if self.path.exists() or self.path.is_symlink():
                    _reject_reparse_or_symlink(self.path, directory=False)
                flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(self.path, flags, 0o600)
                if os.name != "nt":
                    os.fchmod(descriptor, 0o600)
                    info = os.fstat(descriptor)
                    if info.st_uid != os.getuid() or info.st_mode & 0o077:
                        os.close(descriptor)
                        raise TrustStoreError("trust-store lock permissions are unsafe")
                self.stream = os.fdopen(descriptor, "r+b")
                deadline = time.monotonic() + 5.0
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
                        break
                    except OSError as exc:
                        if time.monotonic() >= deadline:
                            self.stream.close()
                            raise TrustStoreError("timed out waiting for the owner trust-store lock") from exc
                        time.sleep(0.05)
                return self

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

        return Lock(self.path.with_name(self.path.name + ".lock"))

    def _reload_locked(self) -> dict[str, Any]:
        _reject_reparse_or_symlink(self.path, directory=False)
        source = self.path.read_bytes()
        document = self._parse_document(source, self._key)
        if document["store_id"] != self.store_id:
            raise TrustStoreError("trust-store identity changed during update")
        return document

    def append_decision(
        self,
        subject_kind: str,
        subject_digest: str,
        decision: str,
        *,
        reviewed_by: str,
        reviewed_at: datetime | None = None,
        expires_at: datetime | None = None,
        rationale: str,
        expected_generation: int | None = None,
    ) -> TrustDecision:
        if expected_generation is not None and (type(expected_generation) is not int or expected_generation < 0):
            raise ValueError("expected_generation must be a non-negative integer")
        if subject_kind not in _KINDS:
            raise ValueError("unsupported trust subject kind")
        if not isinstance(subject_digest, str) or not _DIGEST.fullmatch(subject_digest):
            raise ValueError("subject_digest must use sha256:<64 lowercase hex>")
        if subject_kind == "APPROVAL_NONCE":
            if decision != "CONSUME":
                raise ValueError("approval nonce events must use CONSUME")
        elif decision not in {"TRUST", "REVOKE"}:
            raise ValueError("trust decisions must use TRUST or REVOKE")
        instant = datetime.now(timezone.utc) if reviewed_at is None else reviewed_at
        reviewed_text = _timestamp(instant, "reviewed_at")
        expiry_text = _timestamp(expires_at, "expires_at") if expires_at is not None else None
        with self._locked():
            current = self._reload_locked()
            if expected_generation is not None and current["generation"] != expected_generation:
                raise TrustStoreError("trust store changed after host approval was issued")
            if current["generation"] >= _MAX_EVENTS:
                raise TrustStoreError("trust store reached its event limit")
            if subject_kind == "APPROVAL_NONCE" and any(
                item["subject_kind"] == "APPROVAL_NONCE"
                and item["subject_digest"] == subject_digest
                for item in current["events"]
            ):
                raise TrustStoreError("approval nonce has already been consumed")
            event = TrustDecision(
                sequence=current["generation"] + 1,
                event_id=uuid.uuid4().hex,
                subject_kind=subject_kind,
                subject_digest=subject_digest,
                decision=decision,
                reviewed_by=reviewed_by,
                reviewed_at=reviewed_text,
                expires_at=expiry_text,
                rationale=rationale,
            )
            payload = {
                "schema": _SCHEMA,
                "store_id": current["store_id"],
                "generation": event.sequence,
                "events": [*current["events"], event.to_dict()],
            }
            document = {
                **payload,
                "hmac_sha256": hmac.new(self.key, _canonical(payload), hashlib.sha256).hexdigest(),
            }
            _atomic_write(self.path, _canonical(document) + b"\n")
            self._document = document
            return event

    def trust(
        self,
        subject_kind: str,
        subject_digest: str,
        *,
        reviewed_by: str,
        reviewed_at: datetime | None = None,
        expires_at: datetime | None = None,
        rationale: str,
    ) -> TrustDecision:
        return self.append_decision(
            subject_kind, subject_digest, "TRUST", reviewed_by=reviewed_by,
            reviewed_at=reviewed_at, expires_at=expires_at, rationale=rationale,
        )

    def revoke(
        self,
        subject_kind: str,
        subject_digest: str,
        *,
        reviewed_by: str,
        reviewed_at: datetime | None = None,
        rationale: str,
    ) -> TrustDecision:
        return self.append_decision(
            subject_kind, subject_digest, "REVOKE", reviewed_by=reviewed_by,
            reviewed_at=reviewed_at, rationale=rationale,
        )

    def consume_nonce(
        self,
        nonce_digest: str,
        *,
        reviewed_by: str,
        reviewed_at: datetime | None = None,
        rationale: str = "One-time host approval consumed",
        expected_generation: int | None = None,
    ) -> TrustDecision:
        """Atomically record a single-use approval nonce; duplicate use fails closed."""
        return self.append_decision(
            "APPROVAL_NONCE", nonce_digest, "CONSUME",
            reviewed_by=reviewed_by, reviewed_at=reviewed_at,
            rationale=rationale, expected_generation=expected_generation,
        )

    def is_nonce_consumed(self, nonce_digest: str) -> bool:
        if not isinstance(nonce_digest, str) or not _DIGEST.fullmatch(nonce_digest):
            return False
        return any(
            event.subject_kind == "APPROVAL_NONCE"
            and event.subject_digest == nonce_digest
            and event.decision == "CONSUME"
            for event in self.decisions()
        )

    def sign_host_payload(self, payload: dict[str, Any]) -> str:
        """Create an integrity MAC for a host-approved canonical payload."""
        if not isinstance(payload, dict):
            raise TypeError("host approval payload must be an object")
        return hmac.new(self._key, _canonical(payload), hashlib.sha256).hexdigest()

    def verify_host_payload(self, payload: dict[str, Any], signature: str) -> bool:
        if not isinstance(payload, dict) or not isinstance(signature, str):
            return False
        expected = self.sign_host_payload(payload)
        return hmac.compare_digest(expected, signature)

    def is_trusted(
        self, subject_kind: str, subject_digest: str, *, now: datetime | None = None
    ) -> bool:
        if subject_kind not in _KINDS or not isinstance(subject_digest, str) or not _DIGEST.fullmatch(subject_digest):
            return False
        instant = datetime.now(timezone.utc) if now is None else now
        instant_text = _timestamp(instant, "now")
        at = _parse_timestamp(instant_text, "now")
        latest = None
        for event in self.decisions():
            if event.subject_kind == subject_kind and event.subject_digest == subject_digest:
                latest = event
        if latest is None or latest.decision != "TRUST":
            return False
        reviewed = _parse_timestamp(latest.reviewed_at, "reviewed_at")
        if reviewed > at:
            return False
        return latest.expires_at is None or _parse_timestamp(latest.expires_at, "expires_at") > at

    def require_trusted(
        self, subject_kind: str, subject_digest: str, *, now: datetime | None = None
    ) -> None:
        if not self.is_trusted(subject_kind, subject_digest, now=now):
            raise TrustStoreError(f"exact {subject_kind} digest is not currently trusted")


__all__ = [
    "OwnerTrustStore",
    "TrustDecision",
    "TrustStoreError",
    "default_trust_store_path",
]

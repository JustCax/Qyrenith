"""Deterministic, bounded, read-only project snapshots.

A snapshot fingerprints regular-file contents, portable relative paths, directory
structure, permission bits, and symlink targets. Symlinks are recorded but never
followed. Capture is fail-closed on unsupported filesystem objects or concurrent
changes; this is not an atomic filesystem snapshot or a security sandbox.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import unicodedata
from typing import Any

from .knowledge import strict_object_pairs


_DEFAULT_EXCLUSIONS = (".git", ".qyrenith", ".backups", "__pycache__")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CHUNK_SIZE = 1024 * 1024


class SnapshotError(ValueError):
    """A project snapshot could not be captured or validated safely."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _safe_relative_path(value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 1024:
        raise SnapshotError("snapshot path must be a bounded string")
    if allow_empty and value == "":
        return value
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        raise SnapshotError("snapshot path must be a canonical relative POSIX path")
    parts = value.split("/")
    if any(
        part in {"", ".", ".."}
        or len(part) > 255
        or part.endswith((".", " "))
        or ":" in part
        or unicodedata.normalize("NFC", part) != part
        or part.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
        or any(ord(char) < 32 or ord(char) == 127 for char in part)
        for part in parts
    ):
        raise SnapshotError("snapshot path contains a non-portable component")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class SnapshotLimits:
    max_entries: int = 200_000
    max_file_bytes: int = 256 * 1024 * 1024
    max_total_bytes: int = 2 * 1024 * 1024 * 1024
    max_depth: int = 64
    max_path_length: int = 1024

    def __post_init__(self) -> None:
        for field, maximum in (
            ("max_entries", 1_000_000),
            ("max_file_bytes", 2 * 1024 * 1024 * 1024),
            ("max_total_bytes", 16 * 1024 * 1024 * 1024),
            ("max_depth", 256),
            ("max_path_length", 1024),
        ):
            value = getattr(self, field)
            if type(value) is not int or not 1 <= value <= maximum:
                raise SnapshotError(f"{field} must be an integer between 1 and {maximum}")
        if self.max_file_bytes > self.max_total_bytes:
            raise SnapshotError("max_file_bytes cannot exceed max_total_bytes")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_entries": self.max_entries,
            "max_file_bytes": self.max_file_bytes,
            "max_total_bytes": self.max_total_bytes,
            "max_depth": self.max_depth,
            "max_path_length": self.max_path_length,
        }


@dataclass(frozen=True, slots=True)
class SnapshotEntry:
    path: str
    kind: str
    mode: int
    size: int | None = None
    content_digest: str | None = None
    link_target: str | None = None

    def __post_init__(self) -> None:
        _safe_relative_path(self.path)
        if not isinstance(self.kind, str) or self.kind not in {"file", "directory", "symlink"}:
            raise SnapshotError("snapshot entry kind must be file, directory, or symlink")
        if type(self.mode) is not int or not 0 <= self.mode <= 0o777:
            raise SnapshotError("snapshot mode must contain only portable permission bits")
        if self.kind == "file":
            if type(self.size) is not int or self.size < 0:
                raise SnapshotError("regular file entries require a non-negative size")
            if not isinstance(self.content_digest, str) or not _SHA256.fullmatch(self.content_digest):
                raise SnapshotError("regular file entries require a SHA-256 content digest")
            if self.link_target is not None:
                raise SnapshotError("regular file entries cannot contain a link target")
        elif self.kind == "directory":
            if self.size is not None or self.content_digest is not None or self.link_target is not None:
                raise SnapshotError("directory entries cannot contain file or link metadata")
        else:
            if self.size is not None or self.content_digest is not None:
                raise SnapshotError("symlink entries cannot contain regular-file metadata")
            if not isinstance(self.link_target, str) or not self.link_target or len(self.link_target) > 4096:
                raise SnapshotError("symlink entries require a bounded link target")
            if "\x00" in self.link_target:
                raise SnapshotError("symlink target contains a NUL byte")

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "kind": self.kind,
            "mode": self.mode,
            "size": self.size,
            "content_digest": self.content_digest,
            "link_target": self.link_target,
        }


@dataclass(frozen=True, slots=True)
class ProjectSnapshot:
    entries: tuple[SnapshotEntry, ...]
    excluded_paths: tuple[str, ...]
    limits: SnapshotLimits
    captured_at: str
    schema: int = 1

    def __post_init__(self) -> None:
        if type(self.schema) is not int or self.schema != 1:
            raise SnapshotError("unsupported project snapshot schema")
        if not isinstance(self.limits, SnapshotLimits):
            raise SnapshotError("snapshot limits must be SnapshotLimits")
        if not isinstance(self.entries, (tuple, list)) or len(self.entries) > self.limits.max_entries:
            raise SnapshotError("snapshot entries exceed the configured limit")
        entries = tuple(self.entries)
        if any(not isinstance(item, SnapshotEntry) for item in entries):
            raise SnapshotError("snapshot entries must be SnapshotEntry values")
        paths = [item.path for item in entries]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise SnapshotError("snapshot entries must have unique, canonical path order")
        portable_prefixes: dict[str, str] = {}
        for path in paths:
            parts = path.split("/")
            for index in range(1, len(parts) + 1):
                prefix = "/".join(parts[:index])
                folded = prefix.casefold()
                previous = portable_prefixes.setdefault(folded, prefix)
                if previous != prefix:
                    raise SnapshotError("snapshot entries contain a case-insensitive path collision")
        entry_map = {item.path: item for item in entries}
        total_bytes = 0
        for item in entries:
            parts = item.path.split("/")
            if len(parts) > self.limits.max_depth or len(item.path) > self.limits.max_path_length:
                raise SnapshotError("snapshot entry exceeds its declared depth or path limit")
            for index in range(1, len(parts)):
                parent = "/".join(parts[:index])
                if parent not in entry_map or entry_map[parent].kind != "directory":
                    raise SnapshotError("snapshot entries must include every directory parent")
            if item.kind == "file":
                if item.size > self.limits.max_file_bytes:
                    raise SnapshotError("snapshot file exceeds its declared per-file limit")
                total_bytes += item.size
        if total_bytes > self.limits.max_total_bytes:
            raise SnapshotError("snapshot files exceed their declared aggregate byte limit")
        if not isinstance(self.excluded_paths, (tuple, list)):
            raise SnapshotError("excluded_paths must be a sequence")
        exclusions = tuple(_safe_relative_path(item) for item in self.excluded_paths)
        if exclusions != tuple(sorted(set(exclusions))) or len(exclusions) != len({item.casefold() for item in exclusions}):
            raise SnapshotError("excluded paths must be unique and canonically sorted")
        exclusion_set = {item.casefold() for item in exclusions}
        for excluded in exclusions:
            parts = excluded.split("/")
            if any("/".join(parts[:index]) in exclusion_set for index in range(1, len(parts))):
                raise SnapshotError("excluded paths must not redundantly contain nested exclusions")
        for item in entries:
            parts = item.path.split("/")
            if any("/".join(parts[:index]).casefold() in exclusion_set for index in range(1, len(parts) + 1)):
                raise SnapshotError("snapshot entries cannot contain excluded paths")
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "excluded_paths", exclusions)
        object.__setattr__(self, "captured_at", _validate_timestamp(self.captured_at))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": 1,
            "entries": [item.to_dict() for item in self.entries],
            "excluded_paths": list(self.excluded_paths),
            "limits": self.limits.to_dict(),
            "captured_at": self.captured_at,
        }

    @property
    def snapshot_digest(self) -> str:
        """Content/policy identity; intentionally excludes capture time."""
        payload = self.to_dict()
        payload.pop("captured_at")
        return _digest(payload)

    def to_document(self) -> dict[str, object]:
        return {**self.to_dict(), "snapshot_digest": self.snapshot_digest}

    def to_json_bytes(self) -> bytes:
        encoded = _canonical(self.to_document()) + b"\n"
        if len(encoded) > 64 * 1024 * 1024:
            raise SnapshotError("project snapshot export exceeds the 64 MiB limit")
        return encoded

    @classmethod
    def from_document(cls, document: object) -> "ProjectSnapshot":
        expected = {
            "schema", "entries", "excluded_paths", "limits", "captured_at", "snapshot_digest"
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise SnapshotError("snapshot document has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise SnapshotError("unsupported project snapshot schema")
        payload = {key: value for key, value in document.items() if key != "snapshot_digest"}
        payload.pop("captured_at", None)
        try:
            computed_digest = _digest(payload)
        except (TypeError, ValueError) as exc:
            raise SnapshotError("project snapshot contains invalid canonical values") from exc
        if not isinstance(document["snapshot_digest"], str) or computed_digest != document["snapshot_digest"]:
            raise SnapshotError("project snapshot digest mismatch")
        if not isinstance(document["limits"], dict) or set(document["limits"]) != {
            "max_entries", "max_file_bytes", "max_total_bytes", "max_depth", "max_path_length"
        }:
            raise SnapshotError("snapshot limits have missing or unexpected fields")
        if not isinstance(document["entries"], list) or not isinstance(document["excluded_paths"], list):
            raise SnapshotError("snapshot entries and exclusions must be arrays")
        entries = []
        for item in document["entries"]:
            if not isinstance(item, dict) or set(item) != {
                "path", "kind", "mode", "size", "content_digest", "link_target"
            }:
                raise SnapshotError("snapshot entry has missing or unexpected fields")
            entries.append(SnapshotEntry(**item))
        try:
            snapshot = cls(
                entries=tuple(entries),
                excluded_paths=tuple(document["excluded_paths"]),
                limits=SnapshotLimits(**document["limits"]),
                captured_at=document["captured_at"],
            )
        except (TypeError, KeyError) as exc:
            raise SnapshotError("project snapshot contains invalid contract fields") from exc
        if snapshot.to_document() != document:
            raise SnapshotError("project snapshot document is not canonical")
        return snapshot

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "ProjectSnapshot":
        if isinstance(data, bytes):
            if len(data) > 64 * 1024 * 1024:
                raise SnapshotError("project snapshot import exceeds the 64 MiB limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SnapshotError("project snapshot must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 64 * 1024 * 1024:
                raise SnapshotError("project snapshot import exceeds the 64 MiB limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source, object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise SnapshotError("invalid project snapshot JSON") from exc
        try:
            canonical = _canonical(document)
        except (TypeError, ValueError) as exc:
            raise SnapshotError("project snapshot contains non-canonical JSON values") from exc
        if source.encode("utf-8") not in {canonical, canonical + b"\n", canonical + b"\r\n"}:
            raise SnapshotError("project snapshot JSON is not canonical")
        return cls.from_document(document)


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise SnapshotError("captured_at must be a bounded UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError("captured_at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SnapshotError("captured_at must include a timezone")
    canonical = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if canonical != value:
        raise SnapshotError("captured_at must use canonical UTC format")
    return value


def _same_object(before: os.stat_result, after: os.stat_result) -> bool:
    # Windows exposes file identity and creation-time metadata differently
    # between FindFirstFile/DirEntry and a file descriptor. Keep the portable
    # checks there; POSIX additionally verifies device/inode and ctime.
    portable_match = (
        stat.S_IFMT(before.st_mode) == stat.S_IFMT(after.st_mode)
        and before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns
    )
    if not portable_match:
        return False
    if os.name == "nt":
        return True
    return (
        before.st_dev == after.st_dev
        and before.st_ino == after.st_ino
        and before.st_ctime_ns == after.st_ctime_ns
    )


def _hash_regular_file(path: Path, expected: os.stat_result, limits: SnapshotLimits, remaining: int) -> tuple[int, str]:
    if expected.st_size > limits.max_file_bytes:
        raise SnapshotError(f"file exceeds max_file_bytes: {path.name}")
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SnapshotError(f"cannot safely open regular file: {path.name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not _same_object(expected, before):
            raise SnapshotError(f"file changed before it could be read: {path.name}")
        hasher = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, min(_CHUNK_SIZE, remaining - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > limits.max_file_bytes or total > remaining:
                raise SnapshotError(f"project exceeds max_total_bytes: {path.name}")
            hasher.update(chunk)
        after = os.fstat(descriptor)
        if not _same_object(before, after) or total != after.st_size:
            raise SnapshotError(f"file changed while it was being read: {path.name}")
        return total, hasher.hexdigest()
    finally:
        os.close(descriptor)


def _hash_regular_file_at(
    directory_fd: int,
    name: str,
    display_path: str,
    expected: os.stat_result,
    limits: SnapshotLimits,
    remaining: int,
) -> tuple[int, str]:
    """Hash a regular file relative to an already-open, pinned parent directory."""
    if expected.st_size > limits.max_file_bytes:
        raise SnapshotError(f"file exceeds max_file_bytes: {display_path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise SnapshotError(f"cannot safely open regular file: {display_path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not _same_object(expected, before):
            raise SnapshotError(f"file changed before it could be read: {display_path}")
        hasher = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, min(_CHUNK_SIZE, remaining - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > limits.max_file_bytes or total > remaining:
                raise SnapshotError(f"project exceeds max_total_bytes: {display_path}")
            hasher.update(chunk)
        after = os.fstat(descriptor)
        if not _same_object(before, after) or total != after.st_size:
            raise SnapshotError(f"file changed while it was being read: {display_path}")
        return total, hasher.hexdigest()
    finally:
        os.close(descriptor)


def capture_project_snapshot(
    root: str | os.PathLike[str],
    *,
    excluded_paths: tuple[str, ...] = _DEFAULT_EXCLUSIONS,
    limits: SnapshotLimits | None = None,
) -> ProjectSnapshot:
    """Capture a bounded, read-only snapshot without following symlinks.

    POSIX systems use descriptor-relative traversal with O_NOFOLLOW so replacing
    a directory or file between enumeration and opening cannot redirect the walk.
    Platforms without the required descriptor APIs use the documented portable
    metadata-checked fallback.
    """
    policy = SnapshotLimits() if limits is None else limits
    if not isinstance(policy, SnapshotLimits):
        raise TypeError("limits must be SnapshotLimits")
    if not isinstance(excluded_paths, (tuple, list)):
        raise SnapshotError("excluded_paths must be a sequence")
    exclusions = tuple(sorted(set(_safe_relative_path(item) for item in excluded_paths)))
    if len(exclusions) > 10_000:
        raise SnapshotError("excluded_paths exceeds the 10000-entry limit")
    try:
        root_input = Path(root).absolute()
        input_stat = root_input.lstat()
        if stat.S_ISLNK(input_stat.st_mode):
            raise SnapshotError("project root must be a real directory, not a symlink")
        root_path = root_input.resolve(strict=True)
        root_stat = root_path.lstat()
    except SnapshotError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise SnapshotError("project root must be an existing directory") from exc
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
        raise SnapshotError("project root must be a real directory, not a symlink")

    entries: list[SnapshotEntry] = []
    total_bytes = 0
    enumerated_entries = 0
    exclusion_set = set(exclusions)

    def relative_path(relative: str, name: str) -> str:
        rel = f"{relative}/{name}" if relative else name
        _safe_relative_path(rel)
        if len(rel) > policy.max_path_length:
            raise SnapshotError("project path exceeds max_path_length")
        components = rel.split("/")
        if len(components) > policy.max_depth:
            raise SnapshotError("project exceeds max_depth")
        return rel

    def is_excluded(rel: str) -> bool:
        components = rel.split("/")
        return any(
            "/".join(components[:index]).casefold() in exclusion_set
            for index in range(1, len(components) + 1)
        )

    def walk_path(directory: Path, relative: str, depth: int) -> None:
        """Portable fallback for platforms without descriptor-relative traversal."""
        nonlocal total_bytes, enumerated_entries
        if depth > policy.max_depth:
            raise SnapshotError("project exceeds max_depth")
        try:
            before_dir = directory.stat(follow_symlinks=False)
            children = []
            with os.scandir(directory) as iterator:
                for child in iterator:
                    enumerated_entries += 1
                    if enumerated_entries > policy.max_entries:
                        raise SnapshotError("project traversal exceeds max_entries")
                    children.append(child)
            children.sort(key=lambda item: item.name)
            for child in children:
                if len(entries) >= policy.max_entries:
                    raise SnapshotError("project exceeds max_entries")
                rel = relative_path(relative, child.name)
                if is_excluded(rel):
                    continue
                try:
                    item_stat = child.stat(follow_symlinks=False)
                except OSError as exc:
                    raise SnapshotError(f"cannot stat project entry: {rel}") from exc
                mode = stat.S_IMODE(item_stat.st_mode)
                if stat.S_ISDIR(item_stat.st_mode):
                    entries.append(SnapshotEntry(rel, "directory", mode))
                    walk_path(Path(child.path), rel, depth + 1)
                elif stat.S_ISREG(item_stat.st_mode):
                    remaining = policy.max_total_bytes - total_bytes
                    size, digest = _hash_regular_file(Path(child.path), item_stat, policy, remaining)
                    total_bytes += size
                    entries.append(SnapshotEntry(rel, "file", mode, size, digest))
                elif stat.S_ISLNK(item_stat.st_mode):
                    target = os.readlink(child.path)
                    after_link = Path(child.path).lstat()
                    if not _same_object(item_stat, after_link):
                        raise SnapshotError(f"symbolic link changed during snapshot capture: {rel}")
                    entries.append(SnapshotEntry(rel, "symlink", mode, link_target=target))
                else:
                    raise SnapshotError(f"unsupported filesystem object: {rel}")
                if len(entries) > policy.max_entries:
                    raise SnapshotError("project exceeds max_entries")
            after_dir = directory.stat(follow_symlinks=False)
            if not _same_object(before_dir, after_dir):
                raise SnapshotError(f"directory changed during snapshot capture: {relative or '.'}")
        except OSError as exc:
            raise SnapshotError(f"cannot enumerate project directory: {relative or '.'}") from exc

    def walk_descriptor(directory_fd: int, relative: str, depth: int) -> None:
        """Walk a pinned directory using only descriptor-relative, no-follow operations."""
        nonlocal total_bytes, enumerated_entries
        if depth > policy.max_depth:
            raise SnapshotError("project exceeds max_depth")
        try:
            before_dir = os.fstat(directory_fd)
            with os.scandir(directory_fd) as iterator:
                names = []
                for child in iterator:
                    enumerated_entries += 1
                    if enumerated_entries > policy.max_entries:
                        raise SnapshotError("project traversal exceeds max_entries")
                    names.append(child.name)
            for name in sorted(names):
                if len(entries) >= policy.max_entries:
                    raise SnapshotError("project exceeds max_entries")
                rel = relative_path(relative, name)
                if is_excluded(rel):
                    continue
                try:
                    item_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError as exc:
                    raise SnapshotError(f"cannot stat project entry: {rel}") from exc
                mode = stat.S_IMODE(item_stat.st_mode)
                if stat.S_ISDIR(item_stat.st_mode):
                    entries.append(SnapshotEntry(rel, "directory", mode))
                    child_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
                    child_fd = os.open(name, child_flags, dir_fd=directory_fd)
                    try:
                        opened_stat = os.fstat(child_fd)
                        if not stat.S_ISDIR(opened_stat.st_mode) or not _same_object(item_stat, opened_stat):
                            raise SnapshotError(f"directory changed before it could be traversed: {rel}")
                        walk_descriptor(child_fd, rel, depth + 1)
                    finally:
                        os.close(child_fd)
                elif stat.S_ISREG(item_stat.st_mode):
                    remaining = policy.max_total_bytes - total_bytes
                    size, digest = _hash_regular_file_at(
                        directory_fd, name, rel, item_stat, policy, remaining
                    )
                    total_bytes += size
                    entries.append(SnapshotEntry(rel, "file", mode, size, digest))
                elif stat.S_ISLNK(item_stat.st_mode):
                    target = os.readlink(name, dir_fd=directory_fd)
                    after_link = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if not _same_object(item_stat, after_link):
                        raise SnapshotError(f"symbolic link changed during snapshot capture: {rel}")
                    entries.append(SnapshotEntry(rel, "symlink", mode, link_target=target))
                else:
                    raise SnapshotError(f"unsupported filesystem object: {rel}")
                if len(entries) > policy.max_entries:
                    raise SnapshotError("project exceeds max_entries")
            after_dir = os.fstat(directory_fd)
            if not _same_object(before_dir, after_dir):
                raise SnapshotError(f"directory changed during snapshot capture: {relative or '.'}")
        except SnapshotError:
            raise
        except OSError as exc:
            raise SnapshotError(f"cannot enumerate project directory: {relative or '.'}") from exc

    supports_descriptor_traversal = (
        os.name != "nt"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.readlink in os.supports_dir_fd
        and os.scandir in os.supports_fd
    )
    if supports_descriptor_traversal:
        root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            root_fd = os.open(root_path, root_flags)
        except OSError as exc:
            raise SnapshotError("project root could not be opened without following symlinks") from exc
        try:
            opened_root_stat = os.fstat(root_fd)
            if not stat.S_ISDIR(opened_root_stat.st_mode) or not _same_object(root_stat, opened_root_stat):
                raise SnapshotError("project root changed before snapshot traversal")
            walk_descriptor(root_fd, "", 0)
            final_fd_stat = os.fstat(root_fd)
            final_path_stat = root_path.lstat()
            if not _same_object(final_fd_stat, final_path_stat):
                raise SnapshotError("project root changed during snapshot capture")
        finally:
            os.close(root_fd)
    else:
        walk_path(root_path, "", 0)

    entries.sort(key=lambda item: item.path)
    return ProjectSnapshot(
        entries=tuple(entries),
        excluded_paths=exclusions,
        limits=policy,
        captured_at=_utc_now(),
    )


@dataclass(frozen=True, slots=True)
class SnapshotVerification:
    expected_digest: str
    actual_digest: str | None
    status: str
    changed_paths: tuple[str, ...]
    checked_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.expected_digest, str) or not _SHA256.fullmatch(self.expected_digest):
            raise SnapshotError("expected_digest must be a SHA-256 digest")
        if self.actual_digest is not None and (not isinstance(self.actual_digest, str) or not _SHA256.fullmatch(self.actual_digest)):
            raise SnapshotError("actual_digest must be a SHA-256 digest or None")
        if not isinstance(self.status, str) or self.status not in {"MATCH", "CHANGED"}:
            raise SnapshotError("unsupported snapshot verification status")
        if self.status == "MATCH" and self.expected_digest != self.actual_digest:
            raise SnapshotError("MATCH requires identical snapshot digests")
        if self.status == "CHANGED" and self.expected_digest == self.actual_digest:
            raise SnapshotError("CHANGED requires different snapshot digests")
        if not isinstance(self.changed_paths, (tuple, list)) or len(self.changed_paths) > 10_000:
            raise SnapshotError("changed_paths exceeds the 10000-entry result limit")
        changed = tuple(_safe_relative_path(path) for path in self.changed_paths)
        if changed != tuple(sorted(set(changed))):
            raise SnapshotError("changed_paths must be unique and canonically sorted")
        object.__setattr__(self, "changed_paths", changed)
        object.__setattr__(self, "checked_at", _validate_timestamp(self.checked_at))

    @property
    def matches(self) -> bool:
        return self.status == "MATCH"


def verify_project_snapshot(
    root: str | os.PathLike[str],
    expected: ProjectSnapshot,
) -> SnapshotVerification:
    """Recapture a project and compare its complete portable snapshot identity."""
    if not isinstance(expected, ProjectSnapshot):
        raise TypeError("expected must be a ProjectSnapshot")
    actual = capture_project_snapshot(
        root, excluded_paths=expected.excluded_paths, limits=expected.limits
    )
    if actual.snapshot_digest == expected.snapshot_digest:
        return SnapshotVerification(
            expected.snapshot_digest, actual.snapshot_digest, "MATCH", (), _utc_now()
        )
    before = {item.path: item for item in expected.entries}
    after = {item.path: item for item in actual.entries}
    changed = tuple(sorted(
        path for path in before.keys() | after.keys() if before.get(path) != after.get(path)
    ))
    return SnapshotVerification(
        expected.snapshot_digest, actual.snapshot_digest, "CHANGED",
        changed[:10_000], _utc_now(),
    )


def serialize_project_snapshot(snapshot: ProjectSnapshot) -> bytes:
    if not isinstance(snapshot, ProjectSnapshot):
        raise TypeError("snapshot must be a ProjectSnapshot")
    return snapshot.to_json_bytes()


def deserialize_project_snapshot(data: bytes | str) -> ProjectSnapshot:
    return ProjectSnapshot.from_json_bytes(data)


__all__ = [
    "ProjectSnapshot", "SnapshotEntry", "SnapshotError", "SnapshotLimits",
    "SnapshotVerification", "capture_project_snapshot", "verify_project_snapshot",
    "serialize_project_snapshot", "deserialize_project_snapshot",
]

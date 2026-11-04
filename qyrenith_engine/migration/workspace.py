"""Isolated, source-snapshot-pinned workspace materialization.

Workspace creation copies only regular files represented by a verified project
snapshot into a new, private workspace directory. It never copies symbolic links,
executes project code, launches workers, or mutates the source project.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import uuid
from typing import Any

from .knowledge import strict_object_pairs
from .model import MigrationIdentity
from .snapshot import (
    ProjectSnapshot,
    SnapshotError,
    SnapshotVerification,
    _same_object,
    _validate_timestamp,
    capture_project_snapshot,
    verify_project_snapshot,
)


class WorkspaceError(ValueError):
    """A workspace could not be created or verified safely."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkspaceDescriptor:
    workspace_id: str
    workspace_path: str
    project_path: str
    target: MigrationIdentity
    source_snapshot_digest: str
    file_count: int
    total_bytes: int
    created_at: str
    schema: int = 1

    def __post_init__(self) -> None:
        if type(self.schema) is not int or self.schema != 1:
            raise WorkspaceError("unsupported workspace descriptor schema")
        if not isinstance(self.workspace_id, str) or len(self.workspace_id) != 32:
            raise WorkspaceError("workspace_id must be a 32-character UUID hex value")
        try:
            uuid.UUID(hex=self.workspace_id)
        except ValueError as exc:
            raise WorkspaceError("workspace_id must be a UUID hex value") from exc
        for field in ("workspace_path", "project_path"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
                raise WorkspaceError(f"{field} must be a bounded absolute path")
            if not Path(value).is_absolute():
                raise WorkspaceError(f"{field} must be absolute")
        if not isinstance(self.target, MigrationIdentity):
            raise WorkspaceError("target must be a MigrationIdentity")
        if (
            not isinstance(self.source_snapshot_digest, str)
            or len(self.source_snapshot_digest) != 64
            or any(char not in "0123456789abcdef" for char in self.source_snapshot_digest)
        ):
            raise WorkspaceError("source_snapshot_digest must be a lowercase SHA-256 digest")
        for field in ("file_count", "total_bytes"):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise WorkspaceError(f"{field} must be a non-negative integer")
        object.__setattr__(self, "created_at", _validate_timestamp(self.created_at))
        try:
            workspace = Path(self.workspace_path)
            project = Path(self.project_path)
            if project.parent != workspace or project.name != "project":
                raise WorkspaceError("project_path must be the workspace's direct project child")
        except (OSError, ValueError) as exc:
            raise WorkspaceError("workspace paths are not canonical") from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": 1,
            "workspace_id": self.workspace_id,
            "workspace_path": self.workspace_path,
            "project_path": self.project_path,
            "target": self.target.to_dict(),
            "source_snapshot_digest": self.source_snapshot_digest,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "created_at": self.created_at,
        }

    @property
    def descriptor_digest(self) -> str:
        return _digest(self.to_dict())

    def to_document(self) -> dict[str, object]:
        return {**self.to_dict(), "descriptor_digest": self.descriptor_digest}

    def to_json_bytes(self) -> bytes:
        return _canonical(self.to_document()) + b"\n"

    @classmethod
    def from_document(cls, document: object) -> "WorkspaceDescriptor":
        expected = {
            "schema", "workspace_id", "workspace_path", "project_path", "target",
            "source_snapshot_digest", "file_count", "total_bytes", "created_at",
            "descriptor_digest",
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise WorkspaceError("workspace descriptor has missing or unexpected fields")
        payload = {key: value for key, value in document.items() if key != "descriptor_digest"}
        try:
            actual_digest = _digest(payload)
        except (TypeError, ValueError) as exc:
            raise WorkspaceError("workspace descriptor contains invalid canonical values") from exc
        if not isinstance(document["descriptor_digest"], str) or actual_digest != document["descriptor_digest"]:
            raise WorkspaceError("workspace descriptor digest mismatch")
        if not isinstance(document["target"], dict):
            raise WorkspaceError("workspace target identity must be an object")
        identity_fields = set(MigrationIdentity.__dataclass_fields__)
        if set(document["target"]) != identity_fields:
            raise WorkspaceError("workspace target identity has missing or unexpected fields")
        try:
            descriptor = cls(
                workspace_id=document["workspace_id"],
                workspace_path=document["workspace_path"],
                project_path=document["project_path"],
                target=MigrationIdentity(**document["target"]),
                source_snapshot_digest=document["source_snapshot_digest"],
                file_count=document["file_count"],
                total_bytes=document["total_bytes"],
                created_at=document["created_at"],
            )
        except (TypeError, KeyError) as exc:
            raise WorkspaceError("workspace descriptor contains invalid contract fields") from exc
        if descriptor.to_document() != document:
            raise WorkspaceError("workspace descriptor is not canonical")
        return descriptor

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "WorkspaceDescriptor":
        if isinstance(data, bytes):
            if len(data) > 1024 * 1024:
                raise WorkspaceError("workspace descriptor exceeds the 1 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise WorkspaceError("workspace descriptor must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 1024 * 1024:
                raise WorkspaceError("workspace descriptor exceeds the 1 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source,
                object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
            canonical = _canonical(document)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise WorkspaceError("invalid workspace descriptor JSON") from exc
        if source.encode("utf-8") not in {canonical, canonical + b"\n"}:
            raise WorkspaceError("workspace descriptor JSON is not canonical")
        return cls.from_document(document)


def _copy_regular_file(
    source: Path,
    destination: Path,
    expected_size: int,
    expected_digest: str,
    expected_stat: os.stat_result,
    mode: int,
) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        source_fd = os.open(source, flags)
    except OSError as exc:
        raise WorkspaceError(f"cannot safely open source file: {source.name}") from exc
    destination_fd = -1
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode) or not _same_object(expected_stat, before):
            raise WorkspaceError(f"source file changed before copy: {source.name}")
        create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            create_flags |= os.O_BINARY
        if hasattr(os, "O_NOFOLLOW"):
            create_flags |= os.O_NOFOLLOW
        destination_fd = os.open(destination, create_flags, 0o600)
        hasher = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > expected_size:
                raise WorkspaceError(f"source file grew during copy: {source.name}")
            hasher.update(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(destination_fd, view)
                if written <= 0:
                    raise WorkspaceError(f"short write while copying: {destination.name}")
                view = view[written:]
        after = os.fstat(source_fd)
        if not _same_object(before, after) or total != expected_size:
            raise WorkspaceError(f"source file changed during copy: {source.name}")
        if hasher.hexdigest() != expected_digest:
            raise WorkspaceError(f"source file content digest changed: {source.name}")
        os.fsync(destination_fd)
    finally:
        if destination_fd >= 0:
            os.close(destination_fd)
        os.close(source_fd)
    try:
        os.chmod(destination, mode)
    except OSError as exc:
        raise WorkspaceError(f"cannot preserve file mode: {destination.name}") from exc


def create_isolated_workspace(
    source_root: str | os.PathLike[str],
    snapshot: ProjectSnapshot,
    workspace_parent: str | os.PathLike[str],
    target: MigrationIdentity,
) -> WorkspaceDescriptor:
    """Materialize one independent target workspace from a verified source snapshot.

    The workspace parent must already exist and be trusted. Symlinks are rejected
    because this portable copier intentionally does not reproduce link traversal
    semantics. The operation creates a unique workspace directory and removes it
    on any failure. It never executes code or mutates the source project.
    """
    if not isinstance(snapshot, ProjectSnapshot):
        raise TypeError("snapshot must be a ProjectSnapshot")
    if not isinstance(target, MigrationIdentity):
        raise TypeError("target must be a MigrationIdentity")
    if any(item.kind == "symlink" for item in snapshot.entries):
        raise WorkspaceError("snapshots containing symbolic links cannot be materialized")
    try:
        source = Path(source_root).absolute()
        parent = Path(workspace_parent).absolute()
        source_stat = source.lstat()
        parent_stat = parent.lstat()
    except (OSError, TypeError, ValueError) as exc:
        raise WorkspaceError("source root and workspace parent must exist") from exc
    if not stat.S_ISDIR(source_stat.st_mode) or stat.S_ISLNK(source_stat.st_mode):
        raise WorkspaceError("source root must be a real directory, not a symlink")
    if not stat.S_ISDIR(parent_stat.st_mode) or stat.S_ISLNK(parent_stat.st_mode):
        raise WorkspaceError("workspace parent must be a real directory, not a symlink")
    source_resolved = source.resolve(strict=True)
    parent_resolved = parent.resolve(strict=True)
    if parent_resolved == source_resolved or parent_resolved.is_relative_to(source_resolved):
        raise WorkspaceError("workspace parent must be outside the source project")
    initial = verify_project_snapshot(source, snapshot)
    if not initial.matches:
        raise WorkspaceError("source project does not match the supplied snapshot")
    workspace_dir = Path(tempfile.mkdtemp(prefix=".qyrenith-workspace-", dir=parent_resolved))
    project_dir = workspace_dir / "project"
    try:
        project_dir.mkdir(mode=0o755)
        directories = [item for item in snapshot.entries if item.kind == "directory"]
        for entry in sorted(directories, key=lambda item: (item.path.count("/"), item.path)):
            target_dir = project_dir.joinpath(*entry.path.split("/"))
            target_dir.mkdir()
        for entry in snapshot.entries:
            if entry.kind != "file":
                continue
            source_file = source.joinpath(*entry.path.split("/"))
            destination_file = project_dir.joinpath(*entry.path.split("/"))
            try:
                source_stat_for_file = source_file.lstat()
            except OSError as exc:
                raise WorkspaceError(f"source file disappeared before copy: {entry.path}") from exc
            if not stat.S_ISREG(source_stat_for_file.st_mode) or stat.S_ISLNK(source_stat_for_file.st_mode):
                raise WorkspaceError(f"source entry is no longer a regular file: {entry.path}")
            _copy_regular_file(
                source_file, destination_file, entry.size, entry.content_digest,
                source_stat_for_file, entry.mode,
            )
        for entry in sorted(directories, key=lambda item: (-item.path.count("/"), item.path)):
            target_dir = project_dir.joinpath(*entry.path.split("/"))
            os.chmod(target_dir, entry.mode)
        copied = capture_project_snapshot(
            project_dir, excluded_paths=snapshot.excluded_paths, limits=snapshot.limits
        )
        if copied.snapshot_digest != snapshot.snapshot_digest:
            raise WorkspaceError("materialized workspace does not match the source snapshot")
        final_source = verify_project_snapshot(source, snapshot)
        if not final_source.matches:
            raise WorkspaceError("source project changed while the workspace was being materialized")
        file_count = sum(item.kind == "file" for item in snapshot.entries)
        total_bytes = sum(item.size for item in snapshot.entries if item.kind == "file")
        descriptor = WorkspaceDescriptor(
            workspace_id=workspace_dir.name.removeprefix(".qyrenith-workspace-"),
            workspace_path=str(workspace_dir.resolve()),
            project_path=str(project_dir.resolve()),
            target=target,
            source_snapshot_digest=snapshot.snapshot_digest,
            file_count=file_count,
            total_bytes=total_bytes,
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        metadata = workspace_dir / "workspace.json"
        descriptor_bytes = _canonical(descriptor.to_document()) + b"\n"
        with metadata.open("xb") as stream:
            stream.write(descriptor_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        return descriptor
    except Exception as exc:
        shutil.rmtree(workspace_dir, ignore_errors=True)
        if isinstance(exc, WorkspaceError):
            raise
        if isinstance(exc, (OSError, ValueError, TypeError, SnapshotError)):
            raise WorkspaceError(f"workspace materialization failed: {exc}") from exc
        raise


def verify_workspace_baseline(
    descriptor: WorkspaceDescriptor,
    snapshot: ProjectSnapshot,
) -> SnapshotVerification:
    """Verify that a workspace still matches the source snapshot baseline."""
    if not isinstance(descriptor, WorkspaceDescriptor):
        raise TypeError("descriptor must be a WorkspaceDescriptor")
    if not isinstance(snapshot, ProjectSnapshot):
        raise TypeError("snapshot must be a ProjectSnapshot")
    if descriptor.source_snapshot_digest != snapshot.snapshot_digest:
        raise WorkspaceError("workspace descriptor belongs to a different source snapshot")
    return verify_project_snapshot(descriptor.project_path, snapshot)


def serialize_workspace_descriptor(descriptor: WorkspaceDescriptor) -> bytes:
    if not isinstance(descriptor, WorkspaceDescriptor):
        raise TypeError("descriptor must be a WorkspaceDescriptor")
    return descriptor.to_json_bytes()


def deserialize_workspace_descriptor(data: bytes | str) -> WorkspaceDescriptor:
    return WorkspaceDescriptor.from_json_bytes(data)


__all__ = [
    "WorkspaceDescriptor", "WorkspaceError", "create_isolated_workspace",
    "verify_workspace_baseline", "serialize_workspace_descriptor",
    "deserialize_workspace_descriptor",
]

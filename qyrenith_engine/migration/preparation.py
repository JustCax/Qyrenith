"""Plan-bound preparation of isolated workspaces for multi-target migrations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .knowledge import KnowledgeCatalog, strict_object_pairs
from .model import MigrationIdentity
from .planner import MultiTargetPlan
from .snapshot import ProjectSnapshot, verify_project_snapshot
from .workspace import (
    WorkspaceDescriptor,
    WorkspaceError,
    _remove_failed_workspace,
    create_isolated_workspaces,
    verify_workspace_baseline,
)


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _timestamp(value: datetime | None) -> str:
    instant = datetime.now(timezone.utc) if value is None else value
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise WorkspaceError("created_at must be a timezone-aware datetime")
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise WorkspaceError("created_at must be a bounded UTC timestamp")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkspaceError("created_at must be a valid UTC timestamp") from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise WorkspaceError("created_at must include a UTC offset")
    canonical = instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if canonical != value:
        raise WorkspaceError("created_at must use canonical UTC format")
    return instant.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class MultiTargetWorkspaceBatch:
    """Evidence descriptor binding target workspaces to one exact multi-target plan."""

    plan_digest: str
    snapshot_digest: str
    source: MigrationIdentity
    targets: tuple[MigrationIdentity, ...]
    target_plan_digests: tuple[str, ...]
    workspaces: tuple[WorkspaceDescriptor, ...]
    created_at: str
    schema: int = 1

    def __post_init__(self) -> None:
        if type(self.schema) is not int or self.schema != 1:
            raise WorkspaceError("unsupported multi-target workspace batch schema")
        for name in ("plan_digest", "snapshot_digest"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SHA256.fullmatch(value):
                raise WorkspaceError(f"{name} must be a lowercase SHA-256 digest")
        if not isinstance(self.source, MigrationIdentity):
            raise WorkspaceError("source must be a MigrationIdentity")
        if not isinstance(self.targets, (tuple, list)):
            raise WorkspaceError("targets must be a sequence")
        if not isinstance(self.target_plan_digests, (tuple, list)):
            raise WorkspaceError("target_plan_digests must be a sequence")
        if not isinstance(self.workspaces, (tuple, list)):
            raise WorkspaceError("workspaces must be a sequence")
        targets = tuple(self.targets)
        plan_digests = tuple(self.target_plan_digests)
        descriptors = tuple(self.workspaces)
        if not 1 <= len(plan_digests) <= 64 or len(plan_digests) != len(descriptors) or len(targets) != len(descriptors):
            raise WorkspaceError("batch must bind 1 to 64 matching targets, plans, and workspaces")
        if any(not isinstance(item, MigrationIdentity) for item in targets):
            raise WorkspaceError("targets must contain MigrationIdentity values")
        if any(not isinstance(item, str) or not _SHA256.fullmatch(item) for item in plan_digests):
            raise WorkspaceError("every target plan digest must be a lowercase SHA-256 digest")
        if len(plan_digests) != len(set(plan_digests)):
            raise WorkspaceError("target plan digests must be unique")
        if any(not isinstance(item, WorkspaceDescriptor) for item in descriptors):
            raise WorkspaceError("workspaces must contain WorkspaceDescriptor values")
        if any(item.source_snapshot_digest != self.snapshot_digest for item in descriptors):
            raise WorkspaceError("every workspace must bind the batch source snapshot")
        target_keys = tuple(item.stable_key for item in targets)
        workspace_target_keys = tuple(item.target.stable_key for item in descriptors)
        if len(target_keys) != len(set(target_keys)):
            raise WorkspaceError("target identities must be unique")
        if target_keys != workspace_target_keys:
            raise WorkspaceError("workspace targets must match the ordered target-plan bindings")
        workspace_paths = tuple(item.workspace_path for item in descriptors)
        if len(workspace_paths) != len(set(workspace_paths)):
            raise WorkspaceError("workspace paths must be unique")
        parents = {str(Path(item.workspace_path).parent) for item in descriptors}
        if len(parents) != 1:
            raise WorkspaceError("all target workspaces must share one workspace parent")
        _parse_timestamp(self.created_at)
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "target_plan_digests", plan_digests)
        object.__setattr__(self, "workspaces", descriptors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "plan_digest": self.plan_digest,
            "snapshot_digest": self.snapshot_digest,
            "source": self.source.to_dict(),
            "targets": [item.to_dict() for item in self.targets],
            "target_plan_digests": list(self.target_plan_digests),
            "workspaces": [item.to_document() for item in self.workspaces],
            "created_at": self.created_at,
        }

    def validate_for_plan(
        self,
        plan: MultiTargetPlan,
        snapshot: ProjectSnapshot,
        knowledge: KnowledgeCatalog,
        *,
        now: datetime | None = None,
    ) -> None:
        """Reject stale plan, snapshot, catalog, trust, or transition evidence."""
        if not isinstance(plan, MultiTargetPlan):
            raise TypeError("plan must be a MultiTargetPlan")
        if not isinstance(snapshot, ProjectSnapshot):
            raise TypeError("snapshot must be a ProjectSnapshot")
        if not isinstance(knowledge, KnowledgeCatalog):
            raise TypeError("knowledge must be a KnowledgeCatalog")
        if not plan.plannable:
            raise WorkspaceError("workspace batch validation requires a PLANNED multi-target plan")
        instant = datetime.now(timezone.utc) if now is None else now
        if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
            raise WorkspaceError("validation time must be timezone-aware")
        instant = instant.astimezone(timezone.utc)
        if instant < _parse_timestamp(self.created_at):
            raise WorkspaceError("validation time cannot precede workspace batch preparation")
        ordered_plans = tuple(sorted(plan.targets, key=lambda item: item.target.stable_key))
        if (
            plan.plan_digest != self.plan_digest
            or plan.source != self.source
            or snapshot.snapshot_digest != self.snapshot_digest
            or tuple(item.target for item in ordered_plans) != self.targets
            or tuple(item.plan_digest for item in ordered_plans) != self.target_plan_digests
        ):
            raise WorkspaceError("workspace batch does not match the exact multi-target plan and snapshot")
        if _parse_timestamp(self.created_at) < _parse_timestamp(ordered_plans[0].evaluated_at):
            raise WorkspaceError("workspace batch creation cannot precede route planning")
        expected_knowledge_digest = ordered_plans[0].knowledge_digest
        expected_trust_digest = ordered_plans[0].knowledge_trust_digest
        if any(
            item.knowledge_digest != expected_knowledge_digest
            or item.knowledge_trust_digest != expected_trust_digest
            for item in ordered_plans
        ):
            raise WorkspaceError("target plans do not share one knowledge/trust snapshot")
        if knowledge.content_digest != expected_knowledge_digest:
            raise WorkspaceError("knowledge catalog changed after multi-target planning")
        if not knowledge.is_trusted_at(instant):
            raise WorkspaceError("knowledge trust policy is not current for workspace preparation")
        if knowledge.trust_digest_at(instant) != expected_trust_digest:
            raise WorkspaceError("knowledge trust decision changed after multi-target planning")
        if any(
            not knowledge.validates_transition(transition, instant)
            for route in ordered_plans for transition in route.transitions
        ):
            raise WorkspaceError("knowledge claims are not usable for workspace preparation")

    @property
    def batch_digest(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.to_dict())).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self.to_dict(), "batch_digest": self.batch_digest}

    def to_json_bytes(self) -> bytes:
        encoded = _canonical_bytes(self.to_document()) + b"\n"
        if len(encoded) > 4 * 1024 * 1024:
            raise WorkspaceError("multi-target workspace batch exceeds the 4 MiB export limit")
        return encoded

    @classmethod
    def from_document(cls, document: object) -> "MultiTargetWorkspaceBatch":
        expected = {
            "schema", "plan_digest", "snapshot_digest", "source",
            "targets", "target_plan_digests", "workspaces", "created_at", "batch_digest",
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise WorkspaceError("multi-target workspace batch has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise WorkspaceError("unsupported multi-target workspace batch schema")
        payload = {key: value for key, value in document.items() if key != "batch_digest"}
        if not isinstance(document["batch_digest"], str):
            raise WorkspaceError("batch_digest must be a SHA-256 digest")
        actual_digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if actual_digest != document["batch_digest"]:
            raise WorkspaceError("multi-target workspace batch digest mismatch")
        if not isinstance(document["source"], dict):
            raise WorkspaceError("batch source identity must be an object")
        identity_fields = set(MigrationIdentity.__dataclass_fields__)
        if set(document["source"]) != identity_fields:
            raise WorkspaceError("batch source identity has missing or unexpected fields")
        if not isinstance(document["targets"], list):
            raise WorkspaceError("targets must be an array")
        if not isinstance(document["target_plan_digests"], list):
            raise WorkspaceError("target_plan_digests must be an array")
        if not isinstance(document["workspaces"], list):
            raise WorkspaceError("workspaces must be an array")
        try:
            batch = cls(
                plan_digest=document["plan_digest"],
                snapshot_digest=document["snapshot_digest"],
                source=MigrationIdentity(**document["source"]),
                targets=tuple(MigrationIdentity(**item) for item in document["targets"]),
                target_plan_digests=tuple(document["target_plan_digests"]),
                workspaces=tuple(
                    WorkspaceDescriptor.from_document(item) for item in document["workspaces"]
                ),
                created_at=document["created_at"],
            )
        except (TypeError, KeyError, ValueError) as exc:
            if isinstance(exc, WorkspaceError):
                raise
            raise WorkspaceError("multi-target workspace batch contains invalid fields") from exc
        if batch.to_document() != document:
            raise WorkspaceError("multi-target workspace batch is not canonical")
        return batch

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "MultiTargetWorkspaceBatch":
        if isinstance(data, bytes):
            if len(data) > 4 * 1024 * 1024:
                raise WorkspaceError("multi-target workspace batch exceeds the 4 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise WorkspaceError("multi-target workspace batch must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 4 * 1024 * 1024:
                raise WorkspaceError("multi-target workspace batch exceeds the 4 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source,
                object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"invalid JSON constant: {value}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise WorkspaceError("invalid multi-target workspace batch JSON") from exc
        canonical = _canonical_bytes(document)
        if source.encode("utf-8") not in {canonical, canonical + b"\n"}:
            raise WorkspaceError("multi-target workspace batch JSON is not canonical")
        return cls.from_document(document)


def prepare_multi_target_workspaces(
    source_root: str | os.PathLike[str],
    snapshot: ProjectSnapshot,
    workspace_parent: str | os.PathLike[str],
    plan: MultiTargetPlan,
    knowledge: KnowledgeCatalog,
    *,
    now: datetime | None = None,
) -> MultiTargetWorkspaceBatch:
    """Prepare independent target copies for one fully PLANNED multi-target route set.

    This prepares workspaces only. It does not execute workers, authorize changes,
    or provide an operating-system sandbox.
    """
    if not isinstance(snapshot, ProjectSnapshot):
        raise TypeError("snapshot must be a ProjectSnapshot")
    if not isinstance(plan, MultiTargetPlan):
        raise TypeError("plan must be a MultiTargetPlan")
    if not isinstance(knowledge, KnowledgeCatalog):
        raise TypeError("knowledge must be a KnowledgeCatalog")
    if not plan.plannable:
        raise WorkspaceError(
            f"multi-target workspace preparation requires PLANNED routes; got {plan.status}"
        )
    created_at = _timestamp(now)
    created_instant = _parse_timestamp(created_at)
    plan_instant = _parse_timestamp(plan.targets[0].evaluated_at)
    if created_instant < plan_instant:
        raise WorkspaceError("workspace preparation time cannot precede route planning")
    ordered_plans = tuple(sorted(plan.targets, key=lambda item: item.target.stable_key))
    expected_knowledge_digest = ordered_plans[0].knowledge_digest
    expected_trust_digest = ordered_plans[0].knowledge_trust_digest
    if any(
        item.knowledge_digest != expected_knowledge_digest
        or item.knowledge_trust_digest != expected_trust_digest
        for item in ordered_plans
    ):
        raise WorkspaceError("target plans do not share one knowledge/trust snapshot")
    if knowledge.content_digest != expected_knowledge_digest:
        raise WorkspaceError("knowledge catalog changed after multi-target planning")
    if not knowledge.is_trusted_at(created_instant):
        raise WorkspaceError("knowledge trust policy is not current for workspace preparation")
    if knowledge.trust_digest_at(created_instant) != expected_trust_digest:
        raise WorkspaceError("knowledge trust decision changed after multi-target planning")
    if any(
        not knowledge.validates_transition(transition, created_instant)
        for route in ordered_plans for transition in route.transitions
    ):
        raise WorkspaceError("knowledge claims are not usable for workspace preparation")

    try:
        source_before = verify_project_snapshot(source_root, snapshot)
    except Exception as exc:
        raise WorkspaceError(f"source project does not match the requested snapshot: {exc}") from exc
    if not source_before.matches:
        raise WorkspaceError("source project changed after the multi-target snapshot was captured")

    descriptors = create_isolated_workspaces(
        source_root,
        snapshot,
        workspace_parent,
        tuple(item.target for item in ordered_plans),
    )
    try:
        if len(descriptors) != len(ordered_plans):
            raise WorkspaceError("workspace creation returned an incomplete target set")
        for route, descriptor in zip(ordered_plans, descriptors):
            if descriptor.target != route.target:
                raise WorkspaceError("workspace target order does not match the multi-target plan")
            verification = verify_workspace_baseline(descriptor, snapshot)
            if not verification.matches:
                raise WorkspaceError(
                    f"target workspace baseline changed: {', '.join(verification.changed_paths[:20])}"
                )
        source_after = verify_project_snapshot(source_root, snapshot)
        if not source_after.matches:
            raise WorkspaceError("source project changed during multi-target workspace preparation")
        batch = MultiTargetWorkspaceBatch(
            plan_digest=plan.plan_digest,
            snapshot_digest=snapshot.snapshot_digest,
            source=plan.source,
            targets=tuple(item.target for item in ordered_plans),
            target_plan_digests=tuple(item.plan_digest for item in ordered_plans),
            workspaces=descriptors,
            created_at=created_at,
        )
        batch.validate_for_plan(plan, snapshot, knowledge, now=created_instant)
        return batch
    except BaseException as exc:
        cleanup_errors: list[str] = []
        for descriptor in descriptors:
            try:
                _remove_failed_workspace(Path(descriptor.workspace_path))
            except OSError as cleanup_error:
                cleanup_errors.append(str(cleanup_error))
        if cleanup_errors:
            raise WorkspaceError(
                "multi-target preparation failed and workspace cleanup was incomplete: "
                + "; ".join(cleanup_errors[:5])
            ) from exc
        raise


__all__ = [
    "MultiTargetWorkspaceBatch",
    "prepare_multi_target_workspaces",
]

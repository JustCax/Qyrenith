"""Typed, domain-neutral migration identities and transitions.

This module defines data only. It performs no discovery, execution, network access,
filesystem mutation, or migration verification.
"""
from dataclasses import dataclass
from enum import Enum
import json


class TransitionKind(str, Enum):
    VERSION_UPGRADE = "VERSION_UPGRADE"
    LOADER_CONVERSION = "LOADER_CONVERSION"
    FRAMEWORK_CHANGE = "FRAMEWORK_CHANGE"
    PLATFORM_MIGRATION = "PLATFORM_MIGRATION"
    TOOLCHAIN_CHANGE = "TOOLCHAIN_CHANGE"
    DEPENDENCY_MIGRATION = "DEPENDENCY_MIGRATION"
    PROJECT_PROFILE_CHANGE = "PROJECT_PROFILE_CHANGE"


@dataclass(frozen=True, slots=True)
class MigrationIdentity:
    """Exact identity of one project state across independent dimensions."""

    domain: str
    product: str
    product_version: str | None = None
    platform: str | None = None
    loader: str | None = None
    loader_version: str | None = None
    framework: str | None = None
    framework_version: str | None = None
    language: str | None = None
    toolchain: str | None = None
    dependency_fingerprint: str | None = None
    profile: str | None = None

    def __post_init__(self) -> None:
        for name in ("domain", "product"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 1024:
                raise ValueError(f"{name} must be a non-empty string of at most 1024 characters")
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value.strip() or len(value) > 1024
            ):
                raise ValueError(f"{name} must be None or a non-empty string")

    def to_dict(self) -> dict[str, str | None]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @property
    def stable_key(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def validate_transition_scope(
    source: MigrationIdentity, target: MigrationIdentity, kind: TransitionKind
) -> None:
    """Validate that one atomic transition changes only its declared dimensions."""
    if not isinstance(source, MigrationIdentity) or not isinstance(target, MigrationIdentity):
        raise ValueError("transition scope endpoints must be MigrationIdentity values")
    if not isinstance(kind, TransitionKind):
        raise ValueError("transition kind must be a TransitionKind")
    changed = {
        name for name in source.__dataclass_fields__
        if getattr(source, name) != getattr(target, name)
    }
    allowed = {
        TransitionKind.VERSION_UPGRADE: {"product_version"},
        TransitionKind.LOADER_CONVERSION: {"loader", "loader_version"},
        TransitionKind.FRAMEWORK_CHANGE: {"framework", "framework_version"},
        TransitionKind.PLATFORM_MIGRATION: {"domain", "product", "platform"},
        TransitionKind.TOOLCHAIN_CHANGE: {"language", "toolchain"},
        TransitionKind.DEPENDENCY_MIGRATION: {"dependency_fingerprint"},
        TransitionKind.PROJECT_PROFILE_CHANGE: {"profile"},
    }[kind]
    if not changed:
        raise ValueError("a transition must change the migration identity")
    unexpected = changed - allowed
    if unexpected:
        raise ValueError(
            f"{kind.value} cannot change dimensions: {', '.join(sorted(unexpected))}"
        )


@dataclass(frozen=True, slots=True)
class MigrationTransition:
    """A proposed directed edge; declarations alone do not make it executable."""

    transition_id: str
    source: MigrationIdentity
    target: MigrationIdentity
    kind: TransitionKind
    knowledge_claim_ids: tuple[str, ...]
    worker_id: str | None = None
    worker_version: str | None = None
    required_capabilities: tuple[str, ...] = ()
    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TransitionKind):
            raise ValueError("kind must be a TransitionKind")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if (
            not isinstance(self.transition_id, str)
            or not self.transition_id.strip()
            or len(self.transition_id) > 256
        ):
            raise ValueError("transition_id must be a non-empty string of at most 256 characters")
        if not isinstance(self.source, MigrationIdentity) or not isinstance(self.target, MigrationIdentity):
            raise ValueError("source and target must be MigrationIdentity values")
        validate_transition_scope(self.source, self.target, self.kind)
        if not isinstance(self.knowledge_claim_ids, (tuple, list)) or not self.knowledge_claim_ids:
            raise ValueError("a transition must reference a non-empty sequence of knowledge claims")
        if any(
            not isinstance(item, str) or not item.strip() or len(item) > 256
            for item in self.knowledge_claim_ids
        ):
            raise ValueError("knowledge claim identifiers must be non-empty strings of at most 256 characters")
        if len(self.knowledge_claim_ids) != len(set(self.knowledge_claim_ids)):
            raise ValueError("knowledge claim identifiers must be unique")
        object.__setattr__(self, "knowledge_claim_ids", tuple(sorted(self.knowledge_claim_ids)))
        if self.worker_id is not None and (
            not isinstance(self.worker_id, str) or not self.worker_id.strip()
            or len(self.worker_id) > 256
        ):
            raise ValueError("worker_id must be None or a non-empty string of at most 256 characters")
        if self.worker_id is None and self.worker_version is not None:
            raise ValueError("worker_version cannot be set without worker_id")
        if self.worker_id is not None and (
            not isinstance(self.worker_version, str) or not self.worker_version.strip()
            or len(self.worker_version) > 128
        ):
            raise ValueError("worker_version must be pinned when worker_id is set")
        if not isinstance(self.required_capabilities, (tuple, list)) or any(
            not isinstance(item, str) or not item.strip() or len(item) > 256
            for item in self.required_capabilities
        ):
            raise ValueError("required capabilities must be non-empty strings of at most 256 characters")
        if len(self.required_capabilities) != len(set(self.required_capabilities)):
            raise ValueError("required capabilities must be unique")
        object.__setattr__(self, "required_capabilities", tuple(sorted(self.required_capabilities)))

    def to_dict(self) -> dict[str, object]:
        """Return the complete versioned transition contract."""
        return {
            "schema": 1,
            "transition_id": self.transition_id,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "kind": self.kind.value,
            "knowledge_claim_ids": list(self.knowledge_claim_ids),
            "worker_id": self.worker_id,
            "worker_version": self.worker_version,
            "required_capabilities": list(self.required_capabilities),
            "enabled": self.enabled,
        }

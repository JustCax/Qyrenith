"""Propose-only, evidence-linked repair plans."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Sequence

from .diagnosis import FailureHypothesis
from .events import ExecutionEvent, _canonical, _utc

_MAX_PATHS = 256
_MAX_COMMANDS = 32
_MAX_ARGS = 64
_MAX_TEXT = 2048
_PERMISSIONS = {
    "READ_PROJECT", "WRITE_PROJECT", "EXECUTE_PROCESS", "NETWORK",
    "INSTALL_DEPENDENCIES", "GIT_WRITE", "PUBLISH_ARTIFACT",
}


def _bounded_text(value: object, field: str, limit: int = _MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError(f"{field} must be non-empty bounded text")
    return value


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
        raise ValueError("affected paths must be non-empty bounded project-relative paths")
    if "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ValueError("affected paths must use project-relative POSIX path syntax")
    if any(char in value for char in "*?[]"):
        raise ValueError("affected paths must not contain wildcard characters")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("affected paths must not be absolute or traverse parent directories")
    normalized = path.as_posix()
    if normalized != value:
        raise ValueError("affected path is not canonical")
    return normalized


@dataclass(frozen=True)
class RepairPlan:
    plan_id: str
    event_id: str
    hypothesis_id: str
    failure_category: str
    affected_paths: tuple[str, ...]
    intended_change: str
    expected_invariants: tuple[str, ...]
    risk: str
    required_permissions: tuple[str, ...]
    validation_commands: tuple[tuple[str, ...], ...]
    rollback_strategy: str
    created_at: str
    execution_mode: str = "PROPOSE_ONLY"
    human_review_required: bool = True
    schema: int = 1

    def __post_init__(self) -> None:
        if type(self.schema) is not int or self.schema != 1:
            raise ValueError("unsupported repair plan schema")
        for field in ("plan_id", "hypothesis_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
                raise ValueError(f"{field} must be a UUID hex value")
        if not isinstance(self.event_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.event_id):
            raise ValueError("event_id must be a UUID hex value")
        for field in ("failure_category", "intended_change", "rollback_strategy"):
            _bounded_text(getattr(self, field), field)
        if not isinstance(self.affected_paths, tuple) or not 1 <= len(self.affected_paths) <= _MAX_PATHS:
            raise ValueError("affected_paths must contain between 1 and 256 paths")
        normalized_paths = tuple(_safe_path(item) for item in self.affected_paths)
        if normalized_paths != tuple(sorted(set(normalized_paths))):
            raise ValueError("affected_paths must be unique and canonically sorted")
        object.__setattr__(self, "affected_paths", normalized_paths)
        if not isinstance(self.expected_invariants, tuple) or not 1 <= len(self.expected_invariants) <= 50:
            raise ValueError("expected_invariants must contain between 1 and 50 statements")
        invariants = tuple(_bounded_text(item, "expected invariant", 512) for item in self.expected_invariants)
        if invariants != tuple(sorted(set(invariants))):
            raise ValueError("expected_invariants must be unique and canonically sorted")
        object.__setattr__(self, "expected_invariants", invariants)
        if self.risk not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("risk must be LOW, MEDIUM, or HIGH")
        if not isinstance(self.required_permissions, tuple) or not self.required_permissions:
            raise ValueError("required_permissions must be a non-empty tuple")
        if any(item not in _PERMISSIONS for item in self.required_permissions):
            raise ValueError("required_permissions contains an unknown permission")
        if self.required_permissions != tuple(sorted(set(self.required_permissions))):
            raise ValueError("required_permissions must be unique and canonically sorted")
        if not isinstance(self.validation_commands, tuple) or not 1 <= len(self.validation_commands) <= _MAX_COMMANDS:
            raise ValueError("validation_commands must contain between 1 and 32 commands")
        commands = []
        for command in self.validation_commands:
            if not isinstance(command, tuple) or not 1 <= len(command) <= _MAX_ARGS:
                raise ValueError("each validation command must contain between 1 and 64 arguments")
            if any(
                not isinstance(argument, str) or not argument or len(argument) > 16_384
                or "\x00" in argument for argument in command
            ):
                raise ValueError("validation command arguments must be non-empty bounded strings")
            commands.append(command)
        if len(set(commands)) != len(commands):
            raise ValueError("validation_commands must be unique")
        object.__setattr__(self, "validation_commands", tuple(commands))
        parsed_created_at = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        if _utc(parsed_created_at, "created_at") != self.created_at:
            raise ValueError("created_at must use canonical UTC milliseconds")
        if self.execution_mode != "PROPOSE_ONLY":
            raise ValueError("repair plans are propose-only and cannot request execution mode")
        if self.human_review_required is not True:
            raise ValueError("repair plans always require human review")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "plan_id": self.plan_id,
            "event_id": self.event_id,
            "hypothesis_id": self.hypothesis_id,
            "failure_category": self.failure_category,
            "affected_paths": list(self.affected_paths),
            "intended_change": self.intended_change,
            "expected_invariants": list(self.expected_invariants),
            "risk": self.risk,
            "required_permissions": list(self.required_permissions),
            "validation_commands": [list(item) for item in self.validation_commands],
            "rollback_strategy": self.rollback_strategy,
            "created_at": self.created_at,
            "execution_mode": self.execution_mode,
            "human_review_required": self.human_review_required,
        }

    @property
    def plan_digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self.to_dict(), "plan_digest": self.plan_digest}

    def to_json_bytes(self) -> bytes:
        return _canonical(self.to_document()) + b"\n"


def create_repair_plan(
    event: ExecutionEvent,
    hypothesis: FailureHypothesis,
    *,
    affected_paths: Sequence[str],
    intended_change: str,
    expected_invariants: Sequence[str],
    risk: str,
    required_permissions: Sequence[str] = ("READ_PROJECT", "WRITE_PROJECT", "EXECUTE_PROCESS"),
    validation_commands: Sequence[Sequence[str]],
    rollback_strategy: str,
    created_at: datetime | None = None,
) -> RepairPlan:
    """Create a reviewable proposal; this function never edits or executes project files."""
    if not isinstance(event, ExecutionEvent):
        raise TypeError("event must be an ExecutionEvent")
    if not isinstance(hypothesis, FailureHypothesis):
        raise TypeError("hypothesis must be a FailureHypothesis")
    if hypothesis.event_id != event.event_id:
        raise ValueError("failure hypothesis belongs to a different event")
    if event.execution_status == "PASS":
        raise ValueError("a successful event cannot receive a repair plan")
    if not isinstance(affected_paths, (tuple, list)) or any(not isinstance(item, str) for item in affected_paths):
        raise ValueError("affected_paths must be a sequence of strings")
    if not isinstance(expected_invariants, (tuple, list)) or any(not isinstance(item, str) for item in expected_invariants):
        raise ValueError("expected_invariants must be a sequence of strings")
    if not isinstance(required_permissions, (tuple, list)) or any(not isinstance(item, str) for item in required_permissions):
        raise ValueError("required_permissions must be a sequence of strings")
    if not isinstance(validation_commands, (tuple, list)) or any(
        isinstance(item, (str, bytes)) or not isinstance(item, (tuple, list))
        for item in validation_commands
    ):
        raise ValueError("validation_commands must be a sequence of argument sequences")
    normalized_paths = tuple(sorted(affected_paths))
    normalized_invariants = tuple(sorted(expected_invariants))
    normalized_permissions = tuple(sorted(set(required_permissions)))
    normalized_commands = tuple(tuple(item) for item in validation_commands)
    instant = datetime.now(timezone.utc) if created_at is None else created_at
    created_text = _utc(instant, "created_at")
    plan_id = hashlib.sha256(_canonical({
        "event_id": event.event_id,
        "hypothesis_id": hypothesis.hypothesis_id,
        "affected_paths": list(normalized_paths),
        "intended_change": intended_change,
        "expected_invariants": list(normalized_invariants),
        "risk": risk,
        "required_permissions": list(normalized_permissions),
        "validation_commands": [list(item) for item in normalized_commands],
        "rollback_strategy": rollback_strategy,
        "created_at": created_text,
    })).hexdigest()[:32]
    return RepairPlan(
        plan_id=plan_id,
        event_id=event.event_id,
        hypothesis_id=hypothesis.hypothesis_id,
        failure_category=hypothesis.failure_category,
        affected_paths=normalized_paths,
        intended_change=intended_change,
        expected_invariants=normalized_invariants,
        risk=risk,
        required_permissions=normalized_permissions,
        validation_commands=normalized_commands,
        rollback_strategy=rollback_strategy,
        created_at=created_text,
    )


__all__ = ["RepairPlan", "create_repair_plan"]

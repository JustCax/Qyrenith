"""Normalized QDAS execution events and conservative failure classification."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
import platform
import re
import uuid
from typing import Any, Mapping, Sequence

_SCHEMA = 1
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_ARGV = 256
_MAX_ARG = 16_384
_MAX_TEXT = 4096
_MAX_OUTPUT_BYTES = 8 * 1024 * 1024
_MAX_EVENT_BYTES = 256 * 1024
_EVENT_KINDS = {
    "BUILD", "TEST", "STATIC_ANALYSIS", "RUNTIME", "VERIFICATION", "OTHER",
}
_EXECUTION_STATUSES = {"PASS", "FAIL", "BLOCKED", "ERROR"}
_FAILURE_CATEGORIES = {
    "BUILD_FAILURE", "TEST_FAILURE", "STATIC_ANALYSIS_FAILURE",
    "RUNTIME_FAILURE", "INFRASTRUCTURE_FAILURE", "TIMEOUT",
    "RESOURCE_LIMIT", "ANALYZER_FAILURE", "UNSUPPORTED_STATE",
    "UNKNOWN_FAILURE",
}
_SENSITIVE_KEY = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|ACCESS[_-]?KEY|"
    r"PRIVATE[_-]?KEY|CREDENTIAL|AUTHORIZATION|COOKIE)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]{8,}")
_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:api[_-]?token|access[_-]?token|client[_-]?secret|"
    r"refresh[_-]?token|token|secret|password|passwd|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|authorization|cookie)\b\s*[:=]\s*)"
    r"(?!Bearer\b)(['\"]?)[^\s,'\";]{6,}"
)
_SENSITIVE_ARG = re.compile(
    r"(?i)^--?(?:token|secret|password|passwd|api[-_]?key|access[-_]?key|"
    r"private[-_]?key|authorization|cookie)$"
)
_INLINE_SECRET_ARG = re.compile(
    r"(?i)^(--?(?:token|secret|password|passwd|api[-_]?key|access[-_]?key|"
    r"private[-_]?key|authorization|cookie)=).+$"
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _text(value: object, field: str, limit: int = _MAX_TEXT) -> str:
    if not isinstance(value, str) or not value or len(value) > limit or "\x00" in value:
        raise ValueError(f"{field} must be non-empty bounded text")
    return value


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _utc(value: datetime, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError(f"{field} must be a bounded ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    normalized = parsed.astimezone(timezone.utc)
    if _utc(normalized, field) != value:
        raise ValueError(f"{field} must use canonical UTC milliseconds")
    return normalized


def redact_output(value: str) -> str:
    """Redact common secret forms before any event digest is calculated."""
    if not isinstance(value, str):
        raise TypeError("output must be text")
    redacted = _BEARER.sub(r"\1[REDACTED]", value)
    return _ASSIGNMENT.sub(r"\1[REDACTED]", redacted)


def digest_output(value: str) -> str:
    return hashlib.sha256(redact_output(value).encode("utf-8", "replace")).hexdigest()

def redact_argv(argv: Sequence[str]) -> tuple[str, ...]:
    """Redact secret-bearing command-line values before event persistence."""
    result = []
    redact_next = False
    for value in argv:
        if not isinstance(value, str):
            raise ValueError("argv items must be strings")
        if redact_next:
            result.append("[REDACTED]")
            redact_next = False
            continue
        if _SENSITIVE_ARG.fullmatch(value):
            result.append(value)
            redact_next = True
            continue
        inline = _INLINE_SECRET_ARG.match(value)
        if inline:
            result.append(inline.group(1) + "[REDACTED]")
            continue
        result.append(redact_output(value))
    return tuple(result)


def environment_fingerprint(environment: Mapping[str, str]) -> str:
    """Fingerprint non-secret environment inputs without persisting raw values."""
    if not isinstance(environment, Mapping):
        raise ValueError("environment must be a mapping")
    safe = {}
    for key, value in environment.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("environment keys and values must be strings")
        if "\x00" in key or "\x00" in value:
            raise ValueError("environment keys and values must not contain NUL")
        if _SENSITIVE_KEY.search(key):
            continue
        safe[key] = value
    return hashlib.sha256(_canonical(safe)).hexdigest()


@dataclass(frozen=True)
class ExecutionEvent:
    event_id: str
    project_id: str
    project_revision: str
    workspace_id: str
    event_kind: str
    os_name: str
    os_version: str
    architecture: str
    runtime_name: str
    runtime_version: str
    tool_name: str
    tool_version: str
    argv: tuple[str, ...]
    working_directory: str
    environment_digest: str
    started_at: str
    finished_at: str
    duration_milliseconds: int
    exit_code: int | None
    execution_status: str
    timed_out: bool
    output_limited: bool
    output_incomplete: bool
    input_incomplete: bool
    unsupported_state: bool
    stdout_bytes: int
    stderr_bytes: int
    stdout_digest: str
    stderr_digest: str
    schema: int = _SCHEMA

    def __post_init__(self) -> None:
        if type(self.schema) is not int or self.schema != _SCHEMA:
            raise ValueError("unsupported execution event schema")
        if not isinstance(self.event_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.event_id):
            raise ValueError("event_id must be a UUID hex value")
        for field in (
            "project_id", "project_revision", "workspace_id", "os_name",
            "os_version", "architecture", "runtime_name", "runtime_version",
            "tool_name", "tool_version", "working_directory",
        ):
            _text(getattr(self, field), field)
        if self.event_kind not in _EVENT_KINDS:
            raise ValueError("unsupported event_kind")
        if self.execution_status not in _EXECUTION_STATUSES:
            raise ValueError("unsupported execution_status")
        if not isinstance(self.argv, (tuple, list)) or not 1 <= len(self.argv) <= _MAX_ARGV:
            raise ValueError("argv must contain between 1 and 256 arguments")
        normalized_argv = tuple(_text(item, "argv item", _MAX_ARG) for item in self.argv)
        object.__setattr__(self, "argv", normalized_argv)
        _digest(self.environment_digest, "environment_digest")
        _digest(self.stdout_digest, "stdout_digest")
        _digest(self.stderr_digest, "stderr_digest")
        started = _parse_utc(self.started_at, "started_at")
        finished = _parse_utc(self.finished_at, "finished_at")
        if finished < started:
            raise ValueError("finished_at must not predate started_at")
        for field, maximum in (
            ("duration_milliseconds", 3_600_000),
            ("stdout_bytes", _MAX_OUTPUT_BYTES),
            ("stderr_bytes", _MAX_OUTPUT_BYTES),
        ):
            value = getattr(self, field)
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError(f"{field} must be a bounded non-negative integer")
        if self.exit_code is not None and type(self.exit_code) is not int:
            raise ValueError("exit_code must be an integer or null")
        for field in ("timed_out", "output_limited", "output_incomplete", "input_incomplete", "unsupported_state"):
            if type(getattr(self, field)) is not bool:
                raise ValueError(f"{field} must be a boolean")
        if self.execution_status == "PASS" and (
            self.exit_code != 0 or self.timed_out or self.output_limited
            or self.output_incomplete or self.input_incomplete
        ):
            raise ValueError("PASS event contradicts its exit code or execution flags")
        if self.exit_code == 0 and self.execution_status == "FAIL":
            raise ValueError("FAIL event cannot have a zero exit code")
        if any((self.timed_out, self.output_limited, self.output_incomplete, self.input_incomplete)) and self.execution_status == "PASS":
            raise ValueError("incomplete execution cannot be marked PASS")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "event_id": self.event_id,
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "workspace_id": self.workspace_id,
            "event_kind": self.event_kind,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "architecture": self.architecture,
            "runtime_name": self.runtime_name,
            "runtime_version": self.runtime_version,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "argv": list(self.argv),
            "working_directory": self.working_directory,
            "environment_digest": self.environment_digest,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_milliseconds": self.duration_milliseconds,
            "exit_code": self.exit_code,
            "execution_status": self.execution_status,
            "timed_out": self.timed_out,
            "output_limited": self.output_limited,
            "output_incomplete": self.output_incomplete,
            "input_incomplete": self.input_incomplete,
            "unsupported_state": self.unsupported_state,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
        }

    @property
    def event_digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def to_json_bytes(self) -> bytes:
        encoded = _canonical(self.to_dict()) + b"\n"
        if len(encoded) > _MAX_EVENT_BYTES:
            raise ValueError("execution event exceeds the 256 KiB limit")
        return encoded

    @classmethod
    def from_dict(cls, value: object) -> "ExecutionEvent":
        fields = {
            "schema", "event_id", "project_id", "project_revision", "workspace_id",
            "event_kind", "os_name", "os_version", "architecture", "runtime_name",
            "runtime_version", "tool_name", "tool_version", "argv",
            "working_directory", "environment_digest", "started_at", "finished_at",
            "duration_milliseconds", "exit_code", "execution_status", "timed_out",
            "output_limited", "output_incomplete", "input_incomplete", "unsupported_state", "stdout_bytes",
            "stderr_bytes", "stdout_digest", "stderr_digest",
        }
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("execution event has missing or unexpected fields")
        if not isinstance(value["argv"], list):
            raise ValueError("execution event argv must be an array")
        return cls(**{**value, "argv": tuple(value["argv"])})

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "ExecutionEvent":
        if isinstance(data, bytes):
            if len(data) > _MAX_EVENT_BYTES:
                raise ValueError("execution event exceeds the 256 KiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("execution event must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > _MAX_EVENT_BYTES:
                raise ValueError("execution event exceeds the 256 KiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source, object_pairs_hook=_unique_pairs,
                parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid execution event JSON") from exc
        event = cls.from_dict(document)
        if source.encode("utf-8") not in {event.to_json_bytes(), event.to_json_bytes().rstrip(b"\n")}:
            raise ValueError("execution event JSON is not canonical")
        return event


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def create_execution_event(
    report: Mapping[str, Any],
    *,
    project_id: str,
    project_revision: str,
    workspace_id: str,
    event_kind: str,
    tool_name: str,
    tool_version: str,
    argv: Sequence[str],
    working_directory: str,
    environment: Mapping[str, str],
    runtime_name: str | None = None,
    runtime_version: str | None = None,
    os_name: str | None = None,
    os_version: str | None = None,
    architecture: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> ExecutionEvent:
    """Normalize one shared bounded-process report without retaining raw output."""
    if not isinstance(report, Mapping):
        raise ValueError("report must be a mapping")
    start = datetime.now(timezone.utc) if started_at is None else started_at
    finish = datetime.now(timezone.utc) if finished_at is None else finished_at
    started_text = _utc(start, "started_at")
    finished_text = _utc(finish, "finished_at")
    status = report.get("status")
    if status not in _EXECUTION_STATUSES:
        raise ValueError("execution report has an unsupported status")
    stdout = report.get("stdout", report.get("output", ""))
    stderr = report.get("stderr", "")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise ValueError("execution report streams must be text")
    exit_code = report.get("exit_code")
    for flag in ("timed_out", "output_limited", "output_truncated", "output_incomplete", "input_incomplete", "unsupported_state"):
        if flag in report and type(report[flag]) is not bool:
            raise ValueError(f"execution report {flag} must be a boolean")
    output_limited = bool(report.get("output_limited") or report.get("output_truncated"))
    output_incomplete = bool(report.get("output_incomplete"))
    input_incomplete = bool(report.get("input_incomplete"))
    unsupported_state = bool(report.get("unsupported_state"))
    timed_out = bool(report.get("timed_out"))
    if timed_out or output_limited or output_incomplete or input_incomplete:
        status = "BLOCKED"
    elif status == "PASS" and exit_code != 0:
        raise ValueError("execution report PASS must have exit_code zero")
    duration = report.get("duration_seconds", 0.0)
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 <= duration <= 3600:
        raise ValueError("execution report duration_seconds is invalid")
    stdout_bytes = report.get("stdout_bytes", len(stdout.encode("utf-8", "replace")))
    stderr_bytes = report.get("stderr_bytes", len(stderr.encode("utf-8", "replace")))
    if type(stdout_bytes) is not int or type(stderr_bytes) is not int:
        raise ValueError("execution report stream byte counts must be integers")
    if stdout_bytes > _MAX_OUTPUT_BYTES or stderr_bytes > _MAX_OUTPUT_BYTES:
        raise ValueError("execution report stream byte counts exceed the event limit")
    supplied_environment_digest = report.get("environment_digest")
    if supplied_environment_digest is None:
        environment_digest = environment_fingerprint(environment)
    else:
        environment_digest = _digest(supplied_environment_digest, "report.environment_digest")
    return ExecutionEvent(
        event_id=uuid.uuid4().hex,
        project_id=project_id,
        project_revision=project_revision,
        workspace_id=workspace_id,
        event_kind=event_kind,
        os_name=os.name if os_name is None else os_name,
        os_version=platform.version() if os_version is None else os_version,
        architecture=platform.machine() if architecture is None else architecture,
        runtime_name="CPython" if runtime_name is None else runtime_name,
        runtime_version=platform.python_version() if runtime_version is None else runtime_version,
        tool_name=tool_name,
        tool_version=tool_version,
        argv=redact_argv(argv),
        working_directory=working_directory,
        environment_digest=environment_digest,
        started_at=started_text,
        finished_at=finished_text,
        duration_milliseconds=round(float(duration) * 1000),
        exit_code=exit_code,
        execution_status=status,
        timed_out=timed_out,
        output_limited=output_limited,
        output_incomplete=output_incomplete,
        input_incomplete=input_incomplete,
        unsupported_state=unsupported_state,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        stdout_digest=digest_output(stdout),
        stderr_digest=digest_output(stderr),
    )


@dataclass(frozen=True)
class FailureClassification:
    classification_id: str
    event_id: str
    category: str
    classifier_id: str
    classifier_version: str
    rule_id: str
    rationale: str
    confidence: str
    observed_exit_code: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.classification_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.classification_id):
            raise ValueError("classification_id must be a UUID hex value")
        if not isinstance(self.event_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.event_id):
            raise ValueError("event_id must be a UUID hex value")
        if self.category not in _FAILURE_CATEGORIES:
            raise ValueError("unsupported failure category")
        _text(self.classifier_id, "classifier_id", 128)
        _text(self.classifier_version, "classifier_version", 64)
        _text(self.rule_id, "rule_id", 128)
        _text(self.rationale, "rationale", 2048)
        if self.confidence not in {"HIGH", "MEDIUM", "LOW"}:
            raise ValueError("confidence must be HIGH, MEDIUM, or LOW")
        if self.observed_exit_code is not None and type(self.observed_exit_code) is not int:
            raise ValueError("observed_exit_code must be an integer or null")

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification_id": self.classification_id,
            "event_id": self.event_id,
            "category": self.category,
            "classifier_id": self.classifier_id,
            "classifier_version": self.classifier_version,
            "rule_id": self.rule_id,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "observed_exit_code": self.observed_exit_code,
        }


def classify_failure(event: ExecutionEvent) -> FailureClassification | None:
    """Classify by explicit execution facts; never infer a root cause from exit code alone."""
    if not isinstance(event, ExecutionEvent):
        raise TypeError("event must be an ExecutionEvent")
    if event.execution_status == "PASS":
        return None
    if event.unsupported_state:
        category, rule, reason, confidence = (
            "UNSUPPORTED_STATE", "EXEC-UNSUPPORTED-001",
            "The required operation or execution capability is explicitly unsupported.", "HIGH",
        )
    elif event.timed_out:
        category, rule, reason, confidence = (
            "TIMEOUT", "EXEC-TIMEOUT-001",
            "The bounded execution deadline expired before completion.", "HIGH",
        )
    elif event.output_limited or event.output_incomplete or event.input_incomplete:
        category, rule, reason, confidence = (
            "RESOURCE_LIMIT", "EXEC-RESOURCE-001",
            "The bounded execution input/output contract was not fully satisfied.", "HIGH",
        )
    elif event.execution_status == "ERROR":
        category, rule, reason, confidence = (
            "INFRASTRUCTURE_FAILURE", "EXEC-START-001",
            "The execution layer reported that the process could not be started or supervised.", "HIGH",
        )
        if event.event_kind == "STATIC_ANALYSIS":
            category, rule = "ANALYZER_FAILURE", "ANALYZER-EXEC-001"
    elif event.execution_status == "BLOCKED":
        category, rule, reason, confidence = (
            "INFRASTRUCTURE_FAILURE", "EXEC-BLOCKED-001",
            "Execution was blocked for a reason not represented by a more specific bounded-execution or unsupported-state flag.", "MEDIUM",
        )
    elif event.event_kind == "BUILD":
        category, rule, reason, confidence = (
            "BUILD_FAILURE", "BUILD-EXIT-001",
            "The build command completed without a successful exit status.", "HIGH",
        )
    elif event.event_kind == "TEST":
        category, rule, reason, confidence = (
            "TEST_FAILURE", "TEST-EXIT-001",
            "The test command completed without a successful exit status.", "HIGH",
        )
    elif event.event_kind == "STATIC_ANALYSIS":
        category, rule, reason, confidence = (
            "STATIC_ANALYSIS_FAILURE", "ANALYSIS-EXIT-001",
            "The static-analysis command completed without a successful exit status.", "HIGH",
        )
    elif event.event_kind == "RUNTIME":
        category, rule, reason, confidence = (
            "RUNTIME_FAILURE", "RUNTIME-EXIT-001",
            "The runtime command completed without a successful exit status.", "HIGH",
        )
    else:
        category, rule, reason, confidence = (
            "UNKNOWN_FAILURE", "EXEC-UNKNOWN-001",
            "The event failed, but its declared event kind does not support a more specific classification.", "LOW",
        )
    return FailureClassification(
        classification_id=uuid.uuid4().hex,
        event_id=event.event_id,
        category=category,
        classifier_id="qyrenith-native-failure-classifier",
        classifier_version="1",
        rule_id=rule,
        rationale=reason,
        confidence=confidence,
        observed_exit_code=event.exit_code,
    )


__all__ = [
    "ExecutionEvent", "FailureClassification", "classify_failure",
    "create_execution_event", "digest_output", "environment_fingerprint",
    "redact_argv", "redact_output",
]

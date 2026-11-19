"""QDAS capture for dynamic scenario execution (bounded process audit).

Every run_scenario_with_qdas() run executes a scenario under QDAS observation
via the shared bounded process runner, records a QDAS ExecutionEvent
(event_kind=DYNAMIC_AUDIT) in the QDAS ledger, and returns the capture result
plus a scenario outcome summary. QDAS remains strictly observational: it
records events and classifies failure symptoms; it never executes repairs or
applies patches.

A scenario is accepted either as a ScenarioContract or as a dict. Every
scenario is executed through run_bounded_process before its result is recorded.
Caller-supplied pre-built reports are not accepted here; integrations that need
to ingest an already captured report must use record_execution_report directly
and preserve that report's separate provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .execution import run_bounded_process
from .qdas.collector import QdasCaptureResult, record_execution_report
from .qdas.events import environment_fingerprint
from .qdas.ledger import QdasEventLedger


class OracleType(Enum):
    EXACT = "EXACT"
    PROPERTY = "PROPERTY"
    DIFFERENTIAL = "DIFFERENTIAL"
    HEURISTIC = "HEURISTIC"


@dataclass(frozen=True)
class ScenarioContract:
    """Scenario metadata; setup/actions/observations are not yet evaluated here."""

    scenario_id: str
    name: str
    setup: Any
    inputs: Any
    actions: Any
    expected_observations: Any
    cleanup: Any
    timeout_seconds: int
    oracle: OracleType
    oracle_details: dict[str, Any] = field(default_factory=dict)


_OUTPUT_LIMIT = 16000


def _scenario_mapping(scenario: Any) -> dict[str, Any]:
    """Normalize a ScenarioContract or scenario dict into a plain mapping."""
    if isinstance(scenario, ScenarioContract):
        return {
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "setup": scenario.setup,
            "inputs": scenario.inputs,
            "actions": scenario.actions,
            "expected_observations": scenario.expected_observations,
            "cleanup": scenario.cleanup,
            "timeout_seconds": scenario.timeout_seconds,
            "oracle": scenario.oracle,
            "oracle_details": scenario.oracle_details,
        }
    if not isinstance(scenario, Mapping):
        raise TypeError("scenario must be a mapping or ScenarioContract")
    return dict(scenario)


def _coerce_oracle(value: Any) -> OracleType:
    if isinstance(value, OracleType):
        return value
    if isinstance(value, str):
        try:
            return OracleType(value)
        except ValueError as exc:
            raise ValueError(
                "oracle must be EXACT, PROPERTY, DIFFERENTIAL, or HEURISTIC"
            ) from exc
    raise ValueError(
        "oracle must be EXACT, PROPERTY, DIFFERENTIAL, or HEURISTIC"
    )


def run_scenario_with_qdas(
    scenario: Any,
    project: str | Path,
    qdas_ledger: QdasEventLedger,
    *,
    project_id: str,
    project_revision: str,
    workspace_id: str,
    tool_name: str,
    tool_version: str,
    environment: Mapping[str, str],
    seed: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> tuple[QdasCaptureResult, dict[str, Any]]:
    """Capture one bounded process run as a DYNAMIC_AUDIT event.

    This adapter does not enforce RVL isolation or host approval and does not
    evaluate behavioral oracles. Callers must not use it on an original,
    untrusted project tree; the returned behavior status remains NOT_RUN.
    """
    if not isinstance(qdas_ledger, QdasEventLedger):
        raise TypeError("qdas_ledger must be a QdasEventLedger")
    for field_name, value in (
        ("project_id", project_id),
        ("project_revision", project_revision),
        ("workspace_id", workspace_id),
        ("tool_name", tool_name),
        ("tool_version", tool_version),
    ):
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 4096
            or "\x00" in value
        ):
            raise ValueError(f"{field_name} must be non-empty bounded text")
    if seed is not None and (
        not isinstance(seed, str) or len(seed) > 4096 or "\x00" in seed
    ):
        raise ValueError("seed must be bounded text when supplied")
    environment_fingerprint(environment)
    if started_at is not None and (
        not isinstance(started_at, datetime)
        or started_at.tzinfo is None
        or started_at.utcoffset() is None
    ):
        raise ValueError("started_at must be a timezone-aware datetime")
    if finished_at is not None and (
        not isinstance(finished_at, datetime)
        or finished_at.tzinfo is None
        or finished_at.utcoffset() is None
    ):
        raise ValueError("finished_at must be a timezone-aware datetime")

    root = Path(project).expanduser().resolve(strict=True)
    started = datetime.now(timezone.utc) if started_at is None else started_at
    if finished_at is not None and finished_at < started:
        raise ValueError("finished_at must not predate started_at")

    scenario_dict = _scenario_mapping(scenario)
    scenario_id = scenario_dict.get("scenario_id")
    if (
        not isinstance(scenario_id, str)
        or not scenario_id
        or len(scenario_id) > 256
        or "\x00" in scenario_id
    ):
        raise ValueError("scenario_id must be non-empty bounded text")
    oracle = _coerce_oracle(scenario_dict.get("oracle"))

    if "timeout_seconds" not in scenario_dict:
        raise ValueError("scenario must declare timeout_seconds")
    timeout = scenario_dict["timeout_seconds"]
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ValueError("timeout_seconds must be an integer between 1 and 3600")

    argv = scenario_dict["argv"] if "argv" in scenario_dict else [tool_name]
    if (
        not isinstance(argv, (list, tuple))
        or not 1 <= len(argv) <= 256
        or any(
            not isinstance(argument, str)
            or not argument
            or len(argument) > 16_384
            or "\x00" in argument
            for argument in argv
        )
    ):
        raise ValueError(
            "scenario argv must contain 1 to 256 non-empty bounded strings"
        )

    report = run_bounded_process(
        argv,
        root,
        timeout=timeout,
        output_limit=_OUTPUT_LIMIT,
        env_overrides=dict(environment) if environment is not None else None,
    )

    capture_result = record_execution_report(
        report,
        root,
        qdas_ledger,
        project_id=project_id,
        project_revision=project_revision,
        workspace_id=workspace_id,
        event_kind="DYNAMIC_AUDIT",
        tool_name=tool_name,
        tool_version=tool_version,
        argv=argv,
        environment=dict(environment),
        started_at=started,
        finished_at=finished_at,
    )

    event = capture_result.event
    scenario_outcome = {
        "status": "NOT_RUN",
        "execution_status": event.execution_status,
        "behavior_status": "NOT_RUN",
        "behavior_verified": False,
        "environment_fingerprint": event.environment_digest,
        "seed": seed,
        "stdout_digest": event.stdout_digest,
        "stderr_digest": event.stderr_digest,
        "duration_seconds": event.duration_milliseconds / 1000.0,
        "oracle_type": oracle.value,
        "scenario_id": scenario_id,
    }
    return capture_result, scenario_outcome


__all__ = ["OracleType", "ScenarioContract", "run_scenario_with_qdas"]

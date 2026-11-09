"""QDAS capture for dynamic scenario execution (bounded process audit).

Every run_scenario_with_qdas() run executes a scenario under QDAS observation
via the shared bounded process runner, records a QDAS ExecutionEvent
(event_kind=DYNAMIC_AUDIT) in the QDAS ledger, and returns the capture result
plus a scenario outcome summary. QDAS remains strictly observational: it
records events and classifies failure symptoms; it never executes repairs or
applies patches.

A scenario is accepted either as a ScenarioContract or as a dict (the form
produced by Task 1's make_scenario()). When the dict carries a pre-built
"report" (as the Task 1 test does), that report is recorded directly; otherwise
the scenario's argv is executed through run_bounded_process.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .execution import run_bounded_process
from .qdas.collector import QdasCaptureResult, record_execution_report
from .qdas.ledger import QdasEventLedger


class OracleType(Enum):
    EXACT = "EXACT"
    PROPERTY = "PROPERTY"
    DIFFERENTIAL = "DIFFERENTIAL"
    HEURISTIC = "HEURISTIC"


@dataclass(frozen=True)
class ScenarioContract:
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


_EXECUTION_STATUSES = {"PASS", "FAIL", "BLOCKED", "ERROR"}
_DEFAULT_TIMEOUT = 120
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
        except ValueError:
            pass
    return OracleType.HEURISTIC


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
    **analysis_kwargs: Any,
) -> tuple[QdasCaptureResult, dict[str, Any]]:
    """Run one scenario under QDAS observation and record a DYNAMIC_AUDIT event.

    Returns the QDAS capture result and a scenario outcome dict.
    """
    root = Path(project).expanduser().resolve(strict=True)
    started = datetime.now(timezone.utc) if started_at is None else started_at

    scenario_dict = _scenario_mapping(scenario)
    oracle = _coerce_oracle(scenario_dict.get("oracle"))

    timeout = scenario_dict.get("timeout_seconds", _DEFAULT_TIMEOUT)
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        timeout = _DEFAULT_TIMEOUT

    argv = scenario_dict.get("argv") or [tool_name]

    report = scenario_dict.get("report")
    if not isinstance(report, Mapping):
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
        "status": event.execution_status,
        "environment_fingerprint": event.environment_digest,
        "seed": seed,
        "stdout_digest": event.stdout_digest,
        "stderr_digest": event.stderr_digest,
        "duration_seconds": event.duration_milliseconds / 1000.0,
        "oracle_type": oracle.value,
    }
    return capture_result, scenario_outcome


__all__ = ["OracleType", "ScenarioContract", "run_scenario_with_qdas"]

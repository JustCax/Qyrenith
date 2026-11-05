"""QDAS capture helpers for the shared bounded process runner and existing reports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..execution import run_bounded_process
from .diagnosis import FailureHypothesis, diagnose_failure
from .events import ExecutionEvent, FailureClassification, classify_failure, create_execution_event
from .ledger import QdasEventLedger


@dataclass(frozen=True)
class QdasCaptureResult:
    report: Mapping[str, Any]
    event: ExecutionEvent
    classification: FailureClassification | None
    hypotheses: tuple[FailureHypothesis, ...]
    ledger_record: Mapping[str, Any]


def record_execution_report(
    report: Mapping[str, Any],
    project: str | os.PathLike[str],
    ledger: QdasEventLedger,
    *,
    project_id: str,
    project_revision: str,
    workspace_id: str,
    event_kind: str,
    tool_name: str,
    tool_version: str,
    argv: Sequence[str],
    environment: Mapping[str, str],
    started_at: datetime,
    finished_at: datetime | None = None,
) -> QdasCaptureResult:
    """Ingest an already-executed bounded report without launching a second process."""
    if not isinstance(ledger, QdasEventLedger):
        raise TypeError("ledger must be a QdasEventLedger")
    root = Path(project).expanduser().resolve(strict=True)
    ended = datetime.now(timezone.utc) if finished_at is None else finished_at
    event = create_execution_event(
        report,
        project_id=project_id,
        project_revision=project_revision,
        workspace_id=workspace_id,
        event_kind=event_kind,
        tool_name=tool_name,
        tool_version=tool_version,
        argv=argv,
        working_directory=str(root),
        environment=environment,
        started_at=started_at,
        finished_at=ended,
    )
    classification = classify_failure(event)
    stdout = report.get("stdout", report.get("output", ""))
    stderr = report.get("stderr", "")
    hypotheses = diagnose_failure(event, stdout=stdout, stderr=stderr)
    record = ledger.append(event, classification, hypotheses)
    return QdasCaptureResult(
        report=dict(report),
        event=event,
        classification=classification,
        hypotheses=hypotheses,
        ledger_record=record,
    )


def capture_process_event(
    argv: Sequence[str],
    project: str | os.PathLike[str],
    ledger: QdasEventLedger,
    *,
    project_id: str,
    project_revision: str,
    workspace_id: str,
    event_kind: str,
    tool_name: str,
    tool_version: str,
    timeout: int = 120,
    output_limit: int = 16_000,
    env_overrides: Mapping[str, str] | None = None,
    inherit_environment: bool = False,
) -> QdasCaptureResult:
    """Run one explicitly supplied argv and persist a normalized QDAS event.

    This provides process bounds, not an OS sandbox. The caller remains
    responsible for deciding whether the command is trusted and authorized.
    Raw output is returned to the caller but only redacted stream digests and
    byte counts are persisted in the event ledger.
    """
    root = Path(project).expanduser().resolve(strict=True)
    started_at = datetime.now(timezone.utc)
    report = run_bounded_process(
        argv,
        root,
        timeout=timeout,
        output_limit=output_limit,
        env_overrides=dict(env_overrides) if env_overrides is not None else None,
        inherit_environment=inherit_environment,
    )
    return record_execution_report(
        report, root, ledger,
        project_id=project_id,
        project_revision=project_revision,
        workspace_id=workspace_id,
        event_kind=event_kind,
        tool_name=tool_name,
        tool_version=tool_version,
        argv=argv,
        environment=os.environ if inherit_environment else (
            env_overrides if env_overrides is not None else {}
        ),
        started_at=started_at,
    )


__all__ = [
    "QdasCaptureResult",
    "capture_process_event",
    "record_execution_report",
]

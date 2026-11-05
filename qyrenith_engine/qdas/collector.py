"""QDAS capture wrapper for the shared bounded process runner."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..execution import run_bounded_process
from .events import ExecutionEvent, FailureClassification, classify_failure, create_execution_event
from .ledger import QdasEventLedger


@dataclass(frozen=True)
class QdasCaptureResult:
    report: Mapping[str, Any]
    event: ExecutionEvent
    classification: FailureClassification | None
    ledger_record: Mapping[str, Any]


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
    if not isinstance(ledger, QdasEventLedger):
        raise TypeError("ledger must be a QdasEventLedger")
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
    finished_at = datetime.now(timezone.utc)
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
        environment={},
        started_at=started_at,
        finished_at=finished_at,
    )
    classification = classify_failure(event)
    record = ledger.append(event, classification)
    return QdasCaptureResult(
        report=dict(report),
        event=event,
        classification=classification,
        ledger_record=record,
    )


__all__ = ["QdasCaptureResult", "capture_process_event"]

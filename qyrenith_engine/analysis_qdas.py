"""QDAS capture for static and semantic analysis.

Every analyze_project() run produces a QDAS ExecutionEvent (event_kind=STATIC_ANALYSIS)
recorded in the QDAS ledger. QDAS remains strictly observational: it records events,
classifies failures (symptom-only, never root-cause), and produces unconfirmed
hypotheses. Nothing in this module executes repairs or applies patches.

The pure analysis functions in qyrenith_engine.analysis remain unchanged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .analysis import analyze_project
from .qdas.collector import QdasCaptureResult, record_execution_report
from .qdas.ledger import QdasEventLedger


def record_analysis_with_qdas(
    project: str | Path,
    qdas_ledger: QdasEventLedger,
    *,
    project_id: str,
    project_revision: str,
    workspace_id: str,
    tool_name: str,
    tool_version: str,
    environment: Mapping[str, str],
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    **analysis_kwargs: Any,
) -> tuple[QdasCaptureResult, dict[str, Any]]:
    """Run static analysis under QDAS observation and record a QDAS event.

    Returns the QDAS capture result and the analysis report dict.
    """
    root = Path(project).expanduser().resolve(strict=True)
    started = datetime.now(timezone.utc) if started_at is None else started_at

    analysis_report = analyze_project(root, **analysis_kwargs)

    _STATUS_MAP = {"PASS": "PASS", "FAIL": "FAIL", "BLOCKED": "BLOCKED", "UNKNOWN": "ERROR"}
    status = _STATUS_MAP.get(analysis_report.get("status", "UNKNOWN"), "ERROR")
    if status == "PASS":
        exit_code = 0
    elif status == "ERROR":
        exit_code = None
    else:
        exit_code = 1
    report = {
        "status": status,
        "stdout": json.dumps(analysis_report, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False),
        "stderr": "",
        "exit_code": exit_code,
        "duration_seconds": 0.0,
    }

    capture_result = record_execution_report(
        report,
        root,
        qdas_ledger,
        project_id=project_id,
        project_revision=project_revision,
        workspace_id=workspace_id,
        event_kind="STATIC_ANALYSIS",
        tool_name=tool_name,
        tool_version=tool_version,
        argv=["python", "-m", "qyrenith_analysis"],
        environment=dict(environment),
        started_at=started,
        finished_at=finished_at,
    )

    return capture_result, analysis_report


__all__ = ["record_analysis_with_qdas"]

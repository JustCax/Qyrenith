# QDAS Capture for Static and Semantic Analysis — Qyrenith 1.2.0

**Date:** 2026-11-07  
**Repository:** JustCax/Qyrenith  
**Branch:** feature/1.2.0-universal-migration-core (PR #9 draft)  
**Status:** Draft — awaiting human approval before any build work  
**Module:** Capability module 1 of 14 — Static and semantic analysis

---

## Intent and why

QDAS is stabilized and already connected to migration step execution (QDAS event digest bound into AssuranceLedger evidence_ids). The next 1.2.0 capability module is **Static and semantic analysis** (module 1 of 14). The existing qyrenith_engine/analysis.py already provides analyze_project(), compare_baselines(), and build_change_impact(), but **none of these calls QDAS**.

Goal: add a thin QDAS capture layer so every static analysis run produces a QDAS ExecutionEvent (event_kind STATIC_ANALYSIS) and records it in the QDAS ledger. QDAS remains strictly observational: it records events, classifies failures (symptom-only, never root-cause), and produces unconfirmed hypotheses. Nothing executes repairs or authorizes changes.

## Goals

1. New module qyrenith_engine/analysis_qdas.py provides record_analysis_with_qdas(report_output, project, qdas_ledger, *, project_id, project_revision, workspace_id, tool_name, tool_version, environment, ...) that:
   - Creates a QDAS ExecutionEvent via QDAS create_execution_event() (event_kind=STATIC_ANALYSIS)
   - Appends it to the QDAS ledger
   - Returns both the QDAS capture result and the analysis report dict
2. QDAS event digest (SHA-256 hex, 64 chars) is retained in the QDAS ledger record.
3. All existing analysis.py functions (analyze_project, compare_baselines, build_change_impact) remain unchanged — no regression.
4. New tests cover: QDAS event creation, ledger append, digest binding, tamper detection across QDAS ledger.
5. Standard-library-only, Python 3.11+, no new dependencies.

## Non-goals

- QDAS does not execute static analysis repairs or apply patches.
- analysis.py functions are not modified or wrapped; they remain pure Python.
- QDAS does not provide OS sandboxing or human authentication.
- No merge to main as part of this design.

## Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- QDAS event bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (...Z).
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing 1.1.0 behavior and analysis tests must not regress.

## Approaches considered

**Approach 1 — New analysis_qdas.py module with record_analysis_with_qdas().** (Selected)
Separate module imports analyze_project and QDAS create_execution_event/QdasEventLedger. Minimal change, reversible, no regression risk to existing analysis.py.

**Approach 2 — Modify analysis.py functions to call QDAS internally.**
Rejected: couples pure static analysis to QDAS, breaks testability, and modifies existing behavior.

**Approach 3 — QDAS event inside compare_baselines and build_change_impact too.**
Rejected: scope creep for this first module; only analyze_project needs QDAS capture for now.

## Decided how (as decided)

- New file: qyrenith_engine/analysis_qdas.py
- New test file: tests/test_analysis_qdas_120.py
- Export record_analysis_with_qdas from qyrenith_engine/__init__.py (optional, decided: keep internal to analysis_qdas until needed elsewhere)
- CI already compiles and runs analysis + QDAS tests (wired on the branch)

## What is left to the builder

- Write analysis_qdas.py with exact signature
- Write tests proving QDAS event creation, ledger append, digest binding, tamper detection
- Run analysis + QDAS tests (no regressions)
- Report results before any merge to main

---

## Approval requested

Please confirm this design is acceptable, or state what should change. Once approved, I will proceed to the plan (writing-plans) and then implementation on the feature branch.

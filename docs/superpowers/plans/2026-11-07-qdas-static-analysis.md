# QDAS Static Analysis Capture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add QDAS capture to the Static and semantic analysis capability module (module 1 of 14) so every `analyze_project()` run produces a QDAS `ExecutionEvent` (event_kind=`STATIC_ANALYSIS`) recorded in the QDAS ledger, with QDAS event digest retained in the QDAS ledger record. Existing `analysis.py` functions remain unchanged.

**Architecture:** New module qyrenith_engine/analysis_qdas.py imports analyze_project from qyrenith_engine.analysis and QDAS create_execution_event/QdasEventLedger/verify_qdas_ledger. New test file tests/test_analysis_qdas_120.py covers event creation, ledger append, digest binding, tamper detection.

**Tech Stack:** Python 3.11+ standard library only, unittest, existing QDAS (qyrenith_engine.qdas) and qyrenith_engine.analysis.

**Spec:** docs/superpowers/specs/2026-11-07-qdas-static-analysis-design.md (pushed to feature/1.2.0-universal-migration-core branch)

## Global Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- QDAS event bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (...Z).
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing analysis.py functions (analyze_project, compare_baselines, build_change_impact) remain unchanged — no regression.
- QDAS remains observational only; it does not execute repairs or apply patches.

## Review Focus

1. **QDAS event created with event_kind STATIC_ANALYSIS** — tested in test_analysis_qdas_120.py.
2. **QDAS event digest retained in QDAS ledger record** — tested in test_analysis_qdas_120.py.
3. **Tamper detection across QDAS ledger** — modifying QDAS ledger breaks verify_qdas_ledger; tested in test_analysis_qdas_120.py.
4. **No regression in existing analysis functions** — analyze_project, compare_baselines, build_change_impact unchanged and still pass their existing tests.
5. **QDAS event and analysis report both returned** — integration function returns both QdasCaptureResult and analysis report dict; tested in test_analysis_qdas_120.py.

---

### Task 1: Write failing test for QDAS static analysis capture

**Files:**
- Create: tests/test_analysis_qdas_120.py

**Interfaces:**
- Consumes: nothing external yet
- Produces: failing test file that imports record_analysis_with_qdas from qyrenith_engine.analysis_qdas

- [ ] **Step 1: Write failing test file**

Create tests/test_analysis_qdas_120.py with:
- test_records_qdas_event_and_analysis_report() — calls record_analysis_with_qdas(), asserts it returns a tuple (QdasCaptureResult, analysis_report), QDAS ledger has 1 record, QDAS event digest is retained.
- test_tampering_breaks_qdas_ledger() — tampers QDAS ledger line, expects QdasLedgerError.

Run: python -m unittest tests.test_analysis_qdas_120 -v
Expected: FAIL with ModuleNotFoundError: No module named 'qyrenith_engine.analysis_qdas' or ImportError

- [ ] **Step 2: Commit failing test**

Commit message: test: add QDAS static analysis capture test stub

---

### Task 2: Implement record_analysis_with_qdas in analysis_qdas.py

**Files:**
- Create: qyrenith_engine/analysis_qdas.py

**Interfaces:**
- Consumes: analyze_project from qyrenith_engine.analysis, create_execution_event/QdasEventLedger/verify_qdas_ledger from qyrenith_engine.qdas
- Produces: function record_analysis_with_qdas(project, qdas_ledger, *, project_id, project_revision, workspace_id, tool_name, tool_version, environment, started_at=None, finished_at=None, **analysis_kwargs) -> tuple[QdasCaptureResult, dict]

- [ ] **Step 1: Implement analysis_qdas.py**

Function body:
- Call analyze_project(project, **analysis_kwargs) → analysis_report
- Build report mapping for create_execution_event: status from analysis_report["status"], stdout/stderr from JSON serialization of analysis_report, exit_code = 0 if status PASS else 1, duration_seconds from report or 0.0
- Call create_execution_event(report, project_id=..., project_revision=..., workspace_id=..., event_kind="STATIC_ANALYSIS", tool_name=..., tool_version=..., argv=["python", "-m", "qyrenith_analysis"], working_directory=".", environment=..., started_at=..., finished_at=...)
- Call qdas_ledger.append(event, classification=None, hypotheses=()) → ledger record
- Return (capture_result, analysis_report) — wait, record_execution_report returns QdasCaptureResult, but we're using create_execution_event + qdas_ledger.append directly. Return (ledger_record, analysis_report) or adapt. Per design: return QDAS capture result and analysis report. Use record_execution_report for simplicity since it already does create+append. But we need the QDAS event object. Use record_execution_report(report, project, qdas_ledger, ...) which returns QdasCaptureResult with .event and .ledger_record. Return (capture_result, analysis_report).

- [ ] **Step 2: Run test to verify it passes**

Run: python -m unittest tests.test_analysis_qdas_120 -v
Expected: all PASS

- [ ] **Step 3: Commit**

Commit message: feat: add QDAS static analysis capture module

---

### Task 3: Add digest binding and tamper-detection tests

**Files:**
- Modify: tests/test_analysis_qdas_120.py

**Interfaces:**
- Consumes: record_analysis_with_qdas from qyrenith_engine.analysis_qdas, QDAS ledger APIs

- [ ] **Step 1: Add digest-binding test**

Add test asserting QDAS event digest in ledger record matches capture_result.event.event_digest, and second run with different project produces different digest.

- [ ] **Step 2: Add tamper-detection test (if not in Task 1)**

If Task 1 test was a stub without tampering, add it now: tamper QDAS ledger line, verify_qdas_ledger raises QdasLedgerError.

- [ ] **Step 3: Run all tests**

Run: python -m unittest tests.test_analysis_qdas_120 -v
Expected: all PASS

- [ ] **Step 4: Commit**

Commit message: test: add QDAS static analysis digest binding and tamper detection

---

### Task 4: Run analysis + QDAS regression tests

**Files:**
- Read: existing tests for qyrenith_engine.analysis if any
- Read: tests/test_qdas_*.py

**Interfaces:**
- Consumes: all analysis and QDAS test modules
- Produces: pass/fail results

- [ ] **Step 1: Run QDAS tests**

Run: python -m unittest tests.test_qdas_events tests.test_qdas_collector tests.test_qdas_diagnosis tests.test_qdas_repair tests.test_qdas_ledger tests.test_qdas_lineage tests.test_qdas_self_verification tests.test_qdas_cli_integration -v
Expected: 81 PASS, 0 failures

- [ ] **Step 2: Run analysis tests if exist**

Check for existing analysis test files. If present, run them; if none, run python -c "from qyrenith_engine.analysis import analyze_project, compare_baselines, build_change_impact; print('analysis import OK')"
Expected: import OK

- [ ] **Step 3: Run new QDAS static analysis tests**

Run: python -m unittest tests.test_analysis_qdas_120 -v
Expected: all PASS

- [ ] **Step 4: Commit**

Commit message: test: verify no regressions across analysis and QDAS test suites

---

### Task 5: Report results

**Files:**
- Modify: none (report only)

**Interfaces:**
- Consumes: results from Tasks 1–4
- Produces: summary report to user

- [ ] **Step 1: Summarize results**

Report: import/export status, test pass/fail per module, digest binding result, tamper detection result, regression check result, any remaining issues.

- [ ] **Step 2: Request user direction**

Ask whether to proceed with capability module 2 (Dynamic and behavioral audit) or pause.

---

## Self-Review

1. **Spec coverage:** Every goal in the design doc maps to a task: new analysis_qdas.py module (Task 2), QDAS event creation + ledger append (Task 2), digest retained (Task 3), existing analysis.py unchanged (Task 4), tests for event creation/ledger/digest/tamper (Tasks 1 & 3). No gaps.

2. **Step scan:** Each step is one action with a checkable result. Test steps have exact assertions; code steps have exact signatures; verification steps have exact commands and expected output.

3. **Type consistency:** Function name record_analysis_with_qdas used consistently in Tasks 1, 2, 3. Import path qyrenith_engine.analysis_qdas used throughout.

4. **Review Focus:** All five review-focus items have corresponding tests: STATIC_ANALYSIS event_kind (Task 2), digest retained (Task 3), tamper detection (Task 3), no regression (Task 4), both results returned (Task 2).

5. **Proportion:** Plan is shorter than the spec; no code bodies included except where the spec fixes exact behavior. Task bodies are signatures and test assertions only.

---

Plan complete and saved to docs/superpowers/plans/2026-11-07-qdas-static-analysis.md. Please review the plan. Does it capture what you want?

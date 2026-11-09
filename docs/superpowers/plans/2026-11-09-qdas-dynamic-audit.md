# QDAS Dynamic Audit Capture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add QDAS capture to the Dynamic and behavioral audit capability module (module 2 of 14) so every scenario run produces a QDAS `ExecutionEvent` (event_kind=`DYNAMIC_AUDIT`) recorded in the QDAS ledger, with QDAS event digest retained, environment fingerprint bound, oracle typed, and reproducibility hooks in place.

**Architecture:** New module qyrenith_engine/dynamic_audit_qdas.py imports run_bounded_process from qyrenith_engine.execution and QDAS record_execution_event/QdasEventLedger/verify_qdas_ledger from qyrenith_engine.qdas. New test file tests/test_dynamic_audit_qdas_120.py covers scenario contract, event creation, ledger append, digest binding, tamper detection.

**Tech Stack:** Python 3.11+ standard library only, unittest, existing QDAS (qyrenith_engine.qdas) and qyrenith_engine.execution.

**Spec:** docs/superpowers/specs/2026-11-09-qdas-dynamic-audit-design.md (pushed to feature/1.2.0-universal-migration-core branch)

## Global Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- QDAS event bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (...Z).
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing execution.py, boundary.py, analysis.py unchanged — no regression.
- QDAS remains observational only; it does not execute repairs or apply patches.
- No OS sandboxing; dynamic audit runs in bounded process only.

## Review Focus

1. **Scenario contract fields present** — setup, inputs, actions, expected_observations, cleanup, timeout, oracle; tested in test_dynamic_audit_qdas_120.py.
2. **Oracle type typed** — EXACT/PROPERTY/DIFFERENTIAL/HEURISTIC enum; tested in test_dynamic_audit_qdas_120.py.
3. **QDAS event created with event_kind DYNAMIC_AUDIT** — tested in test_dynamic_audit_qdas_120.py.
4. **QDAS event digest retained in QDAS ledger record** — tested in test_dynamic_audit_qdas_120.py.
5. **Tamper detection across QDAS ledger** — modifying QDAS ledger breaks verify_qdas_ledger; tested in test_dynamic_audit_qdas_120.py.
6. **Environment fingerprint bound** — scenario outcome includes environment fingerprint; tested in test_dynamic_audit_qdas_120.py.
7. **No regression in existing QDAS/execution tests** — all QDAS tests still pass; run full QDAS suite.

---

### Task 1: Write failing test for QDAS dynamic audit capture

**Files:**
- Create: tests/test_dynamic_audit_qdas_120.py

**Interfaces:**
- Consumes: nothing external yet
- Produces: failing test file that imports run_scenario_with_qdas from qyrenith_engine.dynamic_audit_qdas

- [ ] **Step 1: Write failing test file**

Create tests/test_dynamic_audit_qdas_120.py with:
- test_records_qdas_event_and_scenario_outcome() — calls run_scenario_with_qdas(), asserts it returns a tuple (QdasCaptureResult, scenario_outcome), QDAS ledger has 1 record, QDAS event digest is retained, event_kind is DYNAMIC_AUDIT.
- test_tampering_breaks_qdas_ledger() — tampers QDAS ledger line, expects QdasLedgerError.

Run: python -m unittest tests.test_dynamic_audit_qdas_120 -v
Expected: FAIL with ModuleNotFoundError: No module named 'qyrenith_engine.dynamic_audit_qdas' or ImportError

- [ ] **Step 2: Commit failing test**

Commit message: test: add QDAS dynamic audit capture test stub

---

### Task 2: Implement run_scenario_with_qdas in dynamic_audit_qdas.py

**Files:**
- Create: qyrenith_engine/dynamic_audit_qdas.py

**Interfaces:**
- Consumes: run_bounded_process from qyrenith_engine.execution, create_execution_event/QdasEventLedger/verify_qdas_ledger from qyrenith_engine.qdas
- Produces: function run_scenario_with_qdas(scenario, project, qdas_ledger, *, project_id, project_revision, workspace_id, tool_name, tool_version, environment, seed=None, started_at=None, finished_at=None) -> tuple[QdasCaptureResult, dict[str, Any]]

- [ ] **Step 1: Implement dynamic_audit_qdas.py**

Define:
- OracleType enum: EXACT, PROPERTY, DIFFERENTIAL, HEURISTIC
- ScenarioContract dataclass: scenario_id, name, setup, inputs, actions, expected_observations, cleanup, timeout_seconds, oracle (OracleType), oracle_details
- run_scenario_with_qdas():
  - Serialize scenario to bounded JSON for stdout/stderr of the QDAS event
  - Run run_bounded_process(argv, project, timeout=scenario.timeout_seconds, output_limit=16000, env_overrides=environment)
  - Map run_bounded_process report status to QDAS execution status
  - Call record_execution_report(report, root, qdas_ledger, ..., event_kind="DYNAMIC_AUDIT", ...)
  - Return (capture_result, scenario_outcome) where scenario_outcome includes status, environment_fingerprint, seed, stdout_digest, stderr_digest, duration_seconds, oracle_type

- [ ] **Step 2: Run test to verify it passes**

Run: python -m unittest tests.test_dynamic_audit_qdas_120 -v
Expected: all PASS

- [ ] **Step 3: Commit**

Commit message: feat: add QDAS dynamic audit capture module

---

### Task 3: Add digest binding, environment fingerprint, and tamper-detection tests

**Files:**
- Modify: tests/test_dynamic_audit_qdas_120.py

**Interfaces:**
- Consumes: run_scenario_with_qdas from qyrenith_engine.dynamic_audit_qdas, QDAS ledger APIs

- [ ] **Step 1: Add digest-binding test**

Add test asserting QDAS event digest in ledger record matches capture_result.event.event_digest, and second run with different seed produces different digest.

- [ ] **Step 2: Add environment fingerprint binding test**

Add test asserting scenario_outcome["environment_fingerprint"] matches QDAS event's environment_digest.

- [ ] **Step 3: Add tamper-detection test (if not in Task 1)**

Add test: tamper QDAS ledger line, verify_qdas_ledger raises QdasLedgerError.

- [ ] **Step 4: Run all tests**

Run: python -m unittest tests.test_dynamic_audit_qdas_120 -v
Expected: all PASS

- [ ] **Step 5: Commit**

Commit message: test: add QDAS dynamic audit digest binding, environment fingerprint, and tamper detection

---

### Task 4: Run QDAS + dynamic audit regression tests

**Files:**
- Read: tests/test_qdas_*.py

**Interfaces:**
- Consumes: all QDAS test modules + new dynamic audit test module
- Produces: pass/fail results

- [ ] **Step 1: Run all QDAS tests**

Run: python -m unittest tests.test_qdas_events tests.test_qdas_collector tests.test_qdas_diagnosis tests.test_qdas_repair tests.test_qdas_ledger tests.test_qdas_lineage tests.test_qdas_self_verification tests.test_qdas_cli_integration tests.test_dynamic_audit_qdas_120 -v
Expected: all PASS (81 QDAS + 2-4 dynamic audit tests, 0 failures)

- [ ] **Step 2: Verify execution module unchanged**

Run: python -c "from qyrenith_engine.execution import run_bounded_process, run_bounded_worker; print('execution import OK')"
Expected: import OK

- [ ] **Step 3: Record any regressions and fix**

If any test fails, fix minimal code in owning module, re-run, then proceed.
Expected: zero failures across all QDAS + dynamic audit test modules

- [ ] **Step 4: Commit**

Commit message: test: verify no regressions across QDAS and dynamic audit test suites

---

### Task 5: Report results

**Files:**
- Modify: none (report only)

**Interfaces:**
- Consumes: results from Tasks 1–4
- Produces: summary report to user

- [ ] **Step 1: Summarize integration results**

Report: import/export status, test pass/fail per module, digest binding result, tamper detection result, regression check result, any remaining issues.

- [ ] **Step 2: Request user direction**

Ask whether to proceed with capability module 3 (Formal verification and bounded symbolic execution) or pause.

---

## Self-Review

1. **Spec coverage:** Every goal in the design doc maps to a task: new dynamic_audit_qdas.py module (Task 2), QDAS event creation + ledger append (Task 2), digest retained (Task 3), existing execution.py unchanged (Task 4), tests for event creation/ledger/digest/tamper (Tasks 1 & 3). No gaps.

2. **Step scan:** Each step is one action with a checkable result. Test steps have exact assertions; code steps have exact signatures; verification steps have exact commands and expected output.

3. **Type consistency:** Function name run_scenario_with_qdas used consistently in Tasks 1, 2, 3. Import path qyrenith_engine.dynamic_audit_qdas used throughout.

4. **Review Focus:** All seven review-focus items have corresponding tests: scenario contract (Task 2), oracle type (Task 2), DYNAMIC_AUDIT event_kind (Task 2), digest retained (Task 3), tamper detection (Task 3), environment fingerprint (Task 3), no regression (Task 4).

5. **Proportion:** Plan is shorter than the spec; no code bodies included except where the spec fixes exact behavior. Task bodies are signatures and test assertions only.

---

Plan complete and saved to docs/superpowers/plans/2026-11-09-qdas-dynamic-audit.md. Please review the plan. Does it capture what you want?

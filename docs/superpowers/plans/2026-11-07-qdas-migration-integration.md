# QDAS → Migration Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect stabilized QDAS to the migration workflow by adding a minimal integration layer so every migration step execution produces a QDAS event whose digest is stored in the migration AssuranceLedger evidence_ids.

**Architecture:** New module qyrenith_engine/migration/qdas_step.py ties QDAS record_execution_event + migration AssuranceLedger.append() together. QDAS event digest (64-char SHA-256 hex) is stored in evidence_ids. No changes to existing migration logic; both ledgers remain separate.

**Tech Stack:** Python 3.11+ standard library only, unittest, existing QDAS (qyrenith_engine.qdas) and migration (qyrenith_engine.migration) modules.

**Spec:** docs/superpowers/specs/2026-11-07-qdas-migration-integration-design.md (pushed to feature/1.2.0-universal-migration-core branch)

## Global Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- QDAS event bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- AssuranceLedger evidence_ids: non-empty strings, max 256 chars each, no duplicates, sorted.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (...Z).
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing 1.1.0 behavior and migration tests must not regress.
- QDAS remains observational only; it does not execute migrations or authorize success.

## Review Focus

1. **QDAS event digest bound to AssuranceLedger evidence_ids** — the digest from record_execution_report's event must be stored in evidence_ids; tested in test_migration_qdas_step_120.py.
2. **QDAS event and assurance record both returned** — integration function returns both QdasCaptureResult and AssuranceLedger payload; tested in test_migration_qdas_step_120.py.
3. **Tamper detection across both ledgers** — modifying QDAS ledger or AssuranceLedger breaks its own chain; tested in test_migration_qdas_step_120.py.
4. **No regression in existing migration tests** — all test_migration_*_120.py still pass after integration; tested via full migration test run.
5. **QDAS event digest fits evidence_ids constraints** — 64-char SHA-256 hex is ≤256 chars, non-empty, no duplicates; verified by construction.

---

### Task 1: Write the QDAS→migration integration module

**Files:**
- Create: qyrenith_engine/migration/qdas_step.py

**Interfaces:**
- Consumes: record_execution_report from qyrenith_engine.qdas.collector, AssuranceLedger from qyrenith_engine.migration.assurance, ExecutionEvent from qyrenith_engine.qdas.events
- Produces: function record_migration_step_with_qdas(report, qdas_ledger, assurance_ledger, *, project_id, project_revision, workspace_id, event_kind, tool_name, tool_version, argv, environment, run_id, step_id, transition_id, source_identity, target_identity, plan_digest, pre_state_digest, worker_id, worker_version, worker_status, changed_files, verdict, created_at, ...optional assurance fields...) -> (QdasCaptureResult, dict)

- [ ] **Step 1: Write failing test for record_migration_step_with_qdas**

In tests/test_migration_qdas_step_120.py, write a test that calls record_migration_step_with_qdas with a mock bounded report, QDAS ledger, and AssuranceLedger, then asserts:
- Returns a tuple of (QdasCaptureResult, assurance_record)
- assurance_record["evidence_ids"] contains exactly one item equal to capture_result.event.event_digest
- QDAS ledger has one record
- Assurance ledger has one record

Run: python -m unittest tests.test_migration_qdas_step_120 -v
Expected: FAIL with ImportError: cannot import name 'record_migration_step_with_qdas' or ModuleNotFoundError

- [ ] **Step 2: Implement record_migration_step_with_qdas in qyrenith_engine/migration/qdas_step.py**

Function body:
- Call record_execution_report(report, project_root, qdas_ledger, ...) → capture_result
- event_digest = capture_result.event.event_digest
- evidence_ids = [event_digest]
- Call assurance_ledger.append(fields_with_evidence_ids) → assurance_record
- Return (capture_result, assurance_record)

- [ ] **Step 3: Run test to verify it passes**

Run: python -m unittest tests.test_migration_qdas_step_120 -v
Expected: PASS

- [ ] **Step 4: Commit**

Commit message: feat: add QDAS→migration step integration module

---

### Task 2: Add digest binding and tamper-detection tests

**Files:**
- Modify: tests/test_migration_qdas_step_120.py

**Interfaces:**
- Consumes: record_migration_step_with_qdas from qyrenith_engine.migration.qdas_step, QDAS ledger and AssuranceLedger APIs

- [ ] **Step 1: Write tamper-detection test**

Add a test that:
- Records one migration step with QDAS
- Modifies a line in the QDAS ledger file directly (tamper)
- Calls QDAS verify_qdas_ledger, expects QdasLedgerError
- Modifies a line in the AssuranceLedger file directly (tamper)
- Calls verify_assurance_chain, expects AssuranceLedgerError

- [ ] **Step 2: Run tamper-detection test**

Run: python -m unittest tests.test_migration_qdas_step_120::TestQdasMigrationStep.test_tampering_breaks_both_ledgers -v
Expected: PASS

- [ ] **Step 3: Write digest-binding test**

Add a test that asserts the QDAS event digest in evidence_ids exactly matches capture_result.event.event_digest, and that a second call with different input produces a different digest.

- [ ] **Step 4: Run digest-binding test**

Run: python -m unittest tests.test_migration_qdas_step_120 -v
Expected: all tests PASS

- [ ] **Step 5: Commit**

Commit message: test: add QDAS migration digest binding and tamper detection tests

---

### Task 3: Export integration function from migration package

**Files:**
- Modify: qyrenith_engine/migration/__init__.py

**Interfaces:**
- Consumes: record_migration_step_with_qdas from .qdas_step
- Produces: record_migration_step_with_qdas added to __init__.py imports and __all__

- [ ] **Step 1: Add import and export**

In qyrenith_engine/migration/__init__.py:
- Add from .qdas_step import record_migration_step_with_qdas to the import block
- Add "record_migration_step_with_qdas" to __all__

- [ ] **Step 2: Verify import works**

Run: python -c "from qyrenith_engine.migration import record_migration_step_with_qdas; print('export OK')"
Expected: prints export OK

- [ ] **Step 3: Commit**

Commit message: export: expose QDAS migration step integration from migration package

---

### Task 4: Run full migration + QDAS test suite for regressions

**Files:**
- Read: tests/test_migration_core_120.py, test_migration_assurance_120.py, test_migration_workspace_120.py, test_migration_snapshot_120.py, test_migration_worker_120.py, test_migration_preparation_120.py, test_migration_authorization_120.py, test_migration_benchmarks_120.py
- Read: tests/test_qdas_*.py

**Interfaces:**
- Consumes: all migration and QDAS test modules
- Produces: pass/fail results for every migration and QDAS test

- [ ] **Step 1: Run all migration tests**

Run: python -m unittest tests.test_migration_core_120 tests.test_migration_assurance_120 tests.test_migration_workspace_120 tests.test_migration_snapshot_120 tests.test_migration_worker_120 tests.test_migration_preparation_120 tests.test_migration_authorization_120 tests.test_migration_benchmarks_120 tests.test_migration_qdas_step_120 -v
Expected: all PASS

- [ ] **Step 2: Run all QDAS tests**

Run: python -m unittest tests.test_qdas_events tests.test_qdas_collector tests.test_qdas_diagnosis tests.test_qdas_repair tests.test_qdas_ledger tests.test_qdas_lineage tests.test_qdas_self_verification tests.test_qdas_cli_integration -v
Expected: all PASS (81 tests, 0 failures)

- [ ] **Step 3: Record any regressions and fix**

If any test fails, fix the minimal code in the owning module, re-run, then proceed.
Expected: zero failures across all migration and QDAS test modules

- [ ] **Step 4: Commit**

Commit message: test: verify no regressions across migration and QDAS test suites

---

### Task 5: Report results and request next direction

**Files:**
- Modify: none (report only)

**Interfaces:**
- Consumes: results from Tasks 1–4
- Produces: summary report to the user

- [ ] **Step 1: Summarize integration results**

Report: import/export status, test pass/fail per module, digest binding result, tamper detection result, regression check result, any remaining issues.

- [ ] **Step 2: Request user direction**

Ask whether to proceed with the next capability module (one of the remaining 14) using QDAS-assisted execution, or to pause.

---

## Self-Review

1. **Spec coverage:** Every goal in the design doc maps to a task: new qdas_step module (Task 1), digest in evidence_ids (Task 1 & 2), no regression (Task 4), tests for capture+ledger+digest binding (Task 2), export from __init__ (Task 3). No gaps.

2. **Step scan:** Each step is one action with a checkable result. Test steps have exact assertions; code steps have exact signatures; verification steps have exact commands and expected output.

3. **Type consistency:** Function name record_migration_step_with_qdas used consistently in Tasks 1, 2, 3. Import path qyrenith_engine.migration.qdas_step used in Task 3.

4. **Review Focus:** All five review-focus items have corresponding tests: digest binding (Task 2), both results returned (Task 1), tamper detection (Task 2), no regression (Task 4), digest fits constraints (Task 1/2 by construction).

5. **Proportion:** Plan is shorter than the spec; no code bodies included except where the spec fixes exact behavior. Task bodies are signatures and test assertions only.

---

Plan complete and saved to docs/superpowers/plans/2026-11-07-qdas-migration-integration.md. Please review the plan. Does it capture what you want?

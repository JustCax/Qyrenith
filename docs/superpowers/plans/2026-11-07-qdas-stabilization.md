# QDAS Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize QDAS on the `feature/1.2.0-universal-migration-core` branch so it can serve as the assisted execution layer for Qyrenith 1.2.0, then merge to `main` only after the full test matrix passes and the user approves.

**Architecture:** QDAS already exists as source on PR #9's branch (`qyrenith_engine/qdas/` with modules events, collector, diagnosis, repair, ledger, lineage plus tests and schemas). The plan runs the existing test suite locally, fixes any import/test failures, verifies ledger hash-chain tamper detection and repair-plan PROPOSE_ONLY invariants, then runs the CI matrix across Python 3.11–3.14 on Ubuntu/Windows/macOS before any merge.

**Tech Stack:** Python 3.11+ standard library only, unittest, GitHub Actions CI, no new dependencies.

**Spec:** docs/superpowers/specs/2026-11-05-qdas-stabilization-design.md (already pushed to feature/1.2.0-universal-migration-core branch on GitHub)

## Global Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- All paths project-relative POSIX, canonical, no traversal.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (`...Z`).
- Events bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing 1.1.0 behavior and public release package contents must not regress.
- QDAS does not execute repairs, apply patches, or run migrations.
- QDAS does not authenticate human identity or provide OS-level sandboxing.
- Repair plans are strictly PROPOSE_ONLY, always require human review.

## Review Focus

1. **PASS event with non-zero exit code** — events.py must reject execution_status == "PASS" when exit_code != 0; tested in test_qdas_events.py.
2. **Repair plan not PROPOSE_ONLY or not human-reviewed** — repair.py __post_init__ must reject execution_mode != "PROPOSE_ONLY" and human_review_required is not True; tested in test_qdas_repair.py.
3. **Ledger record rewrite without breaking hash chain** — ledger.py verify_qdas_ledger must detect tampering; tested in test_qdas_ledger.py.
4. **Failure classification infers root cause from exit code alone** — events.py classify_failure must be symptom-based only; tested in test_qdas_diagnosis.py.
5. **Event JSON not canonical on re-serialization** — events.py from_json_bytes must reject non-canonical JSON; tested in test_qdas_events.py.

---

### Task 1: Local QDAS import check

**Files:**
- Read: qyrenith_engine/qdas/__init__.py
- Read: qyrenith_engine/qdas/events.py
- Read: qyrenith_engine/qdas/collector.py
- Read: qyrenith_engine/qdas/diagnosis.py
- Read: qyrenith_engine/qdas/repair.py
- Read: qyrenith_engine/qdas/ledger.py
- Read: qyrenith_engine/qdas/lineage.py

**Interfaces:**
- Consumes: nothing external
- Produces: confirmation that all six QDAS modules import cleanly

- [ ] **Step 1: Import all QDAS modules locally**

Run: python -c "from qyrenith_engine.qdas import *; print('QDAS import OK')" from the repo root on the feature/1.2.0-universal-migration-core branch.
Expected: no ImportError, prints "QDAS import OK"

- [ ] **Step 2: Commit if imports pass**

Commit message: chore: verify QDAS module imports on feature branch

---

### Task 2: Run QDAS unittest suite locally

**Files:**
- Read: tests/test_qdas_events.py
- Read: tests/test_qdas_collector.py
- Read: tests/test_qdas_diagnosis.py
- Read: tests/test_qdas_repair.py
- Read: tests/test_qdas_ledger.py
- Read: tests/test_qdas_lineage.py
- Read: tests/test_qdas_self_verification.py
- Read: tests/test_qdas_cli_integration.py

**Interfaces:**
- Consumes: QDAS modules from Task 1
- Produces: test pass/fail results per QDAS test module

- [ ] **Step 1: Run all QDAS tests**

Run: python -m unittest tests.test_qdas_events tests.test_qdas_collector tests.test_qdas_diagnosis tests.test_qdas_repair tests.test_qdas_ledger tests.test_qdas_lineage tests.test_qdas_self_verification tests.test_qdas_cli_integration -v
Expected: all tests PASS

- [ ] **Step 2: Record any failures and fix them**

If any test fails, fix the minimal code in the owning QDAS module, re-run the failing test, then proceed.
Expected: zero failures across all eight QDAS test modules

- [ ] **Step 3: Commit fixes**

Commit message: fix: resolve QDAS test failures on feature branch

---

### Task 3: Verify QDAS ledger hash-chain and tamper detection

**Files:**
- Read: qyrenith_engine/qdas/ledger.py
- Read: tests/test_qdas_ledger.py

**Interfaces:**
- Consumes: QdasEventLedger, verify_qdas_ledger from qyrenith_engine.qdas.ledger
- Produces: confirmation that ledger append, hash-chain verification, and tamper detection all work

- [ ] **Step 1: Write/append ledger records and verify chain**

Create a temporary ledger, append two execution events, call verify_qdas_ledger, confirm it returns valid.
Expected: verification passes for a clean chain

- [ ] **Step 2: Tamper with a ledger record and verify detection**

Modify a single ledger line's content hash without recomputing the chain, call verify_qdas_ledger, confirm it raises QdasLedgerError or returns invalid.
Expected: tampering is detected

- [ ] **Step 3: Commit**

Commit message: test: verify QDAS ledger hash-chain and tamper detection

---

### Task 4: Verify repair plan PROPOSE_ONLY and human-review invariants

**Files:**
- Read: qyrenith_engine/qdas/repair.py
- Read: tests/test_qdas_repair.py

**Interfaces:**
- Consumes: RepairPlan from qyrenith_engine.qdas.repair
- Produces: confirmation that invalid repair plans are rejected at construction

- [ ] **Step 1: Construct a valid RepairPlan**

Create a RepairPlan with execution_mode="PROPOSE_ONLY", human_review_required=True, valid paths/permissions/commands.
Expected: construction succeeds

- [ ] **Step 2: Attempt invalid RepairPlan constructions**

Attempt execution_mode="EXECUTE" and human_review_required=False, confirm both raise ValueError.
Expected: both raise ValueError

- [ ] **Step 3: Commit**

Commit message: test: verify QDAS repair plan propose-only and human-review invariants

---

### Task 5: Simulate CI matrix on available platforms

**Files:**
- Read: .github/workflows/ci.yml
- Read: qyrenith_engine/execution.py

**Interfaces:**
- Consumes: QDAS modules, bounded process runner
- Produces: confirmation that QDAS works under Python 3.11–3.14 bounds without weakening execution limits

- [ ] **Step 1: Check local Python version**

Run: python --version
Expected: Python 3.11 or higher

- [ ] **Step 2: Run QDAS tests with the local Python**

Run: python -m unittest tests.test_qdas_* -v
Expected: all QDAS tests pass

- [ ] **Step 3: Verify bounded process runner integration**

Confirm collector.py uses run_bounded_process with the 1 MiB stdout/stderr bounds, timeout, and process-group cleanup intact.
Expected: no weakening of execution bounds

- [ ] **Step 4: Commit**

Commit message: chore: verify QDAS CI matrix prerequisites on local platform

---

### Task 6: Report results and request merge approval

**Files:**
- Modify: none (report only)

**Interfaces:**
- Consumes: results from Tasks 1–5
- Produces: summary report to the user

- [ ] **Step 1: Summarize stabilization results**

Report: import status, test pass/fail per module, ledger verification result, repair plan invariant result, CI matrix simulation result, any remaining issues.

- [ ] **Step 2: Request user approval to merge to main**

Ask the user whether to open a merge PR from feature/1.2.0-universal-migration-core to main once all checks pass.

---

## Self-Review

1. **Spec coverage:** Every goal in the design doc maps to a task: import + unittest (Task 2), self-verification (Task 2), bounded process integration (Task 5), ledger hash-chain (Task 3), repair plan PROPOSE_ONLY (Task 4), stability for 1.2.0 layer (Task 6). No gaps.

2. **Step scan:** Each step is one action with a checkable result. No step decides nothing; no step carries more than one reasonable action.

3. **Type consistency:** All interfaces reference existing QDAS module names and signatures from PR #9 (qyrenith_engine.qdas.events, collector, diagnosis, repair, ledger, lineage).

4. **Review Focus:** All five review-focus items have a corresponding task and test: PASS/exit-code (Task 2), repair plan invariants (Task 4), ledger tamper detection (Task 3), classification root-cause (Task 2 via diagnosis tests), canonical JSON (Task 2 via events tests).

5. **Proportion:** Plan is shorter than the spec; no code bodies included except where the spec fixes exact behavior. Task bodies are signatures and test assertions only.

---

Plan complete and saved to docs/superpowers/plans/2026-11-07-qdas-stabilization.md. Please review the plan. Does it capture what you want?
# QDAS Capture for Dynamic and Behavioral Audit — Qyrenith 1.2.0

**Date:** 2026-11-09  
**Repository:** JustCax/Qyrenith  
**Branch:** feature/1.2.0-universal-migration-core (PR #9 draft)  
**Status:** Draft — awaiting human approval before any build work  
**Module:** Capability module 2 of 14 — Dynamic and behavioral audit

---

## Intent and why

QDAS capture exists for migration steps (module integration) and static analysis (module 1 of 14). The next module is **Dynamic and behavioral audit** (module 2 of 14), per the QYRENITH_1_2_0_IMPLEMENTATION_AND_ACCEPTANCE_PLAN.md sequence. The DYNAMIC_AND_BEHAVIORAL_AUDIT_SPEC.md defines 12 requirements (DB-01..DB-12): scenario contracts, state-transition checks, error-path checks, resource lifecycle, concurrency, boundary behavior, environment awareness, oracles, reproducibility, QDAS integration, safe execution, reporting.

There is currently **no code** for dynamic audit — only specs. This design adds a minimal QDAS-captured dynamic audit module: scenario contracts, bounded execution via run_bounded_process, QDAS ExecutionEvent (event_kind=DYNAMIC_AUDIT) recorded in the QDAS ledger, environment fingerprint binding, oracle typing, and reproducibility hooks.

QDAS remains strictly observational: it records events, classifies failures (symptom-only, never root-cause), and produces unconfirmed hypotheses. Nothing executes repairs or applies patches.

## Goals

1. New module qyrenith_engine/dynamic_audit_qdas.py provides:
   - ScenarioContract dataclass: setup, inputs, actions, expected_observations, cleanup, timeout, oracle (DB-01)
   - OracleType enum: EXACT, PROPERTY, DIFFERENTIAL, HEURISTIC (DB-08)
   - run_scenario_with_qdas() function: runs scenario under QDAS observation, records QDAS event in QDAS ledger, binds environment fingerprint, returns QDAS capture result + scenario outcome dict (DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, DB-09, DB-11)
   - Scenario outcome includes: status (PASS/FAIL/BLOCKED/INCONCLUSIVE/SKIPPED/UNSUPPORTED/TIMEOUT/INFRASTRUCTURE_FAILURE), environment fingerprint, seed, stdout/stderr digests, duration, oracle type (DB-12)
2. QDAS event digest retained in QDAS ledger record.
3. Scenario reproducibility: same seed + scenario produces deterministic outcome (DB-09).
4. Safe execution: bounded process only, no OS sandbox, resource limits enforced (DB-11).
5. QDAS integration: baseline vs post-repair comparison hook (DB-10 stub).
6. Standard-library-only, Python 3.11+, no new dependencies.

## Non-goals

- No OS sandboxing; dynamic audit runs in bounded process only.
- No authenticated human approval (that's Phase 1, not this module).
- No actual test discovery or unittest execution — scenarios are explicitly defined by the caller.
- No repair execution; QDAS is observational only.
- No merge to main as part of this design.

## Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- QDAS event bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (...Z).
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing analysis.py, execution.py, boundary.py unchanged — no regression.
- QDAS remains observational only.

## Approaches considered

**Approach 1 — New dynamic_audit_qdas.py module with scenario contract + QDAS capture.** (Selected)
Single file, minimal, reversible, follows the same pattern as analysis_qdas.py and qdas_step.py.

**Approach 2 — Separate core + QDAS wrapper (dynamic_audit.py + dynamic_audit_qdas.py).**
Rejected: larger refactor for this early stage; can be factored out later when the module matures.

**Approach 3 — Extend QDAS collector with dynamic audit logic.**
Rejected: couples QDAS to dynamic audit domain; QDAS must stay domain-neutral.

## Decided how (as decided)

- New file: qyrenith_engine/dynamic_audit_qdas.py
- New test file: tests/test_dynamic_audit_qdas_120.py
- No export from qyrenith_engine/__init__.py initially (internal to module until needed elsewhere)
- CI already compiles and runs dynamic_audit + QDAS tests (to be wired on the branch)

## What is left to the builder

- Write dynamic_audit_qdas.py with exact signature
- Write tests: scenario contract, QDAS event creation, ledger append, environment fingerprint binding, oracle typing, tamper detection
- Run dynamic audit + QDAS tests (no regressions)
- Report results before any merge to main

---

## Approval requested

Please confirm this design is acceptable, or state what should change. Once approved, I will proceed to the plan (writing-plans) and then implementation on the feature branch.

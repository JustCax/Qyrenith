# QDAS → Migration Integration Design — Qyrenith 1.2.0

**Date:** 2026-11-07  
**Repository:** JustCax/Qyrenith  
**Branch:** feature/1.2.0-universal-migration-core (PR #9 draft)  
**Status:** Draft — awaiting human approval before any build work  
**Approach:** A (minimal QDAS-instrumented migration steps)

---

## Intent and why

QDAS is stabilized (81 tests pass, hash-chain ledger, PROPOSE_ONLY repair plans) but **not connected** to the migration workflow. The migration modules (planner, knowledge, assurance, worker, preparation, snapshot, workspace, authorization, model) exist with tests, but **none imports QDAS**.

Approach A (chosen): add a thin integration layer so that every migration step execution (bounded process run) produces a QDAS event, and the QDAS event digest is recorded in the migration AssuranceLedger record's evidence_ids. This makes QDAS the evidence/proof layer for migration steps without refactoring the existing migration ledger or weakening its guarantees.

QDAS remains strictly observational: it records events, classifies failures (symptom-only, never root-cause), and produces unconfirmed hypotheses. Nothing in QDAS executes repairs or authorizes migration success.

## Goals

1. New module qyrenith_engine/migration/qdas_step.py provides a single function that:
   - Runs a bounded process via QDAS capture_process_event (producing a QDAS ExecutionEvent)
   - Appends a migration AssuranceLedger record whose evidence_ids contains the QDAS event digest
   - Returns both the QDAS capture result and the assurance record
2. QDAS event digest (SHA-256 hex, 64 chars) fits within AssuranceLedger.evidence_ids constraints (non-empty strings, max 256 chars each, no duplicates).
3. All existing migration tests continue to pass (no regression).
4. New tests cover the QDAS→migration integration (capture + ledger append, digest binding, tamper detection across both ledgers).
5. Standard-library-only, Python 3.11+, no new dependencies.

## Non-goals

- QDAS does not execute migrations, apply patches, or authorize success.
- AssuranceLedger is not replaced or merged into QDAS ledger; both remain separate.
- QDAS does not provide OS sandboxing or human authentication.
- No merge to main as part of this design.

## Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- QDAS event bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- AssuranceLedger evidence_ids: non-empty strings, max 256 chars, no duplicates, sorted.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (...Z).
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing 1.1.0 behavior and migration tests must not regress.

## Approaches considered

**Approach A — QDAS-instrumented migration steps (minimal).** (Selected)
New qdas_step.py module ties capture_process_event + AssuranceLedger.append() together. QDAS event digest stored in evidence_ids. Minimal change, reversible, no regression risk to existing migration tests.

**Approach B — QDAS-as-verification-backend.**
AssuranceLedger.append() internally creates QDAS event and binds record_digest to QDAS event digest. Single hash chain. Rejected: larger refactor, couples two ledgers unnecessarily.

**Approach C — Full QDAS/migration unification.**
Drop AssuranceLedger, make QDAS ledger the single source. Rejected: highest risk, breaks existing migration assurance tests.

## Decided how (as decided)

- New file: qyrenith_engine/migration/qdas_step.py
- New test file: tests/test_migration_qdas_step_120.py
- Export record_migration_step_with_qdas from qyrenith_engine/migration/__init__.py
- CI already compiles and runs migration + QDAS tests (wired on the branch)

## What is left to the builder

- Write the qdas_step.py integration function with exact signature
- Write tests proving capture + ledger append + digest binding
- Run all migration + QDAS tests (no regressions)
- Report results before any merge to main

---

## Approval requested

Please confirm this design is acceptable, or state what should change. Once approved, I will proceed to the plan (writing-plans) and then implementation on the feature branch.

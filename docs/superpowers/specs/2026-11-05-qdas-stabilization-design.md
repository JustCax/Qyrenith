# QDAS Stabilization Design — Qyrenith 1.2.0

**Date:** 2026-11-05  
**Repository:** JustCax/Qyrenith  
**Branch:** feature/1.2.0-universal-migration-core (PR #9 draft)  
**Status:** Draft — awaiting human approval before any build work

---

## Intent and why

QDAS (Qyrenith Development Assurance System) already exists as source on the feature/1.2.0-universal-migration-core branch (PR #9), but it is **not** merged to main and has not been exercised as a stabilized subsystem. The user wants QDAS stabilized first, and only then used as the assisted execution layer for the remaining 1.2.0 capability modules.

QDAS purpose: bounded, digest-bound, evidence-linked execution recording — every build/test/verification step produces an immutable QDAS event, a failure classification (never a root-cause verdict), unconfirmed hypotheses, a propose-only repair plan, and a hash-chained ledger record. Nothing in QDAS executes repairs or authorizes success; it only observes, records, and proposes.

## Goals

1. All QDAS modules (events, collector, diagnosis, repair, ledger, lineage) import cleanly and pass their existing unittest suite on Python 3.11–3.14 across Ubuntu, Windows, macOS.
2. QDAS self-verification passes (tests/test_qdas_self_verification.py, tests/test_qdas_cli_integration.py).
3. QDAS integrates with the existing bounded process runner (qyrenith_engine/execution.py) without weakening its 1 MiB stdout/stderr bounds, timeout, or process-group cleanup.
4. QDAS ledger is append-only, single-writer locked, hash-chain verifiable, and tamper-evident.
5. Repair plans are strictly PROPOSE_ONLY, always require human review, and never execute changes.
6. QDAS is stable enough to serve as the assisted execution layer for the fourteen remaining 1.2.0 capability modules.

## Non-goals

- QDAS does not execute repairs, apply patches, or run migrations.
- QDAS does not authenticate human identity or provide OS-level sandboxing.
- QDAS does not merge to main as part of this design; merge happens only after stabilization and user approval.
- QDAS does not replace the existing worker-run legacy command; it is a separate, stricter observation layer.

## Anti-goals (failure even if technically works)

- A QDAS event marked PASS with a non-zero exit code.
- A repair plan with execution_mode != PROPOSE_ONLY or human_review_required != True.
- A ledger record that can be rewritten without breaking the hash chain.
- Failure classification that infers root cause from exit code alone.

## Constraints

- Standard-library-only core (no new dependencies).
- Python 3.11+.
- All paths project-relative POSIX, canonical, no traversal.
- All digests lowercase SHA-256; all timestamps canonical UTC milliseconds (...Z).
- Events bounded to 256 KiB; stdout/stderr to 8 MiB; argv to 256 args / 16 KiB per arg.
- Deterministic canonical JSON (sorted keys, ensure_ascii, no NaN).
- Existing 1.1.0 behavior and public release package contents must not regress.

## Approaches considered

**Approach 1 — Merge QDAS to main immediately, then stabilize.**
Rejected. QDAS is not yet proven stable; merging unstable observation code into main would expose 1.1.0 users to untested behavior and violate the stable QDAS first requirement.

**Approach 2 — Stabilize QDAS on the feature branch, run full test matrix, then merge to main when green.** (Selected)
QDAS stays on feature/1.2.0-universal-migration-core. We run the CI matrix (Python 3.11–3.14 × Ubuntu/Windows/macOS), fix regressions, then merge only after the full matrix passes and the user approves.

**Approach 3 — Build a separate QDAS package outside the repo.**
Rejected. QDAS is tightly coupled to qyrenith_engine/execution.py and the migration primitives; splitting it adds boundary complexity with no benefit.

## Decided how (as decided)

- QDAS source lives under qyrenith_engine/qdas/ (already present on the branch).
- QDAS tests live under tests/test_qdas_*.py (already present on the branch).
- CI already compiles and runs QDAS tests via .github/workflows/ci.yml (already wired on the branch).
- Stabilization work = run the matrix, fix failures, review ledger/hash-chain and repair-plan invariants, then merge to main.

## What is left to the builder

- Run the QDAS test suite locally and via CI on the feature branch.
- Investigate and fix any test or import failures found.
- Verify QDAS ledger hash-chain verification and tamper-detection behavior.
- Confirm repair plans remain propose-only and human-review-required.
- Report results back to the user before any merge to main is requested.

---

## Approval requested

Please confirm this design is acceptable, or state what should change. Once approved, I will proceed to the plan (writing-plans) and then stabilization work on the feature branch.

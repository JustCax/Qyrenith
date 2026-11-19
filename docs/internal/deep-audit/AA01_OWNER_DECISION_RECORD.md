# AA-01 Owner Decision Record — Qyrenith 1.2.0

**Decision date:** 2026-11-10  
**Owner approval:** Explicitly granted in the project-planning conversation on 2026-11-10  
**Target branch:** `feature/1.2.0-universal-migration-core`  
**Status:** Seven AA-01 decision directions, four AA ADRs, all 70 AA requirements, and all 27 diagnostic domains ACCEPTED for the 1.2.0 scope; implementation remains unverified

## 1. Approval scope

The owner explicitly accepted all seven AA-01 decision directions and the first-class extensibility/supportability architectural requirement. These are binding inputs to 1.2.0 specification reconciliation and implementation planning; they do not mean runtime code, schemas, tests, providers, isolation mechanisms, or support claims are implemented or verified.

The owner separately accepted all four reconciled AA ADRs, all 70 AA requirements across the existing eleven groups, and all 27 diagnostic domains for inclusion in the 1.2.0 release scope on 2026-11-16. This does not accept PR #3 as a whole or the six-pillar product grouping. Acceptance establishes scope and architecture; it does not claim implementation, testing, qualification, or verification.

## 2. Owner decisions recorded on 2026-11-16

- **ADR-AA-001..004:** all four reconciled ADRs accepted as written.
- **AA-REQ-PROJ/PLAN/CHK/EVD/POL/SEC/RPT/EXT/CMP/REL/NFR:** all 70 stable requirements accepted as a grouped cross-cutting assurance contract, preserving their existing eleven-group structure and IDs.
- **Diagnostic capability scope:** all 27 domains and their 81 stable DI-001..DI-081 requirement IDs are included in the 1.2.0 release scope. Their current PARTIAL/NOT_STARTED implementation statuses remain unchanged until evidence supports advancement.
- **Product grouping:** the six-pillar grouping is not accepted by this decision.

These decisions update the acceptance baseline only. Each requirement/domain still needs implementation, tests, retained evidence, and independent review where required.

## 2. Accepted decisions

### AA-D1 — Per-check outcomes

Accepted outcomes: `PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, `UNKNOWN`, `NOT_RUN`, `UNSUPPORTED`, `ERROR`. No missing, stale, ambiguous, blocked, inconclusive, unsupported, not-run, or error state may be upgraded to PASS. UNKNOWN means insufficient trustworthy information to classify; INCONCLUSIVE means an evaluation occurred but did not establish a defensible conclusion. Infrastructure ERROR is not a subject-level FAIL.

Legacy conversion preserves raw values and provenance. The exhaustive mapping table is an implementation prerequisite and must be derived from actual legacy states; ambiguous values remain UNKNOWN.

### AA-D2 — Persistent evidence

Accepted logical model: one canonical QDAS event journal, a content-addressed immutable artifact store, and an optional rebuildable non-authoritative query index. A later external trust anchor is optional and requires a separate identity/key-management design.

The physical backend is deferred until candidates are compared against common atomicity, crash recovery, concurrency, portability, privacy, retention, export/restore, and fault-injection criteria. No second evidence authority is permitted.

### AA-D3 — Isolation and host enforcement

Accepted canonical isolation scale: existing RVL L0–L5. Platform-specific host-enforced capabilities must be discovered and independently tested. Declared configuration is not proof. No silent downgrade is permitted. If a required boundary is unavailable, side-effecting work remains PROPOSE_ONLY or returns BLOCKED/UNSUPPORTED.

### AA-D4 — Verification profiles

Accepted model: immutable, versioned manifests with exact check IDs/versions, scope, prerequisites, exclusions, evidence/oracle requirements, isolation/network policy, resource budgets, concurrency/cancellation, freshness, and retention rules.

Baseline, Standard, and Deep Audit are candidate labels only. Final profile names, inventories, budgets, and support claims are deferred until the checker catalog and resource model are complete.

### AA-D5 — Network providers

Network access is disabled by default at every layer. The first 1.2.0 release MUST NOT contain network-dependent mandatory checks. Any later network provider requires a separate owner-approved threat model, explicit per-run approval, endpoint/operation allowlists, bounded I/O, provenance, and auditable data-flow records.

### AA-D6 — Aggregate project assurance

Accepted aggregate states: `ASSURED`, `NOT_ASSURED`, `BLOCKED`, `INCONCLUSIVE`, and `PARTIAL`. The aggregate decision is separate from per-check outcomes and binds the exact project snapshot, profile, requested/evaluated scope, mandatory/optional inventory, coverage, evidence integrity/freshness, policy version, and evaluator version. ASSURED is impossible when any mandatory condition or evidence requirement is unmet. PASS counts alone never determine the result.

### AA-D7 — Reproducibility

Accepted outcomes: `REPRODUCIBLE`, `NON_REPRODUCIBLE`, `INCONCLUSIVE`, `BLOCKED`, `NOT_RUN`, and `UNSUPPORTED`. Same-environment repeatability, cross-environment, artifact, behavioral, and independent evidence replay dimensions are reported separately. RVL remains the sole execution/replay engine; no second runner is introduced.

## 3. Accepted extensibility principle

Extensibility and supportability are first-class architectural requirements. New language frontends, domain packs, checkers, knowledge packs, build/test integrations, optional providers, isolation providers, and evidence/report integrations use versioned contracts, exact support scopes, provenance, qualification, conformance evidence, and least-privilege permissions.

Extensions may add capability but may not replace or bypass central policy, authorization, evidence integrity, execution isolation, or verdict authority. Discovery/installation does not equal qualification or support. Support classifications remain distinct from check outcomes and aggregate assurance.

The normative contract is `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`; EX-001..EX-016 are accepted specification requirements. Implementation remains NOT_STARTED.

## 4. Deferred details and prerequisites

- Physical evidence-store backend.
- Final verification profile names and exact check inventories.
- Exhaustive legacy-state conversion table until real legacy values are inventoried.
- Platform-by-platform L0–L5 enforcement support matrix.
- Individual extension qualification and ecosystem support claims.
- Final schemas, API/CLI surfaces, and implementation slice boundaries.
- Acceptance evidence and independent verification.

Deferred means explicitly not yet decided or implemented; it does not mean optional where a release gate requires it.

## 5. Governance

- Record and implement these decisions only on `feature/1.2.0-universal-migration-core`.
- Do not modify, merge into, rebase, or otherwise update `main` before explicit 1.2.0 release approval.
- PR #9 remains the release PR to `main`; keep it open/draft and unmerged until release approval.
- PR #3 remains a separate source/review PR. Do not merge it into `main`; selectively integrate only separately reviewed and accepted content into the 1.2.0 branch.
- Do not restore or trigger GitHub Actions without explicit approval.
- No runtime implementation is authorized merely by this decision record.

## 6. Related specifications

- `ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md`
- `ADVANCED_ASSURANCE_INTEGRATION_AND_PR3_REVIEW.md`
- `DEEP_AUDIT_MASTER_ARCHITECTURE.md`
- `LANGUAGE_AND_DOMAIN_ADAPTER_SPEC.md`
- `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`
- `QYRENITH_1_2_0_IMPLEMENTATION_AND_ACCEPTANCE_PLAN.md`
- `REQUIREMENT_TRACEABILITY_MATRIX.md`

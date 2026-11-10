# ADR-AA-001: Separate Observation, Evidence Validation, and Assurance Authority

**Status:** PROPOSED — reconciled with owner-approved AA-01 decision directions; ADR acceptance pending  
**Original proposal date:** 2026-11-04  
**Reconciliation date:** 2026-11-10  
**Scope:** Cross-cutting assurance authority across the canonical five planes

## Context

A checker, worker, native analyzer, or external provider emits observations. Its output may be incorrect, compromised, stale, incomplete, misconfigured, or outside its declared scope. Allowing the producer to validate its own observation, qualify itself, authorize its own actions, or issue the final assurance verdict creates a self-certification path.

Qyrenith already defines five canonical planes and distinguishes discovery, qualification, authorization, execution, and verification. Advanced Assurance (AA) must use those authorities rather than create a parallel subsystem.

## Decision proposal

Separate these responsibilities and preserve one authority for each:

1. **Observation producers** (checkers, analyzers, workers, adapters and providers) emit bounded observations, raw-output references, execution metadata, and limitations. They cannot decide whether their own output is trusted.
2. **Evidence validation** independently checks identity, schema, scope, provenance, completeness, integrity, freshness, and required evidence.
3. **Qualification** evaluates extension/provider conformance. Discovery, installation, registration, and publisher claims do not equal qualification.
4. **Authorization** evaluates a human-approved grant for an exact project snapshot, plan, action, scope, permissions, and limits. A provider cannot authorize itself.
5. **Policy/verdict evaluation** evaluates validated evidence against the selected immutable policy/profile and produces authoritative per-check and aggregate decisions.
6. **Reporting** renders the recorded decision and its evidence/coverage references; it does not recalculate or upgrade the verdict.

These vocabularies remain separate and MUST NOT be collapsed:

- Per-check: `PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, `UNKNOWN`, `NOT_RUN`, `UNSUPPORTED`, `ERROR`.
- Aggregate assurance: `ASSURED`, `NOT_ASSURED`, `BLOCKED`, `INCONCLUSIVE`, `PARTIAL`.
- Reproducibility: `REPRODUCIBLE`, `NON_REPRODUCIBLE`, `INCONCLUSIVE`, `BLOCKED`, `NOT_RUN`, `UNSUPPORTED`.
- Extension support: `NATIVE_SUPPORTED`, `QUALIFIED_PROVIDER`, `EXPERIMENTAL`, `PARTIAL`, `UNSUPPORTED`.

No missing, stale, ambiguous, blocked, inconclusive, unknown, not-run, unsupported, or error state may be promoted to `PASS`. Support classifications are not check results. `ASSURED` requires every mandatory condition and evidence gate; PASS counts alone are insufficient. Infrastructure `ERROR` is not automatically a subject-level `FAIL`.

This is a cross-cutting contract implemented through the existing five planes. It creates no sixth plane, second policy engine, evidence authority, execution engine, or verdict authority. QDAS remains the development-assurance lifecycle; RVL remains the sole canonical execution/replay engine.

## Alternatives considered

1. Checker-owned final status — rejected because producers could self-approve malformed or out-of-scope output.
2. One monolithic verifier — rejected because observation, evidence trust, authorization, and policy would not be independently auditable.
3. External orchestrator as final authority — rejected because it moves deterministic decision authority outside Qyrenith's canonical model.
4. One shared status enum for every layer — rejected because support, per-check, aggregate, reproducibility, and infrastructure states have different meanings.

## Consequences

- Every observation is attributable to a producer identity/version and exact scope.
- Evidence validation, qualification, authorization, and verdict evaluation require versioned contracts and independent tests.
- Legacy conversion preserves raw values and provenance; exhaustive mappings derive from actual legacy values. Ambiguous values remain `UNKNOWN`.
- QDAS's canonical event journal and artifact store remain the evidence authority.
- Policy decisions bind to project snapshot, profile, requested/evaluated scope, mandatory inventory, coverage, evidence integrity/freshness, policy version, and evaluator version.
- Extensions cannot self-qualify, self-authorize, rewrite evidence, or issue final verdicts.

## Verification requirements

- Forged checker output cannot select a final per-check or aggregate outcome.
- Malformed, stale, incomplete, out-of-scope, or integrity-invalid evidence cannot satisfy a mandatory gate.
- An extension cannot self-qualify, self-authorize, modify policy, rewrite accepted evidence, or forge a verdict.
- Reports reproduce the stored decision and reference its evidence/coverage records.
- Exhaustive state tests prove non-positive and uncertain states never become `PASS`.
- Aggregate tests prove unmet mandatory conditions prevent `ASSURED`.
- Reproducibility and support classifications cannot be coerced into per-check outcomes.

## Related contracts

- `DEEP_AUDIT_MASTER_ARCHITECTURE.md`
- `AA01_OWNER_DECISION_RECORD.md`
- `ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md`
- `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`
- `EVIDENCE_AND_CONFIDENCE_MODEL.md`
- `QYRENITH_DEVELOPMENT_ASSURANCE_SYSTEM_SPEC.md`
- `REPRODUCIBLE_VERIFICATION_LAB_SPEC.md`

This proposal does not accept all PR #3 requirements or independently authorize implementation.

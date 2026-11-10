# ADR-AA-001: Separate Observation, Evidence Validation, and Assurance Authority

**Status:** RECONCILED PROPOSAL — OWNER ACCEPTANCE REQUIRED  
**Revision date:** 2026-11-10  
**Scope:** Cross-cutting Advanced Assurance authority model for Qyrenith 1.2.0  
**Implementation status:** NOT STARTED

## Context

A checker, worker, adapter, or external provider produces observations within a declared scope. Its output may be incorrect, compromised, stale, incomplete, or outside that scope. Allowing the producer to validate its own evidence or issue the final project decision would create a self-certifying path.

Qyrenith already defines five canonical planes, QDAS as the canonical development-assurance system, RVL as the only execution/replay engine, and a central trust and policy model. Advanced Assurance must strengthen those boundaries rather than create a parallel authority stack.

## Proposed decision

Separate the following responsibilities through explicit, versioned contracts:

1. **Observation producer:** checker, analyzer, worker, adapter, or provider emits raw observations and bounded execution metadata. It cannot declare its own output trusted or issue a final assurance verdict.
2. **Evidence validation:** validates identity, scope, schema, provenance, integrity, freshness, lineage, and required oracle/evidence conditions. Validation does not itself mean that the subject passed.
3. **Policy and outcome evaluation:** maps validated observations to the canonical per-check outcome vocabulary and evaluates the aggregate project-assurance contract using the exact profile, scope, mandatory inventory, coverage, and evidence state.
4. **Reporting:** renders the already-recorded decision and its supporting limitations. It cannot silently recalculate or upgrade a decision.
5. **Independent verification:** supplies independently collected evidence where a requirement demands it; it is not replaced by a worker's self-attestation or by Qyrenith merely repeating its own claim.

The canonical per-check outcomes are `PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, `UNKNOWN`, `NOT_RUN`, `UNSUPPORTED`, and `ERROR`. Aggregate project assurance remains a separate vocabulary: `ASSURED`, `NOT_ASSURED`, `BLOCKED`, `INCONCLUSIVE`, and `PARTIAL`. Reproducibility outcomes and extension support classifications remain separate again. No conversion may upgrade missing, stale, ambiguous, unsupported, blocked, inconclusive, not-run, or error evidence to PASS or ASSURED.

The central authority is implemented within the existing Control and Evidence planes and their shared contracts. This ADR does not create a sixth plane, a second evidence ledger, a second execution engine, or a separate verdict authority.

## Authority constraints

- An observation producer MUST NOT self-qualify, self-authorize, rewrite accepted evidence, or issue the aggregate verdict.
- Evidence validation MUST preserve raw producer output and provenance and MUST distinguish integrity from authenticity and truth.
- Policy evaluation MUST use only validated evidence and a versioned policy/profile identity.
- Aggregate `ASSURED` MUST be impossible if any mandatory check, coverage, evidence, freshness, or trust requirement is unmet.
- A report MUST render the recorded decision, including unsupported and unevaluated scope.
- Extension providers MUST use these same authorities and MUST NOT replace or bypass them.
- A Qyrenith self-check MUST NOT be presented as independent verification of Qyrenith itself.

## Alternatives considered

1. **Checker-owned final status:** rejected; it allows self-certification.
2. **One monolithic verification function:** rejected; it obscures authority boundaries and makes independent testing difficult.
3. **External orchestrator as final authority:** rejected as the canonical model; it would move Qyrenith's final policy decision outside its deterministic control plane. Independent external verification remains valid as evidence.
4. **A separate AA verdict service:** rejected; it would duplicate the canonical Control-plane authority.

## Consequences

- Checker contracts must return observations, not final project assurance.
- Evidence validation, policy evaluation, and reporting require separate conformance tests.
- Legacy status fields require a loss-preserving compatibility mapping.
- QDAS and RVL remain reusable canonical components; AA is a contract across them, not a replacement.
- More explicit evidence and policy metadata is required, but false-green paths become testable.

## Acceptance criteria

- Forged or malformed checker output cannot select a final decision.
- A producer cannot self-qualify or self-authorize.
- Policy evaluation rejects invalid, stale, out-of-scope, or incomplete evidence.
- All eight per-check outcomes and five aggregate states remain type-distinct.
- No missing or unsupported mandatory check can yield `ASSURED`.
- Reports reproduce the recorded decision without recalculating it.
- Extension conformance tests prove that providers cannot bypass central authority.
- Independent verification claims identify the independent actor, environment, scope, and retained evidence.

## Deferred

Exact schemas, package/API/CLI names, evaluator implementation boundaries, and the final test inventory remain implementation-planning work. This proposal does not accept all AA-01 requirements or PR #3 as a whole.

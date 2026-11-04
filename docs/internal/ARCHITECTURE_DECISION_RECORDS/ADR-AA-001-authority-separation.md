# ADR-AA-001: Separate Checker Execution from Final Decision Authority

**Status:** Proposed for AA-01 acceptance  
**Date:** 2026-11-04  
**Scope:** Advanced Assurance core

## Context

A checker or worker observes a property and emits a result. The checker may be incorrect, compromised, stale, misconfigured, or outside the declared scope. If the same component can declare its observation valid and select the final project assurance decision, an invalid result can authorize itself.

The 1.1.0 control plane already treats worker statements as advisory and retains independent validation gates. Advanced Assurance must generalize this principle across every checker family.

## Decision

Checker execution, evidence validation, policy evaluation, and report rendering are separate responsibilities.

- Checkers report observations and bounded execution metadata.
- The evidence validator decides whether a record satisfies the evidence contract.
- The policy evaluator maps validated evidence to policy outcomes.
- The reporter renders the decision record and does not recalculate it.
- No checker or worker receives authority to write a final assurance decision.

## Alternatives considered

1. **Checker-owned final status:** rejected because a checker could self-approve malformed or incomplete output.
2. **Single monolithic verification function:** rejected because discovery, execution, evidence trust, and policy would be difficult to test or audit independently.
3. **External orchestrator as authority:** rejected because it would move final assurance outside Qyrenith's deterministic core.

## Consequences

Positive:
- clear trust boundaries;
- independently testable validation and policy layers;
- consistent semantics across native and external providers;
- worker output remains useful without becoming authoritative.

Costs:
- more explicit contracts and validation steps;
- evidence must be normalized before policy evaluation;
- old workflow status fields may need a compatibility mapping.

## Verification

- contract tests prove checker output cannot select the final decision;
- malformed and forged outputs are rejected;
- policy tests evaluate only validated evidence;
- report consistency tests prove the report uses the recorded decision.

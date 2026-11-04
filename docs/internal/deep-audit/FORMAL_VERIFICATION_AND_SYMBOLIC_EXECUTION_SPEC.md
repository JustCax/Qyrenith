# Formal Verification and Bounded Symbolic Execution Specification

## 1. Objective
Provide native bounded reasoning over explicit contracts and finite state models. Qyrenith must be precise about what was explored and must never imply an unbounded mathematical proof from bounded execution.

## 2. Requirements
- **FV-01 Contract model:** represent preconditions, postconditions, invariants, assumptions, and observable state.
- **FV-02 State exploration:** bounded breadth/depth exploration with explicit state and transition budgets.
- **FV-03 Symbolic values:** support a documented subset of symbolic integer, boolean, enum, and bounded sequence constraints.
- **FV-04 Constraint solving:** implement a native deterministic solver for the supported constraint subset; unsupported expressions return UNKNOWN.
- **FV-05 Counterexamples:** emit minimal reproducible traces where feasible, with input/state sequence and violated invariant.
- **FV-06 Loop bounds:** require explicit bounds or return INCONCLUSIVE when an unbounded loop affects the property.
- **FV-07 Concurrency model:** document supported scheduling/interleaving model and state-space reduction assumptions.
- **FV-08 Assumption tracking:** every assumption is explicit, scoped, and included in the result digest.
- **FV-09 QDAS integration:** use bounded models for selected repair invariants and regression counterexamples.
- **FV-10 Reporting:** distinguish VERIFIED_WITHIN_BOUND, COUNTEREXAMPLE_FOUND, INCONCLUSIVE, UNSUPPORTED, and ANALYZER_FAILURE.

## 3. Soundness boundary
The engine must document the supported language/model fragment and the semantics it actually implements. No unsupported construct may be silently abstracted away. A proof within a finite bound is not a proof for all executions unless the model and completeness argument establish that fact.

## 4. Acceptance
Use hand-calculated small models, contradictory constraints, satisfiable/unsatisfiable cases, boundary arithmetic, overflow semantics, loops, state explosion, and deliberately omitted transitions. Validate counterexample replay and ensure budget exhaustion always produces INCONCLUSIVE rather than PASS.

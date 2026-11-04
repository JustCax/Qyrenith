# Fuzzing and Property Testing Specification

## 1. Objective
Find input-sensitive defects through deterministic generation, invariant checking, shrinking, and metamorphic relations.

## 2. Requirements
- **FP-01 Generators:** typed, bounded generators for supported primitive and structured inputs.
- **FP-02 Seed control:** every run records seed, generator version, constraints, and execution environment.
- **FP-03 Properties:** properties are explicit predicates with stable IDs and failure explanations.
- **FP-04 Shrinking:** deterministic shrink strategies preserve validity constraints and produce replayable minimal cases.
- **FP-05 Metamorphic testing:** encode transformations whose expected relation between outputs is specified.
- **FP-06 Corpus:** bounded corpus import/export with digest validation and provenance.
- **FP-07 Crash isolation:** distinguish target crash, timeout, resource limit, harness failure, and invalid generated input.
- **FP-08 Regression promotion:** minimized failures can become regression fixtures only after review; no automatic VERIFIED knowledge promotion.
- **FP-09 QDAS integration:** generate targeted cases from a failure hypothesis and replay them after repair.
- **FP-10 Safety:** enforce execution budgets, input sizes, output caps, and workspace isolation.

## 3. Determinism
A seed alone is insufficient if generator/runtime versions differ. Persist all relevant versions and constraints. Corpus minimization must be reproducible.

## 4. Acceptance
Test seed replay, generator boundary cases, shrink validity, metamorphic relation violations, harness crashes, timeouts, duplicate corpus entries, malicious corpus payloads, and budget exhaustion. Demonstrate that an unrepeatable failure is reported as inconclusive evidence, not silently discarded.

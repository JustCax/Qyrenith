# Root-Cause and Cross-Module Analysis Specification

## 1. Objective
Connect symptoms across files, modules, dependency edges, build/test events, runtime observations, and historical failure evidence to produce reviewable root-cause hypotheses.

## 2. Requirements
- **RC-01 Unified graph:** represent files, symbols, modules, dependencies, tests, build tasks, APIs, findings, and evidence as typed graph nodes/edges.
- **RC-02 Provenance:** every edge records its source analyzer, version, confidence, and evidence.
- **RC-03 Impact analysis:** compute bounded reverse/forward reachability and identify affected tests and consumers.
- **RC-04 Failure correlation:** correlate shared paths, symbols, timestamps, dependency changes, and common stack frames without asserting causation.
- **RC-05 Hypothesis ranking:** rank candidate causes using explainable factors and preserve alternatives/contradictions.
- **RC-06 Contract analysis:** identify producer/consumer API contract mismatches and version drift.
- **RC-07 Change analysis:** compare baseline and patch graphs; highlight newly introduced and resolved relationships.
- **RC-08 Historical knowledge:** query Failure Intelligence records with exact scope and version compatibility.
- **RC-09 QDAS integration:** create hypotheses from captured build/test/audit failures and feed repair plans.
- **RC-10 Bounds:** cap graph size, traversal depth, path count, and memory; return partial coverage on exhaustion.
- **RC-11 Output:** explain why each hypothesis was selected, what evidence would falsify it, and what observation is needed next.

## 3. Causality discipline
Use labels such as observed association, plausible causal mechanism, and experimentally supported cause. Only a controlled intervention with repeatable evidence can strengthen a causal claim. A correlation score is not a probability unless calibrated.

## 4. Acceptance
Fixtures must include a direct cause, misleading correlated change, multi-cause failure, transitive dependency failure, missing graph edge, cycle, stale history, and resource exhaustion. Verify that incomplete graph coverage lowers confidence and prevents unsupported definitive claims.

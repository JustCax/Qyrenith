# Integrated Reporting and Orchestration Specification

## 1. Objective
Provide one coherent, machine-readable and human-readable view of audit, migration, QDAS, coverage, evidence, and unresolved risk without flattening distinct verification claims.

## 2. Requirements
- **IR-01 Run identity:** every report binds project, revision, snapshot, policy, toolchain, configuration, and run ID.
- **IR-02 Module orchestration:** resolve prerequisites and capability availability before execution; never silently skip a required module.
- **IR-03 Dependency scheduling:** execute independent checks in bounded parallelism only when resource and isolation contracts permit; preserve deterministic aggregation.
- **IR-04 Verdict separation:** show BUILD_VERIFIED, TEST_VERIFIED, STATIC_ANALYSIS_VERIFIED, BEHAVIOR_VERIFIED, and AUDIT_VERIFIED separately.
- **IR-05 Coverage:** include supported/unsupported features, files, rules, scenarios, paths, states, exclusions, and resource truncation.
- **IR-06 Evidence links:** every finding and verdict references evidence IDs, provenance, digest, and collection method.
- **IR-07 Risk aggregation:** aggregate severity and uncertainty without hiding critical findings behind averages or opaque scores.
- **IR-08 Conflict display:** show contradictory knowledge, stale evidence, missing approvals, and blocked dependencies.
- **IR-09 Comparison:** compare two runs by stable finding identity and exact scope; distinguish resolved, introduced, changed, and no-longer-observed findings.
- **IR-10 QDAS lifecycle:** expose failure-to-repair lineage, approval, patch digest, regression status, and safe-stop reason.
- **IR-11 Export:** support bounded canonical JSON plus readable Markdown/text output; redact secrets and sensitive paths according to policy.
- **IR-12 Reproducibility:** reports include exact rerun instructions where safe and permitted.
- **IR-13 Accessibility:** CLI output remains readable without color; machine-readable output is stable and schema-versioned.
- **IR-14 No false green:** incomplete coverage, unsupported mandatory checks, unresolved critical findings, or missing evidence must prevent an overall clean verdict.

## 3. Orchestration policy
The orchestrator builds a dependency DAG from module contracts. Cycles are configuration errors. A required module that is unavailable results in BLOCKED/UNKNOWN, not an implicit pass. Optional modules may be skipped only when policy explicitly marks them optional, and the report must list them.

## 4. Acceptance
Test missing adapters, cyclic prerequisites, parallel failure, nondeterministic completion order, output truncation, secret redaction, changed finding identities, stale evidence, unsupported mandatory checks, and a false-green regression. Verify reports are stable across repeated runs for identical normalized evidence.

# Static and Semantic Analysis Specification

## 1. Objective
Implement native Qyrenith source analysis that detects structural, semantic, data-flow, dependency, and contract defects without executing the target program. The engine must be deterministic for a fixed source snapshot, parser version, rule set, and configuration.

## 2. Pipeline
`DISCOVER → NORMALIZE → PARSE → RESOLVE → BUILD_GRAPHS → ANALYZE → CORRELATE → REPORT`.
Each stage emits typed diagnostics and coverage. Parse failure must not be silently treated as an empty file or clean analysis.

## 3. Requirements
- **SA-01 Source inventory:** bounded, canonical project discovery; explicit include/exclude policy; symlink and generated-file policy; snapshot identity.
- **SA-02 Native parsing:** versioned language frontends with explicit grammar coverage and error recovery. Unsupported syntax is reported.
- **SA-03 Symbol resolution:** declarations, imports, scopes, overloads, visibility, and cross-file references where supported.
- **SA-04 Structural analysis:** unreachable declarations, duplicate/conflicting definitions, invalid control structure, malformed configuration and schema usage.
- **SA-05 Semantic contracts:** type/shape compatibility, API usage, nullability/optionality, resource ownership and declared invariants where the frontend supports them.
- **SA-06 Data-flow analysis:** bounded intra/interprocedural source-to-sink paths, taint propagation, sanitizers, alias limitations, and path evidence.
- **SA-07 Dependency graph:** imports, package manifests, build declarations, generated relationships, and cycle detection.
- **SA-08 Impact analysis:** identify downstream symbols/modules/tests affected by a changed node; disclose incomplete graph edges.
- **SA-09 Rules:** native versioned rule packs with stable IDs, severity, rationale, examples, false-positive guidance, and test fixtures.
- **SA-10 Suppressions:** scoped, expiring, attributable suppressions; report suppressed findings and never hide them from coverage.
- **SA-11 Incremental analysis:** cache only against content digest, parser/rule version, and configuration digest; invalidation must be safe.
- **SA-12 QDAS integration:** analyze baseline and repair diff, identify changed rule outcomes, and detect suppression/config/test changes.
- **SA-13 Output:** stable finding IDs, source spans, evidence references, confidence rationale, and machine-readable report schema.

## 4. Native implementation constraints
Do not copy external analyzer code or rule packs. Build a minimal common intermediate representation and language-specific frontends. Avoid claiming full-language support from token scanning. Each frontend publishes grammar and semantic coverage levels.

## 5. Failure and coverage
Return PARSE_PARTIAL, UNSUPPORTED_SYNTAX, RESOURCE_LIMIT, ANALYZER_FAILURE, or COMPLETE. COMPLETE requires all declared files and mandatory rule groups to have been processed. Findings=0 with incomplete coverage is not a clean pass.

## 6. Acceptance
Fixtures must cover valid and invalid syntax, nested scopes, imports, shadowing, aliasing, data-flow paths, sanitizers, cycles, generated files, symlinks, malformed encodings, huge files, incremental invalidation, and suppression abuse. Mutation fixtures must demonstrate detection of representative defects. All results bind to the exact source snapshot and engine/rule versions.

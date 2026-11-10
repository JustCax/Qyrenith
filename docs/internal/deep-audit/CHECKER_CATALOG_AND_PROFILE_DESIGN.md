# Checker Catalog and Verification Profile Design — Qyrenith 1.2.0

**Status:** DESIGN BASELINE — profile inventory and final budgets DEFERRED  
**Date:** 2026-11-10  
**Scope:** Native and qualified-provider checks across the canonical five planes  
**Implementation:** NOT STARTED

## 1. Purpose and boundaries

Qyrenith needs one deterministic catalog of available checks and one immutable profile-manifest model that defines exactly what a run requests. This design connects the accepted AA-D1 outcome vocabulary, AA-D4 profile model, AA-D6 aggregate assurance model, RVL L0–L5, QDAS evidence lifecycle, and the owner-approved extension/supportability requirements.

This is not a second checker runtime or execution engine. The catalog describes check capabilities; the Control plane plans and authorizes; the Execution plane/RVL runs supported operations; the Evidence plane validates and stores evidence; the Control plane's policy evaluator produces final decisions.

A migration worker registry is not a general diagnostic checker registry. A profile is not a bag of optional plugins. A catalog entry does not prove that a checker is implemented, qualified, supported, or authorized.

## 2. Canonical identities

Every check MUST have:
- stable namespaced `check_id`;
- immutable `check_version`;
- contract/API version;
- owning module/domain and canonical plane mapping;
- implementation identity and digest;
- origin classification (native or qualified provider);
- exact support scope and feature-level limitations;
- input and output schema versions;
- evidence kinds and required provenance;
- deterministic/non-deterministic behavior declaration;
- prerequisites and dependency edges;
- side-effect and permission declaration;
- network requirement declaration;
- minimum/required RVL isolation capabilities;
- resource budget requirements and hard ceilings;
- timeout/cancellation behavior;
- supported outcome mapping and failure semantics;
- freshness/invalidation rules;
- qualification record and conformance-suite identity where provider-backed;
- lifecycle state (active, deprecated, revoked, expired, withdrawn);
- documentation, test fixtures, and acceptance evidence references.

Check IDs and versions are immutable identities. A behavior or contract change requiring different evidence semantics must publish a new version; an in-place edit must not silently alter what an existing profile means.

## 3. Catalog behavior

The catalog is local/offline-first and versioned. Discovery is declarative and non-executing.

The catalog MUST:
1. Parse and validate manifests without importing or launching extension code.
2. Reject malformed identity, duplicate IDs, invalid versions, missing contract references, and contradictory capability declarations.
3. Resolve exact compatibility against project language/domain/platform/runtime/toolchain/feature scope.
4. Distinguish implementation availability from support qualification and per-run authorization.
5. Return explicit resolution states, including unsupported, incompatible, unqualified, stale, revoked, blocked, and qualified/native-supported cases.
6. Resolve duplicate/conflicting providers deterministically using explicit owner policy; never choose by filesystem order or nondeterministic discovery order.
7. Preserve all rejected/ambiguous candidates and reasons in the run plan/evidence.
8. Avoid network access during catalog discovery; remote catalogs are optional and require the separately approved network contract.
9. Invalidate affected qualification and dependent evidence when implementation digest, API version, dependencies, declared scope, conformance suite, or trust status changes.
10. Never allow a check or provider to self-qualify, self-authorize, change policy, write a verdict, or bypass RVL.

Catalog resolution and supportability classifications are separate from check outcomes and aggregate assurance:
- `NATIVE_SUPPORTED`
- `QUALIFIED_PROVIDER`
- `EXPERIMENTAL`
- `PARTIAL`
- `UNSUPPORTED`

These values describe the support relationship for an exact scope. They do not mean PASS, ASSURED, or that a check has run.

## 4. Exact support scope

Every catalog entry and profile binding MUST use explicit scope dimensions where applicable:

- language and language version;
- source/build format and relevant feature set;
- operating system and version;
- architecture;
- runtime/interpreter/VM and version;
- compiler/build tool and version;
- framework, engine, game, mod loader, or protocol and version;
- dependency/toolchain constraints;
- project type and domain;
- optional hardware/runtime capabilities where the check depends on them.

No implicit wildcard support is allowed. A wildcard or version range is permitted only when explicitly represented, justified, tested, and qualified as a range. Missing dimensions mean unknown or not applicable only when the contract says which; they must not silently broaden support.

## 5. Immutable verification profile manifest

A profile is an immutable, versioned manifest. Each release profile version binds:

- profile ID, version, digest, schema version, and owner;
- purpose and assurance claim/non-claims;
- exact included check IDs and versions;
- mandatory vs optional classification per check;
- exact project/domain/platform scope and support constraints;
- prerequisites and dependency graph;
- explicit exclusions and reasons;
- evidence and oracle requirements for each check;
- required support classification and qualification freshness;
- side-effect permissions and network policy;
- required/minimum RVL L0–L5 isolation;
- CPU, memory, process, disk, output, artifact, wall-time, and concurrency budgets;
- scheduling and parallelism rules;
- cancellation and timeout behavior;
- evidence freshness, invalidation, retention, and export rules;
- failure-state and aggregate-assurance policy version;
- evaluator version and compatibility constraints.

A profile manifest is immutable after publication. A change to its check inventory, mandatory/optional status, scope, budget, policy, isolation, evidence/oracle requirement, or retention semantics creates a new profile version and digest.

Run-specific values (project snapshot, resolved support tuple, granted permissions, observed host capabilities, and allocated budgets within profile limits) are bound in a separate immutable run binding. They do not mutate the profile.

## 6. Candidate profile families

The names below are placeholders only and are not accepted profile names or final inventories:

- **Baseline** — candidate for a bounded, low-cost core set.
- **Standard** — candidate for broader static, dependency, configuration, and regression coverage.
- **Deep Audit** — candidate for the broadest qualified local coverage and selected dynamic/security/formal/fuzz checks within strict resource limits.

The exact names, included checks, mandatory/optional assignments, scope, resource budgets, network policy, and release guarantees MUST remain deferred until:
1. the checker catalog and check contracts exist;
2. each check's real execution/resource profile is measured;
3. platform/isolation capability matrices are known;
4. mandatory coverage can be satisfied for the declared support scope;
5. acceptance tests and evidence requirements are complete.

A profile cannot promise a check that is not implemented and qualified for the requested scope. Unsupported optional checks remain visible; unsupported mandatory checks prevent ASSURED.

## 7. Planning and execution lifecycle

For a requested profile:

1. Bind the exact project snapshot and requested scope.
2. Load the immutable profile manifest by ID/version/digest.
3. Resolve every included check against the local catalog and exact support tuple.
4. Validate profile integrity, check identity, API compatibility, qualification, freshness, prerequisites, conflicts, and exclusions.
5. Build a deterministic dependency/scheduling graph.
6. Evaluate requested permissions, network policy, RVL isolation capabilities, and resource budgets.
7. Produce an immutable pre-execution plan showing mandatory/optional checks, unsupported checks, blocked prerequisites, exclusions, and expected evidence.
8. Obtain exact-scope human authorization for side effects.
9. Execute only eligible checks through the central RVL/execution boundary.
10. Normalize raw observations, preserve producer provenance, and validate evidence independently.
11. Produce one per-check outcome for each requested check, including NOT_RUN/UNSUPPORTED/BLOCKED where applicable.
12. Evaluate aggregate project assurance from mandatory conditions, coverage, evidence integrity/freshness, policy and evaluator versions.
13. Emit human and machine reports from the same immutable decision record.

No check may be silently omitted because a provider is absent, a budget is exhausted, or a prerequisite failed. The plan and final report must account for every requested check.

## 8. Outcome semantics

Each requested check resolves to exactly one accepted per-check outcome:

- `PASS`: executed and all declared oracles/evidence gates passed.
- `FAIL`: executed and a subject-level failure was established.
- `BLOCKED`: execution was prevented by policy, authorization, prerequisite, integrity, or isolation gate.
- `INCONCLUSIVE`: evaluation occurred but evidence/oracle/limits did not establish a defensible conclusion.
- `UNKNOWN`: insufficient trustworthy information to classify the check or subject.
- `NOT_RUN`: requested check was not executed; reason is mandatory.
- `UNSUPPORTED`: requested scope/capability is not supported by a qualified implementation.
- `ERROR`: checker/runner/adapter infrastructure failed before a valid subject result could be established.

A low-level execution event may use its narrower execution vocabulary; the profile evaluator maps it to the per-check outcome while preserving raw event status and flags. `ERROR` must not be used as a catch-all for UNKNOWN or unsupported analyzer results.

## 9. Aggregate assurance

Aggregate states remain `ASSURED`, `NOT_ASSURED`, `BLOCKED`, `INCONCLUSIVE`, and `PARTIAL`.

The aggregate record binds exact project snapshot, profile digest, requested/evaluated scope, mandatory/optional inventory, exclusions, per-check outcomes, coverage, evidence integrity/freshness, support/qualification state, policy version, and evaluator version.

Rules:
- Any unmet mandatory condition prevents `ASSURED`.
- A mandatory check that is NOT_RUN, UNSUPPORTED, BLOCKED, INCONCLUSIVE, UNKNOWN, or ERROR cannot satisfy the profile.
- Optional unsupported checks do not automatically block ASSURED only if the immutable profile explicitly marks them optional and the report discloses the omission.
- PARTIAL is not a synonym for ASSURED.
- PASS counts or percentages alone never determine the aggregate state.
- An incomplete requested scope cannot be silently relabelled as a smaller successful scope.

## 10. Resource and scheduling policy

Resource budgets are enforced by the central scheduler and RVL, not trusted to the checker. Each check declares minimum and maximum needs; the profile caps total run budgets. Scheduling must be deterministic for equivalent inputs and policy.

The manifest must define:
- per-check and total wall-time;
- CPU and memory limits where enforceable;
- process/thread and child-process limits;
- input, output, artifact and temporary-storage ceilings;
- concurrency and queue policy;
- retry policy (default none unless deterministic and safe);
- cancellation propagation and cleanup;
- behavior when the host cannot enforce a requested bound.

An unenforceable mandatory limit blocks or makes the affected check unsupported/inconclusive according to policy; it never becomes an unreported best-effort PASS.

## 11. Qualification and lifecycle

Provider-backed checks require current qualification against exact implementation digest, contract version, declared support scope, conformance-suite version/digest, and host/provider capability set.

Qualification is invalidated by relevant changes to code/package digest, contract, dependencies, scope, conformance suite, trust, revocation, or expiry. Native support still requires tests and evidence; the word native does not mean automatically verified.

Deprecation and revocation remain visible. Existing historical evidence is preserved but may become stale for new profile runs.

## 12. Acceptance requirements for the design

Before implementation begins, produce:
- stable check ID/version registry and schema;
- check contract and manifest schema;
- profile manifest and run-binding schema;
- explicit outcome mapping contract;
- exact support tuple and deterministic resolver contract;
- qualification and invalidation contract;
- resource budget and scheduling model;
- profile catalog with exact mandatory/optional inventory;
- positive, negative, boundary, adversarial, compatibility, and cancellation fixtures;
- traceability from each catalog/profile rule to implementation, test, and evidence.

## 13. Open decisions

- Final profile names and number.
- Initial profile inventories and mandatory/optional assignments.
- Exact budgets and concurrency defaults.
- Which checks are mandatory for the first 1.2.0 release.
- Whether any profile includes optional network providers (network remains disabled by default).
- How much of the long-term 27-domain diagnostic envelope is represented in 1.2.0 profiles.
- Exact check package/module boundaries, after the catalog is inventoried.

These decisions remain open until actual checker capabilities and resource measurements exist.

## 14. Related documents

- `AA01_OWNER_DECISION_RECORD.md`
- `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`
- `LANGUAGE_AND_DOMAIN_ADAPTER_SPEC.md`
- `REPRODUCIBLE_VERIFICATION_LAB_SPEC.md`
- `EVIDENCE_AND_CONFIDENCE_MODEL.md`
- `DEEP_AUDIT_MASTER_ARCHITECTURE.md`
- `REQUIREMENT_TRACEABILITY_MATRIX.md`

This design defines no implemented checker registry or published profile and makes no broad support claim.

# Checker Catalog and Verification Resource Model — Qyrenith 1.2.0

**Status:** ARCHITECTURE PLAN — PROFILE INVENTORY NOT YET SELECTED  
**Owner decision basis:** AA-D4, approved 2026-11-10  
**Primary planes:** Control, Analysis, Execution, Knowledge, Evidence  
**Implementation status:** NOT STARTED

## 1. Purpose

Define the catalog and resource model required before user-facing verification profiles can be finalized. A profile is not a label such as "Deep Audit"; it is an immutable, versioned manifest that resolves to exact checker contracts, scope, prerequisites, evidence/oracle requirements, isolation/network policy, resource budgets, and freshness rules.

The catalog must be shared by native checkers and qualified providers. It must not become an extension execution engine or a second verdict authority.

## 2. Checker identity and manifest

Every checker MUST have:
- stable namespaced checker ID;
- checker contract/API version;
- implementation identity and immutable digest;
- producer kind: native, qualified provider, or explicitly experimental;
- exact supported language/domain/platform/runtime/toolchain/version/feature scope;
- input and output schema versions;
- required project facts and prerequisites;
- declared permissions and side-effect classes;
- required RVL isolation level and host capabilities;
- network/install requirements, defaulting to none;
- resource model and hard upper bounds;
- evidence types, provenance requirements, and lineage behavior;
- oracle definition and oracle limitations;
- deterministic/reproducibility characteristics;
- failure and cancellation semantics;
- positive, negative, boundary, adversarial, and compatibility conformance suite;
- lifecycle state, deprecation policy, and qualification expiry/revocation.

A checker ID is not a support claim. The exact manifest digest and support tuple determine what can be evaluated.

## 3. Catalog state versus result state

The catalog describes availability and qualification, not whether a project passed.

Catalog/qualification dimensions must remain separate from the eight per-check outcomes and five aggregate assurance states. At minimum distinguish:
- discovered declaration;
- schema-valid declaration;
- compatible exact scope;
- qualification pending;
- qualified;
- expired or revoked;
- incompatible;
- unavailable;
- experimental;
- unsupported.

A checker can be qualified for one exact tuple and unsupported for another. A qualified checker can still return FAIL, BLOCKED, INCONCLUSIVE, UNKNOWN, NOT_RUN, UNSUPPORTED, or ERROR for a particular run. Qualification never implies PASS.

## 4. Exact scope resolution

Support matching must consider every applicable dimension, including:
- language and language version;
- operating system and architecture;
- runtime/interpreter/compiler version;
- framework/engine/mod-loader version;
- build system and plugin versions;
- dependency/API versions;
- feature flags and relevant configuration;
- checker contract and implementation version.

Wildcard support must not be inferred. A manifest must explicitly state which dimensions are not applicable and why. If the requested tuple is not covered by a qualified manifest, the result is explicit UNSUPPORTED or UNKNOWN according to whether lack of support is established or knowledge is incomplete.

Provider resolution must be deterministic. Duplicate IDs, conflicting capabilities, incompatible versions, and ambiguous provider selection must be surfaced as conflicts, not resolved by installation order or network discovery.

## 5. Checker lifecycle

Proposed lifecycle:
1. **Declared:** manifest exists; no trust implied.
2. **Discovered:** declaration parsed without executing provider code.
3. **Validated:** schema, identity, digest, dependencies, and scope are structurally valid.
4. **Qualified:** independent conformance suite passed for the exact manifest digest and support tuple.
5. **Available:** required host/toolchain capabilities are present for this run.
6. **Selected:** immutable profile explicitly includes the checker.
7. **Authorized:** all required side effects have exact scope-bound approval.
8. **Executed:** RVL records the actual bounded execution.
9. **Evaluated:** evidence validator and policy evaluator produce the per-check outcome.
10. **Expired/revoked/deprecated:** future use is blocked or requires requalification; historical records remain immutable.

No state transition may be inferred from file presence or a provider's own assertion.

## 6. Resource model

Each checker declares both a **hard budget** and an **expected-cost profile**. Hard budgets are enforced by the central scheduler/RVL; expected cost is advisory and must not be used as a substitute for hard enforcement.

Required budget dimensions:
- wall-clock duration;
- CPU time or bounded work units;
- memory;
- process count and child-process policy;
- input bytes/files/records;
- output bytes/findings;
- artifact count and total artifact bytes;
- network bytes/endpoints, always zero unless separately approved;
- concurrency slots;
- temporary disk/workspace bytes;
- recursion/depth/state-space bounds;
- cancellation grace period and cleanup budget.

Resource declarations must include:
- minimum viable budget;
- recommended budget;
- maximum permitted budget;
- scaling behavior by project-size class;
- whether partial output is useful and how it is labelled;
- deterministic truncation/stop behavior;
- resource-exhaustion outcome and evidence.

Resource exhaustion cannot produce PASS. Depending on the contract and whether execution began, it produces BLOCKED or INCONCLUSIVE with partial evidence and exact limit metadata.

## 7. Profile manifest model

A profile is immutable and versioned. It includes:
- profile ID, version, digest, and human-readable label;
- requested project/domain scope;
- exact mandatory and optional checker IDs plus pinned versions/digests;
- prerequisites and dependency graph;
- explicit exclusions and reasons;
- required evidence/oracles per checker;
- isolation level and authorization policy per checker class;
- network/install policy;
- resource budgets and aggregate run budget;
- concurrency, scheduling, priority, cancellation, and safe-stop rules;
- freshness and evidence reuse/invalidation rules;
- behavior for every non-PASS outcome;
- aggregate assurance policy and mandatory-coverage denominator;
- supported platform matrix and unsupported-scope disclosure.

Changing checker inventory, versions, scope, exclusions, budgets, or policy creates a new profile version/digest. Existing run records remain bound to the original profile.

## 8. Candidate profile tiers — not yet approved

Potential UX aliases such as Baseline, Standard, and Deep Audit remain candidates only.

- A minimal read-only profile should prioritize deterministic, low-cost native checks and never execute project-controlled code.
- A broader profile may include additional qualified checks only where prerequisites, evidence, resource budgets, and host enforcement are available.
- The most comprehensive profile may include expensive dynamic, fuzz, formal, security, and domain-specific checks, but must expose exact exclusions, resource ceilings, and unsupported scope.

Do not publish final profile names or claim relative coverage until the checker catalog is populated and measured against representative project fixtures.

## 9. Scheduling and aggregate resource governance

The scheduler must:
- resolve the immutable profile before execution;
- compute dependency order deterministically;
- reserve aggregate and per-check resource ceilings;
- prevent concurrent execution from exceeding host limits;
- support cancellation and safe-stop without losing accepted evidence;
- avoid running checks whose prerequisites are blocked;
- record skipped/blocked checks as NOT_RUN/BLOCKED/UNSUPPORTED with reason;
- distinguish scheduler/infrastructure ERROR from subject FAIL;
- retain exact actual resource consumption and limit events.

The aggregate project-assurance evaluator must use mandatory inventory and coverage, not PASS counts. A profile run is not ASSURED when mandatory checks were skipped, unsupported, stale, blocked, or inconclusive.

## 10. Acceptance criteria

- Catalog discovery is non-executing and deterministic.
- Exact support tuples reject unsupported versions and implicit wildcard matches.
- Qualification is bound to immutable implementation digest and conformance evidence.
- Expiry, revocation, incompatibility, and provider conflicts fail closed.
- Profile manifests are immutable, versioned, digest-bound, and reproducible.
- All budget dimensions have positive and adversarial tests.
- Resource exhaustion never becomes PASS/ASSURED.
- Cancellation and partial results preserve event/evidence lineage.
- No provider can add itself to a mandatory profile or change policy.
- Reports disclose exact requested/evaluated scope, exclusions, and unsupported coverage.

## 11. Deferred work

The exact checker inventory, final profile names, check budgets, scheduling algorithms, schema/API/CLI surfaces, and supported platform matrix remain deferred until native checker contracts and representative workload measurements exist. This plan does not claim a checker catalog or profile runtime is implemented.

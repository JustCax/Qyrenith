# Extensibility and Supportability Specification — Qyrenith 1.2.0

**Status:** OWNER-APPROVED ARCHITECTURAL REQUIREMENT — IMPLEMENTATION NOT STARTED  
**Approval date:** 2026-11-10  
**Target:** Qyrenith 1.2.0 architecture and long-term ecosystem  
**Parent:** The canonical five-plane architecture and the Language and Domain Adapter Specification.

## 1. Objective

Qyrenith MUST support broad, controlled, long-term extensibility. Adding a language, framework, game engine, mod loader, build system, database, protocol, diagnostic method, knowledge pack, or optional provider MUST NOT require a parallel architecture or weaken central trust, evidence, execution, authorization, or verdict controls.

Extensibility is an architectural requirement, not a claim that every ecosystem is already supported and not permission to load arbitrary third-party code with ambient authority.

## 2. Architectural placement

The extension ecosystem is cross-cutting and maps onto the five canonical planes:

- **Control:** registration policy, capability negotiation, authorization, lifecycle, scheduling, and verdict evaluation.
- **Analysis:** language frontends, domain analyzers, diagnostic packs, compatibility analyzers, and normalized facts.
- **Execution:** build/test providers, checker workers, isolation providers, and bounded external-tool invocation.
- **Knowledge:** versioned compatibility packs, failure knowledge, rule metadata, and domain-specific knowledge.
- **Evidence:** extension identity, provenance, qualification records, raw/normalized observations, lineage, and support claims.

No extension category creates a sixth plane. Extensions MUST NOT introduce a second execution engine, evidence ledger, policy authority, or final verdict authority.

## 3. Extension categories

The contract MAY support, subject to qualification:
1. Native language frontends and semantic models.
2. Build-system, compiler, test-runner, and toolchain integrations.
3. Game-engine, mod-loader, framework, runtime, platform, and domain adapters.
4. Diagnostic/checker modules and domain-specific diagnostic packs.
5. Versioned knowledge, compatibility, vulnerability, and failure-information packs.
6. Optional external-tool providers and protocol integrations.
7. Host isolation and execution-capability providers.
8. Evidence exporters, report renderers, and least-privilege integrations.

A category is a contract family, not a permission grant. Each extension declares exactly which capabilities it implements and requests.

## 4. Extension identity and contract

Every extension MUST declare a stable globally namespaced ID, name, category, publisher identity claims, extension and API versions, immutable implementation/package digest, provenance, exact dependencies, compatible Qyrenith/host matrix, applicable language/domain/platform/framework/loader/build-tool/protocol versions, feature-level capabilities and limitations, input/output schema versions, evidence types, requested permissions, network needs, resource ceilings, lifecycle state, deprecation metadata, and qualification reference.

Names, signatures, package metadata, or registry presence alone do not establish trust, qualification, or support.

## 5. Discovery, registration, and qualification

Discovery MUST be non-executing. Finding a package or parsing its manifest MUST NOT run provider code. Registration and installation MUST NOT grant trust, authorization, qualification, or support.

The lifecycle keeps these states separate:

`DECLARED → DISCOVERED → VALIDATED → QUALIFICATION_PENDING → QUALIFIED`

Authorization, execution, and verification are separate runtime events. Qualification binds the exact implementation digest, API contract, dependencies, host/scope matrix, conformance-suite version, evidence, reviewer/authority, and expiry. A changed digest, API, dependency, permission set, or qualified scope invalidates or triggers review of qualification and dependent evidence. Revocation and expiry fail closed.

## 6. Supportability model

Support is multidimensional. Each claim binds to an exact tuple of applicable Qyrenith/extension versions, language/version, OS/architecture/runtime/toolchain, framework/game engine/mod loader/build system/compiler/protocol versions, project type, and feature/capability set. A non-applicable dimension is explicit; a missing dimension MUST NOT silently mean all versions.

Canonical support classifications:

| Classification | Meaning |
|---|---|
| `NATIVE_SUPPORTED` | Qyrenith-owned implementation qualified for the exact declared scope. |
| `QUALIFIED_PROVIDER` | Optional provider qualified for the exact scope and contract. |
| `EXPERIMENTAL` | Available for controlled evaluation; not a stable support claim. |
| `PARTIAL` | Only a declared subset of requested features or versions is qualified. |
| `UNSUPPORTED` | No qualified implementation covers the requested scope. |

These are support classifications, not per-check outcomes, aggregate assurance decisions, or reproducibility outcomes. A support classification never means a check passed. Reports MUST disclose supported, partial, experimental, unsupported, unknown, stale, and excluded scope. Broad ecosystem labels MUST NOT conceal missing version or feature coverage.

## 7. Qualification and conformance

A qualified extension MUST pass a versioned conformance suite covering, as applicable: valid/malformed declarations; positive, negative, boundary, regression, and adversarial fixtures; schema/protocol compatibility; deterministic normalization; exact scope matching; unsupported feature behavior; resource limits, cancellation, timeouts, and bounded outputs; provenance and digest integrity; permission enforcement; authority-escalation attempts; isolation and cleanup; expiry/revocation/upgrade/rollback; and integration with central evidence and verdict handling.

Raw provider output MUST be retained where policy permits, alongside normalized output, provider identity, transformation version, and evidence lineage. Provider output remains untrusted until validated.

## 8. Trust, permissions, and execution

Extensions MUST NOT self-qualify, self-authorize, alter central policy or aggregate verdict rules, weaken mandatory coverage, mint/rewrite/suppress canonical evidence, self-certify independent verification, bypass central execution/isolation, or silently access networks, install dependencies, mutate target projects, or access secrets.

Executable extensions receive least-privilege, scope-bound permissions and resource budgets. Side effects require authenticated authorization and host-enforced isolation appropriate to the operation. If the host cannot enforce the requested boundary, execution remains propose-only or is blocked/unsupported. Network remains disabled by default under the approved AA-01 decision.

## 9. Compatibility, conflicts, and lifecycle

Capability negotiation uses explicit required/optional capabilities and exact compatible contract versions. Missing required capabilities fail closed; missing optional capabilities remain visible.

Duplicate identities, incompatible providers, ambiguous resolution, dependency cycles, and conflicting claims produce deterministic conflict records. Provider selection MUST NOT be nondeterministic or silently widen scope.

Lifecycle states include proposed, declared, discovered, validated, qualification-pending, qualified, deprecated, revoked, expired, and removed. Transitions retain provenance and evidence. Deprecation includes a replacement path or explicit end-of-support date where applicable. Removal MUST NOT erase historical evidence or rewrite prior qualification decisions.

## 10. Catalog and distribution

The core MUST operate without a remote registry, remote package source, paid service, or network. A local/offline-first catalog is the baseline. Remote registries MAY be optional providers under explicit network policy, provenance verification, allowlists, and owner authorization.

The contract supports reproducible export/import of manifests, packages, qualification records, and evidence references. Registry availability MUST NOT be required to re-evaluate retained local evidence.

## 11. Acceptance criteria

The extension foundation is incomplete until implementation and independent evidence demonstrate:
1. Non-executing discovery and safe parsing of untrusted manifests.
2. Stable identity, digest/provenance validation, and contract-version negotiation.
3. Exact multidimensional support matching without implicit wildcards.
4. Separation of support classifications from check, aggregate, and reproducibility outcomes.
5. Qualification, revocation, expiry, and requalification after identity/dependency changes.
6. Deterministic provider resolution and conflict reporting.
7. Least-privilege authorization and central host-enforced isolation for executable providers.
8. No extension can alter central policy, evidence authority, or final verdicts.
9. Offline operation without remote registries or paid services.
10. Positive, negative, boundary, adversarial, compatibility, resource-exhaustion, and regression suites.
11. Complete provenance, support-scope, evidence-lineage, and limitation reporting.
12. Agreement among docs, schemas, CLI, package manifests, and compatibility matrix.

## 12. Non-claims and release discipline

This specification does not claim that an SDK, plugin loader, registry, package manager, or any provider already exists. It does not promise support for all languages, engines, platforms, or versions in 1.2.0. Every individual support claim requires exact scope and independent qualification evidence. Delivery remains incremental and acceptance-gated.

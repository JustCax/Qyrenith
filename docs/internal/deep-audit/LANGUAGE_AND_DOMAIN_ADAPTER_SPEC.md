# Language and Domain Adapter Specification

## 1. Objective
Define an extensible contract for native language frontends, build-system integrations, platform/domain analyzers, and optional external tools without hard-coding a finite list of ecosystems.

## 2. Adapter contract
An adapter declares stable ID, version, implementation digest, supported language/domain/version scope, capabilities, input/output schemas, resource profile, evidence types, and limitations. Discovery is non-executing. Registration never implies qualification or support.

## 3. Requirements
- **LA-01 Capability discovery:** discover adapters without launching them; invalid declarations remain visible as BLOCKED.
- **LA-02 Exact scope:** language version, platform, loader, framework, build tool, and toolchain dimensions are independently represented.
- **LA-03 Parser contract:** frontends provide normalized syntax/semantic structures and source-span mapping.
- **LA-04 Analyzer contract:** domain adapters expose typed facts, rules, and evidence rather than opaque pass/fail claims.
- **LA-05 Build/test adapters:** declare commands, test inventory, environment needs, and result normalization.
- **LA-06 Versioning:** adapter compatibility is bound to exact adapter/protocol version and implementation digest.
- **LA-07 Qualification:** qualification requires a versioned conformance suite, result digest, reviewer, scope, and expiry.
- **LA-08 Trust separation:** discovered, declared, qualified, authorized, executed, and verified remain separate.
- **LA-09 Optional external tools:** external engines are optional providers, never required runtime dependencies; command execution requires explicit policy.
- **LA-10 Native-first:** core supported language/domain behavior must be implemented natively; adapters cannot silently delegate mandatory semantics to external products.
- **LA-11 Unknown domains:** unknown domains may be represented and inspected generically but cannot be labeled supported without executable evidence.
- **LA-12 QDAS integration:** QDAS consumes adapter capability and qualification data and checks adapter changes against conformance fixtures.

- **LA-13 Adapter trust:** adapter manifests and qualification records discovered in a project are untrusted declarations. They cannot authorize execution or establish QUALIFIED status without explicit local approval and independently validated implementation/conformance evidence.

## 4. Extension ecosystem and supportability

The adapter contract is one entry point into a broader, controlled extension ecosystem. Categories MAY include native language frontends, build/test integrations, domain analyzers, diagnostic packs, knowledge packs, checker providers, isolation providers, evidence exporters, report integrations, and optional external-tool adapters. These categories share qualification, trust, versioning, scope, and evidence rules; they do not create independent policy or verdict authorities.

An extension MUST declare stable identity, publisher/provenance claims, exact implementation digest, contract/API version, dependencies, requested capabilities/permissions, resource ceilings, supported host matrix, and a machine-readable support manifest. Discovery MUST be non-executing. Installation or registration MUST NOT grant trust, authorization, or support status.

Canonical support classifications:
- `NATIVE_SUPPORTED`: Qyrenith-owned implementation qualified for the exact declared scope.
- `QUALIFIED_PROVIDER`: optional provider qualified for the exact scope and contract.
- `EXPERIMENTAL`: available for controlled evaluation, not a stable support claim.
- `PARTIAL`: only declared features or versions are qualified.
- `UNSUPPORTED`: no qualified implementation covers the requested scope.

These are support classifications, not per-check outcomes or aggregate assurance states. They MUST NOT be conflated. Each support claim binds to an exact tuple including applicable language/platform/domain version, OS/architecture/runtime, framework/loader/build-tool version, adapter version, and feature/capability set. Irrelevant dimensions are explicitly not applicable; they are never silently wildcarded.

Qualification MUST include positive, negative, boundary, adversarial, compatibility, resource-bound, and regression fixtures; a versioned conformance-suite identity; raw and normalized results; evidence digests; reviewer/authority; exact qualified scope; and expiry/revalidation triggers. Breaking API/protocol changes require a new major contract version or an explicit compatibility bridge. Deprecation and removal require lifecycle metadata and migration guidance.

Extensions MUST NOT modify central policy, mint authorization, self-qualify, self-verify, rewrite canonical evidence, or issue final aggregate verdicts. Executable providers run only through central execution and isolation contracts. Absence, incompatibility, expiry, failure, or insufficient scope remains visible in coverage and reporting.

A registry/catalog MAY be local and offline-first. Remote catalogs and package sources are optional, network-disabled by default, and subject to provenance, allowlist, approval, and integrity controls. The core MUST remain usable without a remote registry or paid service.

## 5. Compatibility policy
Adapters must declare exact supported ranges and unsupported features. Version-family guesses are not accepted as compatibility evidence. Capability negotiation must fail closed when required features are missing.

## 6. Acceptance
Test malformed manifests, duplicate IDs, digest substitution, protocol mismatch, scope widening, expired qualification, non-executing discovery, optional tool absence, and an unknown domain. Verify that unknown domain visibility does not become a support claim.

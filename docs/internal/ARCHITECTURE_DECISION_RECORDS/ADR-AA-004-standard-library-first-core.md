# ADR-AA-004: Standard-Library-First Core with Qualified Optional Providers

**Status:** RECONCILED PROPOSAL — OWNER ACCEPTANCE REQUIRED  
**Revision date:** 2026-11-10  
**Scope:** Core runtime dependencies, external tools, extension providers, and portability  
**Implementation status:** NOT STARTED

## Context

Qyrenith must remain locally useful, offline-capable, and independent of hosted AI services. Mandatory dependencies increase installation friction, platform variation, supply-chain exposure, licensing obligations, and maintenance cost. At the same time, specialized compilers, scanners, test runners, game-engine integrations, and domain tools can substantially expand diagnostic coverage.

The owner has approved extensibility and supportability as first-class architectural requirements. This does not mean arbitrary third-party code may be loaded with ambient authority or that provider presence implies support.

## Proposed decision

The Qyrenith core remains standard-library-first. A new mandatory runtime dependency requires a separate ADR that documents:
- the exact normative requirement not adequately met by the standard library or existing native implementation;
- alternatives considered, including a native implementation and optional provider;
- package identity, immutable version, digest, provenance, publisher/trust model, and license;
- supported Python, OS, architecture, and runtime matrix;
- maintenance, vulnerability, and supply-chain risks;
- data handling, permissions, network, and execution boundary;
- deterministic behavior and failure semantics;
- behavior when the dependency is absent, incompatible, revoked, or unavailable;
- migration, rollback, and reproducible packaging implications.

External tools and integrations MAY be exposed through optional, versioned provider contracts. Providers must declare exact capability and support scopes, identity, provenance, dependency constraints, permissions, and resource needs. Discovery must be non-executing. Installation or registration does not imply qualification, authorization, or supported status.

Provider outputs are untrusted observations. They must be normalized and validated by Qyrenith's central evidence and policy contracts. Providers cannot independently issue PASS/ASSURED, self-qualify, bypass RVL isolation, access the network by default, or create a parallel execution/evidence/verdict authority.

Support claims use the canonical support classifications `NATIVE_SUPPORTED`, `QUALIFIED_PROVIDER`, `EXPERIMENTAL`, `PARTIAL`, and `UNSUPPORTED`, bound to exact multidimensional version/feature scopes. These classifications are not per-check outcomes or aggregate assurance states.

## Offline-first and network behavior

The core and mandatory first-release path must operate without network access. Network is disabled by default. Remote catalogs or providers are optional and require a separate owner-approved threat model and explicit per-run authorization. No remote provider is required to obtain a valid local result for a profile whose declared mandatory checks are locally supported.

## Alternatives considered

1. **Add a broad framework immediately:** rejected; it increases the trusted computing base before a proven requirement exists.
2. **Never allow external tools/providers:** rejected; this would unnecessarily constrain future domain and platform coverage.
3. **Allow opportunistic undeclared imports or tool discovery:** rejected; it makes installation and runtime behavior non-deterministic.
4. **Load arbitrary extensions in-process with ambient permissions:** rejected; it bypasses least privilege and host-enforced isolation.

## Consequences

- The core remains small, portable, and useful without hosted services or optional tools.
- Advanced capability can grow through qualified providers and versioned domain packs.
- Some feature/platform combinations will initially remain PARTIAL, EXPERIMENTAL, or UNSUPPORTED.
- Provider absence or failure remains explicit and cannot be converted to zero findings or PASS.
- Dependency additions become auditable and require reproducible packaging and compatibility evidence.
- The extension ecosystem shares the canonical five planes and central trust/evidence/policy/execution authorities.

## Acceptance criteria

- Clean installation and core operation succeed without optional providers.
- Optional provider absence is explicit and does not silently remove mandatory checks.
- Provider discovery does not execute provider code.
- Provider identity, digest, provenance, version, license, scope, and dependencies are validated.
- Provider output cannot self-certify or alter central policy/evidence/verdict state.
- Unsupported provider/platform combinations remain visible.
- Network remains disabled by default.
- Dependency additions include license, supply-chain, compatibility, and failure-path tests.
- Core and supported provider contracts pass the declared platform matrix.

## Deferred

The final extension SDK/API, package distribution mechanism, registry/catalog transport, and per-provider qualification suites remain implementation-planning work. This proposal does not approve arbitrary extension loading or claim ecosystem support is already implemented.

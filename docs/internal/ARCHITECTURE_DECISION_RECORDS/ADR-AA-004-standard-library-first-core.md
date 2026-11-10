# ADR-AA-004: Keep the Core Standard-Library-First and Providers Optional

**Status:** PROPOSED — reconciled with owner-approved AA-01 decision directions; ADR acceptance pending  
**Original proposal date:** 2026-11-04  
**Reconciliation date:** 2026-11-10  
**Scope:** Python runtime dependencies, native engines, optional tools, extension providers, and offline operation

## Context

Qyrenith must remain useful locally and offline without requiring a hosted service, AI account, external scanner, or provider installation. Mandatory dependencies can increase installation friction, platform variance, supply-chain exposure, licensing obligations, maintenance cost, and the trusted computing base.

However, first-class extensibility includes language frontends, build/test integrations, domain adapters, diagnostic/knowledge packs, isolation providers, and optional external tools. Standard-library-first must not prevent extensibility or force every specialist compiler/tool to be reimplemented in the core.

## Decision proposal

The core SHOULD remain Python-standard-library-first for mandatory runtime dependencies. First-party native Qyrenith components are preferred for core logic and normalized contracts. Optional external tools and extensions MAY be supported behind versioned, qualified, least-privilege contracts and central authorization/execution/evidence boundaries.

A new mandatory runtime dependency requires a separate owner-reviewed ADR documenting:
- the exact accepted requirement not met by the standard library or existing first-party implementation;
- alternatives, including native implementation and optional provider;
- license, provenance, publisher, and maintenance status;
- supported Python/OS/architecture/runtime/packaging matrix;
- supply-chain, update, vulnerability, and reproducibility risks;
- data access, network behavior, permissions, and isolation;
- failure behavior when absent, incompatible, stale, or compromised;
- migration, rollback, and package-size consequences.

External tools/providers are optional, not hidden prerequisites. Their identity, version, digest/provenance, declared scope, qualification, permissions, and limitations are recorded. Their output is untrusted until validated. A provider cannot independently authorize a critical `PASS`, qualify itself, or bypass central policy.

Extensibility remains first-class through versioned contracts, capability negotiation, exact multidimensional support manifests, conformance suites, provenance, qualification/revocation/expiry/requalification, local/offline-first deterministic catalogs, least-privilege permissions, and central RVL execution/isolation. Support states are `NATIVE_SUPPORTED`, `QUALIFIED_PROVIDER`, `EXPERIMENTAL`, `PARTIAL`, and `UNSUPPORTED`.

Network access is disabled by default. The first 1.2.0 release must not depend on network-required mandatory checks. Optional network providers remain unavailable unless the separate owner-approved per-run network authorization contract is satisfied.

This ADR governs dependency policy, not the implementation language of every internal subsystem. It does not prohibit future owner-approved dependencies when evidence justifies the trade-off.

## Alternatives considered

1. Mandatory broad framework immediately — rejected because it expands trusted/compatibility surface before measured need exists.
2. Never allow external tools/extensions — rejected because specialist tools can provide useful observations.
3. Arbitrary installed plugins with ambient permissions — rejected because installation is not qualification or authorization.
4. Implement every ecosystem-specific capability natively in core — rejected as an unbounded maintenance burden; shared native foundations plus qualified packs are more supportable.
5. Require hosted services or network registries — rejected because offline-first operation and default network denial are required.

## Consequences

- A clean core installation works without optional providers or AI services.
- Some language/domain/tool combinations remain explicitly unsupported until native support or a qualified provider exists.
- Extension growth is governed by contracts and conformance, not arbitrary code loading or undocumented support claims.
- Dependency additions are auditable and have an owner and rollback path.
- Shared contracts support a broad ecosystem without making every provider mandatory.
- Dependency policy is checked against package manifests, imports, release contents, and supported-platform tests.

## Verification requirements

- Clean installation and core tests succeed without optional providers.
- Provider absence, incompatibility, revocation, expiry, malformed output, and crash are explicit and never a successful zero-finding result.
- Providers match exact support tuples and qualification records.
- Providers cannot self-qualify, self-authorize, bypass RVL, rewrite evidence, or issue final verdicts.
- Network-denial tests prove default offline-first behavior.
- Every mandatory dependency has an approved ADR plus license/provenance/platform/security review.
- Package/import tests prove optional providers are not accidentally mandatory.
- The supported platform matrix includes clean core installation.

## Related contracts

- `DEEP_AUDIT_MASTER_ARCHITECTURE.md`
- `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`
- `LANGUAGE_AND_DOMAIN_ADAPTER_SPEC.md`
- `RESEARCH_AND_STANDARDS_ALIGNMENT.md`
- `SECURITY_AND_SUPPLY_CHAIN_AUDIT_SPEC.md`

This proposal accepts no particular provider, adds no mandatory dependency, and does not claim the extension runtime is implemented.

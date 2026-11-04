# ADR-AA-004: Keep the Core Standard-Library-First

**Status:** Proposed for AA-01 acceptance  
**Date:** 2026-11-04  
**Scope:** Qyrenith core dependencies and provider integrations

## Context

Qyrenith is intended to run locally and remain useful without a hosted service, AI account, or external scanner. Additional dependencies can increase install friction, platform variation, supply-chain exposure, licensing obligations, and maintenance cost.

Some verification capabilities may benefit from mature external tools. Those tools should not become hidden mandatory requirements of the core.

## Decision

The core remains standard-library-first. A new mandatory runtime dependency requires an explicit ADR documenting:
- exact requirement not met by the standard library or existing code;
- license and provenance;
- supported Python and platform matrix;
- maintenance and supply-chain risks;
- data and permission boundary;
- alternatives considered;
- behavior when the dependency is unavailable.

External tools are optional providers behind explicit, validated contracts. Their results are labelled with provider identity and version and cannot independently authorize a critical PASS.

## Alternatives considered

1. **Add a broad framework immediately:** rejected because it increases trust and compatibility surface before requirements are proven.
2. **Never allow external tools:** rejected because specialized compilers, scanners, and test runners are valuable verification sources.
3. **Allow undeclared imports opportunistically:** rejected because install behavior and runtime guarantees would become unpredictable.

## Consequences

- some advanced capabilities may initially be unsupported;
- provider failures remain visible;
- dependency decisions become auditable;
- the core stays useful in AI-less and offline workflows.

## Verification

- clean installation works without optional providers;
- optional provider absence is reported explicitly;
- dependency additions include license, version, and trust-boundary tests;
- core tests run on the declared platform matrix.

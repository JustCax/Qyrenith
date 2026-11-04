# Universal Knowledge and Compatibility Specification

## 1. Objective
Maintain reusable, versioned knowledge about APIs, platforms, languages, toolchains, dependencies, migration transitions, and failure patterns without treating unverified observations as facts.

## 2. Knowledge identity
Every claim is scoped by subject, source identity, target identity, dimensions, version ranges, platform/loader/framework/toolchain, provenance, and validity. Canonical keys must be stable and collision-resistant.

## 3. Requirements
- **UK-01 Typed records:** schema-versioned records for compatibility, API changes, dependency constraints, known failures, and migration mappings.
- **UK-02 Provenance:** source locator, author/provider, observed timestamp, content digest, collection method, reviewer, and evidence references.
- **UK-03 Status lifecycle:** OBSERVED, INFERRED, UNKNOWN, VERIFIED, CONFLICTED, STALE with explicit transition rules.
- **UK-04 Scope exactness:** no widening a claim beyond its evidenced versions/platforms.
- **UK-05 Conflict handling:** preserve contradictory claims and block decisions in overlapping scope until resolved.
- **UK-06 Freshness:** expiry and revalidation policy based on source volatility and tool/API versions.
- **UK-07 Import/export:** strict canonical interchange, duplicate-key rejection, size bounds, schema validation, digest checks.
- **UK-08 Offline-first:** no implicit network; retrieval providers are opt-in and their results remain untrusted until reviewed.
- **UK-09 Query:** deterministic matching and explicit partial-match/unknown results.
- **UK-10 Failure Intelligence:** QDAS failure/repair observations enter as OBSERVED and require independent review for VERIFIED.
- **UK-11 Migration planner:** compatibility knowledge may qualify typed migration edges only when exact source/target scope and evidence are valid.
- **UK-12 Auditability:** preserve superseded claims and reasoned lifecycle history.

## 4. Separation of knowledge domains
Migration compatibility knowledge and general audit/failure knowledge may share provenance primitives but must retain separate schemas and semantics. A build failure observed in one environment does not prove an API incompatibility universally.

## 5. Acceptance
Test scope mismatch, version boundary inclusivity, conflicting providers, expired/future-dated claims, stale tool versions, duplicate IDs, malformed canonical input, offline mode, import idempotence, and failure-knowledge non-promotion.

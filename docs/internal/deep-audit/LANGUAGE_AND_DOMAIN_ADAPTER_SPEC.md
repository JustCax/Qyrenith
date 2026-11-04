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

## 4. Compatibility policy
Adapters must declare exact supported ranges and unsupported features. Version-family guesses are not accepted as compatibility evidence. Capability negotiation must fail closed when required features are missing.

## 5. Acceptance
Test malformed manifests, duplicate IDs, digest substitution, protocol mismatch, scope widening, expired qualification, non-executing discovery, optional tool absence, and an unknown domain. Verify that unknown domain visibility does not become a support claim.

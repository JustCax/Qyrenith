# Audit Maturity and Coverage Model

## 1. Purpose
Provide honest, multidimensional reporting of how deeply Qyrenith can audit a specific project revision and environment.

## 2. Dimensions
Report separate values for:
- language syntax and semantic coverage;
- domain/platform/framework coverage;
- source and dependency inventory coverage;
- static rule coverage;
- data-flow/path coverage;
- dynamic scenario and oracle coverage;
- formal state/property bounds;
- fuzz input/property coverage;
- security and supply-chain coverage;
- reproducibility and isolation level;
- evidence provenance/freshness;
- meta-audit quality and independent verification.

Do not collapse these into one universal percentage unless the weighting and denominators are published and the multidimensional values remain visible.

## 3. Maturity levels
- **L0 — Registered:** identity/domain is recognized; no claim of analysis support.
- **L1 — Inventory:** project files and declared metadata can be enumerated with known limits.
- **L2 — Structural:** supported syntax/configuration is parsed and structurally analyzed.
- **L3 — Semantic:** declared semantic, dependency, and selected data-flow analyses are operational.
- **L4 — Verified checks:** repeatable dynamic/static checks and explicit evidence oracles pass for the stated scope.
- **L5 — Independently validated:** end-to-end project workflow is reproduced in an independent environment with reviewed coverage and retained evidence.

Levels are scoped to a project, revision, language/domain versions, and enabled capabilities. A domain-wide maturity label requires a representative benchmark suite and cannot be inferred from one fixture.

## 4. Requirements
- **MC-01** Compute maturity from explicit capability evidence, not registry labels.
- **MC-02** Publish denominators, exclusions, unsupported syntax, and skipped checks.
- **MC-03** Keep each coverage dimension independently visible.
- **MC-04** Lower maturity when evidence expires, tool versions change, or coverage becomes incomplete.
- **MC-05** Distinguish missing capability from failed capability.
- **MC-06** Bind reports to exact revision, environment, adapter versions, and evidence digests.
- **MC-07** QDAS must not inflate maturity after a repair unless required checks and baseline coverage are preserved.
- **MC-08** Meta-audit benchmarks validate maturity claims.

## 5. Acceptance
Test partial parsers, missing test oracles, excluded files, stale evidence, changed toolchain, failed checks, unsupported domains, and single-fixture overgeneralization. Ensure that zero findings with zero semantic coverage never receives a high maturity rating.

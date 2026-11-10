# Diagnostic Intelligence Expansion Specification — Qyrenith 1.2.0

**Status:** PROPOSED REQUIREMENTS — OWNER REVIEW REQUIRED  
**Target:** 1.2.0 capability envelope; delivery is dependency- and evidence-gated  
**Parent:** `DEEP_AUDIT_MASTER_ARCHITECTURE.md` and `UNIVERSAL_SOFTWARE_INTELLIGENCE_ARCHITECTURE.md`

## 1. Objective

Define the complete diagnostic capability envelope: project understanding, language intelligence, security, dependencies, architecture, testing, runtime/production, repair, reporting, APIs/protocols, infrastructure, databases, resilience, compatibility, build/release, accessibility, privacy, documentation consistency, cost/resource efficiency, AI-agent assurance, project knowledge graph, attack-surface analysis, change impact, continuous assurance, forensics and domain packs.

A requirement is a target contract, not an implementation claim. Current inventory status is in `DIAGNOSTIC_CAPABILITY_COVERAGE_MATRIX.md`.

## 2. Design principles

1. Native-first core parsing, normalized models, policy, graph reasoning, evidence lineage, coverage and verdict logic.
2. Evidence-first findings with reproducible lineage from input to observation to decision.
3. Exact support scope by language/version/platform/framework/loader/protocol/toolchain/feature.
4. UNKNOWN, UNSUPPORTED, PARTIAL, INCONCLUSIVE and BLOCKED are first-class.
5. Cross-domain correlation across code, dependencies, runtime, data, infrastructure, tests and documentation.
6. No false green when mandatory coverage, evidence, parsing or oracles are incomplete.
7. Read-only analysis by default; dynamic checks and side effects require bounded execution and policy.
8. Analyzer quality measured with labeled fixtures, mutation tests, false-positive tests, independent oracles and benchmark disclosure.
9. Research informs design; do not copy third-party source, proprietary rules or unlicensed datasets.
10. Capability packs compose shared engines; they need not map one-to-one to executable modules.

## 3. Shared finding contract

Every domain emits normalized records compatible with the Evidence and Confidence Model. A finding identifies stable ID/schema, project/revision/snapshot and exact scope, domain/rule/analyzer version, observed facts versus inference/hypothesis, severity/rationale, source span or typed graph object, supporting and contradicting evidence, confidence/calibration, coverage/exclusions/unsupported constructs, freshness/supersession, remediation and side-effect classification, and reproduction manifest or reason unavailable.

Preserve raw provider evidence and provenance. Finding identity is stable only when issue and scope are equivalent; identity-defining scope changes must produce a different identity.

## 4. Capability domains and requirements

### Diagnostic Core (DI-001–DI-003)

**Scope:** PARTIAL

- Define normalized diagnostic records with stable IDs, schema versions, severity, category, subject scope, source locations and evidence references.
- Normalize provider output without losing raw observations, provider identity or transformation lineage.
- Deduplicate only proven-equivalent findings; retain conflicts and superseded observations.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Language Intelligence (DI-004–DI-006)

**Scope:** PARTIAL

- Declare grammar, language-version and syntax coverage; unsupported constructs remain visible.
- Build symbol, scope, import, type/shape and cross-file reference models where supported.
- Perform bounded data/control-flow analysis with explicit alias, reflection, macro and dynamic-language limits.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Security Intelligence (DI-007–DI-009)

**Scope:** PARTIAL

- Maintain versioned security rules with rationale, severity and false-positive fixtures.
- Trace supported untrusted inputs through transformations to sensitive sinks with sanitizer assumptions.
- Report exploitability assumptions, reachable paths, missing coverage and residual risk.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Dependency Intelligence (DI-010–DI-012)

**Scope:** PARTIAL

- Inventory supported manifests and lockfiles with exact ecosystem, package, version and source.
- Match advisories against exact affected ranges; report source provenance and freshness.
- Exchange SBOM/VEX records; distinguish declared license from legal conclusions.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Architecture Intelligence (DI-013–DI-015)

**Scope:** NOT_STARTED

- Build typed project/component dependency graphs with edge provenance and completeness.
- Detect configured architecture violations, cycles, unstable dependencies and change-coupling hotspots.
- Track architectural fitness functions against versioned policy and explain each violation.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Testing Intelligence (DI-016–DI-018)

**Scope:** PARTIAL

- Inventory suites, test-to-code links, fixtures, oracles, configuration and exclusions.
- Measure mutation sensitivity, property/fuzz coverage and deterministic replay separately.
- Detect test deletion, weakening, quarantine, flaky outcomes and oracle gaps.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Runtime Intelligence (DI-019–DI-021)

**Scope:** PARTIAL

- Capture runtime/toolchain identity, process lifecycle, bounded outputs and resource limits.
- Observe supported runtime state, exceptions, resource ownership and lifecycle leaks.
- Correlate runtime observations with source symbols, tests, environment and evidence lineage.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Repair Intelligence (DI-022–DI-024)

**Scope:** PARTIAL

- Tie bounded repair plans to exact failures, snapshots, invariants, affected scope and rollback.
- Require authenticated approval and host-enforced isolation before side effects; otherwise propose-only.
- Re-run original and baseline checks; detect test/config weakening and preserve full lineage.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Reporting & Integrations (DI-025–DI-027)

**Scope:** PARTIAL

- Emit schema-versioned reports separating findings, coverage, uncertainty, evidence and verdicts.
- Expose integrations through explicit least-privilege versioned protocols.
- Compare runs by stable finding identity and exact scope; retain suppressed, unsupported and stale items.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### API & Protocol Intelligence (DI-028–DI-030)

**Scope:** NOT_STARTED

- Inventory endpoints, operations, schemas, versions and producers/consumers.
- Check contract compatibility, authorization boundaries, validation and protocol-specific risks.
- Compare API surfaces across revisions; identify breaking, undocumented and shadow endpoints.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Infrastructure & Environment Intelligence (DI-031–DI-033)

**Scope:** PARTIAL

- Parse supported infrastructure/configuration formats into typed resources and relationships.
- Detect insecure defaults, privilege expansion, drift and mutable references.
- Bind infrastructure findings to deployment/runtime evidence and disclose parser coverage.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Observability & Production Intelligence (DI-034–DI-036)

**Scope:** NOT_STARTED

- Ingest telemetry with semantic conventions, source identity and time-quality metadata.
- Correlate traces, logs, metrics, deployments and code revisions without asserting causation.
- Evaluate SLO and incident evidence with retention, privacy and sampling gaps disclosed.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Database & Data Integrity Intelligence (DI-037–DI-039)

**Scope:** NOT_STARTED

- Inventory supported schemas, migrations, queries, ORM mappings and database versions.
- Analyze query plans, indexing, N+1 patterns, transaction boundaries and concurrency hazards.
- Verify migration safety, data invariants, rollback and data-loss risk using disposable fixtures.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Reliability & Resilience Intelligence (DI-040–DI-042)

**Scope:** PARTIAL

- Model service dependencies, failure domains, retry/timeout budgets and recovery contracts.
- Run approved fault-injection scenarios only in bounded disposable environments.
- Verify recovery, idempotency, data integrity and bounded degradation against explicit oracles.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Compatibility & Portability Intelligence (DI-043–DI-045)

**Scope:** PARTIAL

- Represent compatibility as exact multidimensional tuples, not broad ecosystem labels.
- Compare declared support with observed builds/tests across OS, architecture and toolchain matrices.
- Report tested, inferred, unsupported and unknown combinations separately.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Build, Artifact & Release Intelligence (DI-046–DI-048)

**Scope:** PARTIAL

- Capture exact build inputs, toolchain, environment, dependency resolution, commands and output digests.
- Verify artifact identity, manifests, signatures/attestations and provenance against explicit trust policy.
- Compare independently rebuilt outputs using byte-level or semantic equivalence as appropriate.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Accessibility & UX Quality Intelligence (DI-049–DI-051)

**Scope:** NOT_STARTED

- Discover UI surfaces and supported accessibility metadata with exact framework/version coverage.
- Check applicable accessibility rules and interaction paths; distinguish automation from human evaluation.
- Compare accessibility regressions and identify criteria requiring human review.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Privacy & Data Governance Intelligence (DI-052–DI-054)

**Scope:** PARTIAL

- Identify sensitive-data classes and data-flow boundaries using configurable policies.
- Detect secret exposure, unsafe logs, excessive collection, retention and transfer risks without persisting secret values.
- Report data lifecycle, redaction effectiveness and policy assumptions without legal conclusions.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Documentation & Specification Intelligence (DI-055–DI-057)

**Scope:** NOT_STARTED

- Inventory docs, specs, ADRs, code symbols, schemas and examples with revision identity.
- Detect stale claims, missing requirement links, broken references and documented behavior absent from implementation.
- Execute supported examples in isolated fixtures and compare documented contracts to observed behavior.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Cost & Resource Efficiency Intelligence (DI-058–DI-060)

**Scope:** PARTIAL

- Capture benchmark context, resource budgets, workload identity and measurement uncertainty.
- Identify bottlenecks and compare optimization candidates with controlled repeated baselines.
- Estimate cost only from explicit rates/usage evidence; disclose assumptions and avoid unsupported savings claims.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### AI & Agent Code Assurance (DI-061–DI-063)

**Scope:** PARTIAL

- Capture agent identity/version, task, tool/action events, permissions and exact before/after snapshots.
- Compare actual changes/actions against approved intent, constraints, allowed paths and verification obligations.
- Detect test gaming, hidden changes, instruction injection, self-certification and missing independent checks.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Universal Project Knowledge Graph (DI-064–DI-066)

**Scope:** PARTIAL

- Define versioned node/edge schemas with stable identity, scope and provenance.
- Support bounded explainable queries and cross-domain joins without merging incompatible claim semantics.
- Incrementally update graph snapshots and detect stale, missing, contradictory or invalidated edges.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Attack Surface & Threat Intelligence (DI-067–DI-069)

**Scope:** PARTIAL

- Inventory externally reachable and privileged surfaces from supported source/config/runtime evidence.
- Build bounded attack paths across identities, inputs, services, dependencies and trust boundaries.
- Prioritize threats with explicit likelihood/impact assumptions and counterevidence.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Change Impact & Regression Prediction (DI-070–DI-072)

**Scope:** PARTIAL

- Compute impact from source, dependency, API, configuration and test graph edges.
- Predict candidate regression areas with explainable features and calibrated metrics where supported.
- Compare predicted and observed impact after change; prediction is never proof.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Continuous Assurance Engine (DI-073–DI-075)

**Scope:** PARTIAL

- Define policies, triggers, cadence, scope, resource ceilings and owner controls.
- Invalidate or re-run evidence when source, toolchain, dependencies, policy or environment changes.
- Maintain historical assurance state without false green; scheduler is opt-in and owner-controlled.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Software Forensics & Root Cause Engine (DI-076–DI-078)

**Scope:** PARTIAL

- Build provenance-backed timelines across commits, builds, deployments, telemetry, dependencies and findings.
- Rank hypotheses with supporting/contradicting evidence and falsifying experiments.
- Promote causality only after controlled intervention/replay; preserve alternatives and uncertainty.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Domain-Specific Diagnostic Packs (DI-079–DI-081)

**Scope:** PARTIAL

- Define domain packs over common schemas with exact platform/version scope.
- Qualify packs with positive, negative, boundary, adversarial and compatibility fixtures.
- Keep domain knowledge separate while exposing common findings/evidence and unsupported states.

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

## 5. Cross-domain correlation

Examples include source symbol → API endpoint → auth policy → runtime trace → incident; dependency version → advisory → reachable code → deployed artifact; schema migration → query behavior → test oracle → data invariant; infrastructure permission → service identity → exposed endpoint → attack path; agent task → tool action → changed file → removed test → QDAS event; code change → affected tests → benchmark delta → release provenance; documentation claim → requirement → implementation symbol → acceptance evidence.

Every join exposes graph edges and confidence. Missing edges and unsupported semantic links remain visible. Graph traversal is not proof of causality.

## 6. Shared quality and acceptance

Every domain supplies supported input/version matrix; positive, negative, boundary and adversarial fixtures; independently reviewed expected outcomes for critical rules; false-positive/near-miss fixtures; mutation tests; parser/analyzer failure and resource-exhaustion tests; determinism/replay tests where expected; benchmark definitions/denominators; blind spots; stable schemas and evidence lineage.

Report precision, recall, mutation detection, false-positive rate, runtime, memory and coverage separately. Do not collapse them into an opaque score.

## 7. Delivery and maturity

Use the existing L0–L5 maturity model, scoped to project/domain/version and evidence. A 1.2.0 support claim requires exact scope, executable implementation, positive/negative tests, evidence, limitations and independent acceptance. A spec, adapter manifest, directory, test name or external tool is insufficient.

## 8. Requirement IDs

DI-001 through DI-081 are stable, three per domain in the order listed. Append new IDs; never recycle IDs after deferral or removal.

## 9. Non-claims

This catalog does not claim all 27 domains are implemented, all languages/platforms are supported, all defects are detectable, absence of findings proves security, regressions can always be predicted, or arbitrary projects can be automatically repaired.

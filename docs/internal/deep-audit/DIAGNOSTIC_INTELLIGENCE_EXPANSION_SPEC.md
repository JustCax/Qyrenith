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

**Scope:** A normalized, versioned finding and observation model with stable identity, scope and provenance.

- Normalize provider output without losing raw observations, provider identity or transformation lineage.
- Deduplicate only proven-equivalent findings; retain conflicts and superseded observations.
- qyrenith_engine/qdas/; qyrenith_engine/analysis.py

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Language Intelligence (DI-004–DI-006)

**Scope:** Native frontends, syntax and semantic understanding, symbols, types and data/control flow.

- Build symbol, scope, import, type/shape and cross-file reference models where supported.
- Perform bounded data/control-flow analysis with explicit alias, reflection, macro and dynamic-language limits.
- Native frontend packages; existing analysis entrypoints

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Security Intelligence (DI-007–DI-009)

**Scope:** Source security, taint, vulnerability patterns, secure configuration and threat reasoning.

- Trace supported untrusted inputs through transformations to sensitive sinks with sanitizer assumptions.
- Report exploitability assumptions, reachable paths, missing coverage and residual risk.
- Trust/boundary primitives; deep native analyzer not established

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Dependency Intelligence (DI-010–DI-012)

**Scope:** Direct/transitive dependency identity, advisory matching, integrity, licenses and SBOM/VEX.

- Match advisories against exact affected ranges; report source provenance and freshness.
- Exchange SBOM/VEX records; distinguish declared license from legal conclusions.
- qyrenith_engine/migration/knowledge.py; intelligence foundations

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Architecture Intelligence (DI-013–DI-015)

**Scope:** Component boundaries, dependency direction, coupling, layering, cycles and constraints.

- Detect configured architecture violations, cycles, unstable dependencies and change-coupling hotspots.
- Track architectural fitness functions against versioned policy and explain each violation.
- No dedicated architecture engine identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Testing Intelligence (DI-016–DI-018)

**Scope:** Test discovery, quality, mutation, property, fuzz, differential and regression testing.

- Measure mutation sensitivity, property/fuzz coverage and deterministic replay separately.
- Detect test deletion, weakening, quarantine, flaky outcomes and oracle gaps.
- Existing test runner, QDAS and benchmark foundations

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Runtime Intelligence (DI-019–DI-021)

**Scope:** Controlled execution, runtime state, resource lifecycle, dynamic behavior and diagnostics.

- Observe supported runtime state, exceptions, resource ownership and lifecycle leaks.
- Correlate runtime observations with source symbols, tests, environment and evidence lineage.
- qyrenith_engine/execution.py; dynamic_audit_qdas.py

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Repair Intelligence (DI-022–DI-024)

**Scope:** Root-cause-informed repair proposals, controlled execution, diff review, rollback and independent re-verification.

- Require authenticated approval and host-enforced isolation before side effects; otherwise propose-only.
- Re-run original and baseline checks; detect test/config weakening and preserve full lineage.
- qyrenith_engine/qdas/repair.py; qyrenith_engine/qdas/lineage.py

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Reporting & Integrations (DI-025–DI-027)

**Scope:** Human/machine reports, CLI/API/IDE/CI integration, stable export and trend comparison.

- Expose integrations through explicit least-privilege versioned protocols.
- Compare runs by stable finding identity and exact scope; retain suppressed, unsupported and stale items.
- qyrenith.py; qyrenith_engine/analysis.py; QDAS CLI

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### API & Protocol Intelligence (DI-028–DI-030)

**Scope:** REST, GraphQL, gRPC, WebSocket, message protocols, schemas, auth and compatibility.

- Check contract compatibility, authorization boundaries, validation and protocol-specific risks.
- Compare API surfaces across revisions; identify breaking, undocumented and shadow endpoints.
- No dedicated API/protocol analyzer identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Infrastructure & Environment Intelligence (DI-031–DI-033)

**Scope:** IaC, containers, orchestration, CI/CD, host configuration, drift and environment identity.

- Detect insecure defaults, privilege expansion, drift and mutable references.
- Bind infrastructure findings to deployment/runtime evidence and disclose parser coverage.
- Execution environment capture; existing config checks to verify

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Observability & Production Intelligence (DI-034–DI-036)

**Scope:** Logs, traces, metrics, profiles, SLOs, incidents and deployment/runtime correlation.

- Correlate traces, logs, metrics, deployments and code revisions without asserting causation.
- Evaluate SLO and incident evidence with retention, privacy and sampling gaps disclosed.
- No production telemetry engine identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Database & Data Integrity Intelligence (DI-037–DI-039)

**Scope:** Schema, query, transaction, migration, data-flow, consistency and performance analysis.

- Analyze query plans, indexing, N+1 patterns, transaction boundaries and concurrency hazards.
- Verify migration safety, data invariants, rollback and data-loss risk using disposable fixtures.
- No dedicated database analyzer identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Reliability & Resilience Intelligence (DI-040–DI-042)

**Scope:** Fault tolerance, timeout/retry, idempotency, backpressure, failover and recovery.

- Run approved fault-injection scenarios only in bounded disposable environments.
- Verify recovery, idempotency, data integrity and bounded degradation against explicit oracles.
- Timeout/resource/recovery primitives; no full resilience engine identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Compatibility & Portability Intelligence (DI-043–DI-045)

**Scope:** Cross-version, OS, CPU, runtime, compiler, framework, loader, API and dependency compatibility.

- Compare declared support with observed builds/tests across OS, architecture and toolchain matrices.
- Report tested, inferred, unsupported and unknown combinations separately.
- Migration model, knowledge and planner

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Build, Artifact & Release Intelligence (DI-046–DI-048)

**Scope:** Build integrity, reproducibility, provenance, artifact verification and release hygiene.

- Verify artifact identity, manifests, signatures/attestations and provenance against explicit trust policy.
- Compare independently rebuilt outputs using byte-level or semantic equivalence as appropriate.
- Existing build/release verification and package checks; workflow files absent by owner request

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Accessibility & UX Quality Intelligence (DI-049–DI-051)

**Scope:** WCAG-oriented accessibility, interaction, keyboard, assistive technology and usability regressions.

- Check applicable accessibility rules and interaction paths; distinguish automation from human evaluation.
- Compare accessibility regressions and identify criteria requiring human review.
- No dedicated accessibility analyzer identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Privacy & Data Governance Intelligence (DI-052–DI-054)

**Scope:** Sensitive-data flow, secret handling, retention, consent, minimization and privacy controls.

- Detect secret exposure, unsafe logs, excessive collection, retention and transfer risks without persisting secret values.
- Report data lifecycle, redaction effectiveness and policy assumptions without legal conclusions.
- Redaction and bounded evidence controls; no full privacy engine identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Documentation & Specification Intelligence (DI-055–DI-057)

**Scope:** Code/documentation/ADR/contract consistency, freshness, examples and traceability.

- Detect stale claims, missing requirement links, broken references and documented behavior absent from implementation.
- Execute supported examples in isolated fixtures and compare documented contracts to observed behavior.
- No dedicated docs/spec analyzer identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Cost & Resource Efficiency Intelligence (DI-058–DI-060)

**Scope:** CPU, memory, I/O, network, build time, cloud/API spend and energy/resource efficiency.

- Identify bottlenecks and compare optimization candidates with controlled repeated baselines.
- Estimate cost only from explicit rates/usage evidence; disclose assumptions and avoid unsupported savings claims.
- Resource limits and performance benchmark foundations

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### AI & Agent Code Assurance (DI-061–DI-063)

**Scope:** Agent intent, tool actions, code changes, instruction compliance, provenance and adversarial behavior.

- Compare actual changes/actions against approved intent, constraints, allowed paths and verification obligations.
- Detect test gaming, hidden changes, instruction injection, self-certification and missing independent checks.
- Agent integration guidance and QDAS capture primitives

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Universal Project Knowledge Graph (DI-064–DI-066)

**Scope:** Typed graph of files, symbols, APIs, tests, dependencies, runtime, findings, evidence and history.

- Support bounded explainable queries and cross-domain joins without merging incompatible claim semantics.
- Incrementally update graph snapshots and detect stale, missing, contradictory or invalidated edges.
- Migration knowledge and QDAS evidence lineage; no unified graph engine identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Attack Surface & Threat Intelligence (DI-067–DI-069)

**Scope:** Assets, entry points, trust boundaries, exposed services, attack paths and threat models.

- Build bounded attack paths across identities, inputs, services, dependencies and trust boundaries.
- Prioritize threats with explicit likelihood/impact assumptions and counterevidence.
- Security/trust primitives; dedicated attack-surface graph not identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Change Impact & Regression Prediction (DI-070–DI-072)

**Scope:** Pre-change impact, affected components/tests/contracts, risk prediction and post-change evidence.

- Predict candidate regression areas with explainable features and calibrated metrics where supported.
- Compare predicted and observed impact after change; prediction is never proof.
- Migration diff/snapshot and analysis foundations

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Continuous Assurance Engine (DI-073–DI-075)

**Scope:** Evidence freshness, scheduled/event-driven checks, policy gates and continuous drift detection.

- Invalidate or re-run evidence when source, toolchain, dependencies, policy or environment changes.
- Maintain historical assurance state without false green; scheduler is opt-in and owner-controlled.
- QDAS event ledger and CLI verification; no scheduler/monitor identified

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Software Forensics & Root Cause Engine (DI-076–DI-078)

**Scope:** Timeline reconstruction, incident correlation, provenance, causal hypotheses and reproducible experiments.

- Rank hypotheses with supporting/contradicting evidence and falsifying experiments.
- Promote causality only after controlled intervention/replay; preserve alternatives and uncertainty.
- QDAS diagnosis/hypotheses and lineage foundations

**Acceptance:** positive, negative, boundary, adversarial and unsupported-scope fixtures; stable evidence IDs; explicit exclusions; bounded resource use; reproducible comparisons.

### Domain-Specific Diagnostic Packs (DI-079–DI-081)

**Scope:** Versioned domain packs for Minecraft, Unity, Unreal, Godot, Roblox, web, backend, mobile, data and others.

- Qualify packs with positive, negative, boundary, adversarial and compatibility fixtures.
- Keep domain knowledge separate while exposing common findings/evidence and unsupported states.
- Minecraft/migration foundations and Node/Rust domain tests

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

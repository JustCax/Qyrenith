# Qyrenith Universal Software Intelligence Architecture — 1.2.0 Extension Proposal

**Status:** PROPOSED DESIGN — OWNER REVIEW REQUIRED  
**Target:** Qyrenith 1.2.0  
**Relationship:** Extends and maps onto `DEEP_AUDIT_MASTER_ARCHITECTURE.md`; does not silently replace or amend its accepted implementation direction.  
**Implementation claim:** Design only.

## 1. Mission

Qyrenith is intended to become a universal, evidence-led software intelligence and assurance platform. It should understand projects, diagnose defects and risks, verify claims, improve software safely, support migration and compatibility work, and govern consequential actions through an auditable control plane.

Depth is more important than a long checklist. A finding must connect to the code or system object, dependency and execution context, supporting and contradicting evidence, uncertainty, and possible safe action. The system must also state what it cannot inspect.

Qyrenith is not a code-generating AI, a linter aggregator, a build system, a dependency manager, or an unrestricted autonomous agent. External tools may supplement native engines through explicit adapters, but core models, policy, normalization, graph reasoning, evidence lineage, coverage accounting and verdict logic remain native.

## 2. Six capability pillars over the existing five planes

The current master architecture's five planes remain canonical:
1. **Control:** CLI, policy, approvals, orchestration, lifecycle and verdict aggregation.
2. **Analysis:** native parsers, analyzers, dependency/impact graphs, security checks and domain adapters.
3. **Execution:** bounded processes, reproducible lab, isolated workspaces, tests/fuzz/formal runners and controlled repair.
4. **Knowledge:** versioned compatibility/failure knowledge, provenance, scope, validity, conflicts and review.
5. **Evidence:** immutable records, digests, lineage, confidence, coverage and reproducible artifacts.

The six product pillars are a user-facing capability grouping, not six replacement runtime planes:

| Capability pillar | Primary planes | Responsibility |
|---|---|---|
| Project Intelligence | Analysis + Knowledge + Evidence | Understand project identity, structure, semantics, contracts, dependencies, domains and history. |
| Diagnostic & Optimization Intelligence | Analysis + Execution + Evidence | Find defects, risks and bottlenecks; compare improvement hypotheses. |
| Verification & Testing Intelligence | Execution + Evidence + Analysis | Test claims through static, dynamic, property, fuzz, formal and differential methods. |
| Migration & Improvement Intelligence | Analysis + Knowledge + Execution + Control | Plan and validate migrations, repairs, refactors and optimizations under authority. |
| Evidence & Assurance Intelligence | Evidence + Knowledge + Control | Preserve provenance, freshness, confidence, independent verification and auditability. |
| Control Plane & Orchestration | Control + all planes | Enforce permissions, policy, isolation, budgets, scheduling and recovery. |

## 3. Operating modes

All modes share project identity, capability registry, evidence schemas, policy engine and module contracts.

### Deep Audit
Capture an immutable project/revision baseline; inventory source, tests, dependencies, build, configuration, APIs, infrastructure, documentation and domain surfaces; resolve capability/prerequisite availability; execute dependency-ordered bounded checks; report findings, coverage, exclusions, unsupported areas, conflicts, stale evidence and resource truncation; retain a rerunnable manifest. Mandatory unsupported scope prevents an overall clean verdict.

### Targeted Analysis
Accept a finding, file, symbol, component, API, dependency, runtime symptom, change or incident. Expand scope through known graph edges and explain why each node is included. Run the minimum sufficient checks, disclose what was not checked, and preserve the exact target/expanded scope for replay.

### Continuous Assurance
React to approved source, dependency, toolchain, deployment, policy and evidence-expiry events. Reuse evidence only while scope, freshness, tool versions, configuration and trust remain valid. Re-run invalidated/impacted checks and periodically reconcile. Scheduling, notifications and network access are opt-in and owner-controlled.

## 4. Universal project model

Represent, where discovered and supported: repositories/revisions/snapshots; files/resources/configuration; languages/grammars/symbols/modules/packages/services; APIs/protocols/schemas/database objects; dependencies/toolchains/runtimes; tests/fixtures/properties/fuzz corpora/oracles; build tasks/artifacts/releases/attestations; infrastructure/deployments/environments; telemetry/incidents; documentation/specifications/decisions/requirements; findings/hypotheses/repairs/migrations/approvals/evidence.

Every node and edge is typed, versioned, scoped and provenance-bearing. Missing edges are distinguishable from proven absence. Graph construction is bounded and incremental.

## 5. Diagnostic reasoning contract

Each finding carries stable identity/schema, project/revision/snapshot, exact scope, category/severity, affected object, observed facts separated from inference/hypothesis, source span or graph object, supporting and contradicting evidence, analyzer/rule version, assumptions/confidence/calibration, coverage/exclusions, freshness, remediation options, side-effect classification and reproduction instructions or a reason they are unavailable.

Numeric confidence is not probability without calibration on a documented representative dataset. Correlation is not causation. Zero findings with incomplete coverage is not a clean result.

## 6. Verification and assurance contract

Keep observation, inference, hypothesis, planned action, authorization, execution, verification and independent verification distinct. Existing verdicts remain scoped and separate: BUILD_VERIFIED, TEST_VERIFIED, STATIC_ANALYSIS_VERIFIED, BEHAVIOR_VERIFIED and AUDIT_VERIFIED. Reproducibility, portability and coverage are separate dimensions, not a replacement green badge.

A claim is VERIFIED only when its declared oracle, scope, evidence, freshness and independence requirements are met. Qyrenith must not certify its own implementation solely from its own output.

## 7. Improvement lifecycle

Optimization is a first-class mission alongside defect detection:

`BASELINE → BOTTLENECK HYPOTHESIS → MEASUREMENT PLAN → APPROVED EXPERIMENT → CANDIDATE CHANGE → REPEATABLE BENCHMARK → REGRESSION CHECK → EVIDENCE-BASED DECISION`

Optimize against declared objectives/constraints: latency, throughput, memory, CPU, I/O, network, build time, energy, cost, maintainability, reliability and accessibility. Every recommendation identifies baseline, workload, environment, measurement noise, trade-offs, confidence and rollback. If the measured difference is within noise, report INCONCLUSIVE.

## 8. Safety invariants

- Discovery is non-executing.
- Project-controlled files cannot grant trust or authorization.
- Declared is not qualified; qualified is not authorized; authorized is not executed.
- Workspace copying is not process/OS isolation.
- Digest proves byte identity, not truth or signer identity.
- External tools require explicit policy and bounded execution.
- Repair, migration, network, installation, Git writes and publication require exact-scope approval.
- Missing host-enforced isolation means propose-only for side-effecting workers.
- Secrets are redacted before persistence; raw retention is policy-controlled.
- Resource exhaustion, unsupported semantics and missing oracles are non-pass states.
- Recovery is evidence-recorded and idempotent where possible.

## 9. Capability catalog and release boundary

The 27 domains are specified in `DIAGNOSTIC_INTELLIGENCE_EXPANSION_SPEC.md`; they are a target capability envelope, not 27 isolated products. Shared primitives include project inventory/snapshots, frontends, typed graphs, policy/execution contracts, common finding/report schemas, reproducible lab, independent oracles, versioned knowledge, adapter qualification, coverage and meta-audit.

The current 1.2.0 delivery order remains: documentation baseline, migration safety completion, QDAS, fourteen existing capability modules, integrated acceptance. The 27 domains do not imply all are fully implemented in one release. Owner-approved scope must identify shared foundations, executable vertical slices, unsupported/partial domains and evidence required for every shipped claim.

## 10. Acceptance of this proposal

Before acceptance, cross-review against the master, QDAS, fourteen capability specifications, migration integration and evidence model; resolve schema/authority/dependency conflicts; confirm six-pillar mapping; approve 1.2.0 vertical slices; record owner approval. This proposal is not an accepted ADR and not implementation evidence.

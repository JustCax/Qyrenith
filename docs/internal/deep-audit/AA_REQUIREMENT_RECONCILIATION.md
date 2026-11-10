# Advanced Assurance Requirement Reconciliation — PR #3 to Qyrenith 1.2.0

**Status:** REVIEW BASELINE — owner disposition pending; all 70 source requirements remain PROPOSED  
**Source:** PR #3, `feature/advanced-assurance-aa01-mainline`, source head `0ee2edb9fe136bba729483e56d5c450421fa6e80`  
**Target:** `feature/1.2.0-universal-migration-core`  
**Review date:** 2026-11-10  
**Scope:** Requirement semantics, overlap, architecture ownership, and integration disposition; no implementation or merge authorization.

## 1. Executive recommendation

Retain the 70 stable AA requirement IDs as a proposed cross-cutting assurance contract, but do not accept PR #3 wholesale and do not create a separate AA product/runtime.

The requirements are broadly useful and align with the Qyrenith 1.2.0 direction. Most should remain as shared pipeline guarantees mapped onto the existing five planes, QDAS, RVL, the evidence model, the migration foundation, and the fourteen capability modules. Their presence must not create duplicate implementations of discovery, checker execution, evidence storage, policy, isolation, or reporting.

**Recommended disposition:** retain all 70 IDs for traceability; reconcile wording and ownership; consolidate duplicate implementation targets with existing requirements; defer individual acceptance until the owner reviews the resulting baseline. No AA requirement is marked ACCEPTED by this document.

## 2. Inventory and priority counts

| Requirement group | IDs | Count | P0 | P1 | Recommended disposition |
|---|---|---:|---:|---:|---|
| Project discovery/model | AA-REQ-PROJ-001..006 | 6 | 4 | 2 | RETAIN; map to Analysis/Knowledge/Evidence and existing project snapshot/discovery |
| Verification planning | AA-REQ-PLAN-001..006 | 6 | 5 | 1 | RETAIN; map to Control, immutable profiles and deterministic planning |
| Checker contract/runtime | AA-REQ-CHK-001..008 | 8 | 7 | 1 | RETAIN; use RVL and central execution; no second checker runner |
| Evidence/provenance | AA-REQ-EVD-001..008 | 8 | 7 | 1 | RETAIN; consolidate under QDAS journal/artifact store/evidence model |
| Policy/decisions | AA-REQ-POL-001..007 | 7 | 6 | 1 | RETAIN WITH WORDING RECONCILIATION; use approved eight-state and aggregate models |
| Security/trust/execution | AA-REQ-SEC-001..010 | 10 | 9 | 1 | RETAIN; map to security, migration authorization and RVL controls |
| Reporting/usability | AA-REQ-RPT-001..006 | 6 | 4 | 2 | RETAIN; one validated decision record and integrated reporting |
| Extensibility/integrations | AA-REQ-EXT-001..005 | 5 | 3 | 2 | RETAIN WITH CONSOLIDATED TRACEABILITY to EX-001..EX-016 |
| Compatibility/performance | AA-REQ-CMP-001..003 | 3 | 2 | 1 | RETAIN; map to support matrices, RVL and benchmark evidence |
| Release assurance | AA-REQ-REL-001..004 | 4 | 4 | 0 | RETAIN; map to existing release manifest/provenance/publication gates |
| Non-functional | AA-REQ-NFR-001..007 | 7 | 4 | 3 | RETAIN WITH DEPENDENCY/COMPATIBILITY RECONCILIATION |
| **Total** | **AA-REQ-*** | **70** | **55** | **15** | **All remain PROPOSED pending owner disposition** |

## 3. Group-by-group reconciliation

### 3.1 Project discovery/model — PROJ-001..006

**Recommendation: RETAIN.**

These requirements define a shared assurance input contract, not a new project scanner package. Bind discovery to the existing project snapshot identity, source provenance, bounded traversal, symlink policy, exclusions, and uncertainty model.

- PROJ-001/004/005 align with project identity, fact-level evidence lineage, and explicit unknown/conflict states.
- PROJ-002 aligns with read-only, non-executing discovery.
- PROJ-003 is a broad project-model inventory; implement incrementally through existing analyzers/adapters rather than promise every project fact.
- PROJ-006 aligns with bounded traversal and platform-specific filesystem rules.

Primary integration: Analysis + Knowledge + Evidence planes; migration snapshots; universal project knowledge graph. No second snapshot authority.

### 3.2 Verification planning — PLAN-001..006

**Recommendation: RETAIN.**

These requirements become the shared planning contract implemented in the Control plane and bound to immutable verification profiles.

- PLAN-001/002 define an inspectable plan with exact check identity/version, scope, prerequisites, inputs, permissions, limits, evidence and outcome mapping.
- PLAN-003 requires deterministic planning for identical declared inputs and versioned policies.
- PLAN-004 prohibits silent scope broadening and unplanned side effects.
- PLAN-005 requires visible inclusion/exclusion/blocking rationale.
- PLAN-006 preserves mandatory checks during optimization.

Primary integration: migration planner/preparation, QDAS orchestration, checker catalog/profile design. No parallel planner or optimization bypass.

### 3.3 Checker contract/runtime — CHK-001..008

**Recommendation: RETAIN, with execution ownership consolidated under RVL.**

- CHK-001/002 define stable checker identity and versioned contracts.
- CHK-003 requires strict output validation before evidence ingestion.
- CHK-004/005 define bounded execution and distinguish crash, invalid output, timeout, cancellation and infrastructure failure.
- CHK-006 enforces authority separation.
- CHK-007 binds project-controlled execution to exact plan and authorization.
- CHK-008 requires independent conformance testing.

Primary integration: Execution plane, RVL, adapter/extension contracts and QDAS. The checker catalog is descriptive and resolves capabilities; it does not execute checks. RVL remains the sole canonical execution/replay engine.

### 3.4 Evidence/provenance — EVD-001..008

**Recommendation: RETAIN, consolidate into the single AA-D2 evidence architecture.**

- EVD-001..004 define stable identity, scope, provenance, references, digests and validation.
- EVD-005 defines atomic acceptance under interruption.
- EVD-006 defines logical immutability, supersession and retention.
- EVD-007 distinguishes integrity from truth/authenticity.
- EVD-008 binds decisions to evidence and policy rules.

Primary integration: QDAS canonical event journal, content-addressed immutable artifact store, optional rebuildable index, Evidence and Confidence Model. No parallel AA or migration ledger authority.

### 3.5 Policy/decisions — POL-001..007

**Recommendation: RETAIN WITH REQUIRED WORDING RECONCILIATION.**

- POL-001 and POL-005 align with independent deterministic policy evaluation.
- POL-002's original seven-state list is stale relative to the owner-approved eight-state vocabulary. The reconciled requirement must include `INCONCLUSIVE` in addition to PASS, FAIL, BLOCKED, UNKNOWN, NOT_RUN, UNSUPPORTED and ERROR.
- POL-003 must not let a generic exception silently turn a non-PASS mandatory check into PASS or ASSURED. Any approved exception must be explicit, scoped, attributable, versioned, and reflected in the mandatory inventory/aggregate decision; it cannot erase the original outcome or evidence.
- POL-004 defines exception governance.
- POL-006 aligns with the aggregate assurance rule that mandatory gates and evidence/coverage cannot be hidden by counts or averages.
- POL-007 aligns with explainable, evidence-linked decisions.

Primary integration: Control plane, AA-D1, AA-D6, policy/evaluator contracts. Per-check, aggregate assurance, reproducibility and support classifications remain distinct.

### 3.6 Security/trust/execution — SEC-001..010

**Recommendation: RETAIN as cross-cutting invariants; consolidate implementation under existing security, authorization and RVL controls.**

- SEC-001 untrusted-input treatment aligns with the trust model and extension qualification.
- SEC-002/003 align with root confinement, symlink policy, platform path semantics and documented race limitations.
- SEC-004/005 align with argv-only execution and explicit environment policy.
- SEC-006 aligns with default-deny network; 1.2.0 must not require network-dependent mandatory checks.
- SEC-007 aligns with redaction and evidence privacy.
- SEC-008 requires measured/enforced resource limits or explicit unsupported reporting.
- SEC-009 prohibits overstating isolation.
- SEC-010 requires coverage/false-positive limitations.

Primary integration: Control + Execution + Evidence planes, migration hardening, RVL L0–L5 and security/supply-chain module. No separate AA sandbox.

### 3.7 Reporting/usability — RPT-001..006

**Recommendation: RETAIN.**

Reports must derive from one immutable validated decision record. The report contract must disclose exact scope, policy/profile version, mandatory and optional coverage, exclusions, unsupported/not-run/blocked checks, stale evidence, exceptions and limitations.

RPT-005 is advisory only: recommended next steps cannot be presented as guaranteed remediation. RPT-006 requires human- and machine-readable views to agree because they share the same decision source.

Primary integration: Integrated Reporting and Orchestration module, Control + Evidence planes.

### 3.8 Extensibility/integrations — EXT-001..005

**Recommendation: RETAIN, with shared traceability to EX-001..EX-016 rather than a second extension architecture.**

- EXT-001 aligns with offline-first operation and optional AI/provider integrations.
- EXT-002 aligns with versioned contracts, exact identity, qualification, authorization and central isolation.
- EXT-003 aligns with untrusted output validation and no provider-owned verdict authority.
- EXT-004 aligns with exact scope, permissions, network needs and limitations.
- EXT-005 aligns with visible unsupported/unavailable states.

Primary integration: `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`, EX-001..EX-016, Language and Domain Adapter Specification. Keep AA IDs as assurance-level obligations and link them to EX IDs where they share implementation/evidence; do not duplicate catalogs, registries or qualification services.

### 3.9 Compatibility/performance — CMP-001..003

**Recommendation: RETAIN.**

CMP-001/002 align with exact multidimensional support scopes and tested platform matrices. Untested combinations remain unverified/unknown, not assumed compatible. CMP-003 aligns with the benchmark specification and requires workload identity, environment, repetitions, uncertainty and resource evidence.

Primary integration: Knowledge + Execution + Evidence planes, RVL, supportability and Meta-Audit/Benchmark module.

### 3.10 Release assurance — REL-001..004

**Recommendation: RETAIN.**

These requirements remain distinct from ordinary verification and from CI workflow existence.

- REL-001 binds artifacts to exact source revision and explicit file manifest.
- REL-002 rejects unintended contents, path escapes and manifest mismatches.
- REL-003 binds artifact digests/provenance to the exact revision.
- REL-004 requires explicit publication authorization and prevents normal commits from publishing.

GitHub Actions being disabled does not waive release evidence; it changes the approved verification route. Do not restore workflows or trigger Actions without explicit owner approval.

Primary integration: release scripts, package manifest/content tests, Evidence + Control + Execution planes.

### 3.11 Non-functional — NFR-001..007

**Recommendation: RETAIN WITH COMPATIBILITY REVIEW.**

- NFR-001 aligns with the standard-library-first proposal, but a mandatory dependency can be added only through an owner-reviewed ADR; this is not a ban on future justified dependencies.
- NFR-002 preserves CLI and exit-code compatibility unless a documented change is approved.
- NFR-003 requires versioned schemas and explicit handling of unknown major versions.
- NFR-004 aligns with fail-closed decisions while preserving diagnostic evidence.
- NFR-005 aligns with candidate lightweight profiles, but exact names and inventories remain deferred.
- NFR-006 aligns with module resource/error/platform contracts.
- NFR-007 aligns with deterministic tests and non-mutation of real user projects.

Primary integration: all five planes and the implementation/acceptance plan.

## 4. Cross-document conflicts and required edits

1. **POL-002 outcome vocabulary:** update the reconciled 1.2.0 traceability statement to include `INCONCLUSIVE`. The original PR #3 source remains unchanged as historical input.
2. **POL-003 exception semantics:** clarify that exceptions cannot falsify the per-check outcome, erase evidence, or silently satisfy mandatory coverage. Any exception's effect on the mandatory inventory must be explicit and policy-versioned.
3. **CHK-004/005 execution mapping:** preserve low-level execution events as their own typed contract; map them to per-check outcomes at the policy/check layer. Do not force all eight per-check outcomes into the process runner enum.
4. **CHK-007/SEC-006 authorization:** bind permissions to exact plan, project snapshot, operation and scope; separate authorization from RVL host-enforced isolation.
5. **EVD-005/006 backend:** use the single logical QDAS journal + immutable artifacts model; backend remains deferred under the evaluation protocol.
6. **EXT group:** link to EX-001..EX-016; avoid duplicate extension runtimes and registries.
7. **REL group:** retain explicit release gates but do not equate release assurance with GitHub Actions or reintroduce workflows.
8. **Support and verdict semantics:** support classifications are not per-check outcomes; aggregate ASSURED is not a count of PASS results.

## 5. Acceptance and governance recommendation

The owner should review the 70 requirements as a coherent baseline after the cross-document wording changes. Recommended owner disposition choices are ACCEPT, ACCEPT WITH SCOPE/WORDING CHANGES, DEFER, or REJECT for each requirement or coherent group.

Until that review:
- all 70 AA requirement IDs remain PROPOSED;
- their existing traceability rows remain PROPOSED;
- no implementation status is advanced;
- PR #3 remains open/draft and is not merged;
- only selectively accepted documentation may be integrated into the 1.2.0 branch;
- no PR is merged into `main`, and `main` remains frozen until 1.2.0 release approval.

## 6. Related documents

- `ADVANCED_ASSURANCE_INTEGRATION_AND_PR3_REVIEW.md`
- `AA01_OWNER_DECISION_RECORD.md`
- `ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md`
- `DEEP_AUDIT_MASTER_ARCHITECTURE.md`
- `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`
- `CHECKER_CATALOG_AND_PROFILE_DESIGN.md`
- `LEGACY_STATE_INVENTORY_AND_MAPPING.md`
- `EVIDENCE_STORE_BACKEND_EVALUATION.md`
- `REQUIREMENT_TRACEABILITY_MATRIX.md`

This reconciliation is a recommendation for owner review, not acceptance of the 70 requirements or PR #3.

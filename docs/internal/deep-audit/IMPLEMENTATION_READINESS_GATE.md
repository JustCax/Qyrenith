# Qyrenith 1.2.0 — Implementation Readiness Gate

**Status:** OPEN — documentation and architecture preparation in progress  
**Assessment date:** 2026-11-10  
**Target branch:** `feature/1.2.0-universal-migration-core`  
**Purpose:** One auditable checklist for deciding when 1.2.0 is sufficiently specified to begin or resume implementation. This is a planning gate, not implementation evidence.

## 1. Readiness principle

Implementation readiness is not measured by the number of documents or commits. It is reached only when:
- the accepted architecture and owner decisions are internally consistent;
- all P0 requirements in the agreed 1.2.0 scope have exact owners, contracts, dependencies, and acceptance methods;
- legacy compatibility semantics are complete and fixture-backed;
- the Phase 1 migration safety gate is independently satisfied;
- QDAS and RVL interfaces are sufficiently defined to prevent parallel authorities;
- implementation slices have explicit prerequisites, positive/negative/adversarial tests, and evidence artifacts;
- the owner approves the final implementation baseline.

No code work may bypass an unresolved safety gate merely because a document is complete.

## 2. Current readiness register

| Area | Current state | Evidence / remaining work | Blocks implementation? |
|---|---|---|---|
| Canonical architecture | **OWNER-APPROVED BASELINE** | Five planes remain canonical; QDAS-first sequence, RVL authority and no-parallel-ledger/verdict rules are documented | No, provided implementation follows it |
| Seven AA-01 decisions | **OWNER-APPROVED** | Decision record and design baseline exist; physical backend, final profiles and exhaustive legacy mapping remain deferred | Related detail gates still block affected slices |
| Extensibility/supportability | **OWNER-APPROVED REQUIREMENT** | EX-001..EX-016 and normative specification exist; schemas, exact API boundaries, conformance implementation and individual support claims remain unimplemented | Yes for extension implementation |
| Four AA ADRs | **RECONCILED DRAFTS — OWNER ACCEPTANCE PENDING** | ADR-AA-001..004 exist in reconciled form; explicit accept/amend/defer decision still required | Yes for AA architecture baseline |
| Seventy PR #3 AA requirements | **RECONCILED — OWNER DISPOSITION PENDING** | Group-by-group reconciliation exists; all 70 remain PROPOSED; wording/overlap/acceptance must be approved | Yes for AA requirement baseline |
| Legacy state inventory | **PARTIAL SOURCE INVENTORY** | Source and test labels inventoried; exhaustive schema/version and real historical fixture corpus still required | Yes for compatibility and outcome conversion |
| Per-check outcome contract | **DESIGN APPROVED; IMPLEMENTATION GAP KNOWN** | Eight states approved; migration assurance allowlist/schema lacks INCONCLUSIVE; analyzer UNKNOWN→execution ERROR mapping needs correction | Yes for verdict/evidence slices |
| Evidence-store architecture | **LOGICAL MODEL APPROVED** | Backend evaluation and fault-injection plan exists; actual candidate measurements and owner backend decision remain open | Yes for persistent evidence implementation |
| Checker catalog | **DESIGN BASELINE EXISTS** | Checker/resource model and profile design exist; real checker inventory, exact contracts, scope, dependencies and qualification status still need audit | Yes for final profiles and checker runtime |
| Verification profiles | **MODEL APPROVED; INVENTORY DEFERRED** | Immutable manifests specified; final names, check inventories, mandatory/optional scope and budgets require catalog measurements | Yes for profile publication/runtime |
| Extension contract | **ARCHITECTURAL REQUIREMENT APPROVED** | Exact manifest/API schemas, protocol compatibility, qualification lifecycle records and provider conformance suites remain to be specified | Yes for extension runtime |
| Phase 1 migration hardening | **OPEN — NOT VERIFIED COMPLETE** | Trust/revocation freshness, worker qualification, authenticated host approval, OS-enforced isolation, concurrency/recovery and platform evidence must all pass the implementation plan's exit gate | **YES — hard blocker before Phase 2** |
| QDAS | **PARTIAL IMPLEMENTATION EXISTS** | Existing event/ledger/diagnosis/repair foundations need migration-gate integration, full acceptance, evidence and independent verification | Yes for Phase 2 completion |
| Fourteen post-QDAS modules | **SPECIFIED AT HIGH LEVEL; DELIVERY NOT STARTED AS A COMPLETE SET** | Exact slices, shared contracts, dependencies, acceptance and scope prioritization remain to be closed | Yes for complete 1.2.0 |
| Twenty-seven diagnostic domains | **TARGET ENVELOPE — NOT A RELEASE PROMISE** | Shared-engine mapping exists; exact 1.2.0 vertical slices and deferred domains must be owner-approved | Yes for release scope clarity |
| Release verification route | **ACTIONS DISABLED BY OWNER** | Approved independent local/external runner and retained revision-bound evidence must be defined; do not restore/trigger Actions without approval | Yes for release |
| Documentation integrity | **IN PROGRESS** | Continue link, terminology, status, requirement-ID, cross-reference and package-content audits | Yes for final readiness |
| Final implementation baseline | **NOT APPROVED YET** | Requires closed P0 gates, reconciled traceability, implementation slice plan, and explicit owner sign-off | **YES** |

## 3. Mandatory pre-implementation exit gates

### Gate A — Owner decisions and scope

- [ ] Owner disposition for ADR-AA-001..004.
- [ ] Owner disposition for all 70 proposed AA requirement IDs, individually or by explicitly approved groups.
- [ ] Confirm which DI/RCA/OI proposals are in 1.2.0 scope and which remain long-term targets.
- [ ] Confirm that the 27 diagnostic domains are an ecosystem target envelope, not an implied 1.2.0 completeness claim.
- [ ] Freeze the initial release scope and define an explicit change-control process.

### Gate B — Outcome and compatibility semantics

- [ ] Complete repository-wide source inventory of status/state fields, schemas, CLI outputs and test fixtures.
- [ ] Inventory representative historical 1.1.0 state/evidence fixtures with secrets redacted.
- [ ] Define exhaustive, versioned conversion rules for every known legacy value and explicit UNKNOWN fallback.
- [ ] Preserve raw values and provenance; prove round-trip/export behavior.
- [ ] Resolve the missing INCONCLUSIVE value in migration assurance schemas and all consumers.
- [ ] Resolve analyzer UNKNOWN versus execution ERROR semantics.
- [ ] Test that no legacy success, VERIFIED label, missing state, or ambiguous value becomes PASS/ASSURED without evidence.

### Gate C — Evidence persistence

- [ ] Run the same candidate comparison suite against all selected backend candidates.
- [ ] Complete crash/fault injection, concurrency, portability, privacy, retention, export/restore and performance evidence.
- [ ] Define the durable event/artifact commit protocol and orphan recovery.
- [ ] Select one physical backend through an owner-reviewed decision record.
- [ ] Prove one canonical journal authority and a rebuildable non-authoritative index.

### Gate D — Checker catalog and profiles

- [ ] Inventory all existing native checks and provider-backed checks with exact IDs/versions.
- [ ] Define manifest/input/output schemas and version compatibility rules.
- [ ] Define exact support tuples and deterministic conflict resolution.
- [ ] Define qualification and invalidation evidence for every provider-backed check.
- [ ] Measure actual resource behavior and enforce hard ceilings through RVL.
- [ ] Publish exact mandatory/optional inventories for each initial profile version.
- [ ] Prove all exclusions, unsupported checks, and NOT_RUN outcomes remain visible.

### Gate E — Extension contracts

- [ ] Finalize extension manifest and API/protocol schemas.
- [ ] Define package identity/provenance and digest verification.
- [ ] Define capability negotiation and exact support matching.
- [ ] Define independent qualification, revocation, expiry, requalification and deprecation.
- [ ] Define least-privilege permission requests and authenticated authorization.
- [ ] Define central RVL execution/isolation integration for executable providers.
- [ ] Define local/offline catalog and deterministic provider resolution.
- [ ] Complete positive, negative, boundary, adversarial and compatibility conformance suites.

### Gate F — Phase 1 migration safety

All items in the implementation plan's Phase 1 exit gate are mandatory:
- [ ] Full 1.1.0 regression suite and required Windows/Linux/macOS matrix pass on the same commit.
- [ ] No unresolved critical/high migration identity, planner, worker, authorization, ledger, snapshot or workspace defects.
- [ ] Owner-controlled trust store, exact digest/revocation, and approval/execution-time freshness checks pass.
- [ ] Worker qualification has independently collected conformance evidence.
- [ ] Human approval uses an authenticated trusted host channel.
- [ ] Filesystem/process/environment/secret/network limits are enforced by OS sandbox or equivalent host-controlled boundary.
- [ ] Workspace/recovery and concurrency adversarial tests pass.
- [ ] CLI, PR description, public docs, internal specs, schemas, traceability and package contents agree.
- [ ] Unsupported host boundaries remain propose-only/blocked/unsupported.

### Gate G — Implementation slices and independent validation

- [ ] Every P0 requirement maps to a concrete implementation slice and acceptance evidence.
- [ ] Dependencies form a deterministic, reviewed implementation order.
- [ ] Every slice has positive, negative, boundary, regression and adversarial tests.
- [ ] QDAS cannot self-certify its own implementation; independent verification route is available.
- [ ] Documentation, schemas, CLI, package manifests and support matrix are updated together.
- [ ] Owner approves the implementation baseline and explicitly authorizes the next phase.

## 4. Recommended implementation sequence after readiness

1. Finish and independently verify Phase 1 migration-platform hardening.
2. Implement/complete QDAS foundation on the single evidence and RVL contracts.
3. Establish checker catalog, profile resolver and policy/aggregate assurance core.
4. Deliver the highest-priority native static/semantic and security vertical slices.
5. Add dynamic/behavioral, fuzz/property, formal and domain-specific capabilities in measured slices.
6. Integrate compatibility knowledge, adapters/extensions and qualification incrementally.
7. Complete reporting/orchestration, maturity/coverage, meta-audit and benchmarks.
8. Run full platform, regression, adversarial, export/restore, packaging and independent release acceptance.

This order is subordinate to the accepted master implementation plan; it refines readiness gates and does not create a parallel phase model.

## 5. Status vocabulary for this register

- **OWNER-APPROVED:** the owner explicitly approved the architecture/requirement direction.
- **RECONCILED DRAFT:** documents have been aligned but still require owner acceptance.
- **PARTIAL SOURCE INVENTORY:** observed sources are recorded; exhaustive historical coverage is not established.
- **OPEN / NOT VERIFIED:** implementation or independent evidence is missing.
- **NOT APPROVED:** owner sign-off has not been granted.

A document existing, a commit landing, or a test passing in isolation never changes a readiness state by itself.

## 6. Governance

- All changes remain on `feature/1.2.0-universal-migration-core`.
- `main` remains untouched until explicit 1.2.0 release approval.
- PR #9 remains open/draft and unmerged.
- PR #3 remains a separate open/draft review source; selectively accepted material is integrated only into the 1.2.0 branch.
- GitHub Actions remain disabled; do not restore or trigger workflows without explicit approval.
- No runtime code, schema, tests, workflow, release, or publication changes are authorized by this readiness document.

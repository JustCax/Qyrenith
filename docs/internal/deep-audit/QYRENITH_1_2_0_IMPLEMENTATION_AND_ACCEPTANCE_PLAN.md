# Qyrenith 1.2.0 Implementation and Acceptance Plan

## 1. Release principle

1.2.0 is complete only when all accepted requirements across the eighteen normative specifications are implemented, tested, integrated, documented, and supported by retained evidence. The deep-audit README is the navigation index. A specification, stub, placeholder, TODO, or passing narrow unit test does not constitute feature completion.

## 2. Mandatory sequence

### Phase 0 — Documentation baseline
- Reconcile all four AA-01 ADRs against the accepted seven owner decision directions, five-plane architecture, QDAS/RVL authority, migration authorization, and extensibility contract; obtain explicit owner acceptance before treating them as accepted architecture.
- Complete requirement-to-ADR traceability and close deferred design prerequisites (legacy-state inventory, checker catalog/resource model, evidence-backend comparison, host approval/isolation matrix, and extension contract boundaries).
- Create and cross-link all eighteen normative specifications and the specification index.
- Maintain `REQUIREMENT_TRACEABILITY_MATRIX.md` as the authoritative requirement-to-implementation/test/evidence/dependency/status map.
- Resolve contradictions with existing public/internal docs.
- Review all security, trust, permission, isolation, and non-claim language.
- Keep internal specifications out of public package contents unless separately approved.

### Phase 1 — Finish existing migration-platform work
- Audit migration identity, transition validation, knowledge catalog, planner, worker contracts, authorization, ledger, snapshots, and workspace copying.
- Close known CI failures, including Windows newline-sensitive subprocess tests.
- Reconcile PR description with implemented workspace API and remaining limitations.
- Resolve subprocess timeout/stdin/output-limit issues and command-path validation bypasses.
- Review environment allowlisting, worker first-run approval, adapter trust, symlink/race behavior, concurrent access, and failure cleanup.
- Finish the trust and execution boundary before any migration worker can run: persist knowledge/worker allowlists in an owner-controlled trust store; revalidate catalog identity, trust decisions, claim scope, and expiry at approval and immediately before execution; implement a controlled conformance runner with independently collected results; add an authenticated host approval channel; and enforce filesystem/process/network limits through an OS sandbox or equivalent host boundary. Until every gate is enforceable, migration-platform and QDAS worker/repair execution remain propose-only. The legacy `worker-run` command is separate: its `--yes` flag is a caller assertion, not authenticated human approval, and it does not provide an OS sandbox.
- Verify and pin the Gradle wrapper bootstrap JAR and distribution checksums; retain cross-platform subprocess newline and output-limit regression tests.
- Enforce generated agent-instruction synchronization in tests and reject symlinked release output paths.
- Integrate only where acceptance tests prove safety; retain explicit non-claims otherwise.
- Re-run complete 1.1.0 regression suite and the full platform matrix.

### Phase 1 exit gate — mandatory before QDAS implementation

Do not begin Phase 2 until all of the following are true:

- The complete 1.1.0 regression suite and required Windows/Linux/macOS matrix pass on the same commit.
- Existing migration identity, knowledge, planner, worker registry, authorization, ledger, snapshot, and workspace contracts have no unresolved critical/high defect.
- Owner-controlled trust-store loading, exact-digest trust/revocation, and approval-time/validation-time freshness checks are implemented and tested.
- Worker qualification is backed by a controlled conformance runner or authenticated attestation with independently collected evidence.
- Human approval is authenticated through a trusted host channel; caller-supplied strings and CLI flags do not count.
- Filesystem, process, environment, secret, and network restrictions are enforced by an OS sandbox or equivalent host-controlled boundary.
- The assurance ledger is integrated into the relevant lifecycle and cannot be treated as independent proof when its local store is replaceable.
- Workspace and recovery behavior has adversarial tests; any unsupported isolation guarantee remains explicitly unavailable.
- The PR description, public docs, internal specs, traceability matrix, CLI behavior, and package contents agree.

If any item is missing, keep the affected execution path disabled/propose-only, record the blocker, and do not declare Phase 1 complete.

### Phase 2 — QDAS foundation
- Implement event schema and ingestion.
- Implement failure taxonomy and evidence lineage.
- Implement root-cause hypothesis contracts and repair planning.
- Integrate exact snapshot and reproducible lab identities.
- Add approval-scoped repair execution only behind an OS-enforced sandbox or equivalent host-controlled least-privilege boundary; otherwise remain propose-only.
- Add regression-preservation checks, anti-false-fix checks, bounded retries, and safe-stop states.
- Demonstrate disposable fixture repair and independent external verification.

### Phase 3 — Remaining fourteen capability modules
Implement each module in small dependency-ordered slices. For every slice: QDAS capture → plan → approval → implementation → targeted tests → full regression → static/security audit → diff review → evidence record. QDAS assists but does not self-certify its own changes.

## 3. Capability modules

The fourteen capability modules after QDAS are:
1. Static and semantic analysis.
2. Dynamic and behavioral audit.
3. Formal verification and bounded symbolic execution.
4. Fuzzing and property testing.
5. Security and supply-chain audit.
6. Root-cause and cross-module analysis.
7. Universal compatibility and failure knowledge.
8. Reproducible verification lab.
9. Meta-audit and benchmark.
10. Evidence and confidence model.
11. Language and domain adapters.
12. Audit maturity and coverage.
13. Migration platform integration.
14. Integrated reporting, orchestration, and acceptance controls.

The master architecture and this plan are governance documents. The migration integration and reporting specifications define the final two capability modules. The README is an index, not a runtime module.

**Phase boundary:** Phase 1 completes and hardens the migration foundation that already exists in the branch (typed identities/transitions, knowledge, planning, worker records, authorization, ledger, snapshots, and workspace copying). Phase 3 module 13 then performs the QDAS/deep-audit integration across the completed migration platform; it must not duplicate or bypass the Phase 1 contracts.

## 4. Requirement traceability

Each requirement must have a stable ID and a traceability row containing:
- specification and requirement ID;
- implementation package/API/CLI;
- positive test and negative/adversarial test;
- evidence artifact type;
- dependencies and blocking prerequisites;
- status: NOT_STARTED, IN_PROGRESS, IMPLEMENTED, TESTED, VERIFIED, BLOCKED;
- reviewer and verification timestamp.

No requirement may be marked VERIFIED solely because its code exists or its unit tests pass.

## 5. Definition of done

A module is done only when:
- all normative requirements have implementation or owner-approved scope removal;
- supported inputs and unsupported cases are explicit;
- positive, negative, boundary, regression, and adversarial tests pass;
- resource limits and failure states are exercised;
- evidence lineage is complete;
- docs, schemas, CLI help, and package manifests agree;
- no critical/high unresolved issue remains without explicit accepted risk;
- independent validation is complete where the claim requires it.

## 6. Release blockers

Any failing required CI job, unresolved critical/high security defect, false PASS path, silent downgrade, missing evidence, unbounded execution path, package-content mismatch, broken compatibility contract, or undocumented public behavior blocks release.

## 7. Governance

- The only active development/integration branch for 1.2.0 is `feature/1.2.0-universal-migration-core`.
- Do not commit, merge into, rebase, or otherwise modify `main` before the approved 1.2.0 release integration.
- PR #9 is the release PR from the 1.2.0 branch to `main`; keep it open and draft during development. Do not merge it before release approval.
- PR #3 and any other supporting PRs are review/source branches only. If accepted, their changes are integrated into the 1.2.0 branch only, after selective review; never merge them into `main`.
- Do not merge every PR automatically. First determine whether its content is needed, non-duplicative, compatible, and accepted. Preserve useful PRs as draft review records when direct integration is unnecessary.
- No tag, PyPI publication, or public release is authorized without explicit owner approval.
- Changes to accepted architecture require a decision record and updated traceability.

## 8. Expanded capability envelope — proposed extension

The 27 diagnostic domains in `DIAGNOSTIC_INTELLIGENCE_EXPANSION_SPEC.md` define the target capability envelope. They are grouped into shared engines and domain packs, not 27 isolated packages or a promise that all domains are complete in 1.2.0.

The six product pillars map onto the existing five planes in `UNIVERSAL_SOFTWARE_INTELLIGENCE_ARCHITECTURE.md`. The current master remains canonical unless the owner approves a decision record changing it.

### 8.1 Planning artifacts
- `DIAGNOSTIC_CAPABILITY_COVERAGE_MATRIX.md`: initial inventory, not verification.
- `REPRODUCIBILITY_AND_CROSS_ENVIRONMENT_ASSURANCE_SPEC.md`: extends the existing lab/evidence model.
- `OPTIMIZATION_AND_REPAIR_INTELLIGENCE_SPEC.md`: controlled optimization and repair.
- `ADVANCED_ASSURANCE_INTEGRATION_AND_PR3_REVIEW.md`: crosswalk for the separate AA-01 draft, reconciled ADRs, and PR #3 disposition.
- `ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md`: owner-approved seven-decision AA-01 design baseline; backend/profile details remain deferred where explicitly stated.
- `ARCHITECTURE_DECISION_RECORDS/ADR-AA-001..004`: selectively reconciled ADR drafts; all four remain PROPOSED pending explicit owner acceptance.
- `LEGACY_STATE_INVENTORY_AND_MAPPING.md`: source-based inventory and conservative mapping proposal; exhaustive historical fixture mapping remains a prerequisite.
- `EVIDENCE_STORE_BACKEND_EVALUATION.md`: common backend comparison and fault-injection protocol; no physical backend is selected until evidence is reviewed.
- `CHECKER_CATALOG_AND_PROFILE_DESIGN.md`: check identity, support resolution, immutable profile manifests, resource budgets, and aggregate assurance rules; final profile inventories remain deferred.
- `AA_REQUIREMENT_RECONCILIATION.md`: review of all 70 proposed PR #3 AA requirements; owner disposition remains pending and IDs remain PROPOSED.
- `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`: owner-approved first-class extension ecosystem, qualification, exact support scope, lifecycle, and compatibility contract.
- `RESEARCH_AND_STANDARDS_ALIGNMENT.md`: source register and interoperability consequences.
- DI-001..DI-081: proposed requirements in the authoritative matrix.
- RCA-01..RCA-12 and OI-01..OI-10: add to the authoritative matrix before implementation.

### 8.2 Delivery interpretation
The 27 domains are the full target envelope, not a promise that all are complete in 1.2.0. Identify shared foundations and end-to-end vertical slices with executable tests/evidence. Other domains remain explicitly PARTIAL, UNSUPPORTED, BLOCKED or deferred. No support claim may be inferred from a registry or document.

The existing Phase 1 migration safety gate and Phase 2 QDAS-first order remain unchanged. Reuse the fourteen existing modules and contracts; do not create a parallel architecture.

### 8.3 Advanced Assurance integration

The separate AA-01 draft is a cross-cutting assurance contract, not a fifteenth capability module or a replacement for QDAS. Its project discovery/model, verification planner, authorization gate, checker registry/runtime, evidence validator/store, policy evaluator, reporting layer and provider boundary map onto the existing five planes and fourteen post-QDAS capability modules.

The PR #3 draft contributes 70 proposed AA requirement IDs across eleven groups, including 55 P0 requirements. They are tracked in `REQUIREMENT_TRACEABILITY_MATRIX.md` as `PROPOSED`; the corrected PR #3 acceptance matrix maps all 70 IDs to an architecture owner, threat references, and a reserved acceptance-test ID. These are planned test identifiers, not existing test code or verification evidence. This does not accept PR #3, its four proposed ADRs, or its architecture. See `ADVANCED_ASSURANCE_INTEGRATION_AND_PR3_REVIEW.md` for the full mapping, overlap rules, resolved AA-01 owner decisions, remaining ADR/requirement review, and safe PR disposition.

Before implementation:
- implement the approved AA-01 decision directions from ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md only after reconciling the required contracts;
- obtain explicit owner disposition for the four reconciled ADR-AA-001..004 drafts; keep their status PROPOSED until individually accepted or rejected;
- obtain owner disposition for the 70 proposed AA requirement IDs after reviewing the reconciliation; do not treat the seven accepted AA-01 decision directions as blanket acceptance of these requirements;
- approve the exact requirement baseline and acceptance methods, including the distinction between SPECIFIED, IMPLEMENTED and VERIFIED;
- complete the repository-wide and historical-fixture legacy state inventory; resolve the `INCONCLUSIVE` schema gap and the analyzer `UNKNOWN`/execution `ERROR` semantic mismatch before finalizing compatibility implementation;
- complete the evidence backend comparison using the common atomicity, crash recovery, concurrency, portability, privacy, retention, export/restore, and fault-injection protocol; obtain owner approval for the selected backend;
- complete the checker inventory and exact check contracts, then derive versioned profile inventories and resource budgets from measured capabilities; do not approve profile labels or mandatory coverage by name alone;
- preserve Phase 1 migration hardening and Phase 2 QDAS-first order;
- define implementation slices against the existing module contracts rather than creating a parallel runtime;
- keep per-check outcomes, aggregate assurance decisions, reproducibility outcomes, and extension support classifications as separate vocabularies;
- implement extensibility through versioned contracts, capability discovery, qualification, support manifests, and conformance—not an untrusted code-loading shortcut.

## 9. Verification while GitHub Actions are disabled

The owner disabled GitHub Actions to avoid usage/billing. Workflow definitions have been removed from the active branches and must not be restored or triggered without explicit approval.

This changes the verification execution method, not the quality bar:
- release verification remains mandatory;
- use an owner-approved independent local or external runner;
- record exact commit, command, OS/architecture, runtime/toolchain, dependencies, timestamp, exit result and artifact digests;
- retain positive, negative, regression and adversarial evidence;
- execute supported platform matrix cells explicitly; unexecuted cells remain NOT_RUN;
- independently review security, packaging and release contents;
- historical Actions runs are not evidence for a newer commit.

If equivalent independent verification is unavailable, release readiness remains BLOCKED. Do not lower acceptance criteria because Actions are disabled.

## 10. Proposal governance

The six-pillar grouping, 27-domain envelope, reproducibility extension and optimization specification remain proposals pending owner review. The extensibility and supportability architecture is an owner-approved requirement, but its implementation and each individual extension's qualification remain unverified. They do not automatically amend accepted architecture or remove requirements. Before implementation, review overlaps with existing modules, add RCA/OI IDs to the matrix, approve exact 1.2.0 vertical slices and record architecture decisions.

# Qyrenith 1.2.0 — Implementation Readiness Gate

**Status:** OVERALL READINESS OPEN — Phase 0 specification baseline COMPLETE; Phase 1 remains a hard blocker  
**Assessment date:** 2026-11-19  
**Target branch:** `feature/1.2.0-universal-migration-core`  
**Purpose:** One auditable checklist for deciding when 1.2.0 is sufficiently specified to begin or resume implementation. This is a planning gate, not implementation evidence.

**Roadmap view:** The reusable [Phase 0–7 Progress Dashboard](PHASE_0_7_PROGRESS_DASHBOARD.md) and its [animated HTML presentation](PHASE_0_7_PROGRESS_DASHBOARD.html) summarize delivery progress. They do not replace this gate, the normative implementation plan, or owner-approved decisions.

**Phase status:** Phase 0 was closed as an owner-accepted documentation/specification baseline on 2026-11-16. This does not certify runtime implementation or test results. Phase 1 remains OPEN and must pass its safety exit gate before QDAS/module execution is enabled.

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
| Phase 0 documentation/specification baseline | **COMPLETE — 2026-11-16** | Four AA ADRs, 70 AA requirements, 27 diagnostic domains, specification index, host matrix, checker source inventory, extension authority boundaries and traceability are recorded; measurement-dependent evidence remains in later gates | No — Phase 1 is the next mandatory gate |
| Canonical architecture | **OWNER-APPROVED BASELINE** | Five planes remain canonical; QDAS-first sequence, RVL authority and no-parallel-ledger/verdict rules are documented | No, provided implementation follows it |
| Seven AA-01 decisions | **OWNER-APPROVED** | Decision record and design baseline exist; physical backend, final profiles and exhaustive legacy mapping remain deferred | Related detail gates still block affected slices |
| Extensibility/supportability | **OWNER-APPROVED REQUIREMENT** | EX-001..EX-016 and normative specification exist; schemas, exact API boundaries, conformance implementation and individual support claims remain unimplemented | Yes for extension implementation |
| Four AA ADRs | **OWNER-ACCEPTED — 2026-11-16** | ADR-AA-001..004 accepted as reconciled; implementation and verification remain separate | No for architecture acceptance; implementation gates remain |
| Seventy PR #3 AA requirements | **OWNER-ACCEPTED — 2026-11-16** | All 70 stable IDs accepted across eleven groups; traceability rows updated; mapped tests/evidence still pending | No for requirement acceptance; implementation gates remain |
| Legacy state inventory | **SOURCE INVENTORY + MAPPING POLICY; HISTORICAL FIXTURE GATE OPEN** | Typed state families and conservative mappings are documented; exhaustive persisted historical fixture coverage and full consumer conversion remain verification/compatibility work | Yes for final compatibility acceptance |
| Per-check outcome contract | **DESIGN APPROVED; PARTIALLY IMPLEMENTED, NOT TEST-VERIFIED** | Eight states approved; migration assurance allowlist/schema now include INCONCLUSIVE and a round-trip test exists; analyzer UNKNOWN is retained in the returned analysis/capture report, while the QDAS ledger stores its bounded event metadata and output digest; it is no longer mapped to execution ERROR. Targeted tests are added but unexecuted; full consumer/legacy fixture compatibility remains open | Yes for verdict/evidence slices |
| Evidence-store architecture | **LOGICAL MODEL APPROVED; CANDIDATE A RECOMMENDED, NOT SELECTED** | ADR-AA-003 fixes one QDAS journal, immutable content-addressed artifacts and optional derived index; comparison/fault-injection protocol exists; Candidate A is recommended for evaluation, but measurements and owner selection remain open | Yes for final backend selection and persistent implementation |
| Checker catalog | **SOURCE-SURFACE INVENTORY ADDED; PROFILE INVENTORY OPEN** | `CHECKER_CATALOG_AND_RESOURCE_MODEL.md` now inventories existing CLI, adapter, QDAS and migration surfaces without treating them as qualified checkers; exact 27-domain checker mappings and profile budgets remain implementation prerequisites | Yes for final profiles and checker runtime |
| Verification profiles | **MODEL APPROVED; INVENTORY DEFERRED** | Immutable manifests specified; final names, check inventories, mandatory/optional scope and budgets require catalog measurements | Yes for profile publication/runtime |
| Extension contract | **OWNER-APPROVED; AUTHORITY BOUNDARIES SPECIFIED** | `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md` now separates manifest, qualification, trust, support, authorization, RVL execution and QDAS evidence authorities. Exact JSON schemas, SDK/API and provider conformance runtime are delivery artifacts for later module slices | No for Phase 0 architecture; yes for extension implementation |
| Host approval/isolation matrix | **SOURCE-RECONCILED; NOT PLATFORM-QUALIFIED** | `HOST_APPROVAL_AND_ISOLATION_CAPABILITY_MATRIX.md` separates source mechanisms, declarations, host enforcement and untested platform cells; no platform currently qualifies side-effecting migration/repair | Yes — Phase 1 hard blocker |
| Phase 1 migration hardening | **OPEN — PARTIAL FOUNDATIONS; NOT VERIFIED COMPLETE** | Owner trust store, exact-digest decisions, freshness rechecks and one-time interactive host-approval records exist. Protected Windows owner/SYSTEM DACL enforcement now covers the trust-store directory, data file, integrity key and lock file; Job Object process-tree containment has a 64-process cap and documented Toolhelp/ResumeThread startup. Windows-only tests are added but not run. The host principal is still populated from `getpass.getuser()` and the trust-store HMAC is local-key integrity, not independent human identity authentication. Sandbox profile ID/digest are caller-supplied scope fields; filesystem/network/environment/secret/resource isolation and a migration worker executor are absent. Worker conformance evidence, authenticated host identity, crash recovery and platform verification remain open. | **YES — hard blocker before Phase 2** |
| QDAS | **PARTIAL IMPLEMENTATION EXISTS** | Existing event/ledger/diagnosis/repair foundations need migration-gate integration, full acceptance, evidence and independent verification | Yes for Phase 2 completion |
| Fourteen post-QDAS modules | **SPECIFIED AT HIGH LEVEL; DELIVERY NOT STARTED AS A COMPLETE SET** | Exact slices, shared contracts, dependencies, acceptance and scope prioritization remain to be closed | Yes for complete 1.2.0 |
| Twenty-seven diagnostic domains | **OWNER-ACCEPTED 1.2.0 RELEASE SCOPE — 2026-11-16** | All 27 domains and DI-001..DI-081 are in scope; each needs implementation/support evidence and an explicit acceptance disposition | Yes for complete release delivery |
| Release verification route | **ACTIONS DISABLED BY OWNER** | Approved independent local/external runner and retained revision-bound evidence must be defined; do not restore/trigger Actions without approval | Yes for release |
| Documentation integrity | **IN PROGRESS** | Continue link, terminology, status, requirement-ID, cross-reference and package-content audits | Yes for final readiness |
| English-only repository language | **CHARACTER-SET CHECK ONLY; SEMANTIC REVIEW OPEN** | `tests/test_english_only_policy.py` rejects non-ASCII letters, but it is not a language detector and cannot identify non-English ASCII text. The test name/message now state this limitation; a complete human review of source, docs, comments, diagnostics, logs, configuration and public artifacts remains required. The test has not been executed on the current revision. | **YES for final release** |
| Final implementation baseline | **NOT APPROVED YET** | Requires closed P0 gates, reconciled traceability, implementation slice plan, and explicit owner sign-off | **YES** |

## 3. Mandatory pre-implementation exit gates

**Owner decision update (2026-11-16):** Gate A decisions for the four AA ADRs, all 70 AA requirements, and all 27 diagnostic domains are complete and recorded. This does not close the remaining Phase 0 design/evidence prerequisites or Phase 1 safety gate.

### Gate A — Owner decisions and scope

- [x] Owner accepted ADR-AA-001..004 on 2026-11-16; acceptance recorded in the decision log and individual ADRs.
- [x] Owner accepted all 70 AA requirements in the existing eleven-group structure on 2026-11-16; implementation evidence remains outstanding.
- [x] Confirmed DI-001..DI-081 and all 27 diagnostic domains are in 1.2.0 scope; RCA/OI remain separately governed proposals.
- [x] Owner explicitly included all 27 diagnostic domains in the 1.2.0 release scope; no implementation or support claim is implied until evidence exists.
- [ ] Freeze the initial release scope and define an explicit change-control process.

### Gate B — Outcome and compatibility semantics

- [ ] Complete repository-wide source inventory of status/state fields, schemas, CLI outputs and test fixtures.
- [ ] Inventory representative historical 1.1.0 state/evidence fixtures with secrets redacted.
- [ ] Define exhaustive, versioned conversion rules for every known legacy value and explicit UNKNOWN fallback.
- [ ] Preserve raw values and provenance; prove round-trip/export behavior.
- [x] Add INCONCLUSIVE to the migration assurance runtime allowlist and JSON schema; add a round-trip test. **Implementation only; test execution and full consumer compatibility remain pending.**
- [x] Correct analyzer UNKNOWN versus execution ERROR mapping without widening the four-state QDAS execution enum; add targeted tests. **Implementation only; test execution remains pending.**
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

All items in the implementation plan's Phase 1 exit gate are mandatory.

#### Source-based status clarification (2026-11-16)

A read-only source review confirms that several foundations exist, but they do not close the gate:

- `qyrenith_engine/trust_store.py` provides a per-user append-only trust-decision store, exact digest matching, revocation/expiry checks, locking, and a local HMAC. Its key is stored alongside the store; this is owner-local integrity protection, not protection against malicious code running as the same OS user or an independent trust anchor. On Windows, source code now applies and reads back a protected DACL restricted to the current user SID and SYSTEM for the trust-store directory, data file, key file, and lock file; this is path-based ACL enforcement, not handle-relative identity binding, and its Windows regression test has not been executed. Trust decisions enforce non-decreasing review timestamps per exact subject both when appending and when validating persisted history, preventing a backdated TRUST event from superseding a later REVOKE; the targeted regression test has not been executed. A cross-process writer-serialization regression test also exercises eight concurrent writers against one store and checks that no events or sequence numbers are lost; that test has not been executed.
- `qyrenith_engine/approval.py` provides an interactive terminal challenge, exact action-scope binding, a trust-store MAC, expiry, and single-use nonce consumption. The request expiry is revalidated after the operator enters the challenge, and `approved_at` is now bound to the successful response rather than the earlier prompt display; a delayed-response regression test was added but has not been executed. The recorded `approved_by`/`host_principal` values are populated from `getpass.getuser()`; that is OS account attribution, not independent authentication of the human. Treat the current mechanism as explicit local confirmation, not yet proof of an authenticated human identity. The initial authorization constructor `authorize_migration()` still accepts caller-supplied `approved_by`/timestamps and does not itself require a `HostApproval`; its attribution is therefore not authenticated. A separate step-boundary integration now exists: `create_migration_step_approval_request()` binds the exact authorization, route, worker grant, workspace, snapshot, command digest, and caller-declared sandbox profile, while `validate_migration_step_approval()` revalidates owner trust and migration authorization, verifies the exact `HostApproval` scope, and atomically consumes its nonce immediately before the intended step boundary. This is an interactive local confirmation gate, not independent human identity authentication or proof that the declared sandbox profile is enforced. It does not establish a worker executor or OS-level isolation.
- `WorkerQualification` validates the shape, digest, PASS label, test count, and timestamps of a qualification record, while `MigrationWorkerRegistry` matches that record to a manifest. The record's `conformance_suite_digest`, `result_digest`, `qualified_by`, and `test_count` are supplied metadata; no controlled runner or independently collected result is established by this model. Owner trust of the record digest approves that exact record, not proof that the declared suite executed.
- `migration_step_approval_scope()` binds a caller-supplied sandbox profile ID/digest into the approval scope. That binds the declaration, not proof that the profile was installed or enforced. No OS sandbox provider or migration worker execution boundary is established by this code.
- `qyrenith_engine/execution.py` explicitly describes bounded subprocess execution as not an OS sandbox. The Windows path now assigns the suspended child to a Job Object before resuming it, enforces a 64-process limit, and uses kill-on-close for descendants. This is process-tree containment only, not a filesystem/network sandbox; its Windows regression test has not been run. The resume implementation now uses documented Toolhelp thread enumeration and `ResumeThread`, after verifying exactly one suspended initial thread belongs to the target PID; this is source-level only and remains unverified on Windows. `terminate_and_close()` checks the `TerminateJobObject` result and still attempts kill-on-close cleanup. A later correction propagates unreliable process-tree cleanup into a `termination_failed` report field and forces the execution result to `BLOCKED`, including when Job Object closure fails after the root process exits; a mocked regression test was added but not executed. A 2026-11-16 source audit also found that the output capture ceiling was applied independently to stdout and stderr; the implementation now shares one aggregate capture budget across both streams, with a targeted regression test added. This correction is **not test-verified** because no local test run or CI run was authorized/performed.
- Workspace materialization creates a verified independent copy; it is not an OS/process/network isolation boundary.
- `qyrenith_engine/migration/snapshot.py` uses descriptor-relative `O_NOFOLLOW` traversal on supported POSIX systems. Windows snapshot capture now fails closed before the path-based fallback because native handle-relative/reparse-point-safe traversal is not implemented. `workspace.py` likewise rejects source opening where descriptor-relative no-follow APIs are unavailable. This deliberately blocks Windows snapshot/workspace preparation until the native implementation and race-focused tests exist; it is not Windows support or verification.

The migration `AssuranceLedger` also validates record structure and its local digest chain only. A `PASS` value is caller-supplied; the current ledger does not resolve evidence IDs, inspect referenced artifacts, independently collect results, or authenticate their origin. Treat it as a recorded verdict label, not independent assurance evidence, until the evidence-validation and authority integration is implemented.
The current `record_migration_step_with_qdas()` integration appends to the QDAS ledger and then to the migration assurance ledger as two independent writes; no cross-ledger transaction exists. `MigrationEvidenceCommitError` preserves the QDAS capture, exact digests and original assurance payload when the assurance append does not return successfully. `inspect_migration_evidence_link()` verifies both ledgers and classifies LINKED/orphaned/dangling/conflict states. The explicit `reconcile_migration_evidence_commit()` operation repairs only a verified `ORPHANED_QDAS_EVENT`, uses the preserved original payload, serializes recovery with a per-event OS advisory lock (automatically released on process exit), and re-verifies both ledgers; repeated calls after success are idempotent. A persistent lock file is reused after a crash; lock ownership is held by the kernel rather than inferred from stale PID text. This is explicit recovery, not atomic commit or automatic background recovery, and the assurance append may have committed before an error surfaced. Crash-safe recovery across process termination and storage failure remains a Phase 1 blocker.

These are source observations, not runtime verification. Do not relabel any of the above as authenticated approval, sandboxing, or completed Phase 1 until independent enforcement and adversarial evidence exist.
- [ ] Full 1.1.0 regression suite and required Windows/Linux/macOS matrix pass on the same commit.
- [ ] No unresolved critical/high migration identity, planner, worker, authorization, ledger, snapshot or workspace defects.
- [ ] Owner-controlled trust store, exact digest/revocation, and approval/execution-time freshness checks pass.
- [ ] Worker qualification has independently collected conformance evidence.
- [ ] Human approval uses an authenticated trusted host channel.
- [ ] Filesystem/process/environment/secret/network limits are enforced by OS sandbox or equivalent host-controlled boundary.
- [ ] Workspace/recovery and concurrency adversarial tests pass.
- [ ] CLI, PR description, public docs, internal specs, schemas, traceability and package contents agree.
- [ ] Unsupported host boundaries remain propose-only/blocked/unsupported.


#### Six-workstream source-audit completion (2026-11-16)

The dedicated six-workstream review is recorded in [Phase 1 Safety Review — Six-Workstream Source Audit](PHASE_1_SIX_WORKSTREAM_SOURCE_AUDIT_2026-11-16.md). The review covers the trust store, host approval, worker qualification, bounded process execution, snapshot/workspace materialization, and migration authorization/step boundary.

**Source-audit disposition: AUDITED — OPEN for all six workstreams.** This closes the requested source-inspection pass only. It does not pass Gate F, upgrade any test to TEST_VERIFIED, or establish independent verification. The report records each observed foundation, material limitation, and required closure evidence. In particular, native Windows handle/reparse-point-safe snapshot/workspace traversal (currently fail-closed), authenticated human identity, independently collected worker conformance, enforced filesystem/network/environment/secret/resource isolation, crash-safe lifecycle/reconciliation, and same-revision cross-platform adversarial evidence remain release blockers. Windows DACL and Job Object changes are source-present but not test-verified.

**Additional fail-closed hardening (2026-11-16):** Windows snapshot capture and workspace source opening no longer use the known-racy path-based fallback. They now reject the operation until native handle-relative, reparse-point-safe traversal is implemented. A POSIX reconciliation lock now requires no-follow opening, current-user ownership, a single link, and exact `0600` permissions; tests cover owner/mode/link count plus symlink and hard-link rejection. Process-tree cleanup failure is now surfaced as `BLOCKED` rather than allowing a false PASS. The new tests are source additions only and have not been executed. These changes reduce unsafe fallback behavior but do not close Phase 1.

### Package-manifest and test/workflow consistency review (updated 2026-11-19)

A read-only release-surface review compared the current Git tree, `PUBLIC_FILES.txt`, `MANIFEST.in`, the setuptools configuration, the release builder, and the wheel-content regression test.

- `PUBLIC_FILES.txt` contains 190 unique entries; `MANIFEST.in` contains the exact same 190 paths. No internal deep-audit documents or GitHub Actions workflow files are included in the public source archive allowlist.
- The review found that the allowlist omitted three QDAS integration modules required by the 1.2.0 source runtime: `qyrenith_engine/analysis_qdas.py`, `qyrenith_engine/dynamic_audit_qdas.py`, and `qyrenith_engine/migration/qdas_step.py`. All three are now included in both manifests.
- `tests/test_release_contents.py` now includes all three modules in its expected wheel inventory and adds an import smoke test for `qyrenith_engine`, the migration QDAS integration, static-analysis QDAS integration, and dynamic-audit QDAS integration. This specifically guards against a source archive/wheel that contains an initializer but omits a module imported by that initializer.
- A source-level parity check against the current recursive Git tree confirms that every `qyrenith_engine/**/*.py` module is present in the public archive manifest, every engine module is represented in the wheel inventory assertion, the six 1.2.0 runtime/policy regression suites are included in the public source archive, and the 190 `PUBLIC_FILES.txt` entries exactly match the 190 `MANIFEST.in` include directives. This is a static source check, not a package build or test execution.
- The branch has no `.github/workflows/` files. GitHub Actions remain disabled by owner direction; no workflow was restored and no CI run was triggered.
- The earlier SECURITY.md correction and the 2026-11-19 Advanced Assurance documentation reconciliation remain in effect. The four AA ADRs, all 70 AA requirements, and all 27 diagnostic domains are recorded as owner-accepted scope; this does not advance implementation or verification states.

The packaging correction is **IMPLEMENTED — NOT TEST-VERIFIED**. No package build, release archive, wheel, local test suite, cross-platform test matrix, or CI was executed during this review. The independent local/external verification route remains mandatory before release.

### Dynamic QDAS input-boundary hardening (2026-11-19)

The QDAS dynamic process-capture wrapper now requires an explicit bounded timeout and rejects missing/invalid values instead of silently replacing them with the 120-second default; it rejects missing or unknown oracle values instead of silently downgrading them to HEURISTIC; validates argv shape, count, length, and NUL content before launching a process; and always obtains the report from the shared bounded process runner. Caller-supplied report mappings can no longer bypass process execution. Targeted negative regression tests were added for missing/invalid timeout values, unknown/missing oracles, empty/oversized/excessive-count/NUL-containing argv, and attempted caller-report injection.

The returned scenario result now keeps `execution_status` separate and reports overall/behavior status as `NOT_RUN` with `behavior_verified=false`; a process exit PASS cannot be mistaken for a passing behavioral oracle. This is a narrow input-contract and evidence-provenance hardening change, not completion of DB-01..DB-12 or the dynamic/behavioral audit module. The current wrapper still captures a bounded process report; it does not implement the full scenario setup/actions/expected-observation/cleanup lifecycle, evaluate behavioral oracles, or provide RVL isolation. The new tests have **not been executed** and remain source-level test additions only.

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
- **RECONCILED DRAFT:** documents have been aligned but still require owner acceptance (not applicable to the four now-accepted AA ADRs).
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

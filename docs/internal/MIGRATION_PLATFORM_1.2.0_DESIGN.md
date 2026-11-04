# Qyrenith 1.2.0 Migration Platform — Engineering Baseline

**Status:** In development  
**Baseline:** Qyrenith 1.1.0, commit 129fde8a761c46a9e78f0ca38acc26cd115fecae  
**Implementation branch:** feature/1.2.0-universal-migration-core

## Product objective

Build a domain-neutral migration control plane. Qyrenith owns identity, typed transitions, evidence qualification, deterministic route planning, authorization, per-step assurance, target isolation, and final verdicts. Domain-specific transformation knowledge and workers remain replaceable providers.

The core must not assume Minecraft, a loader, a build system, a programming language, an AI provider, or a worker implementation language.

## Non-negotiable invariants

1. A migration route is a directed sequence of individually qualified transitions.
2. Version upgrades, loader conversions, framework changes, platform migrations, toolchain changes, dependency migrations, and profile changes are distinct transition types.
3. A transition that changes multiple independent identity dimensions is rejected; the planner must represent it as ordered atomic transitions.
4. A worker capability declaration is not proof that a transformation exists.
5. OBSERVED, INFERRED, UNKNOWN, CONFLICTED, STALE, and VERIFIED knowledge remain distinct.
6. VERIFIED knowledge requires exact source/target scope, evidence provenance, a reviewer identity, a verification timestamp, and non-expired validity.
7. Agent/worker output never authorizes a final migration verdict.
8. Each multi-target result is planned independently from the same source identity.
9. No target is promised when a complete verified route is unavailable.
10. Existing 1.1.0 commands, state, package behavior, and release contents remain compatible unless an explicit reviewed migration says otherwise.

## Threat model and trust boundaries

### Assets to protect

- The user's original project tree, source files, uncommitted changes, dependency declarations, and build outputs.
- The exact source and target identities selected by the user.
- The evidence and compatibility claims used to justify a migration edge.
- The worker implementation and version selected for a transition.
- The migration plan, per-step observations, diff, post-state, and recovery references.
- The final Qyrenith verdict and the authority that is permitted to cause project changes.

### Adversaries and failure modes

The design assumes that repository content, imported knowledge, worker manifests, worker processes, AI outputs, and build outputs may be malformed, stale, misleading, compromised, or deliberately hostile. A normal user may also provide an incomplete project identity or a target request that cannot be supported by the available evidence.

The first implementation slice does not attempt to make hostile worker code safe to execute. The current worker registry never launches code. Any future execution implementation must treat the worker as untrusted code running with potentially dangerous operating-system capabilities unless a real isolation boundary proves otherwise.

### Trust boundaries and controls

| Threat | Current control | Residual risk / required future control |
|---|---|---|
| Malformed or oversized catalog/manifest input | Strict object fields, duplicate-key rejection, schema version checks, bounded JSON size, array bounds, canonical digest verification | JSON-imported catalogs are untrusted by default and require an exact-catalog local allowlist whose trust digest is bound into route plans. A valid digest or local policy does not authenticate the publisher/reviewer or prove that the claims are truthful. A protected trust store and signed or independently anchored records remain future work. |
| Stale or future-dated compatibility knowledge | Explicit UTC timestamps, expiry, one route evaluation instant, exact source/target identity, conflict groups, no automatic promotion | Clock trust and reviewer identity are not cryptographically established. Revalidation and source-authority policy remain future work. |
| Compound transition hidden under a narrower transition kind | One shared transition-scope validator is used by both route edges and worker scopes | New transition kinds require explicit allowed-dimension rules and regression fixtures. |
| Wrong worker version, scope, or capability set | Worker ID and version are pinned; manifest digest, exact scope, transition kind, and required capabilities must match | The registry does not inspect actual worker bytes or run the implementation. A later launcher must verify the measured executable digest before execution. |
| Expired or substituted worker qualification | Qualification is tied to the exact manifest digest and a bounded validity interval; route-wide assessment uses the route plan's timestamp | Qualification records are data, not signatures. The conformance runner, signer/reviewer authentication, and revocation/renewal workflow are not implemented. |
| Worker self-report or fabricated success | WORKED/NO_CHANGE/BLOCKED/FAILED are distinct; worker output never directly creates PASS; ledger PASS requires diff, post-state, evidence, commit, and qualified worker provenance | The ledger is not integrated into the managed migration workflow and does not independently inspect referenced artifacts or commits yet. |
| Local ledger tampering or interrupted writes | Strict canonical JSONL, duplicate-key rejection, sequence/hash chain, fail-closed lock, bounded records, atomic replacement, file and directory synchronization where supported | An actor able to replace the whole ledger can recompute the chain. A protected trust anchor or remote append-only witness is deferred. |
| Permission escalation or confused deputy | Plan-bound authorization intersects requested permissions with a local policy allowlist and the exact worker manifest; it binds plan, assessment, policy, worker, qualification, expiry, and stricter resource limits | Approver identity is not authenticated; policy persistence/signing and a runtime enforcement point remain future work |
| Excessive worker resource use | The manifest requires bounded timeout/input/output/change declarations | These are currently declarations only. A future executor must enforce them at runtime and add operating-system isolation. |
| Cross-target file leakage | Multi-target planning is independent; a snapshot-pinned filesystem-copy workspace API exists for isolated per-target copies | The workspace API is not yet integrated into multi-target execution and is not a Git worktree or OS/process sandbox. Multi-target execution remains prohibited until integration and isolation tests pass. |
| AI or provider hallucination | AI/provider output is not a trusted knowledge status; OBSERVED/INFERRED/UNKNOWN cannot qualify a transition | A human review or a separately governed evidence provider must establish VERIFIED claims. |
| Silent fallback to unsupported migration | Planner returns UNKNOWN, BLOCKED, or UNSUPPORTED instead of fabricating edges | Domain support must be published only after real transformation and end-to-end evidence exist. |

### Explicit authority levels

The following terms are intentionally non-interchangeable:

1. **Declared** — a manifest or transition says a worker or capability exists.
2. **Qualified** — a current reviewed qualification record matches the exact worker manifest and scope.
3. **Authorized** — a short-lived authorization record binds a policy decision to the exact plan, worker assessment, worker manifest/qualification, permission subset, resource ceilings, and expiry. The current record captures caller-supplied approval attribution but does not authenticate the approver or enforce permissions at runtime.
4. **Executed** — a controlled executor actually launched the pinned worker in an identified workspace. This layer is not implemented yet.
5. **Verified** — Qyrenith independently observed the required build/test/runtime results, source diff, post-state, and recovery/commit evidence. This end-to-end gate is not integrated with the new migration planner yet.

A transition may be PLANNED while its worker assessment is UNKNOWN or BLOCKED. A worker assessment may be QUALIFIED without being authorized or executed. No documentation, API, CLI, or report may turn those states into a migration-success claim.

### Acceptance criteria for the current slice

| Area | Acceptance condition |
|---|---|
| Identity and transition model | Every transition changes only the dimensions permitted by its declared kind; the same validator is used by route and worker scope records. |
| Knowledge | No OBSERVED/INFERRED/UNKNOWN/CONFLICTED/STALE claim can qualify a route. Conflicts block every claim in the conflicting exact scope. Expired or future-dated VERIFIED claims are unusable. |
| Route planning | The same input catalog, edge set, endpoints, hop limit, and evaluation timestamp produce the same route and digest. No missing route is fabricated. |
| Worker qualification | Only an exact worker ID/version, manifest digest, transition scope, capability set, current PASS qualification, and exact qualification-digest allowlist match under a time-valid local WorkerTrustPolicy can resolve QUALIFIED; this remains a record-trust state until a controlled conformance runner exists. |
| Authorization | Every grant is bound to the exact ordered route, assessment, policy, worker manifest, qualification, permission subset, resource ceiling, and expiry no later than qualification expiry. |
| Worker assessment | Every route edge has an ordered resolution; mixed states aggregate conservatively. Evaluation time must equal the route plan's timestamp. |
| Assurance | Invalid fields, paths, digest chains, stale locks, duplicate JSON keys, non-WORKED PASS reports, or missing worker provenance are rejected. |
| Packaging | Every public source file is present in both the deterministic archive allowlist and the source-distribution manifest. |
| Compatibility | 1.1.0 version metadata and existing runtime behavior are unchanged during 1.2.0 development. |

The executable conformance runner, authenticated approval/signing, isolated workspace executor, managed recovery integration, and end-to-end transformation validation are intentionally outside the acceptance boundary of this slice. The new authorization record is a policy artifact only; it is not an execution authority.

## Current implementation slice

The first 1.2.0 code slice introduces:

- MigrationIdentity: a stable, dimension-aware identity for a project state.
- TransitionKind and MigrationTransition: typed, directed, atomic migration edges.
- MigrationKnowledgeClaim and EvidenceReference: scoped claims with explicit provenance and review metadata.
- KnowledgeCatalog: rejects duplicate identifiers, validates every referenced claim against the exact transition scope, and treats JSON imports as untrusted unless an exact-catalog local trust policy is supplied.
- plan_route: deterministic shortest-route planning over enabled edges whose complete knowledge set is currently VERIFIED.
- plan_targets: independent plans for multiple targets, with explicit PLANNED, PARTIAL, UNKNOWN, BLOCKED, or UNSUPPORTED aggregate status.
- Canonical knowledge catalog export/import with duplicate-key rejection, digest verification, bounded parsing, idempotent merge, conservative conflict grouping, and explicit local trust policy for imported catalogs.
- JSON Schemas for migration knowledge, transition declarations, assurance records, worker contracts, and route worker assessments.
- An executable synthetic benchmark matrix covering all seven atomic transition kinds across Minecraft and non-Minecraft identity domains.
- A single-writer, atomic JSONL assurance ledger with sequence and SHA-256 hash-chain validation, explicit lock behavior, path checks, and strict PASS evidence requirements.
- Regression tests for unknown evidence, expired claims, scope mismatch, route composition, loader conversion typing, disabled edges, duplicate identifiers, and partial target results.

These are planning primitives only. They do not discover a project, modify files, invoke a worker, run a build, create a worktree, or declare a migration successful. The existing managed Minecraft workflow remains separate until an explicit integration phase and regression gate are complete.

## Planned implementation sequence

### MP-01 — Typed migration core
- [x] Dimension-aware project identity.
- [x] Explicit transition taxonomy.
- [x] Exact-scope verified knowledge gate.
- [x] Canonical ordering for set-like evidence, transition, and worker-manifest fields.
- [x] Deterministic shortest route planner.
- [x] Independent multi-target route planning.
- [x] Unit tests and CI matrix integration.
- [x] Synthetic domain-neutral benchmark fixtures for all transition kinds.
- [ ] Review and acceptance of the initial public data contracts.

### MP-02 — Knowledge lifecycle
- [x] Define evidence references with origin, locator, observation time, and optional SHA-256 digest.
- [x] Add canonical import/export, duplicate-key rejection, content-digest verification, and bounded parsing.
- [x] Detect contradictory assertions for identical subject/source/target scopes; explicit CONFLICTED markers block the full group.
- [x] Add explicit verification timestamps and expiry checks without automatic promotion.
- [ ] Add a reviewed revalidation workflow and evidence-provider conformance.
- [ ] Add signed or independently anchored evidence only if a concrete threat model requires it.
- [x] Keep remote retrieval opt-in; the catalog performs no network access.

### MP-03 — Migration assurance ledger
- [x] Define immutable step records and a versioned JSON schema.
- [x] Bind records to source/target identities, plan and pre-state digests, worker result, changed files, diff, evidence, post-state, artifact, commit, and recovery reference.
- [x] Add tamper-evident sequence/hash-chain verification and atomic file replacement.
- [x] Fail closed on an existing writer lock; stale-lock recovery remains an explicit operator action.
- [x] Keep worker WORKED separate from Qyrenith's evaluated verdict; PASS requires independent evidence, diff, post-state, commit, and exact worker manifest/qualification digests.
- [ ] Integrate ledger records with existing managed migration steps.
- [ ] Add richer lifecycle events, retention policy, and recovery integration.

### MP-04 — Worker contract and capability qualification
- [x] Define version-pinned worker identity, implementation digest, exact source/target scopes, transition kinds, permissions, capabilities, and resource limits.
- [x] Define a qualification record bound to the exact manifest digest, conformance suite identity/version/digest, result digest, reviewer, and expiry.
- [x] Add local registry resolution for NOT_SELECTED, NOT_REGISTERED, INCOMPATIBLE, UNQUALIFIED, STALE, and QUALIFIED.
- [x] Add route-wide worker qualification assessment bound to the exact route plan digest and evaluation timestamp.
- [ ] Implement and independently review the actual conformance-suite runner and qualification issuance workflow.
- [x] Discovery never grants execution permission.
- [x] No automatic download or execution of unknown workers.

### MP-05 — Migration execution orchestration
- [x] Add a plan-bound authorization record with per-transition worker provenance.
- [x] Re-resolve exact worker qualification at approval time and reject changed or expired qualification.
- [x] Intersect requested permissions and resource limits with policy and worker-manifest ceilings.
- [x] Require authorization expiry to precede every worker qualification expiry.
- [x] Add a pre-side-effect validation gate that rechecks plan, assessment, policy, grant scope, current worker qualification, permissions, limits, and expiry.
- [x] Add strict canonical JSON interchange for authorization and policy records, with content-digest verification.
- [ ] Authenticate the approver and protect policy/approval records with a trusted signing or storage boundary.
- [ ] Add a runtime enforcement point that consumes each grant immediately before side effects.
- Execute one transition at a time.
- Preserve backup, pre/post snapshots, validation, diff, commit, and recovery gates.
- Do not replace the current Minecraft workflow until equivalent regression coverage is complete.

### MP-06 — Isolated multi-target workspaces

- [x] Add a deterministic, bounded, read-only project snapshot with content hashes and exact exclusion policy.
- [x] Record symbolic links without following them; reject special filesystem objects and non-portable paths.
- [x] Detect observable concurrent file/directory changes during capture.
- [x] Revalidate a project against the exact captured snapshot and report changed paths.
- [x] Expose read-only `snapshot capture` and `snapshot verify` CLI operations with explicit match/change exit codes.
- [x] Validate snapshot schema, canonical serialization, release packaging, and CLI behavior in CI.
- [x] Add single-target isolated workspace materialization from a verified source snapshot; reject symlinks and remove partial workspaces on failure.
- [x] Bind each workspace descriptor to its workspace ID/path, target identity, and source snapshot digest; validate persisted descriptor metadata before baseline checks.
- [x] Add bounded batch creation with duplicate-target rejection, source revalidation between copies, and rollback of prior copies on failure.
- [x] Test target-to-target filesystem independence and rollback when the source changes mid-batch.
- [x] Bind every target copy to the same source snapshot fingerprint.
- [ ] Add persistent successful-workspace lifecycle/cleanup management.
- [ ] Select and verify a Git-aware isolation strategy (worktree or equivalent) when commit metadata is required.
- [ ] Bind every target to the same Git commit when commit metadata is available.
- [x] Verify file-level independence between target copies; process-level isolation remains deferred.
- [ ] Keep build, evidence, and verdicts independent.

### MP-07 — Minecraft reference integration
- Preserve existing same-loader migration behavior.
- Add a cross-loader reference only after a real transformation and its exact evidence are available.
- No fabricated Fabric/Forge/NeoForge mappings.

### MP-08 — Generic domain adapters and qualification
- Add one non-Minecraft reference domain after the core contract is stable.
- Publish domain maturity only from executable end-to-end evidence.

## Explicit non-claims

The current code does not provide universal automatic code conversion, API mapping discovery, Minecraft cross-loader conversion, Git-worktree or OS-level process isolation, build execution, or production migration support for any newly added domain. Worker manifests and qualification records are validated, but the conformance suite is not executed or signed by this registry. The assurance ledger exists as a standalone primitive but is not yet bound to the existing managed migration workflow. A route being PLANNED means only that the current knowledge catalog qualifies its typed edges under the bound local trust decision; execution authorization and migration success are separate future gates.


---

## 1.2.0 Deep-Audit and Development-Assurance Integration

The migration platform is now governed by the complete deep-audit specification set under [`docs/internal/deep-audit/`](deep-audit/README.md). The master architecture, QDAS specification, module contracts, evidence model, and implementation plan are normative for the remaining 1.2.0 work.

### Required delivery sequence

1. Complete and cross-review the deep-audit documentation set.
2. Finish and independently validate the existing migration-platform slice and its known defects.
3. Implement Qyrenith Development Assurance System (QDAS).
4. Implement the fourteen remaining capability modules with QDAS-assisted development.
5. Complete cross-module acceptance and independent release verification.

### Existing migration work is not yet end-to-end

The current identity, knowledge, planner, worker, authorization, ledger, snapshot, and filesystem-copy workspace primitives must not be described as a completed migration executor. The remaining work is specified in [Migration Platform Integration](deep-audit/MIGRATION_PLATFORM_INTEGRATION_SPEC.md). In particular, conformance execution, authenticated approval, runtime permission enforcement, process isolation, managed workflow integration, transformation execution, recovery, and target build/behavior verification require their own implementation and evidence.

### QDAS relationship

QDAS is the first new implementation milestone after the existing migration work is stabilized. It captures development failures, classifies them, builds evidence-backed root-cause hypotheses, proposes bounded repairs, and verifies the unchanged baseline checks after repair. It is not an OS sandbox, cannot self-certify Qyrenith, and cannot implicitly write, install dependencies, access the network, commit, or publish.

### Release rule

All accepted requirements remain release-blocking until implemented and verified. These design documents do not claim implementation completion. See [Implementation and Acceptance Plan](deep-audit/QYRENITH_1_2_0_IMPLEMENTATION_AND_ACCEPTANCE_PLAN.md).


The authoritative requirement-to-code/test/evidence/dependency/status map is [the 1.2.0 Requirement Traceability Matrix](deep-audit/REQUIREMENT_TRACEABILITY_MATRIX.md). Its status values are deliberately conservative; foundational code is not treated as full lifecycle acceptance.

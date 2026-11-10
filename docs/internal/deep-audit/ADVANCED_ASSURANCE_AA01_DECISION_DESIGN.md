# Advanced Assurance AA-01 — Owner Decision Design Proposal

**Status:** OWNER-APPROVED DECISION BASELINE — DESIGN ONLY  
**Target release:** Qyrenith 1.2.0  
**Scope:** Design analysis for the seven unresolved AA-01 decisions  
**Implementation status:** Design only; no runtime, schema, or test implementation is authorized by this document  
**Architecture constraint:** The existing five planes, QDAS-first sequence, migration safety gate, and evidence model remain canonical.

## 1. Purpose and decision discipline

This document records the alternatives, consequences, and acceptance conditions for the seven AA-01 owner decisions. The owner approved all seven decision directions on 2026-11-10. The accepted decisions are binding design constraints for the 1.2.0 documentation and subsequent implementation planning; this document does not claim runtime implementation or verification.

The owner also approved extensibility and supportability as a first-class architectural requirement. The dedicated `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md` defines that requirement family.

Approval is deliberately scoped: it does not automatically accept all 70 proposed PR #3 AA requirements, the four proposed AA ADRs, every diagnostic domain, every proposed product pillar, or any implementation. Those remain subject to their own reconciliation and approval gates. Physical evidence-storage backend selection and final verification-profile inventories remain explicitly deferred pending comparison/catalog evidence.

AA remains a cross-cutting assurance contract. It must reuse the five existing planes and the QDAS, migration, evidence, and reproducible-lab foundations. It must not create a parallel execution engine, a second evidence ledger, or a separate verdict authority.

## 2. Decision 1 — Per-check outcome states and legacy mapping

### Problem

The existing master architecture defines scoped verification verdicts, including INCONCLUSIVE, while the PR #3 draft proposes seven per-check states. The two vocabularies serve different purposes and must not be conflated.

### Recommended model

Use eight mutually exclusive per-check terminal outcomes:

| Outcome | Meaning | Required interpretation |
|---|---|---|
| PASS | The check executed and satisfied its declared contract. | Positive evidence exists for the exact scope. |
| FAIL | The check executed and violated its declared contract. | A supported failure finding exists. |
| BLOCKED | A prerequisite, policy, integrity, or authorization gate prevented execution or continuation. | Not a subject-level failure; not a pass. |
| INCONCLUSIVE | The check executed but could not reach a defensible conclusion because of limits, ambiguity, missing oracle, or conflicting observations. | Preserve partial evidence and the reason. |
| UNKNOWN | The system cannot determine the check state from available trustworthy information. | Never normalize to PASS or zero findings. |
| NOT_RUN | The check was deliberately not executed, omitted by scope, or not scheduled. | A machine-readable reason is mandatory. |
| UNSUPPORTED | No qualified implementation can evaluate the requested language, domain, version, or check contract. | Unsupported coverage remains visible. |
| ERROR | The check implementation or execution infrastructure failed unexpectedly. | Distinguish this from a subject-level FAIL. |

INCONCLUSIVE is added to the seven-state proposal because the master architecture and QDAS already require it as a meaningful execution result. UNKNOWN remains distinct: INCONCLUSIVE means an evaluation occurred but did not settle the claim; UNKNOWN means the system lacks enough trustworthy information to classify the state.

### Legacy compatibility

- Preserve the original legacy status and source record.
- Map only when legacy semantics are unambiguous.
- A legacy success may map to PASS only when its scope and evidence satisfy the new check contract.
- A legacy failure may map to FAIL only when it represents a checked-subject violation, not an infrastructure failure.
- A skipped state maps to NOT_RUN, BLOCKED, or UNSUPPORTED only when its reason is known; otherwise map to UNKNOWN and retain the raw value.
- A legacy error maps to ERROR unless evidence proves that the subject itself failed.
- Unknown legacy values remain UNKNOWN; never guess.
- Compatibility output may render legacy labels, but the canonical stored state remains the new typed outcome.

### Acceptance conditions

Define a versioned mapping table for every legacy state; test every mapping and ambiguous case; prove round-trip preservation of the raw legacy value; and verify that no conversion can upgrade missing or weaker evidence into PASS.

**Owner decision (2026-11-10): ACCEPTED.** The eight-state model and no-false-PASS rules are approved. The exhaustive legacy mapping table remains an implementation prerequisite and must be based on actual 1.1.0/1.2.0 legacy values; ambiguous values remain UNKNOWN with raw-value preservation.

## 3. Decision 2 — Persistent evidence storage

### Problem

QDAS already specifies an append-only event ledger with canonical serialization, digests, sequence/parent linkage, bounded JSONL records, and explicit limitations. AA must not create a competing store or imply that a local hash chain authenticates its writer.

### Options

| Option | Strengths | Risks / costs |
|---|---|---|
| Canonical append-only journal plus content-addressed artifacts | Portable; preserves event order and lineage; large artifacts are stored separately and verified by digest. | Requires crash recovery, locking, atomicity, retention, and index rebuilding. |
| Embedded transactional database | Strong local transactions and indexed queries; useful for concurrent metadata access. | Adds format/migration and locking complexity; portability and corruption recovery need explicit treatment. |
| Database plus append-only journal | Efficient queries with durable event history. | Two sources of truth unless one is explicitly authoritative; more complex consistency and recovery. |

### Recommended model

Use one logical evidence system with these layers:

1. **Canonical event journal:** authoritative ordered record of events, decisions, state transitions, and evidence references. Reuse the QDAS ledger contract rather than inventing a second journal.
2. **Content-addressed artifact store:** immutable payloads keyed by cryptographic digest. Store large logs, reports, manifests, and test artifacts outside the journal; journal records bind their digest, media type, size, scope, and retention class.
3. **Rebuildable query index:** optional derived index. It is never authoritative and can be deleted and reconstructed from validated journal/artifact records.
4. **External trust anchor:** optional later capability for signed checkpoints or remote anchoring. Do not claim authenticity or protection against full-store replacement until a concrete identity and key-management design exists.

A storage backend may use a transactional database internally only if the journal remains the canonical source of truth or the database transaction/recovery semantics are explicitly made canonical. Do not select a backend solely for convenience.

### Required guarantees

- Atomic commit of a logical event and its artifact references.
- Crash-safe recovery with detection of truncated, duplicated, reordered, or conflicting records.
- Single-writer or correctly coordinated multi-writer semantics.
- Stable canonical serialization and schema evolution.
- Explicit retention, redaction, deletion, export, and privacy policy.
- Bounded storage and query resource use.
- Portable backup/restore and migration between supported platforms.
- Fail-closed validation; never silently rebuild missing evidence as if it were original.
- Clear separation of integrity, authenticity, and independent verification.

### Acceptance conditions

Run fault-injection tests at every write boundary; test concurrent writers, partial writes, disk-full conditions, corruption, restore, export/import, redaction, and schema upgrades. Compare candidate backends using the same acceptance suite before selecting one.

**Owner decision (2026-11-10): ACCEPTED.** The one-logical-evidence-system architecture is approved. QDAS remains the canonical journal authority, with content-addressed artifacts and a rebuildable non-authoritative index. A physical backend is deliberately NOT SELECTED until measured portability, atomicity, privacy, concurrency, and recovery comparisons are complete.

## 4. Decision 3 — Process isolation and host enforcement

### Problem

The reproducible lab already defines isolation levels L0–L5. QDAS and migration specifications require host-enforced isolation for side-effecting workers. AA must not introduce a weaker or contradictory definition.

### Recommended model

Adopt the existing RVL L0–L5 levels as the only canonical isolation scale:

- L0: process bounds only.
- L1: dedicated temporary workspace.
- L2: restricted environment and filesystem scope.
- L3: OS-enforced process/filesystem/network isolation.
- L4: disposable container or VM boundary with measured policy.
- L5: independently provisioned ephemeral environment with retained provenance.

A directory copy is at most L1. A command allowlist, manifest, container label, or declared permission list is not proof of isolation.

Define platform-specific isolation providers behind one Qyrenith-owned capability contract. Each provider must report actual enforcement, unsupported controls, host/version identity, and evidence. Do not silently downgrade an L3/L4 request to L0/L1.

### Execution policy

- Read-only discovery and non-side-effecting analysis may run under a separately declared bounded policy.
- Any operation that can modify project files, spawn uncontrolled child processes, access secrets, install dependencies, or use the network requires an enforceable host boundary meeting the approved policy.
- If the host cannot enforce the required boundary, the operation remains PROPOSE_ONLY and returns BLOCKED or UNSUPPORTED with the missing capability.
- The first release must not claim universal cross-platform isolation. It may support a measured subset of OS/runtime combinations and explicitly reject the rest.

### Acceptance conditions

For every supported OS, test filesystem escape, symlink traversal, child-process escape, environment/secret leakage, network egress, resource exhaustion, cleanup, and boundary teardown. Evidence must demonstrate enforcement rather than merely report configuration.

**Owner decision (2026-11-10): ACCEPTED.** RVL L0–L5 remains the only canonical isolation scale. Platform-specific enforcement is capability-discovered and must be independently tested. No silent downgrade is permitted; unsupported enforcement keeps side-effecting work PROPOSE_ONLY/BLOCKED/UNSUPPORTED.

## 5. Decision 4 — Verification profiles

### Problem

Profile names such as Baseline, Standard, and Deep Audit are useful UX, but a profile without an exact check inventory and resource policy is an untestable label.

### Recommended model

Define profiles as versioned, immutable policy manifests, not hard-coded names that imply coverage. Each profile must specify:

- exact required check IDs and versions;
- optional checks and explicit exclusions;
- supported project/language/domain scopes;
- prerequisite and dependency graph;
- required evidence and oracle;
- isolation level per check class;
- network and installation policy;
- CPU, memory, wall-clock, process, output, and artifact budgets;
- concurrency and cancellation policy;
- behavior for BLOCKED, INCONCLUSIVE, UNKNOWN, NOT_RUN, UNSUPPORTED, and ERROR;
- freshness/reuse rules and evidence retention;
- profile schema/version and digest.

A user-facing profile name is a stable alias for one immutable manifest version. Changing its check inventory or budgets creates a new version and digest.

### Candidate profiles (not yet approved)

- **Baseline:** bounded, read-only, high-signal checks; no network or project mutation.
- **Standard:** Baseline plus supported dependency, configuration, security, and selected behavioral checks within explicit budgets.
- **Deep Audit:** broadest qualified coverage, including expensive dynamic, fuzz, formal, and domain-specific checks where supported.

These names must not be advertised as complete until the exact inventory, dependencies, platform support, resource ceilings, and coverage denominator are defined.

### Acceptance conditions

For every profile version, generate a machine-readable inventory and test that every mandatory check is either executed or produces a visible non-pass outcome. Verify that exclusions and unsupported coverage appear in reports and affect the aggregate decision.

**Owner decision (2026-11-10): ACCEPTED.** Verification profiles must be immutable, versioned manifests with exact check IDs/versions, scope, prerequisites, exclusions, evidence requirements, isolation policy, network policy, and resource budgets. Baseline/Standard/Deep Audit remain candidate names only; final profiles are deferred until the checker catalog and resource model exist.

## 6. Decision 5 — Network-enabled providers

### Problem

External providers can improve coverage but introduce remote data trust, egress, privacy, availability, cost, reproducibility, and supply-chain risks.

### Recommended first-release policy

- Network access is disabled by default at every layer.
- No provider may initiate network access merely because it is installed, registered, or referenced by a profile.
- Keep network-enabled providers out of the default 1.2.0 assurance path.
- If a later owner-approved profile enables a provider, require explicit per-run approval, exact endpoint/operation allowlists, bounded requests/responses, timeout and retry limits, TLS validation, redirect/DNS/IP policy, secret redaction, provenance, provider/version pinning, and an auditable record of data sent and received.
- No telemetry, analytics, remote code execution, remote repair, or automatic package installation by default.
- Remote results are untrusted inputs. They require schema validation, provenance, freshness checks, and independent local verification where the claim permits it.
- If a required check depends on a disabled provider, report BLOCKED or UNSUPPORTED; do not silently skip it or downgrade the profile.

### Acceptance conditions

Test denied egress, DNS rebinding/redirect behavior, endpoint allowlist bypass, response-size exhaustion, secret leakage, provider substitution, stale results, and deterministic replay with captured fixtures.

**Owner decision (2026-11-10): ACCEPTED.** Network access is disabled by default at every layer. No network-dependent mandatory check is permitted in the first 1.2.0 release. Any later provider requires a separate explicit owner-approved threat model and per-run authorization.

## 7. Decision 6 — Aggregate project-level assurance decision

### Problem

Per-check outcomes cannot directly serve as the overall project decision. A single green badge would hide missing coverage, unsupported domains, stale evidence, and unresolved conflicts.

### Recommended model

Keep the aggregate decision as a separate typed object, computed by a policy evaluator from the exact profile, scope, check outcomes, coverage, freshness, evidence integrity, and required independent-verification level.

Proposed primary aggregate states:

| State | Meaning |
|---|---|
| ASSURED | Every mandatory check passed; mandatory coverage and evidence are complete and fresh; no blocking conflict or unresolved required limitation remains. |
| NOT_ASSURED | At least one mandatory check failed, or an explicit policy condition disproves the assurance claim. |
| BLOCKED | A mandatory prerequisite, authorization, integrity, trust, or execution boundary prevented a valid decision. |
| INCONCLUSIVE | Required checks ran but evidence, oracle, confidence, or resource limits prevent a defensible conclusion. |
| PARTIAL | The evaluated scope is explicitly narrower than the requested/declared scope, or optional/declared coverage is missing. This is never equivalent to ASSURED. |

The aggregate record must include the exact project/revision/snapshot, profile digest, requested and evaluated scope, mandatory and optional check inventory, outcome counts, coverage denominator, exclusions, unsupported areas, stale evidence, conflicts, policy version, evaluator version, and evidence references.

### Precedence and safety rules

- A mandatory FAIL yields NOT_ASSURED.
- A mandatory integrity/trust/authorization blocker yields BLOCKED.
- Missing mandatory evidence or unresolved required uncertainty yields INCONCLUSIVE or BLOCKED according to the cause; never ASSURED.
- Missing optional coverage may yield PARTIAL if policy allows it and the omission is explicit.
- A mandatory UNSUPPORTED or NOT_RUN check prevents ASSURED.
- PASS count alone never determines the aggregate state.
- The aggregate state must be reproducible from the retained decision inputs and policy version.

### Legacy compatibility

Keep old workflow status labels as presentation/compatibility fields only. Do not map a legacy generic SUCCESS to ASSURED unless the exact historical profile, coverage, and evidence satisfy the new contract. Otherwise use PARTIAL, UNKNOWN, or INCONCLUSIVE and retain the raw legacy value.

### Acceptance conditions

Test every precedence combination, conflicting checks, mandatory/optional scope, missing evidence, expired evidence, partial coverage, unsupported checks, and replay of the same decision inputs. Prove no path produces ASSURED with an unmet mandatory condition.

**Owner decision (2026-11-10): ACCEPTED.** The separate aggregate states ASSURED, NOT_ASSURED, BLOCKED, INCONCLUSIVE, and PARTIAL are approved with the safety and precedence rules in this document. ASSURED is impossible when any mandatory condition, evidence, or coverage requirement is unmet.

## 8. Decision 7 — Reproducibility outcome vocabulary

### Problem

Reproducibility is cross-cutting and already has a dedicated lab and cross-environment specification. It must not become another execution engine or be collapsed into a check result.

### Recommended model

Use a separate reproducibility assessment with these outcomes:

| Outcome | Meaning |
|---|---|
| REPRODUCIBLE | The declared replay contract was satisfied and normalized outputs/artifacts matched within the explicitly defined equivalence rules. |
| NON_REPRODUCIBLE | A valid comparable replay ran under the declared equivalent inputs/environment and produced a material mismatch. |
| INCONCLUSIVE | A replay occurred but input/environment equivalence, oracle quality, or comparison evidence was insufficient. |
| BLOCKED | A required replay prerequisite or policy boundary prevented execution. |
| NOT_RUN | No replay was attempted; reason is mandatory. |
| UNSUPPORTED | The requested replay mode or platform combination has no qualified implementation. |

ERROR remains a per-check/execution outcome; the reproducibility assessment should classify an execution error as BLOCKED or INCONCLUSIVE only according to the failure semantics, while retaining the underlying ERROR event.

### Required dimensions

- **Same-environment repeatability:** same pinned project snapshot, toolchain, dependencies, commands, configuration, and relevant environment.
- **Cross-environment reproducibility:** compare across explicitly named OS/architecture/runtime/toolchain matrix cells.
- **Artifact reproducibility:** compare normalized or byte-identical build outputs under a declared equivalence contract.
- **Behavioral reproducibility:** compare observable behavior against a versioned oracle and controlled fixtures.
- **Evidence reproducibility:** allow an independent party to replay the claim from retained manifests and artifacts.

Do not use one undifferentiated percentage. Each dimension reports its own scope, denominator, equivalence rule, evidence, exclusions, and result.

### Acceptance conditions

Test deterministic matches, material mismatches, environment drift, dependency drift, missing artifacts, stale manifests, nondeterministic timestamps/paths, normalization mistakes, and independent replay. Prove that an environment mismatch is not mislabeled as a source-code failure.

**Owner decision (2026-11-10): ACCEPTED.** The separate reproducibility states REPRODUCIBLE, NON_REPRODUCIBLE, INCONCLUSIVE, BLOCKED, NOT_RUN, and UNSUPPORTED are approved. RVL remains the sole execution/replay engine; reproducibility dimensions remain separately reported.

## 9. Cross-decision invariants

1. Per-check outcomes, aggregate assurance decisions, reproducibility outcomes, evidence/claim lifecycle states, and module lifecycle states are separate typed vocabularies.
2. No UNKNOWN, INCONCLUSIVE, BLOCKED, NOT_RUN, UNSUPPORTED, stale, or conflicted evidence can silently become PASS or ASSURED.
3. QDAS remains the development-assurance lifecycle; AA remains the cross-cutting assurance contract.
4. RVL remains the execution/replay engine; no duplicate runner is introduced.
5. QDAS ledger/evidence lineage remains the single logical evidence authority; no parallel AA store is created.
6. OS-enforced isolation is an observed host capability, not a declaration in a manifest.
7. Network and side effects remain deny-by-default and exact-scope approved.
8. The policy evaluator is deterministic for identical normalized inputs, policy versions, and evidence.
9. All decisions are versioned and traceable to requirements, tests, threats, and evidence.
10. An owner-approved deferral must state its release impact and cannot be represented as acceptance.

## 10. Required follow-up artifacts before AA-01 acceptance

After the owner reviews this proposal:

1. Record each decision as ACCEPTED, REJECTED, or DEFERRED in an owner-approved decision log.
2. If accepted, create or update the relevant ADRs; do not silently change existing ADR status.
3. Reconcile the AA architecture and acceptance matrix with the five-plane master, QDAS, RVL, migration authorization, and evidence model.
4. Add exact schema/API contracts and legacy compatibility fixtures.
5. Update the 70 AA requirement rows with concrete implementation owners, acceptance test specifications, and evidence artifact types.
6. Resolve overlaps with DA/QDAS/RVL/MI/DI/RCA/OI requirements without deleting stable IDs silently.
7. Update the 1.2.0 plan and requirement matrix in the same documentation change.
8. Only after these gates, define implementation slices. AA checker runtime and project-model work must respect Phase 1 migration hardening and Phase 2 QDAS-first delivery.

## 11. Explicit non-claims

This document does not mean that the proposed states, profiles, storage backend, isolation providers, network policy, schemas, APIs, checkers, or aggregate evaluator are implemented or accepted. It does not authorize PR merges, branch retargeting, code changes, CI runs, release publication, or changes to main.

# Advanced Assurance Integration and PR #3 Review — Qyrenith 1.2.0

**Status:** INTEGRATION PROPOSAL — OWNER REVIEW REQUIRED  
**Source PR:** [#3 — Advanced Assurance AA-01](https://github.com/JustCax/Qyrenith/pull/3)  
**Source branch:** `feature/advanced-assurance-aa01-mainline`  
**Reviewed source head after PR #3 audit corrections:** `0ee2edb9fe136bba729483e56d5c450421fa6e80`  
**Target integration branch:** `feature/1.2.0-universal-migration-core`  
**Scope:** Documentation and architecture reconciliation only. No implementation or merge authorization is implied.

## 1. Executive decision

Advanced Assurance (AA) is relevant to Qyrenith 1.2.0 and should be retained. It is not a separate product, a fifteenth capability module, or a replacement for QDAS. Its strongest contribution is a product-wide verification pipeline and explicit separation of project discovery, planning, authorization, checker execution, evidence validation, policy decisions and reporting.

The correct integration is to treat AA as a **cross-cutting assurance architecture contract** implemented through the existing five planes and fourteen post-QDAS capability modules. QDAS remains the development-assurance lifecycle and integration mechanism. The 27 diagnostic domains remain analyzer/knowledge/execution capabilities. AA defines how checks are discovered, planned, authorized, executed, validated, evaluated and reported.

Do not merge PR #3 independently into `main`. Keep it draft until the owner reviews AA-01 open questions and the integration mapping below. Do not merge PR #9 or PR #3 as part of this documentation pass.

## 2. Repository and branch facts

Repository and PR state observed on 2026-11-10 after the AA-01 decision-design documentation commit:

- `main` HEAD: `2cc0a0c3d34bb056ee8aeb2f16529fe608a7536a`. This review did not modify `main`.
- 1.2.0 branch HEAD: `61df2885d0721c8318ad418dd0d0590698d4096b`.
- PR #9 is the release PR from `feature/1.2.0-universal-migration-core` to `main`. It remains open/draft and unmerged. Its current comparison is 662 commits ahead and 1 behind `main`, across 124 changed files. The large diff requires a separate release review; GitHub's mergeable flag is not an independent quality review.
- PR #3 remains open/draft and unmerged, with head `0ee2edb9fe136bba729483e56d5c450421fa6e80`, targeting `main`. Its current comparison is 14 commits ahead and 11 behind `main`, across 13 paths: eleven AA-01 documentation/ADR/provenance files and two workflow deletions. It contains no implementation code. Do not merge it into `main`; any accepted content is integrated into the 1.2.0 branch only.
- The `.github/workflows/` trees on `main`, the 1.2.0 branch, and PR #3 are empty. No workflow file was added by this documentation update.
- The latest observed Actions runs were created on 2026-11-09 13:15:35 UTC, before the November 10 documentation commits. No newer run was observed. GitHub Actions were disabled by the owner for billing reasons; no CI was run for these commits. Historical runs do not verify the current heads.

## 3. Mapping AA to the existing Qyrenith architecture

The five planes in `DEEP_AUDIT_MASTER_ARCHITECTURE.md` remain canonical. AA's logical components map as follows:

| AA component | Primary existing plane(s) | Existing Qyrenith foundations | Integration rule |
|---|---|---|---|
| Project Discovery | Analysis + Knowledge + Evidence | Project inspection, migration snapshots, compatibility knowledge | Discovery stays read-only; project facts retain provenance and uncertainty. |
| Project Model | Knowledge + Evidence | Migration project snapshots, QDAS lineage and domain knowledge | Use a versioned project model; do not create a second incompatible snapshot identity. |
| Verification Planner | Control + Knowledge | Migration planner/preparation, QDAS orchestration | Reuse policy and plan contracts; no silent scope broadening. |
| Authorization Gate | Control + Execution | Migration authorization, trust store, host approval and workspace boundaries | Exact plan/scope/action binding; authorization is not isolation. |
| Checker Registry / Contract Validator | Analysis + Control | Native analyzer/domain capability declarations and adapter boundaries | Introduce a common versioned checker contract; do not make providers trusted by registration. |
| Checker Runtime | Execution | Bounded process runner, reproducible lab, workspace lifecycle | Reuse execution boundary; do not claim OS sandbox without separately verified OS isolation. |
| Evidence Validator / Store | Evidence | QDAS event ledger, lineage, evidence/confidence model and schemas | Preserve append-only logical history, atomic writes, supersession and provenance. |
| Policy Evaluator | Control + Evidence | Trust/authorization policy and verdict aggregation | Keep decision authority separate from checker execution and report rendering. |
| Reporting Layer | Control + Evidence | CLI/QDAS output and integrated reporting specification | Human and machine reports derive from the same validated decision record. |
| Provider / Adapter Boundary | Analysis + Control + Execution | Language/domain adapters and optional external integrations | External tools remain opt-in providers; their output is untrusted until validated. |

## 4. Requirement-family integration

PR #3 defines 70 stable AA requirement IDs across eleven groups, including the four `AA-REQ-REL` release requirements. They are represented in the 1.2.0 traceability matrix as `PROPOSED`, retaining their original statements and linking them to proposed owners, acceptance tests and evidence. The PR #3 acceptance matrix now maps all 70 IDs individually to an architecture owner, relevant threat references, and a reserved test ID; these are planned test identifiers, not existing test implementations or evidence.

| Requirement group | Count | Primary owner | Existing overlap / integration |
|---|---:|---|---|
| AA-REQ-PROJ | 6 | Project Model / Knowledge | DI Universal Project Knowledge Graph; migration snapshot and domain knowledge |
| AA-REQ-PLAN | 6 | Control / Planner | Migration planning, QDAS orchestration and policy |
| AA-REQ-CHK | 8 | Execution / Checker Contract | Static, dynamic, formal, fuzz and adapter modules |
| AA-REQ-EVD | 8 | Evidence | QDAS ledger/lineage, Evidence and Confidence Model, reproducible lab |
| AA-REQ-POL | 7 | Control / Policy | Trust model, verdict vocabulary, acceptance gates |
| AA-REQ-SEC | 10 | Control + Execution | Security/supply-chain, authorization, workspace and process boundaries |
| AA-REQ-RPT | 6 | Reporting | Integrated reporting and orchestration |
| AA-REQ-EXT | 5 | Adapter Boundary | Language and domain adapters; optional external providers |
| AA-REQ-CMP | 3 | Knowledge + Release | Compatibility matrix, cross-environment assurance and benchmarks |
| AA-REQ-REL | 4 | Release / Evidence | Artifact manifest, provenance, deterministic release and publication gate |
| AA-REQ-NFR | 7 | All planes | Compatibility, schema, deterministic behavior, resource bounds and non-mutation |

The AA requirements are platform-level contracts. They must not duplicate the domain-specific behavior requirements in DI, DA, QDAS, MI, RVL, or the fourteen existing module specifications. Where two requirements appear similar, preserve both only when one defines the shared pipeline guarantee and the other defines domain-specific behavior; otherwise record an explicit consolidation decision before removing either ID.

## 5. Reconciliation of PR #3 proposed ADRs

All four ADRs on PR #3 are still marked **Proposed for AA-01 acceptance**. They are not accepted architecture decisions merely because they are named ADRs.

| Proposed ADR | Relationship to existing 1.2.0 architecture | Required action before acceptance |
|---|---|---|
| ADR-AA-001 — authority separation | Consistent with the existing rule that workers/analyzers cannot self-qualify or issue final verdicts. | Cross-link to the master trust/authority model and policy evaluator; verify no duplicate authority model. |
| ADR-AA-002 — explicit side-effect authorization | Consistent with migration authorization, host approval and controlled execution. | Reconcile action classes and exact-scope authorization with existing migration authorization schemas. |
| ADR-AA-003 — evidence lifecycle | Consistent with QDAS append-only event ledger and evidence lineage. | Reconcile atomicity, supersession, invalidation and retention semantics with existing ledger/schema contracts. |
| ADR-AA-004 — standard-library-first core | Consistent with the current native-engine / optional-provider policy. | Clarify whether this is already a binding constraint or a proposed restatement; avoid duplicate conflicting policy. |

No ADR status is changed in this integration pass.

## 6. AA-01 open decisions that still require owner input

PR #3's acceptance matrix now leaves seven decisions open:

1. Confirm the seven per-check outcome states and the mapping from legacy workflow states.
2. Select persistent evidence storage only after consistency, atomicity, portability and privacy comparison.
3. Decide whether stronger process isolation is a supported OS-specific feature or an external prerequisite.
4. Approve verification profiles only after exact check inventories and resource policies exist.
5. Decide whether any network-enabled provider belongs in the first Advanced Assurance release; default remains disabled.
6. Define the aggregate project-level assurance decision separately from the seven per-check outcome states, including legacy workflow-state compatibility.
7. Confirm the reproducibility outcome vocabulary and its relationship to per-check outcomes, using the cross-environment/reproducibility specification as the detailed contract.

The PR #3 audit also corrected the requirement lifecycle so that `SPECIFIED` is distinct from `IMPLEMENTED`, and `DEFERRED` is a disposition rather than the automatic state after `VERIFIED`. The architecture now distinguishes per-check outcomes, aggregate assurance decisions, and reproducibility outcomes. Reproducibility is explicitly cross-cutting and does not introduce a second execution engine. Three reproducibility-specific threat scenarios were added.

These seven questions must be resolved or explicitly deferred before AA-01 can be marked accepted. The proposed ADRs should be reviewed alongside them, not accepted independently. ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md expands each question into alternatives, recommended defaults, safety consequences, and acceptance conditions. Its recommendations remain proposals until the owner explicitly approves them.

## 7. Reproducibility and optimization integration

The RCA-01..RCA-12 requirements define reproducibility across build, tests, diagnostics, fuzzing, runtime, repair, migration, optimization and reports. They extend the existing Reproducible Verification Lab and Evidence Model; they do not create a second runner.

The OI-01..OI-10 requirements define measured optimization and safe repair. They extend QDAS, root-cause analysis, dynamic audit, formal verification, reproducibility and meta-audit; they do not authorize automatic code mutation.

RCA, OI and AA requirement families are now listed in the traceability matrix as `PROPOSED`. They must be owner-approved before implementation is treated as release scope.

## 8. PR #3 disposition and safe integration sequence

Recommended disposition:

1. Keep PR #3 open and draft. It must not be merged into `main`; if its content is accepted, integrate it only into `feature/1.2.0-universal-migration-core`.
2. Review the requirement and architecture crosswalk in this document.
3. Resolve or explicitly defer the seven AA-01 open decisions and compare each proposed ADR against the existing master architecture and migration authorization/evidence schemas.
4. If accepted, retain the stable AA requirement IDs and proposed ADR content, but integrate them into the 1.2.0 branch as reviewed documents. Prefer reviewed, selective integration over blindly merging the entire divergent PR branch. Preserve PR #3 as the historical review source until the owner decides whether to close it.
5. Update the 1.2.0 plan and traceability matrix in the same change.
6. Only then design implementation slices. AA-02 checker contract/runtime and AA-03 project model/planning must not bypass the Phase 1 migration safety gate or Phase 2 QDAS-first integration sequence.

PR #9 is the release PR for the 1.2.0 branch and remains open/draft against main; it is not an internal integration target. PR #3 remains a separate source/review PR. Any accepted PR #3 content is integrated into the 1.2.0 branch only. No PR merge, branch retargeting, rebase, close, release or publication is authorized by this proposal.

## 9. Verification and repository safety

- The AA-01 specification corrections are documentation-only. No Python source, schema, or test files were changed.
- Two legacy workflow files were removed from the PR #3 branch as a separate repository-safety cleanup; the workflow directories on `main`, PR #3, and PR #9 are now empty.
- The owner has disabled GitHub Actions for billing reasons. Do not restore workflows or initiate CI without explicit approval.
- No new Actions run was observed after the November 10 branch commits. Historical Actions runs do not verify these revisions.
- The PR #3 acceptance matrix no longer requires CI for its documentation-only review gate; it requires a recorded independent documentation validation instead.
- Use the owner-approved local/external verification route for document lint, link checking and requirement-ID consistency; retain exact revision and command output.
- Do not describe PR #3 or any proposed AA component as implemented or verified.

## 10. Sources reviewed

- PR #3 source documents at `0ee2edb9fe136bba729483e56d5c450421fa6e80`: `ADVANCED_ASSURANCE_PROGRAM.md`, `ADVANCED_ASSURANCE_ARCHITECTURE.md`, `ADVANCED_ASSURANCE_REQUIREMENTS.md`, `ADVANCED_ASSURANCE_ACCEPTANCE_MATRIX.md`, `ADVANCED_ASSURANCE_THREAT_MODEL.md`, `ADVANCED_ASSURANCE_TEST_STRATEGY.md`, `COMPONENT_PROVENANCE_REGISTER.md`, and four proposed `ADR-AA-00x` records.
- 1.2.0 branch documents reviewed at the pre-update head `d2c17194b101e2bf2cf5309e266c54600621ac93`: `DEEP_AUDIT_MASTER_ARCHITECTURE.md`, `QYRENITH_1_2_0_IMPLEMENTATION_AND_ACCEPTANCE_PLAN.md`, `REQUIREMENT_TRACEABILITY_MATRIX.md`, `EVIDENCE_AND_CONFIDENCE_MODEL.md`, `REPRODUCIBLE_VERIFICATION_LAB_SPEC.md`, `ROOT_CAUSE_AND_CROSS_MODULE_ANALYSIS_SPEC.md`, `META_AUDIT_AND_BENCHMARK_SPEC.md`, `LANGUAGE_AND_DOMAIN_ADAPTER_SPEC.md`, and the six-pillar/27-domain expansion documents.

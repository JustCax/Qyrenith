# Migration Planning API

**Status:** Experimental in Qyrenith 1.2.0 development  
**Module:** `qyrenith_engine.migration`  
**Runtime dependencies:** Python standard library only

This document describes the first domain-neutral migration planning primitives. It is not a claim that Qyrenith can automatically convert arbitrary projects, discover undocumented API mappings, or execute every planned route.

## 1. Responsibilities

The migration core provides typed project-state identities, typed transition declarations, evidence-scoped knowledge claims, deterministic route planning, and independent multi-target route plans.

It does not currently discover project state, transform source files, select or launch workers, create isolated workspaces, run builds, validate application behavior, authorize side effects, or complete a managed migration. Those capabilities require later integration phases and independent acceptance evidence.

Minecraft remains the first reference domain, but the identity and planning contracts do not require Minecraft-specific fields.

## 2. Migration identity

A `MigrationIdentity` identifies one exact project state through independent optional dimensions:

- Domain and product.
- Product/runtime version.
- Platform.
- Loader and loader version.
- Framework and framework version.
- Language and toolchain.
- Dependency fingerprint.
- Project profile.

The `domain` and `product` fields are required. Other dimensions may be omitted when they do not apply or are not known. Unknown dimensions must not be guessed.

The canonical `stable_key` includes every dimension, including explicit null values. It is an identity key, not a semantic-version comparator.

## 3. Transition kinds

A `MigrationTransition` is a directed edge between two identities. The initial transition taxonomy is:

| Kind | Identity dimensions allowed to change |
|---|---|
| `VERSION_UPGRADE` | Product version |
| `LOADER_CONVERSION` | Loader and loader version |
| `FRAMEWORK_CHANGE` | Framework and framework version |
| `PLATFORM_MIGRATION` | Domain, product, and platform |
| `TOOLCHAIN_CHANGE` | Language and toolchain |
| `DEPENDENCY_MIGRATION` | Dependency fingerprint |
| `PROJECT_PROFILE_CHANGE` | Project profile |

A transition that changes dimensions outside its declared kind is rejected. This prevents a loader conversion from being hidden inside a product-version upgrade. Compound migrations must be represented as ordered transitions.

A transition declaration is not proof that a transformation exists. Its `enabled` field is an explicit availability switch, not a capability verification result. A selected worker ID must be paired with an exact version; both, along with the declared capabilities, are bound into the plan digest. The worker manifest registry described below resolves compatibility and qualification separately from route planning.

## 4. Migration knowledge

A `MigrationKnowledgeClaim` describes one fact for an exact source/target pair. The fields have distinct purposes:

- `subject`: stable identifier for the fact being asserted.
- `assertion`: machine-comparable value used to detect contradictory claims.
- `statement`: human-readable explanation.
- `status`: one of OBSERVED, INFERRED, UNKNOWN, VERIFIED, CONFLICTED, or STALE.
- `evidence`: references to the material supporting the claim.
- `verified_by` and `verified_at`: review attribution and time.
- `valid_until`: optional expiry of the verification.

A VERIFIED claim requires a non-empty assertion, reviewer attribution, timezone-aware verification time, and at least one evidence reference. Evidence observation times cannot be later than the verification time. An expiry must be later than the verification time. Evidence digests, when provided, use `sha256:` followed by 64 lowercase hexadecimal characters.

Reviewer attribution is provenance metadata. It is not an authentication or authorization system. A digest establishes integrity only relative to a trusted digest value; it does not prove that a source is authoritative or that an observation is truthful.

### Conflict handling

Claims with the same subject and exact source/target identities are grouped. Different assertions in the same active group make the group conflicted; every claim in that group is excluded from route qualification. An explicit CONFLICTED claim also blocks the matching group. UNKNOWN and STALE claims do not override current claims, but remain available for inspection.

A conflict is not automatically resolved by choosing the newest, highest-confidence, or AI-generated claim. A maintainer must review the evidence and update the knowledge set explicitly.

### Catalog interchange

`KnowledgeCatalog.to_json_bytes()` and `serialize_knowledge_catalog()` produce canonical UTF-8 JSON with a SHA-256 content digest. `from_json_bytes()` and `deserialize_knowledge_catalog()` reject duplicate JSON object keys, unknown fields, unsupported schema versions, malformed identities, digest mismatches, oversized imports, and non-canonical documents.

The import size is limited to 16 MiB and each claim's evidence array is bounded. Catalog merging is immutable: identical claim IDs with identical full contents are idempotent; reuse of an ID for different content is rejected.

Catalog digesting is a consistency/integrity mechanism, not a signature or proof of origin.

## 5. Route-planning result states

`plan_route(source, target, transitions, knowledge)` evaluates all knowledge at one captured UTC instant. Pass `evaluated_at` explicitly when a reproducible historical decision is required.

| Status | Meaning |
|---|---|
| `PLANNED` | A declared, enabled route exists and every transition has current, exact-scope, non-conflicted VERIFIED knowledge. |
| `UNKNOWN` | An enabled route is declared, but one or more transitions lack usable verified knowledge. |
| `BLOCKED` | A route exists only through disabled transitions, or the configured hop limit prevents its use. |
| `UNSUPPORTED` | No declared transition path connects the source and target. |

`RoutePlan.plannable` is true only for PLANNED. It does **not** mean the migration may be executed. Execution still requires a qualified worker, a separate authorization, an isolated workspace, runtime controls, validation, diff review, and commit/recovery gates.

A plan digest binds the source and target identities, full transition contracts (including worker ID, pinned worker version, and required capabilities), the knowledge catalog digest, planner version, evaluation time, and hop limit. Re-evaluating at a different time or against a different catalog creates a different plan digest.

## 6. Multi-target planning

`plan_targets(source, targets, transitions, knowledge)` plans each requested target independently from the same source identity and one common evaluation instant.

Each target keeps its own route and status. The aggregate result is:

- PLANNED when every target is PLANNED.
- PARTIAL when at least one target is PLANNED and others are not.
- UNKNOWN when none is PLANNED and at least one is UNKNOWN.
- BLOCKED when none is PLANNED and at least one is BLOCKED.
- UNSUPPORTED when every target is UNSUPPORTED.

This is route planning only. It does not create Git worktrees, duplicate a project, isolate builds, or prevent file leakage between targets. Those safeguards must exist before multi-target execution is advertised.

## 7. Worker manifests and qualification

A `MigrationWorkerManifest` pins a worker ID and version to an implementation digest, protocol version, exact source/target transition scopes, declared capabilities, permission requirements, and resource limits. Scope matching is exact: this initial contract does not accept wildcard product versions, loaders, platforms, or target identities.

The registry returns one of these states for a pinned transition:

| State | Meaning |
|---|---|
| `NOT_SELECTED` | The transition does not pin a worker. |
| `NOT_REGISTERED` | The exact worker ID and version are absent from the local registry. |
| `INCOMPATIBLE` | The registered manifest does not cover the exact transition or all required capabilities. |
| `UNQUALIFIED` | No qualification record is present. |
| `STALE` | The qualification is expired or bound to a different manifest digest. |
| `QUALIFIED` | Exact scope and capability match, plus a current PASS qualification record for the same manifest digest. |
| `BLOCKED` | The transition is disabled. |

The `assess_route_workers(plan, registry)` API evaluates every planned edge at the exact route-plan timestamp. It returns `QUALIFIED` only when every edge resolves to a current matching qualification; it returns `UNKNOWN` for missing/unselected/stale workers, `BLOCKED` for disabled or incompatible workers, `ROUTE_NOT_PLANNED` when the route itself is not PLANNED, and `NO_WORK_REQUIRED` for a no-op route. The assessment digest binds the route digest and ordered transition/resolution pairs. `assessment.qualified` is true only when a worker was actually qualified; `assessment.worker_gate_satisfied` is also true for a no-op route with no worker operation. Neither property grants execution permission.

A `WorkerQualification` records the manifest digest, conformance-suite identity and version, suite digest, result digest, PASS status, test count, reviewer attribution, qualification time, and expiry. It is a record of a reviewed result; it is not proof that this library ran the suite. The current registry does not execute conformance tests, sign qualifications, authenticate reviewer identities, fetch worker packages, or launch workers. A qualification record must come from a separately controlled and reviewed process.

Manifest permissions are declarations, not grants. The registry returns permissions and resource limits to the caller; a future execution authority must independently decide whether the current task is allowed to use them. In particular, `WRITE_PROJECT`, `EXECUTE_PROCESS`, `NETWORK`, and `PUBLISH_ARTIFACT` must never be treated as implicitly approved by worker registration.

## 8. Minimal example

The following example deliberately creates only an OBSERVED claim. The route must remain UNKNOWN until a real evidence source is reviewed and the claim is explicitly promoted by an authorized maintainer.

```python
from qyrenith_engine.migration import (
    KnowledgeCatalog,
    KnowledgeStatus,
    MigrationIdentity,
    MigrationKnowledgeClaim,
    MigrationTransition,
    TransitionKind,
    plan_route,
)

source = MigrationIdentity(
    domain="example",
    product="example-runtime",
    product_version="1.0",
    platform="linux",
)
target = MigrationIdentity(
    domain="example",
    product="example-runtime",
    product_version="1.1",
    platform="linux",
)

claim = MigrationKnowledgeClaim(
    claim_id="example-runtime-1.0-to-1.1",
    subject="runtime.compatibility",
    assertion="candidate-compatible",
    statement="An initial compatibility observation; not reviewed.",
    source=source,
    target=target,
    status=KnowledgeStatus.OBSERVED,
)

transition = MigrationTransition(
    transition_id="example-version-upgrade",
    source=source,
    target=target,
    kind=TransitionKind.VERSION_UPGRADE,
    knowledge_claim_ids=(claim.claim_id,),
)

plan = plan_route(source, target, (transition,), KnowledgeCatalog((claim,)))
assert plan.status == "UNKNOWN"
assert not plan.plannable
```

A real VERIFIED claim must be supported by reviewable evidence whose scope exactly matches the transition. Do not use placeholder evidence identifiers or invented hashes in a production knowledge catalog.

## 9. Assurance ledger boundary

`AssuranceLedger` is a separate append-only JSONL record store. It validates record shape, scoped relative paths, digests, commit identifiers, sequence numbers, and a SHA-256 hash chain. Writes use a single-writer lock, bounded input/output, temporary-file replacement, and directory synchronization where supported.

The ledger is not yet integrated into the managed migration workflow. A caller-supplied PASS is structurally rejected unless the worker status is exactly `WORKED` and the record includes changed files, diff digest, post-state digest, evidence references, a Git commit identifier, the pinned worker version, and the exact worker manifest and qualification digests. `NO_CHANGE`, `BLOCKED`, or `FAILED` worker reports cannot become a migration PASS. These checks validate required fields; they do not independently inspect the referenced build, evidence, commit, worker executable, conformance suite, or policy decision.

A local hash chain can detect accidental or partial tampering when its trusted tail is preserved. An actor able to replace the entire ledger can recompute the chain. The ledger is not a digital signature, remote transparency service, database transaction coordinator, or OS security boundary.

## 10. Plan-bound authorization

`MigrationAuthorizationPolicy` defines a local permission allowlist, worker allowlist, resource ceilings, and maximum authorization lifetime. Policies have canonical JSON import/export, a content digest, and a strict JSON Schema so the exact policy can be retained alongside an authorization record. `validate_migration_authorization(...)` is the pre-side-effect consistency gate: it rechecks the exact plan and assessment, active policy digest, authorization time window, worker registration and qualification, grant scope, permissions, and resource ceilings. `authorize_migration(plan, assessment, registry, policy, ...)` creates an immutable authorization bound to the exact route-plan digest, worker-assessment digest, and policy digest.

Before issuing grants, the function re-resolves every worker against the registry at the approval timestamp. It rejects a changed manifest or qualification, a qualification that is not current at approval, permissions not allowed by both policy and worker manifest, resource limits above either declared ceiling, and an authorization expiry later than any worker qualification expiry. Every grant is pinned to one transition, worker ID/version, manifest digest, qualification ID/digest, and qualification expiry. Authorization validity uses a half-open time interval: approved_at <= now < expires_at.

Approval attribution (`approved_by`) is caller-supplied provenance, not authenticated identity or a cryptographic signature. The policy is a local decision input, not a secure account/role system. The authorization object does not persist itself, launch a worker, enforce operating-system permissions, isolate a process, or guarantee that a future executor will enforce the grant. It is a necessary policy artifact, not an execution capability. A future executor must re-check the exact grant, current time, measured worker bytes, workspace boundary, and runtime-enforced resource controls immediately before each side effect.

A no-op route may receive an authorization record with zero worker grants; it authorizes no worker operation.

## 11. Current limitations

The current migration package is a planning and record-keeping foundation. It does not yet provide:

- Project discovery or source-state fingerprint generation for migration plans.
- Automated conformance-suite execution or cryptographic worker qualification signatures.
- Authenticated human approvals, signed authorization records, persistent policy administration, and an execution-time enforcement point.
- Migration source transformations or API mapping discovery.
- Isolated per-target worktrees and cross-target contamination tests.
- Managed workflow integration and recovery orchestration.
- Build, test, runtime, or behavioral verification of target projects.
- A verified cross-loader Minecraft conversion or a newly qualified non-Minecraft domain.

The plan-bound authorization record is available as a policy artifact, but it is not an execution authority. Authenticated approval, protected policy administration, runtime enforcement, isolated execution, and independent target validation remain separate gates.

These limits are deliberate. A registered domain, a worker declaration, a PLANNED route, or an AI response must not be presented as a successful or supported migration.

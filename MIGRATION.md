# Migration Planning API

**Status:** Experimental in Qyrenith 1.2.0 development  
**Module:** `qyrenith_engine.migration`  
**Runtime dependencies:** Python standard library only

This document describes the first domain-neutral migration planning primitives. It is not a claim that Qyrenith can automatically convert arbitrary projects, discover undocumented API mappings, or execute every planned route.

## 1. Responsibilities

The migration core provides typed project-state identities, typed transition declarations, evidence-scoped knowledge claims, deterministic route planning, and independent multi-target route plans.

It does not currently transform source files, select or launch workers, run builds, validate application behavior, enforce authorization at the operating-system boundary, or complete a managed migration. Project state can be fingerprinted through the explicit snapshot API, and one snapshot-pinned filesystem copy can be created per target. Automatic project discovery, Git-aware worktrees, batch workspace lifecycle management, and managed workflow integration remain separate capabilities requiring independent acceptance evidence.

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
- `verified_by` and `verified_at`: human review attribution and time.
- `verified_with`, `verifier_version`, and `verifier_digest`: the exact verifier identity, version, and SHA-256 digest of its implementation or controlled verification procedure.
- `valid_until`: mandatory expiry for VERIFIED knowledge.

A VERIFIED claim requires a non-empty assertion, reviewer attribution, timezone-aware verification time, at least one evidence reference, a SHA-256 digest for every evidence item, pinned verifier identity/version/implementation digest, and an explicit expiry later than the verification time. Evidence observation times cannot be later than the verification time. Evidence and verifier digests use `sha256:` followed by 64 lowercase hexadecimal characters. Non-VERIFIED observations may omit content digests and verifier metadata.

Reviewer attribution is provenance metadata. It is not an authentication or authorization system. A digest establishes integrity only relative to a trusted digest value; it does not prove that a source is authoritative or that an observation is truthful. The claim and catalog digests bind the evidence hashes and verifier build identity into the knowledge record. If evidence bytes, verifier version, or verifier implementation change, a new reviewed claim must be created rather than editing the old claim in place. Qyrenith does not fetch remote evidence or automatically detect changes at a URL; the explicit expiry bounds how long the stored verification may be used, and revalidation must recapture and hash the evidence.

### Conflict handling

Claims with the same subject and exact source/target identities are grouped. Different assertions in the same active group make the group conflicted; every claim in that group is excluded from route qualification. An explicit CONFLICTED claim also blocks the matching group. UNKNOWN and STALE claims do not override current claims, but remain available for inspection.

A conflict is not automatically resolved by choosing the newest, highest-confidence, or AI-generated claim. A maintainer must review the evidence and update the knowledge set explicitly.

### Catalog interchange

`KnowledgeCatalog.to_json_bytes()` and `serialize_knowledge_catalog()` produce canonical UTF-8 schema-v2 JSON with a SHA-256 content digest. Schema-v1 knowledge documents are rejected rather than silently promoted because they do not bind VERIFIED claims to evidence and verifier digests. `from_json_bytes()` and `deserialize_knowledge_catalog()` reject duplicate JSON object keys, unknown fields, unsupported schema versions, malformed identities, digest mismatches, oversized imports, and non-canonical documents.

The import size is limited to 16 MiB and each claim's evidence array is bounded. Catalog merging is immutable: identical claim IDs with identical full contents are idempotent; reuse of an ID for different content is rejected.

Catalog digesting is a consistency/integrity mechanism, not a signature or proof of origin. Catalogs constructed directly in trusted application code are treated as local inputs. JSON imports are **untrusted by default** and cannot qualify a route. To trust an imported catalog, the caller must supply a `KnowledgeTrustPolicy` whose allowlist contains that exact catalog digest. The policy must itself be loaded from an owner-controlled local trust store; its digest is not a signature. Its `reviewed_at` must not be later than the route evaluation time. A changed/merged catalog has a different digest and requires a new review decision. This closes the default-import trust gap while retaining an explicit local trust boundary; it does not authenticate the human reviewer.

Example of the explicit import decision:

```python
from qyrenith_engine.migration import KnowledgeCatalog, KnowledgeTrustPolicy

catalog_bytes = open("reviewed-knowledge.json", "rb").read()
untrusted = KnowledgeCatalog.from_json_bytes(catalog_bytes)
policy = KnowledgeTrustPolicy(
    policy_id="local-reviewed-catalogs",
    reviewed_by="operator-review-attribution",
    reviewed_at="2026-11-04T00:00:00Z",
    trusted_catalog_digests=(untrusted.content_digest,),
)
trusted = KnowledgeCatalog.from_json_bytes(catalog_bytes, trust_policy=policy)
assert trusted.is_trusted
```

The trust policy must be loaded from a protected local source. Do not store an authoritative trust policy beside untrusted project input.

## 5. Route-planning result states

`plan_route(source, target, transitions, knowledge)` evaluates all knowledge at one captured UTC instant. Pass `evaluated_at` explicitly when a reproducible historical decision is required.

| Status | Meaning |
|---|---|
| `PLANNED` | A declared, enabled route exists and every transition has current, exact-scope, non-conflicted VERIFIED knowledge. |
| `UNKNOWN` | An enabled route is declared, but one or more transitions lack usable verified knowledge. |
| `BLOCKED` | A route exists only through disabled transitions, or the configured hop limit prevents its use. |
| `UNSUPPORTED` | No declared transition path connects the source and target. |

`RoutePlan.plannable` is true only for PLANNED. It does **not** mean the migration may be executed. Execution still requires a qualified worker, a separate authorization, an isolated workspace, runtime controls, validation, diff review, and commit/recovery gates.

A plan digest binds the source and target identities, full transition contracts (including worker ID, pinned worker version, and required capabilities), the knowledge catalog digest, the catalog trust-decision digest, planner version, evaluation time, and hop limit. Re-evaluating at a different time, against a different catalog, or under a different trust decision creates a different plan digest.

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
| `UNTRUSTED` | A current qualification exists but its exact digest is not allowlisted by the active local trust policy. |
| `STALE` | The qualification is expired or bound to a different manifest digest. |
| `QUALIFIED` | Exact scope/capability match, a current PASS qualification record for the same manifest digest, and an exact-digest allowlist match under the active local WorkerTrustPolicy. This is a trusted record state, not proof that this library ran the conformance suite. |
| `BLOCKED` | The transition is disabled. |

The `assess_route_workers(plan, registry)` API evaluates every planned edge at the exact route-plan timestamp. It returns `QUALIFIED` only when every edge resolves to a current qualification record allowlisted by the active trust policy; it returns `UNKNOWN` for missing/unselected/unqualified/untrusted/stale workers, `BLOCKED` for disabled or incompatible workers, `ROUTE_NOT_PLANNED` when the route itself is not PLANNED, and `NO_WORK_REQUIRED` for a no-op route. The assessment digest binds the route digest and ordered transition/resolution pairs. `assessment.qualified` is true only when every worker qualification record is current and allowlisted by the active local trust policy; `assessment.worker_gate_satisfied` is also true for a no-op route with no worker operation. Neither property grants execution permission.

A `WorkerQualification` records the manifest digest, conformance-suite identity and version, suite digest, result digest, PASS status, test count, reviewer attribution, qualification time, and expiry. It is a record of a reviewed result; it is not proof that this library ran the suite. The current registry does not execute conformance tests, sign qualifications, authenticate reviewer identities, fetch worker packages, or launch workers. A qualification record must come from a separately controlled and reviewed process. The registry now returns `UNTRUSTED` unless the exact qualification digest is allowlisted by a `WorkerTrustPolicy`; the active policy digest is bound into route-worker assessments and migration authorization.

Example local qualification allowlisting (the trust policy must be protected and reviewed separately):

```python
from qyrenith_engine.migration import MigrationWorkerRegistry, WorkerRegistration, WorkerTrustPolicy

worker_trust = WorkerTrustPolicy(
    policy_id="locally-reviewed-workers",
    reviewed_by="operator-review-attribution",
    reviewed_at="2026-11-04T00:00:00Z",
    trusted_qualification_digests=(qualification.qualification_digest,),
)
registry = MigrationWorkerRegistry(
    (WorkerRegistration(manifest, qualification),),
    trust_policy=worker_trust,
)
```

**Remaining trust limitation:** the policy itself is not cryptographically authenticated, and an allowlisted record still does not prove that the declared conformance suite actually ran. Load the policy only from an owner-controlled source. The conformance runner and independently collected result evidence remain required before worker execution.

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

## 9. Project snapshots

`capture_project_snapshot(root)` creates a deterministic, bounded inventory of a project without modifying it. The snapshot binds canonical relative paths, entry types, portable permission bits, regular-file sizes and SHA-256 content digests, and symbolic-link targets. It records symbolic links but never follows them. Special filesystem objects, non-portable paths, unsafe root types, and files or trees that exceed configured limits fail closed.

The default exclusions are `.git`, `.qyrenith`, `.backups`, and `__pycache__`. Callers may supply an explicit exclusion list and `SnapshotLimits`. Exclusions and limits are part of the snapshot digest, so two snapshots made under different policies are not interchangeable. Capture timestamps are retained for audit but deliberately excluded from the content digest.

`verify_project_snapshot(root, snapshot)` recaptures the project using the exact policy stored in the snapshot and reports `MATCH` or `CHANGED`, including a bounded list of changed paths. Snapshot documents have strict canonical JSON import/export and digest verification.

This is a read-only fingerprint, not an atomic filesystem transaction, Git commit attestation, backup, or sandbox. Filesystem changes during capture are detected where the platform exposes stable metadata, but callers must still revalidate immediately before any side effect. A snapshot digest establishes content identity, not trust or authorship.

The CLI exposes the same read-only operation:

```powershell
python qyrenith.py snapshot capture --project . > ../source.snapshot.json
python qyrenith.py snapshot verify --project . --snapshot-file ../source.snapshot.json
```

Capture writes canonical JSON to standard output; redirect it to a file outside the project when you want to retain it. Verification exits with code 0 for `MATCH`, 1 for `CHANGED`, and a preflight error code when the snapshot cannot be read or checked. Neither command creates Qyrenith state inside the inspected project.

## 10. Isolated target workspaces

`create_isolated_workspace(source_root, snapshot, workspace_parent, target)` creates one new, independent target directory under an existing trusted workspace parent. The parent must be outside the source project. The operation requires the source to match the supplied snapshot before copying, copies only regular files represented in that snapshot, verifies each copied file's size and digest, checks the materialized project against the same snapshot, and rechecks the source before returning. On POSIX, file opens are relative to no-follow directory descriptors so a replaced parent symlink is not traversed; Windows uses the file-handle metadata checks available through the Python standard library.

Snapshots containing symbolic links are rejected for materialization. This avoids reproducing potentially external link targets in a target workspace. Empty directories and portable permission bits are preserved where the host filesystem supports them. A canonical `workspace.json` descriptor binds the unique workspace ID to the workspace path, exact target identity, source snapshot digest, project path, file count, byte count, and creation time. Its SHA-256 digest detects accidental or unsophisticated modification relative to a trusted descriptor; it is not a signature or proof of who created the workspace. `verify_workspace_baseline(descriptor, snapshot)` first verifies the workspace and project directories, safely reads and integrity-checks the persisted descriptor against the supplied descriptor, then checks that the project still matches its original baseline.

Call `create_isolated_workspaces(source_root, snapshot, workspace_parent, targets)` to create up to 64 unique target workspaces as one rollback unit. Each target is revalidated against the same source snapshot before its copy. If any target fails, all workspaces created by that batch are removed. Successful workspaces remain caller-owned; persistent retention and successful-workspace cleanup policy are not managed by this API.

This is a filesystem copy, not a Git worktree: Git metadata excluded by the source snapshot is not copied, no branch or commit is created, and no worker or build process is launched. Workspace separation is not an OS sandbox; processes later launched inside a workspace still require explicit runtime isolation and permission enforcement.

A minimal two-target setup looks like this (the parent directory must already exist outside the source project):

```python
from pathlib import Path

from qyrenith_engine.migration import (
    MigrationIdentity,
    capture_project_snapshot,
    create_isolated_workspaces,
    verify_workspace_baseline,
)

source = Path("path/to/source-project")
workspace_parent = Path("path/to/external-workspaces")
snapshot = capture_project_snapshot(source)

fabric_target = MigrationIdentity(
    domain="minecraft", product="minecraft", product_version="1.21.1",
    platform="java", loader="fabric", loader_version="0.16.0",
)
forge_target = MigrationIdentity(
    domain="minecraft", product="minecraft", product_version="1.21.1",
    platform="java", loader="forge", loader_version="21.1.0",
)

fabric_workspace, forge_workspace = create_isolated_workspaces(
    source, snapshot, workspace_parent, (fabric_target, forge_target)
)

assert verify_workspace_baseline(fabric_workspace, snapshot).matches
assert verify_workspace_baseline(forge_workspace, snapshot).matches
```

Each call allocates a separate workspace. The example deliberately stops before worker execution; target-specific changes and verification belong to later orchestration gates.

### 10.1 Plan-bound multi-target workspace preparation

`prepare_multi_target_workspaces(source_root, snapshot, workspace_parent, multi_target_plan)` connects a fully `PLANNED` `MultiTargetPlan` to the isolated-workspace batch API. It refuses `PARTIAL`, `UNKNOWN`, `BLOCKED`, and `UNSUPPORTED` plans before creating any target directories. It sorts target routes deterministically, revalidates the current knowledge catalog, trust decision, and every referenced claim at preparation time, verifies the source snapshot before and after preparation, creates one independent workspace per target, verifies each workspace baseline, and rolls back the whole batch if a post-creation check fails.

The returned `MultiTargetWorkspaceBatch` binds the exact multi-target plan digest, source identity, snapshot digest, ordered target identities, each target route-plan digest, workspace descriptors, and creation time. Its canonical JSON document has a batch digest. `batch.validate_for_plan(plan, snapshot)` prevents reuse with a different plan or source snapshot. Revalidate the individual workspace baselines before any later operation.

This is preparation, not execution: it does not run workers, authorize side effects, create Git worktrees, or provide an OS sandbox.

```python
from qyrenith_engine.migration import (
    capture_project_snapshot,
    plan_targets,
    prepare_multi_target_workspaces,
    verify_workspace_baseline,
)

snapshot = capture_project_snapshot(source_root)
multi_target_plan = plan_targets(source_identity, targets, transitions, knowledge)
batch = prepare_multi_target_workspaces(
    source_root, snapshot, workspace_parent, multi_target_plan, knowledge
)
batch.validate_for_plan(multi_target_plan, snapshot, knowledge)

for descriptor in batch.workspaces:
    assert verify_workspace_baseline(descriptor, snapshot).matches

batch_bytes = batch.to_json_bytes()
```

## 11. Assurance ledger boundary

`AssuranceLedger` is a separate append-only JSONL record store. It validates record shape, scoped relative paths, digests, commit identifiers, sequence numbers, and a SHA-256 hash chain. Writes use a single-writer lock, bounded input/output, temporary-file replacement, and directory synchronization where supported.

The ledger is not yet integrated into the managed migration workflow. A caller-supplied PASS is structurally rejected unless the worker status is exactly `WORKED` and the record includes changed files, diff digest, post-state digest, evidence references, a Git commit identifier, the pinned worker version, and the exact worker manifest and qualification digests. `NO_CHANGE`, `BLOCKED`, or `FAILED` worker reports cannot become a migration PASS. These checks validate required fields; they do not independently inspect the referenced build, evidence, commit, worker executable, conformance suite, or policy decision.

A local hash chain can detect accidental or partial tampering when its trusted tail is preserved. An actor able to replace the entire ledger can recompute the chain. The ledger is not a digital signature, remote transparency service, database transaction coordinator, or OS security boundary.

## 12. Plan-bound authorization

`MigrationAuthorizationPolicy` defines a local permission allowlist, worker allowlist, resource ceilings, and maximum authorization lifetime. Policies have canonical JSON import/export, a content digest, and a strict JSON Schema so the exact policy can be retained alongside an authorization record. `validate_migration_authorization(...)` is the pre-side-effect consistency gate: it rechecks the exact plan and assessment, current knowledge catalog and trust decision, active authorization policy digest, authorization time window, worker registration and qualification, grant scope, permissions, and resource ceilings. `authorize_migration(plan, assessment, registry, policy, ..., knowledge=...)` creates an immutable authorization bound to the exact route-plan digest, worker-assessment digest, and policy digest.

Before issuing grants, the function re-resolves every worker against the registry at the approval timestamp. It rejects a changed manifest or qualification, a qualification that is not current at approval, permissions not allowed by both policy and worker manifest, resource limits above either declared ceiling, and an authorization expiry later than any worker qualification expiry. Every grant is pinned to one transition, worker ID/version, manifest digest, qualification ID/digest, and qualification expiry. Authorization validity uses a half-open time interval: approved_at <= now < expires_at.

Approval attribution (`approved_by`) is caller-supplied provenance, not authenticated identity or a cryptographic signature. The policy is a local decision input, not a secure account/role system. The authorization object does not persist itself, launch a worker, enforce operating-system permissions, isolate a process, or guarantee that a future executor will enforce the grant. It is a necessary policy artifact, not an execution capability. **Current trust limitation:** because the authorization digest is unkeyed and approver attribution is caller-supplied, a structurally valid record can be fabricated by its producer. `validate_migration_authorization` checks consistency and freshness; it does not prove that a human approved the action. Requirement MI-05 must add a trusted approval channel before this record can gate side effects. A future executor must re-check the exact grant, current time, measured worker bytes, workspace boundary, and runtime-enforced resource controls immediately before each side effect.

A no-op route may receive an authorization record with zero worker grants; it authorizes no worker operation.

### Minimal authorization flow

Assuming `plan`, `assessment`, and `registry` were produced by the preceding APIs, the caller can create a narrow policy and an approval record:

```python
from datetime import datetime, timedelta, timezone

from qyrenith_engine.migration import (
    MigrationAuthorizationPolicy,
    WorkerPermission,
    WorkerResourceLimits,
    authorize_migration,
    validate_migration_authorization,
    serialize_migration_authorization,
    serialize_migration_authorization_policy,
)

# `knowledge` is the exact current catalog reloaded from the owner-controlled trust store.
now = datetime.now(timezone.utc)
policy = MigrationAuthorizationPolicy(
    allowed_permissions=(
        WorkerPermission.READ_PROJECT,
        WorkerPermission.WRITE_PROJECT,
    ),
    max_timeout_seconds=120,
    max_input_bytes=2 * 1024 * 1024,
    max_output_bytes=1024 * 1024,
    max_changed_files=100,
    max_lifetime_seconds=300,
    allowed_worker_ids=("reviewed-porter",),
)

authorization = authorize_migration(
    plan,
    assessment,
    registry,
    policy,
    approved_by="operator-review-attribution",
    approved_at=now,
    expires_at=now + timedelta(minutes=2),
    permissions=(
        WorkerPermission.READ_PROJECT,
        WorkerPermission.WRITE_PROJECT,
    ),
    limits=WorkerResourceLimits(60, 1024 * 1024, 512 * 1024, 50),
    knowledge=knowledge,  # Reload from the owner-controlled trust store before approval.
)

# Persist both records in the caller's trusted audit store.
policy_bytes = serialize_migration_authorization_policy(policy)
authorization_bytes = serialize_migration_authorization(authorization)

# Revalidate immediately before a future controlled side effect.
validate_migration_authorization(
    authorization, plan, assessment, registry, policy,
    knowledge=knowledge,  # Reload again before the side effect.
    now=datetime.now(timezone.utc),
)
```

The example records caller-supplied attribution only. It does not authenticate the operator, persist files by itself, or launch a worker. A real executor must additionally enforce the grant at the operating-system and workspace boundaries.

## 13. Current limitations

The current migration package is a planning and record-keeping foundation. It does not yet provide:

- Automatic project discovery or automatic binding of source snapshots into route plans.
- Automated conformance-suite execution or cryptographic worker qualification signatures.
- Authenticated human approvals, signed authorization records, persistent policy administration, and an execution-time enforcement point.
- Migration source transformations or API mapping discovery.
- Git-aware per-target worktrees, persistent successful-workspace lifecycle/cleanup management, and process-level isolation tests. The current API creates independent filesystem copies and rolls back a failed batch only.
- Managed workflow integration and recovery orchestration.
- Build, test, runtime, or behavioral verification of target projects.
- A verified cross-loader Minecraft conversion or a newly qualified non-Minecraft domain.

The plan-bound authorization record is available as a policy artifact, but it is not an execution authority. Authenticated approval, protected policy administration, runtime enforcement, OS-level process isolation, and independent target validation remain separate gates.

These limits are deliberate. A registered domain, a worker declaration, a PLANNED route, or an AI response must not be presented as a successful or supported migration.

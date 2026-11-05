# Migration Platform Integration Specification

## 1. Objective
Complete the existing 1.2.0 migration foundation into a safe, evidence-driven migration workflow while preserving the 1.1.0 managed Minecraft behavior until equivalent regression and acceptance coverage exists.

## 2. Existing foundation
The current branch contains typed migration identity and transitions, evidence-scoped knowledge, deterministic planning, worker contracts and qualification records, plan-bound authorization, an append-only local assurance ledger, read-only snapshots, and isolated filesystem-copy workspaces. These are useful primitives, not an end-to-end migration executor.

## 3. Requirements
- **MI-01 Project binding:** bind project discovery, source identity, snapshot, Git revision (when available), and user-selected target to one immutable migration request.
- **MI-02 Transition validation:** use the shared atomic transition validator for planner edges, worker scope, authorization, and execution requests.
- **MI-03 Knowledge qualification:** require exact source/target evidence, current validity, conflict-free claims, and reviewed provenance.
- **MI-04 Worker conformance:** execute a versioned conformance suite in a controlled lab; qualification binds worker bytes, manifest, suite, result, scope, reviewer, and expiry.
- **MI-05 Approval authentication and freshness:** define a trusted approval identity and record-integrity boundary; caller-supplied reviewer strings alone are not authentication. Revalidate the exact knowledge catalog digest, trust decision, and every referenced claim's validity at approval time and immediately before a side effect. Changed, revoked, expired, or untrusted knowledge blocks the action.
- **MI-06 Runtime enforcement:** enforce every permission and resource limit at the side-effect boundary through an OS sandbox or equivalent host-controlled isolation. Policy records and command allowlists alone do not enforce filesystem, process, secret, or network permissions; if the host cannot enforce the requested boundary, execution remains disabled and the system is propose-only.
- **MI-07 Workspace isolation:** preserve source baseline, target independence, safe path handling, cleanup, and explicit isolation-level reporting. Add Git-aware behavior only with tests for commit identity and worktree cleanup.
- **MI-08 Execution orchestration:** execute one typed transition at a time; capture before/after snapshots, worker result, diff, build/test evidence, recovery point, and ledger event.
- **MI-09 Recovery:** interruption and partial failure must leave a recoverable state; recovery actions are explicit, idempotent where possible, and evidence-recorded.
- **MI-10 Multi-target:** each target has independent route, authorization, workspace, execution, validation, and verdict, all pinned to one source baseline.
- **MI-11 Legacy compatibility:** run existing 1.1.0 workflow regression tests before and after integration; retain old behavior unless a reviewed migration changes it.
- **MI-12 Domain-neutrality:** Minecraft is the first reference domain, not a hard-coded control-plane assumption. New domains require executable adapters and evidence.
- **MI-13 QDAS:** use QDAS to audit migration changes, failure handling, and regression repairs; QDAS does not bypass migration authorization.
- **MI-14 Honest support claims:** a planned route, registered adapter, qualified worker, or copied workspace is not a completed migration.

- **MI-15 Qualification trust:** a matching qualification record is not proof that a conformance suite actually ran or that its reviewer is authentic. The current exact-digest local allowlist is a provisional trust gate only; it does not establish production qualification. Release acceptance requires a controlled conformance runner with independently collected results or a trusted authenticated attestation. Untrusted/imported records remain UNKNOWN/UNTRUSTED, and any local trust policy must be current at the assessment timestamp. A local allowlist alone must never authorize worker execution.


## 7. Owner-controlled trust store and approval boundary

### 7.1 Trust-store location and authority
- Trust state MUST live in the invoking user's Qyrenith configuration directory, outside every managed project/workspace and outside repository-controlled configuration.
- A project-local adapter, manifest, catalog, instruction file, or worker result MUST NOT create, modify, or implicitly populate owner trust.
- The store MUST be initialized explicitly by the owner. Missing, corrupt, unverifiable, partially initialized, or permission-insecure stores fail closed; the implementation MUST NOT silently regenerate a missing integrity key.
- Store entries are append-only decisions scoped to an exact subject kind and SHA-256 digest. Supported kinds include knowledge catalog, worker manifest, worker qualification, and execution policy.
- Trust and revocation are separate events. The newest valid owner decision applies, but a revocation immediately blocks the exact digest. A changed digest is a new subject and is never trusted by similarity.
- Every decision records a stable event ID, sequence, subject kind/digest, decision, reviewer attribution, UTC timestamp, optional expiry, and bounded rationale. The canonical store is integrity-protected with an owner-held key, and updates are atomic and locked.
- POSIX storage MUST enforce owner-only directory/file permissions and verify ownership. Windows storage MUST reject reparse-point paths and use the current user's profile ACL boundary. The implementation must state that same-user malicious code is outside this local trust-store threat boundary; an HMAC does not prove publisher identity.
- Imported trust policy files are data, not trust anchors. Trust is granted only by a new owner decision in the external store.

### 7.2 Authenticated host approval
- Approval MUST be collected by a trusted Qyrenith host interaction, not inferred from `approved_by`, a CLI `--yes` flag, agent instructions, repository files, or worker output.
- The local host channel requires an interactive terminal (or a separately configured authenticated approval service). It displays the complete action scope and asks the operator to confirm a one-time challenge.
- The resulting approval binds the exact plan digest, baseline snapshot digest, worker manifest and qualification digests, command digest, permissions, resource limits, target workspace, expiry, and a single-use nonce.
- The host signs the canonical approval record with the owner-held local integrity key. Validation checks the signature, scope, expiry, current trust decisions, and replay ledger immediately before each side effect.
- A non-interactive process without an authenticated approval service remains propose-only. A caller-supplied reviewer string is attribution metadata only.
- Local interactive approval proves control of the current host session, not a legal identity or protection from malicious code already running as the same OS user.

### 7.3 Enforcement and execution gate
- Trust and approval are necessary but not sufficient for execution. The executor MUST enforce path, process, environment, secret, network, time, memory, and output restrictions at the OS boundary.
- The default execution policy is deny. If the requested sandbox profile cannot be enforced on the current OS, the worker/repair action is not launched.
- A conformance runner may qualify a worker only when it executes inside the same or stricter enforced sandbox profile that production execution will use. Results are independently captured by the host and bound to exact worker bytes, manifest, suite, environment, and test-result digests.
- No trust-store entry or approval record can elevate a worker result into a final migration verdict.

## 4. Required lifecycle
`DISCOVER → IDENTIFY → SNAPSHOT → PLAN → QUALIFY → AUTHORIZE → ISOLATE → EXECUTE_STEP → VERIFY_STEP → RECORD → RECOVER_OR_CONTINUE → FINAL_AUDIT`.

Each transition is independently gated. A failed step stops later steps unless an explicit safe recovery operation is approved.

## 5. Acceptance
Acceptance requires end-to-end fixture migrations with deterministic source/target identities, verified knowledge, worker qualification, approval enforcement, isolated workspace, real transformation, build/test verification, exact diff review, ledger integrity, rollback/recovery, and independent final evidence. Include unsupported routes, expired/conflicted knowledge, worker substitution, authorization replay, partial copy, process crash, source mutation, and multi-target interference tests.

## 6. Non-claims
Do not claim universal code conversion, automatic API mapping discovery, production cross-loader Minecraft support, authenticated approval, OS isolation, or end-to-end migration success until the corresponding requirements have executable evidence.

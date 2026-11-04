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
- **MI-05 Approval authentication:** define a trusted approval identity and record-integrity boundary; caller-supplied reviewer strings alone are not authentication.
- **MI-06 Runtime enforcement:** enforce every permission and resource limit at the side-effect boundary; policy records alone do not enforce OS permissions.
- **MI-07 Workspace isolation:** preserve source baseline, target independence, safe path handling, cleanup, and explicit isolation-level reporting. Add Git-aware behavior only with tests for commit identity and worktree cleanup.
- **MI-08 Execution orchestration:** execute one typed transition at a time; capture before/after snapshots, worker result, diff, build/test evidence, recovery point, and ledger event.
- **MI-09 Recovery:** interruption and partial failure must leave a recoverable state; recovery actions are explicit, idempotent where possible, and evidence-recorded.
- **MI-10 Multi-target:** each target has independent route, authorization, workspace, execution, validation, and verdict, all pinned to one source baseline.
- **MI-11 Legacy compatibility:** run existing 1.1.0 workflow regression tests before and after integration; retain old behavior unless a reviewed migration changes it.
- **MI-12 Domain-neutrality:** Minecraft is the first reference domain, not a hard-coded control-plane assumption. New domains require executable adapters and evidence.
- **MI-13 QDAS:** use QDAS to audit migration changes, failure handling, and regression repairs; QDAS does not bypass migration authorization.
- **MI-14 Honest support claims:** a planned route, registered adapter, qualified worker, or copied workspace is not a completed migration.

## 4. Required lifecycle
`DISCOVER → IDENTIFY → SNAPSHOT → PLAN → QUALIFY → AUTHORIZE → ISOLATE → EXECUTE_STEP → VERIFY_STEP → RECORD → RECOVER_OR_CONTINUE → FINAL_AUDIT`.

Each transition is independently gated. A failed step stops later steps unless an explicit safe recovery operation is approved.

## 5. Acceptance
Acceptance requires end-to-end fixture migrations with deterministic source/target identities, verified knowledge, worker qualification, approval enforcement, isolated workspace, real transformation, build/test verification, exact diff review, ledger integrity, rollback/recovery, and independent final evidence. Include unsupported routes, expired/conflicted knowledge, worker substitution, authorization replay, partial copy, process crash, source mutation, and multi-target interference tests.

## 6. Non-claims
Do not claim universal code conversion, automatic API mapping discovery, production cross-loader Minecraft support, authenticated approval, OS isolation, or end-to-end migration success until the corresponding requirements have executable evidence.

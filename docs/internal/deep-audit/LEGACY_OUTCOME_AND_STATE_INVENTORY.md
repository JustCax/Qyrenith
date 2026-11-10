# Legacy Outcome and State Inventory — Qyrenith 1.2.0

**Inventory date:** 2026-11-10  
**Source revision:** `feature/1.2.0-universal-migration-core` as inspected on 2026-11-10  
**Status:** SOURCE-INVENTORIED INITIAL BASELINE — MAPPING NOT YET ACCEPTED  
**Purpose:** Evidence-based prerequisite for the owner-approved eight-state per-check outcome model.

## 1. Scope and method

This inventory records status-like values found in the current 1.1.0-compatible orchestrator and the migration/QDAS code already present in the 1.2.0 branch. It distinguishes operational exit codes, execution results, worker claims, planner/qualification states, evidence states, and project-analysis states. These vocabularies are not interchangeable.

The inventory is based on direct source inspection of:
- `qyrenith.py`
- `qyrenith_engine/execution.py`
- `qyrenith_engine/migration/assurance.py`
- `qyrenith_engine/migration/authorization.py`
- `qyrenith_engine/migration/model.py`
- `qyrenith_engine/migration/planner.py`
- `qyrenith_engine/migration/worker.py`
- `qyrenith_engine/qdas/events.py`
- `qyrenith_engine/qdas/ledger.py`
- `qyrenith_engine/qdas/diagnosis.py`
- `qyrenith_engine/qdas/repair.py`
- `tests/test_engine_110.py`
- `tests/test_engine_cli_110.py`

This is a source-level inventory, not a proof that every historical value stored in real user project state files has been observed. Before implementation, fixtures and representative real 1.1.0 state/evidence records must be inventoried without exposing secrets.

## 2. Canonical target vocabularies already approved

### 2.1 Per-check outcome vocabulary

`PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, `UNKNOWN`, `NOT_RUN`, `UNSUPPORTED`, `ERROR`.

### 2.2 Aggregate project assurance vocabulary

`ASSURED`, `NOT_ASSURED`, `BLOCKED`, `INCONCLUSIVE`, `PARTIAL`.

### 2.3 Reproducibility vocabulary

`REPRODUCIBLE`, `NON_REPRODUCIBLE`, `INCONCLUSIVE`, `BLOCKED`, `NOT_RUN`, `UNSUPPORTED`.

### 2.4 Extension support vocabulary

`NATIVE_SUPPORTED`, `QUALIFIED_PROVIDER`, `EXPERIMENTAL`, `PARTIAL`, `UNSUPPORTED`.

These are distinct typed contracts. A support classification, workflow lifecycle state, planner state, process exit status, or raw worker claim must not be copied directly into a per-check outcome without an explicit conversion rule.

## 3. Observed legacy and current source vocabularies

### 3.1 Top-level CLI exit/status vocabulary

The `EXIT` mapping in `qyrenith.py` defines:

| Raw value | Exit code | Initial semantic interpretation |
|---|---:|---|
| `SUCCESS` | 0 | Command-level success claim; not automatically a per-check PASS or project ASSURED. |
| `FAILED` | 1 | Generic command failure; subject failure versus infrastructure failure must be established. |
| `BLOCKED` | 2 | A policy/prerequisite gate stopped work; candidate BLOCKED. |
| `STOPPED` | 3 | User/policy/process stop; cause must distinguish BLOCKED from NOT_RUN or ERROR. |
| `PREFLIGHT_FAILURE` | 10 | Preflight did not complete; classify cause as BLOCKED, ERROR, or NOT_RUN. |
| `AUDIT_BLOCKER` | 11 | Required audit gate failed or was incomplete; candidate BLOCKED, not subject FAIL by default. |
| `UNKNOWN_API` | 12 | Required API/knowledge mapping absent; candidate UNKNOWN or UNSUPPORTED depending on qualified support evidence. |
| `DEPENDENCY_BLOCKER` | 13 | Dependency evidence/prerequisite unresolved; candidate BLOCKED or UNKNOWN. |
| `PORTING_FAILURE` | 14 | Migration operation failed; subject FAIL only when a supported oracle confirms the target contract was violated. |
| `BUILD_FAILURE` | 15 | Build command failed; distinguish subject build failure from runner/tool/infrastructure ERROR. |
| `VALIDATION_FAILURE` | 16 | Validation contract failed; candidate FAIL if subject-level, otherwise ERROR/BLOCKED. |
| `FIX_LIMIT_REACHED` | 17 | Repair loop stopped at a configured bound; candidate INCONCLUSIVE if the required verification remains unresolved. |
| `UNTRUSTED_BUILD` | 18 | Build result rejected due to source/trust inconsistency; candidate BLOCKED. |
| `USAGE` | 20 | Invalid/incomplete CLI invocation; check NOT_RUN or command ERROR, not subject FAIL. |
| `INTERNAL_ERROR` | 70 | Unexpected internal failure; candidate ERROR. |

### 3.2 Legacy orchestrator, build, and workflow values

Observed values include:
- Lifecycle/phase values: `INIT`, `IDLE`, `PREFLIGHT`, `AUDIT`, `BACKUP`, `PLAN`, `BUILD`, `TEST`, `VALIDATE`, `REPORT`, `FIX`, `STOP`, `TERMINAL`, `RUNNING`, `PENDING`, `OPEN`, `COMMITTED`, `WAITING_AGENT`, `READY_FOR_VERIFICATION`.
- Build results: `SUCCESS`, `FAILED`, `UNTRUSTED`.
- Worker/agent claims: `WORKED`, `NO_CHANGE`, `BLOCKED`, `FAILED`, `INVALID_RESULT`, `NOT_IMPLEMENTED`.
- Adapter/knowledge trust labels: `VERIFIED`, `COMMUNITY`, `UNKNOWN`, `UNTRUSTED`, `UNVERIFIED`.
- Evidence/dependency labels: `VERIFIED`, `PASS`, `UNKNOWN`, `BLOCKED`, `UNVERIFIED`.
- Analysis/review labels: `PASS`, `FAIL`, `REVIEW_REQUIRED`, `UNKNOWN`, `UNREADABLE`, `UNRESOLVED`, `RESOLVED_BY_EVIDENCE`.
- Snapshot/diff labels: `MATCH`, `CHANGED`, `UNCHANGED`, `COMMAND_CHANGED`.
- Other domain-specific states: `AVAILABLE`, `NOT_AVAILABLE`, `NOT_ACTIVE`, `SKIPPED_NO_GIT`, `SKIPPED_UNAVAILABLE`, `REQUIRES_VERIFICATION`, `NOT_SEMANTICALLY_VERIFIED`, `REPLAYABLE`, `REPLAY_BLOCKED`.

These values describe different dimensions. For example, `VERIFIED` may describe evidence/trust metadata, not a check outcome; `READY_FOR_VERIFICATION` is a lifecycle state; `MATCH` is a snapshot comparison result; and `WORKED` is a worker claim.

### 3.3 Migration assurance and planner

Source inspection found:
- `qyrenith_engine/migration/assurance.py` defines `_VERDICTS = {PASS, FAIL, BLOCKED, UNKNOWN, NOT_RUN, UNSUPPORTED, ERROR}`. It does not yet include the owner-approved `INCONCLUSIVE` state.
- The same module accepts worker claims `WORKED`, `NO_CHANGE`, `BLOCKED`, `FAILED`; these are not canonical per-check outcomes.
- Planner states include `PLANNED`, `BLOCKED`, `UNKNOWN`, `UNSUPPORTED`, and `PARTIAL`. They describe route planning, not check outcomes.
- Authorization/qualification states include `QUALIFIED`, `NO_WORK_REQUIRED`, and failure/eligibility states including `INCOMPATIBLE`, `NOT_REGISTERED`, `NOT_SELECTED`, `STALE`, `UNQUALIFIED`, `UNTRUSTED`, `BLOCKED`, and `UNKNOWN`. These describe worker/provider qualification and route readiness, not check results.

### 3.4 QDAS and bounded execution

- `qyrenith_engine/execution.py` emits process-level `PASS`, `FAIL`, `BLOCKED`, or `ERROR`.
- `qyrenith_engine/qdas/events.py` currently accepts execution-event statuses `PASS`, `FAIL`, `BLOCKED`, and `ERROR`; failure categories include `BUILD_FAILURE`, `TEST_FAILURE`, `STATIC_ANALYSIS_FAILURE`, `RUNTIME_FAILURE`, `INFRASTRUCTURE_FAILURE`, `TIMEOUT`, `RESOURCE_LIMIT`, `ANALYZER_FAILURE`, `UNSUPPORTED_STATE`, and `UNKNOWN_FAILURE`.
- QDAS diagnosis includes `UNCONFIRMED` as a hypothesis/causality state; it must not be confused with `UNKNOWN` or `INCONCLUSIVE` per-check outcomes.
- QDAS repair permissions include `PROPOSE_ONLY` and operation capabilities such as `READ_PROJECT`, `WRITE_PROJECT`, `EXECUTE_PROCESS`, `INSTALL_DEPENDENCIES`, `NETWORK`, `GIT_WRITE`, and `PUBLISH_ARTIFACT`. These are authorization/execution contract values, not verdicts.

The four-state execution event model is intentionally narrower than the eight-state per-check model: execution events report what happened to a bounded process. A higher-level check evaluator may derive `INCONCLUSIVE`, `UNKNOWN`, `NOT_RUN`, or `UNSUPPORTED` from scope, scheduling, oracle, and capability evidence. Do not blindly add all check outcomes to the process event schema.

## 4. Provisional mapping rules — not yet accepted

| Raw source state | Candidate target | Required condition |
|---|---|---|
| `SUCCESS` | `PASS` | Only if the exact check contract, scope, required evidence, and oracle are satisfied; never from exit code 0 alone. |
| `FAILED` | `FAIL` or `ERROR` | FAIL only for a confirmed subject violation; ERROR for tool/runner/internal failure. |
| `BLOCKED` | `BLOCKED` | Preserve blocker type and missing prerequisite. |
| `STOPPED` | `BLOCKED`, `NOT_RUN`, or `ERROR` | Depends on policy denial, cancellation, or unexpected process termination. |
| `PREFLIGHT_FAILURE` | `BLOCKED`, `ERROR`, or `NOT_RUN` | Depends on whether a safety prerequisite, infrastructure, or invalid invocation prevented evaluation. |
| `AUDIT_BLOCKER` | `BLOCKED` | Preserve exact mandatory gate and evidence gap. |
| `UNKNOWN_API` | `UNKNOWN` or `UNSUPPORTED` | UNKNOWN if knowledge is missing; UNSUPPORTED only if a qualified support catalog establishes no compatible implementation. |
| `DEPENDENCY_BLOCKER` | `BLOCKED` or `UNKNOWN` | Depends on known policy/prerequisite failure versus missing trustworthy compatibility information. |
| `PORTING_FAILURE` / `BUILD_FAILURE` / `VALIDATION_FAILURE` | `FAIL`, `ERROR`, or `BLOCKED` | Must classify subject-level violation versus runner failure versus policy/precondition block. |
| `UNTRUSTED_BUILD` | `BLOCKED` | Trust/integrity gate rejected the observation; do not treat as subject failure or PASS. |
| `FIX_LIMIT_REACHED` | `INCONCLUSIVE` | A bounded repair process ended without resolving the required verification claim. |
| `USAGE` | `NOT_RUN` or `ERROR` | No subject check ran; retain command validation error. |
| `INTERNAL_ERROR` | `ERROR` | Preserve exception/failure metadata with redaction. |
| `WORKED` / `NO_CHANGE` | No direct mapping | Worker claims are not check verdicts; require independent observation and verification. |
| `VERIFIED` / `COMMUNITY` / `UNVERIFIED` | No direct mapping | Trust/knowledge classifications are not check outcomes. |
| `PLANNED` / `QUALIFIED` / `NO_WORK_REQUIRED` | No direct mapping | Planner and provider lifecycle states are not execution results. |
| `MATCH` / `CHANGED` / `UNCHANGED` | No direct mapping | Snapshot/diff states require a check-specific evaluator and oracle. |
| `REVIEW_REQUIRED` / `UNRESOLVED` | Usually `INCONCLUSIVE` or `FAIL` | Depends on the policy rule and whether a confirmed violation exists. |

No mapping above is approved for runtime use. Every raw value must be preserved with source field, schema/version, original record, and conversion-rule version.

## 5. Gaps and required implementation work

1. Add `INCONCLUSIVE` to the migration per-check verdict contract only after all downstream consumers, serializers, schemas, reports, and tests are identified; do not alter process-event statuses indiscriminately.
2. Build a versioned mapping registry with exhaustive source-version coverage and explicit unknown/ambiguous fallback.
3. Inventory real historical state/evidence fixtures, including old schema versions and all documented aliases, with secrets redacted.
4. Separate CLI exit codes, workflow lifecycle, worker claims, trust classifications, planner states, process outcomes, check outcomes, aggregate assurance, reproducibility, and extension support in types and APIs.
5. Prove that no conversion path maps missing, stale, ambiguous, untrusted, blocked, inconclusive, not-run, unsupported, or error evidence to PASS/ASSURED.
6. Define behavior for cancellation, user stop, timeout, resource exhaustion, and partial output independently.
7. Add round-trip tests proving the original raw value and provenance survive conversion.

## 6. Acceptance criteria

- Every source status field and historical schema version has an explicit inventory entry or an explicit `UNMAPPED_UNKNOWN` fallback.
- Every mapping is tested with positive, negative, ambiguous, and malformed fixtures.
- Raw legacy values and provenance survive conversion and export/import.
- A legacy generic `SUCCESS` or `VERIFIED` cannot become PASS/ASSURED without evidence satisfying the new contract.
- Infrastructure failure never becomes subject-level FAIL without a subject-level oracle.
- Unsupported support scope never becomes zero findings.
- `INCONCLUSIVE` remains distinct from `UNKNOWN`, `BLOCKED`, and `ERROR`.
- Migration assurance, QDAS execution events, CLI exit codes, and aggregate assurance retain separate typed vocabularies.

## 7. Governance

This inventory is a planning artifact. It does not authorize schema or runtime changes. The mapping table must be completed and owner-reviewed before implementation. Update the traceability matrix with stable requirement IDs before marking any mapping requirement IMPLEMENTED.

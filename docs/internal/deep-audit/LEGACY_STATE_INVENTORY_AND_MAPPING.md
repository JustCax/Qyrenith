# Legacy State Inventory and Conservative AA-01 Mapping — Qyrenith 1.2.0

**Status:** SOURCE-INVENTORIED DESIGN INPUT — mapping proposal; implementation NOT STARTED  
**Inventory date:** 2026-11-10  
**Target branch:** `feature/1.2.0-universal-migration-core`  
**Purpose:** Establish the actual legacy state vocabularies before designing compatibility conversion. This document does not change runtime behavior or claim an exhaustive inventory of every user-generated historical state file.

## 1. Governing rule

The owner-approved AA-01 per-check vocabulary is:

`PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, `UNKNOWN`, `NOT_RUN`, `UNSUPPORTED`, `ERROR`.

These are check outcomes, not a universal replacement for every existing `status`, `state`, `phase`, worker protocol, transaction, evidence, or exit-code field.

Conversion MUST preserve the original field, raw value, source subsystem/schema version, record identity, and provenance. Mapping is contextual and typed. Unknown or ambiguous values remain `UNKNOWN`; they are never upgraded to `PASS`. A worker/action status is not itself a check outcome.

## 2. Source inventory

The following values were observed in the 1.2.0 branch source and schemas during this read-only inventory.

### 2.1 Legacy CLI workflow state

Source: `qyrenith.py`, especially `initial_state`, `set_phase`, `report`, `close_transaction`, and `cmd_health`.

| Field | Observed values / behavior | Meaning |
|---|---|---|
| `state` | Initially `INIT`; thereafter set to the current phase name | Workflow position, not a verdict |
| `phase` | `INIT`, `PREFLIGHT`, `AUDIT`, `PLAN`, `BUILD`, `VALIDATE`, `ANALYZE`, `FIX`, `PORT_STEP`, `REPORT` | Workflow phase |
| `phase_status` | `IDLE`, default `RUNNING`, `WAITING_AGENT`, `SUCCESS`, `TERMINAL`; health logic also recognizes `FAILED` | Phase lifecycle, not per-check outcome |
| `result_status` | `SUCCESS` is emitted by the successful terminal report path; failures may instead be represented by recorded issue/exit-code paths | Legacy run-level terminal result; exact historical values need fixture inventory |
| Issue status | `OPEN` is the observed default in `record_issue` | Issue lifecycle, not check outcome |
| Transaction status | `OPEN`, `COMMITTED`, `REJECTED_AGENT_RESULT`, `REJECTED_REALITY_DIFF`, `REJECTED_DEPENDENCY_DRIFT`, `REJECTED_FILE_CHANGE_DECLARATION`, `REJECTED_SECURITY_REVIEW` | Migration transaction lifecycle |
| Exit codes | Named values include `SUCCESS`, `FAILED`, `BLOCKED`, `STOPPED`, `PREFLIGHT_FAILURE`, `AUDIT_BLOCKER`, `UNKNOWN_API`, `DEPENDENCY_BLOCKER`, `PORTING_FAILURE`, `BUILD_FAILURE`, `UNTRUSTED_BUILD`, `VALIDATION_FAILURE`, `FIX_LIMIT_REACHED`, `USAGE`, `INTERNAL_ERROR` | Process/CLI control result; not a status enum |

Phase names, transaction statuses, issue states, and exit labels MUST NOT be passed directly into the per-check outcome mapper.

### 2.2 Execution and QDAS

Sources: `qyrenith_engine/execution.py`, `qyrenith_engine/qdas/events.py`, `qyrenith_engine/qdas/collector.py`, `qyrenith_engine/qdas/ledger.py`, `qyrenith_engine/dynamic_audit_qdas.py`.

| Contract | Observed values | Semantics |
|---|---|---|
| Bounded process report / QDAS execution event | `PASS`, `FAIL`, `BLOCKED`, `ERROR` | Execution-layer result; intentionally narrower than the full per-check vocabulary |
| Execution flags | `timed_out`, `output_limited`, `output_incomplete`, `input_incomplete`, `unsupported_state` | Context explaining why execution did not complete normally |
| Failure categories | `BUILD_FAILURE`, `TEST_FAILURE`, `STATIC_ANALYSIS_FAILURE`, `RUNTIME_FAILURE`, `INFRASTRUCTURE_FAILURE`, `TIMEOUT`, `RESOURCE_LIMIT`, `ANALYZER_FAILURE`, `UNSUPPORTED_STATE`, `UNKNOWN_FAILURE` | Symptom classification, not verdict |
| Failure hypothesis state | `UNCONFIRMED` | Hypothesis lifecycle; it is deliberately not a confirmed root cause |

QDAS currently requires a blocked execution event when `unsupported_state` or another incomplete/bounded-execution flag is set. This lower-level execution representation may remain `BLOCKED`; the higher-level check outcome must retain the specific reason and may resolve to `UNSUPPORTED` when the capability itself is unsupported. Do not erase the distinction by treating every blocked execution as the same check outcome.

### 2.3 Migration assurance ledger

Source: `qyrenith_engine/migration/assurance.py` and `schemas/migration-assurance-record.schema.json`.

| Field | Observed values |
|---|---|
| `verdict` / `_VERDICTS` | `PASS`, `FAIL`, `BLOCKED`, `UNKNOWN`, `NOT_RUN`, `UNSUPPORTED`, `ERROR` |
| `worker_status` / `_WORKER_STATUSES` | `WORKED`, `NO_CHANGE`, `BLOCKED`, `FAILED` |
| PASS gate | Requires `WORKED`, changed files, diff digest, post-state digest, evidence IDs, commit ID, and qualified worker provenance | A Qyrenith verdict, not a worker self-report |

**Known gap:** `INCONCLUSIVE` is absent from both the current migration assurance verdict allowlist and its JSON schema, despite being part of the owner-approved eight-state vocabulary. This must be corrected before the final compatibility contract is considered complete. Existing records must not be rewritten merely to make the new enum fit.

### 2.4 Migration worker and planner states

Sources: `qyrenith_engine/migration/worker.py`, `qyrenith_engine/migration/planner.py`.

| Contract | Observed values | Meaning |
|---|---|---|
| Worker result status | `WORKED`, `NO_CHANGE`, `BLOCKED`, `FAILED` | Worker/action report; not assurance verdict |
| Worker resolution | `BLOCKED`, `NOT_SELECTED`, `NOT_REGISTERED`, `INCOMPATIBLE`, `UNQUALIFIED`, `UNTRUSTED`, `STALE`, `QUALIFIED` | Worker selection/trust/qualification state |
| Route worker assessment | `ROUTE_NOT_PLANNED`, `NO_WORK_REQUIRED`, `UNKNOWN`, `BLOCKED`, `QUALIFIED` | Aggregate assessment of worker readiness for a route |
| Route plan | `PLANNED`, `UNKNOWN`, `BLOCKED`, `UNSUPPORTED` | Planning result |
| Multi-target route plan | Derived states include `PLANNED`, `PARTIAL`, `UNKNOWN`, `BLOCKED`, `UNSUPPORTED` | Coverage across multiple targets |
| Worker qualification result | Must be `PASS` | Qualification test-suite result; not the worker's own assurance verdict |

These state families must remain distinct. In particular, `QUALIFIED` is not `PASS` for project verification; `WORKED` is not proof of a correct change; `NO_CHANGE` is not automatically a failure or pass; `NOT_SELECTED` is not `NOT_RUN` without a check-level scope decision.

### 2.5 Other observed legacy statuses

Source: `qyrenith.py`, `qyrenith_engine/analysis_qdas.py`, and related models.

| Context | Observed values | Mapping caution |
|---|---|---|
| Security scan/report | `PASS`, `REVIEW_REQUIRED` | Review required is not automatically subject-level FAIL; unresolved mandatory review blocks assurance |
| Archive safety | `PASS`, `REVIEW_REQUIRED` | Narrow archive-safety result only |
| Provider declaration/discovery | `DECLARED`, `DISCOVERED`, `BLOCKED` | Registration/discovery is not qualification or support |
| Evidence status | Default `OBSERVED`; imported reference fallback `AVAILABLE`; dependency checks use `VERIFIED`, `UNKNOWN`, `BLOCKED`; other evidence values are caller-supplied | Evidence lifecycle labels, not per-check outcomes |
| Version graph | `EVIDENCED`, `VERIFIED`, `OBSERVED`, `CURRENT`, `TARGET`, `PRESENT`, `REFERENCED` | Knowledge/identity annotations |
| Adapter/worker protocol errors | `NOT_IMPLEMENTED`, `INPUT_LIMIT`, `APPROVAL_REQUIRED`, `COMMAND_CHANGED`, `TIMEOUT`, `OUTPUT_LIMIT`, `INPUT_INCOMPLETE`, `OUTPUT_INCOMPLETE`, `INVALID_RESULT`, `FAILED` | Protocol/lifecycle errors; must be interpreted with execution facts |
| Static-analysis QDAS adapter | Maps analyzer `PASS`, `FAIL`, `BLOCKED`, `UNKNOWN`; currently maps `UNKNOWN` to execution `ERROR`, and unrecognized values to `ERROR` | **Semantic concern:** analyzer uncertainty is not necessarily infrastructure error; retain raw status and distinguish unsupported, unknown, inconclusive, and actual adapter error |

## 3. Conservative mapping proposal

This is a semantic mapping policy, not a bulk rewrite instruction.

| Source observation | Candidate per-check outcome | Conditions / restrictions |
|---|---|---|
| Explicit validated check success | `PASS` | Only after required evidence, scope, freshness, profile, and independent validation gates pass |
| Explicit completed check failure | `FAIL` | The subject was actually evaluated and the check's failure condition was observed |
| Authorization, policy, prerequisite, or isolation gate prevented execution | `BLOCKED` | Preserve the specific blocker and whether the check ran |
| Evaluation ran but cannot establish a defensible conclusion | `INCONCLUSIVE` | Use for bounded/ambiguous evidence or unresolved oracle uncertainty; do not use as a synonym for missing knowledge |
| No trustworthy supported information exists | `UNKNOWN` | Preserve raw value and reason; do not infer success/failure |
| Required check was not executed | `NOT_RUN` | Must be scoped to a requested/mandatory check; absence from inventory alone is not enough |
| Required capability/version/feature is explicitly unsupported | `UNSUPPORTED` | Must bind to exact support scope; never represent as zero findings |
| Infrastructure/adapter/runner failed before a valid subject result | `ERROR` | Do not relabel as subject-level `FAIL` |

### Legacy labels that must not be mapped without context

- `SUCCESS`: may describe a complete old workflow, a process exit, or a narrow sub-operation. It is not automatically `PASS`.
- `FAILED`: may describe a subject check, worker process, validation gate, or internal failure. It requires the original event and subsystem context.
- `STOPPED`, `TERMINAL`, `REJECTED_*`, `REVIEW_REQUIRED`: control/lifecycle outcomes, not a universal check verdict.
- `WORKED`, `NO_CHANGE`, `QUALIFIED`, `VERIFIED`: domain-specific action, qualification, or evidence claims; none alone proves a check passed.
- `DECLARED`, `DISCOVERED`, `AVAILABLE`, `CURRENT`, `TARGET`, `PRESENT`, `REFERENCED`: descriptive states, not check outcomes.
- Missing, null, malformed, or unrecognized values: preserve raw representation and map to `UNKNOWN` unless a more specific typed failure is independently established.

## 4. Confirmed reconciliation gaps

1. Add `INCONCLUSIVE` to the migration assurance verdict contract and its JSON schema in a later implementation slice; keep old records byte-for-byte/logically unchanged.
2. Review `analysis_qdas.py`: its current `UNKNOWN` → `ERROR` conversion conflates subject uncertainty with infrastructure failure. Preserve raw analyzer output and introduce a typed mapping that reserves `ERROR` for actual adapter/transport/runtime errors.
3. Preserve the QDAS execution-level four-state enum while defining a separate check-outcome mapping layer. Do not force every low-level event to adopt all eight per-check states.
4. Keep worker result, worker resolution, route plan, route assessment, phase, transaction, issue, evidence, support, and verdict state vocabularies typed and separate.
5. Inventory actual persisted state files and historical fixtures before claiming exhaustive legacy conversion. Source declarations alone cannot prove which historical values exist in user data.

## 5. Required next artifacts before implementation

- A versioned legacy-state schema inventory including source schema versions and historical fixture corpus.
- An exhaustive mapping table for every observed legacy value, with context-specific rule and explicit `UNKNOWN` fallback.
- Round-trip/preservation rules for raw values and provenance.
- Migration tests for valid, ambiguous, unknown, malformed, stale, and contradictory historical records.
- Evidence proving old records are not upgraded to `PASS` and new `INCONCLUSIVE` values validate correctly.
- Traceability links from every mapping rule to implementation, tests, and retained evidence.

## 6. Source scope and limitations

This first inventory read the 1.2.0 branch versions of:
- `qyrenith.py`
- `qyrenith_engine/execution.py`
- `qyrenith_engine/approval.py`
- `qyrenith_engine/trust_store.py`
- `qyrenith_engine/migration/model.py`
- `qyrenith_engine/migration/planner.py`
- `qyrenith_engine/migration/assurance.py`
- `qyrenith_engine/migration/authorization.py`
- `qyrenith_engine/migration/worker.py`
- `qyrenith_engine/qdas/events.py`
- `qyrenith_engine/qdas/collector.py`
- `qyrenith_engine/qdas/ledger.py`
- `qyrenith_engine/qdas/diagnosis.py`
- `qyrenith_engine/qdas/repair.py`
- `qyrenith_engine/analysis_qdas.py`
- `qyrenith_engine/dynamic_audit_qdas.py`
- `schemas/migration-assurance-record.schema.json`
- `schemas/qdas-event-ledger-record.schema.json`

The inventory is source-based, not a scan of user project state directories or every historical release artifact. Additional modules, schemas, CLI outputs, documentation examples, and real legacy fixtures still require a systematic sweep. No runtime code, schema, or tests were changed as part of this document.

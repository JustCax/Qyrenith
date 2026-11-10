# Qyrenith Development Assurance System (QDAS)

**Status:** Required first implementation milestone for 1.2.0  
**Role:** Development-time assurance orchestration  
**Normative language:** MUST, MUST NOT, SHOULD, MAY

## 1. Objective

QDAS continuously verifies development work performed on Qyrenith itself and, when explicitly enabled, on managed projects. It converts build/test/analyzer failures into evidence-linked diagnoses and controlled repair cycles. It does not promise automatic repair, and it never treats an AI or worker claim as proof.

QDAS is implemented and accepted before the other fourteen deep-audit capability modules. Those modules are then developed with QDAS assistance, while QDAS itself is checked by independent CI and reproducible external tests.

## 2. Canonical lifecycle

`CAPTURE → CLASSIFY → INVESTIGATE → HYPOTHESIZE → PLAN → APPROVE → ISOLATE → REPAIR → REVERIFY → COMPARE → RECORD`

A stage may stop with UNKNOWN, INCONCLUSIVE, BLOCKED, or NEEDS_HUMAN_REVIEW. No stage may silently skip a failed prerequisite.

## 3. Requirements

### QDAS-01 — Event ingestion
Ingest build, test, static-analysis, runtime, and verification events. Record project/revision identity, workspace identity, OS, architecture, runtime/tool versions, exact argv, working directory, relevant environment fingerprint, start/end time, exit code, timeout/resource outcome, and bounded stdout/stderr digests. Secrets MUST be redacted before persistence; raw output retention is policy-controlled.

### QDAS-02 — Failure classification
Distinguish BUILD_FAILURE, TEST_FAILURE, STATIC_ANALYSIS_FAILURE, RUNTIME_FAILURE, INFRASTRUCTURE_FAILURE, TIMEOUT, RESOURCE_LIMIT, ANALYZER_FAILURE, UNSUPPORTED_STATE, and UNKNOWN_FAILURE. Preserve the original exit status and raw classification evidence.

### QDAS-03 — Root-cause hypotheses
Generate ranked hypotheses with supporting and contradicting evidence, affected components, confidence rationale, and missing evidence. Correlation MUST NOT be described as causation. Multiple plausible causes remain multiple hypotheses.

### QDAS-04 — Repair planning
Each repair plan identifies the target failure, affected paths/components, expected invariants, minimal intended change, risk, likely regressions, required permissions, validation commands, and rollback strategy.

### QDAS-05 — Baseline and isolation
Capture an exact baseline snapshot and create a uniquely identified isolated workspace. Verify the workspace against the baseline before repair. Filesystem copies alone MUST NOT be called OS/process sandboxes. Symlinks, special files, external mounts, and Git metadata require explicit safe handling.

### QDAS-06 — Controlled repair execution
Repair execution is bounded by an explicit manifest: allowed paths, operations, commands, time, memory/output limits, and network/install permissions. No implicit network, package installation, credential access, commit, push, or publish is allowed.

### QDAS-07 — Reverification
Rerun pinned commands and toolchain versions. Capture the same evidence dimensions as the baseline. If exact reproduction is impossible, report the difference and lower the verification claim.

### QDAS-08 — Regression protection
The original failing check MUST pass after repair, and the full pre-existing required test set MUST remain intact and pass. Deleting, skipping, weakening, quarantining, or changing assertions to hide a failure is not a valid repair. Test inventory and relevant configuration are compared before and after.

### QDAS-09 — Evidence lineage
Maintain explicit links: event → failure classification → hypothesis → repair plan → approval → workspace/baseline → patch → rerun → comparison → verdict. Every link is content-addressed and provenance-bearing.

### QDAS-10 — Bounded convergence
Set retry, wall-clock, CPU, memory, output, and patch-size budgets. Detect repeated patches, repeated failure signatures, oscillation, and no-progress cycles. Stop safely when a budget is exhausted.

### QDAS-11 — Human approval gates
Require explicit approval for source writes, process execution beyond pre-approved safe checks, network access, dependency installation, Git writes, commits, and publication. Approval is exact-scope, time-bounded, and invalidated by relevant manifest or command changes.

### QDAS-12 — Propose-only mode
Without execution authority, QDAS may diagnose and propose a patch/plan only. It MUST NOT infer permission from prior approval, agent instruction, repository content, or a worker manifest.

### QDAS-13 — Qyrenith self-verification
Self-verification uses clean external CI, reproducible package/build checks, independent test runners where feasible, mutation fixtures, and retained artifacts. The verifier must not rely exclusively on the same code path being evaluated.

### QDAS-14 — No self-certification
Qyrenith's own verdict alone MUST NOT establish AUDIT_VERIFIED for Qyrenith. Independent evidence from an external execution boundary is mandatory; critical claims SHOULD have an independent oracle or reviewer.

### QDAS-15 — Verdict separation
Use the exact scoped meanings of BUILD_VERIFIED, TEST_VERIFIED, STATIC_ANALYSIS_VERIFIED, BEHAVIOR_VERIFIED, and AUDIT_VERIFIED defined in the master architecture. A higher-sounding label must never be inferred from a lower-level result.

### QDAS-16 — Failure Intelligence
Store structured, versioned failure patterns, environment signatures, hypotheses, repairs, and outcomes with source/evidence provenance. Observed fixes remain OBSERVED until reviewed and independently validated. No automatic promotion to VERIFIED.

### QDAS-17 — False-fix resistance
Detect changes to tests, assertions, build scripts, analyzer configuration, exclusions, or baseline scope that could suppress the original failure. Such changes require explicit review and cannot be counted as a repair without independent justification.

### QDAS-18 — Evidence integrity
Use append-only event records with canonical serialization, content digests, sequence/parent linkage, and fail-closed verification. Hash chains detect accidental/tamper edits but do not authenticate an actor able to replace the entire store; state that residual risk.

### QDAS-19 — Repeatability
Pin or fingerprint toolchains, commands, environment, inputs, and workspace baseline. Repeat selected repairs in a clean workspace to detect non-deterministic outcomes. Report any unavoidable environmental variance.

### QDAS-20 — Safe stop and escalation
If evidence is insufficient, no safe repair exists, the failure recurs, budgets are exhausted, or a permission boundary is reached, stop without claiming success. Emit a concise diagnosis, unresolved questions, and next required human action.

### QDAS-21 — Approval authenticity and replay protection
Approval must originate from a trusted host interaction or a configured authenticated approval service. Agent text, worker output, repository files, and caller-supplied reviewer strings are not approval. Approval is bound to the exact action scope, command/manifest digest, baseline, and a single-use nonce or equivalent replay-resistant token. If trusted approval cannot be established, QDAS remains propose-only.

### QDAS-22 — Enforced execution isolation and least privilege
Declared worker permissions are policy metadata, not operating-system enforcement. Any repair or worker execution that can modify files, spawn processes, access secrets, install dependencies, or use the network must run inside an enforceable OS sandbox or equivalent host-controlled isolation boundary with explicit read/write roots, process limits, environment controls, and network policy. If the host cannot enforce the requested boundary, QDAS must remain propose-only and report the missing capability; it must never claim that a manifest or command allowlist provides sandboxing.

## 4. State model

`CAPTURED, CLASSIFIED, INVESTIGATING, PLANNED, AWAITING_APPROVAL, REPAIRING, REVERIFYING, RESOLVED, REGRESSION, INCONCLUSIVE, BLOCKED, ABORTED`.

Transitions are explicit and persisted. RESOLVED requires QDAS-07, QDAS-08, and QDAS-09 evidence. A repair attempt that changes files but does not pass reverification is not RESOLVED.

## 5. Safety and permission model

Default mode is read-only. The operator separately grants exact write and execution capabilities. Network and dependency installation are denied by default. Commit, push, release, and publication are never implied by repair permission. A QDAS repair cannot modify the original project before approval and cannot bypass the normal Qyrenith safety/reality-diff/commit gates.

## 6. Interfaces

QDAS consumes normalized events from the execution and verification layers and emits typed failure, hypothesis, repair-plan, approval, patch, rerun, comparison, and verdict records. Its public API must avoid importing optional analyzers at module import time. CLI commands must support inspect/plan/propose/run/verify/report with read-only defaults and explicit execution confirmation.

## 7. Required adversarial tests

- Non-zero build exit; test failure; analyzer crash; timeout; output flood; process spawn failure.
- Malformed, truncated, duplicated, reordered, and tampered evidence records.
- A worker that ignores stdin, floods stdout/stderr, forks children, or exits after a partial patch.
- A repair that deletes a test, weakens an assertion, edits exclusions, changes the build command, or alters the baseline.
- A repair that fixes one failure but introduces another.
- Retry loops, oscillating patches, nondeterministic results, and exhausted budgets.
- Approval replay, scope expansion, manifest substitution, and permission escalation.
- Qyrenith analyzer bug caught by an independent fixture/oracle.

## 8. Acceptance gate

All QDAS-01..22 requirements need implementation and positive/negative/adversarial tests. QDAS must demonstrate at least one deterministic failure-to-diagnosis-to-repair-to-reverification scenario in a disposable fixture, plus safe-stop scenarios. The independent CI run must pass. QDAS cannot be marked complete solely by its own report.

## 9. Explicit non-claims

QDAS is not a general autonomous coding agent, an OS sandbox, a cryptographic identity provider, a guarantee that every failure can be repaired, or permission to commit/publish. It does not turn unverified historical observations into trusted knowledge.

# Qyrenith 1.2.0 Deep Audit — Master Architecture

**Status:** Accepted implementation direction; specification baseline  
**Release target:** 1.2.0  
**Implementation branch:** `feature/1.2.0-universal-migration-core`  
**Normative language:** MUST, MUST NOT, SHOULD, and MAY are requirements terms.

## 1. Purpose and delivery order

Qyrenith 1.2.0 is a deterministic, evidence-led verification and migration control plane. Its deep-audit architecture expands the existing 1.1.0 verification workflow without weakening backward compatibility.

The delivery order is mandatory:

1. Complete and cross-review the full 1.2.0 documentation set.
2. Audit and finish the already-started migration-platform work, including regressions, stale claims, CI failures, and integration gaps.
3. Implement and validate the Qyrenith Development Assurance System (QDAS).
4. Implement the remaining fourteen capability modules under QDAS-assisted development.
5. Run integrated acceptance, independent verification, packaging, and release-readiness checks. Do not publish or merge without explicit owner approval.

Documentation is a binding engineering contract, not evidence that a capability exists. A feature is complete only when its implementation, tests, negative tests, evidence, and acceptance mapping all pass.

## 2. System boundaries

The architecture has five cooperating planes:

- **Control plane:** CLI, workflow orchestration, policy, approvals, lifecycle state, and final verdict aggregation.
- **Analysis plane:** native Qyrenith parsers, structural/semantic analyzers, dependency and impact graphs, security checks, and domain adapters.
- **Execution plane:** bounded process invocation, reproducible verification lab, isolated workspaces, test/fuzz/formal runners, and controlled repair execution.
- **Knowledge plane:** versioned compatibility and failure knowledge with provenance, scope, validity, conflict handling, and explicit review.
- **Evidence plane:** immutable event/evidence records, digests, lineage, confidence, coverage, and externally reproducible verification artifacts.

QDAS orchestrates these planes during development. It is not a privileged bypass around policy, and it does not replace the ordinary project verification workflow.

## 3. Trust and authority model

The following states are distinct and MUST NOT be collapsed:

| State | Meaning |
|---|---|
| DECLARED | A component or capability is described. |
| DISCOVERED | A component was found and parsed. |
| QUALIFIED | A reviewed qualification record matches exact identity, version, scope, and evidence. |
| AUTHORIZED | A human-approved policy grant permits a specific action within exact bounds. |
| EXECUTED | The pinned action actually ran in the identified environment/workspace. |
| VERIFIED | Independent observations satisfy a named verification contract. |

A worker, AI model, adapter, parser, or analyzer MUST NOT grant itself qualification or final success. An authorization record is not an OS sandbox. A workspace copy is not process isolation. A digest proves byte identity, not truth or publisher identity.

## 4. Verification verdict vocabulary

- **BUILD_VERIFIED:** the exact declared build command completed successfully in the recorded environment.
- **TEST_VERIFIED:** the exact declared test set completed successfully; test identity and result evidence are retained.
- **STATIC_ANALYSIS_VERIFIED:** the named static-analysis rules and scopes completed with no disallowed findings.
- **BEHAVIOR_VERIFIED:** specified observable behavior passed the declared behavioral oracle.
- **AUDIT_VERIFIED:** a named audit policy's required coverage and evidence thresholds were satisfied.
- **INCONCLUSIVE:** analysis ran but bounded limits, missing oracles, or unresolved uncertainty prevent a conclusion.
- **UNKNOWN:** the system lacks sufficient supported knowledge or capability.
- **BLOCKED:** a safety, policy, integrity, conflict, or prerequisite gate prevents continuation.
- **UNSUPPORTED:** no compatible implementation or adapter exists for the requested scope.

These are scoped claims. BUILD_VERIFIED does not imply TEST_VERIFIED; TEST_VERIFIED does not imply STATIC_ANALYSIS_VERIFIED; none alone implies AUDIT_VERIFIED.

## 5. Module contracts

Every module MUST declare: purpose, inputs, outputs, identity/scope rules, trust assumptions, resource bounds, failure states, evidence emitted, public API/CLI impact, compatibility constraints, positive and negative tests, acceptance criteria, and explicit non-claims.

Module interfaces MUST be versioned and capability-discovered. Unsupported language or domain features must return explicit unsupported/inconclusive states rather than silently skipping required analysis.

## 6. Native-engine policy

All core analyzers are newly implemented as native Qyrenith components. External tools may be invoked only through explicit optional adapters and approved execution policy; they are not required runtime dependencies. Research may compare concepts and published behavior, but implementation must be independently designed and written. No third-party source code or proprietary rule corpus may be copied.

## 7. Global invariants

1. Deterministic inputs produce deterministic normalized outputs where the underlying observation is deterministic.
2. Every finding has a stable identity, source location or object reference, severity, rationale, and evidence lineage.
3. Unknown is not pass; unsupported is not zero findings.
4. Conflicts and integrity failures fail closed.
5. Resource exhaustion yields INCONCLUSIVE or BLOCKED, never PASS.
6. Exclusions are explicit, hashed, reported, and included in coverage.
7. Analysis must not modify the source project.
8. Repair runs only in an approved isolated workspace and is always diff-reviewed.
9. A repair is valid only if the original failure is resolved and the unchanged baseline checks still pass.
10. Qyrenith cannot be the sole authority verifying its own implementation.

## 8. Integration and dependency order

QDAS depends on the evidence model, reproducible lab, execution boundary, root-cause analysis, and policy controls. Other modules expose stable capability contracts to QDAS. The static, dynamic, formal, fuzz, security, knowledge, adapter, maturity, and meta-audit modules remain independently testable.

The implementation plan is the source of truth for sequencing and release gates. Changes to accepted architecture require a documented decision record and owner approval before implementation.

## 9. Release gate

The 1.2.0 release is blocked until every accepted requirement is either implemented and verified or explicitly removed by an owner-approved scope change. A documented limitation is not a substitute for a promised feature. CI must pass on the current head across the supported platform/Python matrix, public package contents must be checked, and a clean external verification run must be retained.

## 10. Requirement map

- DA-01: this master architecture.
- DA-02..DA-13: the corresponding capability specifications.
- DA-14: implementation and acceptance plan, including migration-platform integration and integrated reporting/orchestration acceptance.
- QDAS-01..QDAS-20: the dedicated QDAS specification and cross-module integration requirements.

The specification index lists all seventeen normative documents plus the navigation README. The fourteen capability modules implemented after QDAS are enumerated in the implementation plan.

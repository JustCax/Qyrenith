# Advanced Assurance Requirements

**Document ID:** QYR-AA-REQ  
**Revision:** 1  
**Status:** Proposed for AA-01 acceptance  
**Applies to:** Qyrenith core and first-party verification capabilities  
**Baseline:** Qyrenith 1.1.0, commit `647398246bc6bc15fdf8fe6038af1bec35710806`

## 1. Purpose

This document converts the Advanced Assurance Program into stable, testable product requirements. It defines what the system must guarantee, what it must disclose, and how each requirement is accepted. It does not claim that the capabilities described here are implemented.

The requirements are intentionally implementation-neutral. Architecture decisions may refine component boundaries, but they must not weaken a requirement without a recorded decision and an explicit scope review.

## 2. Scope

Advanced Assurance applies to project discovery, verification planning, checker execution, evidence handling, policy decisions, reporting, extensibility, security, resilience, compatibility, and release assurance.

The program is project-neutral. Minecraft remains an important reference domain, not a privileged dependency of the core. The same core must be usable for ordinary software projects and other supported modding/content ecosystems.

### 2.1 In scope

- Deterministic project inventory and source traceability.
- Explicit, inspectable verification plans.
- A versioned checker contract and bounded execution lifecycle.
- Validation and storage of evidence with provenance.
- Policy evaluation independent of checker execution.
- Clear result states and non-bypassable mandatory gates.
- Native verification capabilities with declared support limits.
- Opt-in external providers and workers behind validated interfaces.
- Security and trust-boundary controls.
- Failure analysis, recovery, reproducibility, and compatibility.
- User-readable and machine-readable reports.
- Release artifact integrity and provenance.

### 2.2 Out of scope unless separately accepted

- A hosted SaaS service or mandatory account system.
- A proprietary cloud dependency.
- A mandatory AI model, AI agent, or external scanner.
- A general-purpose replacement for compilers, build systems, test frameworks, or security products.
- Claims of formal proof, complete semantic understanding, or malware detection without a specific validated method.
- An operating-system sandbox implemented only by process timeouts or environment filtering.
- Automatic mutation, installation, network access, or publication without explicit authorization.
- An opaque global project-health score.

## 3. Normative language

**MUST**, **MUST NOT**, **SHOULD**, and **MAY** are requirements terms. A MUST requirement is mandatory for acceptance. A SHOULD requirement may be deferred only with a documented rationale, affected scope, and compensating control.

Requirement priorities:

- **P0:** safety, correctness, or release integrity; blocks acceptance when unmet.
- **P1:** essential product capability; blocks the phase that introduces the capability.
- **P2:** quality or usability improvement; may be scheduled after the foundational gate.

## 4. Product invariants

1. A claim is not evidence merely because an agent, checker, process, or provider states it.
2. Missing, stale, contradictory, truncated, malformed, or unvalidated evidence cannot produce PASS.
3. A check that did not execute remains NOT_RUN.
4. An unsupported capability remains UNSUPPORTED; it is not silently omitted.
5. Infrastructure failure is distinguishable from a project defect.
6. A checker cannot authorize its own evidence or the final assurance decision.
7. The policy evaluator is deterministic for the same declared policy and validated inputs.
8. Critical failures cannot be hidden by averages, percentages, or summaries.
9. Project-controlled code is not executed during default discovery.
10. Every operation with side effects is visible and requires the appropriate authorization.
11. AI is optional and advisory; it cannot independently satisfy a mandatory verification requirement.
12. A limitation is reported at the level of the claim it affects.

## 5. Functional requirements

### 5.1 Project discovery and model

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-PROJ-001 | P0 | The system MUST identify the inspected project root and preserve its canonical, scoped identity for the duration of a run. |
| AA-REQ-PROJ-002 | P0 | Discovery MUST be read-only by default and MUST NOT import, execute, install, or build project-controlled code. |
| AA-REQ-PROJ-003 | P1 | The project model MUST represent observed files, configuration, languages, build systems, dependencies, entry points, tests, and platform constraints when evidence is available. |
| AA-REQ-PROJ-004 | P0 | Every derived project fact MUST retain a reference to the evidence source that supports it. |
| AA-REQ-PROJ-005 | P0 | Unknown, conflicting, incomplete, or unsupported discovery facts MUST remain explicitly distinguishable. |
| AA-REQ-PROJ-006 | P1 | Discovery MUST support bounded traversal and disclose exclusions, symlink decisions, entry limits, and incomplete scans. |

### 5.2 Verification planning

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-PLAN-001 | P0 | Every execution run MUST be based on an explicit, inspectable plan. |
| AA-REQ-PLAN-002 | P0 | A plan MUST identify each check, its version, purpose, scope, prerequisites, inputs, permissions, resource limits, expected evidence, and result mapping. |
| AA-REQ-PLAN-003 | P0 | Plan generation MUST be deterministic for equivalent declared project facts, profile, policy, and engine versions. |
| AA-REQ-PLAN-004 | P0 | The system MUST NOT silently broaden the requested project scope or introduce a side effect absent from the plan. |
| AA-REQ-PLAN-005 | P1 | Users MUST be able to inspect why a check was selected, excluded, blocked, or unsupported before execution. |
| AA-REQ-PLAN-006 | P0 | Optimization MUST NOT omit a mandatory check required by the selected policy. |

### 5.3 Checker contract and runtime

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-CHK-001 | P0 | Every checker MUST have a stable identifier, version, declared purpose, supported scope, and compatibility declaration. |
| AA-REQ-CHK-002 | P0 | Checker inputs, outputs, permissions, side effects, and evidence expectations MUST be explicit and versioned. |
| AA-REQ-CHK-003 | P0 | Checker output MUST be schema-validated before it is accepted as evidence input. |
| AA-REQ-CHK-004 | P0 | The runtime MUST enforce configured timeout and output limits and report when a limit truncates or terminates execution. |
| AA-REQ-CHK-005 | P0 | Checker crash, invalid output, timeout, cancellation, and infrastructure failure MUST remain distinguishable. |
| AA-REQ-CHK-006 | P0 | A checker MUST NOT be able to write or select the final policy decision. |
| AA-REQ-CHK-007 | P0 | Project-controlled commands MUST NOT execute unless the plan and user authorization explicitly permit them. |
| AA-REQ-CHK-008 | P1 | A checker MUST be testable independently through a conformance suite without requiring the full CLI. |

### 5.4 Evidence and provenance

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-EVD-001 | P0 | Every accepted evidence item MUST have a stable identifier and a declared evidence type. |
| AA-REQ-EVD-002 | P0 | Evidence MUST identify the project scope, checker and version, plan and policy versions, inputs, relevant environment, and observation time. |
| AA-REQ-EVD-003 | P0 | Content references MUST use stable scoped paths or opaque object references and record integrity digests where applicable. |
| AA-REQ-EVD-004 | P0 | The evidence validator MUST reject malformed, incomplete, unsupported, or integrity-invalid records. |
| AA-REQ-EVD-005 | P0 | Interrupted writes MUST NOT leave records that validate as complete evidence. |
| AA-REQ-EVD-006 | P0 | Evidence immutability and retention semantics MUST be documented; corrections MUST be represented as new records or explicit supersession events. |
| AA-REQ-EVD-007 | P0 | Hashes MUST be described as integrity checks relative to a trusted digest, not proof that the underlying observation was truthful. |
| AA-REQ-EVD-008 | P1 | Reports MUST provide traceability from a decision to the evidence and policy rule that support it. |

### 5.5 Policy and decisions

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-POL-001 | P0 | Policy evaluation MUST be separate from checker execution and checker output generation. |
| AA-REQ-POL-002 | P0 | Core states MUST distinguish PASS, FAIL, BLOCKED, UNKNOWN, NOT_RUN, UNSUPPORTED, and ERROR. |
| AA-REQ-POL-003 | P0 | A mandatory critical check in any non-PASS state MUST prevent a clean assurance conclusion unless an explicit exception rule applies. |
| AA-REQ-POL-004 | P0 | Exceptions MUST be scoped, justified, visible, attributable, time-bounded where appropriate, and auditable. |
| AA-REQ-POL-005 | P0 | Policies MUST be versioned and deterministic for equivalent validated inputs. |
| AA-REQ-POL-006 | P0 | Aggregates MUST NOT hide individual critical findings or convert missing evidence into success. |
| AA-REQ-POL-007 | P1 | Every decision MUST explain the rules applied and the evidence that affected the outcome. |

### 5.6 Security, trust, and execution

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-SEC-001 | P0 | Project content, checker output, worker output, and external provider responses MUST be treated as untrusted input until validated. |
| AA-REQ-SEC-002 | P0 | Filesystem operations MUST enforce an explicit root boundary and a documented symlink policy. |
| AA-REQ-SEC-003 | P0 | Path checks MUST account for platform-specific path semantics and race conditions to the extent supported by the declared platform. |
| AA-REQ-SEC-004 | P0 | Process execution MUST use explicit argument boundaries and MUST NOT invoke a shell implicitly. |
| AA-REQ-SEC-005 | P0 | Child processes MUST receive only the declared environment and permissions required by the check. |
| AA-REQ-SEC-006 | P0 | Network operations MUST be disabled by default and separately authorized, scoped, and reported. |
| AA-REQ-SEC-007 | P0 | Secrets MUST NOT be copied into reports, checker output, evidence, or diagnostic logs without an explicit safe-handling rule. |
| AA-REQ-SEC-008 | P0 | Time, output, file-count, and other applicable resource limits MUST be enforced or explicitly reported as unenforceable on a platform. |
| AA-REQ-SEC-009 | P0 | The product MUST NOT describe process timeout or environment reduction as an operating-system sandbox. |
| AA-REQ-SEC-010 | P1 | Security checks MUST disclose false-positive review, coverage limits, and unsupported constructs. |

### 5.7 Reporting and usability

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-RPT-001 | P0 | Reports MUST show the overall decision, policy version, and the scope to which the decision applies. |
| AA-REQ-RPT-002 | P0 | Reports MUST present critical findings and mandatory non-PASS checks before non-critical summaries. |
| AA-REQ-RPT-003 | P0 | Reports MUST distinguish checked, not checked, excluded, blocked, and unsupported areas. |
| AA-REQ-RPT-004 | P0 | Reports MUST expose material evidence limitations, environment limitations, stale baselines, and policy exceptions. |
| AA-REQ-RPT-005 | P1 | Reports SHOULD provide actionable next steps tied to findings without claiming that a suggested remediation is guaranteed. |
| AA-REQ-RPT-006 | P1 | Human-readable and machine-readable reports MUST derive from the same validated decision record. |

### 5.8 Extensibility and integrations

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-EXT-001 | P0 | The core MUST remain usable without an AI service or external provider. |
| AA-REQ-EXT-002 | P0 | External providers MUST be opt-in, explicitly identified, and isolated behind versioned contracts. |
| AA-REQ-EXT-003 | P0 | External output MUST be validated and MUST NOT independently authorize a critical PASS. |
| AA-REQ-EXT-004 | P1 | Integrations MUST declare identity, version, supported scope, permissions, network needs, and limitations. |
| AA-REQ-EXT-005 | P1 | Missing optional providers MUST produce explicit unsupported or unavailable results, not silent success. |

### 5.9 Compatibility, performance, and release

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-CMP-001 | P0 | Compatibility claims MUST be tied to an explicit tested runtime, OS, architecture, and toolchain matrix. |
| AA-REQ-CMP-002 | P0 | Untested combinations MUST be labelled unverified rather than assumed compatible. |
| AA-REQ-CMP-003 | P1 | Performance measurements MUST record workload, environment, repetitions, and relevant uncertainty. |
| AA-REQ-REL-001 | P0 | Release artifacts MUST be built from a declared source revision and explicit file manifest. |
| AA-REQ-REL-002 | P0 | Release validation MUST reject unintended files, path escapes, and manifest mismatches. |
| AA-REQ-REL-003 | P0 | Release provenance and hashes MUST identify the exact artifact and source revision they cover. |
| AA-REQ-REL-004 | P0 | Publication MUST require an explicit release gate and MUST NOT occur as an implicit side effect of a normal commit. |

## 6. Non-functional requirements

| ID | Priority | Requirement |
|---|---|---|
| AA-REQ-NFR-001 | P0 | The core MUST remain installable and usable without runtime third-party dependencies unless a later ADR justifies an exception. |
| AA-REQ-NFR-002 | P0 | The CLI MUST preserve stable existing command behavior and exit-code meanings unless a documented compatibility change is accepted. |
| AA-REQ-NFR-003 | P0 | Persistent schemas MUST be versioned and support explicit handling of unknown major versions. |
| AA-REQ-NFR-004 | P0 | Failure handling MUST be fail-closed for assurance decisions while retaining enough diagnostic detail to explain the failure. |
| AA-REQ-NFR-005 | P1 | Routine local checks SHOULD provide useful feedback without requiring a full deep-audit profile. |
| AA-REQ-NFR-006 | P1 | Every component MUST document resource bounds, error behavior, and supported platforms. |
| AA-REQ-NFR-007 | P1 | Tests MUST be deterministic by default and MUST not mutate real user projects. |

## 7. Compatibility constraints

The accepted 1.1.0 baseline includes the CLI, existing evidence and migration workflow, JSON schemas, worker contracts, and the `qyrenith_engine` modules for bounded source analysis, filesystem boundary inspection, and process execution.

Advanced Assurance MUST be additive unless a breaking change is explicitly accepted. Existing state files and schemas MUST NOT be silently reinterpreted. The current engine is useful infrastructure, but it is not a complete checker runtime, evidence store, or OS sandbox.

The current supported Python baseline is Python 3.11+. The declared CI coverage for 1.1.0 is Python 3.11–3.14 on Ubuntu, Windows, and macOS. This is the current verified matrix, not an automatic promise for future releases.

## 8. Requirement lifecycle

Each requirement moves through:

`PROPOSED → ACCEPTED → IMPLEMENTED → VERIFIED → DEFERRED`

- **PROPOSED:** written and awaiting architecture/owner review.
- **ACCEPTED:** stable scope and acceptance method approved.
- **IMPLEMENTED:** code or documentation exists.
- **VERIFIED:** required evidence meets the acceptance method.
- **DEFERRED:** intentionally postponed with impact, reason, and review trigger.

A requirement is not VERIFIED because a related file exists or a command exited zero.

## 9. AA-01 acceptance

AA-01 is accepted only when:

1. Every P0 requirement has an unambiguous acceptance method.
2. The architecture assigns ownership for every in-scope responsibility.
3. The threat model covers project content, checkers, external integrations, filesystem access, process execution, evidence, and release operations.
4. Trust boundaries and explicit authorization points are identified.
5. Compatibility and migration constraints against 1.1.0 are explicit.
6. Architecture decisions record the reason for each foundational choice.
7. No critical unresolved trust-boundary ambiguity remains.
8. The acceptance matrix links every requirement to an architecture section and a future verification method.

## 10. Change control

Changes to P0 requirements require:
- a short problem statement;
- affected requirement IDs;
- security and compatibility impact;
- alternatives considered;
- an updated acceptance method;
- a numbered architecture decision when the change affects a foundational boundary.

No requirement may be weakened merely to make an implementation or test pass.

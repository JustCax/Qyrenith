# Advanced Assurance Architecture

**Document ID:** QYR-AA-ARCH  
**Revision:** 1  
**Status:** Proposed for AA-01 acceptance  
**Baseline:** Qyrenith 1.1.0, commit `647398246bc6bc15fdf8fe6038af1bec35710806`

## 1. Architectural objective

Advanced Assurance extends Qyrenith from a collection of project-specific workflow gates into a project-neutral verification system with an explicit pipeline:

`DISCOVER → MODEL → PLAN → AUTHORIZE → EXECUTE → VALIDATE EVIDENCE → EVALUATE POLICY → REPORT`

The architecture must make it impossible for a worker or checker to collapse these stages into a self-reported success claim.

The design is logical and responsibility-oriented. It does not require every responsibility to become a separate Python package. Physical module boundaries are chosen only after the contracts and dependency directions are accepted.

## 2. System boundary

### 2.1 Qyrenith owns

- project identity and bounded discovery;
- project facts and source references;
- verification plans and authorization state;
- checker registration and contract validation;
- execution lifecycle and resource controls;
- evidence acceptance, integrity, and provenance;
- deterministic policy evaluation;
- final decision and report generation;
- compatibility and release gates.

### 2.2 External systems may provide

- compilers, interpreters, build systems, test runners, linters, static analyzers, scanners, package registries, and documentation sources;
- specialist domain tools and project-local workers;
- AI-assisted task decomposition or explanatory suggestions.

External systems remain providers of observations or work results. Their outputs are untrusted inputs to Qyrenith's validation and policy stages. They do not own final decision authority.

### 2.3 Not part of the trusted core

- project source code;
- project configuration that has not passed validation;
- checker output before schema and provenance validation;
- worker or agent statements;
- external API responses;
- downloaded advisory data before provider and freshness checks.

## 3. Logical components

### 3.1 Project Discovery

Responsibilities:
- identify the root and declared scope;
- enumerate files and configuration within explicit bounds;
- classify observed project markers;
- identify languages, build systems, runtimes, tests, and entry points where supported;
- record exclusions, symlink decisions, incomplete scans, and uncertainty.

Discovery is read-only. It must not import modules, execute project scripts, resolve dependencies through a network, or infer semantic guarantees from filenames alone.

### 3.2 Project Model

Responsibilities:
- normalize discovery observations into a versioned project representation;
- retain source references for each fact;
- distinguish observed, inferred, user-declared, provider-reported, and verified facts;
- record confidence and limitations without turning confidence into proof;
- expose a stable input to plan generation.

The model is a snapshot for a declared project scope. Any refresh creates a new model revision or snapshot; it must not silently rewrite the evidence behind an earlier plan.

### 3.3 Verification Planner

Responsibilities:
- select checks from a profile and policy;
- validate prerequisites and capability compatibility;
- calculate exact check inputs and permission requirements;
- declare expected outputs, resource bounds, and state mapping;
- identify checks that are mandatory, optional, excluded, unsupported, or blocked.

A plan is inspectable and immutable once authorized. A change to project identity, policy, checker versions, or relevant inputs invalidates or supersedes the affected plan.

### 3.4 Authorization Gate

Responsibilities:
- compare planned side effects and permissions with user-granted scope;
- distinguish read-only discovery from code execution, file mutation, network access, package installation, and publication;
- record who/what authorized the operation and for which exact plan;
- reject new or broader operations not present in the authorized plan.

Authorization is not inferred from a previous unrelated run or from the existence of a configuration entry.

### 3.5 Checker Registry and Contract Validator

Responsibilities:
- identify native and external checkers by stable identity and version;
- validate checker manifests and capability claims;
- validate declared inputs, outputs, permissions, and side effects;
- reject unsupported protocol versions and malformed declarations;
- expose an inspectable checker capability inventory.

Discovery of a checker does not grant permission to execute it.

### 3.6 Checker Runtime

Responsibilities:
- manage checker lifecycle;
- provide only declared inputs and a reduced environment;
- enforce available timeout, output, file, and concurrency limits;
- collect stdout, stderr, exit state, artifacts, and termination reason;
- normalize execution failures without changing their meaning.

The runtime MUST NOT be described as a sandbox unless a separately validated OS-level isolation mechanism exists. A child process still inherits whatever OS authority is available to it.

### 3.7 Evidence Validator and Store

Responsibilities:
- validate evidence structure and references;
- bind evidence to project, plan, checker, policy, inputs, and environment;
- compute or verify content digests;
- commit evidence atomically;
- preserve supersession and correction history;
- expose evidence references to reports and policy evaluation.

Evidence is append-only at the logical level. A correction creates a replacement or superseding record; it does not silently rewrite a previously accepted observation.

### 3.8 Policy Evaluator

Responsibilities:
- read a versioned policy and validated evidence only;
- apply deterministic rules;
- preserve per-check states and severity;
- apply mandatory gates and explicit exceptions;
- emit a decision record with traceable rule identifiers.

The evaluator cannot execute checks, modify source evidence, or promote an unsupported/unknown state into PASS.

### 3.9 Reporting Layer

Responsibilities:
- render the same decision record as human-readable and machine-readable output;
- show scope, profile, policy version, findings, evidence, exclusions, exceptions, and limitations;
- distinguish project defects from infrastructure failures;
- provide next-step guidance linked to findings.

Reports do not contain hidden decision logic. All decisive semantics are in the policy evaluator and versioned policy.

### 3.10 Provider and Adapter Boundary

Responsibilities:
- adapt external tools to the checker contract;
- declare provider identity, version, scope, permissions, network use, and result provenance;
- validate external responses before they enter evidence validation;
- make absence, failure, and stale data visible.

An adapter is not trusted merely because it is installed or listed in a manifest.

### 3.11 Reproducibility and Cross-Environment Assurance

This is a cross-cutting assurance responsibility, not a second execution engine. It reuses the declared execution authority and binds each reproducibility claim to:
- a named reproducibility class and exact scope;
- a versioned manifest of source, inputs, tools, dependencies, policy, configuration, environment, and execution controls;
- an explicit comparator or oracle;
- raw and normalized output identities, with the normalization policy version;
- uncontrolled or unavailable inputs;
- independently identified attempts and environment-matrix cells where required.

A repeat in the same mutable workspace is not independent reproduction. High-assurance claims require a clean workspace and a separately identified execution attempt. Unknown inputs remain visible; a manifest digest does not prove that the recorded environment was truthful. Replaying side-effecting operations requires fresh authorization.

The detailed manifest schema, reproducibility classes, comparison rules, and acceptance corpus must be integrated with the Qyrenith reproducible-verification specification before implementation. This responsibility must not create a parallel runner or duplicate the existing reproducible lab.

### 3.12 Release Assurance

Responsibilities:
- own the explicit release file manifest and source-revision binding;
- qualify exact ZIP/TAR/sdist/wheel contents and reject unintended files or path escapes;
- bind artifact digests and provenance to the exact source revision and build context;
- enforce the explicit publication gate and prevent ordinary development events from publishing;
- preserve release evidence and disclose signing/provenance capabilities and limitations.

Release Assurance is a named architecture owner, not an assumption that the current release builder already satisfies every future AA requirement.

## 4. Dependency direction

The logical dependency direction is:

`Discovery → Project Model → Planner → Authorization → Runtime → Evidence Validator → Policy Evaluator → Reporter`

Cross-cutting contracts and schemas may be imported by multiple components. They must not import the CLI or depend on report formatting.

Rules:

1. The CLI coordinates components but contains no duplicate policy semantics.
2. Checkers do not import the policy evaluator or write final decisions.
3. The evidence validator does not trust checker-provided status fields without applying its own contract rules.
4. The policy evaluator does not execute processes or inspect arbitrary project files.
5. The reporter does not recalculate the decision.
6. External adapters cannot bypass authorization, evidence validation, or mandatory gates.
7. Lower-level modules do not depend on higher-level orchestration modules.

## 5. Data flow

### 5.1 Discovery flow

1. Resolve and validate the user-declared project root.
2. Apply bounded read-only traversal.
3. Record observations with source references and exclusions.
4. Normalize observations into a project-model snapshot.
5. Calculate a stable identity for the declared scope and relevant inputs.

### 5.2 Planning flow

1. Load a versioned profile and policy.
2. Read the project-model snapshot and checker capability inventory.
3. Resolve prerequisites and compatibility.
4. Generate explicit check entries, including unsupported or blocked items.
5. Validate resource bounds and permission declarations.
6. Display the plan and required authorizations.

### 5.3 Execution flow

1. Bind the exact approved plan to an authorization record.
2. Validate that project identity and relevant inputs have not changed.
3. Prepare a reduced execution context.
4. Invoke only the planned checker through the runtime.
5. Capture bounded execution observations.
6. Normalize timeout, crash, cancellation, output overflow, and provider errors.
7. Submit observations to evidence validation.

### 5.4 Evidence and decision flow

1. Validate schema and required provenance.
2. Verify scoped object references and applicable digests.
3. Commit a complete evidence record atomically.
4. Evaluate the versioned policy against validated evidence.
5. Produce a decision record with rule and evidence references.
6. Render human and machine reports from that record.

## 6. Core data objects

The following logical objects require versioned schemas:

| Object | Purpose | Authority |
|---|---|---|
| Project Snapshot | Scoped, source-linked project facts | Discovery/model |
| Checker Manifest | Identity, scope, inputs, outputs, permissions | Registry validator |
| Verification Plan | Exact check list, prerequisites, limits, and expected evidence | Planner |
| Authorization Record | Approved plan and allowed side effects | Authorization gate |
| Execution Record | Observed process lifecycle and bounded outputs | Runtime |
| Evidence Record | Validated observation with provenance and integrity metadata | Evidence validator |
| Policy | Versioned rules and mandatory gates | Policy owner |
| Decision Record | Deterministic result of evaluating evidence under policy | Policy evaluator |
| Report | Human/machine presentation of one decision record | Reporter |
| Profile Definition | Exact check inventory, exclusions, permissions, limits, and result mapping | Profile / policy owner |
| Exception Record | Scope, rationale, approver, affected rule, expiry/review, and audit reference | Policy owner |
| Reproducibility Manifest | Identity-defining inputs, tools, dependencies, policy, environment, and uncontrolled inputs | Reproducibility assurance |
| Reproducibility Result | Class, scope, comparator, outcome, mismatches, and evidence references | Reproducibility assurance |
| Release Manifest | Exact source revision and intended artifact inventory | Release Assurance |

No object may carry authority beyond its declared owner. In particular, checker output is not a Decision Record.

## 7. Result-state and decision semantics

### 7.1 Per-check outcome states

The seven-state vocabulary applies to an individual planned check after its execution observation and evidence validation have been interpreted:

- **PASS:** the declared condition was checked and validated evidence satisfies its rule.
- **FAIL:** validated evidence demonstrates that the declared condition was not satisfied.
- **BLOCKED:** a prerequisite, permission, or environment condition prevented the check from completing.
- **UNKNOWN:** evidence is insufficient, stale, or contradictory.
- **NOT_RUN:** the check was not executed.
- **UNSUPPORTED:** no applicable implementation exists for the declared scope.
- **ERROR:** the checker or verification infrastructure malfunctioned.

A process exit code is only an execution observation. For example, exit code zero cannot produce PASS when its evidence is malformed, incomplete, stale, or outside the authorized scope.

### 7.2 Aggregate assurance decision

The project-level assurance decision is a separate, policy-derived object. It MUST retain links to every relevant per-check state, mandatory gate, exception, and evidence item. It MUST NOT be represented by copying one check's state or by an undocumented numeric score.

The exact aggregate decision vocabulary and its mapping to legacy workflow states remain an AA-01 owner decision. Until accepted, documents and implementations MUST NOT invent or imply a canonical aggregate-state enum. A mandatory critical check in any non-PASS state prevents a clean assurance conclusion unless an explicit, valid exception applies.

### 7.3 Reproducibility outcomes

Reproducibility status is also separate from check outcomes and aggregate assurance decisions. The proposed vocabulary is:

- **REPRODUCED:** the declared class and scope were independently repeated and the declared comparator/oracle passed.
- **PARTIALLY_REPRODUCED:** some dimensions matched, but mandatory scope remains incomplete.
- **NOT_REPRODUCED:** the repeat completed and the equivalence contract failed.
- **INCONCLUSIVE:** missing oracle, uncontrolled input, nondeterminism, or insufficient observation prevents a conclusion.
- **BLOCKED:** policy, trust, isolation, integrity, or prerequisite conditions prevented the repeat.
- **UNSUPPORTED:** the requested reproducibility class or environment cannot be evaluated.

These proposed outcomes do not replace the seven per-check states. Their final naming and compatibility mapping require owner approval.

## 8. Trust boundaries

| Boundary | Untrusted side | Required control |
|---|---|---|
| Project filesystem | Source, config, symlinks, generated files | Root confinement, bounded read-only discovery, path validation |
| Checker boundary | Native checker and external checker output | Versioned contract, reduced inputs, bounded execution, schema validation |
| Process boundary | Project-controlled command and child process | Explicit authorization, argv execution, limits, reduced environment; disclose lack of OS sandbox |
| Provider boundary | Network responses and remote databases | Explicit network permission, identity, freshness, schema and integrity checks |
| Evidence boundary | Runtime observations before acceptance | Independent validator, atomic write, provenance binding |
| Policy boundary | Validated evidence and versioned policy | Deterministic evaluation; no checker write access |
| Release boundary | Build outputs and repository contents | Explicit manifest, exact source revision, artifact validation, explicit publication authorization |

## 9. Persistence and lifecycle

- Persistent schemas are versioned.
- A run is bound to exact project, plan, checker, and policy identities.
- Completed evidence is logically immutable.
- Partial records are either safely recoverable as incomplete or rejected; they must never appear as complete.
- Baseline replacement is explicit and creates a new identity.
- Retention and redaction policies are documented before sensitive evidence is persisted.
- Temporary files are scoped and cleaned safely without deleting unrelated user data.

The storage backend is not selected by this document. It must meet the consistency, integrity, portability, and recovery requirements before adoption.

## 10. Compatibility and migration

The 1.1.0 baseline remains the compatibility anchor.

- Existing public CLI commands and exit codes remain stable by default.
- Existing `.qyrenith/` state and schemas are not reinterpreted without version-aware migration.
- New capabilities are introduced additively where feasible.
- Schema migrations must be deterministic, testable, and recoverable.
- A failed migration must preserve the original data.
- New runtime capabilities must not silently alter the behavior of legacy migration flows.
- Support claims remain tied to the tested platform matrix.

## 11. Performance model

Profiles separate common low-cost checks from expensive verification. Every checker declares resource needs and limits. The planner reports estimated categories, not false precision.

Initial categories:
- **Low:** bounded local metadata and structural checks.
- **Moderate:** parser-based analysis, unit tests, or bounded dependency inspection.
- **High:** builds, broader test suites, security review, compatibility matrices.
- **Very high:** controlled resilience testing and broad cross-environment qualification.

A profile may not conceal mandatory checks merely because they are expensive.

## 12. Failure behavior

Every component must return a typed result with:
- stable failure code;
- affected scope;
- phase and component identity;
- whether the operation started or completed;
- available evidence references;
- retryability where known;
- cleanup and recovery state;
- explicit limitation or uncertainty.

Failure in one optional check does not erase successful independent checks. It also cannot be silently ignored when a selected policy marks that check mandatory.

## 13. Physical module layout

The initial logical architecture does not prescribe a rigid package layout. Before AA-02 implementation, the repository must receive a module ownership map and dependency graph.

Candidate boundaries may include project discovery/model, planning, checker contracts/runtime, evidence, policy, reporting, and integrations. Names and file placement remain subject to the accepted ADRs and a minimal migration plan from the 1.1.0 code.

The existing `qyrenith_engine.analysis`, `boundary`, and `execution` modules are reusable Qyrenith-native foundations. They do not by themselves satisfy the full logical responsibilities above.

## 14. Architecture acceptance checklist

- [ ] Every logical component has one accountable owner.
- [ ] Dependency direction is acyclic and documented.
- [ ] Checker execution and policy authority are separate.
- [ ] Evidence acceptance is separate from checker output creation.
- [ ] Side effects are covered by authorization.
- [ ] All trust boundaries have controls and residual risks.
- [ ] Persistent objects have versioning and lifecycle rules.
- [ ] Existing 1.1.0 behavior and state migration are addressed.
- [ ] No unsupported sandbox, semantic, or security claim is made.
- [ ] Each P0 requirement maps to a component, threat/control where relevant, and an ID-level acceptance case.
- [ ] Per-check outcomes, aggregate assurance decisions, requirement lifecycle states, and reproducibility outcomes are distinct.
- [ ] Reproducibility claims bind a named class, scope, manifest, comparator/oracle, and uncontrolled-input list.
- [ ] Profile and exception records have explicit ownership and versioned contracts.
- [ ] Release Assurance owns manifest, artifact qualification, provenance, and publication gates.

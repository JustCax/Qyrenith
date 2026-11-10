# Advanced Assurance Test Strategy

**Document ID:** QYR-AA-TEST  
**Revision:** 1  
**Status:** Proposed for AA-01 acceptance

## 1. Purpose

This strategy defines how Advanced Assurance itself will be verified. It is not a substitute for the test plan attached to each checker. A passing test suite supports only the behavior and fixtures it actually exercises.

## 2. Test layers

### 2.1 Unit tests

Verify isolated deterministic behavior:
- path normalization and scope rules;
- schema validation;
- project fact normalization;
- plan selection and prerequisites;
- state mapping;
- evidence identity and digest handling;
- policy rule evaluation;
- report serialization and redaction.

Unit tests must avoid network access and uncontrolled process execution.

### 2.2 Contract tests

Verify protocol boundaries:
- valid and invalid checker manifests;
- supported and unsupported protocol versions;
- required and optional input fields;
- malformed, extra, missing, or oversized output;
- identity/version mismatches;
- declared versus observed side effects;
- provider-specific metadata and limitation fields.

Each checker implementation must pass the same relevant contract suite.

### 2.3 Integration tests

Verify the full pipeline:
`DISCOVER → MODEL → PLAN → AUTHORIZE → EXECUTE → VALIDATE → EVALUATE → REPORT`

Tests must assert exact project scope, plan identity, evidence references, decision state, report content, and absence of undeclared side effects.

### 2.4 Adversarial tests

Include:
- path traversal, drive-relative paths, UNC paths, case collisions, and symlink escapes;
- malformed and deeply nested data;
- shell metacharacters and argument-boundary attacks;
- malicious or deceptive worker output;
- secret canaries in environment and process output;
- output floods, hung children, cancellation, and forced termination;
- stale input and baseline changes;
- evidence tampering and interrupted writes;
- contradictory providers;
- attempts to bypass mandatory policy gates.

Adversarial fixtures must be synthetic and must not target real user projects or external systems.

### 2.5 Failure and recovery tests

Inject process crashes, permission errors, disk-full simulations where feasible, interrupted writes, unavailable tools, timeouts, partial artifacts, and platform-specific process behavior.

Every injected failure must have an expected state, preserved evidence, cleanup behavior, and recovery assertion.

### 2.6 Compatibility tests

Test each declared combination, not just the newest runtime. The existing 1.1.0 CI baseline is Python 3.11–3.14 on Ubuntu, Windows, and macOS. A capability may narrow or expand its support only with explicit evidence.

Existing CLI commands, exit codes, persisted state, and schema compatibility require regression tests.

### 2.7 Release tests

Verify:
- explicit public file manifest;
- exact artifact content;
- ZIP/TAR/sdist/wheel consistency;
- version metadata consistency;
- source commit and artifact digest linkage;
- no unintended internal, temporary, or sensitive files;
- no publication from ordinary pushes.

### 2.8 Reproducibility and cross-environment tests

For every reproducibility claim, tests must:
- name the reproducibility class, scope, comparator/oracle, and expected equivalence;
- verify that a versioned manifest records identity-defining inputs and explicitly lists uncontrolled inputs;
- distinguish raw artifact digests from normalized comparison digests;
- verify that normalization is versioned and does not erase security- or behavior-relevant differences;
- use a clean workspace and separately identified attempt when independent reproduction is required;
- report each environment-matrix cell independently and never generalize from an untested cell;
- reject REPRODUCED when required evidence, an oracle, or a mandatory scope dimension is missing;
- require fresh exact-scope authorization before replaying side-effecting operations.

These are future acceptance requirements; this strategy does not claim that the reproducibility engine or its tests already exist.

## 3. Determinism and test isolation

- Unit and policy tests use fixed inputs.
- Generated-input tests record their seed and bounds.
- Time-dependent behavior uses injected clocks where feasible.
- Network tests use controlled local fixtures or mocks, never live public services by default.
- Process tests use purpose-built fixtures with explicit time and output limits.
- Test output must not contain secrets or depend on a developer's home-directory contents.
- Tests must not delete, reset, or mutate user repositories.

## 4. Quality measures

Track at minimum:
- requirement-to-test traceability;
- test pass/fail/skip/error state;
- supported OS/runtime combinations;
- adversarial scenario coverage;
- flaky test rate and root cause;
- false-positive review outcomes for finding-producing checkers;
- resource use and runtime for declared profiles;
- regression findings introduced and resolved.

Coverage percentages may be useful diagnostics, but they are not proof of correctness and cannot replace requirement-level acceptance.

## 5. Evidence format for a phase

Every phase report records:
- exact source commit;
- exact command and relevant arguments;
- Python/runtime/tool versions;
- OS and architecture;
- test case identifiers;
- exit state and summary;
- logs or artifact references with digests where appropriate;
- skipped and unsupported tests;
- failures and disposition;
- known limitations;
- for reproducibility claims: class, scope, manifest revision/digest, comparator/oracle version, uncontrolled inputs, independent-attempt identity, environment-matrix cell, and raw/normalized artifact digests.

A phase is not VERIFIED while a mandatory test is skipped, unsupported, or unresolved unless an approved exception explicitly addresses that test.

## 6. AA-01 status

AA-01 establishes the test strategy and traceability rules only. It does not claim that AA-02 through AA-12 tests, runtime components, or checker capabilities already exist.

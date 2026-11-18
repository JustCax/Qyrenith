# Advanced Assurance Threat Model

**Document ID:** QYR-AA-TM  
**Revision:** 1  
**Status:** Proposed for AA-01 acceptance  
**Baseline:** Qyrenith 1.1.0, commit `647398246bc6bc15fdf8fe6038af1bec35710806`

## 1. Purpose and scope

This threat model identifies assets, actors, trust boundaries, attack surfaces, plausible failure and abuse scenarios, required controls, and residual risks for Advanced Assurance.

It is a design artifact, not a claim that every mitigation is already implemented. Each threat must be mapped to a requirement, a component owner, and a verification method before the component is accepted.

## 2. Security objectives

1. Project-controlled content cannot silently expand the inspected filesystem scope.
2. No project-controlled code executes during default discovery.
3. Execution occurs only when the exact planned operation is authorized.
4. A checker, worker, provider, or AI agent cannot self-approve evidence or final success.
5. Evidence cannot appear complete after malformed, interrupted, or partial collection.
6. A stale or contradictory result cannot silently satisfy a mandatory gate.
7. Secrets and unrelated user data are not disclosed through outputs or persistent records.
8. Resource exhaustion and process failure produce bounded, explicit outcomes.
9. Reports make uncertainty and coverage limitations visible.
10. Release artifacts correspond to the declared source revision and intended manifest.

## 3. System assumptions

- The user controls the host operating system, account permissions, installed toolchains, and repository access.
- The project being inspected may be malicious, compromised, malformed, or simply inconsistent.
- Native code is maintained under the Qyrenith repository's development and release controls.
- External providers and workers may be incorrect, compromised, unavailable, or adversarial.
- A normal child process is not isolated from the operating system merely because Qyrenith uses timeouts, argument arrays, output caps, or a reduced environment.
- Local administrators and malware with equal or higher OS privileges are outside the guarantees of application-level path checks.
- Cryptographic hashes establish consistency relative to a trusted digest; they do not prove that the original observation was honest.
- The initial core remains standard-library-first. Optional integrations can expand the attack surface and require separate approval.

## 4. Assets

| Asset ID | Asset | Security property |
|---|---|---|
| AA-AS-01 | User project source and configuration | Confidentiality, integrity, scope isolation |
| AA-AS-02 | Files outside the declared project root | Must not be read or modified without authorization |
| AA-AS-03 | Credentials and environment secrets | Confidentiality and non-disclosure |
| AA-AS-04 | Verification plan and authorization record | Integrity, binding to exact scope |
| AA-AS-05 | Checker binaries/scripts and manifests | Identity, provenance, integrity |
| AA-AS-06 | Evidence records and source references | Integrity, completeness, provenance |
| AA-AS-07 | Baselines and prior decision records | Identity, freshness, non-repudiation within declared threat model |
| AA-AS-08 | Policy rules and exception records | Integrity, versioning, auditability |
| AA-AS-09 | Process resources and host stability | Availability and bounded consumption |
| AA-AS-10 | Release artifacts and publication credentials | Integrity, confidentiality, authorized release |
| AA-AS-11 | Diagnostic logs and reports | Confidentiality, integrity, accurate disclosure |

## 5. Actors

| Actor | Trust classification | Capabilities / concern |
|---|---|---|
| Maintainer | Authorized operator | Defines policies, approves releases, manages configuration |
| Project user | Authorized scope owner | Selects project, profile, and permitted operations |
| Project content | Untrusted | Can contain malformed files, symlinks, scripts, and deceptive metadata |
| Native checker | Trusted code, limited authority | Can contain defects; must not own final decision |
| External checker/worker | Untrusted until validated | May emit malformed, deceptive, excessive, or malicious output |
| AI agent | Untrusted advisory executor | May hallucinate, omit failures, or propose unsafe actions |
| External provider | Untrusted data source | May return stale, incorrect, malformed, or unavailable data |
| Hostile local process | Potential attacker | May race filesystem operations or inspect shared resources |
| Compromised dependency/toolchain | Supply-chain threat | May alter execution or build results |
| Network attacker | External threat | May influence traffic when optional network access is enabled |

## 6. Trust-boundary map

```text
       User / Maintainer
              |
       declared scope + approval
              v
  +---------------------------+
  | Qyrenith Control Plane    |
  | discovery / planning      |
  | authorization / policy    |
  | evidence validation       |
  +---------------------------+
      |                  |
      | read-only        | explicit, bounded execution
      v                  v
+-------------+    +---------------------+
| Project     |    | Checker / Worker    |
| filesystem  |    | external process    |
+-------------+    +---------------------+
                           |
                           | untrusted result
                           v
                  +----------------------+
                  | Evidence Validator   |
                  +----------------------+
                           |
                           v
                  +----------------------+
                  | Policy Evaluator     |
                  +----------------------+
                           |
                           v
                  +----------------------+
                  | Decision / Report    |
                  +----------------------+
```

External network providers are a separate boundary. A response from a remote service enters the same untrusted-input and evidence-validation path as a local worker response.

## 7. Threat register

Risk ratings are qualitative and provisional. They must be revisited with implementation evidence. "High" does not imply a confirmed vulnerability; it indicates an unacceptable consequence if the control fails.

| ID | Threat scenario | Impact | Required controls | Verification |
|---|---|---|---|---|
| AA-THR-001 | A symlink or path traversal entry escapes the project root during discovery. | Exposure of unrelated files or access outside declared scope. | Canonical root policy, path-component validation, bounded traversal, explicit symlink handling, platform-specific tests. | In-root/out-of-root symlink tests, traversal corpus, Windows path cases. |
| AA-THR-002 | A filesystem path changes between validation and use. | TOCTOU escape or unintended file access. | Minimize check/use gaps, use safe directory-relative APIs where available, revalidate immediately before sensitive operations, document residual OS races. | Controlled race tests where platform permits; code review of every path-open boundary. |
| AA-THR-003 | Malformed source/config causes parser crash, excessive memory, or unbounded traversal. | Denial of service or false/incomplete report. | File/entry/depth/size limits, bounded parser inputs, typed parse errors, incomplete status. | Oversized, deeply nested, malformed, and high-entry fixtures. |
| AA-THR-004 | Project-controlled code executes during discovery. | Arbitrary code execution and data access. | Default discovery must be read-only and non-executing; execution requires plan and explicit authorization. | Instrumented project fixtures proving discovery makes no process/import calls. |
| AA-THR-005 | A checker invokes a shell or constructs an unsafe command. | Command injection or unintended command execution. | Explicit argv contract, no implicit shell, validated executable and arguments, execution authorization. | Metacharacter fixtures and process-spawn assertions. |
| AA-THR-006 | A child process inherits secrets or ambient permissions. | Credential disclosure or unauthorized actions. | Environment allowlist, explicit working directory, no secret forwarding by default, documented permissions. | Sentinel-secret tests, environment inspection fixture. |
| AA-THR-007 | A worker emits oversized output or never terminates. | Resource exhaustion or hung run. | Timeout and output limits, process termination/reaping, explicit truncation/termination state. | Flood-output and hung-child tests across supported OS. |
| AA-THR-008 | A worker fabricates a successful result or embeds untrusted instructions in output. | False PASS or unsafe follow-on action. | Treat output as data, strict schema validation, no authority to select final status, safe display/escaping. | Malformed and deceptive protocol fixtures; policy bypass tests. |
| AA-THR-009 | A checker produces a valid-looking but incomplete evidence record. | False assurance. | Independent evidence validation, required-field policy, completeness flags, validated source references. | Missing-field, truncated-content, mismatched-plan tests. |
| AA-THR-010 | Evidence is partially written, duplicated, or changed after acceptance. | Corrupted audit history or misleading reports. | Atomic writes, stable IDs, digests, immutable logical records, supersession semantics. | Interruption tests at write boundaries; tamper detection tests. |
| AA-THR-011 | A stale baseline or previous result is reused for changed inputs. | Outdated checks incorrectly satisfy current policy. | Bind evidence to project/model/input hashes and checker/policy versions; validate freshness. | Mutate relevant input after baseline and require invalidation. |
| AA-THR-012 | Policy aggregation hides a critical failure or maps UNKNOWN to PASS. | Unsafe assurance decision. | Separate deterministic evaluator, explicit states, mandatory gates, property tests. | Exhaustive state-combination and critical-gate tests. |
| AA-THR-013 | An exception is broad, permanent, or unaudited. | Policy bypass. | Scope, reason, owner, expiry/review, affected requirement, and audit event. | Exception schema and expiry/over-scope tests. |
| AA-THR-014 | Provider data is stale, unavailable, or manipulated. | Incorrect dependency/security conclusion. | Provider identity, retrieval time, data version, freshness rule, failure state, provenance. | Stale/malformed/unavailable provider simulations. |
| AA-THR-015 | Network access occurs without user awareness. | Data exfiltration, untrusted download, nondeterminism. | Network disabled by default; per-check permission and endpoint scope; visible reporting. | Network-deny integration tests and allowed-endpoint tests. |
| AA-THR-016 | Reports or logs reveal secrets from paths, environment, or tool output. | Credential or personal-data exposure. | Redaction rules, output sanitization, controlled diagnostic verbosity, bounded retention. | Sentinel-secret fixtures for stdout, stderr, paths, and environment. |
| AA-THR-017 | Optional provider/checker failure is silently skipped. | Misleading coverage and false clean result. | Explicit UNSUPPORTED/BLOCKED/ERROR/NOT_RUN states; profile coverage reporting. | Remove provider and assert visible non-PASS status. |
| AA-THR-018 | A compromised build tool or dependency falsifies results. | Supply-chain compromise and false assurance. | Record tool identity/version/hash where feasible; distinguish provider trust; support independent corroboration; disclose limits. | Tool identity mismatch and provider disagreement fixtures. |
| AA-THR-019 | Cancellation or crash leaves stale locks, temporary files, or a valid-looking partial run. | Data corruption or blocked future runs. | Transaction lifecycle, atomic records, safe cleanup, recoverable incomplete state. | Kill/cancel at each lifecycle stage and verify recovery. |
| AA-THR-020 | Release manifest or package build includes unintended internal files or secrets. | Information disclosure or compromised package. | Explicit public manifest, content tests, artifact inventory, hash and source revision binding. | ZIP/TAR/sdist/wheel content tests and secret canary scan. |
| AA-THR-021 | Publication is triggered by an ordinary commit or unreviewed tag. | Unauthorized release. | Separate publish workflow, protected environment, explicit release event, trusted publishing, release gate. | Workflow event tests and permissions review. |
| AA-THR-022 | Cross-platform path, process, or permission semantics differ from assumptions. | Escape, hanging process, or false compatibility. | Explicit platform matrix, capability detection, platform-specific fallback states. | Windows/macOS/Linux adversarial regression matrix. |
| AA-THR-023 | AI-generated guidance is treated as a verified remediation or fact. | Unsafe changes or false claims. | AI remains advisory; every proposed change requires normal approval and verification. | Tests proving agent text cannot change decision state. |
| AA-THR-024 | Resource limits are configured but not enforceable on a platform. | Overstated containment. | Capability report and explicit unsupported enforcement state; never claim unsupported limits. | Platform-specific capability tests and documentation review. |

| AA-THR-025 | A reproducibility claim omits a mutable or uncontrolled input such as a dependency source, toolchain, environment variable, clock, cache, or remote service. | False claim that a result can be repeated or compared. | Versioned reproducibility manifest; explicit uncontrolled-input inventory; invalidate affected evidence when identity-defining inputs change. | Change one hidden input at a time and assert that the manifest or reproducibility verdict changes or becomes INCONCLUSIVE. |
| AA-THR-026 | Output normalization removes a security- or behavior-relevant difference. | A materially different or unsafe result is reported as equivalent. | Versioned comparator/normalizer; preserve raw digests; prohibit normalization of security-relevant modes, signatures, permissions, or behavior. | Adversarial fixtures differing only in protected fields must not compare equivalent. |
| AA-THR-027 | A replay repeats a destructive or externally visible side effect using stale authorization. | Data loss, duplicate deployment/publication, or unintended external action. | Fresh exact-scope authorization for side-effecting replay; default-deny destructive operations. | Replayed mutation/publication fixture must be blocked without a new authorization record. |

## 8. Mitigation priorities

### P0 before checker execution is expanded

- Exact plan-to-authorization binding.
- Read-only default discovery.
- Root confinement and symlink policy.
- Explicit process invocation and bounded output/time.
- Evidence schema and completeness validation.
- Deterministic result-state semantics.
- Checker/policy authority separation.
- Secret-safe logs and reports.
- Atomic evidence lifecycle.
- No implicit network or publication.
- Reproducibility claims bind identity-defining inputs and list uncontrolled inputs.
- Comparators and normalization policies are versioned; raw evidence remains available.
- Side-effecting replay requires fresh exact-scope authorization.

### P1 before broad integrations

- Provider freshness and identity.
- Compatibility-specific enforcement tests.
- Cross-platform process lifecycle tests.
- Explicit exception governance.
- Supply-chain metadata and provenance.
- Controlled fault-injection and recovery harness.

## 9. Residual risks and honest limitations

- Application-level path validation cannot fully defend against a hostile process with equal OS privileges or every filesystem race.
- A bounded process runner is not a security sandbox.
- Static analysis cannot prove absence of vulnerabilities or behavioral defects.
- A digest proves consistency relative to a trusted digest, not truthfulness of the original observation.
- A provider with valid data format can still be factually wrong.
- A tool version string can be spoofed unless independently authenticated.
- A local administrator, kernel compromise, or malicious host toolchain is outside the core guarantee.
- Time and memory limits may be unavailable or approximate on some platforms.
- No assurance profile can prove that a project is defect-free.
- Exact reproduction may be impossible when external services, hardware, mutable dependencies, or host state cannot be preserved; the correct outcome is an explicit limitation or INCONCLUSIVE, not an inferred match.

These limitations must be visible in product documentation and in affected reports where relevant.

## 10. Threat-model maintenance

Each new execution capability, provider, persistence mechanism, or release operation triggers a threat-model review.

A threat may be closed only when:
1. the control exists;
2. the control has a reproducible test or justified verification method;
3. the test evidence is recorded;
4. residual limitations are documented.

Threat closure is not inferred from documentation alone.

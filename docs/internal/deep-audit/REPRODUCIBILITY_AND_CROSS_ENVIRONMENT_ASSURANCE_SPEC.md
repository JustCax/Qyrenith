# Reproducibility and Cross-Environment Assurance Specification — Qyrenith 1.2.0

**Status:** PROPOSED SPECIFICATION EXTENSION — OWNER REVIEW REQUIRED  
**Extends:** `REPRODUCIBLE_VERIFICATION_LAB_SPEC.md`, `EVIDENCE_AND_CONFIDENCE_MODEL.md`, dynamic audit, fuzz/property testing and integrated reporting.

## 1. Objective

Make reproducibility a cross-cutting assurance capability for builds, tests, diagnostics, benchmarks, runtime scenarios, fuzzing, repairs, migrations, reports and release artifacts. Preserve enough trustworthy context to repeat a check, compare results, explain differences and state when exact reproduction is impossible.

A seed or command line alone is not a guarantee. Source, toolchain, dependency, environment, policy, data, oracle, network, time and execution inputs must be captured or declared uncontrolled.

## 2. Reproducibility classes

1. **Bit-for-bit:** independently produced outputs have identical bytes under a defined normalization policy.
2. **Artifact-structural:** permitted volatile fields differ, but normalized structure and invariant fields match.
3. **Functional:** outputs satisfy the same explicit functional contract/oracle.
4. **Behavioral:** observable state transitions and declared invariants match within a specified scenario and observation boundary.
5. **Diagnostic:** the same scoped inputs, analyzer/rule versions and policy produce equivalent normalized findings, coverage and verdicts.
6. **Experimental:** a benchmark can be repeated with the same workload/protocol; results include variance and uncertainty.
7. **Procedural:** repair/migration steps, approvals, tool versions and evidence lineage can be reconstructed and audited.

A run may satisfy one class and fail another. Never use the unqualified word "reproducible" without naming class and scope.

## 3. Reproducibility manifest

Bind, where applicable: project/revision/snapshot; exact input/fixture/corpus digests; lockfiles and resolved dependency identities/sources; OS/distribution/kernel/architecture; compiler/interpreter/runtime/SDK/build/analyzer/plugin versions and digests; exact argv/executable/working directory/shell behavior; effective environment policy and digest (never secret values); timezone/locale/clock policy; random seeds/generator/scheduler settings; network policy/remotes/cache state; resource limits/isolation level; config/feature flags/policy/rule/schema versions; oracle/comparator/normalization; timestamps, exit status, bounded output and artifact digests.

Unknown or unrecorded inputs are listed as uncontrolled. A manifest digest proves manifest byte identity, not that the environment matched it.

## 4. Execution and capture

The existing reproducible lab remains the execution authority; this document adds assurance semantics, not a second runner:
1. Capture and verify read-only baseline.
2. Resolve dependencies from pinned/verified sources or declare network resolution uncontrolled.
3. Provision environment and record measured isolation.
4. Execute exact command with bounded resources and captured effective environment.
5. Collect raw bounded observations, normalized outputs, artifact digests and provenance.
6. Repeat in a clean workspace or independent environment when required.
7. Compare with declared comparator; retain raw and normalized identities.
8. Emit scoped verdict with mismatches and uncontrolled inputs.

A repeat in the same mutable workspace is not independent reproduction. High-assurance claims require a clean workspace and separately identified runner/trust boundary.

## 5. Determinism controls

Detect/control timestamps, timezone, locale, filesystem/archive ordering, modes, paths, random seeds, mutable remote dependencies, environment inheritance, parallel scheduling, clocks, caches, generated files, encodings and line endings. Controls are domain-aware: never normalize away security-relevant modes, signatures or behavior. Version and digest every normalization policy.

## 6. Cross-environment verification

A matrix is an explicit set of dimensions, not universal portability. Dimensions may include OS/distribution, CPU architecture, language/compiler/runtime/SDK, dependencies, framework/game/loader/API version, locale/timezone/filesystem/network and isolation profile.

Every cell reports NOT_RUN, PASS, FAIL, BLOCKED, UNSUPPORTED or INCONCLUSIVE with exact evidence. Do not infer all Windows versions from one runner or ARM support from x86-64. Distinguish expected platform-specific output, semantic equivalence, byte identity, incompatibility, setup failure and insufficient evidence.

## 7. Status vocabulary

- **REPRODUCED:** declared class/scope independently repeated and comparator/oracle passed.
- **PARTIALLY_REPRODUCED:** some dimensions matched but mandatory scope remains incomplete.
- **NOT_REPRODUCED:** repeat completed and equivalence contract failed.
- **INCONCLUSIVE:** missing oracle, uncontrolled input, nondeterminism or insufficient observation.
- **BLOCKED:** policy/trust/isolation/integrity/prerequisite prevented run.
- **UNSUPPORTED:** requested class/environment cannot be evaluated.

These statuses supplement, not replace, BUILD_VERIFIED, TEST_VERIFIED, BEHAVIOR_VERIFIED or AUDIT_VERIFIED.

## 8. Artifact comparison

Retain raw hashes and normalized comparison digests separately. Record comparator and normalization version. Bit-level claims use cryptographic digests; functional/behavioral claims use explicit oracles; benchmark claims use repeated samples, workload, machine profile, variance and measurement protocol. Never compare materially different environments as equivalent.

## 9. Security and privacy

Never persist secrets in manifests. Use controlled references and non-revealing metadata. Treat external artifacts as untrusted until integrity/provenance policy validates them. Replay must not repeat destructive actions, deployments, publication or other irreversible side effects without fresh exact-scope approval. Existing RVL isolation levels remain authoritative; a copy is not a sandbox.

## 10. Domain acceptance

- Builds: clean rebuilds, pinned dependencies, builder identity, byte vs semantic equivalence.
- Tests: replay seeds, inventory, fixture digests, order and oracle; detect flakes and selection drift.
- Fuzzing: bind seed, generator, constraints, corpus and shrinker; replay minimized counterexamples.
- Diagnostics: repeat analyzer/rule/config; compare finding IDs, coverage and suppressions.
- Runtime: replay scenario, clock/network policy, state fixtures and observation boundary.
- Repair: reproduce failure, apply reviewed patch in disposable workspace, rerun original and full baseline checks.
- Migration: bind source snapshot, knowledge, route, worker digest, policy, target and per-target validation.
- Optimization: reproduce workload/baseline; use repeated measurements and uncertainty.
- Reports: identical normalized evidence/schema/policy produces stable machine-readable output.

## 11. Requirements

- **RCA-01:** name reproducibility class, scope, comparator/oracle and evidence IDs.
- **RCA-02:** persist versioned manifest with source, toolchain, dependencies, config, environment and execution identity.
- **RCA-03:** enumerate uncontrolled inputs; never assume unknown inputs are stable.
- **RCA-04:** independent reproduction uses clean workspace and separately identified execution attempt.
- **RCA-05:** report each cross-environment matrix cell independently.
- **RCA-06:** retain raw and normalized artifact digests separately.
- **RCA-07:** normalization is explicit/versioned and cannot erase security/behavior differences.
- **RCA-08:** fuzz replay binds seed, generator, constraints, corpus and shrinker versions.
- **RCA-09:** benchmark reproducibility includes workload, machine profile, repeated samples, variance and protocol.
- **RCA-10:** invalidate evidence when identity-defining input, tool, policy, dependency or environment changes.
- **RCA-11:** side-effecting replay requires fresh exact-scope authorization.
- **RCA-12:** incomplete runs cannot produce REPRODUCED.

## 12. Acceptance tests

Test manifest invalidation; timestamp variation; safe normalization; changed generator version; hidden environment/mutable network inputs; OS/architecture non-generalization; benchmark variance/noise; clean-workspace identity; secret redaction; destructive replay blocking; missing oracle/resource exhaustion/unsupported isolation non-pass; independent verification of comparator decisions.

## 13. Non-claims

Reproducibility is scoped, not universal. Vanished services, inaccessible dependencies, unavailable hardware and unrecorded external state may be unreproducible. Deterministic reports do not prove evidence truth; matching digests do not authenticate producers; reproducible builds do not prove safe source.

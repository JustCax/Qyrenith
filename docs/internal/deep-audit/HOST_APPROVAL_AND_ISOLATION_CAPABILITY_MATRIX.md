# Host Approval and Isolation Capability Matrix — Qyrenith 1.2.0

**Status:** SOURCE-RECONCILED CAPABILITY BASELINE — NOT PLATFORM-QUALIFIED  
**Assessment date:** 2026-11-16  
**Target branch:** `feature/1.2.0-universal-migration-core`  
**Authority:** Accepted AA-D3 and ADR-AA-002; RVL remains the sole isolation/replay authority.

## 1. Purpose

This matrix separates implemented source mechanisms, declared capabilities, actual host enforcement, and platform verification. A source-level code path is not a platform support claim. No platform is considered qualified for side-effecting migration or repair execution until the required host boundary is independently tested on the exact release candidate.

## 2. Capability vocabulary

- **SOURCE_PRESENT:** relevant implementation exists in the inspected branch.
- **DECLARATIVE_ONLY:** metadata or a caller-supplied profile names a capability but does not enforce it.
- **NOT_IMPLEMENTED:** no enforcing implementation was identified.
- **NOT_TESTED:** no exact-revision platform evidence is available.
- **NOT_QUALIFIED:** the complete required contract has not passed independent qualification.
- **PROPOSE_ONLY:** planning/inspection may occur, but side-effecting execution must remain disabled.

These labels are not per-check outcomes and do not imply PASS.

## 3. Cross-platform capability matrix

| Capability | Linux | macOS | Windows | Android / Termux |
|---|---|---|---|---|
| Interactive challenge prompt | SOURCE_PRESENT | SOURCE_PRESENT | SOURCE_PRESENT | SOURCE_PRESENT |
| Independent human identity authentication | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| Approval scope binding and one-time nonce | SOURCE_PRESENT | SOURCE_PRESENT | SOURCE_PRESENT | SOURCE_PRESENT |
| Independent trust anchor for approval signing | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| Trust-store owner-only permissions | POSIX permission path present; NOT_TESTED | POSIX permission path present; NOT_TESTED | Windows protected owner/SYSTEM ACL enforcement SOURCE_PRESENT; NOT_TESTED | POSIX permission path expected; NOT_TESTED |
| Snapshot descriptor-relative traversal | POSIX implementation present; NOT_TESTED | POSIX implementation present; NOT_TESTED | Handle-relative/reparse-point-safe path NOT_IMPLEMENTED | POSIX path expected; NOT_TESTED |
| Race-safe workspace traversal | NOT_QUALIFIED | NOT_QUALIFIED | NOT_QUALIFIED | NOT_QUALIFIED |
| Bounded subprocess execution | SOURCE_PRESENT; not a sandbox | SOURCE_PRESENT; not a sandbox | SOURCE_PRESENT; not a sandbox | SOURCE_PRESENT; not a sandbox |
| Process-tree containment | POSIX process-group termination path present; NOT_TESTED | POSIX process-group termination path present; NOT_TESTED | Windows Job Object descendant containment and 64-process cap SOURCE_PRESENT; NOT_TESTED | POSIX process-group path expected; NOT_TESTED |
| Filesystem isolation | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| Network isolation | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| Secret isolation | Reduced child environment is present; OS boundary NOT_IMPLEMENTED | Same | Same | Same |
| Memory / CPU / process hard quotas | NOT_IMPLEMENTED as a complete host boundary | NOT_IMPLEMENTED as a complete host boundary | NOT_IMPLEMENTED as a complete host boundary | NOT_IMPLEMENTED as a complete host boundary |
| Controlled worker conformance runner | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| Independently collected qualification evidence | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| Side-effecting migration/repair execution | PROPOSE_ONLY | PROPOSE_ONLY | PROPOSE_ONLY | PROPOSE_ONLY |

The Android column is an implementation-path expectation only. It is not a compatibility or security claim for Termux, Android storage providers, or device-specific kernels.

## 4. Approval contract boundary

The current HostApproval flow provides an interactive terminal challenge, HMAC-protected exact-scope records, owner trust-store ID/generation binding, expiry revalidation after operator input, and one-time nonce consumption at the migration step boundary.

The following limitations remain:

1. The recorded local principal is derived from `getpass.getuser()`; this is attribution, not independent authentication.
2. The HMAC key is local to the trust store and is not an independent identity or hardware trust anchor.
3. The lower-level authorization constructor still accepts caller-supplied attribution and timestamps.
4. The step-boundary API is not a complete worker executor and does not yet prove that every side-effect path requires the approval.
5. A caller-declared sandbox profile identifier/digest binds a declaration only; it does not establish enforcement.

Until the missing identity and execution-path contracts are implemented, approval records cannot authorize production worker/repair execution.

## 5. Worker qualification boundary

A manifest, assessment, or qualification record is not proof that a conformance suite ran. Qualification must be bound to the exact worker implementation digest, API contract, dependencies, support tuple, conformance-suite version, raw test results, execution environment, runner identity, reviewer/authority, and expiry/revocation state.

The current branch does not contain a controlled qualification runner that independently collects and authenticates these results. Worker execution remains unavailable for migration/repair side effects.

## 6. Required implementation and verification slices

1. Add a platform-authentication provider interface with explicit authenticated, unavailable, expired, and rejected outcomes. Unsupported platforms must fail closed.
2. Bind approvals to an authenticated principal and a host trust anchor; do not treat local username or caller strings as proof.
3. Make approval mandatory at the central side-effect dispatcher, not only at helper APIs.
4. Verify the source-implemented Windows owner/SYSTEM trust-store ACLs; implement handle/reparse-point-safe traversal.
5. Verify the source-implemented Windows Job Object descendant containment and 64-process cap; define and verify equivalent process-tree behavior on POSIX platforms.
6. Introduce a host-enforced RVL isolation provider contract for filesystem, network, environment, secrets, CPU, memory, process count, timeout, and output.
7. Implement controlled worker conformance execution with independently collected, digest-bound raw evidence.
8. Verify the Windows Job Object process-tree containment and 64-process cap on supported Windows hosts; add adversarial tests for replay, expiry, principal substitution, trust revocation, TOCTOU, child-process escape, network access, filesystem escape, resource exhaustion, crash recovery, and concurrent access.
9. Run the same exact revision across supported Windows, macOS, Linux, and Android/Termux cells where support is claimed. Unsupported cells remain explicit.
10. Retain exact commit, host/kernel, Python/runtime, filesystem, command, test IDs, raw results, and evidence digests.

## 7. Release rule

Until all mandatory approval, qualification, and host-isolation gates are implemented and independently verified, migration-worker and QDAS repair side effects remain **PROPOSE_ONLY / BLOCKED** on every platform. A workspace copy, reduced environment, timeout, process group, approval prompt, HMAC record, or declared profile is not by itself an OS sandbox or authenticated human approval.

## 8. Related documents

- `IMPLEMENTATION_READINESS_GATE.md`
- `PHASE_1_SIX_WORKSTREAM_SOURCE_AUDIT_2026-11-16.md`
- `QYRENITH_1_2_0_IMPLEMENTATION_AND_ACCEPTANCE_PLAN.md`
- `REPRODUCIBLE_VERIFICATION_LAB_SPEC.md`
- `ADR-AA-002-explicit-side-effect-authorization.md`

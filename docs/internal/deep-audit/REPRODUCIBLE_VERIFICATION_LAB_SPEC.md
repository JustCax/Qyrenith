# Reproducible Verification Lab Specification

## 1. Objective

Provide controlled, repeatable execution environments for builds, tests, analyzers, fuzzers, behavioral checks, and QDAS repair validation.

## 2. Lab identity

A lab run MUST bind project revision and snapshot digest, OS/architecture, runtime and tool versions, exact command argv, working directory, selected environment variables or environment fingerprint, dependency lock state, network policy, resource limits, start/end timestamps, and output digests.

## 3. Isolation levels

Report isolation as a concrete level, never as a generic "sandbox":
- L0: process bounds only;
- L1: dedicated temporary workspace;
- L2: restricted environment and filesystem scope;
- L3: OS-enforced process/filesystem/network isolation;
- L4: disposable VM/container boundary with measured policy;
- L5: independently provisioned ephemeral environment with retained provenance.

A copied directory is L1 at most. Do not claim L3+ without verifying the OS-enforced boundary. The lab must expose unsupported isolation features rather than silently downgrade.

## 4. Execution controls

All commands use argument arrays, no implicit shell, bounded stdin/stdout/stderr, timeout, process-tree termination where supported, controlled environment, working-directory validation, and explicit network/install policy. The timeout budget begins before any potentially blocking input transfer. Output-limit breach is a distinct terminal outcome and must terminate promptly.

## 5. Repeatability

Support baseline capture, clean reruns, exact command replay, artifact digesting, and comparison of normalized results. If dependency resolution is not locked or network state cannot be reproduced, disclose this and lower the repeatability claim.

## 6. QDAS integration

QDAS uses the lab for isolated repair and post-repair validation. The lab returns execution facts; QDAS owns diagnosis, approval, regression comparison, and final verdict. Lab records are evidence inputs, not final success claims.

## 7. Failure behavior

Return explicit statuses for timeout, output limit, resource limit, spawn failure, unsupported isolation, environment drift, cancellation, and command failure. No failure may be normalized to a successful empty result.

## 8. Acceptance tests

Include workers that never read stdin, flood either output stream, spawn children, change working directory, attempt path escape, alter files during snapshotting, exceed memory/time budgets, and observe environment leakage. Test Windows newline behavior and POSIX process-group behavior independently.

## 9. Non-claims

The lab does not guarantee hermeticity unless every relevant input is pinned and isolation is measured. A process timeout is not a security sandbox.

# Phase 1 Safety Review — Six-Workstream Source Audit

**Review date:** 2026-11-16  
**Target branch:** `feature/1.2.0-universal-migration-core`  
**Review scope:** Trust Store, Host Approval, Worker Qualification, Process Execution, Workspace Materialization, and Migration Authorization  
**Review method:** Read-only source inspection of the branch head and related tests/specification  
**Execution status:** Static source review only. No Python tests, platform tests, CI, or adversarial runtime tests were executed.

## Executive result

The six-workstream source review is complete. It confirms useful integrity, freshness, scope-binding, bounded-I/O, and snapshot-copy foundations. It does **not** establish a secure migration execution boundary. The current implementation remains a planning, trust-recording, approval-recording, and workspace-preparation foundation; it is not yet a safely executable migration platform.

**Phase 1 remains OPEN and is still a hard blocker.** No workstream is marked TEST_VERIFIED or independently verified by this review.

## 1. Owner Trust Store

**Follow-up source change (2026-11-16):** `trust_store.py` now applies and reads back a protected Windows DACL for the trust-store directory, data file, key file, and lock file when the lock is acquired. The ACL is restricted to the current user SID and SYSTEM, requires the current user to own the path, rejects unexpected ACE principals, and blocks inherited permissions. A Windows-only regression test now exercises the lock-file ACL path as well. This is source-level implementation only; it has not been executed on Windows and does not close the remaining handle-relative/reparse-point race, same-user threat, or host identity limitations.
 — `qyrenith_engine/trust_store.py`

### Observed foundations

- Stores exact-digest TRUST/REVOKE decisions in an append-only event sequence.
- Canonical JSON and a local HMAC detect accidental or unauthorized edits that do not also replace the local key.
- Revalidates persisted sequence numbers, unique event IDs, event structure, and non-decreasing review timestamps per exact subject.
- Uses an inter-process lock, reload-under-lock, expected-generation checks for nonce consumption, atomic replacement, and POSIX file/directory permission hardening.
- Rejects symlink/reparse-point store entries and Git-worktree placement at the checked directory boundary.
- Bounds store size and event count.

### Findings and limits

- The HMAC key is stored beside the store. This is local integrity protection, not an independent trust anchor, publisher identity, remote attestation, or protection against a malicious process running as the same OS user.
- Windows handling confines the default store beneath the user profile and rejects observed reparse points. A follow-up now applies and verifies a protected owner/SYSTEM DACL for the trust-store directory, data file and key file; the Windows-only regression test has not been run. Handle-relative/reparse-point-safe traversal and same-user isolation remain unresolved.
- The path checks and subsequent path-based reads/writes are not a complete handle-relative defense against concurrent replacement. The current code must not be described as race-safe against a hostile local process.
- POSIX ownership/mode checks are materially stronger than the Windows checks; cross-platform equivalence is not established.
- The lock serializes cooperating processes. It is not a boundary against a malicious same-user process that can alter the files or key.

### Required closure evidence

- Windows owner/SYSTEM-only ACL verification now covers the trust-store directory, data file, key file and lock path. Handle-relative/reparse-point-safe filesystem operations remain open; the ACL helper's path-based application/readback is not a substitute for handle-relative identity binding.
- Handle-based file identity checks and race-focused tests on each supported platform.
- Cross-process contention, crash-during-replacement, tamper, revocation, expiry, and recovery tests on the same revision.
- Explicitly retain the documented same-OS-user threat-model limitation unless a stronger protected service/key boundary is introduced.

## 2. Host Approval — `qyrenith_engine/approval.py`

### Observed foundations

- Requires interactive TTY input/output and an exact challenge string.
- Binds approval to an exact action type and canonical scope digest.
- Signs the approval record with the owner trust-store key and records store identity/generation.
- Rechecks request expiry after the challenge response, rejects a trust-store generation change during the prompt, and supports single-use nonce consumption.
- Nonce consumption is performed through the trust store's locked expected-generation append path, preventing ordinary concurrent replay.

### Findings and limits

- `approved_by` and `host_principal` are both populated from `getpass.getuser()`. This is local account attribution, not independent authentication of the human at the keyboard.
- A TTY and a typed challenge prove an interactive input path, not operator identity, authorization authority, MFA, or resistance to a compromised terminal/session.
- The HMAC proves that the local store key signed the record; it does not prove who controlled the terminal.
- The lower-level `authorize_migration()` API still accepts caller-supplied attribution and timestamps. Authenticated step-boundary approval is a separate integration and must not be inferred from the existence of an authorization object.
- The expiry regression test exists but has not been executed on the current head.

### Required closure evidence

- A host-controlled authenticated approval channel with an explicit principal/authority model and independently verifiable approval evidence.
- Tests for wrong principal, unauthorized principal, terminal/session substitution, expiry while waiting, trust-store mutation, concurrent replay, and crash/retry behavior.
- API-level proof that every executable side effect requires the authenticated step-boundary approval path, not merely a caller-created authorization record.

## 3. Worker Manifest and Qualification — `qyrenith_engine/migration/worker.py`

### Observed foundations

- Strict, bounded, canonical manifest and qualification records.
- Worker identity/version and implementation digest are pinned; exact transition scopes, capabilities, permissions, and resource declarations are validated.
- Qualification records are bound to a manifest digest and include conformance suite/result digests, PASS status, test count, reviewer attribution, and validity interval.
- Registry resolution distinguishes missing, incompatible, unqualified, stale, untrusted, and qualified records.
- A local trust policy can allowlist an exact qualification-record digest.

### Findings and limits

- The qualification fields are declarations supplied in a record. The module does not run the conformance suite, collect its output, verify the result artifact, or independently authenticate the qualifier.
- Trusting a qualification digest means accepting that exact record; it does not establish that the declared suite actually ran or that the result belongs to the claimed worker binary.
- The implementation digest is not checked against an installed/launched executable because there is no controlled worker installation or execution boundary here.
- `QUALIFIED` is therefore an eligibility/record-match status only. It is not proof of execution, behavior, or safe isolation.

### Required closure evidence

- A controlled runner that fetches or accepts a pinned worker artifact, verifies its digest, executes the complete technology-specific and shared baseline conformance profile in an isolated environment, and captures raw results.
- Independently verifiable qualification attestations bound to the exact worker artifact, suite version/digest, runner identity/version, environment profile, raw evidence digest, and result.
- Negative/adversarial qualification tests, revocation/expiry tests, and independent reproduction of published qualification evidence.

## 4. Bounded Process Execution — `qyrenith_engine/execution.py`

### Observed foundations

- Uses argument arrays with `shell=False`, a bounded timeout, bounded input, an allowlisted default environment, and bounded output capture.
- Worker stdout and stderr share one aggregate capture budget; output overflow is reported as BLOCKED and triggers termination.
- POSIX launches a new session and attempts process-group termination.
- The module explicitly states that this is not an OS sandbox.

### Findings and limits

- Windows execution now creates a suspended child, assigns it to a Job Object before resuming it, sets kill-on-close, and caps the job at 64 active processes. A Windows-only descendant-cleanup regression test was added but has not been run. This is process-tree containment, not filesystem/network isolation. The resume path has been changed to use the documented Toolhelp thread-enumeration APIs plus `OpenThread`/`ResumeThread`: the child is created suspended, assigned to the Job Object, and its single initial thread is located and resumed only after exact process-owner matching. The implementation fails closed unless exactly one initial thread is found and its prior suspend count is exactly one. Job termination checks and reports `TerminateJobObject` failure while still attempting the kill-on-close handle cleanup. A platform-independent mocked termination-failure regression test and a Windows-only descendant-cleanup test are present; neither has been executed.
- POSIX process-group cleanup is process cleanup, not filesystem, network, secret, syscall, identity, or resource isolation.
- The default environment is reduced, but callers can opt into inherited environment. Neither mode is an OS security boundary.
- Timeout/output limits do not constrain CPU, memory, disk, network, child process creation, filesystem access, or access to credentials available to the invoking account.
- Existing bounded-execution tests and recent output-budget regression coverage have not been executed against this head.

### Required closure evidence

- Verify Windows Job Object assignment-before-resume, kill-on-close, the 64-process cap, and descendant cleanup on Windows; retain fail-closed behavior if assignment or resume fails.
- POSIX and Windows isolation providers with explicit filesystem, network, process, resource, environment, and secret-access policies.
- Adversarial child/descendant, pipe inheritance, timeout, output flood, environment leakage, resource exhaustion, and cleanup tests on supported platforms.
- A capability contract that distinguishes process cleanup from actual sandbox enforcement.

## 5. Snapshot and Workspace Materialization — `qyrenith_engine/migration/snapshot.py`, `workspace.py`, `preparation.py`

### Observed foundations

- Snapshot verification and workspace materialization are separate from worker execution.
- Workspace creation copies regular files represented by the source snapshot, checks file identity/content while copying, rejects snapshots containing symbolic links, and verifies the resulting baseline.
- The POSIX source-file opener uses descriptor-relative traversal with `O_NOFOLLOW` where supported.
- Multi-target preparation checks the source before and after creation, validates each workspace, and attempts rollback of partially created batches.

### Findings and limits

- The Windows/portable path-based fallback cannot provide the same parent-component no-follow guarantee as the POSIX descriptor-relative path. A last-moment directory check narrows but does not close replacement races.
- The workspace parent is a trusted caller-supplied location; the API does not turn it into a protected security boundary.
- A copied workspace is an independent filesystem tree, not a process/container/VM sandbox. It does not isolate network, credentials, host files, or OS privileges.
- The current preparation API creates workspace copies and descriptors. It does not execute transformations, run target builds/tests, or provide a complete durable workspace lifecycle/recovery manager.
- Rollback is best-effort cleanup, not a crash-consistent transaction across filesystem state and external evidence stores.

### Required closure evidence

- Windows handle/reparse-point-safe traversal and copy, with race-focused tests; define and test the supported filesystem semantics.
- Owner-controlled workspace-parent validation, collision/race handling, durable lifecycle states, crash recovery, and cleanup evidence.
- Tests for source replacement, nested reparse points, destination substitution, partial copy, disk-full, process crash, rollback failure, and concurrent preparation.
- Keep the explicit distinction between workspace separation and OS execution isolation.

## 6. Migration Authorization and Step Boundary — `qyrenith_engine/migration/authorization.py`

### Observed foundations

- Authorization binds a route-plan digest, worker-assessment digest, policy digest, approval attribution, expiry, and per-transition grants.
- Creation and validation recheck knowledge freshness, worker qualification, exact manifest/qualification digests, permission subsets, resource ceilings, worker policy, and qualification expiry.
- The owner-trust wrapper requires exact catalog/worker digests to be trusted.
- Step-approval scope binds the authorization, route/transition, grant, workspace, snapshot, command digest, and caller-declared sandbox profile ID/digest.
- The step-boundary validator rechecks trust/authorization, verifies exact host-approval scope, and consumes the nonce before the intended boundary.

### Findings and limits

- `approved_by` and authorization timestamps in the base constructor are caller-supplied metadata. The authorization digest is an integrity checksum, not a signature or authenticated approval.
- Owner trust is an additional local decision gate, not proof of an authenticated human or independently qualified worker.
- Permission and resource grants are data contracts. They are not enforced by the OS in this module.
- A sandbox profile ID/digest in the approval scope proves only which profile was declared. It does not prove that a provider installed or enforced that profile.
- The step-boundary approval function is not itself a worker executor; no atomic handoff to a verified executor or post-execution evidence lifecycle is established here.

### Required closure evidence

- Require authenticated host approval for every side effect and make unsafe lower-level paths inaccessible to the execution layer.
- Bind grants to an independently qualified executable and an enforced sandbox-provider attestation, not caller-declared profile metadata alone.
- Enforce permission/resource limits at the execution boundary and revalidate immediately before each side effect.
- Add end-to-end tests for authorization substitution, stale/revoked trust, expired qualification, changed workspace/snapshot/command, profile substitution, replay, partial execution, and recovery.

## Cross-workstream disposition

| Workstream | Source-level foundation | Material blocker | Review disposition |
|---|---|---|---|
| 1. Trust Store | Exact-digest local trust, HMAC, append/locking/freshness checks; protected Windows owner/SYSTEM DACL source implementation for directory/data/key/lock paths | Windows handle/reparse-point safety, independent trust-anchor and same-user threat limitations; ACL test not run | **AUDITED — OPEN** |
| 2. Host Approval | Interactive exact-scope approval and nonce lifecycle | No independent authenticated human identity | **AUDITED — OPEN** |
| 3. Worker Qualification | Pinned declarations and qualification-record matching | No controlled runner or independently collected conformance evidence | **AUDITED — OPEN** |
| 4. Process Execution | Bounded subprocess, POSIX process-group cleanup, Windows Job Object descendant containment and 64-process cap (source only) | No filesystem/network/environment/secret/resource sandbox; Windows test not run | **AUDITED — OPEN** |
| 5. Workspace | Snapshot-pinned copies and partial rollback | Windows path race and no execution isolation/lifecycle guarantee | **AUDITED — OPEN** |
| 6. Authorization | Plan/policy/worker/scope-bound grant validation | Caller attribution and declarative limits are not authenticated/enforced | **AUDITED — OPEN** |

### Phase 1 exit decision

**NOT PASSED.** The six source reviews are complete, but the safety exit criteria are not. The following remain release-blocking:

1. Authenticated human approval with an independently verifiable principal and authority.
2. Independently collected worker conformance evidence bound to the exact executable artifact.
3. Enforced OS-level filesystem/network/environment/resource/secret isolation; Windows process-tree containment is source-present but must be tested.
4. Verify Windows owner-only trust-store ACLs; implement handle/reparse-point-safe filesystem operations.
5. Crash-safe execution/workspace/evidence lifecycle and cross-store reconciliation.
6. Cross-platform adversarial tests and full regression evidence on the same revision.

No test status is upgraded by this report. All existing and newly added regression tests remain unexecuted on the reviewed head; GitHub Actions remain disabled by owner direction.

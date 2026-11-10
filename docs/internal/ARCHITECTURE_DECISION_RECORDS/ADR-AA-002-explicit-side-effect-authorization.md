# ADR-AA-002: Explicit, Scope-Bound Authorization for Side Effects

**Status:** RECONCILED PROPOSAL — OWNER ACCEPTANCE REQUIRED  
**Revision date:** 2026-11-10  
**Scope:** Discovery, planning, execution, providers, migration, repair, and release  
**Implementation status:** NOT STARTED

## Context

Qyrenith operations range from read-only metadata inspection to running project-controlled code, modifying files, installing tools, accessing credentials, using the network, or publishing artifacts. Treating all of these as generic verification conceals risk and user intent.

The existing architecture requires read-only discovery by default, explicit authorization for side effects, host-enforced execution boundaries, and the RVL L0–L5 isolation scale. The migration platform and QDAS repair path must remain propose-only until every required trust, approval, and isolation gate is enforceable.

## Proposed decision

Discovery is non-executing and read-only by default. Every side-effecting operation MUST be declared in a versioned plan and separately authorized for its exact scope, operation, target, and limits before execution.

At minimum, side-effect classes include:
- project-controlled process or script execution;
- filesystem creation, modification, or deletion;
- package, tool, or dependency installation;
- network access, remote retrieval, or protocol invocation;
- credential or secret access;
- migration, repair, or source transformation;
- artifact signing, publication, deployment, or release.

Authorization MUST bind:
- project identity and immutable snapshot/revision;
- plan and profile identity/digest;
- exact operation and target/resource scope;
- requested capabilities and permitted paths/processes/endpoints;
- required RVL isolation level and host capability evidence;
- resource, time, output, and concurrency bounds;
- approval identity, authority, timestamp, expiry, and revocation state.

A changed project snapshot, plan, target, operation, permission, or relevant provider identity invalidates the affected authorization and requires re-evaluation. A global allow-all switch, command-line confirmation flag, caller-provided identity string, or worker assertion is not authenticated human approval.

## Isolation and fail-closed behavior

RVL L0–L5 is the only canonical isolation scale. A requested level must be independently shown to be enforced by the host for the exact platform/runtime combination. Configuration declarations, directory copies, command allowlists, containers without measured controls, or provider self-reports do not prove a stronger boundary.

No silent downgrade is permitted. If the host cannot enforce the required boundary, the operation MUST remain `PROPOSE_ONLY` or return an explicit `BLOCKED`/`UNSUPPORTED` outcome. The system MUST NOT execute the operation under a weaker level and then report success.

## Network policy

Network access is disabled by default at every layer. The first 1.2.0 release MUST NOT require network-dependent mandatory checks. A later network-enabled provider requires a separate owner-approved threat model and explicit per-run approval, exact endpoint/operation allowlists, bounded I/O, timeout/response limits, provenance, secret/data-flow controls, and retained request/response metadata subject to redaction policy.

## Alternatives considered

1. **Implicit execution after discovery:** rejected; project scripts and metadata are untrusted.
2. **Global allow-all permission:** rejected; it removes operation-level scope and auditability.
3. **Always block all execution:** rejected as a permanent design; controlled execution remains useful when explicitly authorized and host-enforced.
4. **Treating a workspace copy as a sandbox:** rejected; a copy does not constrain processes, secrets, network, or host resources.

## Consequences

- Plans and authorization records become explicit, versioned artifacts.
- Human approval requires a trusted host channel; CLI flags alone cannot satisfy it.
- Provider and extension permissions are centrally evaluated and least-privileged.
- Unsupported host controls remain visible and block the affected operation.
- Network-enabled functionality remains outside the mandatory first-release path.
- Migration and repair execution remain disabled/propose-only until the complete safety gate is met.

## Acceptance criteria

- Default discovery causes no project-controlled process execution, network access, or project mutation.
- An undeclared operation cannot execute.
- Scope, snapshot, plan, or provider changes invalidate affected approval.
- Caller-supplied strings and CLI flags cannot impersonate authenticated approval.
- Required isolation is independently measured for every supported platform cell.
- Filesystem, process, environment, secret, network, and resource boundaries are adversarially tested.
- Missing host enforcement produces propose-only/BLOCKED/UNSUPPORTED behavior, never a silent downgrade.
- Network is denied by default and no network-dependent mandatory check is present in 1.2.0.

## Deferred

Exact host approval protocol, OS-specific isolation-provider matrix, permission schema, and final API/CLI surfaces remain to be specified and tested. This proposal does not authorize implementation or execution.

# ADR-AA-002: Explicit, Exact-Scope Authorization for Side Effects

**Status:** PROPOSED — reconciled with owner-approved AA-01 decision directions; ADR acceptance pending  
**Original proposal date:** 2026-11-04  
**Reconciliation date:** 2026-11-10  
**Scope:** Discovery, planning, process execution, filesystem mutation, providers, network, migration, repair, and release

## Context

Project inspection ranges from bounded local metadata reads to running project-controlled code, changing files, installing packages, accessing credentials, contacting remote services, invoking external providers, replaying mutations, or publishing artifacts. Treating these as ordinary verification hides their distinct risks.

Qyrenith's migration authorization, host approval, RVL isolation, and five-plane architecture separate permission from containment. Authorization is not proof that a host-enforced boundary exists.

## Decision proposal

Read-only, bounded, non-executing discovery is the default. Every side-effecting operation MUST be declared in a versioned plan and receive explicit authorization for its exact scope before execution.

The action taxonomy MUST distinguish at minimum:
- process execution, including project-controlled build/test scripts;
- filesystem writes, deletes, renames, and workspace mutation;
- package, tool, or dependency installation;
- network access and remote data retrieval;
- credential or secret access;
- external provider invocation where side effects are possible;
- deployment, publication, release, or other externally visible mutation;
- destructive or state-changing replay.

Authorization MUST bind to exact project identity/snapshot, plan digest/version, operation, target scope, requested capabilities, limits, and expiry/revocation context. A changed snapshot, plan, action, target, permission, or material limit requires re-evaluation and, where scope changed, a new authorization. Approval is not a blanket grant for later runs.

Authorization and isolation are separate gates:
- RVL L0–L5 is the only canonical isolation scale.
- Platform host-enforced capabilities must be discovered and independently qualified; declarations alone are not proof.
- No silent downgrade is permitted.
- If a required boundary is unavailable, side-effecting work remains `PROPOSE_ONLY` or returns `BLOCKED`/`UNSUPPORTED`; it must not execute under a weaker unannounced boundary.
- A workspace copy, CLI flag, caller-supplied string, or authorization record alone is not an OS sandbox or authenticated human approval.

Network policy is stricter:
- Network access is disabled by default at every layer.
- The first 1.2.0 release MUST NOT require network-dependent mandatory checks.
- Any later network provider requires a separate owner-approved threat model, explicit per-run approval, endpoint/operation allowlists, bounded I/O, provenance, and auditable data-flow records.
- Provider discovery/registration must not contact remote services unless separately authorized.

## Alternatives considered

1. Implicit execution after discovery — rejected because project-controlled scripts/providers are untrusted.
2. Global allow-all permission — rejected because it hides operation-specific scope.
3. Treat authorization as sandboxing — rejected because permission records do not enforce OS containment.
4. Always block all execution — rejected as a universal rule; bounded builds/tests may run only with exact approval and independently enforced isolation.
5. Network enabled by default — rejected because it introduces exfiltration, mutable inputs, and nondeterminism.

## Consequences

- Plans enumerate actions, capabilities, targets, and resource ceilings before execution.
- Approval must use a trusted host channel; caller flags or self-asserted strings do not count.
- Authorization is revalidated immediately before action.
- Isolation qualification and authorization must both pass.
- Denied, unavailable, stale, or insufficient permissions remain visible as non-PASS states.
- Extensions use central policy and RVL boundaries and cannot obtain ambient authority.
- Network-dependent optional functionality may remain unavailable offline; that is a disclosed support limitation, not a successful check.

## Verification requirements

- Default discovery performs no process execution, network access, credential access, or project mutation.
- A plan cannot execute an undeclared action or exceed its exact authorization.
- Changed snapshot, plan, action, target, or permission invalidates the prior grant as defined by the authorization contract.
- Missing host enforcement prevents side-effecting execution.
- No L0–L5 downgrade occurs silently.
- Network-denial tests prove no traffic occurs by default, including during extension discovery.
- Network use requires a fresh per-run grant, endpoint/operation allowlists, bounded I/O, and provenance.
- Destructive/external replay requires fresh exact-scope authorization.
- Publication cannot be triggered by an ordinary commit or unapproved tag.

## Related contracts

- `DEEP_AUDIT_MASTER_ARCHITECTURE.md`
- `AA01_OWNER_DECISION_RECORD.md`
- `MIGRATION_PLATFORM_INTEGRATION_SPEC.md`
- `REPRODUCIBLE_VERIFICATION_LAB_SPEC.md`
- `EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md`
- `SECURITY_AND_SUPPLY_CHAIN_AUDIT_SPEC.md`

This proposal does not authorize restoring GitHub Actions, publishing artifacts, or enabling network by default.

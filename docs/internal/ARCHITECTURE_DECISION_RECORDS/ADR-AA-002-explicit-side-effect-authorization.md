# ADR-AA-002: Explicit Authorization for Side Effects

**Status:** Proposed for AA-01 acceptance  
**Date:** 2026-11-04  
**Scope:** Discovery, planning, execution, network integrations, and release

## Context

Project inspection can range from reading local metadata to executing project-controlled build scripts, installing dependencies, contacting remote services, modifying files, or publishing artifacts. Treating all of these actions as ordinary "verification" hides material differences in risk and user intent.

## Decision

Read-only discovery is the default. Every side-effecting operation must be declared in the verification plan and separately authorized for the exact scope in which it will run.

Side effects are classified at minimum as:
- process execution of project-controlled code;
- filesystem mutation;
- package or tool installation;
- network access or remote data retrieval;
- credential use;
- release artifact publication.

Authorization is bound to project identity, plan identity, operation, and declared limits. A changed plan or broader permission requires new authorization. A previously granted permission is not a blanket grant for later runs.

## Alternatives considered

1. **Implicit execution after discovery:** rejected because project scripts may be untrusted.
2. **Global allow-all setting:** rejected because it hides operation-specific risk.
3. **Always block all execution:** rejected because controlled builds/tests are useful when explicitly requested and bounded.

## Consequences

- plans must declare permissions before execution;
- execution and publication workflows require visible approval;
- denied or unavailable permissions become explicit non-PASS outcomes;
- routine read-only discovery remains useful without execution.

## Verification

- default discovery tests assert no process execution, network access, or filesystem mutation;
- a plan cannot execute an undeclared operation;
- changed scope invalidates prior authorization;
- publication tests prove ordinary pushes cannot publish artifacts.

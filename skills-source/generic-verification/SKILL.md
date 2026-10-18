---
name: qyrenith-verify
description: Project-neutral AI development verification with Qyrenith. Verify Python, Node, Rust or any other project through deterministic gates: doctor, verify, inspect, explain. No Minecraft knowledge required.
triggers: [qyrenith, verification, verify, audit, code review, build fix, test failure, regression check]
keywords: [verify, audit, reality map, evidence, validation, policy, compatibility, inspect, explain, adapter, benchmark]
domains: [generic, python, javascript, rust, java, cpp]
capabilities: [verification, skill-routing, evidence-gating, state-recovery, artifact-verification]
priority: high
---

# Qyrenith Verification

`qyrenith.py` in the project root is the deterministic verification authority.
It verifies; it never builds, never migrates, and never trusts an agent's word
for the result.

## Agent contract

For any verification task — checking a change, reviewing a fix, validating a
build, auditing a project — the agent MUST use the project-root `qyrenith.py`
workflow when it exists.

1. Check readiness:
   `python qyrenith.py doctor --project .`
2. Discover expertise:
   `python qyrenith.py skills --task "<user task>"`
3. Run generic verification:
   `python qyrenith.py verify --project . --execute`
4. Inspect state when something is unclear:
   `python qyrenith.py inspect --project .`
5. Explain any blocker instead of guessing past it:
   `python qyrenith.py explain <BLOCKER_CODE>`
6. Never claim SUCCESS from an agent statement. Only executed adapters with
   exit code 0, observed artifacts, and recorded evidence advance the verdict.
7. If verification reports `NOT_AVAILABLE`, say so honestly. Do not invent a
   check that did not run.
8. If verification reports `BLOCKED`, resolve the named blocker; the gate
   stays in place until its condition is met.

## Project Reality Map

Qyrenith maintains `.qyrenith/reality-map.json` and `.qyrenith/reality-map.md`.
It inventories evidenced versions, observed feature/source areas,
integrations/dependencies, known issues/blockers, risk areas, fingerprints, and
workflow state.

Treat `PRESENT`, `OBSERVED`, and `REFERENCED` as inventory only. They are not
compatibility proof. Do not convert weak observations into verified facts.

## Authority hierarchy

`qyrenith.py` orchestration rules > this policy > specialized skills > reference material.

Discovery selects expertise; it never overrides workflow safety. All installed
skills may remain installed. Unrelated skills are not activated merely because
they exist.

## Hard invariants

- `AUDIT_BEFORE_PATCH`
- `BACKUP_BEFORE_PATCH`
- `NO_GUESSING`
- `MINIMAL_PATCH`
- `VALIDATE_BEFORE_COMMIT`
- `HONEST_FINAL_REPORT`

## Safety

- Dirty Git state stops managed modification; never discard user changes.
- State is written atomically and includes a run ID, plan hash, step identity,
  build history, events, and recovery information.
- If state contradicts the plan/filesystem/Git state, STOP instead of guessing.
- Never delete, disable, stub, reflect around, or comment out working features
  to make a check pass.
- Never silently replace/remove dependencies.

## Diagnostics

- `python qyrenith.py doctor --project .`
- `python qyrenith.py status --project .`
- `python qyrenith.py report --project .`
- `python qyrenith.py self-test`

## Responsibility boundary

### Qyrenith owns
workflow, state, routing, preflight, backup, audit orchestration, plan gates,
confirmation, fix counter, build delegation, artifact trust, validation gate,
commit gate, reporting, recovery and stop conditions.

### Other skills own
Their declared specialist expertise only. They must not create a competing
orchestrator or work around Qyrenith gates.

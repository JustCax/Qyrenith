# Agent Integration

## Principle

The agent is the domain expert; Qyrenith is the transaction controller.

Qyrenith keeps the integration tool-agnostic: OpenCode, Claude Code, Codex, Cursor, Gemini CLI, generic CLI agents, and MCP-driven workers can participate through the same handoff/result boundary without changing core orchestration.

## Required sequence

1. Discover relevant skills.
2. Read `.qyrenith/audit.md`.
3. Read `.qyrenith/plan.md`.
4. Read `.qyrenith/current-port-step.md`.
5. Use verified specialist evidence.
6. Make the smallest justified patch.
7. Do not declare project success.
8. Return control to Qyrenith.
9. Let build + validation + Reality Map diff decide whether the step is acceptable.

## Agent handoff contract

The handoff includes:

- run ID
- step ID
- exact version transition
- loader
- evidence rule
- selected skills
- conflicts
- forbidden changes
- completion command

See `WORKER_PROTOCOL.md` for the generic lifecycle, `schemas/` for machine-readable contracts, and `workers/README.md` for runnable examples.

## Result contract

A worker/agent result is advisory until Doctor verification. The result must provide structured facts:

- `summary` / claimed result
- `files_changed`
- `commands_run`
- `unresolved`
- `evidence` references
- `dependency_changes` (empty when no dependency drift)

Qyrenith compares `files_changed` against the actual Reality Diff. A mismatch stops the workflow.

Allowed worker result states are `WORKED`, `NO_CHANGE`, `BLOCKED`, and `FAILED`. Doctor adds `verified_by_doctor=false` when accepting an unverified external result.

## Tool-agnostic integration

The integration boundary does not depend on an agent-specific CLI command. The agent receives a deterministic handoff and returns control with:

```bash
python qyrenith.py continue --project . --managed
```

Examples:

- **OpenCode / Claude Code / Codex / Cursor / Gemini CLI:** use the handoff files as the task contract and execute the project's normal agent workflow.
- **Generic CLI agent:** read the handoff and write the structured result expected by the protocol.
- **MCP-driven worker:** treat MCP as the worker transport; Qyrenith still owns the same verification boundary.

No adapter may bypass state, backup, evidence, validation, Reality Diff, or commit gates.

## Skill priority

```text
qyrenith.py orchestration rules
        ↓
qyrenith policy
        ↓
specialist skill
        ↓
general skill
```

Skill discovery cannot bypass state, backup, validation, or commit gates.

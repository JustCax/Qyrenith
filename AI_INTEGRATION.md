# AI Integration

## Purpose

Qyrenith can be used with or without an AI agent. When an agent is connected, it supplies domain knowledge and performs explicitly delegated work; Qyrenith remains responsible for deterministic workflow state, evidence checks, validation gates, and final workflow decisions.

The integration is tool-agnostic. OpenCode, Claude Code, Codex, Cursor, Gemini CLI, other coding agents, and custom workers can use the same CLI and handoff contracts. No specific AI provider or model is required.

## Install optional specialist skills

Qyrenith's reusable skills are distributed in `skills-source/`:

- `generic-verification/` — general software verification guidance.
- `minecraft-porting/` — Minecraft migration guidance.

Copy only the skills relevant to the project into the agent's skill directory:

```bash
mkdir -p .agents/skills
cp -R /path/to/qyrenith/skills-source/generic-verification .agents/skills/
cp -R /path/to/qyrenith/skills-source/minecraft-porting .agents/skills/
```

Skill discovery is optional. Qyrenith can run its CLI and verification workflows without an AI agent or installed skills. Existing user skills should be preserved.

## Discover and select skills

```bash
python qyrenith.py skills --project . --task "review this Python project"
python qyrenith.py skills --project . --task "port this Minecraft mod"
```

Discovery ranks installed `.agents/skills/**/SKILL.md` files using their metadata and task relevance. A discovered skill is advisory expertise; it does not grant authority to bypass Qyrenith's state, evidence, backup, build, validation, or commit gates.

## Recommended agent workflow

1. Run `python qyrenith.py doctor --project .`.
2. Run the appropriate read-only audit or inspection command.
3. Read the generated project state and task/plan files under `.qyrenith/`.
4. Review the exact requested change, constraints, and evidence requirements.
5. Make one minimal, justified patch.
6. Report the actual files changed, commands run, evidence collected, and unresolved issues.
7. Return control to Qyrenith for validation and final decision.

For managed Minecraft migration, use the handoff and continuation workflow documented in `AGENT_INTEGRATION.md` and `WORKER_PROTOCOL.md`.

## Result authority

An agent's statement that work is complete is not verification evidence. A worker result is advisory until Qyrenith checks it against the actual project state and required gates.

The result contract includes:

- summary and claimed result;
- files changed;
- commands run;
- unresolved items;
- evidence references;
- dependency changes.

Qyrenith compares declared file changes with the observed project diff. Mismatches, missing evidence, failed validation, or incomplete execution must remain visible and cannot be promoted to success.

## Security and execution boundaries

- AI is optional and must not be required for core operation.
- Agent output is untrusted input.
- Do not provide credentials or unnecessary permissions to an agent.
- Review commands before allowing project-controlled code to execute.
- Qyrenith's bounded process controls are not an operating-system sandbox.
- Do not use ordinary worker execution to run hostile or untrusted workloads.
- Network access, dependency installation, file modification, and publication must be explicitly authorized by the user or project policy.

## Further documentation

- `AGENT_INTEGRATION.md` — handoff and result lifecycle.
- `WORKER_PROTOCOL.md` — worker contract.
- `ADAPTERS.md` — adapter discovery and capabilities.
- `EVIDENCE.md` — evidence and claim model.
- `SAFETY.md` — safety boundaries and recovery.

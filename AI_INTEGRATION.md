# Qyrenith AI Integration

How to let an AI coding client work with Qyrenith. The same rules hold with or
without an agent — see `AI_FREE.md` for the CLI-only path. Nothing here
contradicts it; this guide only adds where each client reads its instructions
from and what the agent may and may not decide.

## The one rule

The agent supplies expertise. Only executed checks, observed artifacts, and
recorded evidence advance any verdict. An agent statement is never proof of
completion. If a client file below ever seems to say otherwise, the CLI wins.

## Install per client

All files below are generated from `skills-source/` by
`scripts/generate-client-entries.py`. Do not edit them by hand.

| Client | File | Install |
|---|---|---|
| OpenCode, Codex | `AGENTS.md` | Copy to the repository root. |
| Claude Code | `CLAUDE.md` | Copy to the repository root. |
| Gemini CLI | `GEMINI.md` | Copy to the repository root. |
| Cursor | `.cursor/rules/qyrenith.mdc` | Copy to `.cursor/rules/qyrenith.mdc`. |
| Windsurf | `.windsurf/rules/qyrenith.md` | Copy to `.windsurf/rules/qyrenith.md`. |
| Cline | `.clinerules` | Copy to the repository root. |
| Aider | `CONVENTIONS.md` | Copy to the repository root. |
| Continue | `.continue/rules/qyrenith.md` | Copy to `.continue/rules/qyrenith.md`. |

The Qyrenith skill itself (`skills-source/`, also installed as
`.agents/skills/qyrenith/SKILL.md` in this repository) is discovered through
`python qyrenith.py skills --task "<task>"` like any other skill.

## Regenerating after a skill change

```bash
python scripts/generate-client-entries.py
```

Commit the regenerated files together with the canonical change.

## What the agent may decide

- Which specialist skill to use for a delegated patch.
- The contents of a minimal patch, within verified evidence.
- When to stop and report `UNKNOWN_API`, `BLOCKED`, or a failed check.

## What the agent may never decide

- Whether a check passed (only exit code 0 plus recorded evidence counts).
- Whether a gate can be skipped (it cannot; resolve the named condition).
- Whether `NOT_AVAILABLE` means success (it means nothing ran).
- Whether a migration route exists (only verified version edges count).

## Suggested first prompts

- "Verify this project with Qyrenith and report the result honestly."
- "Port this mod one version step following the Qyrenith handoff, then return
  control with `continue`."
- "Explain this Qyrenith blocker and what evidence would resolve it."

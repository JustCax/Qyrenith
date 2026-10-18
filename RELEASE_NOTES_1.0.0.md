# Qyrenith 1.0.0 — First Public Release

## What Qyrenith is

A verification, safety, and orchestration control plane for Non-AI and
AI-assisted software development. One file (`qyrenith.py`), standard library only, no
dependencies. An agent statement is never proof of completion; only executed
checks, observed artifacts, and recorded evidence advance any verdict.

## What is verified in this release

| Domain | Level | Evidence |
|---|---|---|
| Minecraft | L5 — production | CI gate, policy engine, recovery tests, adversarial/failure-quality cases, golden migration benchmark. |
| Python | L2 — verified | `python-compile` + `python-unittest` adapters, reproducible benchmark, failure-detection test. |
| JavaScript/TypeScript/Node | L2 — verified | `node-tests` adapter (built-in runner), reproducible benchmark, failure-detection test. |
| Rust | L2 — verified | `rust-check` adapter, reproducible benchmark, failure-detection test. |
| All other registered domains | L0 — registered | Routing names only. |

## What is explicitly not claimed

- No runtime validation (headless server runs, crash/log scans) is enabled
  implicitly or claimed as satisfied offline.
- No L3 worker ecosystem: there is no worker registry, no benchmark scoring,
  and no multi-agent orchestration beyond the handoff/result contract.
- No hosted service, dashboard, or team product.
- A real Gradle/JAR build for Minecraft migration remains a mandatory real
  gate; it is never reported as satisfied without running.
- Unknown stays unknown: `NOT_AVAILABLE` means nothing ran, and zero available
  capability is never a pass.

## Install paths

- Copy `qyrenith.py` into the project root (primary, documented path).
- Or install the repository as a Python project (`pyproject.toml`,
  build-system only, no dependencies).

## AI and AI-less use

- `AI_FREE.md`: the full workflow with no AI agent, validated end-to-end.
- `AI_INTEGRATION.md`: per-client install table (OpenCode, Codex, Claude Code,
  Gemini CLI, Cursor, Windsurf, Cline, Aider, Continue) and what an agent may
  and may not decide.
- Client files are generated from `skills-source/` and must not be hand-edited.

## Verification

This release passed, locally: the full test suite (`OK (skipped=5)`),
`self-test`, `benchmark` (all fixtures including the new language-verification
ones), `public-audit`, documentation-link and JSON-schema checks.

# Qyrenith without AI

You do not need an AI agent to use Qyrenith. Everything below is plain CLI use:
copy one file, run commands, read the output. No account, no plugin, no agent.

## Install

Requirements: Python 3.8 or newer. Git is recommended but optional.

```bash
# 1. Copy the control file into your project
cp /path/to/qyrenith.py /path/to/your-project/
cd /path/to/your-project

# 2. Check the project is healthy
python qyrenith.py doctor --project .
```

`doctor` prints a checklist. `READY` means everything works.
`READY_WITH_LIMITATIONS` means verification works but managed Minecraft
build/port execution is unavailable (no canonical build skill). Either is a
good starting point; `BLOCKED` names what is missing.

## Verify your project

```bash
# 3. Discover what can be checked (runs nothing)
python qyrenith.py verify --project .

# 4. Run the checks
python qyrenith.py verify --project . --execute
```

If every applicable check passes, the status is `PASS`. If a detected check
cannot run because its tool is not installed (for example `python-tests` when
pytest is missing), the gate stays `BLOCKED` by default — install the tool,
or re-run with the explicit opt-in to note it as informational instead:

```bash
python qyrenith.py verify --project . --execute --allow-missing-adapters
```

This never turns "nothing could run" into a pass: a project with no
applicable checks still reports `NOT_AVAILABLE`.

The report lists one adapter per capability found in your project:

| Status | Meaning |
|---|---|
| `PASS` | The check ran and exited zero. |
| `FAIL` | The check ran and failed. Fix the underlying problem, not the report. |
| `AVAILABLE` | The check exists but was not run (you omitted `--execute`). |
| `NOT_AVAILABLE` | The tool for this check is not installed. Install it or accept the gap. |
| `SKIPPED_UNAVAILABLE` | Only with `--allow-missing-adapters`: noted, not blocking. |

A project with no applicable checks reports `NOT_AVAILABLE` — an honest answer,
not a pass.

For strict CI use, add `--ci`: any failure or unavailable adapter blocks with
exit code 1 or 2, unless you explicitly pass `--allow-missing-adapters`.

## Understand the result

```bash
# 5. Read the project state in plain language
python qyrenith.py inspect --project .

# 6. Ask what a blocker means and what to do next
python qyrenith.py explain <BLOCKER_CODE>
```

`inspect` prints versions, features, integrations, issues, evidence counts and
workflow state. `explain` prints the why, the effect, the evidence needed, and
the next action for any blocker code.

## Check policy and history

```bash
# 7. Evaluate project policy (optional policy.json)
python qyrenith.py policy --project .

# 8. See the last report and run status
python qyrenith.py report --project .
python qyrenith.py status --project .
```

## Run the project's own quality gates

```bash
# 9. Full self-test, benchmarks, and release hygiene
python qyrenith.py self-test
python qyrenith.py benchmark --project .
python qyrenith.py public-audit --project .
```

These are the same gates the Qyrenith project itself must pass before any
release. If they pass on your machine, your checkout is healthy.

## What Qyrenith will not do for you

- It will not fix your code. It tells you exactly what failed and where.
- It will not guess. Unknown stays unknown until you provide evidence.
- It will not migrate a Minecraft mod without the Minecraft workflow
  (`audit`, `plan`, `port`, `continue`, `build`), which additionally requires
  the canonical build skill and a clean Git tree. For that path, read
  `SETUP.md`.

## Troubleshooting

- `PREFLIGHT_FAILURE: Qyrenith orchestrator missing or unsafe` — you ran a
  command in a directory without `qyrenith.py`. Copy it there first.
- `This command applies to a Minecraft mod project` — you ran a migration
  command (`port`, `plan`, `dry-run`, `build`) on a non-Minecraft project.
  Use `verify` instead.
- `Security review required` — run `python qyrenith.py explain AUDIT_BLOCKER`,
  inspect the finding, and either remove the cause or approve that exact
  finding with `security-review --finding-id <id> --reason "..." --yes`.

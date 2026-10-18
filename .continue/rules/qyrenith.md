<!-- GENERATED from skills-source/ by scripts/generate-client-entries.py. Do not edit by hand; edit the canonical skill and re-run the generator. -->

# Qyrenith (Continue)

Continue loads rules from `.continue/rules/`.

## Install

Copy this file to `.continue/rules/qyrenith.md` in the repository.

# Qyrenith — verification and orchestration control plane

`qyrenith.py` in the project root is the deterministic authority. The agent supplies expertise; only executed checks, observed artifacts, and recorded evidence advance any verdict. An agent statement is never proof of completion.

## Generic verification (any project)

```bash
python qyrenith.py doctor --project .
python qyrenith.py verify --project . --execute
python qyrenith.py inspect --project .
python qyrenith.py explain <BLOCKER_CODE>
```

State lives in `.qyrenith/`. A `NOT_AVAILABLE` result is an honest answer, never a reason to invent a check. A `BLOCKED` result names its blocker; resolve the named condition and re-run.

## Hard invariants

- `AUDIT_BEFORE_PATCH`
- `BACKUP_BEFORE_PATCH`
- `NO_GUESSING`
- `MINIMAL_PATCH`
- `VALIDATE_BEFORE_COMMIT`
- `HONEST_FINAL_REPORT`

## Minecraft migration (Minecraft projects only)

```bash
python qyrenith.py port --project . --target-mc <target> --target-loader <loader> --managed
python qyrenith.py continue --project . --managed
```

One verified version step at a time, at most five fix iterations per step, build plus validation before every commit. Unknown APIs stop the workflow with `UNKNOWN_API` instead of being guessed.

## Full contracts

The text below is the canonical skill source. It is advisory routing and procedure; the CLI owns every gate.

<details>
<summary>Generic verification skill (canonical)</summary>

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

</details>

<details>
<summary>Minecraft porting skill (canonical)</summary>

# Qyrenith Minecraft Porting

`qyrenith.py` in the project root is the deterministic workflow authority. It is
an orchestrator, not a Minecraft API encyclopedia.

## Agent contract

For any managed Minecraft migration, the agent MUST use the project-root
`qyrenith.py` workflow. Domain-specific migration knowledge is used only inside
the delegated patch; it never overrides workflow safety.

1. Discover expertise first:
   `python qyrenith.py skills --task "<user task>"`
2. Read `.qyrenith/skill-index.json` and `.qyrenith/agent-task.md`.
3. Start managed orchestration:
   `python qyrenith.py port --project . --target-mc <target> --target-loader <loader> --managed`
4. Read `.qyrenith/current-port-step.md`.
5. Perform only the delegated specialist work. Use verified migration evidence
   for API changes.
6. Every API change needs verified evidence. If evidence is unavailable, STOP
   with `UNKNOWN_API`; do not guess.
7. After the minimal patch, return control:
   `python qyrenith.py continue --project . --managed`
8. If the build fails, read the generated fix handoff. At most five fix
   iterations are permitted per step.
9. Never claim SUCCESS from an agent statement. Qyrenith verifies build exit
   status, source stability, JAR identity/existence, metadata, validation, and
   commit gates.

## Project Reality Map

Before migration work, Qyrenith maintains `.qyrenith/reality-map.json` and
`.qyrenith/reality-map.md`. It inventories evidenced versions, observed
feature/source areas, integrations/dependencies, known issues/blockers, risk
areas, fingerprints, and workflow state. Before every port step it freezes
`.qyrenith/baseline.json`; after validation it compares the post-step map
against that baseline.

Treat `PRESENT`, `OBSERVED`, and `REFERENCED` as inventory only. They are not
compatibility proof. Do not convert weak observations into verified API facts.
Feature/integration removals detected by the step diff are validation failures
unless the workflow explicitly and safely accounts for them.

## Authority hierarchy

`qyrenith.py` orchestration rules > this policy > specialized skills > reference material.

Discovery selects expertise; it never overrides workflow safety. All installed
skills may remain installed. Unrelated skills are not activated merely because
they exist.

## Hard invariants

- `AUDIT_BEFORE_PATCH`
- `BACKUP_BEFORE_PATCH`
- `ONE_VERSION_STEP_AT_A_TIME`
- `NO_GUESSING`
- `MINIMAL_PATCH`
- `BUILD_AFTER_PATCH`
- `SUCCESS_REQUIRES_EXIT_0_AND_NONEMPTY_JAR`
- `SOURCE_CHANGE_DURING_BUILD => UNTRUSTED`
- `MAX_5_FIX_ITERATIONS`
- `VALIDATE_BEFORE_COMMIT`
- `COMMIT_BEFORE_NEXT_STEP`
- `HONEST_FINAL_REPORT`

## Safety

- Dirty Git state stops the workflow; never discard user changes.
- Non-Git projects receive a safe ZIP backup before patching.
- Backup archives are checked for path traversal and case collisions.
- State is written atomically and includes a run ID, plan hash, step identity,
  build history, events, and recovery information.
- A stale lock from a crashed process may be recovered only when its recorded
  PID is no longer active.
- If state contradicts the plan/filesystem/Git state, STOP instead of guessing.
- Never delete, disable, stub, reflect around, or comment out working features
  to make a build pass.
- Never silently replace/remove dependencies.

## Version planning

A migration step must be a real, verified transition. Qyrenith does not invent
a version chain. If a verified route is unavailable, the workflow stops with
`UNKNOWN_API` and asks for evidence rather than fabricating intermediate
versions.

## Build boundary

Build execution belongs to:
`.agents/skills/minecraft-build/scripts/build.sh <project>`

Qyrenith does not implement a second Gradle builder. It records the delegated
output and independently evaluates:

- exit code
- source fingerprint before/after build
- non-empty JAR existence
- JAR SHA-256
- stale-artifact warning

UP-TO-DATE artifacts are valid when the source fingerprint is stable.

## Validation

Mandatory levels 1–4:

1. compile/build exit evidence
2. delegated Gradle build success
3. non-empty JAR
4. metadata and mod-ID integrity, plus target-version reachability for the
   current step

Levels 5–6 (headless server / crash scan) are not enabled implicitly.

## Resume / idempotency

`python qyrenith.py status --project .` shows the resumable state.

`continue` is safe to repeat: an already completed step is not executed again.
The current plan is protected by a hash. A changed plan, mismatched step,
corrupt state, or conflicting target causes STOP rather than an inferred
recovery.

A successful step must be committed before the next step can begin.

## Confirmation modes

- Interactive: confirmation may be requested for migration plans.
- `--yes`: explicitly approves confirmation gates.
- `--noninteractive`: never fabricates approval; it stops at agent handoffs.
- `--managed`: marks an agent-managed workflow and generates explicit handoff
  files.

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

### minecraft-porting owns
Minecraft/loader API migration knowledge, verified version/API interpretation,
minimal migration patches, reference lookup, and migration-log content.

### minecraft-build owns
Gradle invocation, build logs, failure extraction, JAR discovery and
build-oriented validation.

### Other skills own
Their declared specialist expertise only. They must not create a competing
orchestrator or work around Qyrenith gates.

</details>

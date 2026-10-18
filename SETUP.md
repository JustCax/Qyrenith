# Qyrenith — Full Setup Guide

## 1. Requirements

- Python 3.8+
- Git recommended for transactional commits and rollback
- Any software project (Minecraft mod, Python application, Node service, etc.)
- `.agents/skills/qyrenith/` for the Qyrenith skill (agent integration)
- Optional specialist skills such as debugging and validation

No Python packages are required.

## 2. Install into a project

Place `qyrenith.py` at the project root and copy the `qyrenith` skill into `.agents/skills/qyrenith/`.

Keep every existing skill. Qyrenith discovers and routes to relevant skills; it does not require deleting unrelated ones.

## 3. First health check

```bash
python qyrenith.py doctor --project .
python qyrenith.py self-test
python qyrenith.py inspect --project .
```

`doctor` checks Python, write access, Git availability, the canonical build script, skill discovery and the Reality Map state. If the canonical build skill is absent but another generic verification adapter is available, the result is `READY_WITH_LIMITATIONS` and explicitly reports that managed build/port execution is unavailable. It never treats Qyrenith itself as a project-language adapter inside a Minecraft project.

On Windows, Qyrenith configures stdout/stderr for UTF-8 with replacement for unsupported console characters. Symlink-specific tests require Windows Developer Mode or elevated privileges; without that capability, those four tests are skipped rather than reported as engine failures.

## 3.5. Quickstart for non-Minecraft projects

Qyrenith is project-neutral. For a Python, Node, Rust, or any other project:

```bash
# 1. Copy Qyrenith into the project root
cp /path/to/qyrenith.py .

# 2. Run the health check
python qyrenith.py doctor --project .

# 3. Run generic verification
python qyrenith.py verify --project . --execute

# 4. Run generic verification
python qyrenith.py verify --project . --execute

# 5. Inspect the Reality Map
python qyrenith.py inspect --project .
```

`doctor` checks Python, write access, Git availability, skill discovery and the Reality Map state. If no canonical build skill is found but a generic verification adapter is available, the result is `READY_WITH_LIMITATIONS` and explicitly reports that managed build/port execution is unavailable. `verify` discovers language adapters (Python compile/unittest, Node tests, Rust check) and runs them with `--execute`.

## 4. Skill discovery

```bash
python qyrenith.py skills --project . --task "port a Minecraft mod to the target loader and version"
```

Outputs:

- `.qyrenith/skill-index.json`
- `.qyrenith/agent-task.md`

Discovery is expertise selection only. It cannot bypass workflow rules.

## 5. Reality Map

```bash
python qyrenith.py reality --project .
```

The map is stored in:

- `.qyrenith/reality-map.json`
- `.qyrenith/reality-map.md`
- `.qyrenith/reality-history.jsonl`

It records observable versions, project identity, dependencies/integrations, feature declarations or conservative source areas, issues, blockers, risks, evidence, fingerprints, and a relationship graph.

For higher semantic accuracy, declare project features in `.qyrenith/project-map.json`. This file belongs to the project and can contain any feature names; Qyrenith itself stays generic.

## 6. Audit

```bash
python qyrenith.py audit --project . --target-mc <target> --target-loader <loader>
```

The audit is source/resource read-only. It detects Minecraft/loader/Java/Gradle/mod metadata, dependencies, inventories and risk areas.

Unknown critical identity blocks modification. Dependency compatibility must be supported by evidence before it can be treated as verified.

## 7. Plan

```bash
python qyrenith.py plan --project . --target-mc <target> --target-loader <loader>
```

A plan is executable only when a verified one-step path is available. Qyrenith never invents an intermediate version or API replacement.

## 8. Dry-run

```bash
python qyrenith.py dry-run --project . --target-mc <target> --target-loader <loader>
```

This command performs console-only planning. It does not create state files, branches, backups, patches, builds, or commits.

## 9. Managed migration

```bash
python qyrenith.py port --project . --target-mc <target> --target-loader <loader> --managed
```

The workflow is:

```text
PREFLIGHT → BACKUP → AUDIT → PLAN → PORT STEP HANDOFF
```

The agent reads the generated handoff and uses the selected specialist skills. It must not bypass Qyrenith.

## 10. Agent return protocol

After the minimal verified patch:

```bash
python qyrenith.py continue --project . --managed
```

Qyrenith then performs:

```text
BUILD → ARTIFACT TRUST → VALIDATION → REALITY DIFF → MIGRATION LOG → COMMIT
```

## 11. Reality baseline

Before every port step, `.qyrenith/baseline.json` freezes the Reality Map plus file hashes.

After validation, Qyrenith compares:

- source fingerprints
- files added/modified/removed
- observed features
- integrations
- issues
- relationship state

Unexpected declared feature/integration removals fail validation. User changes are never discarded.

## 12. Evidence

Optional explicit evidence can live in `.qyrenith/evidence.json`:

```json
{
  "evidence": [
    {
      "type": "api-migration",
      "claim": "Example verified migration claim",
      "source": "verified-reference",
      "confidence": "HIGH"
    }
  ]
}
```

Evidence confidence is informational unless a workflow gate requires verification. Reference presence alone is never treated as proof.

## 13. Build trust

The canonical command is:

```text
.agents/skills/minecraft-build/scripts/build.sh <project>
```

A successful build requires:

1. exit code 0;
2. stable source fingerprint during the build;
3. non-empty JAR in `build/libs`.

JAR modification time alone never decides success. UP-TO-DATE builds can legitimately reuse an older artifact.

## 14. Repair loop

A failed build creates a bounded fix handoff:

```text
1/5 → 2/5 → 3/5 → 4/5 → 5/5 → STOP
```

There is no automatic sixth attempt.

## 15. Resume and idempotency

```bash
python qyrenith.py status --project .
python qyrenith.py continue --project . --managed
```

State is atomically written to `.qyrenith/state.json`; events are appended to `.qyrenith/events.jsonl`.

If the plan hash, step identity, or filesystem state no longer matches the recorded transaction, Qyrenith stops rather than guessing.

## 16. Noninteractive mode

```bash
python qyrenith.py port --project . --target-mc <target> --target-loader <loader> --managed --noninteractive
```

Noninteractive mode does not auto-approve a missing human decision. `--yes` only approves explicit confirmation gates; it does not disable safety invariants.

## 17. Git transaction model

A managed Git migration requires a clean working tree. Qyrenith uses a dedicated migration branch and commits only after mandatory validation.

Rollback is an explicit Git revert, never a silent `reset --hard`:

```bash
python qyrenith.py rollback --project . --yes
```

Rollback requires a clean tree and a recorded Qyrenith commit, so user work cannot be silently discarded.

## 18. Inspect and explain

```bash
python qyrenith.py inspect --project .
python qyrenith.py explain UNKNOWN_API
python qyrenith.py explain DEPENDENCY_BLOCKER
python qyrenith.py explain UNTRUSTED_BUILD
python qyrenith.py explain FIX_LIMIT_REACHED
```

These commands are designed to make the tool explainable instead of a black box.

## 19. Public project hygiene

Do not put private project paths, API keys, personal names, proprietary source, or project-specific feature names into the Qyrenith distribution.

Project-specific knowledge belongs in the user's project or its specialist skills.


## Quality gates before publishing

Run the complete local quality gate before publishing changes:

```bash
python qyrenith.py self-test
python qyrenith.py security-test
python qyrenith.py security-review --project . --finding-id <finding-id> --reason "Explain why this exact finding is a reviewed false positive" --yes
python qyrenith.py recovery-test
python qyrenith.py benchmark
python qyrenith.py doctor
```

Useful inspection commands:

```bash
python qyrenith.py graph
python qyrenith.py adapters
python qyrenith.py evidence
```

The control-plane state lives under `.qyrenith/`. Do not commit secrets into evidence files. Project-specific semantic feature declarations belong in `.qyrenith/project-map.json`; automatically discovered feature candidates remain unverified until confirmed.

## Target artifact inspection

Inspect a target JAR/ZIP without extracting it:

```bash
python qyrenith.py artifact-inspect --project . target.jar
```

The Doctor applies archive path/resource/symlink safety checks first, then reads only known metadata files and records the artifact SHA-256. The artifact must remain inside the project root.

## Further reading

- `AI_FREE.md` — the same workflow with no AI agent, CLI only.
- `AI_INTEGRATION.md` — per-client install table and what an agent may and may
  not decide.

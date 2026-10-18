# Architecture

```text
Agent / OpenCode
      │
      ▼
Skill Discovery / Router
      │
      ▼
qyrenith policy
      │
      ▼
qyrenith.py
 ├─ preflight
 ├─ audit
 ├─ Reality Map
 ├─ evidence gates
 ├─ plan
 ├─ one-step handoff
 ├─ build delegation
 ├─ failure analysis / bounded repair
 ├─ validation
 ├─ Reality Map diff
 ├─ migration log
 └─ Git transaction
      │
      ├── minecraft-porting → Minecraft/loader knowledge
      ├── minecraft-build   → Gradle/build evidence
      └── other specialist skills → their declared expertise
```

## Responsibility boundary

`qyrenith.py` owns workflow, ordering, safety, state, evidence gates, artifact trust, validation, commit gating and reporting.

`qyrenith/SKILL.md` tells agents how to participate.

`minecraft-porting` owns version-specific migration knowledge and minimal API changes.

`minecraft-build` owns canonical Gradle execution, logs, error extraction and JAR detection.

Other skills own their declared domain expertise.

The orchestrator intentionally contains no user-specific mod names and no Minecraft API encyclopedia.


## Control-plane layers

```text
PROJECT
  ↓
PREFLIGHT / BACKUP / TRANSACTION
  ↓
REALITY MAP + EVIDENCE ENGINE
  ├─ dependency lock
  ├─ version graph
  ├─ feature candidates
  └─ security findings
  ↓
SKILL / ADAPTER ROUTER
  ↓
ONE PORT STEP
  ↓
AGENT / WORKER
  ↓
BUILD
  ↓
VALIDATION
  ↓
REALITY DIFF + SECURITY GATE
  ↓
COMMIT
```

### Non-negotiable authority rule

Workers provide expertise. They do not provide authority. A worker result is advisory until Qyrenith independently verifies the resulting project state.

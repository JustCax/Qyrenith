# Benchmarks

Run:

```bash
python qyrenith.py benchmark --project .
```

The suite contains two classes of public benchmarks:

- **control-plane structural fixtures**: tiny projects, dependency-heavy projects,
  networking, datagen, resources, multi-loader structure, intentionally broken /
  recovery scenarios, and semantic migration scenarios;
- **a real NeoForge golden migration**: `neoforge-1.21-to-1.21.1`, a small
  NeoForge-shaped Java mod using the verified 1.21 / 21.0.167 baseline and
  1.21.1 / 21.1.235 target. Its bounded external porter changes only the
  declared Minecraft/NeoForge version properties. The benchmark executes that
  worker in a temporary copy and checks the exact changed/unchanged files,
  target properties, and `verified_by_doctor=false` contract.

The golden benchmark intentionally does not claim a successful Gradle build in
an offline development environment. Build and final Doctor verification remain
mandatory gates in a real migration.

## Failure-quality / adversarial benchmarks

The benchmark gate also checks that unsafe states fail closed. The required
adversarial cases include:

- unknown API / missing verified route
- tampered trusted worker
- dirty Git state
- missing migration evidence
- critical feature/integration disappearance
- fake worker SUCCESS claim
- stale build artifact
- unsafe path / project-root escape

These cases are deterministic assertions about the controller's safety
behavior, not claims that a worker can never fail.

`python qyrenith.py failure-quality` runs the focused safety cases.
`python qyrenith.py benchmark` includes them in the complete benchmark result.

## Deterministic replay

`python qyrenith.py replay` verifies both the recorded plan hash and the recorded
plan-context fingerprint. It also recomputes the current decision context from
live audit, version-graph, dependency-lock, and adapter-trust inputs. If the
live context differs, replay is blocked rather than silently continuing from a
stale plan.

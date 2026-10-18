# Adapter Protocol

Qyrenith is a control plane, not a replacement for every worker.

Adapters may represent:

- specialized migration tools
- installed agent skills
- MCP-backed tooling
- generic coding agents
- project-local workers

A worker must not declare final success. The protocol is:

```text
AGENT_HANDOFF → AGENT_WORK → AGENT_RESULT → DOCTOR_VERIFICATION
```

Optional `.qyrenith/adapters.json`:

```json
{
  "adapters": [
    {
      "name": "example-worker",
      "kind": "external",
      "version": "1.0.0",
      "command": ["example-worker", "--project"],
      "capabilities": ["port", "debug"],
      "supported_loaders": ["neoforge"],
      "supported_minecraft_versions": ["1.21", "1.21.1"],
      "task_types": ["port"],
      "risk_profile": "bounded",
      "evidence_requirements": ["verified-mapping"],
      "trust": "COMMUNITY",
      "sha256": "<sha256-of-worker-entrypoint>"
    }
  ]
}
```

Worker selection is advisory. Qyrenith still owns safety, evidence, build, validation, reality-diff and commit gates.

## External worker fixture

`workers/example-worker.py` is a runnable protocol fixture. It accepts one JSON request on stdin and emits one JSON result on stdout. Its `WORKED` result explicitly carries `verified_by_doctor=false`.

This proves the external-process boundary without pretending that the fixture is a Minecraft porter.

## Bounded NeoForge porter

`workers/neoforge-porter.py` is a deliberately narrow real migration worker used by the public golden benchmark. It supports only the verified `Minecraft 1.21 / NeoForge 21.0.167 -> Minecraft 1.21.1 / NeoForge 21.1.235` transition and refuses unknown mappings. The worker reports `WORKED`; build, validation and final verification remain Doctor responsibilities.

## Adapter trust and provenance

Adapter discovery records a trust level separately from capability matching.
The effective trust levels are:

- `VERIFIED` — explicitly declared as verified and the SHA-256 of the executable entrypoint matches.
- `COMMUNITY` — explicitly declared as community-trusted and the SHA-256 matches.
- `UNKNOWN` — default for undeclared/unverifiable provenance, or whenever a declared hash does not match.
- `LOCAL` — project-local skills discovered from the project itself.

A hash mismatch never silently preserves the previous trust level. Trust is advisory metadata; it does not authorize worker SUCCESS. Doctor still independently verifies build, validation, Reality Map, Reality Diff and commit gates.

Generated records:

- `.qyrenith/adapter-index.json` — discovered adapters and trust metadata.
- `.qyrenith/adapter-trust.json` — normalized trust/provenance records.

The current implementation does not automatically download or execute an undisclosed adapter. External workers remain explicitly declared by the project configuration.

### Execution trust gate

For an external adapter that declares `VERIFIED` or `COMMUNITY` trust, the manifest may provide an `entrypoint` field identifying the worker file whose SHA-256 is trusted. Qyrenith recomputes that hash immediately before execution. If the observed hash no longer matches the declared hash, execution is stopped with `STOPPED`; the worker is not allowed to run under stale provenance.

`UNKNOWN` adapters may still be executed when the user explicitly names the adapter with `worker-run`, but their output remains advisory and can never authorize Doctor `SUCCESS`.

### Resource and process boundary

External workers are treated as untrusted processes. Their stdout and stderr are each bounded to 1 MiB. Exceeding either bound stops the worker result before it can be interpreted as migration evidence. Timeouts terminate the worker process group where the platform supports process groups, with a forced termination fallback. The worker never receives the controller's ambient environment; only the reduced execution environment is passed through.

## Manifest execution contract

For non-protocol work operations such as `port`, an external adapter must declare:

- `version`
- `task_types`
- `risk_profile`
- `evidence_requirements`

Minecraft reference adapters additionally declare `supported_loaders` and `supported_minecraft_versions`. Generic/non-Minecraft adapters instead declare `supported_platforms` and `supported_versions`. The two scope models are mutually exclusive at validation time.

Qyrenith rejects an incomplete manifest before launching the worker. When the request supplies a loader/platform or an explicit `SOURCE -> TARGET` task, the declared support list must match. This makes the adapter protocol genuinely reusable without weakening the established Minecraft contract.

### Machine-readable contracts

The generic integration contracts are published under `schemas/`:

- `worker-handoff.schema.json`
- `worker-result.schema.json`
- `adapter-manifest.schema.json`
- `evidence.schema.json`

## Specialist skill discovery

Project-local `SKILL.md` files are discoverable independently of hard-coded skill names or domain allow-lists. Every discovered skill is represented in the adapter index.
For routing visibility, Qyrenith may infer capability labels from skill metadata when explicit capabilities are absent, including known specialist terms such as `blockbench`, `modeling`, `asset`, `resource`, and `animation`; these labels are optional routing metadata, not an allow-list.

This inference is deliberately non-authoritative: a discovered skill remains `LOCAL` and `DISCOVERED`; it is not converted into an external worker and it cannot authorize a migration, build, or Doctor `SUCCESS`. A Blockbench modelling skill can therefore be recognized and selected for relevant work while its actual model-editing operations remain inside the skill/tool boundary. An entirely new specialist skill domain is also visible even if Qyrenith has never seen its name before.

## External engine compatibility

A porter or transformation engine does not need to be part of Qyrenith itself.
A third-party engine can become compatible by implementing or being wrapped by
the adapter contract (`discover`, `inspect`, `plan`, `execute`, `result`).

The external engine may be a CLI, executable, library, agent, service, or tool
written in another language/runtime. The adapter declares identity, version,
capabilities, supported platform/loader/version scope, task type, risk profile,
evidence requirements, execution interface, result schema, and provenance.

Qyrenith treats the external executor as untrusted. `WORKED` is an execution
claim, not a verified success state. Build, validation, Reality Map, Reality
Diff, security, and other required gates remain under Qyrenith control.

Minecraft is the primary reference ecosystem, but the protocol is intentionally
platform-neutral enough for future non-Minecraft modding/content ecosystems to
connect through adapters. Such integrations must be concrete and tested rather
than pre-built as speculative platform support.

## Universal external-engine discovery

External engines may advertise a protocol-compatible adapter through a JSON manifest in `.qyrenith/adapters.d/*.json`. Discovery is non-executing: the manifest is inspected, validated, and indexed, but the declared command is never run merely because it was discovered.

This directory is intentionally open-ended. Qyrenith does not maintain a closed list of engine names or domains. A valid manifest can describe a previously unknown engine, platform, version family, capability, or task type. Invalid manifests remain visible as `BLOCKED` with an explanatory error instead of disappearing from discovery.

Discovery, capability matching, provenance/trust, execution permission, and Doctor verification are separate gates. Recognition never grants execution authority, and a worker/engine cannot self-authorize `SUCCESS`.

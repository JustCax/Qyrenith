# Worker examples

These workers are protocol fixtures, not part of Qyrenith's product identity.

## Lifecycle

```text
discover → inspect → plan → execute → result → Doctor verification
```

The generic external boundary is JSON-over-stdin/stdout. A worker must never self-authorize final success.

## Example worker

`example-worker.py` demonstrates `discover`, `inspect`, `plan`, and `result`. Its `WORKED` result always carries `verified_by_doctor=false`.

## Bounded porter

`neoforge-porter.py` is a deliberately narrow benchmark worker for one verified migration route. It is not the general Minecraft migration engine.

## Result example

```json
{
  "schema": 1,
  "worker": "example-worker",
  "status": "WORKED",
  "summary": "Worker completed its requested operation.",
  "files_changed": [],
  "commands_run": [],
  "evidence": [],
  "unresolved": [],
  "verified_by_doctor": false
}
```

## Failure example

```json
{
  "schema": 1,
  "worker": "example-worker",
  "status": "BLOCKED",
  "summary": "Required evidence is unavailable.",
  "files_changed": [],
  "unresolved": ["UNKNOWN_API"]
}
```

See `WORKER_PROTOCOL.md` and `ADAPTERS.md` for the execution, capability, provenance, and resource boundaries.

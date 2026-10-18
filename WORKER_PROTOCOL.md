# Worker / Porter Protocol

Workers are replaceable execution specialists. Qyrenith owns the safety boundary.

Lifecycle:

`DISCOVER -> HANDOFF -> WORK -> RESULT -> DOCTOR_VERIFICATION`

## Handoff

```json
{
  "schema": 1,
  "worker": "example-worker",
  "task": "one version step",
  "source": "1.20.1",
  "target": "1.20.2",
  "project_root": ".",
  "constraints": ["minimal patch", "preserve behavior"]
}
```

## Result

```json
{
  "schema": 1,
  "status": "WORKED",
  "files_changed": [],
  "commands_run": [],
  "claims": [],
  "unresolved": []
}
```

`WORKED` is not `SUCCESS`. Result objects for work operations must include `summary`, `files_changed`, `commands_run`, `unresolved`, `evidence`, and `dependency_changes`. Qyrenith compares `files_changed` with the actual Reality Diff. Only Qyrenith can produce a verified success after build, validation, and Reality Diff gates pass.

## Capability boundary

Adapter manifests may declare task capabilities such as `inspect`, `plan`, or `port`. Protocol control operations (`discover`, `inspect`, `plan`, `result`) remain protocol-level operations. A non-protocol task operation is treated as a required capability unless the handoff explicitly supplies `required_capability`. If the declared capability is missing, Qyrenith stops before launching the worker.


## Adapter manifest

A non-protocol work operation requires a manifest with version, capabilities, supported loaders, supported Minecraft versions, task types, risk profile, evidence requirements, command/interface, and result schema. Qyrenith validates these declarations before execution.

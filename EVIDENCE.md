# Evidence Model

Qyrenith distinguishes observation from verification.

```text
CLAIM → EVIDENCE → CONFIDENCE → STATUS
```

Evidence can come from local references, project references, migration knowledge, official documentation, mappings, target artifacts, build/runtime checks, or explicit human confirmation. Each recorded claim carries explicit `provider`, `source`, `timestamp`, `verification_method`, `confidence`, and optional `human_confirmation` fields. Sensitive values are redacted before persistence.

A missing or weak claim remains `UNKNOWN`. The orchestrator must not turn an agent guess into a verified fact.

The append-only evidence ledger is `.qyrenith/evidence-ledger.jsonl`. Dependency verification is represented in `.qyrenith/dependency-lock.json` and version relationships in `.qyrenith/version-graph.json`.


## Generic verification evidence

The generic `verify --execute` path may append evidence for directly observed adapter exit codes and non-empty project-local artifacts. Artifact evidence includes the project-relative path, size, and SHA-256 fingerprint. Symlinked or project-boundary-escaping artifacts are excluded rather than trusted.

Verification evidence is not inferred from an adapter declaration: a declared adapter is only `AVAILABLE` until an explicit execution observes its result.


## Policy evidence boundary

Policy evaluation is a separate deterministic gate. A policy result does not become a permission grant, and a recommendation or worker result cannot override a policy violation.

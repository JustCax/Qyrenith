# Evidence Provider Protocol

Evidence providers are optional, read-oriented extensions. They never authorize a migration by themselves.

A provider should expose these conceptual operations:

- `supports(claim)` — whether the provider can investigate a claim.
- `collect(claim, context)` — return evidence records.
- `verify(claim, evidence)` — return VERIFIED, UNKNOWN, or BLOCKED.
- `describe()` — provider name, version, capabilities, and trust model.

The core control plane remains responsible for policy, ordering, and final verification.

## Evidence record

```json
{
  "id": "stable-id",
  "provider": "example-provider",
  "claim": "target API exists",
  "status": "VERIFIED",
  "confidence": "HIGH",
  "source": "local-target-jar",
  "details": {}
}
```

Providers must not silently turn inference into verification. Conflicting evidence must remain visible.

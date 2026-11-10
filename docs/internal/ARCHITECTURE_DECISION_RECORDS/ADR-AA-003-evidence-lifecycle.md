# ADR-AA-003: One Logical Evidence System with Immutable Lifecycle

**Status:** PROPOSED — reconciled with owner-approved AA-01 decision directions; ADR acceptance pending  
**Original proposal date:** 2026-11-04  
**Reconciliation date:** 2026-11-10  
**Scope:** QDAS evidence journal, immutable artifacts, provenance, integrity, freshness, retention, and reporting

## Context

Evidence may be incomplete, corrected, invalidated by changed inputs, superseded by newer observations, or retained for audit. Rewriting historical evidence makes prior decisions difficult to reconstruct. Multiple independent ledgers create competing sources of truth.

A digest detects a mismatch relative to a trusted digest; it does not establish that an observation was truthful or its producer qualified. The owner-approved AA-D2 direction requires one logical evidence system, while physical backend selection remains deferred pending comparative evaluation.

## Decision proposal

Qyrenith MUST expose one logical evidence system with three cooperating roles:

1. **Canonical QDAS event journal:** the authoritative ordered record of lifecycle events, evidence acceptance, invalidation, supersession, qualification, authorization, and decision references.
2. **Content-addressed immutable artifact store:** stores immutable raw and normalized evidence artifacts by digest, with media/schema identity, provenance, size bounds, and retention metadata.
3. **Optional rebuildable query index:** accelerates lookup but is non-authoritative, rebuildable from the journal/artifacts, and cannot independently establish evidence existence or validity.

These are logical roles, not a mandate for three independent services/databases. There MUST NOT be a second evidence ledger, independent verdict store, or competing evidence authority.

Accepted evidence is logically immutable. Corrections, invalidations, revocations, and replacements use new events/artifacts referencing prior identities; accepted records are not silently rewritten. Records bind to relevant project snapshot/scope, producer/checker identity and version, extension digest/qualification where applicable, plan/profile, policy/evaluator versions, relevant inputs, environment, observation time, result semantics, and integrity metadata.

Persistence MUST provide an atomic acceptance boundary. Interrupted/partial writes remain incomplete and cannot satisfy policy. The storage contract defines stable identifiers, deduplication, ordering, concurrency, crash recovery, integrity validation, export/restore, retention, privacy, and secure deletion.

The physical backend is DEFERRED. Candidates must be compared against common measurable criteria:
- atomicity and durability;
- crash/interruption recovery and fault injection;
- concurrent writer/reader semantics and ordering;
- portability across supported OS/filesystems;
- privacy, access control, retention, and secure deletion;
- export, backup, restore, and disaster recovery;
- performance and bounded resource use;
- corruption detection and rebuild/recovery procedures.

A future external trust anchor/signature mechanism requires a separate key-management and threat-model decision. Content addressing does not imply publisher identity or observation truth.

## Alternatives considered

1. Mutable latest-result rows as the sole history — rejected because previous decisions lose their original support.
2. Append-only unstructured text log as the whole model — rejected because typed validation, provenance, bounded artifacts, and rebuildable queries are required.
3. Hash-only evidence — rejected because it does not prove producer identity, truth, or authorization.
4. Multiple independent ledgers — rejected because they create competing authority and inconsistent lifecycle state.
5. Immediate backend selection — deferred until common evaluation and fault-injection evidence exist.

## Consequences

- QDAS owns canonical journal/evidence lifecycle integration.
- RVL and other modules emit evidence into the shared contract; they do not create independent stores.
- Query indexes and reports are derived views and cannot overrule validated journal/artifact records.
- Freshness/invalidation bind to relevant project snapshot, profile, checker/provider version, policy, evaluator, and environment inputs.
- Retention, privacy, export/restore, and secure deletion require explicit policy; immutability does not mean retaining sensitive raw data forever.
- Backend selection remains open until comparison and fault-injection plans are complete.

## Verification requirements

- Interrupted writes cannot appear as complete accepted evidence.
- Tampered artifacts fail integrity validation and cannot satisfy mandatory policy.
- Superseded, expired, revoked, or invalidated evidence remains traceable and cannot silently satisfy a fresh run.
- The query index can be deleted/rebuilt without changing authoritative decisions.
- Concurrency, ordering, duplicate submission, crash recovery, export/restore, and retention are tested against the selected backend.
- No module, extension, report exporter, or provider introduces another evidence authority.
- Raw observations and normalized records retain provenance and schema identity.
- Sensitive-data retention, redaction, export, and deletion behavior are tested.
- Backend choice remains unaccepted until comparative evidence is reviewed.

## Related contracts

- `AA01_OWNER_DECISION_RECORD.md`
- `ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md`
- `QYRENITH_DEVELOPMENT_ASSURANCE_SYSTEM_SPEC.md`
- `EVIDENCE_AND_CONFIDENCE_MODEL.md`
- `REPRODUCIBLE_VERIFICATION_LAB_SPEC.md`
- `REQUIREMENT_TRACEABILITY_MATRIX.md`

This proposal records the logical evidence architecture only; it selects no physical backend and claims no completed persistence implementation.

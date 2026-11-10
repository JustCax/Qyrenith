# Evidence Store Backend Evaluation — Qyrenith 1.2.0

**Status:** ARCHITECTURE EVALUATION PLAN — backend selection DEFERRED  
**Date:** 2026-11-10  
**Decision owner:** Project owner  
**Parent decision:** AA-D2 / ADR-AA-003  
**Implementation:** NOT STARTED

## 1. Decision boundary

The accepted logical model is fixed:

- one canonical QDAS event journal;
- one content-addressed immutable artifact store;
- an optional rebuildable, non-authoritative query index.

This evaluation selects no physical backend. It must not create a second evidence authority, a parallel migration ledger, or a separate verdict store. Existing QDAS and migration assurance ledgers are implementation evidence and candidate starting points, not permission to preserve permanently separate authorities.

A candidate is acceptable only if it can enforce the logical contract, recover safely after interruption, retain exact provenance, and pass the same adversarial acceptance suite.

## 2. Existing implementation baseline

The 1.2.0 branch currently contains two related local ledger implementations:

| Component | Current mechanism | Useful properties | Known design limits / questions |
|---|---|---|---|
| `QdasEventLedger` | Canonical JSONL, sequence numbers, SHA-256 hash chain, file lock, append + flush + fsync, strict verification, bounded file/record sizes | Append-oriented history, tamper detection within retained chain, explicit writer serialization, strict parsing, owner-only permissions on POSIX | One local file; no independent artifact store; hash chain cannot detect whole-store replacement without an external anchor; crash/torn-write and Windows durability semantics need fault tests; current 64 MiB / 100,000-record caps |
| `AssuranceLedger` | Canonical JSONL, hash chain, exclusive lock file, full-file temporary rewrite + fsync + atomic replace + directory fsync on POSIX | Atomic replacement model, chain verification, fail-closed stale-lock behavior | Rewrites full history per append; platform-specific durability/locking needs tests; separate ledger risks competing authority |
| Artifact handling | Evidence references/digests exist in event and migration records; no unified content-addressed immutable artifact store was identified in the inspected contracts | Existing digest and lineage foundations | Need a single artifact identity/retention/export contract and orphan recovery policy |
| Query/index layer | No canonical rebuildable index contract identified in the inspected ledger code | Can be added later without becoming authoritative | Any index must be derivable and disposable |

This is a bounded source review, not a claim that no other persistence code exists elsewhere in the repository.

## 3. Candidate physical designs

### Candidate A — JSONL journal + filesystem content-addressed artifacts

- Canonical append-only event journal remains JSONL.
- Artifacts are written under digest-derived immutable paths.
- Optional indexes are rebuilt from the journal and artifact metadata.
- Append uses a single-writer lock and durable write protocol.

**Strengths:** close to the current QDAS design; transparent/exportable records; simple local/offline operation; artifact files can be streamed and independently hashed.

**Risks/questions:** cross-file commit ordering; torn final journal record; lock semantics across Windows/macOS/Linux and network filesystems; high-volume verification cost; safe compaction/retention; artifact/journal consistency after power loss.

### Candidate B — SQLite event journal + filesystem content-addressed artifacts

- One SQLite database owns canonical event ordering, metadata, and lifecycle references.
- Immutable artifact bytes live in a content-addressed filesystem store.
- SQLite indexes and views remain rebuildable/non-authoritative unless explicitly declared part of the canonical journal contract.

**Strengths:** transactional event metadata, indexed queries, concurrent readers, explicit schema migration; artifacts can remain streamable outside the database.

**Risks/questions:** coordination between durable artifact creation and database commit; WAL/sidecar backup and restore; locking and filesystem behavior across supported platforms; database corruption/recovery; schema migration; orphan artifact cleanup; not all filesystems provide equivalent durability guarantees.

### Candidate C — SQLite journal and artifacts in one database

- Event journal, metadata, and artifact blobs share one transactional database.
- Content digests identify immutable blobs; query indexes are database-derived.

**Strengths:** event-to-artifact references can share one database transaction; simpler consistency boundary; fewer separately coordinated stores.

**Risks/questions:** large blobs may increase database size and backup/restore costs; streaming and partial artifact access; write amplification; WAL growth/checkpoint behavior; retention and secure deletion; single-database portability and recovery characteristics.

### Candidate D — Keep current JSONL journals and add a CAS artifact store without unification

**Status:** NOT ACCEPTABLE as the final architecture.

It may be used only as a temporary migration bridge if one journal is explicitly designated canonical and all other records are imported/referenced through that authority. Permanently maintaining QDAS and migration ledgers as independent authorities would violate AA-D2.

## 4. Mandatory comparison dimensions

Every candidate must be measured against the same requirements. A qualitative preference or feature checklist is insufficient.

| Dimension | Required evidence |
|---|---|
| Atomicity | No accepted event may reference an artifact that was not durably committed; no partial record may be accepted |
| Crash recovery | Process termination and simulated power-loss boundaries at every write/rename/fsync/commit stage; deterministic recovery result |
| Concurrency | Multi-process writers/readers, lock contention, duplicate event IDs, ordering, deadlock, stale-lock recovery |
| Portability | Windows, macOS, Linux; supported filesystem types; explicit unsupported network-filesystem behavior |
| Integrity | Canonical serialization, content digests, hash-chain validation, corruption detection, whole-store replacement limitation |
| Privacy | Owner-only access where supported, secret redaction, data classification, retention, export controls, secure deletion limits |
| Retention | Expiry, legal/owner hold if later required, artifact reference counting, supersession, garbage-collection safety |
| Export/restore | Complete self-describing export, checksums, manifest, restore verification, interrupted restore recovery |
| Performance | Append latency, verify latency, indexed query latency, memory, disk usage, compaction/rebuild time |
| Scalability | Measured behavior at small, medium, and large event/artifact volumes; bounded operation and explicit limit behavior |
| Schema evolution | Forward/backward compatibility rules, migration interruption, rollback or safe read-only fallback |
| Observability | Exact failure category, recovery action, integrity status, and evidence for every lifecycle transition |
| Determinism | Stable record identities and canonical encodings; deterministic replay of decisions from the same accepted inputs |
| Operational simplicity | Backup, restore, support diagnostics, lock recovery, portability, and user-facing repair instructions |

## 5. Required fault-injection matrix

Each candidate must run the same fault points:

1. Before artifact staging.
2. During artifact write.
3. After artifact write but before artifact fsync.
4. After artifact durability but before event creation.
5. During event append/transaction.
6. After event write but before journal/database durability.
7. After event durability but before index update.
8. During index rebuild.
9. During concurrent duplicate submission.
10. During retention/garbage collection.
11. During export.
12. During restore.
13. During schema migration.
14. During process termination while a writer holds a lock.

For every point, prove:
- accepted history remains valid;
- no incomplete event is treated as accepted;
- an orphan artifact is safe and recoverable/collectable;
- a dangling accepted artifact reference is impossible;
- the next write either safely resumes or fails closed;
- recovery never silently rewrites prior accepted evidence.

## 6. Reference transaction protocol to evaluate

Regardless of backend, the implementation design must preserve this logical sequence:

1. Validate project/run identity, schema, permissions, resource limits, and artifact metadata.
2. Write artifacts to a non-authoritative staging area.
3. Verify content digests and enforce size/type limits.
4. Make immutable artifacts durable using the candidate's measured durability protocol.
5. Commit one canonical journal event that references only durable artifact identities.
6. Verify the committed event and lineage.
7. Update optional indexes asynchronously or synchronously as derived data; index failure cannot change the authoritative event result.
8. On recovery, detect and report unreferenced staged/orphan artifacts without inventing accepted events.

The protocol must define exactly which filesystem/database operations are atomic on each supported platform. Do not assume rename, fsync, lock, or WAL behavior is identical across operating systems or filesystems.

## 7. Benchmark and acceptance dataset

Use deterministic synthetic fixtures and retained real-world sanitized fixtures:

- 1,000 events / 10,000 events / 100,000 events;
- small metadata-only events;
- 10 KiB, 1 MiB, and bounded large artifacts;
- repeated identical artifact digests to test deduplication;
- high-cardinality artifact sets;
- concurrent readers and serialized writers;
- deliberately corrupted, truncated, reordered, duplicated, stale, and missing records;
- export/restore of a complete project evidence history.

Record exact runtime, OS, architecture, filesystem, storage medium, process count, dataset digest, command, warm/cold cache condition, repeated measurements, median/tail latency, peak memory, disk footprint, and recovery result. Do not publish a performance claim from a single run.

## 8. Decision rule

A candidate is disqualified if it:
- can accept a journal event before referenced artifacts are durable;
- silently accepts a partial/torn record;
- loses or reorders accepted events under its declared concurrency model;
- cannot recover safely from injected interruption;
- requires network access for normal local operation;
- creates a second evidence or verdict authority;
- cannot export and restore a verifiable complete history;
- has unsupported platform behavior that is reported as successful.

Among candidates that pass every mandatory gate, compare operational simplicity, portability, measured performance, retention/privacy behavior, and maintenance cost. Record the decision and trade-offs in a separate owner-reviewed ADR update. Until then, backend choice remains DEFERRED.

## 9. Open questions deliberately not decided here

- Whether the canonical journal is implemented as JSONL, SQLite, or another measured local transactional store.
- Whether artifacts are filesystem-backed or stored in the same transactional database.
- Exact compaction, archival, retention, and secure-deletion policy.
- Whether external signatures/trust anchors are needed and, if so, the key identity/rotation/revocation model.
- Whether multi-user/shared-host operation is in 1.2.0 scope; no networked or remote evidence service is implied.

## 10. Related contracts

- `ADR-AA-003-evidence-lifecycle.md`
- `AA01_OWNER_DECISION_RECORD.md`
- `EVIDENCE_AND_CONFIDENCE_MODEL.md`
- `QYRENITH_DEVELOPMENT_ASSURANCE_SYSTEM_SPEC.md`
- `REQUIREMENT_TRACEABILITY_MATRIX.md`

No backend is selected and no persistence implementation is authorized by this evaluation plan.

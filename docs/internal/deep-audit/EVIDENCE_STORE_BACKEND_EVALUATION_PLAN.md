# Evidence Store Backend Evaluation Plan — Qyrenith 1.2.0

**Status:** EVALUATION PLAN — NO PHYSICAL BACKEND SELECTED  
**Owner decision basis:** AA-D2, approved 2026-11-10  
**Architecture owner:** QDAS / Evidence plane  
**Implementation status:** NOT STARTED

## 1. Purpose

Select a physical persistence strategy only after measured comparison against one shared acceptance and fault-injection suite. This plan does not change the accepted logical evidence model:

1. QDAS canonical event journal is the sole authoritative ordered history.
2. Content-addressed immutable artifacts hold larger payloads.
3. An optional query index is derived and non-authoritative.
4. An external trust anchor is deferred to a separate owner-approved identity/key-management design.

A database, file format, or index must not create a second source of truth.

## 2. Candidate architectures

### Candidate A — Append-only journal plus content-addressed artifact directory

- Canonical events are stored in a bounded, versioned append-only journal.
- Large evidence payloads are written to a content-addressed artifact directory.
- Event commit protocol must define artifact staging, digest verification, durable rename/fsync, journal append, recovery markers, and orphan cleanup.
- Query acceleration may use a disposable derived index.

**Strengths:** portable, inspectable, easy to export, naturally append-oriented.  
**Risks:** multi-writer coordination, atomicity across journal and artifact files, recovery complexity, and query performance at scale.

### Candidate B — Transactional embedded database as canonical journal

- A single embedded database owns ordered event records, metadata, and transactional references to immutable external artifacts.
- Event ordering, uniqueness, and journal semantics are defined by schema/transactions.
- Artifact bytes remain content-addressed files or immutable blobs and are committed through a recoverable protocol.

**Strengths:** mature transactions, indexes, concurrency controls, and query support.  
**Risks:** database format/version migration, locking and WAL behavior across platforms, backup consistency, corruption recovery, and operational portability.

### Candidate C — Canonical journal plus transactional derived database index

- The append-only journal remains authoritative.
- An embedded database stores only a rebuildable query projection.
- Every index row is traceable to journal sequence/digest and can be regenerated from the journal.

**Strengths:** preserves portable canonical history while supporting efficient queries.  
**Risks:** dual-write/rebuild complexity, index lag, invalidation bugs, and accidental authority leakage if callers trust the index.

Candidate C is not allowed to become a second canonical event store. It is a projection only.

## 3. Mandatory evaluation dimensions

| Dimension | Required measurements and failure cases |
|---|---|
| Atomicity | Event/artifact commit boundaries, crash between every step, partial records, orphan artifacts, duplicate/reordered events |
| Crash recovery | Process kill, OS restart simulation where practical, truncated journal, corrupt page/segment, disk full, interrupted compaction |
| Concurrency | Single writer, multiple readers, competing writers, lock timeout, stale lock, concurrent export and verification |
| Portability | Windows, Linux, macOS; filesystem semantics; path/case behavior; supported Python versions |
| Privacy | Secret redaction before persistence, data minimization, scoped retention, deletion policy, metadata leakage |
| Retention | Expiry, supersession, invalidation, archival, bounded storage, safe pruning without breaking lineage |
| Export/restore | Deterministic portable export, integrity verification, restore into clean environment, schema migration |
| Fault injection | Write failure, fsync/rename failure, permission loss, process termination, malformed payload, hash mismatch |
| Performance | Append latency, lookup latency, replay/rebuild time, storage growth, peak memory, large artifact handling |
| Maintainability | Standard-library compatibility, dependency/licensing footprint, format observability, migration burden |

## 4. Common workload and fault-injection suite

All candidates must process the same deterministic synthetic workload:
- small frequent execution events;
- large stdout/stderr and structured reports;
- many small artifacts and a small number of large artifacts;
- long lineage chains and branching/supersession;
- multiple projects/workspaces;
- repeated reads, filters, and evidence replay;
- schema-version upgrades;
- concurrent read/write pressure;
- retention and redaction operations.

Fault injection must occur at every durable boundary, including:
1. artifact temporary-file creation;
2. artifact byte write;
3. artifact flush/fsync;
4. artifact finalization/rename;
5. event serialization;
6. journal/database transaction start;
7. event persistence;
8. transaction commit or journal flush/fsync;
9. index projection update;
10. export and restore.

For each injected failure, the system must recover to either a complete valid event or an explicitly incomplete/rejected state. It must never manufacture a successful evidence record from a partial write.

## 5. Measurement and decision rules

- Use the same hardware, OS image, Python version, workload seed, artifact set, and measurement protocol.
- Run warm and cold cases; repeat enough times to report median and tail latency, not a single best result.
- Record raw measurements, tool versions, environment fingerprint, test revision, and artifact digests.
- Reject any candidate that violates evidence immutability, atomicity, fail-closed recovery, privacy, or export/restore requirements, regardless of speed.
- Compare complexity and operational burden as well as throughput.
- Do not optimize for theoretical scale before a measured workload justifies it.
- Record a decision ADR with results, rejected alternatives, migration strategy, recovery procedures, and limitations.

## 6. Acceptance criteria

- One shared test suite runs unchanged against each candidate.
- Every fault-injection point produces a deterministic, explainable recovery result.
- Canonical evidence lineage survives export/restore and schema migration.
- Derived indexes can be deleted and rebuilt without changing canonical decisions.
- Secret values are not persisted in raw or derived artifacts.
- Concurrent access cannot duplicate, reorder, overwrite, or silently lose accepted events.
- Supported platform behavior is measured and documented.
- The selected design has a documented backup, recovery, retention, redaction, and migration procedure.

## 7. Deferred decisions

No physical backend is selected by this document. The choice remains open until the comparative suite and owner review are complete. External signatures/anchors, cloud storage, remote synchronization, and multi-host distributed writes are outside the first 1.2.0 mandatory path unless separately approved.

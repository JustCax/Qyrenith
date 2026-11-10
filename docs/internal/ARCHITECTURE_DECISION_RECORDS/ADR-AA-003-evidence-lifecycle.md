# ADR-AA-003: Immutable Evidence Lifecycle Under the Canonical QDAS Journal

**Status:** RECONCILED PROPOSAL — OWNER ACCEPTANCE REQUIRED  
**Revision date:** 2026-11-10  
**Scope:** QDAS event journal, evidence artifacts, lineage, retention, and assurance decisions  
**Implementation status:** NOT STARTED

## Context

Evidence can be incomplete, corrected, invalidated by changed inputs, or superseded by newer observations. Rewriting accepted evidence in place destroys the ability to reconstruct earlier decisions. At the same time, a digest or local hash chain proves neither that an observation was truthful nor that its producer was authentic.

Qyrenith already designates QDAS as the canonical event-journal authority and defines an evidence lineage model. AA must reuse those contracts rather than create another ledger.

## Proposed decision

Qyrenith uses one logical evidence system:

1. **Canonical QDAS event journal:** the sole authoritative ordered record for events, evidence references, lifecycle transitions, invalidations, and decision lineage.
2. **Content-addressed immutable artifact store:** stores larger payloads such as logs, reports, manifests, and test artifacts under cryptographic content digests. The journal binds each artifact's digest, media type, size, scope, provenance, and retention classification.
3. **Optional rebuildable query index:** derived from validated journal/artifact records, non-authoritative, and safe to delete/rebuild without changing the historical record.
4. **Optional future external trust anchor:** signed checkpoints or external anchoring may be considered only after a separate owner-approved identity/key-management and threat-model design.

Accepted evidence is logically immutable. Corrections, invalidations, supersession, and replacement are new records/events referencing prior records; accepted history is not silently overwritten.

Every evidence record MUST bind, as applicable, project/snapshot identity, producer/checker identity and version, plan/profile and policy versions, exact scope, relevant inputs, environment/toolchain, observation time, normalized outcome, raw observation reference, provenance, parent lineage, integrity metadata, and freshness/retention information.

## Integrity, authenticity, and truth

These are separate claims:
- **Integrity:** retained bytes match the recorded digest and structural contract.
- **Authenticity:** the producer identity and origin are established under an explicit trust model.
- **Truth/validity:** the observation is sufficiently supported by independent evidence and the declared oracle.

A digest or local hash chain may detect accidental or partial modification relative to retained trusted metadata. It does not authenticate the writer and does not protect against an actor able to replace the entire unanchored store.

## Atomicity and recovery

A logical event and its required artifact references must become visible atomically or remain explicitly incomplete. Interrupted writes, partial artifacts, missing parents, duplicate IDs, sequence gaps, conflicting records, or failed digest validation MUST NOT be accepted as complete evidence.

The storage design must support bounded crash recovery, concurrency semantics, canonical serialization, schema evolution, export/restore, privacy, redaction, and retention. Backend selection is deliberately deferred until candidate backends are measured against the same fault-injection and portability suite.

## Alternatives considered

1. **Mutable latest-result row:** rejected; historical decisions lose their original basis.
2. **Unstructured append-only log as the only representation:** rejected; structured contracts, artifact references, and validation are still required.
3. **Hash-only integrity model:** rejected; digest equality does not establish source authenticity or observation truth.
4. **Separate AA evidence database/ledger:** rejected; it creates a second authority and inconsistent histories.
5. **Immediate backend selection:** deferred; no backend is accepted without comparative recovery, atomicity, concurrency, portability, and privacy evidence.

## Consequences

- QDAS remains the single evidence authority.
- Evidence lifecycle operations are append-only and lineage-preserving.
- Large artifacts can be stored separately without becoming a second source of truth.
- Query indexes can be rebuilt without changing canonical history.
- Retention and redaction must be explicit and auditable.
- Physical backend choice remains open pending measured comparison.

## Acceptance criteria

- Interrupted persistence cannot produce a valid complete evidence record.
- Tampering, digest mismatch, duplicate/reordered events, missing parents, and incomplete artifacts fail closed.
- Superseded or invalidated evidence remains traceable and cannot silently satisfy a fresh profile.
- Evidence freshness is evaluated against exact project, tool, policy, and profile identities.
- Export/restore and schema migration preserve lineage and canonical meaning.
- Redaction prevents secret persistence while retaining an auditable redaction event.
- Rebuilding the optional index cannot alter canonical decisions.
- Tests distinguish integrity, authenticity, and independent verification.

## Deferred

The physical storage backend, external trust anchor, exact retention/deletion policy, schema/API/CLI names, and concurrency implementation remain undecided. This proposal does not claim that any of them is implemented.

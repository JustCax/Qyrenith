# ADR-AA-003: Immutable Evidence Records with Explicit Supersession

**Status:** Proposed for AA-01 acceptance  
**Date:** 2026-11-04  
**Scope:** Evidence and provenance subsystem

## Context

Verification evidence may be incomplete, corrected, invalidated by changed inputs, or superseded by newer observations. Rewriting prior evidence in place would make it difficult to reconstruct why an earlier decision was reached.

A digest can detect a mismatch relative to a trusted digest, but it does not establish that the original checker or observation was truthful.

## Decision

Accepted evidence is logically immutable. Corrections, invalidations, and replacements are represented by new records or explicit supersession/invalidation events referencing the prior record.

Each record is bound to project scope, checker identity/version, plan and policy versions, relevant inputs, environment, observation time, result, and integrity metadata.

Persistence must use an atomic commit strategy. Partial writes must remain incomplete and must never be accepted as valid evidence.

## Alternatives considered

1. **Mutable latest-result row:** rejected because historical decisions lose their supporting evidence.
2. **Append-only unstructured log only:** rejected as the sole model because record validation and indexed lookup need explicit structure.
3. **Hash-only integrity model:** rejected because a digest does not prove observation authenticity or checker honesty.

## Consequences

- storage and retention design must support stable IDs and supersession;
- reports can reconstruct decisions over time;
- schema migration must preserve historical records;
- storage backend selection remains deferred until consistency, portability, privacy, and recovery are evaluated.

## Verification

- interrupted persistence cannot produce a valid complete record;
- post-acceptance tampering is detected against a trusted digest;
- superseded evidence remains traceable and cannot silently satisfy a fresh plan;
- incomplete evidence is rejected.

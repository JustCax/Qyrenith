# Evidence and Confidence Model

## 1. Purpose

This specification defines how Qyrenith represents observations, claims, findings, verification outcomes, and confidence across audit, migration, and QDAS workflows.

## 2. Evidence record

Every evidence item MUST include a stable identifier, schema version, evidence kind, producer identity/version, project and revision identity, scope, observation timestamp, collection command or method, result status, content digest, and provenance. Optional fields include bounded artifact locator, toolchain fingerprint, source location, parent evidence IDs, and retention classification.

Evidence records must be canonicalized before hashing. A digest identifies content; it does not prove truth, authorship, completeness, or trusted collection.

## 3. Claim lifecycle

Knowledge and findings use explicit statuses: OBSERVED, INFERRED, UNKNOWN, VERIFIED, CONFLICTED, and STALE. Status transitions require recorded reasons and evidence. OBSERVED or INFERRED claims MUST NOT be promoted automatically. Conflicting claims remain visible and block decisions within their exact overlapping scope.

## 4. Confidence

Confidence is not a substitute for evidence. Each hypothesis reports:
- confidence category or calibrated score;
- supporting evidence;
- contradicting evidence;
- assumptions;
- missing observations;
- scope and expiry;
- calibration dataset/version, when numeric calibration is claimed.

Do not present a numeric probability unless it is calibrated against a documented dataset. A heuristic score must be labeled heuristic and must not be interpreted as probability.

## 5. Verdict requirements

Every verdict names the policy, scope, revision, toolchain, checks, exclusions, and evidence set. A PASS requires all mandatory checks to be executed and supported. Missing evidence yields UNKNOWN/INCONCLUSIVE/BLOCKED, not PASS. A partial audit must state exact coverage and omitted capabilities.

## 6. Integrity and retention

Use append-only records and canonical digests. Hash-chain or Merkle-style structures may detect modification, but a local actor able to replace the whole store can rebuild an unanchored chain. External anchoring/signatures are separate capabilities and require a defined identity/trust model. Retention and redaction rules must prevent secrets from being persisted in logs.

## 7. Evidence lineage

Evidence lineage must connect input → tool invocation → raw observation → normalized result → finding/claim → decision → final report. Derived evidence must reference its parents and transformation version. QDAS repair lineage follows the exact chain specified in its dedicated specification.

## 8. Acceptance tests

Test duplicate IDs, malformed digests, invalid timestamps, future evidence, expired claims, missing parent records, cyclic lineage, changed tool versions, redaction failures, oversized artifacts, tampered chains, and incomplete mandatory evidence. Verify that each case fails closed.

## 9. Non-claims

A green badge, digest, hash chain, reviewer string, or self-reported tool result alone is not independent verification or authenticated identity.

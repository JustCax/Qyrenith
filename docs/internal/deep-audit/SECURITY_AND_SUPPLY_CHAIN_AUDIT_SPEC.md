# Security and Supply-Chain Audit Specification

## 1. Objective
Provide native, evidence-backed security review of source, configuration, dependencies, build workflows, artifacts, and execution boundaries.

## 2. Requirements
- **SS-01 Threat modeling:** assets, actors, trust boundaries, abuse cases, and residual risks per project profile.
- **SS-02 Source security:** native rules for dangerous APIs, injection paths, unsafe deserialization, path traversal, weak randomness, secret exposure, and authorization mistakes where language semantics are supported.
- **SS-03 Taint paths:** source/sink/sanitizer reasoning linked to static-analysis evidence.
- **SS-04 Secrets:** detect likely credentials without storing secret values; redact findings and minimize false disclosure.
- **SS-05 Dependency inventory:** parse supported manifests/lockfiles and resolve direct/transitive dependency identity where available.
- **SS-06 Vulnerability knowledge:** importable, versioned advisory records with source, publication time, affected ranges, and freshness. No network access or automatic trust promotion by default.
- **SS-07 Integrity:** validate checksums, signatures when available, lockfile consistency, and artifact provenance; distinguish missing signature from invalid signature.
- **SS-08 Build pipeline:** inspect workflow permissions, mutable action references, untrusted pull-request execution, artifact handling, and secret exposure.
- **SS-09 Configuration:** detect insecure defaults, overly broad permissions, unsafe debug settings, and policy drift.
- **SS-10 License and provenance:** report declared license/provenance gaps without pretending automated text matching is legal advice.
- **SS-11 QDAS integration:** review repair patches, changed dependencies, workflow/config changes, and permission escalation.
- **SS-12 Reporting:** severity, exploitability assumptions, evidence, remediation guidance, confidence, and accepted-risk record.

## 3. Security posture
Do not equate absence of findings with security. Report scanned assets, unsupported formats, dependency resolution coverage, freshness, and excluded scope. Network-based enrichment is explicit opt-in and must be recorded.

## 4. Acceptance
Fixtures include known-bad and known-good patterns, obfuscated secrets, false-positive examples, vulnerable version ranges, lockfile mismatch, mutable workflow refs, permission escalation, path traversal, and malicious manifests. Test redaction and ensure no secret value is persisted in reports or logs.

# Research and Standards Alignment — Qyrenith 1.2.0

**Status:** Research baseline for design review — not certification or compliance  
**Research cut-off:** 2026-11-10

## 1. Method

Prioritize primary specifications and project-maintained documentation. Distinguish normative standards, maturity frameworks, operational guidance and Qyrenith design decisions. A standards mapping is not a compliance certificate. Pin exact version/source/date in adapters and reports.

## 2. Research mapping

| Source | Contribution | Qyrenith use | Limitation |
|---|---|---|---|
| NIST SP 800-218 SSDF 1.1 | Secure development practices across prepare, protect, produce and respond | Security lifecycle, provenance, risk/requirement traceability, vulnerability response | Framework guidance, not tool certification |
| NIST SP 800-218 Rev.1 IPD (2025) | Draft evolution for secure and reliable development | Track future changes | Initial public draft, not final baseline |
| SLSA v1.2 | Source/build tracks, provenance and increasing supply-chain guarantees | Build provenance, artifact trust and integrity | SLSA level is scoped; not identical to reproducibility or product security |
| in-toto Attestation Framework v1.2 | Predicate, statement, envelope and bundle | Interoperable attestations; separate subject, predicate and signer | Structure does not make signer trustworthy |
| Reproducible Builds | Environment capture, deterministic inputs, timestamps, paths, archive ordering and verification | Reproducibility manifests, clean rebuilds and mismatch analysis | External state/hardware may prevent exact reproduction |
| OpenTelemetry semantic conventions | Common names for traces, metrics, logs, profiles and resources | Telemetry normalization and correlation | Does not prove causal relationship or data quality |
| CycloneDX 1.7 | BOM, vulnerability, VEX and attestation exchange | SBOM/VEX interoperability | Imported BOM needs completeness, provenance and freshness checks |
| SPDX 3.0/3.0.1 | BOM model for software, AI, data, licenses, provenance, integrity and relationships | SBOM, license and provenance interchange | Format validity does not prove completeness or legal correctness |
| OWASP SAMM 2.0 | Security maturity across governance, design, implementation, verification and operations | Security maturity and gap assessment | Organizational model, not product certification |
| OWASP API Security Top 10 2023 | API risks: authorization, resource consumption, SSRF, inventory and more | API threat/test categories | Awareness taxonomy, not complete API test specification |
| WCAG 2.2 | Accessibility success criteria and conformance model | UI checks, reporting and human review requirements | Automation alone cannot establish full conformance |
| OpenSSF Scorecard | Automated checks for selected open-source security practices | Optional external signal and comparison | Limited signal, not substitute for native analysis |

## 3. Design consequences

### Security lifecycle
Map SSDF/SAMM practices into requirements, design, implementation, verification, operations and response. Link findings to assets, threat assumptions, affected versions, remediation and post-fix evidence.

### Provenance, integrity and authenticity
SLSA/in-toto demonstrate that artifact identity, build process, signer identity and trust policy are distinct. A digest, local hash chain, reviewer string or imported VERIFIED label is not authenticated provenance.

### Reproducibility
Capture timestamps, filesystem ordering, environment, paths, locale, timezone and toolchain. Define equivalence classes for build bytes, artifact structure, function, behavior, diagnostics and experiments.

### Telemetry
Normalize with OpenTelemetry conventions while preserving source identity, sampling gaps, clock quality and transformation lineage. Correlation is not causation.

### BOM interoperability
CycloneDX/SPDX support exchange, not automatic security verdicts. Independently validate scope, completeness, digest, source and freshness; retain provider conflicts.

### Maturity
Keep scores scoped by project, version, capability and evidence. Do not collapse missing coverage into one universal score.

### Accessibility
Separate automated checks from manual and assistive-technology review. Mark untested criteria explicitly.

## 4. Interoperability policy

Prefer published schemas; preserve imported raw documents/digests; normalize without losing original fields; pin schema/spec versions; treat imports as untrusted; validate signature, signer, trust, subject digest, scope, freshness and completeness separately; keep Qyrenith's internal evidence schema authoritative; no implicit network access or mandatory third-party runtime dependency.

## 5. Source register

1. NIST SSDF v1.1: https://csrc.nist.gov/pubs/sp/800/218/final
2. NIST SSDF Rev.1 Initial Public Draft: https://csrc.nist.gov/pubs/sp/800/218/r1/ipd
3. NIST SSDF project: https://csrc.nist.gov/projects/ssdf
4. SLSA v1.2: https://slsa.dev/spec/v1.2/
5. SLSA provenance: https://slsa.dev/spec/v1.2/provenance
6. SLSA build track: https://slsa.dev/spec/v1.2/build-track-basics
7. in-toto attestation: https://github.com/in-toto/attestation/blob/main/spec/README.md
8. Reproducible Builds: https://reproducible-builds.org/docs/
9. OpenTelemetry semantic conventions: https://opentelemetry.io/docs/concepts/semantic-conventions/
10. CycloneDX: https://github.com/CycloneDX/specification
11. SPDX: https://spdx.dev/use/specifications/
12. OWASP SAMM: https://owaspsamm.org/model/
13. OWASP API Top 10: https://devguide.owasp.org/en/07-training-education/07-api-top-ten/
14. WCAG: https://www.w3.org/WAI/standards-guidelines/wcag/
15. OpenSSF Scorecard: https://openssf.org/projects/scorecard/

## 6. Maintenance

Review this register each release cycle and when adapters consume changed schemas. Label drafts/proposals as such, preserve superseded mappings and document migrations. Research informs requirements; it does not authorize architecture changes or implementation scope.

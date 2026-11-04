# Qyrenith 1.2.0 Implementation and Acceptance Plan

## 1. Release principle

1.2.0 is complete only when all accepted requirements across the seventeen normative specifications are implemented, tested, integrated, documented, and supported by retained evidence. The deep-audit README is the navigation index. A specification, stub, placeholder, TODO, or passing narrow unit test does not constitute feature completion.

## 2. Mandatory sequence

### Phase 0 — Documentation baseline
- Create and cross-link all seventeen normative specifications and the specification index.
- Maintain `REQUIREMENT_TRACEABILITY_MATRIX.md` as the authoritative requirement-to-implementation/test/evidence/dependency/status map.
- Resolve contradictions with existing public/internal docs.
- Review all security, trust, permission, isolation, and non-claim language.
- Keep internal specifications out of public package contents unless separately approved.

### Phase 1 — Finish existing migration-platform work
- Audit migration identity, transition validation, knowledge catalog, planner, worker contracts, authorization, ledger, snapshots, and workspace copying.
- Close known CI failures, including Windows newline-sensitive subprocess tests.
- Reconcile PR description with implemented workspace API and remaining limitations.
- Resolve subprocess timeout/stdin/output-limit issues and command-path validation bypasses.
- Review environment allowlisting, worker first-run approval, adapter trust, symlink/race behavior, concurrent access, and failure cleanup.
- Integrate only where acceptance tests prove safety; retain explicit non-claims otherwise.
- Re-run complete 1.1.0 regression suite and the full platform matrix.

### Phase 2 — QDAS foundation
- Implement event schema and ingestion.
- Implement failure taxonomy and evidence lineage.
- Implement root-cause hypothesis contracts and repair planning.
- Integrate exact snapshot and reproducible lab identities.
- Add approval-scoped isolated repair execution.
- Add regression-preservation checks, anti-false-fix checks, bounded retries, and safe-stop states.
- Demonstrate disposable fixture repair and independent external verification.

### Phase 3 — Remaining fourteen capability modules
Implement each module in small dependency-ordered slices. For every slice: QDAS capture → plan → approval → implementation → targeted tests → full regression → static/security audit → diff review → evidence record. QDAS assists but does not self-certify its own changes.

## 3. Capability modules

The fourteen capability modules after QDAS are:
1. Static and semantic analysis.
2. Dynamic and behavioral audit.
3. Formal verification and bounded symbolic execution.
4. Fuzzing and property testing.
5. Security and supply-chain audit.
6. Root-cause and cross-module analysis.
7. Universal compatibility and failure knowledge.
8. Reproducible verification lab.
9. Meta-audit and benchmark.
10. Evidence and confidence model.
11. Language and domain adapters.
12. Audit maturity and coverage.
13. Migration platform integration.
14. Integrated reporting, orchestration, and acceptance controls.

The master architecture and this plan are governance documents. The migration integration and reporting specifications define the final two capability modules. The README is an index, not a runtime module.

## 4. Requirement traceability

Each requirement must have a stable ID and a traceability row containing:
- specification and requirement ID;
- implementation package/API/CLI;
- positive test and negative/adversarial test;
- evidence artifact type;
- dependencies and blocking prerequisites;
- status: NOT_STARTED, IN_PROGRESS, IMPLEMENTED, TESTED, VERIFIED, BLOCKED;
- reviewer and verification timestamp.

No requirement may be marked VERIFIED solely because its code exists or its unit tests pass.

## 5. Definition of done

A module is done only when:
- all normative requirements have implementation or owner-approved scope removal;
- supported inputs and unsupported cases are explicit;
- positive, negative, boundary, regression, and adversarial tests pass;
- resource limits and failure states are exercised;
- evidence lineage is complete;
- docs, schemas, CLI help, and package manifests agree;
- no critical/high unresolved issue remains without explicit accepted risk;
- independent validation is complete where the claim requires it.

## 6. Release blockers

Any failing required CI job, unresolved critical/high security defect, false PASS path, silent downgrade, missing evidence, unbounded execution path, package-content mismatch, broken compatibility contract, or undocumented public behavior blocks release.

## 7. Governance

Work occurs on `feature/1.2.0-universal-migration-core`. Do not merge to main, tag, publish to PyPI, or create a public release without explicit owner approval. Changes to this plan or architecture require a decision record and updated traceability.

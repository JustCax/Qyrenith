# Qyrenith 1.2.0 Deep Audit Specifications

This directory contains eighteen normative engineering specifications for the 1.2.0 deep-audit and development-assurance work, plus navigation, decision, and traceability records. All documents are internal design/implementation material; they are not a claim that the described capabilities are already implemented.

## Required delivery order

1. **Documentation baseline:** review and reconcile this specification set.
2. **Existing work completion:** audit and finish the migration-platform foundation and known 1.1.0/1.2.0 regression issues.
3. **QDAS first:** implement and independently validate the Qyrenith Development Assurance System.
4. **Fourteen remaining capability modules:** implement with QDAS-assisted capture, planning, testing, auditing, and evidence recording.
5. **Integrated acceptance:** required platform verification through CI or an owner-approved independent local/external runner, package verification, independent review, and owner approval.

## Specification index

| Document | Scope |
|---|---|
| [Master architecture](DEEP_AUDIT_MASTER_ARCHITECTURE.md) | System planes, trust boundaries, global invariants, verdict vocabulary |
| [QDAS](QYRENITH_DEVELOPMENT_ASSURANCE_SYSTEM_SPEC.md) | Failure-to-repair-to-reverification development assurance |
| [Static and semantic analysis](STATIC_AND_SEMANTIC_ANALYSIS_SPEC.md) | Native parsing, symbols, data flow, rules, impact |
| [Dynamic and behavioral audit](DYNAMIC_AND_BEHAVIORAL_AUDIT_SPEC.md) | Scenarios, runtime behavior, lifecycle, concurrency |
| [Formal verification](FORMAL_VERIFICATION_AND_SYMBOLIC_EXECUTION_SPEC.md) | Contracts, bounded state exploration, symbolic constraints |
| [Fuzzing and property testing](FUZZING_AND_PROPERTY_TESTING_SPEC.md) | Generators, properties, shrinking, metamorphic tests |
| [Security and supply chain](SECURITY_AND_SUPPLY_CHAIN_AUDIT_SPEC.md) | Source, dependencies, secrets, workflows, provenance |
| [Root cause and cross-module analysis](ROOT_CAUSE_AND_CROSS_MODULE_ANALYSIS_SPEC.md) | Dependency graph, impact, hypotheses, failure correlation |
| [Universal knowledge and compatibility](UNIVERSAL_KNOWLEDGE_AND_COMPATIBILITY_SPEC.md) | Scoped compatibility and failure knowledge |
| [Reproducible verification lab](REPRODUCIBLE_VERIFICATION_LAB_SPEC.md) | Pinned commands, isolation levels, repeatable execution |
| [Migration platform integration](MIGRATION_PLATFORM_INTEGRATION_SPEC.md) | End-to-end typed migration, authorization, execution, recovery |
| [Meta-audit and benchmarks](META_AUDIT_AND_BENCHMARK_SPEC.md) | Mutation fixtures, false positives, blind spots, metrics |
| [Evidence and confidence](EVIDENCE_AND_CONFIDENCE_MODEL.md) | Provenance, confidence, verdict evidence, integrity |
| [Language and domain adapters](LANGUAGE_AND_DOMAIN_ADAPTER_SPEC.md) | Native frontends, adapter contracts, capability qualification |
| [Extensibility and supportability](EXTENSIBILITY_AND_SUPPORTABILITY_SPEC.md) | Versioned extension ecosystem, qualification, exact support scope, lifecycle, compatibility and trust |
| [Audit maturity and coverage](AUDIT_MATURITY_AND_COVERAGE_MODEL.md) | Multidimensional support and honest maturity |
| [Integrated reporting and orchestration](INTEGRATED_REPORTING_AND_ORCHESTRATION_SPEC.md) | Dependency scheduling, verdicts, coverage, report exports |
| [Implementation and acceptance plan](QYRENITH_1_2_0_IMPLEMENTATION_AND_ACCEPTANCE_PLAN.md) | Phase gates, traceability, definition of done |

[Requirement Traceability Matrix](REQUIREMENT_TRACEABILITY_MATRIX.md) maps every stable requirement ID to its planned implementation target, acceptance tests, evidence artifact, dependencies, and conservative current status. It is the working status ledger and must be updated alongside implementation.

## Requirement families

- **DA-01:** master architecture and global trust/safety invariants.
- **DA-02:** static and semantic analysis (SA-01..SA-13).
- **DA-03:** dynamic and behavioral audit (DB-01..DB-12).
- **DA-04:** formal verification (FV-01..FV-10).
- **DA-05:** fuzzing and property testing (FP-01..FP-10).
- **DA-06:** security and supply-chain audit (SS-01..SS-12).
- **DA-07:** root-cause and cross-module analysis (RC-01..RC-11).
- **DA-08:** universal knowledge and compatibility (UK-01..UK-13).
- **DA-09:** reproducible verification lab (RVL sections and acceptance tests).
- **DA-10:** meta-audit and benchmark (MA-01..MA-12).
- **DA-11:** evidence and confidence model.
- **DA-12:** language and domain adapters (LA-01..LA-13).
- **DA-13:** audit maturity and coverage (MC-01..MC-08).
- **DA-14:** implementation plan, migration integration (MI-01..MI-15), and integrated reporting (IR-01..IR-14).
- **QDAS-01..QDAS-22:** dedicated QDAS requirements.

## Global completion rule

Every requirement must map to implementation, positive test, negative/adversarial test, evidence artifact, and an explicit status. Documentation alone never satisfies an implementation requirement. Missing mandatory evidence is a blocker, not a pass.

## Universal software intelligence expansion

These proposals extend and map onto the existing five-plane architecture; they do not silently amend accepted architecture or claim implementation.

| Document | Scope |
|---|---|
| [Universal software intelligence architecture](UNIVERSAL_SOFTWARE_INTELLIGENCE_ARCHITECTURE.md) | Six capability pillars mapped onto existing planes; Deep Audit, Targeted Analysis and Continuous Assurance |
| [Diagnostic intelligence expansion](DIAGNOSTIC_INTELLIGENCE_EXPANSION_SPEC.md) | 27 diagnostic domains and 81 proposed requirements |
| [Diagnostic capability coverage matrix](DIAGNOSTIC_CAPABILITY_COVERAGE_MATRIX.md) | Initial inventory-level capability map and evidence gaps |
| [Reproducibility and cross-environment assurance](REPRODUCIBILITY_AND_CROSS_ENVIRONMENT_ASSURANCE_SPEC.md) | Reproducibility classes, manifests, independent replay and environment matrices |
| [Optimization and repair intelligence](OPTIMIZATION_AND_REPAIR_INTELLIGENCE_SPEC.md) | Controlled optimization experiments, multi-objective decisions and safe repair |
| [Research and standards alignment](RESEARCH_AND_STANDARDS_ALIGNMENT.md) | Primary research sources and interoperability consequences |
| [Advanced Assurance integration and PR #3 review](ADVANCED_ASSURANCE_INTEGRATION_AND_PR3_REVIEW.md) | AA-01 crosswalk, requirement mapping, proposed ADR reconciliation and PR disposition |
| [AA-01 owner decision design](ADVANCED_ASSURANCE_AA01_DECISION_DESIGN.md) | Owner-approved decisions and their semantics, consequences, and acceptance conditions |
| [AA-01 owner decision record](AA01_OWNER_DECISION_RECORD.md) | Explicit approval scope, accepted decisions, deferred details, and governance boundaries |

The six pillars are a product-level grouping, not a replacement for control, analysis, execution, knowledge and evidence planes. The 27 domains are a target envelope; delivery remains dependency- and acceptance-gated.

## Additional requirement families

- **DI-001..DI-081:** proposed diagnostic requirements, three per domain.
- **RCA-01..RCA-12:** proposed reproducibility requirements.
- **OI-01..OI-10:** proposed optimization requirements.
- **AA-REQ-*** (70 IDs): proposed cross-cutting Advanced Assurance requirements from PR #3; the seven owner decision directions do not automatically accept this entire requirement family.
- **EX-001..EX-016:** accepted extensibility/supportability requirements; implementation remains NOT_STARTED until evidence is produced.

RCA, OI and the 70 PR #3 AA requirement IDs remain `PROPOSED` unless separately accepted. The AA-01 decision directions and EX-001..EX-016 design requirements are owner-approved; documentation approval does not establish implementation or verification.

## CI-disabled verification constraint

GitHub Actions workflow files are intentionally absent from the active 1.2.0 branch at this update. Do not restore or trigger Actions without explicit owner approval. This does not waive release verification: required test/platform evidence must be produced through an approved independent local or external process and retained with exact revision, toolchain, environment and artifact digests. Historical Actions runs are not evidence for a newer commit.

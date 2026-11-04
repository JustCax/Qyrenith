# Qyrenith 1.2.0 Deep Audit Specifications

This directory contains the normative engineering specifications for the 1.2.0 deep-audit and development-assurance work. All documents are internal design/implementation material; they are not a claim that the described capabilities are already implemented.

## Required delivery order

1. **Documentation baseline:** review and reconcile this specification set.
2. **Existing work completion:** audit and finish the migration-platform foundation and known 1.1.0/1.2.0 regression issues.
3. **QDAS first:** implement and independently validate the Qyrenith Development Assurance System.
4. **Fourteen remaining capability modules:** implement with QDAS-assisted capture, planning, testing, auditing, and evidence recording.
5. **Integrated acceptance:** external CI, package verification, independent review, and owner approval.

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
- **QDAS-01..QDAS-21:** dedicated QDAS requirements.

## Global completion rule

Every requirement must map to implementation, positive test, negative/adversarial test, evidence artifact, and an explicit status. Documentation alone never satisfies an implementation requirement. Missing mandatory evidence is a blocker, not a pass.

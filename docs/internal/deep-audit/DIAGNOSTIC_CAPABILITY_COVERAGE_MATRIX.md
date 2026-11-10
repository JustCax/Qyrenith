# Diagnostic Capability Coverage Matrix — Qyrenith 1.2.0

**Status:** Initial repository-inventory assessment — NOT an implementation certification  
**Branch/HEAD:** `feature/1.2.0-universal-migration-core` / `e2e164ed16f6d9012669e4b3e7b57bf0d57cb356`  
**Assessment date:** 2026-11-10  
**Method:** Git tree inventory, deep-audit specifications, visible source/test path inventory and PR #9 description. No test suite was executed and this was not a line-by-line source audit.

## 1. Status semantics

- **PARTIAL:** a relevant foundation/adjacent capability is visible, but the complete proposed domain contract is not established.
- **NOT_STARTED:** no dedicated implementation was identified in the reviewed engine tree; adjacent primitives may exist.
- **UNKNOWN:** evidence is insufficient.
- These are inventory labels only, not TESTED or VERIFIED. The detailed traceability matrix remains authoritative.

## 2. Engine inventory observed

The reviewed `qyrenith_engine/` tree contains analysis, execution, approval, trust, QDAS and dynamic-audit files, plus `migration/` and `qdas/` packages. Migration includes model, knowledge, planner, worker, authorization, assurance, snapshot, workspace, preparation and QDAS integration. QDAS includes collector, diagnosis, events, ledger, lineage and repair.

No dedicated engine packages were identified in the reviewed tree for API analysis, production observability, database intelligence, accessibility, privacy analysis, documentation intelligence or a unified architecture/knowledge graph. This is a package-inventory observation, not proof that no legacy behavior exists elsewhere.

Tests include migration/QDAS/approval/trust/recovery/release/performance and Node/Rust domain suites. A test filename does not prove behavioral breadth.

## 3. Domain coverage

| # | Domain | Initial status | Visible foundation | Major missing proof / next audit |
|---:|---|---|---|---|
| 1 | Diagnostic Core | undefined | tests/test_qdas_events.py; tests/test_qdas_collector.py | PARTIAL |
| 2 | Language Intelligence | undefined | tests/test_node_domain.py; tests/test_rust_domain.py | PARTIAL |
| 3 | Security Intelligence | undefined | tests/test_verification_invariants.py; security regression fixtures | PARTIAL |
| 4 | Dependency Intelligence | undefined | tests/test_intelligence.py; tests/test_migration_core_120.py | PARTIAL |
| 5 | Architecture Intelligence | undefined | New architecture graph fixtures required | NOT_STARTED |
| 6 | Testing Intelligence | undefined | tests/test_engine_110.py; tests/test_qdas_cli_integration.py; tests/test_performance.py | PARTIAL |
| 7 | Runtime Intelligence | undefined | tests/test_dynamic_audit_qdas_120.py; tests/test_external_check.py | PARTIAL |
| 8 | Repair Intelligence | undefined | tests/test_qdas_repair.py; tests/test_qdas_lineage.py; tests/test_host_approval.py | PARTIAL |
| 9 | Reporting & Integrations | undefined | tests/test_client_entrypoints.py; tests/test_qdas_cli_integration.py | PARTIAL |
| 10 | API & Protocol Intelligence | undefined | New protocol fixtures and contract tests required | NOT_STARTED |
| 11 | Infrastructure & Environment Intelligence | undefined | tests/test_qdas_collector.py; tests/test_verification_invariants.py | PARTIAL |
| 12 | Observability & Production Intelligence | undefined | New telemetry adapter and incident fixtures required | NOT_STARTED |
| 13 | Database & Data Integrity Intelligence | undefined | New database fixture suites required | NOT_STARTED |
| 14 | Reliability & Resilience Intelligence | undefined | tests/test_recovery_and_targets.py; tests/test_external_check.py | PARTIAL |
| 15 | Compatibility & Portability Intelligence | undefined | tests/test_migration_core_120.py; tests/test_node_domain.py; tests/test_rust_domain.py | PARTIAL |
| 16 | Build, Artifact & Release Intelligence | undefined | tests/test_release_contents.py; tests/test_version_consistency.py | PARTIAL |
| 17 | Accessibility & UX Quality Intelligence | undefined | New UI fixtures and manual review protocol required | NOT_STARTED |
| 18 | Privacy & Data Governance Intelligence | undefined | tests/test_qdas_collector.py; tests/test_qdas_events.py | PARTIAL |
| 19 | Documentation & Specification Intelligence | undefined | New docs consistency fixtures required | NOT_STARTED |
| 20 | Cost & Resource Efficiency Intelligence | undefined | tests/test_performance.py; tests/test_external_check.py | PARTIAL |
| 21 | AI & Agent Code Assurance | undefined | tests/test_qdas_cli_integration.py; tests/test_qdas_self_verification.py | PARTIAL |
| 22 | Universal Project Knowledge Graph | undefined | tests/test_qdas_lineage.py; tests/test_intelligence.py | PARTIAL |
| 23 | Attack Surface & Threat Intelligence | undefined | tests/test_trust_store.py; tests/test_verification_invariants.py | PARTIAL |
| 24 | Change Impact & Regression Prediction | undefined | tests/test_migration_snapshot_120.py; tests/test_migration_preparation_120.py | PARTIAL |
| 25 | Continuous Assurance Engine | undefined | tests/test_qdas_ledger.py; tests/test_qdas_self_verification.py | PARTIAL |
| 26 | Software Forensics & Root Cause Engine | undefined | tests/test_qdas_diagnosis.py; tests/test_qdas_lineage.py | PARTIAL |
| 27 | Domain-Specific Diagnostic Packs | undefined | tests/test_node_domain.py; tests/test_rust_domain.py; tests/test_migration_benchmarks_120.py | PARTIAL |

## 4. Cross-cutting maturity gaps

1. Unified project identity and typed knowledge graph across planes.
2. Normalized finding model with scope, provenance, confidence and lifecycle.
3. Reproducibility classes and independent cross-environment execution.
4. Evidence authenticity/external trust anchors beyond local digests/hash chains.
5. OS-enforced process/filesystem/network isolation for side-effecting workers.
6. Analyzer meta-audit: labeled fixtures, mutation tests, false-positive measurement and blind-spot disclosure.
7. Coverage-aware verdict aggregation with no false green.
8. Safe optimization experiment lifecycle with repeatable measurement.
9. Versioned domain packs and conformance qualification.
10. Release acceptance independent of GitHub Actions while Actions remain disabled.

## 5. Required next audit

Before changing any label, inspect implementation and call graph, positive/negative/boundary/adversarial tests, run the relevant suite in an approved local/external environment without GitHub Actions, capture exact command/toolchain/environment/revision/evidence digests, and compare each requirement with acceptance criteria.

## 6. Non-claims

This matrix does not claim all domains are implemented, all tests pass at this HEAD, or package presence proves runtime capability.

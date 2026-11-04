# Component Provenance Register

**Document ID:** QYR-AA-PROV  
**Revision:** 1  
**Status:** Proposed for AA-01 acceptance

This register identifies the origin and ownership of Qyrenith components relevant to Advanced Assurance. It is intended to make implementation provenance auditable and to prevent accidental transplantation of third-party code or distinctive product architecture.

## 1. Provenance policy

- Qyrenith-owned code is designed and implemented specifically for Qyrenith requirements.
- General engineering disciplines may inform requirements, but source code, distinctive algorithms, report layouts, and proprietary workflows are not copied.
- Every new component records its purpose, design rationale, authoring context, tests, dependencies, and relevant ADR.
- Third-party tools are optional providers, not Qyrenith-native implementations.
- A dependency is not accepted solely because it accelerates delivery.
- Uncertain provenance or licensing blocks incorporation until resolved.

## 2. Existing Qyrenith-owned components

| Component | Current location | Provenance | Responsibility in 1.1.0 | Advanced Assurance treatment |
|---|---|---|---|---|
| CLI/control plane | `qyrenith.py` | Qyrenith project implementation | Command dispatch, legacy workflows, integration surface | Preserve compatibility; progressively delegate to defined owners without duplicating policy. |
| Static source inventory | `qyrenith_engine/analysis.py` | Qyrenith-native implementation | Bounded Python AST inventory, syntax state, imports, symbols, hashes | Reuse as a bounded foundation; do not overstate it as semantic verification. |
| Filesystem boundary inspection | `qyrenith_engine/boundary.py` | Qyrenith-native implementation | Read-only boundary inspection and symlink escape detection | Reuse and extend only after path and race threat review. |
| Bounded process execution | `qyrenith_engine/execution.py` | Qyrenith-native implementation | Explicit argv execution, reduced environment, timeout/output bounds | Reuse as process lifecycle foundation; explicitly not an OS sandbox. |
| Public release builder | `scripts/release.py` | Qyrenith project implementation | Manifest-driven ZIP/TAR release artifact generation and checksums | Preserve explicit manifest and artifact tests; extend only with provenance requirements. |
| Public schemas | `schemas/` | Qyrenith project contracts | Existing evidence, worker, and adapter contracts | Version deliberately; keep legacy compatibility mapping explicit. |

## 3. Proposed first-party components

The following are design owners, not claims that the implementation already exists.

| Component | Owning domain | Required origin record | Planned first phase |
|---|---|---|---|
| Project Discovery | Qyrenith core | Qyrenith-specific discovery rules and supported-marker corpus | AA-03 |
| Project Model | Qyrenith core | Qyrenith-owned model, identity, and source-reference schema | AA-03 |
| Verification Planner | Qyrenith core | Qyrenith-owned planning and prerequisite rules | AA-03 |
| Authorization Gate | Qyrenith core | Qyrenith-owned side-effect and approval contract | AA-02 / AA-03 |
| Checker Contract Validator | Qyrenith core | Qyrenith-owned protocol and conformance corpus | AA-02 |
| Checker Runtime | Qyrenith core | Qyrenith-owned lifecycle and resource policy | AA-02 |
| Evidence Validator and Store | Qyrenith core | Qyrenith-owned evidence lifecycle and persistence design | AA-04 |
| Policy Evaluator | Qyrenith core | Qyrenith-owned state semantics and deterministic rules | AA-05 |
| Reporting Layer | Qyrenith core | Qyrenith-owned output contract and accessibility requirements | AA-05 |
| Native checker families | Qyrenith core | Individual algorithm, supported-scope, and test provenance | AA-06 onward |

## 4. External provider register

An external tool is recorded only when it is selected for a concrete integration. Each entry must include:

- provider name and legal project identity;
- exact version or immutable revision;
- source URL and license;
- reason for use;
- data and permission boundary;
- network behavior;
- update and maintenance policy;
- known limitations and fallback;
- conformance tests;
- whether results are advisory or may contribute to validated evidence.

No external provider may independently produce a Qyrenith final PASS.

## 5. New-component provenance record template

Every new Qyrenith-owned component must record:

| Field | Required content |
|---|---|
| Component ID | Stable unique identifier |
| Name and owner | Logical name and accountable owner |
| Purpose | Specific requirement(s) satisfied |
| Design origin | Qyrenith requirements, ADR, and authoring context |
| Originality statement | Confirmation that code/design was authored for Qyrenith and not copied |
| Dependencies | Runtime, development, and optional dependencies with versions/licenses |
| Trust boundary | Inputs, outputs, permissions, and side effects |
| Supported scope | Languages, platforms, project types, and exclusions |
| Tests | Unit, integration, adversarial, compatibility, and acceptance references |
| Limitations | Known blind spots and unsupported behavior |
| Revision history | Change record and related commits |

## 6. 1.1.0 baseline provenance notes

The 1.1.0 engineering modules were introduced as Qyrenith-owned, standard-library-first functionality. Their guarantees are intentionally limited to the documented bounded static analysis, read-only boundary inspection, and bounded process execution behavior. These modules do not claim complete semantic analysis, complete security auditing, or operating-system isolation.

No third-party source implementation is treated as a Qyrenith-native component by this register.

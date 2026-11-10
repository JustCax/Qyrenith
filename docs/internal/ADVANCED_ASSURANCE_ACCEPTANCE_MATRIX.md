# Advanced Assurance Acceptance Matrix

**Document ID:** QYR-AA-ACCEPT  
**Revision:** 1  
**Status:** Proposed for AA-01 acceptance  
**Baseline:** Qyrenith 1.1.0, commit `647398246bc6bc15fdf8fe6038af1bec35710806`

This matrix connects the stable requirement groups to architecture ownership, threat coverage, and the verification method that must exist before the relevant capability is declared complete.

## 1. AA-01 design acceptance

| AA-01 gate | Required evidence | Acceptance rule | Status |
|---|---|---|---|
| A01-01 Requirements coverage | `ADVANCED_ASSURANCE_REQUIREMENTS.md` | Every P0 requirement has a stable ID and an observable acceptance method. | Proposed |
| A01-02 Architecture ownership | `ADVANCED_ASSURANCE_ARCHITECTURE.md` | Every logical responsibility has one accountable owner and a documented dependency direction. | Proposed |
| A01-03 Trust boundaries | `ADVANCED_ASSURANCE_THREAT_MODEL.md` | Project files, processes, checkers, providers, evidence, policy, and release paths are covered. | Proposed |
| A01-04 Security controls | Threat register and architecture controls | Every P0 threat has an assigned control and verification plan. | Proposed |
| A01-05 Compatibility | Requirements and architecture compatibility sections | 1.1.0 CLI, data, state, schema, and release constraints are explicit. | Proposed |
| A01-06 Decision records | `ARCHITECTURE_DECISION_RECORDS/` | Foundational choices state context, alternatives, decision, and consequences. | Proposed |
| A01-07 Provenance | `COMPONENT_PROVENANCE_REGISTER.md` | Existing and proposed Qyrenith-owned components have origin, owner, and dependency records. | Proposed |
| A01-08 Traceability | This matrix | Every P0 requirement maps to a component, threat/control where relevant, and a verification method. | Proposed |
| A01-09 Review | Independent review and deterministic documentation validation | Review the complete branch diff, requirement-ID uniqueness, requirement-level traceability, relative links, cross-document consistency, and implementation-status claims. Record exact revision and validation output. GitHub Actions/CI is not a prerequisite for this documentation-only gate while Actions is disabled; no CI result may be implied. | Pending |
| A01-10 Owner decisions | Recorded owner decisions for all open AA-01 questions | Resolve or explicitly defer every open architecture decision without leaving a P0 trust-boundary ambiguity. | Pending |

## 2. Requirement-to-component mapping

| Requirement group | Architecture owner | Threat references | Verification method introduced by |
|---|---|---|---|
| AA-REQ-PROJ | Project Discovery / Project Model | 001–004 | AA-03 discovery and model tests |
| AA-REQ-PLAN | Verification Planner / Authorization Gate | 011–013, 021, 027 | AA-03 plan determinism and scope tests |
| AA-REQ-CHK | Checker Registry / Runtime | 004–008, 022, 024, 027 | AA-02 conformance and execution tests |
| AA-REQ-EVD | Evidence Validator / Store | 008–011, 016, 019, 025–026 | AA-04 schema, atomicity, integrity tests |
| AA-REQ-POL | Policy Evaluator | 008, 012–014, 017, 023 | AA-05 exhaustive decision and exception tests |
| AA-REQ-SEC | Discovery, Authorization, Runtime, Provider Boundary | 001–008, 014–016, 022, 024, 027 | AA-02 and AA-07 adversarial tests |
| AA-REQ-RPT | Reporting Layer | 009–017, 023 | AA-05 report consistency and redaction tests |
| AA-REQ-EXT | Provider and Adapter Boundary | 008, 014, 015, 017, 018 | AA-02 protocol tests; AA-07 provider simulations |
| AA-REQ-CMP | Compatibility owner | 018, 020–022, 024–026 | AA-10 platform matrix and benchmark qualification |
| AA-REQ-REL | Release Assurance / Evidence | 020–021, 027 | AA-11 manifest, artifact-content, provenance, and publication-gate tests |
| AA-REQ-NFR | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | Per-phase regression, schema compatibility, and supported-platform evidence |

## 3. Requirement-level traceability

The following identifiers reserve one independently verifiable acceptance case for every requirement. They are **planned test identifiers**, not claims that test code or execution evidence already exists. Each case MUST assert the full normative requirement, preserve the declared scope, and record its exact inputs, environment, result, and evidence. A reserved test ID does not make a requirement IMPLEMENTED or VERIFIED.

| Requirement ID | Priority | Architecture owner | Threat references | Planned acceptance case |
|---|---|---|---|---|
| `AA-REQ-PROJ-001` | P0 | Project Discovery / Project Model | 001–004 | `AA-TST-PROJ-001` |
| `AA-REQ-PROJ-002` | P0 | Project Discovery / Project Model | 001–004 | `AA-TST-PROJ-002` |
| `AA-REQ-PROJ-003` | P1 | Project Discovery / Project Model | 001–004 | `AA-TST-PROJ-003` |
| `AA-REQ-PROJ-004` | P0 | Project Discovery / Project Model | 001–004 | `AA-TST-PROJ-004` |
| `AA-REQ-PROJ-005` | P0 | Project Discovery / Project Model | 001–004 | `AA-TST-PROJ-005` |
| `AA-REQ-PROJ-006` | P1 | Project Discovery / Project Model | 001–004 | `AA-TST-PROJ-006` |
| `AA-REQ-PLAN-001` | P0 | Verification Planner / Authorization Gate | 011–013, 021, 027 | `AA-TST-PLAN-001` |
| `AA-REQ-PLAN-002` | P0 | Verification Planner / Authorization Gate | 011–013, 021, 027 | `AA-TST-PLAN-002` |
| `AA-REQ-PLAN-003` | P0 | Verification Planner / Authorization Gate | 011–013, 021, 027 | `AA-TST-PLAN-003` |
| `AA-REQ-PLAN-004` | P0 | Verification Planner / Authorization Gate | 011–013, 021, 027 | `AA-TST-PLAN-004` |
| `AA-REQ-PLAN-005` | P1 | Verification Planner / Authorization Gate | 011–013, 021, 027 | `AA-TST-PLAN-005` |
| `AA-REQ-PLAN-006` | P0 | Verification Planner / Authorization Gate | 011–013, 021, 027 | `AA-TST-PLAN-006` |
| `AA-REQ-CHK-001` | P0 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-001` |
| `AA-REQ-CHK-002` | P0 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-002` |
| `AA-REQ-CHK-003` | P0 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-003` |
| `AA-REQ-CHK-004` | P0 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-004` |
| `AA-REQ-CHK-005` | P0 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-005` |
| `AA-REQ-CHK-006` | P0 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-006` |
| `AA-REQ-CHK-007` | P0 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-007` |
| `AA-REQ-CHK-008` | P1 | Checker Registry / Checker Runtime | 004–008, 022, 024, 027 | `AA-TST-CHK-008` |
| `AA-REQ-EVD-001` | P0 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-001` |
| `AA-REQ-EVD-002` | P0 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-002` |
| `AA-REQ-EVD-003` | P0 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-003` |
| `AA-REQ-EVD-004` | P0 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-004` |
| `AA-REQ-EVD-005` | P0 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-005` |
| `AA-REQ-EVD-006` | P0 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-006` |
| `AA-REQ-EVD-007` | P0 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-007` |
| `AA-REQ-EVD-008` | P1 | Evidence Validator / Evidence Store | 008–011, 016, 019, 025–026 | `AA-TST-EVD-008` |
| `AA-REQ-POL-001` | P0 | Policy Evaluator | 008, 012–014, 017, 023 | `AA-TST-POL-001` |
| `AA-REQ-POL-002` | P0 | Policy Evaluator | 008, 012–014, 017, 023 | `AA-TST-POL-002` |
| `AA-REQ-POL-003` | P0 | Policy Evaluator | 008, 012–014, 017, 023 | `AA-TST-POL-003` |
| `AA-REQ-POL-004` | P0 | Policy Evaluator | 008, 012–014, 017, 023 | `AA-TST-POL-004` |
| `AA-REQ-POL-005` | P0 | Policy Evaluator | 008, 012–014, 017, 023 | `AA-TST-POL-005` |
| `AA-REQ-POL-006` | P0 | Policy Evaluator | 008, 012–014, 017, 023 | `AA-TST-POL-006` |
| `AA-REQ-POL-007` | P1 | Policy Evaluator | 008, 012–014, 017, 023 | `AA-TST-POL-007` |
| `AA-REQ-SEC-001` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-001` |
| `AA-REQ-SEC-002` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-002` |
| `AA-REQ-SEC-003` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-003` |
| `AA-REQ-SEC-004` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-004` |
| `AA-REQ-SEC-005` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-005` |
| `AA-REQ-SEC-006` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-006` |
| `AA-REQ-SEC-007` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-007` |
| `AA-REQ-SEC-008` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-008` |
| `AA-REQ-SEC-009` | P0 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-009` |
| `AA-REQ-SEC-010` | P1 | Discovery / Authorization / Runtime / Provider Boundary | 001–008, 014–016, 022, 024, 027 | `AA-TST-SEC-010` |
| `AA-REQ-RPT-001` | P0 | Reporting Layer | 009–017, 023 | `AA-TST-RPT-001` |
| `AA-REQ-RPT-002` | P0 | Reporting Layer | 009–017, 023 | `AA-TST-RPT-002` |
| `AA-REQ-RPT-003` | P0 | Reporting Layer | 009–017, 023 | `AA-TST-RPT-003` |
| `AA-REQ-RPT-004` | P0 | Reporting Layer | 009–017, 023 | `AA-TST-RPT-004` |
| `AA-REQ-RPT-005` | P1 | Reporting Layer | 009–017, 023 | `AA-TST-RPT-005` |
| `AA-REQ-RPT-006` | P1 | Reporting Layer | 009–017, 023 | `AA-TST-RPT-006` |
| `AA-REQ-EXT-001` | P0 | Provider / Adapter Boundary | 008, 014, 015, 017, 018 | `AA-TST-EXT-001` |
| `AA-REQ-EXT-002` | P0 | Provider / Adapter Boundary | 008, 014, 015, 017, 018 | `AA-TST-EXT-002` |
| `AA-REQ-EXT-003` | P0 | Provider / Adapter Boundary | 008, 014, 015, 017, 018 | `AA-TST-EXT-003` |
| `AA-REQ-EXT-004` | P1 | Provider / Adapter Boundary | 008, 014, 015, 017, 018 | `AA-TST-EXT-004` |
| `AA-REQ-EXT-005` | P1 | Provider / Adapter Boundary | 008, 014, 015, 017, 018 | `AA-TST-EXT-005` |
| `AA-REQ-CMP-001` | P0 | Compatibility owner | 018, 020–022, 024–026 | `AA-TST-CMP-001` |
| `AA-REQ-CMP-002` | P0 | Compatibility owner | 018, 020–022, 024–026 | `AA-TST-CMP-002` |
| `AA-REQ-CMP-003` | P1 | Compatibility owner | 018, 020–022, 024–026 | `AA-TST-CMP-003` |
| `AA-REQ-REL-001` | P0 | Release Assurance / Evidence | 020–021, 027 | `AA-TST-REL-001` |
| `AA-REQ-REL-002` | P0 | Release Assurance / Evidence | 020–021, 027 | `AA-TST-REL-002` |
| `AA-REQ-REL-003` | P0 | Release Assurance / Evidence | 020–021, 027 | `AA-TST-REL-003` |
| `AA-REQ-REL-004` | P0 | Release Assurance / Evidence | 020–021, 027 | `AA-TST-REL-004` |
| `AA-REQ-NFR-001` | P0 | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | `AA-TST-NFR-001` |
| `AA-REQ-NFR-002` | P0 | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | `AA-TST-NFR-002` |
| `AA-REQ-NFR-003` | P0 | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | `AA-TST-NFR-003` |
| `AA-REQ-NFR-004` | P0 | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | `AA-TST-NFR-004` |
| `AA-REQ-NFR-005` | P1 | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | `AA-TST-NFR-005` |
| `AA-REQ-NFR-006` | P1 | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | `AA-TST-NFR-006` |
| `AA-REQ-NFR-007` | P1 | Cross-cutting architecture owners | 003, 007, 019, 022, 025–027 | `AA-TST-NFR-007` |

## 4. P0 requirement acceptance methods

The complete stable requirement IDs are defined in `ADVANCED_ASSURANCE_REQUIREMENTS.md`. The following method categories are mandatory:

| Requirement family | Minimum verification evidence |
|---|---|
| Project identity and discovery | In-root/out-of-root path fixtures; symlink policy cases; bounded scan cases; proof that discovery does not execute project code. |
| Plan and authorization | Determinism tests; plan tamper tests; changed-input invalidation; deny-by-default side-effect tests; mandatory-check preservation tests. |
| Checker protocol/runtime | Valid and invalid contract fixtures; timeout/crash/output-limit tests; cancellation and process cleanup tests; authority separation tests. |
| Evidence | Schema conformance; provenance binding; missing/truncated input rejection; interruption tests; digest mismatch; supersession and retention behavior. |
| Policy | Exhaustive state table; critical non-PASS gate tests; exception scope and expiry tests; deterministic replay. |
| Security | Path traversal and symlink corpus; secret canaries; shell-metacharacter inputs; resource exhaustion; external output injection; network-denial tests. |
| Reporting | Machine/human report equivalence; exact decision-to-evidence references; coverage and exclusion checks; redaction tests. |
| External integrations | Missing provider, stale data, malformed response, contradictory response, and explicit permission tests. |
| Compatibility | Existing CLI regression; state/schema migration and rollback; Windows/macOS/Linux CI for every declared capability. |
| Release integrity | Explicit manifest comparison; source revision binding; ZIP/TAR/sdist/wheel content tests; unauthorized publication trigger tests. |

## 5. Phase exit gates

| Phase | Exit evidence |
|---|---|
| AA-01 | Accepted requirements, architecture, threat model, ADR set, component map, and traceability matrix. |
| AA-02 | Contract schemas, runtime lifecycle tests, limits, cancellation, malformed output, and conformance suite. |
| AA-03 | Project-model schema, source links, deterministic plans, prerequisite and authorization tests. |
| AA-04 | Evidence schema, atomic persistence, digest verification, immutable lifecycle, provenance and interruption tests. |
| AA-05 | Versioned policy engine, mandatory gates, exception handling, deterministic decisions, report traceability. |
| AA-06 | Native checker capability declarations, parser/analysis support matrix, finding evidence, false-positive review corpus. |
| AA-07 | Security and dependency checks, provider identity/freshness, trust-boundary adversarial tests. |
| AA-08 | Baseline identity, change graph, impact selection, evidence invalidation, mandatory-check preservation. |
| AA-09 | Isolated fault harness, reproducible seeds, bounded generated tests, recovery evidence. |
| AA-10 | Declared platform matrix, environment fingerprints, reproducible benchmark protocol, measurement limitations. |
| AA-11 | Release manifest, provenance, artifact qualification, migration and public documentation. |
| AA-12 | End-to-end adversarial corpus, platform results, final limitations register, acceptance report. |

## 6. Traceability rules

- A requirement without a test or other explicit verification method cannot be marked VERIFIED.
- A test without a requirement or documented engineering rationale is not an acceptance gate by itself.
- Every P0 threat must map to at least one control and at least one verification method.
- A failed or skipped verification method remains visible in the phase report.
- The same test result cannot be silently reused after a relevant source, checker, policy, or environment change.
- The phase owner records exact commit, runtime, platform, command, exit result, and evidence references.

## 7. AA-01 open review items

These are explicit review questions, not permission to begin implementation:

1. Approve the initial seven-state vocabulary and confirm whether legacy workflow states require a separate compatibility mapping.
2. Decide the persistent evidence storage backend only after an explicit consistency, atomicity, portability, and privacy comparison.
3. Decide whether process isolation beyond the current bounded runner is a supported OS-specific feature or an external prerequisite.
4. Approve initial verification profiles only after each profile has an exact check inventory and resource policy.
5. Confirm whether any network-enabled provider is in the first Advanced Assurance release; default remains disabled.
6. Define the aggregate project-level assurance decision separately from the seven per-check outcome states, including legacy workflow-state compatibility.
7. Confirm the reproducibility outcome vocabulary and its relationship to per-check outcomes, using the cross-environment/reproducibility specification as the detailed contract.

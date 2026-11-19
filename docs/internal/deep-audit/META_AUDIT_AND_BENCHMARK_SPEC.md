# Meta-Audit and Benchmark Specification

## 1. Objective
Measure whether Qyrenith's analyzers detect the defects they claim to detect, avoid false alarms, preserve determinism, and disclose blind spots.

## 2. Requirements
- **MA-01 Analyzer contracts:** each analyzer publishes supported constructs, rule inventory, expected limitations, and failure modes.
- **MA-02 Golden fixtures:** maintain labeled positive, negative, boundary, and adversarial fixtures per rule/capability.
- **MA-03 Mutation benchmark:** introduce controlled defect mutations and measure whether the analyzer detects them.
- **MA-04 False-positive measurement:** include benign near-miss fixtures and require explanation of expected outcomes.
- **MA-05 Coverage metrics:** measure files, syntax constructs, rules, paths, states, scenarios, and evidence completeness separately.
- **MA-06 Determinism:** compare normalized output digests across repeated runs and supported environments.
- **MA-07 Regression:** every fixed analyzer defect becomes a reviewed regression fixture.
- **MA-08 Independent oracle:** critical analyzers require independently authored expected results or external verification.
- **MA-09 Blind-spot reporting:** disclose unsupported constructs, skipped checks, parser recovery, resource truncation, and untested rule families.
- **MA-10 QDAS integration:** QDAS runs targeted meta-audits on changed analyzers and rejects self-certification.
- **MA-11 Benchmarks:** publish fixture version, machine profile, commands, raw result digests, and metric definitions.
- **MA-12 Anti-gaming:** do not improve scores by deleting fixtures, disabling rules, broadening exclusions, or relabeling expected findings without review.

## 3. Metrics
Report precision/recall only when fixture labels and denominator are explicit. Also report mutation detection rate, false-positive rate, execution coverage, deterministic replay rate, and unsupported-scope rate. Never combine them into a single opaque score.

## 4. Acceptance
Seed known analyzer bugs, false-positive cases, fixture tampering, nondeterministic outputs, and scope exclusions. The meta-audit must detect missing fixtures and score changes caused by test inventory changes. Release reports must include per-engine metrics and limitations.

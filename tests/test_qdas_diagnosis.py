import unittest
from datetime import datetime, timedelta, timezone

from qyrenith_engine.qdas import create_execution_event, diagnose_failure


START = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)
FINISH = START + timedelta(seconds=1)


def make_event(stdout="", stderr="", status="FAIL", kind="BUILD", exit_code=1):
    return create_execution_event(
        {
            "status": status,
            "exit_code": exit_code,
            "duration_seconds": 1,
            "stdout": stdout,
            "stderr": stderr,
        },
        project_id="diagnosis-fixture",
        project_revision="git:diagnosis",
        workspace_id="workspace-diagnosis",
        event_kind=kind,
        tool_name="fixture-tool",
        tool_version="1",
        argv=("fixture-tool",),
        working_directory=".",
        environment={},
        started_at=START,
        finished_at=FINISH,
    )


class QdasDiagnosisTests(unittest.TestCase):
    def test_module_resolution_failure_creates_unconfirmed_hypothesis(self):
        output = "ModuleNotFoundError: No module named 'example_dependency'"
        event = make_event(stderr=output, kind="TEST")
        hypotheses = diagnose_failure(event, stdout="", stderr=output)
        self.assertEqual(len(hypotheses), 1)
        item = hypotheses[0]
        self.assertEqual(item.failure_category, "TEST_FAILURE")
        self.assertEqual(item.rule_id, "DEPENDENCY_OR_IMPORT_PATH_MISSING")
        self.assertEqual(item.state, "UNCONFIRMED")
        self.assertEqual(item.confidence, "LOW")
        self.assertTrue(item.missing_evidence)
        self.assertTrue(item.supporting_evidence)

    def test_multiple_distinct_symptoms_remain_separate_hypotheses(self):
        output = (
            "PermissionError: access denied\n"
            "ModuleNotFoundError: No module named 'fixture'\n"
        )
        event = make_event(stderr=output)
        hypotheses = diagnose_failure(event, stdout="", stderr=output)
        self.assertEqual(
            {item.rule_id for item in hypotheses},
            {"DEPENDENCY_OR_IMPORT_PATH_MISSING", "ACCESS_PERMISSION_DENIED"},
        )
        self.assertEqual(len({item.hypothesis_id for item in hypotheses}), 2)

    def test_observation_excerpt_is_redacted(self):
        output = "ModuleNotFoundError: token=super-secret-value"
        event = make_event(stderr=output)
        hypotheses = diagnose_failure(event, stdout="", stderr=output)
        excerpt = hypotheses[0].supporting_evidence[0].excerpt
        self.assertNotIn("super-secret-value", excerpt)
        self.assertIn("[REDACTED]", excerpt)

    def test_unknown_failure_is_explicit_unknown_not_pass(self):
        output = "something strange happened"
        event = make_event(stderr=output)
        hypotheses = diagnose_failure(event, stdout="", stderr=output)
        self.assertEqual(len(hypotheses), 1)
        self.assertEqual(hypotheses[0].rule_id, "QDAS-ROOT-UNKNOWN-001")
        self.assertEqual(hypotheses[0].confidence, "LOW")
        self.assertEqual(hypotheses[0].state, "UNCONFIRMED")

    def test_output_must_match_original_event_digests(self):
        event = make_event(stderr="ModuleNotFoundError")
        with self.assertRaisesRegex(ValueError, "does not match"):
            diagnose_failure(event, stdout="", stderr="different failure")

    def test_successful_event_has_no_failure_hypotheses(self):
        event = make_event(status="PASS", exit_code=0, stderr="")
        self.assertEqual(diagnose_failure(event, stdout="", stderr=""), ())

    def test_hypothesis_ids_are_deterministic_for_exact_event_evidence(self):
        output = "SyntaxError: invalid syntax"
        event = make_event(stderr=output)
        first = diagnose_failure(event, stdout="", stderr=output)
        second = diagnose_failure(event, stdout="", stderr=output)
        self.assertEqual(
            [item.hypothesis_id for item in first],
            [item.hypothesis_id for item in second],
        )
        self.assertEqual(
            [item.hypothesis_digest for item in first],
            [item.hypothesis_digest for item in second],
        )

    def test_rejects_unbounded_diagnosis_stream(self):
        event = make_event(stderr="x")
        with self.assertRaisesRegex(ValueError, "8 MiB"):
            diagnose_failure(event, stdout="x" * (8 * 1024 * 1024 + 1), stderr="x")


if __name__ == "__main__":
    unittest.main()

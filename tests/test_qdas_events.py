import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from qyrenith_engine.qdas import (
    ExecutionEvent,
    classify_failure,
    create_execution_event,
    environment_fingerprint,
    redact_argv,
    redact_output,
)


START = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)
FINISH = START + timedelta(seconds=2)


def make_event(
    *,
    kind="BUILD",
    status="FAIL",
    exit_code=1,
    timed_out=False,
    output_limited=False,
    output_incomplete=False,
    input_incomplete=False,
    unsupported_state=False,
):
    return create_execution_event(
        {
            "status": status,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "output_limited": output_limited,
            "output_incomplete": output_incomplete,
            "input_incomplete": input_incomplete,
            "unsupported_state": unsupported_state,
            "duration_seconds": 2,
            "stdout": "compiler output",
            "stderr": "failure detail",
        },
        project_id="fixture-project",
        project_revision="git:0123456789abcdef",
        workspace_id="fixture-workspace",
        event_kind=kind,
        tool_name="fixture-compiler",
        tool_version="21.0",
        argv=("compiler", "--release", "21"),
        working_directory=".",
        environment={"PATH": "/usr/bin", "API_TOKEN": "do-not-retain"},
        started_at=START,
        finished_at=FINISH,
    )


class QdasExecutionEventTests(unittest.TestCase):
    def test_normalizes_execution_report_without_retaining_raw_streams(self):
        event = make_event()
        self.assertEqual(event.execution_status, "FAIL")
        self.assertEqual(event.duration_milliseconds, 2000)
        self.assertEqual(event.event_kind, "BUILD")
        self.assertNotIn("compiler output", event.to_json_bytes().decode("utf-8"))
        self.assertNotIn("failure detail", event.to_json_bytes().decode("utf-8"))
        self.assertEqual(event.stdout_digest, hashlib.sha256(b"compiler output").hexdigest())
        self.assertEqual(event.stderr_digest, hashlib.sha256(b"failure detail").hexdigest())

    def test_classifies_failure_by_event_kind(self):
        expected = {
            "BUILD": "BUILD_FAILURE",
            "TEST": "TEST_FAILURE",
            "STATIC_ANALYSIS": "STATIC_ANALYSIS_FAILURE",
            "RUNTIME": "RUNTIME_FAILURE",
            "OTHER": "UNKNOWN_FAILURE",
        }
        for kind, category in expected.items():
            with self.subTest(kind=kind):
                self.assertEqual(classify_failure(make_event(kind=kind)).category, category)

    def test_timeout_has_precedence_over_nonzero_exit_code(self):
        event = make_event(timed_out=True, status="BLOCKED", exit_code=124)
        classification = classify_failure(event)
        self.assertEqual(classification.category, "TIMEOUT")
        self.assertEqual(classification.confidence, "HIGH")

    def test_output_and_input_limits_are_resource_failures(self):
        for flags in (
            {"output_limited": True},
            {"output_incomplete": True},
            {"input_incomplete": True},
        ):
            with self.subTest(flags=flags):
                event = make_event(status="BLOCKED", exit_code=124, **flags)
                self.assertEqual(classify_failure(event).category, "RESOURCE_LIMIT")

    def test_execution_start_failure_is_infrastructure_or_analyzer_failure(self):
        self.assertEqual(
            classify_failure(make_event(status="ERROR", exit_code=None)).category,
            "INFRASTRUCTURE_FAILURE",
        )
        self.assertEqual(
            classify_failure(make_event(kind="STATIC_ANALYSIS", status="ERROR", exit_code=None)).category,
            "ANALYZER_FAILURE",
        )

    def test_explicit_unsupported_state_is_not_a_pass_or_zero_findings(self):
        event = make_event(status="BLOCKED", exit_code=None, unsupported_state=True)
        self.assertEqual(classify_failure(event).category, "UNSUPPORTED_STATE")

    def test_successful_event_has_no_failure_classification(self):
        event = make_event(status="PASS", exit_code=0)
        self.assertIsNone(classify_failure(event))

    def test_sensitive_output_is_redacted_before_digest(self):
        self.assertEqual(
            redact_output("Authorization: Bearer abcdef1234567890"),
            "Authorization: Bearer [REDACTED]",
        )
        self.assertEqual(
            redact_output("API_TOKEN=super-secret-value"),
            "API_TOKEN=[REDACTED]",
        )

    def test_secret_command_arguments_are_redacted(self):
        argv = redact_argv((
            "tool", "--token", "secret-value-123",
            "--api-key=another-secret",
            "Bearer abcdef1234567890",
        ))
        self.assertEqual(argv, (
            "tool", "--token", "[REDACTED]",
            "--api-key=[REDACTED]",
            "Bearer [REDACTED]",
        ))

    def test_environment_fingerprint_excludes_secret_key_values(self):
        first = environment_fingerprint({
            "PATH": "/usr/bin",
            "API_TOKEN": "one-secret",
        })
        second = environment_fingerprint({
            "PATH": "/usr/bin",
            "API_TOKEN": "different-secret",
        })
        self.assertEqual(first, second)
        self.assertNotEqual(first, environment_fingerprint({"PATH": "/opt/bin"}))

    def test_canonical_event_round_trip(self):
        event = make_event()
        restored = ExecutionEvent.from_json_bytes(event.to_json_bytes())
        self.assertEqual(restored, event)
        self.assertEqual(restored.event_digest, event.event_digest)

    def test_rejects_noncanonical_and_duplicate_json(self):
        event = make_event()
        with self.assertRaisesRegex(ValueError, "canonical"):
            ExecutionEvent.from_json_bytes(
                event.to_json_bytes().decode("utf-8").replace('"schema":1', '"schema": 1')
            )
        with self.assertRaisesRegex(ValueError, "invalid execution event JSON"):
            ExecutionEvent.from_json_bytes(
                b'{"schema":1,"schema":1}'
            )

    def test_rejects_pass_with_timeout_or_nonzero_exit(self):
        with self.assertRaisesRegex(ValueError, "contradicts"):
            make_event(status="PASS", exit_code=1)
        with self.assertRaisesRegex(ValueError, "cannot be marked PASS"):
            make_event(status="PASS", exit_code=0, timed_out=True)

    def test_rejects_unsupported_status_and_invalid_duration(self):
        with self.assertRaisesRegex(ValueError, "unsupported status"):
            create_execution_event(
                {"status": "MAYBE"},
                project_id="p", project_revision="r", workspace_id="w",
                event_kind="BUILD", tool_name="tool", tool_version="1",
                argv=("tool",), working_directory=".", environment={},
                started_at=START, finished_at=FINISH,
            )
        with self.assertRaisesRegex(ValueError, "duration_seconds"):
            create_execution_event(
                {"status": "PASS", "exit_code": 0, "duration_seconds": -1},
                project_id="p", project_revision="r", workspace_id="w",
                event_kind="BUILD", tool_name="tool", tool_version="1",
                argv=("tool",), working_directory=".", environment={},
                started_at=START, finished_at=FINISH,
            )

    def test_rejects_finish_before_start(self):
        with self.assertRaisesRegex(ValueError, "must not predate"):
            create_execution_event(
                {"status": "PASS", "exit_code": 0},
                project_id="p", project_revision="r", workspace_id="w",
                event_kind="BUILD", tool_name="tool", tool_version="1",
                argv=("tool",), working_directory=".", environment={},
                started_at=FINISH, finished_at=START,
            )


if __name__ == "__main__":
    unittest.main()

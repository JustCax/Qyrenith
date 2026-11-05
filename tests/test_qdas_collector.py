import sys
import tempfile
import unittest
from pathlib import Path

from qyrenith_engine.qdas import QdasEventLedger, capture_process_event


class QdasProcessCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ledger = QdasEventLedger(self.root / ".qdas" / "events.jsonl")

    def capture(self, code, *, kind="TEST", timeout=5, extra_argv=()):
        return capture_process_event(
            [sys.executable, "-c", code, *extra_argv],
            self.root,
            self.ledger,
            project_id="qdas-fixture",
            project_revision="git:fixture",
            workspace_id="workspace-fixture",
            event_kind=kind,
            tool_name="python",
            tool_version=sys.version.split()[0],
            timeout=timeout,
            output_limit=4096,
        )

    def test_successful_process_is_captured_and_recorded(self):
        result = self.capture("print('qdas-ok')")
        self.assertEqual(result.report["status"], "PASS")
        self.assertEqual(result.event.execution_status, "PASS")
        self.assertIsNone(result.classification)
        records = self.ledger.verify()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event"]["event_id"], result.event.event_id)
        self.assertNotIn("qdas-ok", self.ledger.path.read_text(encoding="utf-8"))

    def test_nonzero_process_exit_is_classified_and_recorded(self):
        result = self.capture("raise SystemExit(7)", kind="BUILD")
        self.assertEqual(result.report["exit_code"], 7)
        self.assertEqual(result.classification.category, "BUILD_FAILURE")
        self.assertEqual(len(self.ledger.verify()), 1)

    def test_timeout_is_captured_as_blocked_not_pass(self):
        result = self.capture("import time; time.sleep(3)", timeout=1)
        self.assertTrue(result.event.timed_out)
        self.assertEqual(result.event.execution_status, "BLOCKED")
        self.assertEqual(result.classification.category, "TIMEOUT")

    def test_sensitive_argv_is_redacted_in_persisted_event(self):
        result = self.capture(
            "print('safe')",
            extra_argv=("--token=super-secret-command-value",),
        )
        self.assertEqual(result.event.argv[-1], "--token=[REDACTED]")
        encoded = self.ledger.path.read_text(encoding="utf-8")
        self.assertNotIn("super-secret-command-value", encoded)

    def test_environment_digest_is_taken_from_actual_process_report(self):
        result = self.capture("print('environment')")
        self.assertEqual(
            result.event.environment_digest,
            result.report["environment_digest"],
        )
        self.assertEqual(len(result.event.environment_digest), 64)


if __name__ == "__main__":
    unittest.main()

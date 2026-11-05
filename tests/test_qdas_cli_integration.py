import hashlib
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qyrenith_qdas_integration_test", ROOT / "qyrenith.py")
QYRENITH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QYRENITH)

from qyrenith_engine.qdas import QdasEventLedger


class QdasCliLifecycleIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "main.py").write_text("print('fixture')\\n", encoding="utf-8")

    def report(self, argv, *, output="safe output", exit_code=0, status="PASS"):
        return {
            "schema": 1,
            "status": status,
            "exit_code": exit_code,
            "argv": list(argv),
            "output": output,
            "output_bytes": len(output.encode("utf-8")),
            "stdout_bytes": len(output.encode("utf-8")),
            "stderr_bytes": 0,
            "output_truncated": False,
            "output_incomplete": False,
            "input_incomplete": False,
            "timed_out": False,
            "duration_seconds": 0.125,
            "shell": False,
            "environment_digest": hashlib.sha256(b"effective-environment").hexdigest(),
        }

    def ledger(self):
        return QdasEventLedger(self.root / ".qyrenith" / "qdas" / "events.jsonl")

    def test_cmdrun_ingests_existing_report_without_running_twice(self):
        argv = ["python", "-c", "print('safe')"]
        process_report = self.report(argv)
        with patch.object(QYRENITH, "run_bounded_process", return_value=process_report) as runner:
            code, output = QYRENITH.cmdrun(argv, self.root, qdas_event_kind="TEST")
        self.assertEqual((code, output), (0, "safe output"))
        runner.assert_called_once()
        records = self.ledger().verify()
        self.assertEqual(len(records), 1)
        event = records[0]["event"]
        self.assertEqual(event["event_kind"], "TEST")
        self.assertEqual(event["execution_status"], "PASS")
        self.assertEqual(event["project_revision"], QYRENITH.source_fingerprint(self.root))
        self.assertEqual(event["environment_digest"], process_report["environment_digest"])
        self.assertEqual(event["duration_milliseconds"], 125)
        self.assertEqual(event["stdout_bytes"], len(b"safe output"))

    def test_failed_test_command_is_classified_and_persisted(self):
        argv = ["python", "-m", "unittest"]
        process_report = self.report(argv, output="FAILED (failures=1)", exit_code=1, status="FAIL")
        with patch.object(QYRENITH, "run_bounded_process", return_value=process_report):
            code, _ = QYRENITH.cmdrun(argv, self.root, qdas_event_kind="TEST")
        self.assertEqual(code, 1)
        records = self.ledger().verify()
        self.assertEqual(records[0]["classification"]["category"], "TEST_FAILURE")

    def test_secret_output_and_arguments_are_not_persisted(self):
        secret = "super-secret-value-9182"
        argv = ["python", "--token=" + secret]
        process_report = self.report(argv, output="token=" + secret)
        with patch.object(QYRENITH, "run_bounded_process", return_value=process_report):
            QYRENITH.cmdrun(argv, self.root, qdas_event_kind="BUILD")
        encoded = self.ledger().path.read_text(encoding="utf-8")
        self.assertNotIn(secret, encoded)
        self.assertIn("[REDACTED]", encoded)

    def test_qdas_persistence_failure_blocks_acceptance(self):
        argv = ["python", "-c", "pass"]
        process_report = self.report(argv)
        state = self.root / ".qyrenith"
        state.write_text("not a directory", encoding="utf-8")
        with patch.object(QYRENITH, "run_bounded_process", return_value=process_report):
            with self.assertRaises(QYRENITH.QyrenithError):
                QYRENITH.cmdrun(argv, self.root, qdas_event_kind="BUILD")

    def test_generic_verify_ingests_build_check_report(self):
        process_report = self.report(["python", "-m", "compileall"])
        with patch.object(QYRENITH, "run_bounded_process", return_value=process_report) as runner:
            result = QYRENITH.generic_verify(self.root, execute=True)
        self.assertEqual(result["status"], "PASS")
        runner.assert_called_once()
        records = self.ledger().verify()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event"]["event_kind"], "BUILD")

    def test_bounded_check_ingests_the_existing_report(self):
        process_report = self.report(["python", "-c", "print(1)"])
        args = type("Args", (), {
            "check_command_one": "python -c 'print(1)'",
            "project": str(self.root),
            "timeout": 5,
            "output_limit": 4096,
        })()
        with patch("qyrenith_engine.run_bounded_process", return_value=process_report) as runner:
            result = QYRENITH.cmd_bounded_check(args)
        self.assertEqual(result, 0)
        runner.assert_called_once()
        records = self.ledger().verify()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event"]["event_kind"], "VERIFICATION")

    def test_commands_without_qdas_opt_in_do_not_create_qdas_state(self):
        argv = ["git", "status", "--short"]
        with patch.object(QYRENITH, "run_bounded_process", return_value=self.report(argv)):
            QYRENITH.cmdrun(argv, self.root)
        self.assertFalse((self.root / ".qyrenith").exists())


if __name__ == "__main__":
    unittest.main()

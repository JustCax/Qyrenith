"""Tests for QDAS dynamic audit capture of scenario execution (1.2.0)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qyrenith_engine.dynamic_audit_qdas import run_scenario_with_qdas
from qyrenith_engine.qdas.collector import QdasCaptureResult
from qyrenith_engine.qdas.ledger import verify_qdas_ledger, QdasLedgerError


def make_qdas_ledger(path):
    from qyrenith_engine.qdas.ledger import QdasEventLedger

    return QdasEventLedger(path)


def make_scenario():
    return {
        "scenario_id": "scenario-1",
        "scenario_kind": "BOUNDED_PROCESS",
        "timeout_seconds": 120,
        "oracle": "HEURISTIC",
    }


def make_report():
    return {
        "status": "PASS",
        "stdout": "scenario executed",
        "stderr": "",
        "exit_code": 0,
        "duration_seconds": 1.0,
    }


class TestQdasDynamicAuditCapture(unittest.TestCase):
    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_invalid_timeout_is_rejected_without_fallback(self, bounded_runner):
        for timeout in (0, 3601, 1.5, True, None):
            with self.subTest(timeout=timeout):
                with tempfile.TemporaryDirectory() as directory:
                    scenario = make_scenario()
                    scenario["timeout_seconds"] = timeout
                    with self.assertRaises(ValueError):
                        run_scenario_with_qdas(
                            scenario,
                            project=directory,
                            qdas_ledger=make_qdas_ledger(Path(directory) / "qdas.jsonl"),
                            project_id="proj-alpha",
                            project_revision="rev-1",
                            workspace_id="ws-1",
                            tool_name="python",
                            tool_version="3.11",
                            environment={"PYTHONPATH": "src"},
                        )

        bounded_runner.assert_not_called()

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_unknown_oracle_is_rejected(self, bounded_runner):
        with tempfile.TemporaryDirectory() as directory:
            scenario = make_scenario()
            scenario["oracle"] = "UNRECOGNIZED"
            with self.assertRaises(ValueError):
                run_scenario_with_qdas(
                    scenario,
                    project=directory,
                    qdas_ledger=make_qdas_ledger(Path(directory) / "qdas.jsonl"),
                    project_id="proj-alpha",
                    project_revision="rev-1",
                    workspace_id="ws-1",
                    tool_name="python",
                    tool_version="3.11",
                    environment={"PYTHONPATH": "src"},
                )

        bounded_runner.assert_not_called()

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_missing_oracle_is_rejected(self, bounded_runner):
        with tempfile.TemporaryDirectory() as directory:
            scenario = make_scenario()
            del scenario["oracle"]
            with self.assertRaises(ValueError):
                run_scenario_with_qdas(
                    scenario,
                    project=directory,
                    qdas_ledger=make_qdas_ledger(Path(directory) / "qdas.jsonl"),
                    project_id="proj-alpha",
                    project_revision="rev-1",
                    workspace_id="ws-1",
                    tool_name="python",
                    tool_version="3.11",
                    environment={"PYTHONPATH": "src"},
                )

        bounded_runner.assert_not_called()

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_missing_timeout_is_rejected(self, bounded_runner):
        with tempfile.TemporaryDirectory() as directory:
            scenario = make_scenario()
            del scenario["timeout_seconds"]
            with self.assertRaises(ValueError):
                run_scenario_with_qdas(
                    scenario,
                    project=directory,
                    qdas_ledger=make_qdas_ledger(Path(directory) / "qdas.jsonl"),
                    project_id="proj-alpha",
                    project_revision="rev-1",
                    workspace_id="ws-1",
                    tool_name="python",
                    tool_version="3.11",
                    environment={"PYTHONPATH": "src"},
                )

        bounded_runner.assert_not_called()

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_invalid_argv_is_rejected_before_process_execution(self, bounded_runner):
        invalid_argv_values = (
            [],
            ["python", "\x00"],
            ["x" * 16_385],
            ["python"] * 257,
        )
        for argv in invalid_argv_values:
            with self.subTest(argument_count=len(argv)):
                with tempfile.TemporaryDirectory() as directory:
                    scenario = make_scenario()
                    scenario["argv"] = argv
                    with self.assertRaises(ValueError):
                        run_scenario_with_qdas(
                            scenario,
                            project=directory,
                            qdas_ledger=make_qdas_ledger(Path(directory) / "qdas.jsonl"),
                            project_id="proj-alpha",
                            project_revision="rev-1",
                            workspace_id="ws-1",
                            tool_name="python",
                            tool_version="3.11",
                            environment={"PYTHONPATH": "src"},
                        )

        bounded_runner.assert_not_called()

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_records_qdas_event_and_scenario_outcome(self, bounded_runner):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            qdas_ledger = make_qdas_ledger(qdas_path)

            scenario = make_scenario()
            capture_result, scenario_outcome = run_scenario_with_qdas(
                scenario,
                project=directory,
                qdas_ledger=qdas_ledger,
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                tool_name="python",
                tool_version="3.11",
                environment={"PYTHONPATH": "src"},
            )

            # Returns both results
            self.assertIsInstance(capture_result, QdasCaptureResult)
            self.assertIsInstance(scenario_outcome, dict)
            bounded_runner.assert_called_once()
            self.assertEqual(bounded_runner.call_args.args[0], ["python"])
            self.assertEqual(bounded_runner.call_args.kwargs["timeout"], 120)

            # QDAS ledger has one record
            qdas_records = verify_qdas_ledger(qdas_path)
            self.assertEqual(len(qdas_records), 1)

            # QDAS event digest is retained in ledger record
            self.assertEqual(
                qdas_records[0]["event"]["event_id"],
                capture_result.event.event_id,
            )

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_caller_supplied_report_cannot_bypass_bounded_runner(self, bounded_runner):
        with tempfile.TemporaryDirectory() as directory:
            scenario = make_scenario()
            scenario["report"] = {
                "status": "PASS",
                "stdout": "forged caller-supplied report",
                "stderr": "",
                "exit_code": 0,
                "duration_seconds": 0.0,
            }
            capture_result, _ = run_scenario_with_qdas(
                scenario,
                project=directory,
                qdas_ledger=make_qdas_ledger(Path(directory) / "qdas.jsonl"),
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                tool_name="python",
                tool_version="3.11",
                environment={"PYTHONPATH": "src"},
            )
            bounded_runner.assert_called_once()
            self.assertEqual(
                capture_result.event.stdout_digest,
                hashlib.sha256(b"scenario executed").hexdigest(),
            )

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_tampering_breaks_qdas_ledger(self, bounded_runner):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            qdas_ledger = make_qdas_ledger(qdas_path)

            scenario = make_scenario()
            run_scenario_with_qdas(
                scenario,
                project=directory,
                qdas_ledger=qdas_ledger,
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                tool_name="python",
                tool_version="3.11",
                environment={"PYTHONPATH": "src"},
            )

            # Tamper QDAS ledger: modify stdout_digest in first record
            lines = qdas_path.read_text(encoding="utf-8").splitlines(keepends=True)
            self.assertEqual(len(lines), 1)
            tampered_qdas = json.loads(lines[0])
            tampered_qdas["event"]["stdout_digest"] = "0" * 64
            lines[0] = json.dumps(tampered_qdas, sort_keys=True) + "\n"
            qdas_path.write_text("".join(lines), encoding="utf-8")

            with self.assertRaises(QdasLedgerError):
                verify_qdas_ledger(qdas_path)

    @patch(
        "qyrenith_engine.dynamic_audit_qdas.run_bounded_process",
        return_value=make_report(),
    )
    def test_environment_fingerprint_binding(self, bounded_runner):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            qdas_ledger = make_qdas_ledger(qdas_path)

            scenario = make_scenario()
            capture_result, scenario_outcome = run_scenario_with_qdas(
                scenario,
                project=directory,
                qdas_ledger=qdas_ledger,
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                tool_name="python",
                tool_version="3.11",
                environment={"PYTHONPATH": "src"},
            )

            # The scenario outcome carries the QDAS event's environment digest
            self.assertEqual(
                scenario_outcome["environment_fingerprint"],
                capture_result.event.environment_digest,
            )


if __name__ == "__main__":
    unittest.main()

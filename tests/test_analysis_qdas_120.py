"""Tests for QDAS capture of static and semantic analysis (1.2.0)."""
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from qyrenith_engine.analysis_qdas import record_analysis_with_qdas
from qyrenith_engine.qdas.ledger import verify_qdas_ledger, QdasLedgerError


def make_qdas_ledger(path):
    from qyrenith_engine.qdas.ledger import QdasEventLedger
    return QdasEventLedger(path)


class TestQdasStaticAnalysisCapture(unittest.TestCase):
    def test_records_qdas_event_and_analysis_report(self):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            qdas_ledger = make_qdas_ledger(qdas_path)

            capture_result, analysis_report = record_analysis_with_qdas(
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
            from qyrenith_engine.qdas.collector import QdasCaptureResult
            self.assertIsInstance(capture_result, QdasCaptureResult)
            self.assertIsInstance(analysis_report, dict)

            # QDAS ledger has one record
            qdas_records = verify_qdas_ledger(qdas_path)
            self.assertEqual(len(qdas_records), 1)

            # QDAS event digest is retained in ledger record
            self.assertEqual(
                qdas_records[0]["event"]["event_id"],
                capture_result.event.event_id,
            )
            self.assertEqual(qdas_records[0]["event"]["event_kind"], "STATIC_ANALYSIS")

    @patch("qyrenith_engine.analysis_qdas.analyze_project")
    def test_unknown_analysis_is_not_misclassified_as_infrastructure_error(self, analyze):
        analyze.return_value = {
            "schema": 1,
            "status": "UNKNOWN",
            "reason": "The analyzer could not establish a complete result.",
            "files": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            capture_result, analysis_report = record_analysis_with_qdas(
                project=directory,
                qdas_ledger=make_qdas_ledger(qdas_path),
                project_id="proj-unknown",
                project_revision="rev-unknown",
                workspace_id="ws-unknown",
                tool_name="python",
                tool_version="3.11",
                environment={},
            )
            self.assertEqual(analysis_report["status"], "UNKNOWN")
            self.assertEqual(
                json.loads(capture_result.report["stdout"])["status"], "UNKNOWN"
            )
            self.assertEqual(capture_result.report["status"], "BLOCKED")
            self.assertEqual(capture_result.event.execution_status, "BLOCKED")
            self.assertEqual(capture_result.classification.category, "UNKNOWN_FAILURE")
            self.assertEqual(capture_result.classification.rule_id, "ANALYSIS-INCOMPLETE-001")

    def test_tampering_breaks_qdas_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            qdas_ledger = make_qdas_ledger(qdas_path)

            record_analysis_with_qdas(
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


if __name__ == "__main__":
    unittest.main()

"""Tests for the QDAS→migration step integration (1.2.0)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from qyrenith_engine.migration.qdas_step import record_migration_step_with_qdas
from qyrenith_engine.migration.assurance import AssuranceLedger, verify_assurance_chain, AssuranceLedgerError
from qyrenith_engine.qdas.collector import QdasCaptureResult
from qyrenith_engine.qdas.ledger import verify_qdas_ledger, QdasLedgerError


def bounded_report():
    return {
        "status": "PASS",
        "stdout": "build ok",
        "stderr": "",
        "exit_code": 0,
        "duration_seconds": 1.5,
    }


def assurance_fields(**overrides):
    fields = {
        "run_id": "run-001",
        "step_id": "step-001",
        "transition_id": "mc-version-001",
        "source_identity": '{"product_version":"1.21"}',
        "target_identity": '{"product_version":"1.21.1"}',
        "plan_digest": "a" * 64,
        "pre_state_digest": "b" * 64,
        "worker_id": "worker-fixture",
        "worker_version": "1.0.0",
        "worker_status": "WORKED",
        "changed_files": [],
        "verdict": "UNKNOWN",
        "created_at": "2026-11-04T12:00:00Z",
    }
    fields.update(overrides)
    return fields


class TestQdasMigrationStep(unittest.TestCase):
    def test_records_qdas_event_and_assurance_record_with_digest_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            assurance_path = Path(directory) / "assurance.jsonl"

            from qyrenith_engine.qdas.ledger import QdasEventLedger
            qdas_ledger = QdasEventLedger(qdas_path)
            assurance_ledger = AssuranceLedger(assurance_path)

            capture_result, assurance_record = record_migration_step_with_qdas(
                bounded_report(),
                project=directory,
                qdas_ledger=qdas_ledger,
                assurance_ledger=assurance_ledger,
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                event_kind="BUILD",
                tool_name="python",
                tool_version="3.11",
                argv=["python", "-m", "build"],
                environment={"PYTHONPATH": "src"},
                run_id="run-001",
                step_id="step-001",
                transition_id="mc-version-001",
                source_identity='{"product_version":"1.21"}',
                target_identity='{"product_version":"1.21.1"}',
                plan_digest="a" * 64,
                pre_state_digest="b" * 64,
                worker_id="worker-fixture",
                worker_version="1.0.0",
                worker_status="WORKED",
                changed_files=[],
                verdict="UNKNOWN",
                created_at="2026-11-04T12:00:00Z",
            )

            # Returns both results
            self.assertIsInstance(capture_result, QdasCaptureResult)
            self.assertIsInstance(assurance_record, dict)

            # QDAS event digest bound into AssuranceLedger evidence_ids
            self.assertEqual(
                assurance_record["evidence_ids"],
                [capture_result.event.event_digest],
            )

            # QDAS ledger has one record
            qdas_records = verify_qdas_ledger(qdas_path)
            self.assertEqual(len(qdas_records), 1)

            # Assurance ledger has one record
            assurance_records = verify_assurance_chain([assurance_record])
            self.assertEqual(len(assurance_records), 1)

    def test_tampering_breaks_both_ledgers(self):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            assurance_path = Path(directory) / "assurance.jsonl"

            from qyrenith_engine.qdas.ledger import QdasEventLedger
            qdas_ledger = QdasEventLedger(qdas_path)
            assurance_ledger = AssuranceLedger(assurance_path)

            record_migration_step_with_qdas(
                bounded_report(),
                project=directory,
                qdas_ledger=qdas_ledger,
                assurance_ledger=assurance_ledger,
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                event_kind="BUILD",
                tool_name="python",
                tool_version="3.11",
                argv=["python", "-m", "build"],
                environment={"PYTHONPATH": "src"},
                run_id="run-001",
                step_id="step-001",
                transition_id="mc-version-001",
                source_identity='{"product_version":"1.21"}',
                target_identity='{"product_version":"1.21.1"}',
                plan_digest="a" * 64,
                pre_state_digest="b" * 64,
                worker_id="worker-fixture",
                worker_version="1.0.0",
                worker_status="WORKED",
                changed_files=[],
                verdict="UNKNOWN",
                created_at="2026-11-04T12:00:00Z",
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

            # Tamper AssuranceLedger: modify record_digest in first record
            lines = assurance_path.read_text(encoding="utf-8").splitlines(keepends=True)
            self.assertEqual(len(lines), 1)
            tampered_assurance = json.loads(lines[0])
            tampered_assurance["record_digest"] = "0" * 64
            lines[0] = json.dumps(tampered_assurance, sort_keys=True) + "\n"
            assurance_path.write_text("".join(lines), encoding="utf-8")

            with self.assertRaises(AssuranceLedgerError):
                verify_assurance_chain([tampered_assurance])

    def test_digest_changes_with_different_input(self):
        with tempfile.TemporaryDirectory() as directory:
            qdas_path = Path(directory) / "qdas.jsonl"
            assurance_path = Path(directory) / "assurance.jsonl"

            from qyrenith_engine.qdas.ledger import QdasEventLedger
            qdas_ledger = QdasEventLedger(qdas_path)
            assurance_ledger = AssuranceLedger(assurance_path)

            # First run
            capture_result_1, assurance_record_1 = record_migration_step_with_qdas(
                bounded_report(),
                project=directory,
                qdas_ledger=qdas_ledger,
                assurance_ledger=assurance_ledger,
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                event_kind="BUILD",
                tool_name="python",
                tool_version="3.11",
                argv=["python", "-m", "build"],
                environment={"PYTHONPATH": "src"},
                run_id="run-001",
                step_id="step-001",
                transition_id="mc-version-001",
                source_identity='{"product_version":"1.21"}',
                target_identity='{"product_version":"1.21.1"}',
                plan_digest="a" * 64,
                pre_state_digest="b" * 64,
                worker_id="worker-fixture",
                worker_version="1.0.0",
                worker_status="WORKED",
                changed_files=[],
                verdict="UNKNOWN",
                created_at="2026-11-04T12:00:00Z",
            )

            # evidence_ids contains the QDAS event digest
            self.assertEqual(
                assurance_record_1["evidence_ids"],
                [capture_result_1.event.event_digest],
            )

            # Second run with different report stdout → different digest
            report_2 = dict(bounded_report())
            report_2["stdout"] = "different output"
            capture_result_2, assurance_record_2 = record_migration_step_with_qdas(
                report_2,
                project=directory,
                qdas_ledger=qdas_ledger,
                assurance_ledger=assurance_ledger,
                project_id="proj-alpha",
                project_revision="rev-1",
                workspace_id="ws-1",
                event_kind="BUILD",
                tool_name="python",
                tool_version="3.11",
                argv=["python", "-m", "build"],
                environment={"PYTHONPATH": "src"},
                run_id="run-002",
                step_id="step-002",
                transition_id="mc-version-002",
                source_identity='{"product_version":"1.21"}',
                target_identity='{"product_version":"1.21.1"}',
                plan_digest="a" * 64,
                pre_state_digest="b" * 64,
                worker_id="worker-fixture",
                worker_version="1.0.0",
                worker_status="WORKED",
                changed_files=[],
                verdict="UNKNOWN",
                created_at="2026-11-04T12:00:00Z",
            )

            # Different input produces different QDAS event digest
            self.assertNotEqual(
                capture_result_1.event.event_digest,
                capture_result_2.event.event_digest,
            )

            # Each assurance record binds its own QDAS event digest
            self.assertEqual(
                assurance_record_2["evidence_ids"],
                [capture_result_2.event.event_digest],
            )


if __name__ == "__main__":
    unittest.main()

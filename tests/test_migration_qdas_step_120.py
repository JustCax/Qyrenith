"""Tests for the QDAS→migration step integration (1.2.0)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from qyrenith_engine.migration.qdas_step import (
    _exclusive_reconciliation_lock,
    MigrationEvidenceCommitError,
    inspect_migration_evidence_link,
    reconcile_migration_evidence_commit,
    record_migration_step_with_qdas,
)
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
    def test_reconciliation_api_is_exported_from_public_packages(self):
        from qyrenith_engine import (
            MigrationEvidenceCommitError as EngineCommitError,
            inspect_migration_evidence_link as engine_inspector,
            reconcile_migration_evidence_commit as engine_reconciler,
        )
        from qyrenith_engine.migration import (
            MigrationEvidenceCommitError as MigrationCommitError,
            inspect_migration_evidence_link as migration_inspector,
            reconcile_migration_evidence_commit as migration_reconciler,
        )

        self.assertIs(EngineCommitError, MigrationCommitError)
        self.assertIs(engine_inspector, migration_inspector)
        self.assertIs(engine_reconciler, migration_reconciler)

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
            link_status = inspect_migration_evidence_link(
                capture_result.event.event_digest, qdas_ledger, assurance_ledger
            )
            self.assertEqual(link_status["status"], "LINKED")
            self.assertEqual(
                link_status["assurance_record_digests"],
                [assurance_record["record_digest"]],
            )

    def test_assurance_failure_exposes_committed_qdas_evidence_for_recovery(self):
        class FailingAssuranceLedger:
            def append(self, fields):
                raise RuntimeError("simulated assurance write failure")

        with tempfile.TemporaryDirectory() as directory:
            from qyrenith_engine.qdas.ledger import QdasEventLedger
            qdas_path = Path(directory) / "qdas.jsonl"
            qdas = QdasEventLedger(qdas_path)

            with self.assertRaises(MigrationEvidenceCommitError) as raised:
                record_migration_step_with_qdas(
                    bounded_report(),
                    project=directory,
                    qdas_ledger=qdas,
                    assurance_ledger=FailingAssuranceLedger(),
                    project_id="proj-alpha",
                    project_revision="rev-1",
                    workspace_id="ws-1",
                    event_kind="BUILD",
                    tool_name="python",
                    tool_version="3.11",
                    argv=["python", "-m", "build"],
                    environment={"PYTHONPATH": "src"},
                    run_id="run-recovery",
                    step_id="step-recovery",
                    transition_id="transition-recovery",
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

            error = raised.exception
            exposed_payload = error.assurance_fields
            exposed_payload["verdict"] = "PASS"
            self.assertEqual(error.assurance_fields["verdict"], "UNKNOWN")
            records = verify_qdas_ledger(qdas_path)
            self.assertEqual(len(records), 1)
            self.assertEqual(error.event_digest, records[0]["event"]["event_digest"])
            self.assertEqual(error.qdas_record_digest, records[0]["record_digest"])
            self.assertIsInstance(error.capture_result, QdasCaptureResult)
            self.assertIsInstance(error.__cause__, RuntimeError)
            link_status = inspect_migration_evidence_link(
                error.event_digest,
                qdas,
                AssuranceLedger(Path(directory) / "assurance.jsonl"),
            )
            self.assertEqual(link_status["status"], "ORPHANED_QDAS_EVENT")
            self.assertEqual(
                link_status["qdas_record_digest"], error.qdas_record_digest
            )
            self.assertEqual(link_status["assurance_record_digests"], [])

            real_assurance = AssuranceLedger(Path(directory) / "assurance.jsonl")
            recovery_lock = real_assurance.path.with_name(
                real_assurance.path.name
                + ".reconcile-" + error.event_digest + ".lock"
            )
            with _exclusive_reconciliation_lock(recovery_lock):
                with self.assertRaisesRegex(RuntimeError, "already active"):
                    reconcile_migration_evidence_commit(error, qdas, real_assurance)

            # A persistent lock file from a crashed process is reusable:
            # the kernel lock, not file existence, determines ownership.
            recovery_lock.write_text("stale", encoding="ascii")

            original_qdas_record_digest = error.qdas_record_digest
            error.qdas_record_digest = "0" * 64
            with self.assertRaisesRegex(RuntimeError, "does not match the verified QDAS record"):
                reconcile_migration_evidence_commit(error, qdas, real_assurance)
            error.qdas_record_digest = original_qdas_record_digest

            repaired = reconcile_migration_evidence_commit(
                error, qdas, real_assurance
            )
            self.assertEqual(repaired["status"], "LINKED")
            self.assertEqual(len(real_assurance.read()), 1)

            # Re-running recovery after a successful commit is idempotent,
            # even if a stale recovery lock remains from a prior crash.
            stale_lock = real_assurance.path.with_name(
                real_assurance.path.name
                + ".reconcile-" + error.event_digest + ".lock"
            )
            repeated = reconcile_migration_evidence_commit(
                error, qdas, real_assurance
            )
            self.assertEqual(repeated["status"], "LINKED")
            self.assertEqual(len(real_assurance.read()), 1)
            self.assertTrue(stale_lock.exists())

    def test_recovery_does_not_duplicate_assurance_append_that_committed_before_error(self):
        class CommitThenRaiseAssuranceLedger:
            def __init__(self, ledger):
                self.ledger = ledger

            def append(self, fields):
                self.ledger.append(fields)
                raise RuntimeError("simulated post-commit durability error")

        with tempfile.TemporaryDirectory() as directory:
            from qyrenith_engine.qdas.ledger import QdasEventLedger
            qdas = QdasEventLedger(Path(directory) / "qdas.jsonl")
            assurance = AssuranceLedger(Path(directory) / "assurance.jsonl")

            with self.assertRaises(MigrationEvidenceCommitError) as raised:
                record_migration_step_with_qdas(
                    bounded_report(),
                    project=directory,
                    qdas_ledger=qdas,
                    assurance_ledger=CommitThenRaiseAssuranceLedger(assurance),
                    project_id="proj-alpha",
                    project_revision="rev-1",
                    workspace_id="ws-ambiguous",
                    event_kind="BUILD",
                    tool_name="python",
                    tool_version="3.11",
                    argv=["python", "-m", "build"],
                    environment={"PYTHONPATH": "src"},
                    run_id="run-ambiguous",
                    step_id="step-ambiguous",
                    transition_id="transition-ambiguous",
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

            error = raised.exception
            before = inspect_migration_evidence_link(error.event_digest, qdas, assurance)
            self.assertEqual(before["status"], "LINKED")
            after = reconcile_migration_evidence_commit(error, qdas, assurance)
            self.assertEqual(after["status"], "LINKED")
            self.assertEqual(len(assurance.read()), 1)

    def test_reconciliation_detects_dangling_and_duplicate_assurance_references(self):
        with tempfile.TemporaryDirectory() as directory:
            from qyrenith_engine.qdas.ledger import QdasEventLedger
            qdas = QdasEventLedger(Path(directory) / "qdas.jsonl")
            assurance = AssuranceLedger(Path(directory) / "assurance.jsonl")
            digest = "c" * 64

            assurance.append(assurance_fields(evidence_ids=[digest]))
            dangling = inspect_migration_evidence_link(digest, qdas, assurance)
            self.assertEqual(
                dangling["status"], "ASSURANCE_REFERENCE_WITHOUT_QDAS_EVENT"
            )

            assurance.append(
                assurance_fields(
                    evidence_ids=[digest], run_id="run-duplicate",
                    step_id="step-duplicate",
                )
            )
            conflict = inspect_migration_evidence_link(digest, qdas, assurance)
            self.assertEqual(conflict["status"], "CONFLICT")
            self.assertEqual(len(conflict["assurance_record_digests"]), 2)

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

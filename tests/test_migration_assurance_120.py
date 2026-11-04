"""Tests for the Qyrenith migration assurance ledger."""
import json
import tempfile
import unittest
from pathlib import Path

from qyrenith_engine.migration.assurance import (
    AssuranceLedger,
    AssuranceLedgerError,
    LedgerLockedError,
    verify_assurance_chain,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def record_fields(**overrides):
    fields = {
        "run_id": "run-001",
        "step_id": "step-001",
        "transition_id": "mc-version-001",
        "source_identity": '{"product_version":"1.21"}',
        "target_identity": '{"product_version":"1.21.1"}',
        "plan_digest": HASH_A,
        "pre_state_digest": HASH_B,
        "worker_id": "worker-fixture",
        "worker_version": "1.0.0",
        "worker_status": "WORKED",
        "changed_files": [],
        "evidence_ids": [],
        "verdict": "UNKNOWN",
        "created_at": "2026-11-04T12:00:00Z",
    }
    fields.update(overrides)
    return fields


class TestAssuranceLedger(unittest.TestCase):
    def test_append_and_read_creates_linked_records(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            first = ledger.append(record_fields())
            second = ledger.append(record_fields(step_id="step-002"))
            records = ledger.read()
            self.assertEqual([item["sequence"] for item in records], [1, 2])
            self.assertEqual(second["previous_digest"], first["record_digest"])
            self.assertEqual(len(verify_assurance_chain(records)), 2)

    def test_worker_qualification_provenance_round_trips_through_chain_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            fields = record_fields(
                worker_manifest_digest=HASH_A,
                worker_qualification_id="qualification-001",
                worker_qualification_digest=HASH_B,
            )
            appended = ledger.append(fields)
            verified = verify_assurance_chain((appended,))
            persisted = ledger.read()
            self.assertEqual(len(persisted), 1)
            self.assertEqual(persisted[0]["record_digest"], appended["record_digest"])
            self.assertEqual(verified[0]["worker_manifest_digest"], HASH_A)
            self.assertEqual(verified[0]["worker_qualification_id"], "qualification-001")
            self.assertEqual(verified[0]["worker_qualification_digest"], HASH_B)

    def test_worker_worked_does_not_become_pass_without_qyrenith_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(verdict="PASS", worker_status="WORKED"))

    def test_pass_requires_diff_post_state_evidence_and_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            result = ledger.append(record_fields(
                verdict="PASS",
                changed_files=["gradle.properties"],
                diff_digest=HASH_C,
                post_state_digest=HASH_A,
                evidence_ids=["build-evidence", "reality-diff"],
                commit_id="0123456789abcdef0123456789abcdef01234567",
                worker_manifest_digest=HASH_A,
                worker_qualification_id="qualification-001",
                worker_qualification_digest=HASH_B,
            ))
            self.assertEqual(result["verdict"], "PASS")

    def test_pass_requires_worker_status_worked(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(
                    verdict="PASS",
                    worker_status="FAILED",
                    changed_files=["gradle.properties"],
                    diff_digest=HASH_C,
                    post_state_digest=HASH_A,
                    evidence_ids=["build"],
                    commit_id="0123456789abcdef0123456789abcdef01234567",
                    worker_manifest_digest=HASH_A,
                    worker_qualification_id="qualification-001",
                    worker_qualification_digest=HASH_B,
                ))

    def test_unknown_worker_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(worker_status="SUCCESS"))

    def test_pass_requires_worker_manifest_and_qualification_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(
                    verdict="PASS",
                    changed_files=["gradle.properties"],
                    diff_digest=HASH_C,
                    post_state_digest=HASH_A,
                    evidence_ids=["build"],
                    commit_id="0123456789abcdef0123456789abcdef01234567",
                ))

    def test_partial_worker_qualification_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(worker_manifest_digest=HASH_A))

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assurance.jsonl"
            ledger = AssuranceLedger(path)
            ledger.append(record_fields())
            item = json.loads(path.read_text(encoding="utf-8"))
            item["worker_status"] = "SUCCESS"
            path.write_text(
                json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssuranceLedgerError):
                ledger.read()

    def test_schema_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assurance.jsonl"
            ledger = AssuranceLedger(path)
            ledger.append(record_fields())
            item = json.loads(path.read_text(encoding="utf-8"))
            item["schema"] = 99
            path.write_text(
                json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssuranceLedgerError):
                ledger.read()

    def test_duplicate_json_object_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assurance.jsonl"
            ledger = AssuranceLedger(path)
            ledger.append(record_fields())
            line = path.read_text(encoding="utf-8").rstrip("\n")
            path.write_text(line[:-1] + ',"schema":1}\n', encoding="utf-8")
            with self.assertRaises(AssuranceLedgerError):
                ledger.read()

    def test_non_list_evidence_ids_are_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(evidence_ids=None))

    def test_unknown_record_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(unreviewed_flag=True))

    def test_noncanonical_changed_file_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            for path in ("./source.py", "source//file.py", "C:/outside.py"):
                with self.subTest(path=path), self.assertRaises(AssuranceLedgerError):
                    ledger.append(record_fields(changed_files=[path]))

    def test_oversized_evidence_identifier_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(evidence_ids=["e" * 257]))

    def test_non_string_commit_identity_is_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(commit_id=7))

    def test_invalid_git_commit_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(
                    verdict="PASS", changed_files=["source.py"],
                    diff_digest=HASH_C, post_state_digest=HASH_A,
                    evidence_ids=["build"], commit_id="not-a-commit",
                ))

    def test_configured_byte_limit_is_enforced_before_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assurance.jsonl"
            ledger = AssuranceLedger(path, max_bytes=1024)
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(source_identity="x" * 1500))
            self.assertFalse(path.exists())

    def test_parent_traversal_in_changed_files_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl")
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(changed_files=["../outside.py"]))

    def test_configured_record_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AssuranceLedger(Path(directory) / "assurance.jsonl", max_records=1)
            ledger.append(record_fields())
            with self.assertRaises(AssuranceLedgerError):
                ledger.append(record_fields(step_id="step-002"))
            self.assertEqual(len(ledger.read()), 1)

    def test_stale_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assurance.jsonl"
            ledger = AssuranceLedger(path)
            ledger.lock_path.write_text("interrupted-writer", encoding="ascii")
            with self.assertRaises(LedgerLockedError):
                ledger.append(record_fields())
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from qyrenith_engine.qdas import (
    QdasEventLedger,
    QdasLedgerError,
    classify_failure,
    create_execution_event,
)


def event(status="FAIL", exit_code=1, kind="BUILD"):
    return create_execution_event(
        {
            "status": status,
            "exit_code": exit_code,
            "duration_seconds": 0.01,
            "stdout": "log output",
            "stderr": "compiler failed",
        },
        project_id="ledger-fixture",
        project_revision="revision-a",
        workspace_id="workspace-a",
        event_kind=kind,
        tool_name="fixture-tool",
        tool_version="1",
        argv=("fixture-tool",),
        working_directory=".",
        environment={"PATH": "/usr/bin"},
    )


class QdasEventLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / ".qdas" / "events.jsonl"
        self.ledger = QdasEventLedger(self.path)

    def test_append_chains_events_and_verifies_round_trip(self):
        first = event()
        first_classification = classify_failure(first)
        first_record = self.ledger.append(first, first_classification)
        second = event(status="PASS", exit_code=0)
        second_record = self.ledger.append(second, None)
        records = self.ledger.verify()
        self.assertEqual(len(records), 2)
        self.assertEqual(first_record["sequence"], 1)
        self.assertEqual(second_record["sequence"], 2)
        self.assertEqual(second_record["previous_digest"], first_record["record_digest"])
        self.assertEqual(records[-1]["event"]["event_id"], second.event_id)
        self.assertIsNone(records[-1]["classification"])

    def test_concurrent_appends_preserve_one_contiguous_hash_chain(self):
        def append_one(_):
            item = event()
            ledger = QdasEventLedger(self.path)
            return ledger.append(item, classify_failure(item))

        with ThreadPoolExecutor(max_workers=8) as pool:
            written = list(pool.map(append_one, range(24)))
        records = self.ledger.verify()
        self.assertEqual(len(records), 24)
        self.assertEqual(sorted(item["sequence"] for item in written), list(range(1, 25)))
        self.assertEqual([item["sequence"] for item in records], list(range(1, 25)))
        for previous, current in zip(records, records[1:]):
            self.assertEqual(current["previous_digest"], previous["record_digest"])

    def test_rejects_duplicate_event(self):
        item = event()
        classification = classify_failure(item)
        self.ledger.append(item, classification)
        with self.assertRaisesRegex(QdasLedgerError, "already been recorded"):
            self.ledger.append(item, classification)

    def test_rejects_classification_for_another_event(self):
        first = event()
        second = event()
        with self.assertRaisesRegex(ValueError, "different execution event"):
            self.ledger.append(first, classify_failure(second))

    def test_requires_classification_for_failed_events(self):
        with self.assertRaisesRegex(ValueError, "require one"):
            self.ledger.append(event(), None)

    def test_rejects_tampered_record(self):
        item = event()
        self.ledger.append(item, classify_failure(item))
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["event"]["project_revision"] = "silently-changed"
        self.path.write_text(
            json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(QdasLedgerError, "digest mismatch"):
            self.ledger.verify()

    def test_rejects_incomplete_trailing_record(self):
        item = event()
        self.ledger.append(item, classify_failure(item))
        with self.path.open("ab") as stream:
            stream.write(b'{"partial":')
        with self.assertRaisesRegex(QdasLedgerError, "incomplete trailing"):
            self.ledger.verify()

    def test_rejects_symlink_ledger(self):
        item = event()
        self.ledger.append(item, classify_failure(item))
        alias = self.path.with_name("alias.jsonl")
        try:
            alias.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are unavailable")
        with self.assertRaisesRegex(QdasLedgerError, "symbolic links"):
            QdasEventLedger(alias).verify()

    def test_rejects_symlinked_ancestor_directory(self):
        target = Path(self.temporary.name) / "real-parent"
        target.mkdir()
        alias = Path(self.temporary.name) / "alias-parent"
        try:
            alias.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symbolic links are unavailable")
        redirected = QdasEventLedger(alias / "nested" / "events.jsonl")
        item = event()
        with self.assertRaisesRegex(QdasLedgerError, "ancestor paths"):
            redirected.append(item, classify_failure(item))

    def test_empty_uncreated_ledger_is_not_a_valid_state_when_parent_missing(self):
        missing = QdasEventLedger(Path(self.temporary.name) / "missing" / "events.jsonl")
        with self.assertRaisesRegex(QdasLedgerError, "does not exist"):
            missing.verify()


if __name__ == "__main__":
    unittest.main()

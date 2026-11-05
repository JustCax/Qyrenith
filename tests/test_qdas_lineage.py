import hashlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qyrenith_engine.qdas import (
    QdasEventLedger,
    QdasEvidenceLineage,
    QdasLineageError,
    classify_failure,
    create_execution_event,
    create_repair_plan,
    diagnose_failure,
)


START = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)


def make_event(status, kind, stderr="", offset=0, revision=None):
    start = START + timedelta(seconds=offset * 3)
    return create_execution_event(
        {
            "status": status,
            "exit_code": 1 if status == "FAIL" else 0,
            "duration_seconds": 1,
            "stdout": "",
            "stderr": stderr,
        },
        project_id="lineage-fixture",
        project_revision=revision or ("revision-" + str(offset)),
        workspace_id="lineage-workspace",
        event_kind=kind,
        tool_name="fixture",
        tool_version="1",
        argv=("fixture", "check"),
        working_directory=".",
        environment={},
        started_at=start,
        finished_at=start + timedelta(seconds=1),
    )


class QdasEvidenceLineageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name) / ".qyrenith" / "qdas"
        self.events = QdasEventLedger(root / "events.jsonl")
        self.lineage = QdasEvidenceLineage(root / "lineage.jsonl", self.events)
        failed = make_event("FAIL", "BUILD", "ModuleNotFoundError: fixture", 0)
        self.hypothesis = diagnose_failure(failed, stdout="", stderr="ModuleNotFoundError: fixture")[0]
        self.failure_record = self.events.append(failed, classify_failure(failed), (self.hypothesis,))
        self.plan = create_repair_plan(
            failed,
            self.hypothesis,
            affected_paths=("src/module.py",),
            intended_change="Restore the missing module import.",
            expected_invariants=("Existing tests remain unchanged.",),
            risk="LOW",
            validation_commands=(("python", "-m", "unittest"),),
            rollback_strategy="Restore the captured source snapshot.",
            created_at=START,
        )

    def _record_plan(self):
        return self.lineage.append("REPAIR_PLAN", {
            "event_id": self.failure_record["event"]["event_id"],
            "event_record_digest": self.failure_record["record_digest"],
            "hypothesis_id": self.hypothesis.hypothesis_id,
            "plan_document": self.plan.to_document(),
            "plan_digest": self.plan.plan_digest,
        })

    def _approved_plan(self):
        plan = self._record_plan()
        review = self.lineage.append("HUMAN_REVIEW", {
            "plan_digest": self.plan.plan_digest,
            "decision": "APPROVE",
            "reviewer_id": "owner-local-assertion",
            "reviewed_at": "2026-11-05T08:10:00Z",
            "note": "Reviewed the proposed scope.",
            "authentication_state": "UNAUTHENTICATED_ASSERTION",
        })
        return plan, review

    def test_full_evidence_lineage_requires_and_binds_each_stage(self):
        _, review = self._approved_plan()
        patch = self.lineage.append("PATCH", {
            "plan_digest": self.plan.plan_digest,
            "review_record_digest": review["record_digest"],
            "base_revision": "revision-0",
            "resulting_revision": "revision-after",
            "diff_digest": hashlib.sha256(b"observed diff").hexdigest(),
            "changed_paths": ["src/module.py"],
            "patch_applied": True,
        })
        verification = make_event("PASS", "BUILD", offset=1, revision="revision-after")
        verification_record = self.events.append(verification, None)
        reverification = self.lineage.append("REVERIFICATION", {
            "patch_record_digest": patch["record_digest"],
            "event_id": verification.event_id,
            "event_record_digest": verification_record["record_digest"],
            "scope_digest": hashlib.sha256(b"build scope").hexdigest(),
        })
        regression = make_event("PASS", "TEST", offset=2, revision="revision-after")
        regression_record = self.events.append(regression, None)
        regression_evidence = self.lineage.append("REGRESSION", {
            "patch_record_digest": patch["record_digest"],
            "event_id": regression.event_id,
            "event_record_digest": regression_record["record_digest"],
            "scope_digest": hashlib.sha256(b"regression suite scope").hexdigest(),
        })
        verdict = self.lineage.append("FINAL_VERDICT", {
            "plan_digest": self.plan.plan_digest,
            "patch_record_digest": patch["record_digest"],
            "reverification_record_digest": reverification["record_digest"],
            "regression_record_digest": regression_evidence["record_digest"],
            "verdict": "PASS",
            "rationale": "Approved proposal, observed patch, successful rebuild and regression evidence are linked.",
        })
        records = self.lineage.verify()
        self.assertEqual([item["kind"] for item in records], [
            "REPAIR_PLAN", "HUMAN_REVIEW", "PATCH",
            "REVERIFICATION", "REGRESSION", "FINAL_VERDICT",
        ])
        self.assertEqual(records[-1]["record_digest"], verdict["record_digest"])

    def test_concurrent_plan_appends_preserve_one_contiguous_chain(self):
        payloads = []
        for offset in range(1, 9):
            failed = make_event("FAIL", "BUILD", "ModuleNotFoundError: fixture", offset)
            hypothesis = diagnose_failure(
                failed, stdout="", stderr="ModuleNotFoundError: fixture"
            )[0]
            event_record = self.events.append(
                failed, classify_failure(failed), (hypothesis,)
            )
            plan = create_repair_plan(
                failed,
                hypothesis,
                affected_paths=("src/module.py",),
                intended_change="Restore the missing module import.",
                expected_invariants=("Existing tests remain unchanged.",),
                risk="LOW",
                validation_commands=(("python", "-m", "unittest"),),
                rollback_strategy="Restore the captured source snapshot.",
                created_at=START + timedelta(seconds=offset * 3),
            )
            payloads.append({
                "event_id": event_record["event"]["event_id"],
                "event_record_digest": event_record["record_digest"],
                "hypothesis_id": hypothesis.hypothesis_id,
                "plan_document": plan.to_document(),
                "plan_digest": plan.plan_digest,
            })
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda payload: self.lineage.append("REPAIR_PLAN", payload), payloads))
        records = self.lineage.verify()
        self.assertEqual(len(records), 8)
        self.assertEqual([item["sequence"] for item in records], list(range(1, 9)))
        for previous, current in zip(records, records[1:]):
            self.assertEqual(current["previous_digest"], previous["record_digest"])

    def test_rejects_plan_without_matching_persisted_hypothesis(self):
        payload = {
            "event_id": self.failure_record["event"]["event_id"],
            "event_record_digest": self.failure_record["record_digest"],
            "hypothesis_id": "0" * 32,
            "plan_document": self.plan.to_document(),
            "plan_digest": self.plan.plan_digest,
        }
        with self.assertRaisesRegex(ValueError, "hypothesis"):
            self.lineage.append("REPAIR_PLAN", payload)

    def test_review_is_explicitly_not_authenticated(self):
        self._record_plan()
        payload = {
            "plan_digest": self.plan.plan_digest,
            "decision": "APPROVE",
            "reviewer_id": "owner",
            "reviewed_at": "2026-11-05T08:10:00Z",
            "note": None,
            "authentication_state": "AUTHENTICATED",
        }
        with self.assertRaisesRegex(ValueError, "cannot authenticate"):
            self.lineage.append("HUMAN_REVIEW", payload)

    def test_patch_requires_prior_approval(self):
        self._record_plan()
        with self.assertRaisesRegex(ValueError, "prior approving review"):
            self.lineage.append("PATCH", {
                "plan_digest": self.plan.plan_digest,
                "review_record_digest": "0" * 64,
                "base_revision": "before",
                "resulting_revision": "after",
                "diff_digest": hashlib.sha256(b"diff").hexdigest(),
                "changed_paths": ["src/module.py"],
                "patch_applied": True,
            })

    def test_patch_rejects_revision_drift_and_unplanned_paths(self):
        _, review = self._approved_plan()
        base = {
            "plan_digest": self.plan.plan_digest,
            "review_record_digest": review["record_digest"],
            "base_revision": "revision-0",
            "resulting_revision": "revision-after",
            "diff_digest": hashlib.sha256(b"observed diff").hexdigest(),
            "changed_paths": ["src/module.py"],
            "patch_applied": True,
        }
        wrong_base = dict(base, base_revision="revision-other")
        with self.assertRaisesRegex(ValueError, "base revision"):
            self.lineage.append("PATCH", wrong_base)
        outside_scope = dict(base, changed_paths=["tests/unplanned.py"])
        with self.assertRaisesRegex(ValueError, "exceed the approved repair plan"):
            self.lineage.append("PATCH", outside_scope)

    def test_reverification_must_reference_a_passing_event(self):
        _, review = self._approved_plan()
        patch = self.lineage.append("PATCH", {
            "plan_digest": self.plan.plan_digest,
            "review_record_digest": review["record_digest"],
            "base_revision": "revision-0",
            "resulting_revision": "revision-after",
            "diff_digest": hashlib.sha256(b"diff").hexdigest(),
            "changed_paths": ["src/module.py"],
            "patch_applied": True,
        })
        failed = make_event("FAIL", "BUILD", "still broken", 1)
        failed_record = self.events.append(failed, classify_failure(failed), diagnose_failure(failed, stdout="", stderr="still broken"))
        with self.assertRaisesRegex(ValueError, "passing execution event"):
            self.lineage.append("REVERIFICATION", {
                "patch_record_digest": patch["record_digest"],
                "event_id": failed.event_id,
                "event_record_digest": failed_record["record_digest"],
                "scope_digest": hashlib.sha256(b"scope").hexdigest(),
            })

    def test_rejects_tampered_lineage_record(self):
        self._record_plan()
        raw = json.loads(self.lineage.path.read_text(encoding="utf-8"))
        raw["payload"]["plan_digest"] = "f" * 64
        self.lineage.path.write_bytes(
            (json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        )
        with self.assertRaisesRegex(QdasLineageError, "invalid"):
            self.lineage.verify()


if __name__ == "__main__":
    unittest.main()

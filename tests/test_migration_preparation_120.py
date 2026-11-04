import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from qyrenith_engine.migration import (
    EvidenceReference,
    KnowledgeCatalog,
    KnowledgeStatus,
    MigrationIdentity,
    MigrationKnowledgeClaim,
    MigrationTransition,
    MultiTargetWorkspaceBatch,
    ProjectSnapshot,
    SnapshotVerification,
    TransitionKind,
    WorkspaceError,
    capture_project_snapshot,
    plan_targets,
    prepare_multi_target_workspaces,
    verify_workspace_baseline,
)


NOW = datetime.now(timezone.utc).replace(microsecond=0)
PLAN_TIME = NOW - timedelta(seconds=30)
VERIFIED_AT = (PLAN_TIME - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
OBSERVED_AT = (PLAN_TIME - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
VALID_UNTIL = (NOW + timedelta(days=30)).isoformat().replace("+00:00", "Z")
VERIFIER_DIGEST = hashlib.sha256(
    Path("qyrenith_engine/migration/knowledge.py").read_bytes()
).hexdigest()


def identity(version):
    return MigrationIdentity(
        domain="minecraft",
        product="example-mod",
        product_version=version,
        platform="java",
        loader="fabric",
        loader_version="0.16.0",
        language="java",
        toolchain="jdk-21",
    )


def verified_claim(claim_id, source, target, valid_until=VALID_UNTIL):
    evidence = EvidenceReference(
        evidence_id=f"evidence-{claim_id}",
        origin="local-test-fixture",
        locator=f"fixtures/{claim_id}.json",
        observed_at=OBSERVED_AT,
        digest="a" * 64,
    )
    return MigrationKnowledgeClaim(
        claim_id=claim_id,
        subject="Example mod version compatibility",
        statement="The declared source state can be migrated to the exact target state.",
        source=source,
        target=target,
        status=KnowledgeStatus.VERIFIED,
        assertion="compatible",
        evidence=(evidence,),
        verified_by="test-reviewer",
        verified_at=VERIFIED_AT,
        valid_until=valid_until,
        verified_with="qyrenith-native-verifier",
        verifier_version="1.2.0-test",
        verifier_digest=VERIFIER_DIGEST,
    )


def multi_target_plan(*, include_second_claim=True, valid_until=VALID_UNTIL):
    source = identity("1.21")
    target_a = identity("1.21.1")
    target_b = identity("1.22")
    claims = [verified_claim("claim-a", source, target_a, valid_until)]
    transitions = [
        MigrationTransition(
            "upgrade-a", source, target_a, TransitionKind.VERSION_UPGRADE, ("claim-a",)
        )
    ]
    if include_second_claim:
        claims.append(verified_claim("claim-b", source, target_b, valid_until))
        transitions.append(
            MigrationTransition(
                "upgrade-b", source, target_b, TransitionKind.VERSION_UPGRADE, ("claim-b",)
            )
        )
    catalog = KnowledgeCatalog(tuple(claims))
    plan = plan_targets(
        source, (target_b, target_a), tuple(transitions), catalog, evaluated_at=PLAN_TIME
    )
    return source, target_a, target_b, catalog, plan


def project_snapshot(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("source baseline\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('baseline')\n", encoding="utf-8")
    return capture_project_snapshot(root)


class MultiTargetWorkspacePreparationTests(unittest.TestCase):
    def test_prepares_plan_bound_independent_workspaces_and_round_trips(self):
        source, target_a, target_b, catalog, plan = multi_target_plan()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            snapshot = project_snapshot(source_root)
            workspace_parent = root / "prepared"
            batch = prepare_multi_target_workspaces(
                source_root, snapshot, workspace_parent, plan, catalog
            )

            self.assertEqual(batch.plan_digest, plan.plan_digest)
            self.assertEqual(batch.snapshot_digest, snapshot.snapshot_digest)
            self.assertEqual(batch.source, source)
            self.assertEqual(batch.targets, (target_a, target_b))
            self.assertEqual(len(batch.workspaces), 2)
            self.assertNotEqual(
                batch.workspaces[0].workspace_path,
                batch.workspaces[1].workspace_path,
            )
            for descriptor, target in zip(batch.workspaces, (target_a, target_b)):
                self.assertEqual(descriptor.target, target)
                self.assertTrue(verify_workspace_baseline(descriptor, snapshot).matches)
            batch.validate_for_plan(plan, snapshot, catalog)

            restored = MultiTargetWorkspaceBatch.from_json_bytes(batch.to_json_bytes())
            self.assertEqual(restored, batch)
            self.assertEqual(restored.batch_digest, batch.batch_digest)

    def test_rejects_partial_multi_target_plan_before_creating_workspaces(self):
        _, _, _, catalog, plan = multi_target_plan(include_second_claim=False)
        self.assertEqual(plan.status, "PARTIAL")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            snapshot = project_snapshot(source_root)
            workspace_parent = root / "prepared"
            with self.assertRaisesRegex(WorkspaceError, "requires PLANNED"):
                prepare_multi_target_workspaces(
                    source_root, snapshot, workspace_parent, plan, catalog
                )
            self.assertFalse(workspace_parent.exists())

    def test_rejects_expired_knowledge_before_workspace_creation(self):
        expiry = (PLAN_TIME + timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
        _, _, _, catalog, plan = multi_target_plan(valid_until=expiry)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            snapshot = project_snapshot(source_root)
            workspace_parent = root / "prepared"
            with self.assertRaisesRegex(WorkspaceError, "claims are not usable"):
                prepare_multi_target_workspaces(
                    source_root, snapshot, workspace_parent, plan, catalog,
                    now=PLAN_TIME + timedelta(seconds=10),
                )
            self.assertFalse(workspace_parent.exists())

    def test_rejects_changed_source_before_creating_workspaces(self):
        _, _, _, catalog, plan = multi_target_plan()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            snapshot = project_snapshot(source_root)
            (source_root / "README.md").write_text("changed\n", encoding="utf-8")
            workspace_parent = root / "prepared"
            with self.assertRaisesRegex(WorkspaceError, "changed after"):
                prepare_multi_target_workspaces(
                    source_root, snapshot, workspace_parent, plan, catalog
                )
            self.assertFalse(workspace_parent.exists())

    def test_batch_cannot_be_reused_with_another_plan_or_snapshot(self):
        _, _, _, catalog, plan = multi_target_plan()
        other_plan = plan_targets(
            plan.source,
            tuple(item.target for item in plan.targets),
            tuple(transition for route in plan.targets for transition in route.transitions),
            catalog,
            max_hops=31,
            evaluated_at=PLAN_TIME,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            snapshot = project_snapshot(source_root)
            batch = prepare_multi_target_workspaces(
                source_root, snapshot, root / "prepared", plan, catalog
            )
            with self.assertRaisesRegex(WorkspaceError, "does not match"):
                batch.validate_for_plan(other_plan, snapshot, catalog)
            (source_root / "README.md").write_text("new baseline\n", encoding="utf-8")
            changed_snapshot = capture_project_snapshot(source_root)
            with self.assertRaisesRegex(WorkspaceError, "does not match"):
                batch.validate_for_plan(plan, changed_snapshot, catalog)

    def test_failed_post_creation_verification_rolls_back_all_workspaces(self):
        _, _, _, catalog, plan = multi_target_plan()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            snapshot = project_snapshot(source_root)
            workspace_parent = root / "prepared"
            changed = SnapshotVerification(
                expected_digest=snapshot.snapshot_digest,
                actual_digest="f" * 64,
                status="CHANGED",
                changed_paths=("README.md",),
                checked_at=NOW.isoformat().replace("+00:00", "Z"),
            )
            with mock.patch(
                "qyrenith_engine.migration.preparation.verify_workspace_baseline",
                return_value=changed,
            ):
                with self.assertRaisesRegex(WorkspaceError, "baseline changed"):
                    prepare_multi_target_workspaces(
                        source_root, snapshot, workspace_parent, plan, catalog
                    )
            self.assertTrue(workspace_parent.exists())
            self.assertEqual(list(workspace_parent.iterdir()), [])

    def test_batch_document_rejects_tampering(self):
        _, _, _, catalog, plan = multi_target_plan()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            snapshot = project_snapshot(source_root)
            batch = prepare_multi_target_workspaces(
                source_root, snapshot, root / "prepared", plan, catalog
            )
            document = json.loads(batch.to_json_bytes())
            document["plan_digest"] = "0" * 64
            tampered = json.dumps(
                document, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            with self.assertRaisesRegex(WorkspaceError, "digest mismatch"):
                MultiTargetWorkspaceBatch.from_json_bytes(tampered)


if __name__ == "__main__":
    unittest.main()

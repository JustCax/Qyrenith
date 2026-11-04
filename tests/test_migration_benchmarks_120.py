"""Executable domain-neutral migration benchmark fixtures."""
import hashlib
import json
import unittest
from datetime import datetime
from pathlib import Path

from qyrenith_engine.migration import (
    EvidenceReference,
    KnowledgeCatalog,
    KnowledgeStatus,
    MigrationIdentity,
    MigrationKnowledgeClaim,
    MigrationTransition,
    TransitionKind,
    plan_route,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "semantic-migration" / "ROUTES.json"
VERIFIER_DIGEST = "sha256:" + hashlib.sha256((ROOT / "qyrenith_engine/migration/knowledge.py").read_bytes()).hexdigest()


def load_fixture():
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if document.get("schema") != 1 or not isinstance(document.get("cases"), list):
        raise ValueError("invalid semantic migration route fixture")
    return document


def build_case(item):
    source = MigrationIdentity(**item["source"])
    target = MigrationIdentity(**item["target"])
    evidence = EvidenceReference(
        evidence_id=item["evidence_id"],
        origin="synthetic-benchmark",
        locator="ROUTES.json#" + item["case_id"],
        observed_at=item["observed_at"],
        digest="sha256:" + hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
    )
    claim = MigrationKnowledgeClaim(
        claim_id="claim-" + item["case_id"],
        subject=item["subject"],
        statement=item["statement"],
        assertion=item["assertion"],
        source=source,
        target=target,
        status=KnowledgeStatus.VERIFIED,
        evidence=(evidence,),
        verified_by=item["verified_by"],
        verified_at=item["verified_at"],
        valid_until=item["valid_until"],
        verified_with="qyrenith-semantic-fixture-validator",
        verifier_version="1",
        verifier_digest=VERIFIER_DIGEST,
    )
    edge = MigrationTransition(
        transition_id="transition-" + item["case_id"],
        source=source,
        target=target,
        kind=TransitionKind(item["kind"]),
        knowledge_claim_ids=(claim.claim_id,),
    )
    return source, target, claim, edge


class TestDomainNeutralMigrationBenchmarks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = load_fixture()

    def test_fixture_covers_every_atomic_transition_kind(self):
        expected = {item.value for item in TransitionKind}
        actual = {item["kind"] for item in self.fixture["cases"]}
        self.assertEqual(actual, expected)
        self.assertEqual(len(self.fixture["cases"]), len(expected))

    def test_every_fixture_builds_an_exact_scope_verified_route(self):
        evaluated_at = datetime.fromisoformat(
            self.fixture["evaluated_at"].replace("Z", "+00:00")
        )
        for item in self.fixture["cases"]:
            with self.subTest(case=item["case_id"]):
                source, target, claim, edge = build_case(item)
                plan = plan_route(
                    source,
                    target,
                    (edge,),
                    KnowledgeCatalog((claim,)),
                    evaluated_at=evaluated_at,
                )
                self.assertEqual(plan.status, item["expected_route_status"])
                self.assertTrue(plan.plannable)
                self.assertEqual(plan.transitions, (edge,))
                self.assertEqual(len(plan.plan_digest), 64)

    def test_fixture_does_not_claim_a_real_worker_or_executable_mapping(self):
        for item in self.fixture["cases"]:
            with self.subTest(case=item["case_id"]):
                self.assertNotIn("worker_id", item)
                self.assertNotIn("worker_version", item)
                self.assertIn("Synthetic", item["statement"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the first Qyrenith 1.2.0 migration-core slice."""
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_DIGEST = "sha256:" + hashlib.sha256((ROOT / "qyrenith_engine/migration/knowledge.py").read_bytes()).hexdigest()

from qyrenith_engine.migration import (
    EvidenceReference,
    KnowledgeCatalog,
    KnowledgeStatus,
    MigrationIdentity,
    MigrationKnowledgeClaim,
    MigrationTransition,
    TransitionKind,
    plan_route,
    plan_targets,
)


def identity(version, loader="fabric", loader_version="0.16.0"):
    return MigrationIdentity(
        domain="minecraft",
        product="minecraft",
        product_version=version,
        platform="java",
        loader=loader,
        loader_version=loader_version,
        language="java",
        toolchain="jdk-21",
    )


def verified_claim(claim_id, source, target):
    return MigrationKnowledgeClaim(
        claim_id=claim_id,
        subject="transition-compatibility",
        statement="A reviewed transition is available for this exact scope.",
        assertion="SUPPORTED",
        source=source,
        target=target,
        status=KnowledgeStatus.VERIFIED,
        evidence=(EvidenceReference(
            evidence_id=f"evidence-{claim_id}",
            origin="controlled-reference-test",
            locator=f"tests/fixtures/{claim_id}",
            observed_at="2026-10-01T12:00:00Z",
            digest="sha256:" + "a" * 64,
        ),),
        verified_by="maintainer-review",
        verified_at="2026-10-02T12:00:00Z",
        valid_until="2026-12-01T00:00:00Z",
        verified_with="qyrenith-migration-knowledge-validator",
        verifier_version="2",
        verifier_digest=VERIFIER_DIGEST,
    )


class TestMigrationIdentity(unittest.TestCase):
    def test_identity_is_dimension_aware(self):
        self.assertNotEqual(identity("1.21", "fabric"), identity("1.21", "neoforge"))
        self.assertNotEqual(identity("1.21", "fabric"), identity("1.21.1", "fabric"))

    def test_required_dimensions_are_validated(self):
        with self.assertRaises(ValueError):
            MigrationIdentity(domain="", product="minecraft")

    def test_stable_key_is_deterministic(self):
        self.assertEqual(identity("1.21").stable_key, identity("1.21").stable_key)


class TestVerifiedKnowledge(unittest.TestCase):
    def test_agent_observation_is_not_verified_knowledge(self):
        source, target = identity("1.21"), identity("1.21.1")
        claim = MigrationKnowledgeClaim(
            claim_id="agent-note", subject="api", statement="It should work",
            assertion="UNKNOWN", source=source, target=target, status=KnowledgeStatus.OBSERVED,
        )
        self.assertFalse(claim.is_usable())

    def test_verified_claim_requires_reviewer_and_evidence(self):
        source, target = identity("1.21"), identity("1.21.1")
        claim = verified_claim("claim-1", source, target)
        self.assertTrue(claim.is_usable())
        with self.assertRaises(ValueError):
            MigrationKnowledgeClaim(
                claim_id="claim-2", subject="api", statement="Claim", assertion="SUPPORTED",
                source=source, target=target, status=KnowledgeStatus.VERIFIED,
                verified_by="reviewer", verified_at="2026-10-02T12:00:00Z",
            )

    def test_expired_claim_is_not_usable(self):
        source, target = identity("1.21"), identity("1.21.1")
        claim = MigrationKnowledgeClaim(
            claim_id="expired", subject="api", statement="Claim", assertion="SUPPORTED",
            source=source, target=target, status=KnowledgeStatus.VERIFIED,
            evidence=(EvidenceReference("e", "test", "fixture", "2026-10-01T00:00:00Z", "sha256:" + "c" * 64),),
            verified_by="reviewer", verified_at="2026-10-01T00:00:00Z",
            valid_until="2026-10-02T00:00:00Z",
            verified_with="qyrenith-migration-knowledge-validator",
            verifier_version="2", verifier_digest=VERIFIER_DIGEST,
        )
        from datetime import datetime, timezone
        self.assertFalse(claim.is_usable(datetime(2026, 10, 3, tzinfo=timezone.utc)))

    def test_claim_field_size_limits_are_enforced(self):
        source, target = identity("1.21"), identity("1.21.1")
        with self.assertRaises(ValueError):
            MigrationKnowledgeClaim(
                claim_id="x", subject="s" * 257, statement="statement",
                assertion="A", source=source, target=target, status=KnowledgeStatus.OBSERVED,
            )
        with self.assertRaises(ValueError):
            EvidenceReference("e", "origin", "x" * 4097, "2026-10-01T00:00:00Z")

    def test_naive_evaluation_time_is_rejected(self):
        from datetime import datetime
        source, target = identity("1.21"), identity("1.21.1")
        claim = verified_claim("claim", source, target)
        with self.assertRaises(ValueError):
            claim.is_usable(datetime(2026, 11, 4))

    def test_future_review_timestamp_is_not_usable(self):
        source, target = identity("1.21"), identity("1.21.1")
        claim = MigrationKnowledgeClaim(
            claim_id="future", subject="api", statement="Claim", assertion="SUPPORTED",
            source=source, target=target, status=KnowledgeStatus.VERIFIED,
            evidence=(EvidenceReference("e", "test", "fixture", "2026-10-01T00:00:00Z", "sha256:" + "c" * 64),),
            verified_by="reviewer", verified_at="2030-01-01T00:00:00Z",
            valid_until="2031-01-01T00:00:00Z",
            verified_with="qyrenith-migration-knowledge-validator",
            verifier_version="2", verifier_digest=VERIFIER_DIGEST,
        )
        from datetime import datetime, timezone
        self.assertFalse(claim.is_usable(datetime(2026, 11, 4, tzinfo=timezone.utc)))

    def test_scope_mismatch_rejects_claim(self):
        source, target = identity("1.21"), identity("1.21.1")
        wrong = verified_claim("wrong", identity("1.20.1"), target)
        catalog = KnowledgeCatalog((wrong,))
        edge = MigrationTransition("edge", source, target, TransitionKind.VERSION_UPGRADE, ("wrong",))
        self.assertFalse(catalog.validates_transition(edge))

    def test_conflicting_claims_for_same_scoped_fact_block_both(self):
        source, target = identity("1.21"), identity("1.21.1")
        approved = verified_claim("approved", source, target)
        contradicted = MigrationKnowledgeClaim(
            claim_id="contradicted", subject=approved.subject,
            statement="The transition is not supported.", assertion="UNSUPPORTED",
            source=source, target=target, status=KnowledgeStatus.OBSERVED,
            evidence=(EvidenceReference("conflict-evidence", "test", "fixture", "2026-10-01T00:00:00Z"),),
        )
        catalog = KnowledgeCatalog((approved, contradicted))
        edge = MigrationTransition("edge", source, target, TransitionKind.VERSION_UPGRADE, ("approved",))
        self.assertEqual(catalog.conflicts, (("approved", "contradicted"),))
        self.assertFalse(catalog.validates_transition(edge))

    def test_explicit_conflicted_marker_blocks_same_scoped_verified_claim(self):
        source, target = identity("1.21"), identity("1.21.1")
        approved = verified_claim("approved", source, target)
        marker = MigrationKnowledgeClaim(
            claim_id="conflict-marker", subject=approved.subject,
            statement="Conflicting evidence requires review.", assertion=None,
            source=source, target=target, status=KnowledgeStatus.CONFLICTED,
        )
        catalog = KnowledgeCatalog((approved, marker))
        edge = MigrationTransition("edge", source, target, TransitionKind.VERSION_UPGRADE, ("approved",))
        self.assertFalse(catalog.validates_transition(edge))

    def test_stale_conflicting_claim_does_not_override_current_verified_claim(self):
        source, target = identity("1.21"), identity("1.21.1")
        approved = verified_claim("approved", source, target)
        old = MigrationKnowledgeClaim(
            claim_id="old", subject=approved.subject,
            statement="Previous compatibility result.", assertion="UNSUPPORTED",
            source=source, target=target, status=KnowledgeStatus.STALE,
            evidence=(EvidenceReference("old-evidence", "test", "old-fixture", "2026-09-01T00:00:00Z"),),
        )
        catalog = KnowledgeCatalog((approved, old))
        edge = MigrationTransition("edge", source, target, TransitionKind.VERSION_UPGRADE, ("approved",))
        self.assertTrue(catalog.validates_transition(edge))

    def test_catalog_export_import_is_canonical_and_integrity_checked(self):
        from qyrenith_engine.migration import deserialize_knowledge_catalog, serialize_knowledge_catalog
        source, target = identity("1.21"), identity("1.21.1")
        catalog = KnowledgeCatalog((verified_claim("portable", source, target),))
        encoded = serialize_knowledge_catalog(catalog)
        restored = deserialize_knowledge_catalog(encoded)
        self.assertEqual(restored.content_digest, catalog.content_digest)
        self.assertEqual(restored.claims()[0].to_dict()["schema"], 2)
        tampered = encoded.replace(b"SUPPORTED", b"UNSUPPORTED")
        with self.assertRaises(ValueError):
            deserialize_knowledge_catalog(tampered)

    def test_claim_evidence_order_does_not_change_catalog_digest(self):
        source, target = identity("1.21"), identity("1.21.1")
        first = verified_claim("stable", source, target)
        extra = EvidenceReference(
            "second-evidence", "test", "fixture:second", "2026-10-01T00:00:00Z",
            "sha256:" + "d" * 64,
        )
        with_two = MigrationKnowledgeClaim(
            claim_id=first.claim_id,
            subject=first.subject,
            statement=first.statement,
            assertion=first.assertion,
            source=source,
            target=target,
            status=KnowledgeStatus.VERIFIED,
            evidence=(*first.evidence, extra),
            verified_by=first.verified_by,
            verified_at=first.verified_at,
            valid_until=first.valid_until,
            verified_with=first.verified_with,
            verifier_version=first.verifier_version,
            verifier_digest=first.verifier_digest,
        )
        reversed_order = MigrationKnowledgeClaim(
            claim_id=first.claim_id,
            subject=first.subject,
            statement=first.statement,
            assertion=first.assertion,
            source=source,
            target=target,
            status=KnowledgeStatus.VERIFIED,
            evidence=(extra, *first.evidence),
            verified_by=first.verified_by,
            verified_at=first.verified_at,
            valid_until=first.valid_until,
        )
        self.assertEqual(
            KnowledgeCatalog((with_two,)).content_digest,
            KnowledgeCatalog((reversed_order,)).content_digest,
        )

    def test_catalog_merge_is_idempotent_but_rejects_changed_identifier_content(self):
        source, target = identity("1.21"), identity("1.21.1")
        original = verified_claim("same-id", source, target)
        catalog = KnowledgeCatalog((original,))
        merged = catalog.merge(catalog)
        self.assertEqual(merged.content_digest, catalog.content_digest)
        changed = MigrationKnowledgeClaim(
            claim_id="same-id", subject=original.subject,
            statement="Changed statement.", assertion=original.assertion,
            source=source, target=target, status=KnowledgeStatus.VERIFIED,
            evidence=original.evidence, verified_by=original.verified_by,
            verified_at=original.verified_at,
        )
        with self.assertRaises(ValueError):
            catalog.merge(KnowledgeCatalog((changed,)))

    def test_catalog_summary_counts_conflicted_verified_claims_as_unusable(self):
        source, target = identity("1.21"), identity("1.21.1")
        approved = verified_claim("approved", source, target)
        conflict = MigrationKnowledgeClaim(
            claim_id="conflict", subject=approved.subject,
            statement="Conflict needs review.", assertion="UNSUPPORTED",
            source=source, target=target, status=KnowledgeStatus.OBSERVED,
        )
        catalog = KnowledgeCatalog((approved, conflict))
        from datetime import datetime, timezone
        summary = catalog.summary(datetime(2026, 11, 4, tzinfo=timezone.utc))
        self.assertEqual(summary["usable_verified"], 0)
        self.assertEqual(summary["unusable_verified"], 1)

    def test_catalog_summary_does_not_promote_unverified_claims(self):
        source, target = identity("1.21"), identity("1.21.1")
        catalog = KnowledgeCatalog((
            verified_claim("verified", source, target),
            MigrationKnowledgeClaim(
                claim_id="observed", subject="other-fact",
                statement="An observation only.", assertion="OBSERVED",
                source=source, target=target, status=KnowledgeStatus.OBSERVED,
            ),
        ))
        from datetime import datetime, timezone
        summary = catalog.summary(datetime(2026, 11, 4, tzinfo=timezone.utc))
        self.assertEqual(summary["claim_count"], 2)
        self.assertEqual(summary["usable_verified"], 1)
        self.assertEqual(summary["status_counts"]["OBSERVED"], 1)

    def test_catalog_import_rejects_noncanonical_whitespace(self):
        from qyrenith_engine.migration import deserialize_knowledge_catalog, serialize_knowledge_catalog
        source, target = identity("1.21"), identity("1.21.1")
        encoded = serialize_knowledge_catalog(KnowledgeCatalog((verified_claim("canonical", source, target),)))
        with self.assertRaises(ValueError):
            deserialize_knowledge_catalog(b" " + encoded)

    def test_catalog_import_rejects_duplicate_json_keys(self):
        from qyrenith_engine.migration import deserialize_knowledge_catalog
        with self.assertRaises(ValueError):
            deserialize_knowledge_catalog(b'{"schema":1,"schema":1,"claims":[],"content_digest":"x"}')


class TestUniversalPlanner(unittest.TestCase):
    def test_plans_only_verified_edges(self):
        a, b, c = identity("1.20.1"), identity("1.21"), identity("1.21.1")
        claims = (verified_claim("ab", a, b), verified_claim("bc", b, c))
        edges = (
            MigrationTransition("edge-ab", a, b, TransitionKind.VERSION_UPGRADE, ("ab",)),
            MigrationTransition("edge-bc", b, c, TransitionKind.VERSION_UPGRADE, ("bc",)),
        )
        from datetime import datetime, timezone
        result = plan_route(a, c, edges, KnowledgeCatalog(claims),
                            evaluated_at=datetime(2026, 11, 4, tzinfo=timezone.utc))
        self.assertTrue(result.plannable)
        self.assertEqual([edge.transition_id for edge in result.transitions], ["edge-ab", "edge-bc"])
        self.assertEqual(len(result.plan_digest), 64)
        self.assertEqual(result.transitions[0].to_dict()["kind"], "VERSION_UPGRADE")

    def test_route_plan_rejects_discontinuous_manual_routes(self):
        from datetime import datetime, timezone
        from qyrenith_engine.migration.planner import RoutePlan
        source, middle, target = identity("1.20.1"), identity("1.21"), identity("1.21.1")
        edge_a = MigrationTransition("a", source, middle, TransitionKind.VERSION_UPGRADE, ("a",))
        edge_b = MigrationTransition("b", source, target, TransitionKind.VERSION_UPGRADE, ("b",))
        with self.assertRaises(ValueError):
            RoutePlan(
                "PLANNED", source, target, (edge_a, edge_b), "invalid",
                "2026-11-04T00:00:00Z", "a" * 64, 5,
            )

    def test_multi_target_plan_rejects_different_evaluation_times(self):
        from datetime import datetime, timezone
        from qyrenith_engine.migration.planner import MultiTargetPlan
        source, a, b = identity("1.20.1"), identity("1.21"), identity("1.21.1")
        now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        claim_a, claim_b = verified_claim("a", source, a), verified_claim("b", source, b)
        edge_a = MigrationTransition("a", source, a, TransitionKind.VERSION_UPGRADE, ("a",))
        edge_b = MigrationTransition("b", source, b, TransitionKind.VERSION_UPGRADE, ("b",))
        catalog = KnowledgeCatalog((claim_a, claim_b))
        route_a = plan_route(source, a, (edge_a,), catalog, evaluated_at=now)
        route_b = plan_route(source, b, (edge_b,), catalog, evaluated_at=now.replace(hour=1))
        with self.assertRaises(ValueError):
            MultiTargetPlan(source, (route_a, route_b))

    def test_set_like_transition_fields_have_canonical_order(self):
        source, target = identity("1.21"), identity("1.21.1")
        first = MigrationTransition(
            "canonical", source, target, TransitionKind.VERSION_UPGRADE,
            ("claim-b", "claim-a"),
            worker_id="worker", worker_version="1.0.0",
            required_capabilities=("validate", "rewrite"),
        )
        second = MigrationTransition(
            "canonical", source, target, TransitionKind.VERSION_UPGRADE,
            ("claim-a", "claim-b"),
            worker_id="worker", worker_version="1.0.0",
            required_capabilities=("rewrite", "validate"),
        )
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_plan_digest_binds_worker_capability_contract(self):
        from datetime import datetime, timezone
        source, target = identity("1.21"), identity("1.21.1")
        claim = verified_claim("claim", source, target)
        edge_a = MigrationTransition(
            "edge", source, target, TransitionKind.VERSION_UPGRADE, ("claim",),
            worker_id="worker-a", worker_version="1.0.0", required_capabilities=("rewrite",),
        )
        edge_b = MigrationTransition(
            "edge", source, target, TransitionKind.VERSION_UPGRADE, ("claim",),
            worker_id="worker-b", worker_version="2.0.0", required_capabilities=("rewrite", "validate"),
        )
        catalog = KnowledgeCatalog((claim,))
        at = datetime(2026, 11, 4, tzinfo=timezone.utc)
        plan_a = plan_route(source, target, (edge_a,), catalog, evaluated_at=at)
        plan_b = plan_route(source, target, (edge_b,), catalog, evaluated_at=at)
        self.assertNotEqual(plan_a.plan_digest, plan_b.plan_digest)

    def test_max_hops_must_be_a_positive_integer(self):
        with self.assertRaises(ValueError):
            plan_route(identity("1.21"), identity("1.21.1"), (), KnowledgeCatalog(), max_hops=True)

    def test_unverified_or_missing_edge_blocks_route(self):
        a, b = identity("1.21"), identity("1.21.1")
        edge = MigrationTransition("edge", a, b, TransitionKind.VERSION_UPGRADE, ("missing",))
        result = plan_route(a, b, (edge,), KnowledgeCatalog())
        self.assertEqual(result.status, "UNKNOWN")
        self.assertFalse(result.plannable)

    def test_completely_unknown_destination_is_unsupported(self):
        source, target = identity("1.21"), identity("1.22")
        result = plan_route(source, target, (), KnowledgeCatalog())
        self.assertEqual(result.status, "UNSUPPORTED")

    def test_disabled_route_is_blocked(self):
        source, target = identity("1.21"), identity("1.21.1")
        claim = verified_claim("disabled-claim", source, target)
        edge = MigrationTransition(
            "disabled-edge", source, target, TransitionKind.VERSION_UPGRADE,
            ("disabled-claim",), enabled=False,
        )
        self.assertEqual(
            plan_route(source, target, (edge,), KnowledgeCatalog((claim,))).status,
            "BLOCKED",
        )

    def test_maximum_hop_limit_blocks_longer_verified_route(self):
        source, middle, target = identity("1.20.1"), identity("1.21"), identity("1.21.1")
        claims = (
            verified_claim("first", source, middle),
            verified_claim("second", middle, target),
        )
        edges = (
            MigrationTransition("first", source, middle, TransitionKind.VERSION_UPGRADE, ("first",)),
            MigrationTransition("second", middle, target, TransitionKind.VERSION_UPGRADE, ("second",)),
        )
        result = plan_route(source, target, edges, KnowledgeCatalog(claims), max_hops=1)
        self.assertEqual(result.status, "BLOCKED")

    def test_loader_conversion_is_a_distinct_transition(self):
        source = identity("1.21", "fabric")
        target = identity("1.21", "neoforge", "21.1.0")
        claim = verified_claim("loader", source, target)
        edge = MigrationTransition("loader-edge", source, target, TransitionKind.LOADER_CONVERSION, ("loader",))
        from datetime import datetime, timezone
        self.assertEqual(
            plan_route(source, target, (edge,), KnowledgeCatalog((claim,)),
                       evaluated_at=datetime(2026, 11, 4, tzinfo=timezone.utc)).status,
            "PLANNED",
        )

    def test_disabled_transition_is_not_planned(self):
        a, b = identity("1.21"), identity("1.21.1")
        claim = verified_claim("claim", a, b)
        edge = MigrationTransition("edge", a, b, TransitionKind.VERSION_UPGRADE, ("claim",), enabled=False)
        self.assertEqual(plan_route(a, b, (edge,), KnowledgeCatalog((claim,))).status, "BLOCKED")

    def test_multi_target_results_are_independent(self):
        source = identity("1.21")
        supported = identity("1.21.1")
        unsupported = identity("1.20.1", "neoforge", "21.0.0")
        claim = verified_claim("claim", source, supported)
        edge = MigrationTransition("edge", source, supported, TransitionKind.VERSION_UPGRADE, ("claim",))
        result = plan_targets(source, (unsupported, supported), (edge,), KnowledgeCatalog((claim,)))
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(sum(item.plannable for item in result.targets), 1)
        self.assertEqual(len({item.evaluated_at for item in result.targets}), 1)

    def test_transition_kind_cannot_hide_a_loader_change_inside_version_upgrade(self):
        source = identity("1.21", "fabric")
        target = identity("1.21.1", "neoforge", "21.1.0")
        with self.assertRaises(ValueError):
            MigrationTransition("mixed", source, target, TransitionKind.VERSION_UPGRADE, ("claim",))

    def test_empty_multi_target_request_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_targets(identity("1.21"), (), (), KnowledgeCatalog())

    def test_multi_target_all_unsupported_is_reported(self):
        source = identity("1.21")
        targets = (identity("1.20.1", "neoforge", "21.0.0"),)
        result = plan_targets(source, targets, (), KnowledgeCatalog())
        self.assertEqual(result.status, "UNSUPPORTED")

    def test_duplicate_transition_ids_are_rejected(self):
        a, b = identity("1.21"), identity("1.21.1")
        claim = verified_claim("claim", a, b)
        edge = MigrationTransition("edge", a, b, TransitionKind.VERSION_UPGRADE, ("claim",))
        with self.assertRaises(ValueError):
            plan_route(a, b, (edge, edge), KnowledgeCatalog((claim,)))


if __name__ == "__main__":
    unittest.main()

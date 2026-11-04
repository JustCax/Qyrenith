"""Tests for version-pinned migration worker contracts and local qualification."""
import unittest
from datetime import datetime, timezone

from qyrenith_engine.migration import (
    EvidenceReference,
    KnowledgeCatalog,
    KnowledgeStatus,
    MigrationIdentity,
    MigrationKnowledgeClaim,
    MigrationTransition,
    MigrationWorkerManifest,
    MigrationWorkerRegistry,
    TransitionKind,
    WorkerPermission,
    WorkerQualification,
    WorkerRegistration,
    WorkerResourceLimits,
    WorkerScope,
    assess_route_workers,
    plan_route,
    deserialize_worker_manifest,
    deserialize_worker_qualification,
    serialize_worker_manifest,
    serialize_worker_qualification,
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
        subject="runtime.compatibility",
        statement="A reviewed exact-scope compatibility fact.",
        assertion="SUPPORTED",
        source=source,
        target=target,
        status=KnowledgeStatus.VERIFIED,
        evidence=(
            EvidenceReference(
                evidence_id=claim_id + "-evidence",
                origin="qualification-fixture",
                locator="fixture:" + claim_id,
                observed_at="2026-11-01T12:00:00Z",
            ),
        ),
        verified_by="maintainer-review",
        verified_at="2026-11-01T12:00:00Z",
        valid_until="2026-12-01T00:00:00Z",
    )


def manifest(source=None, target=None, *, capabilities=("rewrite", "validate"), worker_version="1.0.0"):
    source = source or identity("1.21")
    target = target or identity("1.21.1")
    return MigrationWorkerManifest(
        worker_id="example-porter",
        worker_version=worker_version,
        implementation_digest="sha256:" + "a" * 64,
        protocol_version=1,
        scopes=(WorkerScope(TransitionKind.VERSION_UPGRADE, source, target),),
        capabilities=capabilities,
        permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
        limits=WorkerResourceLimits(
            timeout_seconds=120,
            max_input_bytes=1024 * 1024,
            max_output_bytes=256 * 1024,
            max_changed_files=250,
        ),
    )


def qualification(worker_manifest, *, valid_until="2026-12-01T00:00:00Z", digest=None):
    return WorkerQualification(
        qualification_id="qualification-001",
        worker_id=worker_manifest.worker_id,
        worker_version=worker_manifest.worker_version,
        manifest_digest=digest or worker_manifest.manifest_digest,
        conformance_suite_id="qyrenith-migration-worker-contract",
        conformance_suite_version="1.0.0",
        conformance_suite_digest="sha256:" + "b" * 64,
        result_digest="sha256:" + "c" * 64,
        result_status="PASS",
        test_count=24,
        qualified_by="maintainer-review",
        qualified_at="2026-11-01T12:00:00Z",
        valid_until=valid_until,
    )


def transition(source=None, target=None, *, capabilities=("rewrite",)):
    source = source or identity("1.21")
    target = target or identity("1.21.1")
    return MigrationTransition(
        transition_id="transition-001",
        source=source,
        target=target,
        kind=TransitionKind.VERSION_UPGRADE,
        knowledge_claim_ids=("knowledge-001",),
        worker_id="example-porter",
        worker_version="1.0.0",
        required_capabilities=capabilities,
    )


class TestMigrationWorkerManifest(unittest.TestCase):
    def test_manifest_round_trip_is_canonical_and_digest_preserving(self):
        original = manifest()
        encoded = serialize_worker_manifest(original)
        restored = deserialize_worker_manifest(encoded)
        self.assertEqual(restored.manifest_digest, original.manifest_digest)
        self.assertEqual(restored.to_document(), original.to_document())

    def test_manifest_import_rejects_digest_tampering(self):
        encoded = serialize_worker_manifest(manifest())
        tampered = encoded.replace(b"example-porter", b"other-porter")
        with self.assertRaises(ValueError):
            deserialize_worker_manifest(tampered)

    def test_manifest_import_rejects_noncanonical_whitespace(self):
        with self.assertRaises(ValueError):
            deserialize_worker_manifest(serialize_worker_manifest(manifest()) + b" ")

    def test_manifest_import_rejects_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            deserialize_worker_manifest(
                b'{"schema":1,"schema":1,"manifest_digest":"x"}'
            )

    def test_manifest_rejects_duplicate_scopes(self):
        scope = WorkerScope(
            TransitionKind.VERSION_UPGRADE, identity("1.21"), identity("1.21.1")
        )
        with self.assertRaises(ValueError):
            MigrationWorkerManifest(
                worker_id="duplicate",
                worker_version="1",
                implementation_digest="sha256:" + "a" * 64,
                protocol_version=1,
                scopes=(scope, scope),
                capabilities=(),
                permissions=(),
                limits=WorkerResourceLimits(30, 1024, 1024, 10),
            )

    def test_resource_limits_reject_boolean_values(self):
        with self.assertRaises(ValueError):
            WorkerResourceLimits(True, 1024, 1024, 10)

    def test_manifest_collection_order_does_not_change_digest(self):
        source, target = identity("1.21"), identity("1.21.1")
        second_source, second_target = identity("1.20.1"), identity("1.21")
        scope_a = WorkerScope(TransitionKind.VERSION_UPGRADE, source, target)
        scope_b = WorkerScope(TransitionKind.VERSION_UPGRADE, second_source, second_target)
        first = MigrationWorkerManifest(
            worker_id="stable-worker",
            worker_version="1.0.0",
            implementation_digest="sha256:" + "a" * 64,
            protocol_version=1,
            scopes=(scope_a, scope_b),
            capabilities=("validate", "rewrite"),
            permissions=(WorkerPermission.WRITE_PROJECT, WorkerPermission.READ_PROJECT),
            limits=WorkerResourceLimits(120, 1024 * 1024, 256 * 1024, 250),
        )
        second = MigrationWorkerManifest(
            worker_id="stable-worker",
            worker_version="1.0.0",
            implementation_digest="sha256:" + "a" * 64,
            protocol_version=1,
            scopes=(scope_b, scope_a),
            capabilities=("rewrite", "validate"),
            permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
            limits=WorkerResourceLimits(120, 1024 * 1024, 256 * 1024, 250),
        )
        self.assertEqual(first.manifest_digest, second.manifest_digest)

    def test_manifest_requires_exact_supported_scope(self):
        current = manifest()
        self.assertTrue(current.supports(transition()))
        different_target = transition(target=identity("1.22"))
        self.assertFalse(current.supports(different_target))

    def test_manifest_requires_all_declared_capabilities(self):
        current = manifest(capabilities=("rewrite",))
        self.assertFalse(current.supports(transition(capabilities=("rewrite", "validate"))))


class TestWorkerQualificationAndRegistry(unittest.TestCase):
    def test_qualification_import_rejects_noncanonical_whitespace(self):
        current = manifest()
        with self.assertRaises(ValueError):
            deserialize_worker_qualification(serialize_worker_qualification(qualification(current)) + b" ")

    def test_qualification_import_rejects_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            deserialize_worker_qualification(
                b'{"schema":1,"schema":1,"qualification_id":"duplicate"}'
            )

    def test_qualification_round_trip(self):
        current = manifest()
        record = qualification(current)
        encoded = serialize_worker_qualification(record)
        restored = deserialize_worker_qualification(encoded)
        self.assertEqual(restored.to_dict(), record.to_dict())

    def test_exact_pinned_worker_with_current_qualification_resolves_as_qualified(self):
        current = manifest()
        record = qualification(current)
        registry = MigrationWorkerRegistry((WorkerRegistration(current, record),))
        result = registry.resolve(
            transition(),
            datetime(2026, 11, 4, tzinfo=timezone.utc),
        )
        self.assertEqual(result.status, "QUALIFIED")
        self.assertTrue(result.qualified)
        self.assertEqual(result.manifest_digest, current.manifest_digest)
        self.assertEqual(result.qualification_digest, record.qualification_digest)
        self.assertIn(WorkerPermission.WRITE_PROJECT, result.permissions)

    def test_disabled_transition_cannot_resolve_to_available_worker(self):
        current = manifest()
        record = qualification(current)
        disabled = transition()
        disabled = MigrationTransition(
            transition_id=disabled.transition_id,
            source=disabled.source,
            target=disabled.target,
            kind=disabled.kind,
            knowledge_claim_ids=disabled.knowledge_claim_ids,
            worker_id=disabled.worker_id,
            worker_version=disabled.worker_version,
            required_capabilities=disabled.required_capabilities,
            enabled=False,
        )
        registry = MigrationWorkerRegistry((WorkerRegistration(current, record),))
        self.assertEqual(registry.resolve(disabled).status, "BLOCKED")

    def test_worker_scope_rejects_mismatched_transition_kind(self):
        with self.assertRaises(ValueError):
            WorkerScope(
                TransitionKind.VERSION_UPGRADE,
                identity("1.21", "fabric"),
                identity("1.21", "neoforge", "21.1.0"),
            )
        with self.assertRaises(ValueError):
            WorkerScope(
                TransitionKind.VERSION_UPGRADE,
                identity("1.21", "fabric"),
                identity("1.21.1", "neoforge", "21.1.0"),
            )

    def test_manifest_rejects_duplicate_capabilities(self):
        with self.assertRaises(ValueError):
            manifest(capabilities=("rewrite", "rewrite"))

    def test_manifest_without_qualification_is_not_available(self):
        current = manifest()
        result = MigrationWorkerRegistry((WorkerRegistration(current),)).resolve(transition())
        self.assertEqual(result.status, "UNQUALIFIED")

    def test_unregistered_worker_is_not_available(self):
        result = MigrationWorkerRegistry().resolve(transition())
        self.assertEqual(result.status, "NOT_REGISTERED")

    def test_transition_without_worker_is_not_selected(self):
        source, target = identity("1.21"), identity("1.21.1")
        item = MigrationTransition(
            "no-worker", source, target, TransitionKind.VERSION_UPGRADE,
            ("knowledge-001",),
        )
        result = MigrationWorkerRegistry().resolve(item)
        self.assertEqual(result.status, "NOT_SELECTED")

    def test_expired_qualification_is_stale(self):
        current = manifest()
        record = qualification(current, valid_until="2026-11-03T00:00:00Z")
        registry = MigrationWorkerRegistry((WorkerRegistration(current, record),))
        result = registry.resolve(
            transition(),
            datetime(2026, 11, 4, tzinfo=timezone.utc),
        )
        self.assertEqual(result.status, "STALE")

    def test_non_passing_conformance_result_cannot_be_qualified(self):
        current = manifest()
        with self.assertRaises(ValueError):
            WorkerQualification(
                qualification_id="failed-qualification",
                worker_id=current.worker_id,
                worker_version=current.worker_version,
                manifest_digest=current.manifest_digest,
                conformance_suite_id="suite",
                conformance_suite_version="1",
                conformance_suite_digest="sha256:" + "b" * 64,
                result_digest="sha256:" + "c" * 64,
                result_status="FAIL",
                test_count=10,
                qualified_by="reviewer",
                qualified_at="2026-11-01T12:00:00Z",
                valid_until="2026-12-01T00:00:00Z",
            )

    def test_qualification_from_another_manifest_is_stale(self):
        current = manifest()
        record = qualification(current, digest="0" * 64)
        registry = MigrationWorkerRegistry((WorkerRegistration(current, record),))
        result = registry.resolve(
            transition(),
            datetime(2026, 11, 4, tzinfo=timezone.utc),
        )
        self.assertEqual(result.status, "STALE")

    def test_worker_capability_mismatch_is_incompatible(self):
        current = manifest()
        record = qualification(current)
        restricted = manifest(capabilities=("inspect",))
        registry = MigrationWorkerRegistry((WorkerRegistration(restricted, qualification(restricted)),))
        result = registry.resolve(transition(capabilities=("rewrite",)))
        self.assertEqual(result.status, "INCOMPATIBLE")
        self.assertFalse(result.qualified)

    def test_invalid_evaluation_time_is_rejected_even_for_unregistered_worker(self):
        with self.assertRaises(ValueError):
            MigrationWorkerRegistry().resolve(transition(), datetime(2026, 11, 4))

    def test_worker_version_is_pinned_and_not_floated(self):
        current = manifest(worker_version="2.0.0")
        record = qualification(current)
        registry = MigrationWorkerRegistry((WorkerRegistration(current, record),))
        self.assertEqual(registry.resolve(transition()).status, "NOT_REGISTERED")

    def test_resolution_rejects_inconsistent_qualified_state(self):
        with self.assertRaises(ValueError):
            from qyrenith_engine.migration.worker import WorkerResolution
            WorkerResolution(
                status="QUALIFIED",
                worker_id="worker",
                worker_version="1.0.0",
                manifest_digest="a" * 64,
                qualification_id=None,
                qualification_digest=None,
                permissions=(),
                limits=None,
                reason="Invalid manually constructed result",
            )

    def test_qualified_assessment_covers_every_transition_and_binds_digests(self):
        source, middle, target = identity("1.20.1"), identity("1.21"), identity("1.21.1")
        edge_a = MigrationTransition(
            "first", source, middle, TransitionKind.VERSION_UPGRADE, ("claim-a",),
            worker_id="example-porter", worker_version="1.0.0",
            required_capabilities=("rewrite",),
        )
        edge_b = MigrationTransition(
            "second", middle, target, TransitionKind.VERSION_UPGRADE, ("claim-b",),
            worker_id="example-porter", worker_version="1.0.0",
            required_capabilities=("rewrite",),
        )
        catalog = KnowledgeCatalog((
            verified_claim("claim-a", source, middle),
            verified_claim("claim-b", middle, target),
        ))
        now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        plan = plan_route(source, target, (edge_a, edge_b), catalog, evaluated_at=now)
        current = MigrationWorkerManifest(
            worker_id="example-porter",
            worker_version="1.0.0",
            implementation_digest="sha256:" + "a" * 64,
            protocol_version=1,
            scopes=(
                WorkerScope(TransitionKind.VERSION_UPGRADE, source, middle),
                WorkerScope(TransitionKind.VERSION_UPGRADE, middle, target),
            ),
            capabilities=("rewrite",),
            permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
            limits=WorkerResourceLimits(120, 1024 * 1024, 256 * 1024, 250),
        )
        registry = MigrationWorkerRegistry((
            WorkerRegistration(current, qualification(current)),
        ))
        assessment = assess_route_workers(plan, registry)
        self.assertEqual(assessment.status, "QUALIFIED")
        self.assertTrue(assessment.qualified)
        self.assertEqual(len(assessment.evaluations), 2)
        self.assertEqual(len(assessment.assessment_digest), 64)
        self.assertEqual(assessment.to_dict()["route_plan_digest"], plan.plan_digest)

    def test_planned_route_without_pinned_worker_is_unknown(self):
        source, target = identity("1.21"), identity("1.21.1")
        edge = MigrationTransition(
            "unassigned", source, target, TransitionKind.VERSION_UPGRADE, ("claim",)
        )
        catalog = KnowledgeCatalog((verified_claim("claim", source, target),))
        now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        plan = plan_route(source, target, (edge,), catalog, evaluated_at=now)
        assessment = assess_route_workers(plan, MigrationWorkerRegistry())
        self.assertEqual(plan.status, "PLANNED")
        self.assertEqual(assessment.status, "UNKNOWN")
        self.assertEqual(assessment.evaluations[0][1].status, "NOT_SELECTED")

    def test_registered_worker_without_required_capability_blocks_assessment(self):
        source, target = identity("1.21"), identity("1.21.1")
        edge = MigrationTransition(
            "capability-mismatch", source, target, TransitionKind.VERSION_UPGRADE,
            ("claim",), worker_id="example-porter", worker_version="1.0.0",
            required_capabilities=("rewrite", "validate"),
        )
        catalog = KnowledgeCatalog((verified_claim("claim", source, target),))
        now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        plan = plan_route(source, target, (edge,), catalog, evaluated_at=now)
        restricted = manifest(capabilities=("rewrite",))
        registry = MigrationWorkerRegistry((
            WorkerRegistration(restricted, qualification(restricted)),
        ))
        assessment = assess_route_workers(plan, registry)
        self.assertEqual(assessment.status, "BLOCKED")
        self.assertEqual(assessment.evaluations[0][1].status, "INCOMPATIBLE")

    def test_route_that_is_not_planned_does_not_assess_workers(self):
        source, target = identity("1.21"), identity("1.21.1")
        edge = MigrationTransition("unknown", source, target, TransitionKind.VERSION_UPGRADE, ("missing",))
        plan = plan_route(
            source, target, (edge,), KnowledgeCatalog(),
            evaluated_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
        )
        assessment = assess_route_workers(plan, MigrationWorkerRegistry())
        self.assertEqual(assessment.status, "ROUTE_NOT_PLANNED")
        self.assertEqual(assessment.evaluations, ())

    def test_noop_route_requires_no_worker(self):
        same = identity("1.21")
        plan = plan_route(
            same, same, (), KnowledgeCatalog(),
            evaluated_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
        )
        assessment = assess_route_workers(plan, MigrationWorkerRegistry())
        self.assertEqual(assessment.status, "NO_WORK_REQUIRED")
        self.assertFalse(assessment.qualified)
        self.assertTrue(assessment.worker_gate_satisfied)

    def test_assessment_rejects_resolution_for_wrong_pinned_worker(self):
        from qyrenith_engine.migration.worker import RouteWorkerAssessment, WorkerResolution
        source, target = identity("1.21"), identity("1.21.1")
        edge = transition(source, target)
        wrong = WorkerResolution(
            status="NOT_REGISTERED",
            worker_id="different-worker",
            worker_version="1.0.0",
            manifest_digest=None,
            qualification_id=None,
            qualification_digest=None,
            permissions=(),
            limits=None,
            reason="Not registered",
        )
        with self.assertRaises(ValueError):
            RouteWorkerAssessment(
                "a" * 64, "2026-11-04T00:00:00Z", "UNKNOWN",
                ((edge, wrong),), "Mismatched worker resolution",
            )

    def test_assessment_rejects_non_contiguous_manual_evaluations(self):
        from qyrenith_engine.migration.worker import RouteWorkerAssessment
        source, middle, target = identity("1.20.1"), identity("1.21"), identity("1.21.1")
        edge_a = MigrationTransition(
            "first", source, middle, TransitionKind.VERSION_UPGRADE, ("a",)
        )
        edge_b = MigrationTransition(
            "second", source, target, TransitionKind.VERSION_UPGRADE, ("b",)
        )
        empty = MigrationWorkerRegistry().resolve(
            MigrationTransition("placeholder", source, middle, TransitionKind.VERSION_UPGRADE, ("p",))
        )
        with self.assertRaises(ValueError):
            RouteWorkerAssessment(
                "a" * 64, "2026-11-04T00:00:00Z", "UNKNOWN",
                ((edge_a, empty), (edge_b, empty)),
                "Invalid discontinuous transition assessment",
            )

    def test_worker_assessment_must_use_route_plan_timestamp(self):
        source, target = identity("1.21"), identity("1.21.1")
        edge = MigrationTransition(
            "pinned", source, target, TransitionKind.VERSION_UPGRADE, ("claim",)
        )
        plan = plan_route(
            source, target, (edge,), KnowledgeCatalog((verified_claim("claim", source, target),)),
            evaluated_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
        )
        with self.assertRaises(ValueError):
            assess_route_workers(
                plan, MigrationWorkerRegistry(), datetime(2026, 11, 4, 1, tzinfo=timezone.utc)
            )

    def test_registry_rejects_duplicate_worker_versions(self):
        current = manifest()
        with self.assertRaises(ValueError):
            MigrationWorkerRegistry((
                WorkerRegistration(current),
                WorkerRegistration(current),
            ))


if __name__ == "__main__":
    unittest.main()

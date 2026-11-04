"""Security-boundary tests for plan-bound migration authorization."""
import unittest
from datetime import datetime, timezone

from qyrenith_engine.migration import (
    MigrationAuthorizationPolicy,
    MigrationIdentity,
    MigrationKnowledgeClaim,
    KnowledgeCatalog,
    KnowledgeStatus,
    EvidenceReference,
    MigrationTransition,
    MigrationWorkerManifest,
    MigrationWorkerRegistry,
    MigrationStepGrant,
    RouteWorkerAssessment,
    TransitionKind,
    WorkerPermission,
    WorkerQualification,
    WorkerRegistration,
    WorkerResourceLimits,
    WorkerScope,
    assess_route_workers,
    authorize_migration,
    deserialize_migration_authorization,
    serialize_migration_authorization,
    deserialize_migration_authorization_policy,
    serialize_migration_authorization_policy,
    plan_route,
)


NOW = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
SOURCE = MigrationIdentity(
    domain="minecraft", product="minecraft", product_version="1.21",
    platform="java", loader="fabric", loader_version="0.16",
)
TARGET = MigrationIdentity(
    domain="minecraft", product="minecraft", product_version="1.21.1",
    platform="java", loader="fabric", loader_version="0.16",
)


def fixture():
    claim = MigrationKnowledgeClaim(
        claim_id="authorization-claim",
        subject="runtime.compatibility",
        assertion="SUPPORTED",
        statement="Reviewed fixture assertion.",
        source=SOURCE,
        target=TARGET,
        status=KnowledgeStatus.VERIFIED,
        evidence=(EvidenceReference(
            evidence_id="authorization-evidence", origin="test",
            locator="fixture:authorization", observed_at="2026-11-01T00:00:00Z",
        ),),
        verified_by="test-reviewer",
        verified_at="2026-11-01T00:00:00Z",
        valid_until="2026-12-01T00:00:00Z",
    )
    edge = MigrationTransition(
        transition_id="authorization-transition",
        source=SOURCE,
        target=TARGET,
        kind=TransitionKind.VERSION_UPGRADE,
        knowledge_claim_ids=(claim.claim_id,),
        worker_id="fixture-worker",
        worker_version="1.0.0",
        required_capabilities=("rewrite",),
    )
    manifest = MigrationWorkerManifest(
        worker_id="fixture-worker",
        worker_version="1.0.0",
        implementation_digest="sha256:" + "a" * 64,
        protocol_version=1,
        scopes=(WorkerScope(TransitionKind.VERSION_UPGRADE, SOURCE, TARGET),),
        capabilities=("rewrite", "validate"),
        permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT,
                     WorkerPermission.EXECUTE_PROCESS),
        limits=WorkerResourceLimits(600, 16 * 1024 * 1024, 8 * 1024 * 1024, 500),
    )
    qualification = WorkerQualification(
        qualification_id="fixture-qualification",
        worker_id=manifest.worker_id,
        worker_version=manifest.worker_version,
        manifest_digest=manifest.manifest_digest,
        conformance_suite_id="fixture-suite",
        conformance_suite_version="1.0",
        conformance_suite_digest="sha256:" + "b" * 64,
        result_digest="sha256:" + "c" * 64,
        result_status="PASS",
        test_count=20,
        qualified_by="reviewer",
        qualified_at="2026-11-01T00:00:00Z",
        valid_until="2026-11-05T00:00:00Z",
    )
    registry = MigrationWorkerRegistry((WorkerRegistration(manifest, qualification),))
    plan = plan_route(SOURCE, TARGET, (edge,), KnowledgeCatalog((claim,)), evaluated_at=NOW)
    assessment = assess_route_workers(plan, registry)
    policy = MigrationAuthorizationPolicy(
        allowed_permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
        max_timeout_seconds=300,
        max_input_bytes=8 * 1024 * 1024,
        max_output_bytes=4 * 1024 * 1024,
        max_changed_files=1000,
        max_lifetime_seconds=900,
        allowed_worker_ids=("fixture-worker",),
    )
    limits = WorkerResourceLimits(120, 1024 * 1024, 512 * 1024, 100)
    return plan, assessment, registry, policy, limits


def authorize(*, approved_at=NOW, expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
              permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
              limits=None):
    plan, assessment, registry, policy, default_limits = fixture()
    return authorize_migration(
        plan, assessment, registry, policy,
        approved_by="human-review-record",
        approved_at=approved_at,
        expires_at=expires_at,
        permissions=permissions,
        limits=limits or default_limits,
    )


class TestMigrationAuthorization(unittest.TestCase):
    def test_creates_exact_plan_bound_grant_with_narrower_limits(self):
        authorization = authorize()
        plan, assessment, _, _, limits = fixture()
        self.assertEqual(authorization.route_plan_digest, plan.plan_digest)
        self.assertEqual(authorization.worker_assessment_digest, assessment.assessment_digest)
        self.assertEqual(len(authorization.grants), 1)
        grant = authorization.grants[0]
        self.assertEqual(grant.transition_id, "authorization-transition")
        self.assertEqual(grant.permissions, (
            WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT,
        ))
        self.assertEqual(grant.limits, limits)
        self.assertEqual(len(authorization.authorization_digest), 64)

    def test_policy_round_trip_preserves_canonical_digest(self):
        _, _, _, policy, _ = fixture()
        encoded = serialize_migration_authorization_policy(policy)
        restored = deserialize_migration_authorization_policy(encoded)
        self.assertEqual(restored.to_document(), policy.to_document())
        self.assertEqual(restored.policy_digest, policy.policy_digest)

    def test_policy_import_rejects_digest_tampering(self):
        _, _, _, policy, _ = fixture()
        encoded = serialize_migration_authorization_policy(policy)
        tampered = encoded.replace(b"fixture-worker", b"other-worker!")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            deserialize_migration_authorization_policy(tampered)

    def test_policy_import_rejects_duplicate_json_keys(self):
        with self.assertRaisesRegex(ValueError, "invalid migration authorization policy JSON"):
            deserialize_migration_authorization_policy(b'{"schema":1,"schema":1}')

    def test_policy_import_rejects_noncanonical_whitespace(self):
        _, _, _, policy, _ = fixture()
        with self.assertRaisesRegex(ValueError, "not canonical"):
            deserialize_migration_authorization_policy(serialize_migration_authorization_policy(policy) + b" ")

    def test_policy_collection_order_does_not_change_digest(self):
        first = MigrationAuthorizationPolicy(
            allowed_permissions=(WorkerPermission.WRITE_PROJECT, WorkerPermission.READ_PROJECT),
            allowed_worker_ids=("z-worker", "a-worker"),
        )
        second = MigrationAuthorizationPolicy(
            allowed_permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
            allowed_worker_ids=("a-worker", "z-worker"),
        )
        self.assertEqual(first.policy_digest, second.policy_digest)

    def test_authorization_round_trip_is_canonical_and_digest_preserving(self):
        original = authorize()
        encoded = serialize_migration_authorization(original)
        restored = deserialize_migration_authorization(encoded)
        self.assertEqual(restored.to_document(), original.to_document())
        self.assertEqual(restored.authorization_digest, original.authorization_digest)

    def test_authorization_import_rejects_digest_tampering(self):
        encoded = serialize_migration_authorization(authorize())
        tampered = encoded.replace(b"human-review-record", b"other-review-record")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            deserialize_migration_authorization(tampered)

    def test_authorization_import_rejects_duplicate_json_keys(self):
        with self.assertRaisesRegex(ValueError, "invalid migration authorization JSON"):
            deserialize_migration_authorization(b'{"schema":1,"schema":1}')

    def test_authorization_import_rejects_noncanonical_whitespace(self):
        with self.assertRaisesRegex(ValueError, "not canonical"):
            deserialize_migration_authorization(serialize_migration_authorization(authorize()) + b" ")

    def test_authorization_is_current_only_inside_half_open_interval(self):
        authorization = authorize()
        self.assertFalse(authorization.is_current(datetime(2026, 11, 4, 17, 59, tzinfo=timezone.utc)))
        self.assertTrue(authorization.is_current(NOW))
        self.assertFalse(authorization.is_current(datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc)))

    def test_rejects_expiry_after_worker_qualification(self):
        with self.assertRaisesRegex(ValueError, "no later than"):
            authorize(
                approved_at=datetime(2026, 11, 4, 23, 50, tzinfo=timezone.utc),
                expires_at=datetime(2026, 11, 5, 0, 1, tzinfo=timezone.utc),
            )

    def test_rejects_approval_after_worker_qualification_expires(self):
        with self.assertRaisesRegex(ValueError, "not current at plan evaluation"):
            authorize(approved_at=datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc))

    def test_rejects_permission_escalation_beyond_policy(self):
        with self.assertRaisesRegex(ValueError, "authorization policy"):
            authorize(permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.NETWORK))

    def test_rejects_permission_not_declared_by_worker(self):
        plan, assessment, registry, _, limits = fixture()
        policy = MigrationAuthorizationPolicy(
            allowed_permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.PUBLISH_ARTIFACT),
            max_timeout_seconds=300, max_input_bytes=8 * 1024 * 1024,
            max_output_bytes=4 * 1024 * 1024, max_changed_files=1000,
            max_lifetime_seconds=900, allowed_worker_ids=("fixture-worker",),
        )
        with self.assertRaisesRegex(ValueError, "worker declaration"):
            authorize_migration(
                plan, assessment, registry, policy,
                approved_by="reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.PUBLISH_ARTIFACT),
                limits=limits,
            )

    def test_rejects_limits_above_policy_ceiling(self):
        with self.assertRaisesRegex(ValueError, "authorization policy"):
            authorize(limits=WorkerResourceLimits(301, 1024, 1024, 10))

    def test_rejects_limits_above_worker_manifest(self):
        with self.assertRaisesRegex(ValueError, "worker declaration"):
            authorize(limits=WorkerResourceLimits(120, 1024 * 1024, 512 * 1024, 600))

    def test_rejects_authorization_lifetime_above_policy(self):
        with self.assertRaisesRegex(ValueError, "lifetime"):
            authorize(expires_at=datetime(2026, 11, 4, 18, 16, tzinfo=timezone.utc))

    def test_rejects_no_work_assessment_for_a_route_that_has_transitions(self):
        plan, assessment, registry, policy, limits = fixture()
        forged_noop = RouteWorkerAssessment(
            route_plan_digest=plan.plan_digest,
            evaluated_at=plan.evaluated_at,
            status="NO_WORK_REQUIRED",
            evaluations=(),
            reason="Forged no-op assessment",
        )
        with self.assertRaisesRegex(ValueError, "exact ordered transitions"):
            authorize_migration(
                plan, forged_noop, registry, policy,
                approved_by="reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT,), limits=limits,
            )

    def test_rejects_worker_assessment_from_another_plan(self):
        plan, assessment, registry, policy, limits = fixture()
        with self.assertRaisesRegex(ValueError, "different route plan"):
            authorize_migration(
                plan, assessment.__class__(
                    route_plan_digest="0" * 64,
                    evaluated_at=assessment.evaluated_at,
                    status=assessment.status,
                    evaluations=assessment.evaluations,
                    reason=assessment.reason,
                ), registry, policy, approved_by="reviewer",
                approved_at=NOW, expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT,), limits=limits,
            )

    def test_rejects_worker_qualification_changed_after_assessment(self):
        plan, assessment, registry, policy, limits = fixture()
        original = registry.registrations()[0]
        altered_manifest = MigrationWorkerManifest(
            worker_id=original.manifest.worker_id,
            worker_version=original.manifest.worker_version,
            implementation_digest="sha256:" + "d" * 64,
            protocol_version=1,
            scopes=original.manifest.scopes,
            capabilities=original.manifest.capabilities,
            permissions=original.manifest.permissions,
            limits=original.manifest.limits,
        )
        altered_registry = MigrationWorkerRegistry((WorkerRegistration(
            altered_manifest, original.qualification,
        ),))
        with self.assertRaisesRegex(ValueError, "not qualified at approval"):
            authorize_migration(
                plan, assessment, altered_registry, policy,
                approved_by="reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT,), limits=limits,
            )

    def test_rejects_approval_before_plan_evaluation(self):
        with self.assertRaisesRegex(ValueError, "predate"):
            authorize(approved_at=datetime(2026, 11, 4, 17, 59, tzinfo=timezone.utc))

    def test_rejects_noncanonical_manual_grant_digest(self):
        with self.assertRaises(ValueError):
            MigrationStepGrant(
                "step", "worker", "1", "Z" * 64, "qualification", "a" * 64,
                "2026-11-05T00:00:00Z", (), WorkerResourceLimits(1, 1, 1, 1),
            )


if __name__ == "__main__":
    unittest.main()

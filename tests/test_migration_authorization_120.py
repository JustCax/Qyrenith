"""Security-boundary tests for plan-bound migration authorization."""
import atexit
import hashlib
import io
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from qyrenith_engine.approval import HostApprovalError, approve_host_request
from qyrenith_engine.trust_store import OwnerTrustStore, TrustStoreError
from qyrenith_engine.migration.snapshot import capture_project_snapshot
from qyrenith_engine.migration.workspace import create_isolated_workspace

from qyrenith_engine.migration import (
    MigrationAuthorizationPolicy,
    MigrationIdentity,
    MigrationKnowledgeClaim,
    KnowledgeCatalog,
    KnowledgeStatus,
    KnowledgeTrustPolicy,
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
    WorkerTrustPolicy,
    assess_route_workers,
    authorize_migration,
    authorize_migration_with_owner_trust,
    create_migration_step_approval_request,
    deserialize_migration_authorization,
    serialize_migration_authorization,
    deserialize_migration_authorization_policy,
    serialize_migration_authorization_policy,
    validate_migration_authorization,
    validate_migration_authorization_with_owner_trust,
    validate_migration_step_approval,
    plan_route,
)


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_DIGEST = "sha256:" + hashlib.sha256((ROOT / "qyrenith_engine/migration/knowledge.py").read_bytes()).hexdigest()
NOW = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)

_OWNER_TRUST_TEST_DIRECTORIES = []


def _cleanup_owner_trust_test_directories():
    for directory in _OWNER_TRUST_TEST_DIRECTORIES:
        directory.cleanup()


atexit.register(_cleanup_owner_trust_test_directories)
SOURCE = MigrationIdentity(
    domain="minecraft", product="minecraft", product_version="1.21",
    platform="java", loader="fabric", loader_version="0.16",
)
TARGET = MigrationIdentity(
    domain="minecraft", product="minecraft", product_version="1.21.1",
    platform="java", loader="fabric", loader_version="0.16",
)


def knowledge_catalog(valid_until="2026-12-01T00:00:00Z"):
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
            digest="sha256:" + "c" * 64,
        ),),
        verified_by="test-reviewer",
        verified_at="2026-11-01T00:00:00Z",
        valid_until=valid_until,
        verified_with="qyrenith-migration-knowledge-validator",
        verifier_version="2",
        verifier_digest=VERIFIER_DIGEST,
    )
    return KnowledgeCatalog((claim,))


def fixture(knowledge_valid_until="2026-12-01T00:00:00Z"):
    catalog = knowledge_catalog(knowledge_valid_until)
    claim = catalog.get("authorization-claim")
    assert claim is not None
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
    worker_trust = WorkerTrustPolicy(
        policy_id="authorization-fixture-worker-trust",
        reviewed_by="test-owner",
        reviewed_at="2026-11-04T00:00:00Z",
        trusted_qualification_digests=(qualification.qualification_digest,),
    )
    registry = MigrationWorkerRegistry(
        (WorkerRegistration(manifest, qualification),),
        trust_policy=worker_trust,
    )
    plan = plan_route(SOURCE, TARGET, (edge,), catalog, evaluated_at=NOW)
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


def owner_trust_store(plan, registry, catalog, *, now=NOW, expires_at=None, trust_workers=True):
    temporary = tempfile.TemporaryDirectory()
    store = OwnerTrustStore.open(Path(temporary.name) / "owner" / "trust-store.json", create=True)
    store._test_temporary_directory = temporary
    _OWNER_TRUST_TEST_DIRECTORIES.append(temporary)
    store.trust(
        "KNOWLEDGE_CATALOG", "sha256:" + catalog.content_digest,
        reviewed_by="test-owner", reviewed_at=now, expires_at=expires_at,
        rationale="Explicit test fixture owner decision",
    )
    if trust_workers:
        for registration in registry.registrations():
            store.trust(
                "WORKER_MANIFEST", "sha256:" + registration.manifest.manifest_digest,
                reviewed_by="test-owner", reviewed_at=now, expires_at=expires_at,
                rationale="Explicit test fixture worker manifest decision",
            )
            if registration.qualification is not None:
                store.trust(
                    "WORKER_QUALIFICATION",
                    "sha256:" + registration.qualification.qualification_digest,
                    reviewed_by="test-owner", reviewed_at=now, expires_at=expires_at,
                    rationale="Explicit test fixture worker qualification decision",
                )
    return store


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
        knowledge=knowledge_catalog(),
    )


class InteractiveTestTerminal(io.StringIO):
    def isatty(self):
        return True


class TestMigrationStepApproval(unittest.TestCase):
    def _approved_step(self, temporary):
        plan, assessment, registry, policy, limits = fixture()
        catalog = knowledge_catalog()
        store = owner_trust_store(plan, registry, catalog)
        authorization = authorize_migration_with_owner_trust(
            plan, assessment, registry, policy,
            trust_store=store, approved_by="test-reviewer", approved_at=NOW,
            expires_at=NOW + timedelta(minutes=10),
            permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
            limits=limits, knowledge=catalog,
        )
        source = Path(temporary) / "source"
        source.mkdir()
        (source / "README.md").write_text("baseline\n", encoding="utf-8")
        workspace_parent = Path(temporary) / "workspaces"
        workspace_parent.mkdir()
        snapshot = capture_project_snapshot(source)
        workspace = create_isolated_workspace(source, snapshot, workspace_parent, TARGET)
        grant = authorization.grants[0]
        command_digest = "e" * 64
        sandbox_profile_id = "test-linux-bwrap-profile-v1"
        sandbox_profile_digest = "f" * 64
        request = create_migration_step_approval_request(
            authorization, plan, grant, workspace, snapshot,
            command_digest=command_digest,
            sandbox_profile_id=sandbox_profile_id,
            sandbox_profile_digest=sandbox_profile_digest,
            lifetime_seconds=300, now=NOW,
        )
        challenge = f"APPROVE {request.action_type} {request.request_id} {request.nonce}"
        approval = approve_host_request(
            request, store, input_stream=InteractiveTestTerminal(challenge + "\n"),
            output_stream=InteractiveTestTerminal(), now=NOW,
        )
        return (
            plan, assessment, registry, policy, catalog, store, authorization,
            grant, workspace, snapshot, approval, command_digest,
            sandbox_profile_id, sandbox_profile_digest,
        )

    def _validate(self, values, *, now=NOW + timedelta(seconds=1), command_digest=None):
        (
            plan, assessment, registry, policy, catalog, store, authorization,
            grant, workspace, snapshot, approval, original_command,
            sandbox_profile_id, sandbox_profile_digest,
        ) = values
        validate_migration_step_approval(
            authorization, plan, assessment, registry, policy, grant,
            workspace, snapshot, approval,
            trust_store=store, knowledge=catalog,
            command_digest=original_command if command_digest is None else command_digest,
            sandbox_profile_id=sandbox_profile_id,
            sandbox_profile_digest=sandbox_profile_digest,
            now=now,
        )

    def test_step_approval_binds_plan_worker_baseline_command_and_sandbox(self):
        with tempfile.TemporaryDirectory() as temporary:
            values = self._approved_step(temporary)
            self._validate(values)
            with self.assertRaisesRegex(HostApprovalError, "already been consumed"):
                self._validate(values, now=NOW + timedelta(seconds=2))

    def test_command_substitution_is_rejected_without_consuming_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            values = self._approved_step(temporary)
            with self.assertRaisesRegex(HostApprovalError, "exact action scope"):
                self._validate(values, command_digest="9" * 64)
            self._validate(values)

    def test_modified_workspace_baseline_blocks_step_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            values = self._approved_step(temporary)
            workspace = values[8]
            (Path(workspace.project_path) / "README.md").write_text(
                "modified after approval\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "no longer matches"):
                self._validate(values)

class TestOwnerTrustAuthorization(unittest.TestCase):
    def test_owner_store_allows_only_exact_catalog_manifest_and_qualification(self):
        plan, assessment, registry, policy, limits = fixture()
        catalog = knowledge_catalog()
        store = owner_trust_store(plan, registry, catalog)
        authorization = authorize_migration_with_owner_trust(
            plan, assessment, registry, policy,
            trust_store=store,
            approved_by="test-reviewer", approved_at=NOW,
            expires_at=NOW + timedelta(minutes=10),
            permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
            limits=limits, knowledge=catalog,
        )
        self.assertEqual(authorization.route_plan_digest, plan.plan_digest)

    def test_missing_worker_manifest_trust_blocks_authorization(self):
        plan, assessment, registry, policy, limits = fixture()
        catalog = knowledge_catalog()
        store = owner_trust_store(plan, registry, catalog, trust_workers=False)
        with self.assertRaisesRegex(TrustStoreError, "WORKER_MANIFEST"):
            authorize_migration_with_owner_trust(
                plan, assessment, registry, policy,
                trust_store=store, approved_by="test-reviewer", approved_at=NOW,
                expires_at=NOW + timedelta(minutes=10),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=limits, knowledge=catalog,
            )

    def test_revoked_worker_qualification_blocks_authorization(self):
        plan, assessment, registry, policy, limits = fixture()
        catalog = knowledge_catalog()
        store = owner_trust_store(plan, registry, catalog)
        qualification = registry.registrations()[0].qualification
        store.revoke(
            "WORKER_QUALIFICATION", "sha256:" + qualification.qualification_digest,
            reviewed_by="test-owner", reviewed_at=NOW + timedelta(seconds=1),
            rationale="Adversarial revocation fixture",
        )
        with self.assertRaisesRegex(TrustStoreError, "WORKER_QUALIFICATION"):
            authorize_migration_with_owner_trust(
                plan, assessment, registry, policy,
                trust_store=store, approved_by="test-reviewer", approved_at=NOW + timedelta(seconds=2),
                expires_at=NOW + timedelta(minutes=10),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=limits, knowledge=catalog,
            )

    def test_expired_owner_trust_blocks_authorization(self):
        plan, assessment, registry, policy, limits = fixture()
        catalog = knowledge_catalog()
        expiry = NOW + timedelta(seconds=1)
        store = owner_trust_store(plan, registry, catalog, expires_at=expiry)
        with self.assertRaisesRegex(TrustStoreError, "not currently trusted"):
            authorize_migration_with_owner_trust(
                plan, assessment, registry, policy,
                trust_store=store, approved_by="test-reviewer", approved_at=NOW + timedelta(seconds=2),
                expires_at=NOW + timedelta(minutes=10),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=limits, knowledge=catalog,
            )

    def test_validation_rechecks_owner_trust_and_honors_revocation(self):
        plan, assessment, registry, policy, limits = fixture()
        catalog = knowledge_catalog()
        store = owner_trust_store(plan, registry, catalog)
        authorization = authorize_migration_with_owner_trust(
            plan, assessment, registry, policy,
            trust_store=store, approved_by="test-reviewer", approved_at=NOW,
            expires_at=NOW + timedelta(minutes=10),
            permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
            limits=limits, knowledge=catalog,
        )
        qualification = registry.registrations()[0].qualification
        store.revoke(
            "WORKER_QUALIFICATION", "sha256:" + qualification.qualification_digest,
            reviewed_by="test-owner", reviewed_at=NOW + timedelta(seconds=1),
            rationale="Revoke after authorization",
        )
        with self.assertRaisesRegex(TrustStoreError, "WORKER_QUALIFICATION"):
            validate_migration_authorization_with_owner_trust(
                authorization, plan, assessment, registry, policy,
                trust_store=store, knowledge=catalog, now=NOW + timedelta(seconds=2),
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

    def test_authorization_rejects_untrusted_worker_qualification(self):
        plan, _, registry, policy, limits = fixture()
        untrusted_registry = MigrationWorkerRegistry(registry.registrations())
        untrusted_assessment = assess_route_workers(plan, untrusted_registry)
        self.assertEqual(untrusted_assessment.status, "UNKNOWN")
        with self.assertRaisesRegex(ValueError, "worker gate"):
            authorize_migration(
                plan, untrusted_assessment, untrusted_registry, policy,
                approved_by="test-reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=limits,
                knowledge=knowledge_catalog(),
            )

    def test_execution_gate_accepts_current_exact_authorization(self):
        authorization = authorize()
        plan, assessment, registry, policy, _ = fixture()
        self.assertIsNone(validate_migration_authorization(
            authorization, plan, assessment, registry, policy, knowledge=knowledge_catalog(), now=NOW,
        ))

    def test_authorization_rechecks_knowledge_expiry(self):
        valid_until = "2026-11-04T18:01:00Z"
        plan, assessment, registry, policy, limits = fixture(valid_until)
        catalog = knowledge_catalog(valid_until)

        with self.assertRaisesRegex(ValueError, "not usable at approval time"):
            authorize_migration(
                plan, assessment, registry, policy,
                approved_by="test-reviewer",
                approved_at=datetime(2026, 11, 4, 18, 2, tzinfo=timezone.utc),
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=limits, knowledge=catalog,
            )

        authorization = authorize_migration(
            plan, assessment, registry, policy,
            approved_by="test-reviewer",
            approved_at=datetime(2026, 11, 4, 18, 0, 30, tzinfo=timezone.utc),
            expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
            permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
            limits=limits, knowledge=catalog,
        )
        with self.assertRaisesRegex(ValueError, "not usable at validation time"):
            validate_migration_authorization(
                authorization, plan, assessment, registry, policy,
                knowledge=catalog,
                now=datetime(2026, 11, 4, 18, 2, tzinfo=timezone.utc),
            )

    def test_authorization_rejects_revoked_knowledge_trust(self):
        authorization = authorize()
        plan, assessment, registry, policy, limits = fixture()
        revoked_catalog = KnowledgeCatalog.from_json_bytes(
            knowledge_catalog().to_json_bytes()
        )
        self.assertFalse(revoked_catalog.is_trusted)
        with self.assertRaisesRegex(ValueError, "knowledge trust policy"):
            authorize_migration(
                plan, assessment, registry, policy,
                approved_by="test-reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=limits, knowledge=revoked_catalog,
            )
        with self.assertRaisesRegex(ValueError, "knowledge trust policy"):
            validate_migration_authorization(
                authorization, plan, assessment, registry, policy,
                knowledge=revoked_catalog, now=NOW,
            )

    def test_authorization_rejects_knowledge_trust_policy_substitution(self):
        plan, assessment, registry, policy, limits = fixture()
        catalog_bytes = knowledge_catalog().to_json_bytes()
        untrusted = KnowledgeCatalog.from_json_bytes(catalog_bytes)
        changed_policy = KnowledgeTrustPolicy(
            policy_id="different-knowledge-trust-policy",
            reviewed_by="test-owner",
            reviewed_at="2026-11-04T00:00:00Z",
            trusted_catalog_digests=(untrusted.content_digest,),
        )
        substituted = KnowledgeCatalog.from_json_bytes(
            catalog_bytes, trust_policy=changed_policy
        )
        with self.assertRaisesRegex(ValueError, "knowledge trust decision changed"):
            authorize_migration(
                plan, assessment, registry, policy,
                approved_by="test-reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=limits, knowledge=substituted,
            )

    def test_execution_gate_rejects_expired_authorization(self):
        authorization = authorize()
        plan, assessment, registry, policy, _ = fixture()
        with self.assertRaisesRegex(ValueError, "not currently valid"):
            validate_migration_authorization(
                authorization, plan, assessment, registry, policy,
                knowledge=knowledge_catalog(),
                now=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
            )

    def test_execution_gate_rejects_policy_substitution(self):
        authorization = authorize()
        plan, assessment, registry, policy, _ = fixture()
        changed_policy = MigrationAuthorizationPolicy(
            allowed_permissions=(WorkerPermission.READ_PROJECT,),
            max_timeout_seconds=300, max_input_bytes=8 * 1024 * 1024,
            max_output_bytes=4 * 1024 * 1024, max_changed_files=1000,
            max_lifetime_seconds=900, allowed_worker_ids=("fixture-worker",),
        )
        with self.assertRaisesRegex(ValueError, "policy digest"):
            validate_migration_authorization(
                authorization, plan, assessment, registry, changed_policy, knowledge=knowledge_catalog(), now=NOW,
            )

    def test_execution_gate_rejects_worker_manifest_substitution(self):
        authorization = authorize()
        plan, assessment, registry, policy, _ = fixture()
        original = registry.registrations()[0]
        replacement = MigrationWorkerManifest(
            worker_id=original.manifest.worker_id,
            worker_version=original.manifest.worker_version,
            implementation_digest="sha256:" + "e" * 64,
            protocol_version=1, scopes=original.manifest.scopes,
            capabilities=original.manifest.capabilities,
            permissions=original.manifest.permissions, limits=original.manifest.limits,
        )
        replacement_registry = MigrationWorkerRegistry(
            (WorkerRegistration(replacement, original.qualification),),
            trust_policy=registry._trust_policy,
        )
        with self.assertRaisesRegex(ValueError, "not currently qualified"):
            validate_migration_authorization(
                authorization, plan, assessment, replacement_registry, policy, knowledge=knowledge_catalog(), now=NOW,
            )

    def test_execution_gate_rejects_worker_trust_policy_substitution(self):
        authorization = authorize()
        plan, assessment, registry, policy, _ = fixture()
        registration = registry.registrations()
        changed_trust = WorkerTrustPolicy(
            policy_id="different-worker-trust-policy",
            reviewed_by="test-owner",
            reviewed_at="2026-11-04T00:00:00Z",
            trusted_qualification_digests=(
                registration[0].qualification.qualification_digest,
            ),
        )
        substituted_registry = MigrationWorkerRegistry(
            registration, trust_policy=changed_trust
        )
        with self.assertRaisesRegex(ValueError, "trust policy changed"):
            validate_migration_authorization(
                authorization, plan, assessment, substituted_registry, policy, knowledge=knowledge_catalog(), now=NOW,
            )
        with self.assertRaisesRegex(ValueError, "trust policy changed"):
            authorize_migration(
                plan, assessment, substituted_registry, policy,
                approved_by="test-reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT, WorkerPermission.WRITE_PROJECT),
                limits=WorkerResourceLimits(120, 1024 * 1024, 512 * 1024, 100),
                knowledge=knowledge_catalog(),
            )

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
        with self.assertRaisesRegex(ValueError, "not qualified at approval time"):
            authorize(approved_at=datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc),
                      expires_at=datetime(2026, 11, 5, 0, 1, tzinfo=timezone.utc))

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
                knowledge=knowledge_catalog(),
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
            trust_policy_digest=registry.trust_policy_digest,
        )
        with self.assertRaisesRegex(ValueError, "exact ordered transitions"):
            authorize_migration(
                plan, forged_noop, registry, policy,
                approved_by="reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT,), limits=limits,
                knowledge=knowledge_catalog(),
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
                    trust_policy_digest=assessment.trust_policy_digest,
                ), registry, policy, approved_by="reviewer",
                approved_at=NOW, expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT,), limits=limits,
                knowledge=knowledge_catalog(),
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
        altered_registry = MigrationWorkerRegistry(
            (WorkerRegistration(altered_manifest, original.qualification),),
            trust_policy=registry._trust_policy,
        )
        with self.assertRaisesRegex(ValueError, "not current at plan evaluation"):
            authorize_migration(
                plan, assessment, altered_registry, policy,
                approved_by="reviewer", approved_at=NOW,
                expires_at=datetime(2026, 11, 4, 18, 10, tzinfo=timezone.utc),
                permissions=(WorkerPermission.READ_PROJECT,), limits=limits,
                knowledge=knowledge_catalog(),
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

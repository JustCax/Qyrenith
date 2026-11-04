"""Domain-neutral migration planning primitives.

Execution, filesystem mutation, worker dispatch, and assurance persistence are
intentionally not implied by route planning.
"""
from .assurance import AssuranceLedger, AssuranceLedgerError, LedgerLockedError, verify_assurance_chain
from .authorization import (MigrationAuthorization, MigrationAuthorizationPolicy, MigrationStepGrant, authorize_migration, deserialize_migration_authorization, serialize_migration_authorization, deserialize_migration_authorization_policy, serialize_migration_authorization_policy, validate_migration_authorization)
from .knowledge import (
    EvidenceReference,
    KnowledgeCatalog,
    KnowledgeStatus,
    MigrationKnowledgeClaim,
    deserialize_knowledge_catalog,
    serialize_knowledge_catalog,
)
from .model import MigrationIdentity, MigrationTransition, TransitionKind
from .planner import MultiTargetPlan, RoutePlan, plan_route, plan_targets
from .snapshot import (ProjectSnapshot, SnapshotEntry, SnapshotError, SnapshotLimits, SnapshotVerification, capture_project_snapshot, deserialize_project_snapshot, serialize_project_snapshot, verify_project_snapshot)
from .worker import (
    MigrationWorkerManifest, MigrationWorkerRegistry, RouteWorkerAssessment,
    WorkerPermission, WorkerQualification, WorkerRegistration, WorkerResolution,
    WorkerResourceLimits, WorkerScope, assess_route_workers, deserialize_worker_manifest,
    deserialize_worker_qualification, serialize_worker_manifest,
    serialize_worker_qualification,
)

__all__ = [
    "AssuranceLedger", "AssuranceLedgerError", "LedgerLockedError", "verify_assurance_chain",
    "MigrationAuthorization", "MigrationAuthorizationPolicy", "MigrationStepGrant", "authorize_migration",
    "deserialize_migration_authorization", "serialize_migration_authorization",
    "deserialize_migration_authorization_policy", "serialize_migration_authorization_policy",
    "validate_migration_authorization",
    "EvidenceReference",
    "KnowledgeCatalog",
    "KnowledgeStatus",
    "MigrationIdentity",
    "MigrationKnowledgeClaim",
    "deserialize_knowledge_catalog",
    "serialize_knowledge_catalog",
    "MigrationTransition",
    "MultiTargetPlan",
    "RoutePlan",
    "TransitionKind",
    "plan_route",
    "plan_targets",
    "MigrationWorkerManifest", "MigrationWorkerRegistry", "RouteWorkerAssessment",
    "assess_route_workers", "WorkerPermission",
    "WorkerQualification", "WorkerRegistration", "WorkerResolution",
    "WorkerResourceLimits", "WorkerScope", "deserialize_worker_manifest",
    "deserialize_worker_qualification", "serialize_worker_manifest",
    "serialize_worker_qualification",
    "ProjectSnapshot", "SnapshotEntry", "SnapshotError", "SnapshotLimits",
    "SnapshotVerification", "capture_project_snapshot", "verify_project_snapshot",
    "serialize_project_snapshot", "deserialize_project_snapshot",
]

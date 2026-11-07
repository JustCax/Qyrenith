"""Domain-neutral migration planning primitives.

Execution, filesystem mutation, worker dispatch, and assurance persistence are
intentionally not implied by route planning.
"""
from .assurance import AssuranceLedger, AssuranceLedgerError, LedgerLockedError, verify_assurance_chain
from .authorization import (MigrationAuthorization, MigrationAuthorizationPolicy, MigrationStepGrant, authorize_migration, authorize_migration_with_owner_trust, deserialize_migration_authorization, serialize_migration_authorization, deserialize_migration_authorization_policy, serialize_migration_authorization_policy, validate_migration_authorization, validate_migration_authorization_with_owner_trust, migration_step_approval_scope, create_migration_step_approval_request, validate_migration_step_approval)
from .knowledge import (
    EvidenceReference,
    KnowledgeCatalog,
    KnowledgeStatus,
    KnowledgeTrustPolicy,
    MigrationKnowledgeClaim,
    deserialize_knowledge_catalog,
    serialize_knowledge_catalog,
)
from .model import MigrationIdentity, MigrationTransition, TransitionKind
from .planner import MultiTargetPlan, RoutePlan, plan_route, plan_targets
from .preparation import MultiTargetWorkspaceBatch, prepare_multi_target_workspaces
from .qdas_step import record_migration_step_with_qdas
from .snapshot import (ProjectSnapshot, SnapshotEntry, SnapshotError, SnapshotLimits, SnapshotVerification, capture_project_snapshot, deserialize_project_snapshot, serialize_project_snapshot, verify_project_snapshot)
from .workspace import (WorkspaceDescriptor, WorkspaceError, create_isolated_workspace, create_isolated_workspaces, deserialize_workspace_descriptor, serialize_workspace_descriptor, verify_workspace_baseline)
from .worker import (
    MigrationWorkerManifest, MigrationWorkerRegistry, RouteWorkerAssessment,
    WorkerPermission, WorkerQualification, WorkerRegistration, WorkerResolution,
    WorkerResourceLimits, WorkerScope, WorkerTrustPolicy, assess_route_workers, deserialize_worker_manifest,
    deserialize_worker_qualification, serialize_worker_manifest,
    serialize_worker_qualification,
)

__all__ = [
    "AssuranceLedger", "AssuranceLedgerError", "LedgerLockedError", "verify_assurance_chain",
    "MigrationAuthorization", "MigrationAuthorizationPolicy", "MigrationStepGrant", "authorize_migration",
    "deserialize_migration_authorization", "serialize_migration_authorization",
    "deserialize_migration_authorization_policy", "serialize_migration_authorization_policy",
    "validate_migration_authorization",
    "authorize_migration_with_owner_trust", "validate_migration_authorization_with_owner_trust",
    "migration_step_approval_scope", "create_migration_step_approval_request",
    "validate_migration_step_approval",
    "EvidenceReference",
    "KnowledgeCatalog",
    "KnowledgeStatus",
    "KnowledgeTrustPolicy",
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
    "MultiTargetWorkspaceBatch", "prepare_multi_target_workspaces",
    "record_migration_step_with_qdas",
    "MigrationWorkerManifest", "MigrationWorkerRegistry", "RouteWorkerAssessment",
    "assess_route_workers", "WorkerPermission",
    "WorkerQualification", "WorkerRegistration", "WorkerResolution",
    "WorkerResourceLimits", "WorkerScope", "WorkerTrustPolicy", "deserialize_worker_manifest",
    "deserialize_worker_qualification", "serialize_worker_manifest",
    "serialize_worker_qualification",
    "ProjectSnapshot", "SnapshotEntry", "SnapshotError", "SnapshotLimits",
    "SnapshotVerification", "capture_project_snapshot", "verify_project_snapshot",
    "serialize_project_snapshot", "deserialize_project_snapshot",
    "WorkspaceDescriptor", "WorkspaceError", "create_isolated_workspace", "create_isolated_workspaces",
    "verify_workspace_baseline", "serialize_workspace_descriptor",
    "deserialize_workspace_descriptor",
]

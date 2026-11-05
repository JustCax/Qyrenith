"""Additive deterministic engineering capabilities for Qyrenith."""
from .analysis import analyze_project, build_change_impact, compare_baselines
from .approval import (HostApproval, HostApprovalError, HostApprovalRequest, approve_host_request, create_host_approval_request, validate_host_approval)
from .boundary import inspect_project_boundary
from .execution import run_bounded_process, run_bounded_worker
from .trust_store import OwnerTrustStore, TrustDecision, TrustStoreError, default_trust_store_path
from .migration import (
    MigrationAuthorization, MigrationAuthorizationPolicy, MigrationStepGrant, authorize_migration,
    authorize_migration_with_owner_trust, validate_migration_authorization_with_owner_trust,
    deserialize_migration_authorization, serialize_migration_authorization,
    deserialize_migration_authorization_policy, serialize_migration_authorization_policy,
    ProjectSnapshot, SnapshotEntry, SnapshotError, SnapshotLimits, SnapshotVerification,
    capture_project_snapshot, deserialize_project_snapshot, serialize_project_snapshot,
    verify_project_snapshot,
    WorkspaceDescriptor, WorkspaceError, create_isolated_workspace, create_isolated_workspaces,
    deserialize_workspace_descriptor, serialize_workspace_descriptor, verify_workspace_baseline,
    validate_migration_authorization,
    AssuranceLedger, AssuranceLedgerError, LedgerLockedError, verify_assurance_chain,
    EvidenceReference, KnowledgeCatalog, KnowledgeStatus, MigrationIdentity,
    MigrationKnowledgeClaim, MigrationTransition, MultiTargetPlan, RoutePlan,
    TransitionKind, deserialize_knowledge_catalog, plan_route, plan_targets,
    serialize_knowledge_catalog, MigrationWorkerManifest, MigrationWorkerRegistry,
    RouteWorkerAssessment, assess_route_workers, WorkerPermission, WorkerQualification, WorkerRegistration, WorkerResolution,
    WorkerResourceLimits, WorkerScope, deserialize_worker_manifest,
    deserialize_worker_qualification, serialize_worker_manifest, serialize_worker_qualification,
)

__all__ = [
    "analyze_project", "build_change_impact", "compare_baselines",
    "HostApproval", "HostApprovalError", "HostApprovalRequest",
    "approve_host_request", "create_host_approval_request", "validate_host_approval",
    "inspect_project_boundary", "run_bounded_process", "run_bounded_worker",
    "OwnerTrustStore", "TrustDecision", "TrustStoreError", "default_trust_store_path",
    "AssuranceLedger", "AssuranceLedgerError", "LedgerLockedError", "verify_assurance_chain",
    "MigrationAuthorization", "MigrationAuthorizationPolicy", "MigrationStepGrant", "authorize_migration",
    "deserialize_migration_authorization", "serialize_migration_authorization",
    "deserialize_migration_authorization_policy", "serialize_migration_authorization_policy",
    "validate_migration_authorization",
    "authorize_migration_with_owner_trust", "validate_migration_authorization_with_owner_trust",
    "ProjectSnapshot", "SnapshotEntry", "SnapshotError", "SnapshotLimits",
    "SnapshotVerification", "capture_project_snapshot", "verify_project_snapshot",
    "serialize_project_snapshot", "deserialize_project_snapshot",
    "WorkspaceDescriptor", "WorkspaceError", "create_isolated_workspace", "create_isolated_workspaces",
    "verify_workspace_baseline", "serialize_workspace_descriptor",
    "deserialize_workspace_descriptor",
    "EvidenceReference", "KnowledgeCatalog", "KnowledgeStatus",
    "MigrationIdentity", "MigrationKnowledgeClaim", "MigrationTransition",
    "MultiTargetPlan", "RoutePlan", "TransitionKind", "plan_route", "plan_targets",
    "deserialize_knowledge_catalog", "serialize_knowledge_catalog",
    "MigrationWorkerManifest", "MigrationWorkerRegistry", "RouteWorkerAssessment",
    "assess_route_workers", "WorkerPermission",
    "WorkerQualification", "WorkerRegistration", "WorkerResolution",
    "WorkerResourceLimits", "WorkerScope", "deserialize_worker_manifest",
    "deserialize_worker_qualification", "serialize_worker_manifest", "serialize_worker_qualification",
]

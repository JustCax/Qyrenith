"""Plan-bound, time-bounded migration authorization.

Authorization is an explicit approval record, not an execution mechanism. This
module never launches workers, mutates projects, or authenticates approver identity.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import json
from typing import Any

from .knowledge import KnowledgeCatalog, strict_object_pairs
from .planner import RoutePlan
from ..trust_store import OwnerTrustStore
from .worker import (
    MigrationWorkerRegistry,
    RouteWorkerAssessment,
    WorkerPermission,
    WorkerResourceLimits,
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _instant(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ValueError(f"{field} must be a bounded ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat().replace("+00:00", "Z")
    if canonical != value:
        raise ValueError(f"{field} must use canonical UTC format")
    return parsed


def _utc(value: datetime, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_int(value: object, field: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{field} must be an integer between 1 and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class MigrationAuthorizationPolicy:
    """Local policy ceiling; policy data is not a user identity or signature."""

    allowed_permissions: tuple[WorkerPermission, ...]
    max_timeout_seconds: int = 300
    max_input_bytes: int = 8 * 1024 * 1024
    max_output_bytes: int = 4 * 1024 * 1024
    max_changed_files: int = 1000
    max_lifetime_seconds: int = 900
    allowed_worker_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_permissions, (tuple, list)) or any(
            not isinstance(item, WorkerPermission) for item in self.allowed_permissions
        ):
            raise ValueError("allowed_permissions must contain WorkerPermission values")
        permissions = tuple(sorted(set(self.allowed_permissions), key=lambda item: item.value))
        if len(permissions) != len(self.allowed_permissions):
            raise ValueError("allowed_permissions must be unique")
        object.__setattr__(self, "allowed_permissions", permissions)
        for field, maximum in (
            ("max_timeout_seconds", 3600), ("max_input_bytes", 64 * 1024 * 1024),
            ("max_output_bytes", 16 * 1024 * 1024), ("max_changed_files", 100_000),
            ("max_lifetime_seconds", 86_400),
        ):
            _bounded_int(getattr(self, field), field, maximum)
        if not isinstance(self.allowed_worker_ids, (tuple, list)):
            raise ValueError("allowed_worker_ids must be a sequence")
        workers = tuple(self.allowed_worker_ids)
        if len(workers) > 10_000:
            raise ValueError("allowed_worker_ids exceeds the 10000-entry limit")
        if any(not isinstance(item, str) or not item.strip() or len(item) > 256 for item in workers):
            raise ValueError("allowed worker IDs must be non-empty bounded strings")
        if len(workers) != len(set(workers)):
            raise ValueError("allowed worker IDs must be unique")
        object.__setattr__(self, "allowed_worker_ids", tuple(sorted(workers)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "allowed_permissions": [item.value for item in self.allowed_permissions],
            "max_timeout_seconds": self.max_timeout_seconds,
            "max_input_bytes": self.max_input_bytes,
            "max_output_bytes": self.max_output_bytes,
            "max_changed_files": self.max_changed_files,
            "max_lifetime_seconds": self.max_lifetime_seconds,
            "allowed_worker_ids": list(self.allowed_worker_ids),
        }

    @property
    def policy_digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self.to_dict(), "policy_digest": self.policy_digest}

    def to_json_bytes(self) -> bytes:
        return _canonical(self.to_document()) + b"\n"

    @classmethod
    def from_document(cls, document: object) -> "MigrationAuthorizationPolicy":
        expected = {
            "schema", "allowed_permissions", "max_timeout_seconds", "max_input_bytes",
            "max_output_bytes", "max_changed_files", "max_lifetime_seconds",
            "allowed_worker_ids", "policy_digest",
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise ValueError("migration authorization policy has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise ValueError("unsupported migration authorization policy schema")
        payload = {key: value for key, value in document.items() if key != "policy_digest"}
        if not isinstance(document["policy_digest"], str) or hashlib.sha256(_canonical(payload)).hexdigest() != document["policy_digest"]:
            raise ValueError("migration authorization policy digest mismatch")
        if not isinstance(document["allowed_permissions"], list) or not isinstance(document["allowed_worker_ids"], list):
            raise ValueError("policy permissions and worker IDs must be arrays")
        try:
            permissions = tuple(WorkerPermission(value) for value in document["allowed_permissions"])
        except (ValueError, TypeError) as exc:
            raise ValueError("policy contains an unknown worker permission") from exc
        policy = cls(
            allowed_permissions=permissions,
            max_timeout_seconds=document["max_timeout_seconds"],
            max_input_bytes=document["max_input_bytes"],
            max_output_bytes=document["max_output_bytes"],
            max_changed_files=document["max_changed_files"],
            max_lifetime_seconds=document["max_lifetime_seconds"],
            allowed_worker_ids=tuple(document["allowed_worker_ids"]),
        )
        if policy.to_document() != document:
            raise ValueError("migration authorization policy is not canonical")
        return policy

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "MigrationAuthorizationPolicy":
        if isinstance(data, bytes):
            if len(data) > 4 * 1024 * 1024:
                raise ValueError("migration authorization policy exceeds the 4 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("migration authorization policy must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 4 * 1024 * 1024:
                raise ValueError("migration authorization policy exceeds the 4 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source, object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid migration authorization policy JSON") from exc
        canonical = _canonical(document)
        if source.encode("utf-8") not in {canonical, canonical + b"\n"}:
            raise ValueError("migration authorization policy JSON is not canonical")
        return cls.from_document(document)

    def limits(self) -> WorkerResourceLimits:
        return WorkerResourceLimits(
            self.max_timeout_seconds, self.max_input_bytes,
            self.max_output_bytes, self.max_changed_files,
        )


@dataclass(frozen=True, slots=True)
class MigrationStepGrant:
    transition_id: str
    worker_id: str
    worker_version: str
    manifest_digest: str
    qualification_id: str
    qualification_digest: str
    qualification_valid_until: str
    permissions: tuple[WorkerPermission, ...]
    limits: WorkerResourceLimits

    def __post_init__(self) -> None:
        for field, limit in (("transition_id", 256), ("worker_id", 256),
                             ("worker_version", 128), ("qualification_id", 256)):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{field} must be a non-empty bounded string")
        for field in ("manifest_digest", "qualification_digest"):
            value = getattr(self, field)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{field} must be a lowercase SHA-256 digest")
        _instant(self.qualification_valid_until, "qualification_valid_until")
        if not isinstance(self.permissions, (tuple, list)) or any(
            not isinstance(item, WorkerPermission) for item in self.permissions
        ):
            raise ValueError("grant permissions must contain WorkerPermission values")
        normalized = tuple(sorted(set(self.permissions), key=lambda item: item.value))
        if len(normalized) != len(self.permissions):
            raise ValueError("grant permissions must be unique")
        object.__setattr__(self, "permissions", normalized)
        if not isinstance(self.limits, WorkerResourceLimits):
            raise ValueError("grant limits must be WorkerResourceLimits")

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "worker_id": self.worker_id,
            "worker_version": self.worker_version,
            "manifest_digest": self.manifest_digest,
            "qualification_id": self.qualification_id,
            "qualification_digest": self.qualification_digest,
            "qualification_valid_until": self.qualification_valid_until,
            "permissions": [item.value for item in self.permissions],
            "limits": self.limits.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class MigrationAuthorization:
    route_plan_digest: str
    worker_assessment_digest: str
    policy_digest: str
    approved_by: str
    approved_at: str
    expires_at: str
    grants: tuple[MigrationStepGrant, ...]

    def __post_init__(self) -> None:
        for field in ("route_plan_digest", "worker_assessment_digest", "policy_digest"):
            value = getattr(self, field)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{field} must be a lowercase SHA-256 digest")
        if not isinstance(self.approved_by, str) or not self.approved_by.strip() or len(self.approved_by) > 256:
            raise ValueError("approved_by must be a non-empty bounded attribution string")
        approved = _instant(self.approved_at, "approved_at")
        expires = _instant(self.expires_at, "expires_at")
        if expires <= approved:
            raise ValueError("expires_at must be later than approved_at")
        if not isinstance(self.grants, (tuple, list)) or len(self.grants) > 10_000 or any(
            not isinstance(item, MigrationStepGrant) for item in self.grants
        ):
            raise ValueError("grants must contain at most 10000 MigrationStepGrant values")
        ids = [item.transition_id for item in self.grants]
        if len(ids) != len(set(ids)):
            raise ValueError("authorization contains duplicate transition grants")
        object.__setattr__(self, "grants", tuple(self.grants))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "route_plan_digest": self.route_plan_digest,
            "worker_assessment_digest": self.worker_assessment_digest,
            "policy_digest": self.policy_digest,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "grants": [item.to_dict() for item in self.grants],
        }

    @property
    def authorization_digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self.to_dict(), "authorization_digest": self.authorization_digest}

    def to_json_bytes(self) -> bytes:
        return _canonical(self.to_document()) + b"\n"

    @classmethod
    def from_document(cls, document: object) -> "MigrationAuthorization":
        expected = {
            "schema", "route_plan_digest", "worker_assessment_digest", "policy_digest",
            "approved_by", "approved_at", "expires_at", "grants", "authorization_digest",
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise ValueError("migration authorization has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise ValueError("unsupported migration authorization schema")
        payload = {key: value for key, value in document.items() if key != "authorization_digest"}
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        if document["authorization_digest"] != digest:
            raise ValueError("migration authorization digest mismatch")
        grant_data = document["grants"]
        if not isinstance(grant_data, list) or len(grant_data) > 10_000:
            raise ValueError("migration authorization grants must be a bounded array")
        grants = []
        for item in grant_data:
            expected_grant = {
                "transition_id", "worker_id", "worker_version", "manifest_digest",
                "qualification_id", "qualification_digest", "qualification_valid_until",
                "permissions", "limits",
            }
            if not isinstance(item, dict) or set(item) != expected_grant:
                raise ValueError("migration authorization grant has missing or unexpected fields")
            if not isinstance(item["permissions"], list) or not isinstance(item["limits"], dict):
                raise ValueError("migration authorization grant permissions and limits must be objects/arrays")
            if set(item["limits"]) != {
                "timeout_seconds", "max_input_bytes", "max_output_bytes", "max_changed_files"
            }:
                raise ValueError("migration authorization grant limits have unexpected fields")
            try:
                permissions = tuple(WorkerPermission(value) for value in item["permissions"])
            except (ValueError, TypeError) as exc:
                raise ValueError("migration authorization grant contains an unknown permission") from exc
            grants.append(MigrationStepGrant(
                transition_id=item["transition_id"],
                worker_id=item["worker_id"],
                worker_version=item["worker_version"],
                manifest_digest=item["manifest_digest"],
                qualification_id=item["qualification_id"],
                qualification_digest=item["qualification_digest"],
                qualification_valid_until=item["qualification_valid_until"],
                permissions=permissions,
                limits=WorkerResourceLimits(**item["limits"]),
            ))
        authorization = cls(
            route_plan_digest=document["route_plan_digest"],
            worker_assessment_digest=document["worker_assessment_digest"],
            policy_digest=document["policy_digest"],
            approved_by=document["approved_by"],
            approved_at=document["approved_at"],
            expires_at=document["expires_at"],
            grants=tuple(grants),
        )
        if authorization.to_document() != document:
            raise ValueError("migration authorization is not in canonical form")
        return authorization

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "MigrationAuthorization":
        if isinstance(data, bytes):
            if len(data) > 16 * 1024 * 1024:
                raise ValueError("migration authorization exceeds the 16 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("migration authorization must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 16 * 1024 * 1024:
                raise ValueError("migration authorization exceeds the 16 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source, object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid migration authorization JSON") from exc
        canonical = _canonical(document)
        if source.encode("utf-8") not in {canonical, canonical + b"\n"}:
            raise ValueError("migration authorization JSON is not canonical")
        return cls.from_document(document)

    def is_current(self, now: datetime) -> bool:
        instant = _utc(now, "now")
        return _instant(self.approved_at, "approved_at") <= _instant(instant, "now") < _instant(self.expires_at, "expires_at")


def authorize_migration(
    plan: RoutePlan,
    assessment: RouteWorkerAssessment,
    registry: MigrationWorkerRegistry,
    policy: MigrationAuthorizationPolicy,
    *,
    approved_by: str,
    approved_at: datetime,
    expires_at: datetime,
    permissions: tuple[WorkerPermission, ...],
    limits: WorkerResourceLimits,
    knowledge: KnowledgeCatalog,
) -> MigrationAuthorization:
    """Create a short-lived authorization after fresh knowledge and worker revalidation.

    The approval attribution is caller-supplied metadata. This function does not
    authenticate the human, persist an approval, launch a worker, or enforce OS
    permissions/resource limits. An executor must independently enforce every grant.
    """
    if not isinstance(plan, RoutePlan):
        raise TypeError("plan must be a RoutePlan")
    if not isinstance(assessment, RouteWorkerAssessment):
        raise TypeError("assessment must be a RouteWorkerAssessment")
    if not isinstance(registry, MigrationWorkerRegistry):
        raise TypeError("registry must be a MigrationWorkerRegistry")
    if not isinstance(policy, MigrationAuthorizationPolicy):
        raise TypeError("policy must be a MigrationAuthorizationPolicy")
    if not isinstance(knowledge, KnowledgeCatalog):
        raise TypeError("knowledge must be a KnowledgeCatalog")
    if plan.status != "PLANNED" or assessment.status not in {"QUALIFIED", "NO_WORK_REQUIRED"}:
        raise ValueError("only a PLANNED route with a satisfied worker gate can be authorized")
    if assessment.route_plan_digest != plan.plan_digest:
        raise ValueError("worker assessment belongs to a different route plan")
    if assessment.evaluated_at != plan.evaluated_at:
        raise ValueError("worker assessment timestamp does not match the route plan")
    if assessment.trust_policy_digest != registry.trust_policy_digest:
        raise ValueError("worker trust policy changed after route assessment")
    assessed_transitions = tuple(item[0] for item in assessment.evaluations)
    if assessed_transitions != plan.transitions:
        raise ValueError("worker assessment must cover the exact ordered transitions in the route plan")
    if plan.transitions and assessment.status != "QUALIFIED":
        raise ValueError("a route with work required must have a QUALIFIED worker assessment")
    if not plan.transitions and assessment.status != "NO_WORK_REQUIRED":
        raise ValueError("a no-op route must use the NO_WORK_REQUIRED worker assessment")
    approved_text = _utc(approved_at, "approved_at")
    expiry_text = _utc(expires_at, "expires_at")
    approved = _instant(approved_text, "approved_at")
    expiry = _instant(expiry_text, "expires_at")
    planned = _instant(plan.evaluated_at, "plan.evaluated_at")
    if knowledge.content_digest != plan.knowledge_digest:
        raise ValueError("knowledge catalog changed after route planning")
    if not knowledge.is_trusted_at(approved):
        raise ValueError("knowledge trust policy is not current at approval time")
    if knowledge.trust_digest_at(approved) != plan.knowledge_trust_digest:
        raise ValueError("knowledge trust decision changed after route planning")
    if any(not knowledge.validates_transition(transition, approved) for transition in plan.transitions):
        raise ValueError("knowledge claims are not usable at approval time")
    if approved < planned:
        raise ValueError("approval cannot predate the route plan evaluation")
    if expiry <= approved:
        raise ValueError("authorization expiry must be later than approval")
    if (expiry - approved).total_seconds() > policy.max_lifetime_seconds:
        raise ValueError("authorization lifetime exceeds the policy maximum")
    if not isinstance(permissions, (tuple, list)) or any(
        not isinstance(item, WorkerPermission) for item in permissions
    ):
        raise ValueError("permissions must contain WorkerPermission values")
    requested = tuple(sorted(set(permissions), key=lambda item: item.value))
    if len(requested) != len(permissions):
        raise ValueError("requested permissions must be unique")
    if not set(requested).issubset(policy.allowed_permissions):
        raise ValueError("requested permissions exceed the authorization policy")
    if not isinstance(limits, WorkerResourceLimits):
        raise ValueError("limits must be WorkerResourceLimits")
    ceiling = policy.limits()
    for field in ("timeout_seconds", "max_input_bytes", "max_output_bytes", "max_changed_files"):
        if getattr(limits, field) > getattr(ceiling, field):
            raise ValueError(f"requested {field} exceeds the authorization policy")
    if len(plan.transitions) > 10_000:
        raise ValueError("route exceeds the 10000-step authorization limit")
    registrations = {
        (item.manifest.worker_id, item.manifest.worker_version): item
        for item in registry.registrations()
    }
    grants = []
    for transition, prior in assessment.evaluations:
        if prior.status != "QUALIFIED" or prior.worker_id is None or prior.worker_version is None:
            raise ValueError("every route transition must have a qualified pinned worker")
        registration = registrations.get((prior.worker_id, prior.worker_version))
        if registration is None or registration.qualification is None:
            raise ValueError("qualified worker registration disappeared before approval")
        manifest = registration.manifest
        qualification = registration.qualification
        at_plan = registry.resolve(transition, planned)
        if at_plan.status != "QUALIFIED":
            raise ValueError(f"worker qualification was not current at plan evaluation: {transition.transition_id}")
        current = registry.resolve(transition, approved)
        if current.status != "QUALIFIED":
            raise ValueError(f"worker is not qualified at approval time: {transition.transition_id}")
        for observed in (at_plan, current):
            if (
                observed.manifest_digest != prior.manifest_digest
                or observed.qualification_id != prior.qualification_id
                or observed.qualification_digest != prior.qualification_digest
            ):
                raise ValueError("worker manifest or qualification changed after route assessment")
        if policy.allowed_worker_ids and manifest.worker_id not in policy.allowed_worker_ids:
            raise ValueError(f"worker is not permitted by policy: {manifest.worker_id}")
        if not set(requested).issubset(manifest.permissions):
            raise ValueError(f"requested permissions exceed worker declaration: {manifest.worker_id}")
        for field in ("timeout_seconds", "max_input_bytes", "max_output_bytes", "max_changed_files"):
            if getattr(limits, field) > getattr(manifest.limits, field):
                raise ValueError(f"requested {field} exceeds worker declaration: {manifest.worker_id}")
        valid_until = _instant(qualification.valid_until, "qualification.valid_until")
        if expiry > valid_until:
            raise ValueError("authorization must expire no later than every worker qualification")
        grants.append(MigrationStepGrant(
            transition_id=transition.transition_id,
            worker_id=manifest.worker_id,
            worker_version=manifest.worker_version,
            manifest_digest=manifest.manifest_digest,
            qualification_id=qualification.qualification_id,
            qualification_digest=qualification.qualification_digest,
            qualification_valid_until=qualification.valid_until,
            permissions=requested,
            limits=limits,
        ))
    if assessment.status == "NO_WORK_REQUIRED" and assessment.evaluations:
        raise ValueError("no-op assessment must not contain worker evaluations")
    return MigrationAuthorization(
        route_plan_digest=plan.plan_digest,
        worker_assessment_digest=assessment.assessment_digest,
        policy_digest=policy.policy_digest,
        approved_by=approved_by,
        approved_at=approved_text,
        expires_at=expiry_text,
        grants=tuple(grants),
    )



def validate_migration_authorization(
    authorization: MigrationAuthorization,
    plan: RoutePlan,
    assessment: RouteWorkerAssessment,
    registry: MigrationWorkerRegistry,
    policy: MigrationAuthorizationPolicy,
    *,
    knowledge: KnowledgeCatalog,
    now: datetime,
) -> None:
    """Validate current knowledge, worker qualification, and grants before a controlled side effect.

    This verifies consistency and current qualification; it does not authenticate
    the approver, verify a signature, or enforce permissions at the OS boundary.
    """
    if not isinstance(authorization, MigrationAuthorization):
        raise TypeError("authorization must be a MigrationAuthorization")
    if not isinstance(plan, RoutePlan) or not isinstance(assessment, RouteWorkerAssessment):
        raise TypeError("plan and assessment must use their migration contract types")
    if not isinstance(registry, MigrationWorkerRegistry):
        raise TypeError("registry must be a MigrationWorkerRegistry")
    if not isinstance(policy, MigrationAuthorizationPolicy):
        raise TypeError("policy must be a MigrationAuthorizationPolicy")
    if not isinstance(knowledge, KnowledgeCatalog):
        raise TypeError("knowledge must be a KnowledgeCatalog")
    now_text = _utc(now, "now")
    instant = _instant(now_text, "now")
    if knowledge.content_digest != plan.knowledge_digest:
        raise ValueError("knowledge catalog changed after route planning")
    if not knowledge.is_trusted_at(instant):
        raise ValueError("knowledge trust policy is not current at validation time")
    if knowledge.trust_digest_at(instant) != plan.knowledge_trust_digest:
        raise ValueError("knowledge trust decision changed after route planning")
    if any(not knowledge.validates_transition(transition, instant) for transition in plan.transitions):
        raise ValueError("knowledge claims are not usable at validation time")
    if not authorization.is_current(instant):
        raise ValueError("migration authorization is not currently valid")
    if plan.status != "PLANNED" or authorization.route_plan_digest != plan.plan_digest:
        raise ValueError("authorization does not match the current planned route")
    if authorization.worker_assessment_digest != assessment.assessment_digest:
        raise ValueError("authorization does not match the current worker assessment")
    if assessment.route_plan_digest != plan.plan_digest or assessment.evaluated_at != plan.evaluated_at:
        raise ValueError("worker assessment does not match the exact route plan")
    if assessment.trust_policy_digest != registry.trust_policy_digest:
        raise ValueError("worker trust policy changed after route assessment")
    if authorization.policy_digest != policy.policy_digest:
        raise ValueError("authorization policy digest does not match the active policy")
    if _instant(authorization.approved_at, "approved_at") < _instant(plan.evaluated_at, "plan.evaluated_at"):
        raise ValueError("authorization approval predates the route plan")
    if _instant(authorization.expires_at, "expires_at") - _instant(authorization.approved_at, "approved_at") > timedelta(seconds=policy.max_lifetime_seconds):
        raise ValueError("authorization lifetime exceeds the active policy")
    assessed_transitions = tuple(item[0] for item in assessment.evaluations)
    if assessed_transitions != plan.transitions:
        raise ValueError("worker assessment does not cover the exact ordered route transitions")
    if not plan.transitions:
        if assessment.status != "NO_WORK_REQUIRED" or authorization.grants:
            raise ValueError("no-op route authorization must have no worker grants")
        return
    if assessment.status != "QUALIFIED" or len(authorization.grants) != len(plan.transitions):
        raise ValueError("authorization must contain one grant for every qualified route transition")
    registrations = {
        (item.manifest.worker_id, item.manifest.worker_version): item
        for item in registry.registrations()
    }
    expiry = _instant(authorization.expires_at, "expires_at")
    for (transition, resolution), grant in zip(assessment.evaluations, authorization.grants):
        if resolution.status != "QUALIFIED":
            raise ValueError(f"worker assessment is no longer qualified: {transition.transition_id}")
        if (
            grant.transition_id != transition.transition_id
            or grant.worker_id != transition.worker_id
            or grant.worker_version != transition.worker_version
        ):
            raise ValueError("authorization grant does not match its exact transition worker")
        registration = registrations.get((grant.worker_id, grant.worker_version))
        if registration is None or registration.qualification is None:
            raise ValueError(f"authorized worker is no longer registered: {grant.worker_id}")
        manifest = registration.manifest
        qualification = registration.qualification
        current = registry.resolve(transition, instant)
        if current.status != "QUALIFIED":
            raise ValueError(f"authorized worker is not currently qualified: {grant.worker_id}")
        if (
            current.manifest_digest != grant.manifest_digest
            or current.qualification_id != grant.qualification_id
            or current.qualification_digest != grant.qualification_digest
            or current.manifest_digest != resolution.manifest_digest
            or current.qualification_digest != resolution.qualification_digest
            or current.qualification_id != resolution.qualification_id
        ):
            raise ValueError("authorized worker manifest or qualification has changed")
        valid_until = _instant(qualification.valid_until, "qualification.valid_until")
        if grant.qualification_valid_until != qualification.valid_until or expiry > valid_until:
            raise ValueError("authorization outlives or mismatches the worker qualification")
        if policy.allowed_worker_ids and grant.worker_id not in policy.allowed_worker_ids:
            raise ValueError(f"worker is not permitted by the active policy: {grant.worker_id}")
        if not set(grant.permissions).issubset(policy.allowed_permissions):
            raise ValueError("authorization grant exceeds the active policy permissions")
        if not set(grant.permissions).issubset(manifest.permissions):
            raise ValueError("authorization grant exceeds the worker's declared permissions")
        policy_limits = {
            "timeout_seconds": policy.max_timeout_seconds,
            "max_input_bytes": policy.max_input_bytes,
            "max_output_bytes": policy.max_output_bytes,
            "max_changed_files": policy.max_changed_files,
        }
        for field, policy_limit in policy_limits.items():
            value = getattr(grant.limits, field)
            if value > policy_limit:
                raise ValueError(f"authorization grant exceeds the active policy resource limit: {field}")
            if value > getattr(manifest.limits, field):
                raise ValueError(f"authorization grant exceeds the worker resource limit: {field}")



def _require_owner_trust(
    plan: RoutePlan,
    registry: MigrationWorkerRegistry,
    knowledge: KnowledgeCatalog,
    trust_store: OwnerTrustStore,
    now: datetime,
) -> None:
    """Require owner-store decisions for the exact catalog and every pinned worker."""
    if not isinstance(trust_store, OwnerTrustStore):
        raise TypeError("trust_store must be an OwnerTrustStore")
    trust_store.require_trusted(
        "KNOWLEDGE_CATALOG", "sha256:" + knowledge.content_digest, now=now
    )
    registrations = {
        (item.manifest.worker_id, item.manifest.worker_version): item
        for item in registry.registrations()
    }
    for transition in plan.transitions:
        resolution = registry.resolve(transition, now)
        if resolution.status != "QUALIFIED":
            continue
        if resolution.worker_id is None or resolution.worker_version is None:
            raise ValueError("qualified worker resolution is missing its exact identity")
        registration = registrations.get((resolution.worker_id, resolution.worker_version))
        if registration is None or registration.qualification is None:
            raise ValueError("qualified worker registration disappeared during trust validation")
        if resolution.manifest_digest != registration.manifest.manifest_digest:
            raise ValueError("worker manifest digest changed during owner trust validation")
        if resolution.qualification_digest != registration.qualification.qualification_digest:
            raise ValueError("worker qualification digest changed during owner trust validation")
        trust_store.require_trusted(
            "WORKER_MANIFEST", "sha256:" + resolution.manifest_digest, now=now
        )
        trust_store.require_trusted(
            "WORKER_QUALIFICATION",
            "sha256:" + resolution.qualification_digest,
            now=now,
        )


def authorize_migration_with_owner_trust(
    plan: RoutePlan,
    assessment: RouteWorkerAssessment,
    registry: MigrationWorkerRegistry,
    policy: MigrationAuthorizationPolicy,
    *,
    trust_store: OwnerTrustStore,
    approved_by: str,
    approved_at: datetime,
    expires_at: datetime,
    permissions: tuple[WorkerPermission, ...],
    limits: WorkerResourceLimits,
    knowledge: KnowledgeCatalog,
) -> MigrationAuthorization:
    """Create a plan authorization only when exact digests are trusted by the owner store.

    This adds an owner-controlled trust gate; it does not authenticate the approver,
    launch a worker, or enforce operating-system permissions.
    """
    _require_owner_trust(plan, registry, knowledge, trust_store, approved_at)
    return authorize_migration(
        plan, assessment, registry, policy,
        approved_by=approved_by, approved_at=approved_at, expires_at=expires_at,
        permissions=permissions, limits=limits, knowledge=knowledge,
    )


def validate_migration_authorization_with_owner_trust(
    authorization: MigrationAuthorization,
    plan: RoutePlan,
    assessment: RouteWorkerAssessment,
    registry: MigrationWorkerRegistry,
    policy: MigrationAuthorizationPolicy,
    *,
    trust_store: OwnerTrustStore,
    knowledge: KnowledgeCatalog,
    now: datetime,
) -> None:
    """Recheck exact owner trust and ordinary authorization freshness before a side effect."""
    _require_owner_trust(plan, registry, knowledge, trust_store, now)
    validate_migration_authorization(
        authorization, plan, assessment, registry, policy,
        knowledge=knowledge, now=now,
    )
    for grant in authorization.grants:
        trust_store.require_trusted(
            "WORKER_MANIFEST", "sha256:" + grant.manifest_digest, now=now
        )
        trust_store.require_trusted(
            "WORKER_QUALIFICATION", "sha256:" + grant.qualification_digest, now=now
        )


def serialize_migration_authorization_policy(policy: MigrationAuthorizationPolicy) -> bytes:
    if not isinstance(policy, MigrationAuthorizationPolicy):
        raise TypeError("policy must be a MigrationAuthorizationPolicy")
    return policy.to_json_bytes()


def deserialize_migration_authorization_policy(data: bytes | str) -> MigrationAuthorizationPolicy:
    return MigrationAuthorizationPolicy.from_json_bytes(data)


def serialize_migration_authorization(authorization: MigrationAuthorization) -> bytes:
    if not isinstance(authorization, MigrationAuthorization):
        raise TypeError("authorization must be a MigrationAuthorization")
    return authorization.to_json_bytes()


def deserialize_migration_authorization(data: bytes | str) -> MigrationAuthorization:
    return MigrationAuthorization.from_json_bytes(data)


__all__ = [
    "MigrationAuthorizationPolicy", "MigrationStepGrant",
    "MigrationAuthorization", "authorize_migration",
    "serialize_migration_authorization", "deserialize_migration_authorization",
    "serialize_migration_authorization_policy", "deserialize_migration_authorization_policy",
    "validate_migration_authorization",
    "authorize_migration_with_owner_trust",
    "validate_migration_authorization_with_owner_trust",
]

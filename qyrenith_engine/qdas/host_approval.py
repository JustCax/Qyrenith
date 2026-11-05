"""QDAS-specific scope binding for the existing local host-approval service."""
from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any

from ..approval import (
    HostApproval,
    HostApprovalError,
    validate_host_approval,
)
from ..trust_store import OwnerTrustStore
from .events import _canonical
from .repair import RepairPlan

QDAS_REPAIR_REVIEW_ACTION = "QDAS_REPAIR_REVIEW"


class QdasHostApprovalError(RuntimeError):
    """A host approval does not authorize the exact QDAS repair plan."""


def repair_review_scope(plan: RepairPlan) -> dict[str, Any]:
    """Return the complete immutable scope shown to the local owner for review."""
    if not isinstance(plan, RepairPlan):
        raise TypeError("plan must be a RepairPlan")
    return {
        "plan_digest": plan.plan_digest,
        "event_id": plan.event_id,
        "hypothesis_id": plan.hypothesis_id,
        "failure_category": plan.failure_category,
        "affected_paths": list(plan.affected_paths),
        "intended_change": plan.intended_change,
        "expected_invariants": list(plan.expected_invariants),
        "risk": plan.risk,
        "required_permissions": list(plan.required_permissions),
        "validation_commands": [list(command) for command in plan.validation_commands],
        "rollback_strategy": plan.rollback_strategy,
        "execution_mode": plan.execution_mode,
        "human_review_required": plan.human_review_required,
    }


def consume_qdas_host_approval(
    approval: HostApproval,
    plan: RepairPlan,
    trust_store: OwnerTrustStore,
    *,
    now: datetime | None = None,
) -> HostApproval:
    """Validate and atomically consume a single-use approval for this exact plan."""
    if not isinstance(approval, HostApproval):
        raise TypeError("approval must be a HostApproval")
    if not isinstance(trust_store, OwnerTrustStore):
        raise TypeError("trust_store must be an OwnerTrustStore")
    scope = repair_review_scope(plan)
    try:
        validate_host_approval(
            approval,
            QDAS_REPAIR_REVIEW_ACTION,
            scope,
            trust_store,
            now=now,
            consume=True,
        )
    except HostApprovalError as exc:
        raise QdasHostApprovalError(str(exc)) from exc
    return approval


def verify_consumed_qdas_host_approval(
    document: dict[str, Any],
    plan: RepairPlan,
    trust_store: OwnerTrustStore | None,
) -> HostApproval:
    """Verify persisted signature, exact plan scope, and nonce consumption."""
    if not isinstance(document, dict):
        raise QdasHostApprovalError("persisted host approval must be an object")
    if not isinstance(trust_store, OwnerTrustStore):
        raise QdasHostApprovalError("the owner trust store is required to verify host approval evidence")
    try:
        approval = HostApproval.from_json_bytes(_canonical(document) + b"\n")
    except (TypeError, ValueError, HostApprovalError) as exc:
        raise QdasHostApprovalError("persisted host approval document is invalid") from exc
    scope = repair_review_scope(plan)
    expected_scope_digest = hashlib.sha256(_canonical(scope)).hexdigest()
    if (
        approval.action_type != QDAS_REPAIR_REVIEW_ACTION
        or approval.scope_digest != expected_scope_digest
    ):
        raise QdasHostApprovalError("persisted host approval is not bound to this exact repair plan")
    if approval.trust_store_id != trust_store.store_id:
        raise QdasHostApprovalError("persisted host approval belongs to a different owner trust store")
    if not trust_store.verify_host_payload(approval.unsigned_dict(), approval.signature):
        raise QdasHostApprovalError("persisted host approval signature is invalid")
    if trust_store.generation <= approval.trust_store_generation:
        raise QdasHostApprovalError("host approval nonce consumption is not present in the owner trust history")
    nonce_digest = "sha256:" + hashlib.sha256(approval.nonce.encode("ascii")).hexdigest()
    if not trust_store.is_nonce_consumed(nonce_digest):
        raise QdasHostApprovalError("host approval nonce has not been consumed")
    return approval


__all__ = [
    "QDAS_REPAIR_REVIEW_ACTION",
    "QdasHostApprovalError",
    "consume_qdas_host_approval",
    "repair_review_scope",
    "verify_consumed_qdas_host_approval",
]

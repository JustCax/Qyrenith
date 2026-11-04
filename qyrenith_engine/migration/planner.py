"""Deterministic route planning over exact, verified migration transitions."""
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

from .knowledge import KnowledgeCatalog
from .model import MigrationIdentity, MigrationTransition


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"PLANNED", "UNKNOWN", "BLOCKED", "UNSUPPORTED"}


def _timestamp(value: datetime | None) -> str:
    instant = value or datetime.now(timezone.utc)
    if not isinstance(instant, datetime):
        raise TypeError("evaluated_at must be a datetime")
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("evaluated_at must be timezone-aware")
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _shortest_route(source, target, adjacency):
    """Return the deterministic shortest route in a finite directed graph."""
    if source == target:
        return ()
    queue = deque([source])
    parents = {source: None}
    while queue:
        current = queue.popleft()
        for edge in adjacency.get(current, ()):
            if edge.target in parents:
                continue
            parents[edge.target] = (current, edge)
            if edge.target == target:
                reversed_route = []
                node = target
                while parents[node] is not None:
                    previous, incoming = parents[node]
                    reversed_route.append(incoming)
                    node = previous
                reversed_route.reverse()
                return tuple(reversed_route)
            queue.append(edge.target)
    return None


def _adjacency(edges):
    result = {}
    for edge in edges:
        result.setdefault(edge.source, []).append(edge)
    for outgoing in result.values():
        outgoing.sort(key=lambda item: (item.target.stable_key, item.transition_id))
    return result


@dataclass(frozen=True, slots=True)
class RoutePlan:
    status: str
    source: MigrationIdentity
    target: MigrationIdentity
    transitions: tuple[MigrationTransition, ...]
    reason: str
    evaluated_at: str
    knowledge_digest: str
    knowledge_trust_digest: str
    max_hops: int

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("unsupported route plan status")
        if not isinstance(self.source, MigrationIdentity) or not isinstance(self.target, MigrationIdentity):
            raise ValueError("route plan endpoints must be MigrationIdentity values")
        if not isinstance(self.transitions, (tuple, list)) or any(
            not isinstance(item, MigrationTransition) for item in self.transitions
        ):
            raise ValueError("route plan transitions must be MigrationTransition values")
        if not isinstance(self.reason, str) or not self.reason.strip() or len(self.reason) > 2048:
            raise ValueError("route plan reason must be a non-empty string of at most 2048 characters")
        if not isinstance(self.evaluated_at, str) or not self.evaluated_at.strip():
            raise ValueError("route plan evaluation time must be a non-empty ISO-8601 timestamp")
        try:
            evaluated = datetime.fromisoformat(self.evaluated_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("route plan evaluation time must be ISO-8601") from exc
        if evaluated.tzinfo is None or evaluated.utcoffset() is None:
            raise ValueError("route plan evaluation time must include a timezone")
        if _timestamp(evaluated) != self.evaluated_at:
            raise ValueError("route plan evaluation time must use canonical UTC format")
        if not isinstance(self.knowledge_digest, str) or not _DIGEST.fullmatch(self.knowledge_digest):
            raise ValueError("knowledge_digest must be a lowercase SHA-256 hex digest")
        if not isinstance(self.knowledge_trust_digest, str) or not _DIGEST.fullmatch(self.knowledge_trust_digest):
            raise ValueError("knowledge_trust_digest must be a lowercase SHA-256 hex digest")
        if not isinstance(self.max_hops, int) or isinstance(self.max_hops, bool) or self.max_hops < 1:
            raise ValueError("max_hops must be a positive integer")
        route = tuple(self.transitions)
        if self.status == "PLANNED":
            if self.source == self.target:
                if route:
                    raise ValueError("a no-op route must not contain transitions")
            else:
                if not route or len(route) > self.max_hops:
                    raise ValueError("a planned route must contain a non-empty route within max_hops")
                if route[0].source != self.source or route[-1].target != self.target:
                    raise ValueError("planned route endpoints do not match the declared endpoints")
                if any(route[index].target != route[index + 1].source for index in range(len(route) - 1)):
                    raise ValueError("planned route contains a discontinuity")
        elif route:
            raise ValueError("non-planned route outcomes must not contain selected transitions")
        object.__setattr__(self, "transitions", route)

    @property
    def plannable(self) -> bool:
        """Whether a complete evidence-qualified route exists; not execution authorization."""
        return self.status == "PLANNED"

    @property
    def plan_digest(self) -> str:
        payload = {
            "schema": 1, "planner": "qyrenith-route-planner/1",
            "status": self.status, "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "transitions": [item.to_dict() for item in self.transitions],
            "reason": self.reason,
            "evaluated_at": self.evaluated_at,
            "knowledge_digest": self.knowledge_digest,
            "knowledge_trust_digest": self.knowledge_trust_digest,
            "max_hops": self.max_hops,
        }
        return hashlib.sha256(json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class MultiTargetPlan:
    source: MigrationIdentity
    targets: tuple[RoutePlan, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source, MigrationIdentity):
            raise ValueError("multi-target source must be a MigrationIdentity")
        if not isinstance(self.targets, (tuple, list)) or not self.targets:
            raise ValueError("multi-target plan must contain at least one route")
        if any(not isinstance(item, RoutePlan) for item in self.targets):
            raise ValueError("multi-target plan entries must be RoutePlan values")
        if any(item.source != self.source for item in self.targets):
            raise ValueError("all target plans must originate from the declared common source")
        target_keys = [item.target.stable_key for item in self.targets]
        if len(target_keys) != len(set(target_keys)):
            raise ValueError("multi-target plan contains duplicate target identities")
        evaluation_times = {item.evaluated_at for item in self.targets}
        if len(evaluation_times) != 1:
            raise ValueError("all target plans must share one evaluation timestamp")
        object.__setattr__(self, "targets", tuple(self.targets))

    @property
    def status(self) -> str:
        if all(item.plannable for item in self.targets):
            return "PLANNED"
        if any(item.plannable for item in self.targets):
            return "PARTIAL"
        statuses = {item.status for item in self.targets}
        if "UNKNOWN" in statuses:
            return "UNKNOWN"
        if "BLOCKED" in statuses:
            return "BLOCKED"
        return "UNSUPPORTED"

    @property
    def plannable(self) -> bool:
        return self.status == "PLANNED"

    @property
    def plan_digest(self) -> str:
        payload = {
            "schema": 1,
            "source": self.source.to_dict(),
            "target_plan_digests": [item.plan_digest for item in self.targets],
            "status": self.status,
        }
        return hashlib.sha256(json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()


def plan_route(
    source: MigrationIdentity,
    target: MigrationIdentity,
    transitions: tuple[MigrationTransition, ...],
    knowledge: KnowledgeCatalog,
    *,
    max_hops: int = 32,
    evaluated_at: datetime | None = None,
) -> RoutePlan:
    """Classify a route as PLANNED, UNKNOWN, BLOCKED, or UNSUPPORTED.

    PLANNED only means that an enabled route has current, non-conflicted VERIFIED
    knowledge for every edge. Execution still requires a separate worker registry,
    authorization, workspace, and runtime validation.
    """
    if not isinstance(source, MigrationIdentity) or not isinstance(target, MigrationIdentity):
        raise TypeError("source and target must be MigrationIdentity values")
    if not isinstance(knowledge, KnowledgeCatalog):
        raise TypeError("knowledge must be a KnowledgeCatalog")
    if not isinstance(max_hops, int) or isinstance(max_hops, bool) or max_hops < 1:
        raise ValueError("max_hops must be a positive integer")
    if not isinstance(transitions, (tuple, list)) or any(
        not isinstance(item, MigrationTransition) for item in transitions
    ):
        raise TypeError("transitions must contain MigrationTransition values")
    if len(transitions) > 100_000:
        raise ValueError("transition catalog exceeds the 100000-edge planning limit")

    at = _timestamp(evaluated_at)
    now = datetime.fromisoformat(at.replace("Z", "+00:00"))
    knowledge_digest = knowledge.content_digest
    knowledge_trust_digest = knowledge.trust_digest_at(now)

    def result(status, route, reason):
        return RoutePlan(
            status, source, target, route or (), reason, at,
            knowledge_digest, knowledge_trust_digest, max_hops,
        )

    if source == target:
        return result("PLANNED", (), "Source already matches target; no transition is required")

    seen_ids = set()
    all_edges = []
    enabled_edges = []
    verified_edges = []
    for edge in transitions:
        if edge.transition_id in seen_ids:
            raise ValueError(f"duplicate transition identifier: {edge.transition_id}")
        seen_ids.add(edge.transition_id)
        all_edges.append(edge)
        if edge.enabled:
            enabled_edges.append(edge)
            if knowledge.validates_transition(edge, now):
                verified_edges.append(edge)

    verified_route = _shortest_route(source, target, _adjacency(verified_edges))
    if verified_route is not None and len(verified_route) <= max_hops:
        return result("PLANNED", verified_route, "Complete route has current, exact-scope verified knowledge")

    enabled_route = _shortest_route(source, target, _adjacency(enabled_edges))
    if enabled_route is not None and len(enabled_route) <= max_hops:
        reason = (
            "A declared enabled route exists, but the knowledge catalog is not trusted by a local trust policy"
            if not knowledge.is_trusted_at(now)
            else "A declared enabled route exists, but one or more transitions lack usable verified knowledge"
        )
        return result("UNKNOWN", (), reason)

    all_route = _shortest_route(source, target, _adjacency(all_edges))
    if all_route is not None:
        if enabled_route is not None and len(enabled_route) > max_hops:
            reason = f"Shortest enabled route exceeds the configured maximum of {max_hops} transitions"
        elif len(all_route) > max_hops:
            reason = f"Shortest declared route exceeds the configured maximum of {max_hops} transitions"
        else:
            reason = "A route exists only through disabled transitions"
        return result("BLOCKED", (), reason)

    if verified_route is not None or enabled_route is not None:
        return result("BLOCKED", (), f"No qualifying route fits the configured maximum of {max_hops} transitions")
    return result("UNSUPPORTED", (), "No declared transition path connects the requested source and target")


def plan_targets(
    source: MigrationIdentity,
    targets: tuple[MigrationIdentity, ...],
    transitions: tuple[MigrationTransition, ...],
    knowledge: KnowledgeCatalog,
    *,
    max_hops: int = 32,
    evaluated_at: datetime | None = None,
) -> MultiTargetPlan:
    """Plan each target independently from the same source and time snapshot."""
    if not isinstance(targets, (tuple, list)) or not targets:
        raise ValueError("at least one migration target is required")
    if any(not isinstance(target, MigrationIdentity) for target in targets):
        raise TypeError("targets must contain MigrationIdentity values")
    keys = [target.stable_key for target in targets]
    if len(keys) != len(set(keys)):
        raise ValueError("multi-target requests must not contain duplicate targets")
    at = _timestamp(evaluated_at)
    instant = datetime.fromisoformat(at.replace("Z", "+00:00"))
    plans = tuple(
        plan_route(source, target, transitions, knowledge, max_hops=max_hops, evaluated_at=instant)
        for target in sorted(targets, key=lambda item: item.stable_key)
    )
    return MultiTargetPlan(source, plans)

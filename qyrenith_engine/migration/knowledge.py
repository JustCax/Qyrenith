"""Evidence-scoped migration knowledge and deterministic catalog interchange."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any

from .model import MigrationIdentity


class KnowledgeStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    VERIFIED = "VERIFIED"
    CONFLICTED = "CONFLICTED"
    STALE = "STALE"


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_IDENTITY_FIELDS = set(MigrationIdentity.__dataclass_fields__)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamps must be non-empty ISO-8601 strings")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamps must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def strict_object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def identity_from_dict(value: object) -> MigrationIdentity:
    if not isinstance(value, dict) or set(value) != _IDENTITY_FIELDS:
        raise ValueError("migration identity has missing or unexpected dimensions")
    return MigrationIdentity(**value)


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    evidence_id: str
    origin: str
    locator: str
    observed_at: str
    digest: str | None = None

    def __post_init__(self) -> None:
        for name in ("evidence_id", "origin", "locator", "observed_at"):
            value = getattr(self, name)
            limit = 4096 if name == "locator" else 256
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{name} must be a non-empty string of at most {limit} characters")
        if len(self.observed_at) > 64:
            raise ValueError("observed_at must not exceed 64 characters")
        parse_timestamp(self.observed_at)
        if self.digest is not None and (
            not isinstance(self.digest, str) or not _SHA256.fullmatch(self.digest)
        ):
            raise ValueError("digest must be None or sha256 followed by 64 lowercase hex characters")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "evidence_id": self.evidence_id, "origin": self.origin,
            "locator": self.locator, "observed_at": self.observed_at,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class MigrationKnowledgeClaim:
    claim_id: str
    subject: str
    statement: str
    source: MigrationIdentity
    target: MigrationIdentity
    status: KnowledgeStatus
    assertion: str | None = None
    evidence: tuple[EvidenceReference, ...] = ()
    verified_by: str | None = None
    verified_at: str | None = None
    valid_until: str | None = None

    def __post_init__(self) -> None:
        limits = {"claim_id": 256, "subject": 256, "statement": 8192}
        for name, limit in limits.items():
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{name} must be a non-empty string of at most {limit} characters")
        if not isinstance(self.source, MigrationIdentity) or not isinstance(self.target, MigrationIdentity):
            raise ValueError("source and target must be MigrationIdentity values")
        if not isinstance(self.status, KnowledgeStatus):
            raise ValueError("status must be a KnowledgeStatus")
        if self.assertion is not None and (
            not isinstance(self.assertion, str) or not self.assertion.strip()
            or len(self.assertion) > 2048
        ):
            raise ValueError("assertion must be None or a non-empty string of at most 2048 characters")
        if len(self.statement) > 8192:
            raise ValueError("statement must not exceed 8192 characters")
        if not isinstance(self.evidence, (tuple, list)) or len(self.evidence) > 10000 or any(
            not isinstance(item, EvidenceReference) for item in self.evidence
        ):
            raise ValueError("evidence must be a bounded sequence of EvidenceReference values")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("evidence identifiers must be unique within a claim")
        if self.verified_by is not None and (
            not isinstance(self.verified_by, str) or not self.verified_by.strip()
            or len(self.verified_by) > 256
        ):
            raise ValueError("verified_by must be None or a non-empty string of at most 256 characters")
        if self.source == self.target:
            raise ValueError("a knowledge claim must identify a non-empty transition")
        if self.verified_at is not None and (
            not isinstance(self.verified_at, str) or len(self.verified_at) > 64
        ):
            raise ValueError("verified_at must be a string of at most 64 characters")
        if self.valid_until is not None and (
            not isinstance(self.valid_until, str) or len(self.valid_until) > 64
        ):
            raise ValueError("valid_until must be a string of at most 64 characters")
        verified_time = parse_timestamp(self.verified_at) if self.verified_at is not None else None
        expiry_time = parse_timestamp(self.valid_until) if self.valid_until is not None else None
        if self.status is KnowledgeStatus.VERIFIED and (
            not self.assertion or not self.verified_by or verified_time is None or not self.evidence
        ):
            raise ValueError("VERIFIED claims require an assertion, reviewer, timestamp, and evidence")
        if self.valid_until is not None and verified_time is None:
            raise ValueError("valid_until requires verified_at")
        if verified_time is not None and any(
            parse_timestamp(item.observed_at) > verified_time for item in self.evidence
        ):
            raise ValueError("evidence cannot be observed after the claim verification time")
        if verified_time is not None and expiry_time is not None and expiry_time <= verified_time:
            raise ValueError("valid_until must be later than verified_at")
        object.__setattr__(
            self, "evidence", tuple(sorted(self.evidence, key=lambda item: item.evidence_id))
        )

    def is_usable(self, now: datetime | None = None) -> bool:
        if self.status is not KnowledgeStatus.VERIFIED or not self.evidence:
            return False
        if not self.verified_by or not self.verified_at or not self.assertion:
            return False
        current = now or datetime.now(timezone.utc)
        if not isinstance(current, datetime):
            raise TypeError("now must be a datetime")
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        current = current.astimezone(timezone.utc)
        verified_time = parse_timestamp(self.verified_at)
        if verified_time > current:
            return False
        if self.valid_until is not None and current >= parse_timestamp(self.valid_until):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "claim_id": self.claim_id, "subject": self.subject,
            "statement": self.statement, "assertion": self.assertion,
            "source": self.source.to_dict(), "target": self.target.to_dict(),
            "status": self.status.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "verified_by": self.verified_by, "verified_at": self.verified_at,
            "valid_until": self.valid_until,
        }


def _claim_from_dict(value: object) -> MigrationKnowledgeClaim:
    required = {
        "schema", "claim_id", "subject", "statement", "assertion", "source", "target",
        "status", "evidence", "verified_by", "verified_at", "valid_until",
    }
    if not isinstance(value, dict) or set(value) != required or type(value.get("schema")) is not int or value["schema"] != 1:
        raise ValueError("knowledge claim has missing, unexpected, or unsupported fields")
    evidence_data = value["evidence"]
    if not isinstance(evidence_data, list) or len(evidence_data) > 10000:
        raise ValueError("claim evidence must be a bounded array")
    evidence = []
    for item in evidence_data:
        if not isinstance(item, dict) or set(item) != {
            "evidence_id", "origin", "locator", "observed_at", "digest"
        }:
            raise ValueError("evidence reference has missing or unexpected fields")
        evidence.append(EvidenceReference(**item))
    try:
        status = KnowledgeStatus(value["status"])
    except (ValueError, TypeError) as exc:
        raise ValueError("unknown knowledge status") from exc
    return MigrationKnowledgeClaim(
        claim_id=value["claim_id"], subject=value["subject"],
        statement=value["statement"], assertion=value["assertion"],
        source=identity_from_dict(value["source"]), target=identity_from_dict(value["target"]),
        status=status, evidence=tuple(evidence), verified_by=value["verified_by"],
        verified_at=value["verified_at"], valid_until=value["valid_until"],
    )


class KnowledgeCatalog:
    """Read-only catalog with conservative conflict detection and stable content identity."""

    def __init__(self, claims: tuple[MigrationKnowledgeClaim, ...] = ()) -> None:
        indexed = {}
        for claim in claims:
            if not isinstance(claim, MigrationKnowledgeClaim):
                raise ValueError("catalog entries must be MigrationKnowledgeClaim values")
            if claim.claim_id in indexed:
                raise ValueError(f"duplicate knowledge claim: {claim.claim_id}")
            indexed[claim.claim_id] = claim
        if len(indexed) > 50000:
            raise ValueError("knowledge catalog exceeds the 50000-claim limit")
        self._claims = indexed
        groups = {}
        for claim in indexed.values():
            if claim.status in {KnowledgeStatus.UNKNOWN, KnowledgeStatus.STALE}:
                continue
            key = (claim.source.stable_key, claim.target.stable_key, claim.subject)
            groups.setdefault(key, []).append(claim)
        conflicts = []
        conflicted_ids = set()
        for key in sorted(groups):
            items = groups[key]
            assertions = {item.assertion for item in items if item.assertion is not None}
            explicit_conflict = any(item.status is KnowledgeStatus.CONFLICTED for item in items)
            if explicit_conflict or len(assertions) > 1:
                ids = tuple(sorted(item.claim_id for item in items))
                conflicts.append(ids)
                conflicted_ids.update(ids)
        self._conflict_groups = tuple(conflicts)
        self._conflicted_ids = frozenset(conflicted_ids)

    def get(self, claim_id: str) -> MigrationKnowledgeClaim | None:
        return self._claims.get(claim_id)

    def claims(self) -> tuple[MigrationKnowledgeClaim, ...]:
        return tuple(self._claims[key] for key in sorted(self._claims))

    @property
    def conflicts(self) -> tuple[tuple[str, ...], ...]:
        return self._conflict_groups

    @property
    def content_digest(self) -> str:
        payload = {"schema": 1, "claims": [claim.to_dict() for claim in self.claims()]}
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()

    def merge(self, *others: "KnowledgeCatalog") -> "KnowledgeCatalog":
        """Return a new catalog; identical IDs are idempotent, changed IDs are rejected."""
        merged = dict(self._claims)
        for other in others:
            if not isinstance(other, KnowledgeCatalog):
                raise TypeError("all merge inputs must be KnowledgeCatalog values")
            for claim in other.claims():
                existing = merged.get(claim.claim_id)
                if existing is not None:
                    if existing.to_dict() != claim.to_dict():
                        raise ValueError(f"claim identifier collision: {claim.claim_id}")
                    continue
                merged[claim.claim_id] = claim
        return KnowledgeCatalog(tuple(merged[key] for key in sorted(merged)))

    def summary(self, now: datetime | None = None) -> dict[str, Any]:
        """Return deterministic counts without promoting or mutating any claim."""
        instant = datetime.now(timezone.utc) if now is None else now
        if not isinstance(instant, datetime):
            raise TypeError("now must be a datetime")
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        counts = {status.value: 0 for status in KnowledgeStatus}
        usable_verified = 0
        unusable_verified = 0
        for claim in self.claims():
            counts[claim.status.value] += 1
            if claim.status is KnowledgeStatus.VERIFIED:
                if claim.claim_id in self._conflicted_ids:
                    unusable_verified += 1
                elif claim.is_usable(instant):
                    usable_verified += 1
                else:
                    unusable_verified += 1
        return {
            "schema": 1,
            "claim_count": len(self._claims),
            "status_counts": counts,
            "usable_verified": usable_verified,
            "unusable_verified": unusable_verified,
            "conflict_group_count": len(self._conflict_groups),
            "conflict_groups": [list(group) for group in self._conflict_groups],
            "content_digest": self.content_digest,
        }

    def claim_is_usable(self, claim_id: str, now: datetime | None = None) -> bool:
        claim = self.get(claim_id)
        return bool(claim is not None and claim_id not in self._conflicted_ids and claim.is_usable(now))

    def validates_transition(self, transition: object, now: datetime | None = None) -> bool:
        source = getattr(transition, "source", None)
        target = getattr(transition, "target", None)
        claim_ids = getattr(transition, "knowledge_claim_ids", ())
        if not claim_ids or len(claim_ids) != len(set(claim_ids)):
            return False
        for claim_id in claim_ids:
            claim = self.get(claim_id)
            if claim is None or not self.claim_is_usable(claim_id, now):
                return False
            if claim.source != source or claim.target != target:
                return False
        return True

    def to_document(self) -> dict[str, Any]:
        payload = {"schema": 1, "claims": [claim.to_dict() for claim in self.claims()]}
        return {**payload, "content_digest": hashlib.sha256(_canonical_bytes(payload)).hexdigest()}

    def to_json_bytes(self) -> bytes:
        return _canonical_bytes(self.to_document()) + b"\n"

    @classmethod
    def from_document(cls, document: object) -> "KnowledgeCatalog":
        if not isinstance(document, dict) or set(document) != {"schema", "claims", "content_digest"}:
            raise ValueError("knowledge catalog document has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise ValueError("unsupported knowledge catalog schema")
        claims_data = document["claims"]
        if not isinstance(claims_data, list) or len(claims_data) > 50000:
            raise ValueError("knowledge catalog claims must be a bounded array")
        payload = {"schema": 1, "claims": claims_data}
        digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if document["content_digest"] != digest:
            raise ValueError("knowledge catalog content digest mismatch")
        catalog = cls(tuple(_claim_from_dict(item) for item in claims_data))
        if catalog.to_document() != document:
            raise ValueError("knowledge catalog is not in canonical form")
        return catalog

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "KnowledgeCatalog":
        if isinstance(data, bytes):
            if len(data) > 16 * 1024 * 1024:
                raise ValueError("knowledge catalog exceeds the 16 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("knowledge catalog must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 16 * 1024 * 1024:
                raise ValueError("knowledge catalog exceeds the 16 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source, object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid knowledge catalog JSON") from exc
        canonical = _canonical_bytes(document)
        encoded_source = source.encode("utf-8")
        if encoded_source not in {canonical, canonical + b"\n"}:
            raise ValueError("knowledge catalog JSON is not in canonical form")
        return cls.from_document(document)


def serialize_knowledge_catalog(catalog: KnowledgeCatalog) -> bytes:
    if not isinstance(catalog, KnowledgeCatalog):
        raise TypeError("catalog must be a KnowledgeCatalog")
    return catalog.to_json_bytes()


def deserialize_knowledge_catalog(data: bytes | str) -> KnowledgeCatalog:
    return KnowledgeCatalog.from_json_bytes(data)


__all__ = [
    "EvidenceReference", "KnowledgeCatalog", "KnowledgeStatus",
    "MigrationKnowledgeClaim", "deserialize_knowledge_catalog",
    "serialize_knowledge_catalog",
]

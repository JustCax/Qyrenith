"""Evidence-scoped migration knowledge and deterministic catalog interchange."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any
from types import MappingProxyType

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
    verified_with: str | None = None
    verifier_version: str | None = None
    verifier_digest: str | None = None

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
        for name, limit in (("verified_with", 256), ("verifier_version", 128)):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value.strip() or len(value) > limit
            ):
                raise ValueError(f"{name} must be None or a non-empty string of at most {limit} characters")
        if self.verifier_digest is not None and (
            not isinstance(self.verifier_digest, str) or not _SHA256.fullmatch(self.verifier_digest)
        ):
            raise ValueError("verifier_digest must be None or sha256 followed by 64 lowercase hex characters")
        verified_time = parse_timestamp(self.verified_at) if self.verified_at is not None else None
        expiry_time = parse_timestamp(self.valid_until) if self.valid_until is not None else None
        if self.status is KnowledgeStatus.VERIFIED and (
            not self.assertion or not self.verified_by or verified_time is None
            or not self.evidence or any(item.digest is None for item in self.evidence)
            or not self.verified_with or not self.verifier_version
            or not self.verifier_digest or expiry_time is None
        ):
            raise ValueError(
                "VERIFIED claims require assertion, reviewer, time-bounded evidence digests, "
                "verifier identity/version/digest, and expiry"
            )
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
        if (
            not self.verified_by or not self.verified_at or not self.assertion
            or not self.valid_until or not self.verified_with or not self.verifier_version
            or not self.verifier_digest or any(item.digest is None for item in self.evidence)
        ):
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
            "schema": 2,
            "claim_id": self.claim_id, "subject": self.subject,
            "statement": self.statement, "assertion": self.assertion,
            "source": self.source.to_dict(), "target": self.target.to_dict(),
            "status": self.status.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "verified_by": self.verified_by, "verified_at": self.verified_at,
            "valid_until": self.valid_until, "verified_with": self.verified_with,
            "verifier_version": self.verifier_version, "verifier_digest": self.verifier_digest,
        }


def _claim_from_dict(value: object) -> MigrationKnowledgeClaim:
    required = {
        "schema", "claim_id", "subject", "statement", "assertion", "source", "target",
        "status", "evidence", "verified_by", "verified_at", "valid_until",
        "verified_with", "verifier_version", "verifier_digest",
    }
    if not isinstance(value, dict) or set(value) != required or type(value.get("schema")) is not int or value["schema"] != 2:
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
        verified_with=value["verified_with"], verifier_version=value["verifier_version"],
        verifier_digest=value["verifier_digest"],
    )


@dataclass(frozen=True, slots=True)
class KnowledgeTrustPolicy:
    """Local allowlist for exact catalog digests; the policy file itself must be trusted."""

    policy_id: str
    reviewed_by: str
    reviewed_at: str
    trusted_catalog_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        for field, limit in (("policy_id", 256), ("reviewed_by", 256)):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{field} must be a non-empty bounded string")
        reviewed = parse_timestamp(self.reviewed_at)
        canonical_time = reviewed.isoformat().replace("+00:00", "Z")
        if canonical_time != self.reviewed_at:
            raise ValueError("reviewed_at must use canonical UTC format")
        if not isinstance(self.trusted_catalog_digests, (tuple, list)):
            raise ValueError("trusted_catalog_digests must be a sequence")
        digests = tuple(self.trusted_catalog_digests)
        if len(digests) > 10000:
            raise ValueError("trusted_catalog_digests exceeds the 10000-entry limit")
        if any(
            not isinstance(item, str) or len(item) != 64
            or any(char not in "0123456789abcdef" for char in item)
            for item in digests
        ):
            raise ValueError("trusted catalog digests must be lowercase SHA-256 hex digests")
        if len(digests) != len(set(digests)):
            raise ValueError("trusted catalog digests must be unique")
        object.__setattr__(self, "trusted_catalog_digests", tuple(sorted(digests)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "policy_id": self.policy_id,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "trusted_catalog_digests": list(self.trusted_catalog_digests),
        }

    @property
    def policy_digest(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.to_dict())).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self.to_dict(), "policy_digest": self.policy_digest}

    def to_json_bytes(self) -> bytes:
        return _canonical_bytes(self.to_document()) + b"\n"

    def is_current(self, now: datetime | None = None) -> bool:
        instant = datetime.now(timezone.utc) if now is None else now
        if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("now must be a timezone-aware datetime")
        return parse_timestamp(self.reviewed_at) <= instant.astimezone(timezone.utc)

    def trusts(self, catalog_digest: str, now: datetime | None = None) -> bool:
        return catalog_digest in self.trusted_catalog_digests and self.is_current(now)

    @classmethod
    def from_document(cls, document: object) -> "KnowledgeTrustPolicy":
        expected = {
            "schema", "policy_id", "reviewed_by", "reviewed_at",
            "trusted_catalog_digests", "policy_digest",
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise ValueError("knowledge trust policy has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise ValueError("unsupported knowledge trust policy schema")
        payload = {key: value for key, value in document.items() if key != "policy_digest"}
        digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if document["policy_digest"] != digest:
            raise ValueError("knowledge trust policy digest mismatch")
        if not isinstance(document["trusted_catalog_digests"], list):
            raise ValueError("trusted_catalog_digests must be an array")
        policy = cls(
            policy_id=document["policy_id"],
            reviewed_by=document["reviewed_by"],
            reviewed_at=document["reviewed_at"],
            trusted_catalog_digests=tuple(document["trusted_catalog_digests"]),
        )
        if policy.to_document() != document:
            raise ValueError("knowledge trust policy is not canonical")
        return policy

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "KnowledgeTrustPolicy":
        if isinstance(data, bytes):
            if len(data) > 1024 * 1024:
                raise ValueError("knowledge trust policy exceeds the 1 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("knowledge trust policy must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 1024 * 1024:
                raise ValueError("knowledge trust policy exceeds the 1 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source, object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid knowledge trust policy JSON") from exc
        canonical = _canonical_bytes(document)
        if source.encode("utf-8") not in {canonical, canonical + b"\n"}:
            raise ValueError("knowledge trust policy JSON is not canonical")
        return cls.from_document(document)


class KnowledgeCatalog:
    """Read-only catalog with conservative conflicts and explicit import trust."""

    __slots__ = (
        "_claims", "_conflict_groups", "_conflicted_ids",
        "_trust_policy", "_trusted", "_imported",
    )

    def __setattr__(self, name, value) -> None:
        if hasattr(self, name):
            raise AttributeError("KnowledgeCatalog is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name) -> None:
        raise AttributeError("KnowledgeCatalog is immutable")

    def __init__(
        self,
        claims: tuple[MigrationKnowledgeClaim, ...] = (),
        *,
        trust_policy: KnowledgeTrustPolicy | None = None,
        _imported: bool = False,
    ) -> None:
        if trust_policy is not None and not isinstance(trust_policy, KnowledgeTrustPolicy):
            raise TypeError("trust_policy must be a KnowledgeTrustPolicy")
        indexed = {}
        for claim in claims:
            if not isinstance(claim, MigrationKnowledgeClaim):
                raise ValueError("catalog entries must be MigrationKnowledgeClaim values")
            if claim.claim_id in indexed:
                raise ValueError(f"duplicate knowledge claim: {claim.claim_id}")
            indexed[claim.claim_id] = claim
        if len(indexed) > 50000:
            raise ValueError("knowledge catalog exceeds the 50000-claim limit")
        immutable_claims = MappingProxyType(indexed)
        payload = {"schema": 2, "claims": [immutable_claims[key].to_dict() for key in sorted(immutable_claims)]}
        catalog_digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        trusted = (
            catalog_digest in trust_policy.trusted_catalog_digests
            if trust_policy is not None
            else not _imported
        )
        groups = {}
        for claim in immutable_claims.values():
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
        self._claims = immutable_claims
        self._conflict_groups = tuple(conflicts)
        self._conflicted_ids = frozenset(conflicted_ids)
        self._trust_policy = trust_policy
        self._trusted = trusted
        self._imported = _imported

    def get(self, claim_id: str) -> MigrationKnowledgeClaim | None:
        return self._claims.get(claim_id)

    def claims(self) -> tuple[MigrationKnowledgeClaim, ...]:
        return tuple(self._claims[key] for key in sorted(self._claims))

    @property
    def conflicts(self) -> tuple[tuple[str, ...], ...]:
        return self._conflict_groups

    @property
    def is_allowlisted(self) -> bool:
        """Whether the exact catalog digest appears in the supplied local allowlist."""
        return self._trusted

    @property
    def is_trusted(self) -> bool:
        """Whether the local trust decision is valid at the current time."""
        return self.is_trusted_at()

    def is_trusted_at(self, now: datetime | None = None) -> bool:
        if not self._trusted:
            return False
        return self._trust_policy is None or self._trust_policy.is_current(now)

    @property
    def trust_policy_digest(self) -> str | None:
        return self._trust_policy.policy_digest if self._trust_policy is not None else None

    @property
    def content_digest(self) -> str:
        payload = {"schema": 2, "claims": [claim.to_dict() for claim in self.claims()]}
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()

    @property
    def trust_digest(self) -> str:
        payload = {
            "schema": 1,
            "catalog_digest": self.content_digest,
            "catalog_origin": "IMPORTED" if self._imported else "LOCAL",
            "trusted_allowlisted": self._trusted,
            "trust_policy_digest": self.trust_policy_digest,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()

    def trust_digest_at(self, now: datetime | None = None) -> str:
        instant = datetime.now(timezone.utc) if now is None else now
        if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("now must be a timezone-aware datetime")
        payload = {
            "schema": 1,
            "catalog_digest": self.content_digest,
            "catalog_origin": "IMPORTED" if self._imported else "LOCAL",
            "trusted": self.is_trusted_at(instant),
            "trust_policy_digest": self.trust_policy_digest,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()

    def merge(self, *others: "KnowledgeCatalog") -> "KnowledgeCatalog":
        """Return a new catalog; imported trust is never silently inherited by a changed digest."""
        if not others:
            return self
        merged = dict(self._claims)
        imported = self._imported
        for other in others:
            if not isinstance(other, KnowledgeCatalog):
                raise TypeError("all merge inputs must be KnowledgeCatalog values")
            imported = imported or other._imported
            for claim in other.claims():
                existing = merged.get(claim.claim_id)
                if existing is not None:
                    if existing.to_dict() != claim.to_dict():
                        raise ValueError(f"claim identifier collision: {claim.claim_id}")
                    continue
                merged[claim.claim_id] = claim
        return KnowledgeCatalog(
            tuple(merged[key] for key in sorted(merged)),
            _imported=imported,
        )

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
                if not self.is_trusted_at(instant) or claim.claim_id in self._conflicted_ids or not claim.is_usable(instant):
                    unusable_verified += 1
                else:
                    usable_verified += 1
        return {
            "schema": 1,
            "claim_count": len(self._claims),
            "status_counts": counts,
            "usable_verified": usable_verified,
            "unusable_verified": unusable_verified,
            "conflict_group_count": len(self._conflict_groups),
            "conflict_groups": [list(group) for group in self._conflict_groups],
            "content_digest": self.content_digest,
            "trusted": self.is_trusted_at(instant),
            "trust_policy_digest": self.trust_policy_digest,
            "trust_digest": self.trust_digest_at(instant),
        }

    def claim_is_usable(self, claim_id: str, now: datetime | None = None) -> bool:
        claim = self.get(claim_id)
        return bool(
            self.is_trusted_at(now) and claim is not None
            and claim_id not in self._conflicted_ids and claim.is_usable(now)
        )

    def validates_transition(self, transition: object, now: datetime | None = None) -> bool:
        if not self._trusted:
            return False
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
        payload = {"schema": 2, "claims": [claim.to_dict() for claim in self.claims()]}
        return {**payload, "content_digest": hashlib.sha256(_canonical_bytes(payload)).hexdigest()}

    def to_json_bytes(self) -> bytes:
        return _canonical_bytes(self.to_document()) + b"\n"

    @classmethod
    def from_document(
        cls,
        document: object,
        *,
        trust_policy: KnowledgeTrustPolicy | None = None,
    ) -> "KnowledgeCatalog":
        if not isinstance(document, dict) or set(document) != {"schema", "claims", "content_digest"}:
            raise ValueError("knowledge catalog document has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 2:
            raise ValueError("unsupported knowledge catalog schema")
        claims_data = document["claims"]
        if not isinstance(claims_data, list) or len(claims_data) > 50000:
            raise ValueError("knowledge catalog claims must be a bounded array")
        payload = {"schema": 2, "claims": claims_data}
        digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if document["content_digest"] != digest:
            raise ValueError("knowledge catalog content digest mismatch")
        catalog = cls(
            tuple(_claim_from_dict(item) for item in claims_data),
            trust_policy=trust_policy,
            _imported=True,
        )
        if catalog.to_document() != document:
            raise ValueError("knowledge catalog is not in canonical form")
        return catalog

    @classmethod
    def from_json_bytes(
        cls,
        data: bytes | str,
        *,
        trust_policy: KnowledgeTrustPolicy | None = None,
    ) -> "KnowledgeCatalog":
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
        return cls.from_document(document, trust_policy=trust_policy)


def serialize_knowledge_catalog(catalog: KnowledgeCatalog) -> bytes:
    if not isinstance(catalog, KnowledgeCatalog):
        raise TypeError("catalog must be a KnowledgeCatalog")
    return catalog.to_json_bytes()


def deserialize_knowledge_catalog(
    data: bytes | str,
    *,
    trust_policy: KnowledgeTrustPolicy | None = None,
) -> KnowledgeCatalog:
    return KnowledgeCatalog.from_json_bytes(data, trust_policy=trust_policy)


__all__ = [
    "EvidenceReference", "KnowledgeCatalog", "KnowledgeStatus", "KnowledgeTrustPolicy",
    "MigrationKnowledgeClaim", "deserialize_knowledge_catalog",
    "serialize_knowledge_catalog",
]

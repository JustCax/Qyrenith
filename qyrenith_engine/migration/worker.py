"""Version-pinned migration worker contracts and qualification records.

This module validates declarations and existing qualification records only. It
never downloads, launches, authorizes, or executes a worker.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any
from types import MappingProxyType

from .knowledge import identity_from_dict, parse_timestamp, strict_object_pairs
from .model import MigrationIdentity, MigrationTransition, TransitionKind, validate_transition_scope
from .planner import RoutePlan


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_WORKER_KEY_LIMIT = 256
_MAX_SCOPES = 10_000
_MAX_CAPABILITIES = 1_000
_RESOLUTION_STATUSES = {
    "BLOCKED", "NOT_SELECTED", "NOT_REGISTERED", "INCOMPATIBLE",
    "UNQUALIFIED", "UNTRUSTED", "STALE", "QUALIFIED",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _text(value: object, field: str, limit: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")
    return value


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must use sha256: followed by 64 lowercase hexadecimal characters")
    return value


def _hex_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not _HEX_DIGEST.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 hexadecimal digest")
    return value


def _positive_int(value: object, field: str, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise ValueError(f"{field} must be an integer between 1 and {maximum}")
    return value


class WorkerPermission(str, Enum):
    READ_PROJECT = "READ_PROJECT"
    WRITE_PROJECT = "WRITE_PROJECT"
    EXECUTE_PROCESS = "EXECUTE_PROCESS"
    NETWORK = "NETWORK"
    INSTALL_DEPENDENCIES = "INSTALL_DEPENDENCIES"
    GIT_WRITE = "GIT_WRITE"
    PUBLISH_ARTIFACT = "PUBLISH_ARTIFACT"


@dataclass(frozen=True, slots=True)
class WorkerScope:
    """One exact source/target transition scope; wildcards are not supported."""

    kind: TransitionKind
    source: MigrationIdentity
    target: MigrationIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TransitionKind):
            raise ValueError("scope kind must be a TransitionKind")
        if not isinstance(self.source, MigrationIdentity) or not isinstance(self.target, MigrationIdentity):
            raise ValueError("scope endpoints must be MigrationIdentity values")
        validate_transition_scope(self.source, self.target, self.kind)
        changed = {
            name for name in self.source.__dataclass_fields__
            if getattr(self.source, name) != getattr(self.target, name)
        }
        allowed = {
            TransitionKind.VERSION_UPGRADE: {"product_version"},
            TransitionKind.LOADER_CONVERSION: {"loader", "loader_version"},
            TransitionKind.FRAMEWORK_CHANGE: {"framework", "framework_version"},
            TransitionKind.PLATFORM_MIGRATION: {"domain", "product", "platform"},
            TransitionKind.TOOLCHAIN_CHANGE: {"language", "toolchain"},
            TransitionKind.DEPENDENCY_MIGRATION: {"dependency_fingerprint"},
            TransitionKind.PROJECT_PROFILE_CHANGE: {"profile"},
        }[self.kind]
        if not changed <= allowed:
            raise ValueError(f"worker scope kind cannot change dimensions: {', '.join(sorted(changed - allowed))}")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class WorkerResourceLimits:
    timeout_seconds: int
    max_input_bytes: int
    max_output_bytes: int
    max_changed_files: int

    def __post_init__(self) -> None:
        _positive_int(self.timeout_seconds, "timeout_seconds", 3600)
        _positive_int(self.max_input_bytes, "max_input_bytes", 64 * 1024 * 1024)
        _positive_int(self.max_output_bytes, "max_output_bytes", 16 * 1024 * 1024)
        _positive_int(self.max_changed_files, "max_changed_files", 100_000)

    def to_dict(self) -> dict[str, int]:
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_input_bytes": self.max_input_bytes,
            "max_output_bytes": self.max_output_bytes,
            "max_changed_files": self.max_changed_files,
        }


@dataclass(frozen=True, slots=True)
class MigrationWorkerManifest:
    worker_id: str
    worker_version: str
    implementation_digest: str
    protocol_version: int
    scopes: tuple[WorkerScope, ...]
    capabilities: tuple[str, ...]
    permissions: tuple[WorkerPermission, ...]
    limits: WorkerResourceLimits

    def __post_init__(self) -> None:
        _text(self.worker_id, "worker_id", _WORKER_KEY_LIMIT)
        _text(self.worker_version, "worker_version", 128)
        _digest(self.implementation_digest, "implementation_digest")
        if type(self.protocol_version) is not int or self.protocol_version != 1:
            raise ValueError("only migration worker protocol version 1 is supported")
        if not isinstance(self.scopes, (tuple, list)) or not 1 <= len(self.scopes) <= _MAX_SCOPES:
            raise ValueError(f"scopes must contain between 1 and {_MAX_SCOPES} exact scopes")
        if any(not isinstance(item, WorkerScope) for item in self.scopes):
            raise ValueError("scopes must contain WorkerScope values")
        scope_keys = {
            (item.kind.value, item.source.stable_key, item.target.stable_key)
            for item in self.scopes
        }
        if len(scope_keys) != len(self.scopes):
            raise ValueError("worker manifest contains duplicate exact scopes")
        if not isinstance(self.capabilities, (tuple, list)) or len(self.capabilities) > _MAX_CAPABILITIES:
            raise ValueError(f"capabilities must contain at most {_MAX_CAPABILITIES} values")
        capabilities = tuple(_text(item, "capability", 256) for item in self.capabilities)
        if len(capabilities) != len(set(capabilities)):
            raise ValueError("worker capabilities must be unique")
        if not isinstance(self.permissions, (tuple, list)):
            raise ValueError("permissions must be a sequence of WorkerPermission values")
        if any(not isinstance(item, WorkerPermission) for item in self.permissions):
            raise ValueError("permissions must contain WorkerPermission values")
        if len(self.permissions) != len(set(self.permissions)):
            raise ValueError("worker permissions must be unique")
        if not isinstance(self.limits, WorkerResourceLimits):
            raise ValueError("limits must be a WorkerResourceLimits value")
        object.__setattr__(
            self, "scopes",
            tuple(sorted(
                self.scopes,
                key=lambda item: (
                    item.kind.value, item.source.stable_key, item.target.stable_key
                ),
            )),
        )
        object.__setattr__(self, "capabilities", tuple(sorted(capabilities)))
        object.__setattr__(
            self, "permissions", tuple(sorted(self.permissions, key=lambda item: item.value))
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "worker_id": self.worker_id,
            "worker_version": self.worker_version,
            "implementation_digest": self.implementation_digest,
            "protocol_version": self.protocol_version,
            "scopes": [item.to_dict() for item in self.scopes],
            "capabilities": list(self.capabilities),
            "permissions": [item.value for item in self.permissions],
            "limits": self.limits.to_dict(),
        }

    @property
    def manifest_digest(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.to_payload())).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self.to_payload(), "manifest_digest": self.manifest_digest}

    def to_json_bytes(self) -> bytes:
        return _canonical_bytes(self.to_document()) + b"\n"

    def supports(self, transition: MigrationTransition) -> bool:
        if not isinstance(transition, MigrationTransition):
            raise TypeError("transition must be a MigrationTransition")
        if transition.worker_id != self.worker_id or transition.worker_version != self.worker_version:
            return False
        if not set(transition.required_capabilities).issubset(self.capabilities):
            return False
        return any(
            scope.kind is transition.kind
            and scope.source == transition.source
            and scope.target == transition.target
            for scope in self.scopes
        )

    @classmethod
    def from_document(cls, document: object) -> "MigrationWorkerManifest":
        required = {
            "schema", "worker_id", "worker_version", "implementation_digest",
            "protocol_version", "scopes", "capabilities", "permissions",
            "limits", "manifest_digest",
        }
        if not isinstance(document, dict) or set(document) != required:
            raise ValueError("worker manifest has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise ValueError("unsupported worker manifest schema")
        payload = {key: value for key, value in document.items() if key != "manifest_digest"}
        digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if document["manifest_digest"] != digest:
            raise ValueError("worker manifest digest mismatch")
        scopes_data = document["scopes"]
        if not isinstance(scopes_data, list) or not 1 <= len(scopes_data) <= _MAX_SCOPES:
            raise ValueError("worker scopes must be a bounded non-empty array")
        scopes = []
        for item in scopes_data:
            if not isinstance(item, dict) or set(item) != {"kind", "source", "target"}:
                raise ValueError("worker scope has missing or unexpected fields")
            try:
                kind = TransitionKind(item["kind"])
            except (ValueError, TypeError) as exc:
                raise ValueError("unknown worker transition kind") from exc
            scopes.append(WorkerScope(
                kind=kind,
                source=identity_from_dict(item["source"]),
                target=identity_from_dict(item["target"]),
            ))
        capabilities = document["capabilities"]
        permissions = document["permissions"]
        limits = document["limits"]
        if not isinstance(capabilities, list) or not isinstance(permissions, list):
            raise ValueError("worker capabilities and permissions must be arrays")
        if not isinstance(limits, dict) or set(limits) != {
            "timeout_seconds", "max_input_bytes", "max_output_bytes", "max_changed_files"
        }:
            raise ValueError("worker limits have missing or unexpected fields")
        try:
            parsed_permissions = tuple(WorkerPermission(item) for item in permissions)
        except (ValueError, TypeError) as exc:
            raise ValueError("unknown worker permission") from exc
        manifest = cls(
            worker_id=document["worker_id"],
            worker_version=document["worker_version"],
            implementation_digest=document["implementation_digest"],
            protocol_version=document["protocol_version"],
            scopes=tuple(scopes),
            capabilities=tuple(capabilities),
            permissions=parsed_permissions,
            limits=WorkerResourceLimits(**limits),
        )
        if manifest.to_document() != document:
            raise ValueError("worker manifest is not in canonical form")
        return manifest

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "MigrationWorkerManifest":
        if isinstance(data, bytes):
            if len(data) > 4 * 1024 * 1024:
                raise ValueError("worker manifest exceeds the 4 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("worker manifest must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 4 * 1024 * 1024:
                raise ValueError("worker manifest exceeds the 4 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source,
                object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid worker manifest JSON") from exc
        canonical = _canonical_bytes(document)
        encoded_source = source.encode("utf-8")
        if encoded_source not in {canonical, canonical + b"\n"}:
            raise ValueError("worker manifest JSON is not in canonical form")
        return cls.from_document(document)


@dataclass(frozen=True, slots=True)
class WorkerQualification:
    qualification_id: str
    worker_id: str
    worker_version: str
    manifest_digest: str
    conformance_suite_id: str
    conformance_suite_version: str
    conformance_suite_digest: str
    result_digest: str
    result_status: str
    test_count: int
    qualified_by: str
    qualified_at: str
    valid_until: str

    def __post_init__(self) -> None:
        _text(self.qualification_id, "qualification_id", 256)
        _text(self.worker_id, "worker_id", 256)
        _text(self.worker_version, "worker_version", 128)
        _hex_digest(self.manifest_digest, "manifest_digest")
        _text(self.conformance_suite_id, "conformance_suite_id", 256)
        _text(self.conformance_suite_version, "conformance_suite_version", 128)
        _digest(self.conformance_suite_digest, "conformance_suite_digest")
        _digest(self.result_digest, "result_digest")
        if self.result_status != "PASS":
            raise ValueError("worker qualification result_status must be PASS")
        _positive_int(self.test_count, "test_count", 1_000_000)
        _text(self.qualified_by, "qualified_by", 256)
        qualified = parse_timestamp(self.qualified_at)
        expires = parse_timestamp(self.valid_until)
        if len(self.qualified_at) > 64 or len(self.valid_until) > 64:
            raise ValueError("qualification timestamps must not exceed 64 characters")
        if expires <= qualified:
            raise ValueError("valid_until must be later than qualified_at")

    def to_json_bytes(self) -> bytes:
        return _canonical_bytes(self.to_dict()) + b"\n"

    @classmethod
    def from_document(cls, document: object) -> "WorkerQualification":
        expected = {
            "schema", "qualification_id", "worker_id", "worker_version", "manifest_digest",
            "conformance_suite_id", "conformance_suite_version", "conformance_suite_digest",
            "result_digest", "result_status", "test_count", "qualified_by", "qualified_at", "valid_until",
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise ValueError("worker qualification has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise ValueError("unsupported worker qualification schema")
        qualification = cls(
            qualification_id=document["qualification_id"],
            worker_id=document["worker_id"],
            worker_version=document["worker_version"],
            manifest_digest=document["manifest_digest"],
            conformance_suite_id=document["conformance_suite_id"],
            conformance_suite_version=document["conformance_suite_version"],
            conformance_suite_digest=document["conformance_suite_digest"],
            result_digest=document["result_digest"],
            result_status=document["result_status"],
            test_count=document["test_count"],
            qualified_by=document["qualified_by"],
            qualified_at=document["qualified_at"],
            valid_until=document["valid_until"],
        )
        if qualification.to_dict() != document:
            raise ValueError("worker qualification is not in canonical form")
        return qualification

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "WorkerQualification":
        if isinstance(data, bytes):
            if len(data) > 1024 * 1024:
                raise ValueError("worker qualification exceeds the 1 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("worker qualification must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 1024 * 1024:
                raise ValueError("worker qualification exceeds the 1 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source,
                object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid worker qualification JSON") from exc
        canonical = _canonical_bytes(document)
        encoded_source = source.encode("utf-8")
        if encoded_source not in {canonical, canonical + b"\n"}:
            raise ValueError("worker qualification JSON is not in canonical form")
        return cls.from_document(document)

    @property
    def qualification_digest(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.to_dict())).hexdigest()

    def is_current(self, manifest: MigrationWorkerManifest, now: datetime | None = None) -> bool:
        if not isinstance(manifest, MigrationWorkerManifest):
            raise TypeError("manifest must be a MigrationWorkerManifest")
        instant = datetime.now(timezone.utc) if now is None else now
        if not isinstance(instant, datetime):
            raise TypeError("now must be a datetime")
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        instant = instant.astimezone(timezone.utc)
        return (
            self.worker_id == manifest.worker_id
            and self.worker_version == manifest.worker_version
            and self.manifest_digest == manifest.manifest_digest
            and parse_timestamp(self.qualified_at) <= instant < parse_timestamp(self.valid_until)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "qualification_id": self.qualification_id,
            "worker_id": self.worker_id,
            "worker_version": self.worker_version,
            "manifest_digest": self.manifest_digest,
            "conformance_suite_id": self.conformance_suite_id,
            "conformance_suite_version": self.conformance_suite_version,
            "conformance_suite_digest": self.conformance_suite_digest,
            "result_digest": self.result_digest,
            "result_status": self.result_status,
            "test_count": self.test_count,
            "qualified_by": self.qualified_by,
            "qualified_at": self.qualified_at,
            "valid_until": self.valid_until,
        }


@dataclass(frozen=True, slots=True)
class WorkerTrustPolicy:
    """Local allowlist for exact qualification digests; the policy source must be trusted."""

    policy_id: str
    reviewed_by: str
    reviewed_at: str
    trusted_qualification_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.policy_id, "policy_id", 256)
        _text(self.reviewed_by, "reviewed_by", 256)
        reviewed = parse_timestamp(self.reviewed_at)
        if reviewed.isoformat().replace("+00:00", "Z") != self.reviewed_at:
            raise ValueError("reviewed_at must use canonical UTC format")
        if not isinstance(self.trusted_qualification_digests, (tuple, list)):
            raise ValueError("trusted_qualification_digests must be a sequence")
        digests = tuple(self.trusted_qualification_digests)
        if len(digests) > 10000:
            raise ValueError("trusted_qualification_digests exceeds the 10000-entry limit")
        for digest in digests:
            _hex_digest(digest, "trusted qualification digest")
        if len(digests) != len(set(digests)):
            raise ValueError("trusted qualification digests must be unique")
        object.__setattr__(self, "trusted_qualification_digests", tuple(sorted(digests)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "policy_id": self.policy_id,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "trusted_qualification_digests": list(self.trusted_qualification_digests),
        }

    @property
    def policy_digest(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.to_dict())).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self.to_dict(), "policy_digest": self.policy_digest}

    def to_json_bytes(self) -> bytes:
        return _canonical_bytes(self.to_document()) + b"\n"

    def trusts(self, qualification_digest: str) -> bool:
        return qualification_digest in self.trusted_qualification_digests

    @classmethod
    def from_document(cls, document: object) -> "WorkerTrustPolicy":
        expected = {
            "schema", "policy_id", "reviewed_by", "reviewed_at",
            "trusted_qualification_digests", "policy_digest",
        }
        if not isinstance(document, dict) or set(document) != expected:
            raise ValueError("worker trust policy has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise ValueError("unsupported worker trust policy schema")
        payload = {key: value for key, value in document.items() if key != "policy_digest"}
        digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if document["policy_digest"] != digest:
            raise ValueError("worker trust policy digest mismatch")
        if not isinstance(document["trusted_qualification_digests"], list):
            raise ValueError("trusted_qualification_digests must be an array")
        policy = cls(
            policy_id=document["policy_id"],
            reviewed_by=document["reviewed_by"],
            reviewed_at=document["reviewed_at"],
            trusted_qualification_digests=tuple(document["trusted_qualification_digests"]),
        )
        if policy.to_document() != document:
            raise ValueError("worker trust policy is not canonical")
        return policy

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "WorkerTrustPolicy":
        if isinstance(data, bytes):
            if len(data) > 1024 * 1024:
                raise ValueError("worker trust policy exceeds the 1 MiB import limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("worker trust policy must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > 1024 * 1024:
                raise ValueError("worker trust policy exceeds the 1 MiB import limit")
            source = data
        else:
            raise TypeError("data must be bytes or str")
        try:
            document = json.loads(
                source, object_pairs_hook=strict_object_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid worker trust policy JSON") from exc
        canonical = _canonical_bytes(document)
        if source.encode("utf-8") not in {canonical, canonical + b"\n"}:
            raise ValueError("worker trust policy JSON is not canonical")
        return cls.from_document(document)


@dataclass(frozen=True, slots=True)
class WorkerRegistration:
    manifest: MigrationWorkerManifest
    qualification: WorkerQualification | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, MigrationWorkerManifest):
            raise ValueError("registration must contain a MigrationWorkerManifest")
        if self.qualification is not None:
            if not isinstance(self.qualification, WorkerQualification):
                raise ValueError("qualification must be a WorkerQualification or None")
            if (
                self.qualification.worker_id != self.manifest.worker_id
                or self.qualification.worker_version != self.manifest.worker_version
            ):
                raise ValueError("qualification worker identity does not match the manifest")


@dataclass(frozen=True, slots=True)
class WorkerResolution:
    status: str
    worker_id: str | None
    worker_version: str | None
    manifest_digest: str | None
    qualification_id: str | None
    qualification_digest: str | None
    permissions: tuple[WorkerPermission, ...]
    limits: WorkerResourceLimits | None
    reason: str

    def __post_init__(self) -> None:
        if self.status not in _RESOLUTION_STATUSES:
            raise ValueError("unsupported worker resolution status")
        if not isinstance(self.reason, str) or not self.reason.strip() or len(self.reason) > 2048:
            raise ValueError("worker resolution reason must be non-empty and bounded")
        has_worker = self.worker_id is not None and self.worker_version is not None
        if (self.worker_id is None) != (self.worker_version is None):
            raise ValueError("worker resolution identity must include both ID and version")
        if has_worker:
            _text(self.worker_id, "worker_id", 256)
            _text(self.worker_version, "worker_version", 128)
        if not isinstance(self.permissions, (tuple, list)) or any(
            not isinstance(item, WorkerPermission) for item in self.permissions
        ):
            raise ValueError("worker resolution permissions must be WorkerPermission values")
        object.__setattr__(self, "permissions", tuple(self.permissions))
        if self.limits is not None and not isinstance(self.limits, WorkerResourceLimits):
            raise ValueError("worker resolution limits must be WorkerResourceLimits or None")
        if self.manifest_digest is not None:
            _hex_digest(self.manifest_digest, "manifest_digest")
        if self.qualification_digest is not None:
            _hex_digest(self.qualification_digest, "qualification_digest")
        if self.qualification_id is not None:
            _text(self.qualification_id, "qualification_id", 256)

        if self.status == "NOT_SELECTED":
            if has_worker or any((
                self.manifest_digest, self.qualification_id, self.qualification_digest,
                self.permissions, self.limits,
            )):
                raise ValueError("NOT_SELECTED resolution cannot contain worker registration data")
        elif self.status == "NOT_REGISTERED":
            if not has_worker or any((
                self.manifest_digest, self.qualification_id, self.qualification_digest,
                self.permissions, self.limits,
            )):
                raise ValueError("NOT_REGISTERED resolution contains inconsistent registration data")
        elif self.status == "BLOCKED":
            if any((
                self.manifest_digest, self.qualification_id, self.qualification_digest,
                self.permissions, self.limits,
            )):
                raise ValueError("BLOCKED resolution cannot contain worker registration or qualification data")
        elif self.status == "INCOMPATIBLE":
            if not has_worker or not self.manifest_digest or self.qualification_id or self.qualification_digest or not self.limits:
                raise ValueError("INCOMPATIBLE resolution requires a manifest but no qualification")
        elif self.status == "UNQUALIFIED":
            if not has_worker or not self.manifest_digest or self.qualification_id or self.qualification_digest or not self.limits:
                raise ValueError("UNQUALIFIED resolution requires a manifest but no qualification")
        elif self.status in {"STALE", "UNTRUSTED", "QUALIFIED"}:
            if not has_worker or not self.manifest_digest or not self.qualification_id or not self.qualification_digest or not self.limits:
                raise ValueError(f"{self.status} resolution requires manifest and qualification provenance")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "worker_id": self.worker_id,
            "worker_version": self.worker_version,
            "manifest_digest": self.manifest_digest,
            "qualification_id": self.qualification_id,
            "qualification_digest": self.qualification_digest,
            "permissions": [item.value for item in self.permissions],
            "limits": self.limits.to_dict() if self.limits is not None else None,
            "reason": self.reason,
        }

    @property
    def qualified(self) -> bool:
        """True only when the exact worker manifest has a current PASS qualification record."""
        return self.status == "QUALIFIED"


class MigrationWorkerRegistry:
    """Local allow-list; qualification requires an exact trusted digest allowlist."""

    __slots__ = ("_registrations", "_trust_policy")

    def __setattr__(self, name, value) -> None:
        if hasattr(self, name):
            raise AttributeError("MigrationWorkerRegistry is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name) -> None:
        raise AttributeError("MigrationWorkerRegistry is immutable")

    def __init__(
        self,
        registrations: tuple[WorkerRegistration, ...] = (),
        *,
        trust_policy: WorkerTrustPolicy | None = None,
    ) -> None:
        if trust_policy is not None and not isinstance(trust_policy, WorkerTrustPolicy):
            raise TypeError("trust_policy must be a WorkerTrustPolicy")
        if not isinstance(registrations, (tuple, list)):
            raise TypeError("registrations must be a sequence")
        if len(registrations) > 10_000:
            raise ValueError("worker registry exceeds the 10000-registration limit")
        indexed = {}
        for registration in registrations:
            if not isinstance(registration, WorkerRegistration):
                raise TypeError("registrations must contain WorkerRegistration values")
            key = (registration.manifest.worker_id, registration.manifest.worker_version)
            if key in indexed:
                raise ValueError(f"duplicate worker registration: {key[0]}@{key[1]}")
            indexed[key] = registration
        self._registrations = MappingProxyType(indexed)
        self._trust_policy = trust_policy

    @property
    def trust_policy_digest(self) -> str | None:
        return self._trust_policy.policy_digest if self._trust_policy is not None else None

    def registrations(self) -> tuple[WorkerRegistration, ...]:
        return tuple(self._registrations[key] for key in sorted(self._registrations))

    def resolve(
        self, transition: MigrationTransition, now: datetime | None = None
    ) -> WorkerResolution:
        if not isinstance(transition, MigrationTransition):
            raise TypeError("transition must be a MigrationTransition")
        if now is not None:
            if not isinstance(now, datetime):
                raise TypeError("now must be a datetime")
            if now.tzinfo is None or now.utcoffset() is None:
                raise ValueError("now must be timezone-aware")
        if not transition.enabled:
            return WorkerResolution(
                "BLOCKED", transition.worker_id, transition.worker_version,
                None, None, None, (), None, "Transition is disabled by its migration declaration",
            )
        if transition.worker_id is None:
            return WorkerResolution(
                "NOT_SELECTED", None, None, None, None, None, (), None,
                "No worker is pinned to this transition",
            )
        key = (transition.worker_id, transition.worker_version)
        registration = self._registrations.get(key)
        if registration is None:
            return WorkerResolution(
                "NOT_REGISTERED", transition.worker_id, transition.worker_version,
                None, None, None, (), None, "Pinned worker version is not registered",
            )
        manifest = registration.manifest
        if not manifest.supports(transition):
            return WorkerResolution(
                "INCOMPATIBLE", manifest.worker_id, manifest.worker_version,
                manifest.manifest_digest, None, None, manifest.permissions, manifest.limits,
                "Worker manifest does not declare this exact scope or required capabilities",
            )
        qualification = registration.qualification
        if qualification is None:
            return WorkerResolution(
                "UNQUALIFIED", manifest.worker_id, manifest.worker_version,
                manifest.manifest_digest, None, None, manifest.permissions, manifest.limits,
                "Worker has no conformance qualification record",
            )
        if not qualification.is_current(manifest, now):
            return WorkerResolution(
                "STALE", manifest.worker_id, manifest.worker_version,
                manifest.manifest_digest, qualification.qualification_id,
                qualification.qualification_digest, manifest.permissions, manifest.limits,
                "Worker qualification is expired or does not match the current manifest digest",
            )
        if (
            self._trust_policy is None
            or not self._trust_policy.trusts(qualification.qualification_digest)
        ):
            return WorkerResolution(
                "UNTRUSTED", manifest.worker_id, manifest.worker_version,
                manifest.manifest_digest, qualification.qualification_id,
                qualification.qualification_digest, manifest.permissions, manifest.limits,
                "Worker qualification is not allowlisted by the active local trust policy",
            )
        return WorkerResolution(
            "QUALIFIED", manifest.worker_id, manifest.worker_version,
            manifest.manifest_digest, qualification.qualification_id,
            qualification.qualification_digest, manifest.permissions, manifest.limits,
            "Pinned worker version is scope-compatible and has a current qualification record",
        )



@dataclass(frozen=True, slots=True)
class RouteWorkerAssessment:
    """Snapshot of worker qualification for every edge in one route plan.

    QUALIFIED is an engineering eligibility signal only. It is not execution
    authorization and does not assert that worker code has been launched.
    """

    route_plan_digest: str
    evaluated_at: str
    status: str
    evaluations: tuple[tuple[MigrationTransition, WorkerResolution], ...]
    reason: str

    def __post_init__(self) -> None:
        _hex_digest(self.route_plan_digest, "route_plan_digest")
        instant = parse_timestamp(self.evaluated_at)
        if instant.isoformat().replace("+00:00", "Z") != self.evaluated_at:
            raise ValueError("assessment time must use canonical UTC format")
        if self.status not in {
            "ROUTE_NOT_PLANNED", "NO_WORK_REQUIRED", "UNKNOWN", "BLOCKED", "QUALIFIED"
        }:
            raise ValueError("unsupported route worker assessment status")
        if not isinstance(self.reason, str) or not self.reason.strip() or len(self.reason) > 2048:
            raise ValueError("assessment reason must be non-empty and bounded")
        if not isinstance(self.evaluations, (tuple, list)) or any(
            not isinstance(item, tuple) or len(item) != 2
            or not isinstance(item[0], MigrationTransition)
            or not isinstance(item[1], WorkerResolution)
            for item in self.evaluations
        ):
            raise ValueError("evaluations must be transition/resolution pairs")
        evaluations = tuple(self.evaluations)
        transition_ids = [transition.transition_id for transition, _ in evaluations]
        if len(transition_ids) != len(set(transition_ids)):
            raise ValueError("route worker assessment contains duplicate transitions")
        for transition, resolution in evaluations:
            if transition.worker_id is None:
                if resolution.status != "NOT_SELECTED":
                    raise ValueError("unselected transition must have a NOT_SELECTED worker resolution")
            elif (
                resolution.worker_id != transition.worker_id
                or resolution.worker_version != transition.worker_version
            ):
                raise ValueError("worker resolution does not match the transition's pinned worker")
        if any(
            evaluations[index][0].target != evaluations[index + 1][0].source
            for index in range(len(evaluations) - 1)
        ):
            raise ValueError("route worker assessment transitions are not contiguous")
        if self.status in {"ROUTE_NOT_PLANNED", "NO_WORK_REQUIRED"} and evaluations:
            raise ValueError(f"{self.status} assessment must not contain worker evaluations")
        if self.status == "QUALIFIED" and (
            not evaluations or any(not resolution.qualified for _, resolution in evaluations)
        ):
            raise ValueError("QUALIFIED assessment requires a qualification for every route transition")
        if self.status == "UNKNOWN" and (
            not evaluations or not any(
                resolution.status in {"NOT_SELECTED", "NOT_REGISTERED", "UNQUALIFIED", "STALE"}
                for _, resolution in evaluations
            ) or any(
                resolution.status in {"BLOCKED", "INCOMPATIBLE"}
                for _, resolution in evaluations
            )
        ):
            raise ValueError("UNKNOWN assessment requires at least one missing or stale qualification")
        if self.status == "BLOCKED" and (
            not evaluations or not any(
                resolution.status in {"BLOCKED", "INCOMPATIBLE"}
                for _, resolution in evaluations
            )
        ):
            raise ValueError("BLOCKED assessment requires a disabled or incompatible transition")
        object.__setattr__(self, "evaluations", evaluations)

    @property
    def qualified(self) -> bool:
        """True only when at least one worker was assessed and all are qualified."""
        return self.status == "QUALIFIED"

    @property
    def worker_gate_satisfied(self) -> bool:
        """True when all required workers are qualified or no worker operation is needed."""
        return self.status in {"QUALIFIED", "NO_WORK_REQUIRED"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "route_plan_digest": self.route_plan_digest,
            "evaluated_at": self.evaluated_at,
            "status": self.status,
            "evaluations": [
                {
                    "transition": transition.to_dict(),
                    "resolution": resolution.to_dict(),
                }
                for transition, resolution in self.evaluations
            ],
            "reason": self.reason,
        }

    @property
    def assessment_digest(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.to_dict())).hexdigest()


def assess_route_workers(
    plan: RoutePlan,
    registry: MigrationWorkerRegistry,
    now: datetime | None = None,
) -> RouteWorkerAssessment:
    """Assess exact worker qualification for a route at the plan's evaluation instant."""
    if not isinstance(plan, RoutePlan):
        raise TypeError("plan must be a RoutePlan")
    if not isinstance(registry, MigrationWorkerRegistry):
        raise TypeError("registry must be a MigrationWorkerRegistry")
    planned_at = parse_timestamp(plan.evaluated_at)
    instant = planned_at if now is None else now
    if not isinstance(instant, datetime):
        raise TypeError("now must be a datetime")
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    instant = instant.astimezone(timezone.utc)
    evaluated_at = instant.isoformat().replace("+00:00", "Z")
    if evaluated_at != plan.evaluated_at:
        raise ValueError("worker qualification must use the route plan's exact evaluation timestamp")

    if not plan.plannable:
        return RouteWorkerAssessment(
            plan.plan_digest, evaluated_at, "ROUTE_NOT_PLANNED", (),
            "Worker qualification is not evaluated until the route itself is PLANNED",
        )
    if not plan.transitions:
        return RouteWorkerAssessment(
            plan.plan_digest, evaluated_at, "NO_WORK_REQUIRED", (),
            "The source already matches the target; no worker transition is required",
        )

    evaluations = tuple(
        (transition, registry.resolve(transition, instant))
        for transition in plan.transitions
    )
    statuses = {resolution.status for _, resolution in evaluations}
    if statuses == {"QUALIFIED"}:
        status = "QUALIFIED"
        reason = "Every route transition has a current qualification for its exact pinned worker manifest"
    elif statuses & {"BLOCKED", "INCOMPATIBLE"}:
        status = "BLOCKED"
        reason = "At least one route transition is disabled or incompatible with its registered worker"
    else:
        status = "UNKNOWN"
        reason = "At least one route transition is unselected, unregistered, unqualified, or stale"
    return RouteWorkerAssessment(plan.plan_digest, evaluated_at, status, evaluations, reason)


def serialize_worker_manifest(manifest: MigrationWorkerManifest) -> bytes:
    if not isinstance(manifest, MigrationWorkerManifest):
        raise TypeError("manifest must be a MigrationWorkerManifest")
    return manifest.to_json_bytes()


def deserialize_worker_manifest(data: bytes | str) -> MigrationWorkerManifest:
    return MigrationWorkerManifest.from_json_bytes(data)


def serialize_worker_qualification(qualification: WorkerQualification) -> bytes:
    if not isinstance(qualification, WorkerQualification):
        raise TypeError("qualification must be a WorkerQualification")
    return qualification.to_json_bytes()


def deserialize_worker_qualification(data: bytes | str) -> WorkerQualification:
    return WorkerQualification.from_json_bytes(data)


__all__ = [
    "MigrationWorkerManifest",
    "MigrationWorkerRegistry",
    "WorkerPermission",
    "WorkerQualification",
    "WorkerRegistration",
    "WorkerResolution",
    "WorkerResourceLimits",
    "WorkerScope",
    "RouteWorkerAssessment",
    "assess_route_workers",
    "deserialize_worker_manifest",
    "deserialize_worker_qualification",
    "serialize_worker_manifest",
    "serialize_worker_qualification",
]

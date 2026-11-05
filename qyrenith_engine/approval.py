"""Interactive, scope-bound, replay-resistant local host approvals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import getpass
import hashlib
import hmac
import json
import re
import secrets
import uuid
from typing import Any, TextIO
import sys

from .trust_store import OwnerTrustStore, TrustStoreError, _canonical

_MAX_SCOPE_BYTES = 64 * 1024
_MAX_APPROVAL_BYTES = 128 * 1024
_ACTION = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_NONCE = re.compile(r"^[0-9a-f]{48}$")


class HostApprovalError(RuntimeError):
    """A host approval is unavailable, invalid, expired, or already consumed."""


def _utc(value: datetime, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise HostApprovalError(f"{field} must be a bounded UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HostApprovalError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HostApprovalError(f"{field} must include a timezone")
    normalized = parsed.astimezone(timezone.utc)
    if _utc(normalized, field) != value:
        raise HostApprovalError(f"{field} must use canonical UTC seconds")
    return normalized


def _validate_scope_value(value: Any) -> None:
    if value is None or type(value) in {str, bool, int}:
        return
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("approval scope cannot contain non-finite numbers")
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("approval scope object keys must be strings")
        for item in value.values():
            _validate_scope_value(item)
        return
    if isinstance(value, list):
        for item in value:
            _validate_scope_value(item)
        return
    raise ValueError("approval scope must contain only JSON objects, arrays, and scalar values")


def _scope_bytes(scope: object) -> bytes:
    if not isinstance(scope, dict):
        raise ValueError("approval scope must be a JSON object")
    try:
        _validate_scope_value(scope)
        encoded = _canonical(scope)
    except (TypeError, ValueError) as exc:
        raise ValueError("approval scope must contain only finite JSON values with string keys") from exc
    if len(encoded) > _MAX_SCOPE_BYTES:
        raise ValueError("approval scope exceeds the 64 KiB limit")
    return encoded


def _scope_digest(scope: object) -> str:
    return hashlib.sha256(_scope_bytes(scope)).hexdigest()


def _request_payload(
    request_id: str,
    action_type: str,
    scope_digest: str,
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    return {
        "schema": 1,
        "request_id": request_id,
        "action_type": action_type,
        "scope_digest": scope_digest,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
    }


@dataclass(frozen=True)
class HostApprovalRequest:
    request_id: str
    action_type: str
    scope_json: str
    scope_digest: str
    issued_at: str
    expires_at: str
    nonce: str
    request_digest: str

    @property
    def scope(self) -> dict[str, Any]:
        return json.loads(self.scope_json)

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.request_id):
            raise ValueError("request_id must be a UUID hex value")
        if not isinstance(self.action_type, str) or not _ACTION.fullmatch(self.action_type):
            raise ValueError("action_type must be a canonical uppercase identifier")
        if not isinstance(self.scope_json, str) or len(self.scope_json.encode("utf-8")) > _MAX_SCOPE_BYTES:
            raise ValueError("scope_json exceeds the 64 KiB limit")
        try:
            scope = json.loads(self.scope_json)
        except json.JSONDecodeError as exc:
            raise ValueError("scope_json must be valid JSON") from exc
        if _canonical(scope).decode("utf-8") != self.scope_json:
            raise ValueError("scope_json must be canonical JSON")
        if _scope_digest(scope) != self.scope_digest:
            raise ValueError("approval scope digest mismatch")
        _parse_utc(self.issued_at, "issued_at")
        issued = _parse_utc(self.issued_at, "issued_at")
        expiry = _parse_utc(self.expires_at, "expires_at")
        if expiry <= issued or (expiry - issued) > timedelta(minutes=15):
            raise ValueError("approval request lifetime must be between zero and 15 minutes")
        if not isinstance(self.nonce, str) or not _NONCE.fullmatch(self.nonce):
            raise ValueError("approval nonce must be 48 lowercase hex characters")
        expected = hashlib.sha256(_canonical(_request_payload(
            self.request_id, self.action_type, self.scope_digest,
            self.issued_at, self.expires_at, self.nonce,
        ))).hexdigest()
        if self.request_digest != expected:
            raise ValueError("approval request digest mismatch")


@dataclass(frozen=True)
class HostApproval:
    approval_id: str
    request_id: str
    action_type: str
    request_digest: str
    scope_digest: str
    issued_at: str
    approved_at: str
    expires_at: str
    nonce: str
    approved_by: str
    host_principal: str
    trust_store_id: str
    trust_store_generation: int
    signature: str

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "approval_id": self.approval_id,
            "request_id": self.request_id,
            "action_type": self.action_type,
            "request_digest": self.request_digest,
            "scope_digest": self.scope_digest,
            "issued_at": self.issued_at,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "approved_by": self.approved_by,
            "host_principal": self.host_principal,
            "trust_store_id": self.trust_store_id,
            "trust_store_generation": self.trust_store_generation,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "signature": self.signature}

    @property
    def approval_digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def __post_init__(self) -> None:
        if not isinstance(self.approval_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.approval_id):
            raise ValueError("approval_id must be a UUID hex value")
        if not isinstance(self.request_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.request_id):
            raise ValueError("request_id must be a UUID hex value")
        if not isinstance(self.action_type, str) or not _ACTION.fullmatch(self.action_type):
            raise ValueError("action_type must be a canonical uppercase identifier")
        for field, value in (
            ("request_digest", self.request_digest),
            ("scope_digest", self.scope_digest),
            ("signature", self.signature),
        ):
            if not isinstance(value, str) or not _HEX.fullmatch(value):
                raise ValueError(f"{field} must be a lowercase SHA-256 digest")
        if not isinstance(self.nonce, str) or not _NONCE.fullmatch(self.nonce):
            raise ValueError("approval nonce must be 48 lowercase hex characters")
        if not isinstance(self.trust_store_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.trust_store_id):
            raise ValueError("trust_store_id must be a UUID hex value")
        if type(self.trust_store_generation) is not int or self.trust_store_generation < 0:
            raise ValueError("trust_store_generation must be a non-negative integer")
        for field, value in (
            ("approved_by", self.approved_by),
            ("host_principal", self.host_principal),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError(f"{field} must be non-empty bounded text")
        issued = _parse_utc(self.issued_at, "issued_at")
        approved = _parse_utc(self.approved_at, "approved_at")
        expiry = _parse_utc(self.expires_at, "expires_at")
        if approved < issued or expiry <= approved or (expiry - issued) > timedelta(minutes=15):
            raise ValueError("approval timestamps are outside the request lifetime")
        expected_request = hashlib.sha256(_canonical(_request_payload(
            self.request_id, self.action_type, self.scope_digest,
            self.issued_at, self.expires_at, self.nonce,
        ))).hexdigest()
        if self.request_digest != expected_request:
            raise ValueError("approval request digest mismatch")

    def to_json_bytes(self) -> bytes:
        return _canonical(self.to_dict()) + b"\n"

    @classmethod
    def from_json_bytes(cls, data: bytes | str) -> "HostApproval":
        if isinstance(data, bytes):
            if len(data) > _MAX_APPROVAL_BYTES:
                raise HostApprovalError("host approval exceeds the 128 KiB limit")
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HostApprovalError("host approval must be UTF-8") from exc
        elif isinstance(data, str):
            if len(data.encode("utf-8")) > _MAX_APPROVAL_BYTES:
                raise HostApprovalError("host approval exceeds the 128 KiB limit")
            source = data
        else:
            raise TypeError("host approval data must be bytes or str")
        try:
            document = json.loads(source, object_pairs_hook=_unique_pairs)
        except (json.JSONDecodeError, HostApprovalError) as exc:
            raise HostApprovalError("host approval JSON is invalid") from exc
        expected_fields = {
            "schema", "approval_id", "request_id", "action_type", "request_digest",
            "scope_digest", "issued_at", "approved_at", "expires_at", "nonce",
            "approved_by", "host_principal", "trust_store_id",
            "trust_store_generation", "signature",
        }
        if not isinstance(document, dict) or set(document) != expected_fields:
            raise HostApprovalError("host approval has missing or unexpected fields")
        if type(document["schema"]) is not int or document["schema"] != 1:
            raise HostApprovalError("unsupported host approval schema")
        try:
            approval = cls(**{key: value for key, value in document.items() if key != "schema"})
        except (TypeError, ValueError) as exc:
            raise HostApprovalError("host approval fields are invalid") from exc
        canonical = approval.to_json_bytes()
        if source.encode("utf-8") not in {canonical, canonical.rstrip(b"\n")}:
            raise HostApprovalError("host approval JSON is not canonical")
        return approval


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise HostApprovalError(f"duplicate host approval JSON key: {key}")
        result[key] = value
    return result


def create_host_approval_request(
    action_type: str,
    scope: dict[str, Any],
    *,
    lifetime_seconds: int = 300,
    now: datetime | None = None,
) -> HostApprovalRequest:
    if not isinstance(action_type, str) or not _ACTION.fullmatch(action_type):
        raise ValueError("action_type must be a canonical uppercase identifier")
    if type(lifetime_seconds) is not int or not 1 <= lifetime_seconds <= 900:
        raise ValueError("lifetime_seconds must be between 1 and 900")
    instant = datetime.now(timezone.utc) if now is None else now
    issued_at = _utc(instant, "now")
    expires_at = _utc(instant + timedelta(seconds=lifetime_seconds), "expires_at")
    scope_bytes = _scope_bytes(scope)
    digest = hashlib.sha256(scope_bytes).hexdigest()
    request_id = uuid.uuid4().hex
    nonce = secrets.token_hex(24)
    request_digest = hashlib.sha256(_canonical(_request_payload(
        request_id, action_type, digest, issued_at, expires_at, nonce,
    ))).hexdigest()
    return HostApprovalRequest(
        request_id, action_type, scope_bytes.decode("utf-8"), digest,
        issued_at, expires_at, nonce, request_digest,
    )


def approve_host_request(
    request: HostApprovalRequest,
    trust_store: OwnerTrustStore,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    now: datetime | None = None,
) -> HostApproval:
    if not isinstance(request, HostApprovalRequest):
        raise TypeError("request must be a HostApprovalRequest")
    if not isinstance(trust_store, OwnerTrustStore):
        raise TypeError("trust_store must be an OwnerTrustStore")
    source = sys.stdin if input_stream is None else input_stream
    output = sys.stdout if output_stream is None else output_stream
    if not source.isatty() or not output.isatty():
        raise HostApprovalError("authenticated local approval requires an interactive terminal")
    issued = _parse_utc(request.issued_at, "issued_at")
    expiry = _parse_utc(request.expires_at, "expires_at")
    instant = datetime.now(timezone.utc) if now is None else now
    approved_at = _utc(instant, "approved_at")
    approved = _parse_utc(approved_at, "approved_at")
    if approved < issued or approved >= expiry:
        raise HostApprovalError("approval request is not currently valid")
    print("QYRENITH HOST ACTION APPROVAL", file=output)
    print(f"Action: {request.action_type}", file=output)
    print(f"Request ID: {request.request_id}", file=output)
    print(f"Scope digest: sha256:{request.scope_digest}", file=output)
    print(f"Expires: {request.expires_at}", file=output)
    print("Exact action scope:", file=output)
    print(json.dumps(request.scope, indent=2, sort_keys=True, ensure_ascii=True), file=output)
    print("Approval grants only this exact scope. It does not bypass OS sandbox policy.", file=output)
    challenge = f"APPROVE {request.action_type} {request.request_id} {request.nonce}"
    print(f"To approve, type exactly: {challenge}", file=output)
    output.flush()
    supplied = source.readline().rstrip("\r\n")
    if not hmac.compare_digest(supplied, challenge):
        raise HostApprovalError("host approval challenge was not confirmed")
    trust_store.decisions()
    principal = getpass.getuser() or "local-user"
    unsigned = {
        "schema": 1,
        "approval_id": uuid.uuid4().hex,
        "request_id": request.request_id,
        "action_type": request.action_type,
        "request_digest": request.request_digest,
        "scope_digest": request.scope_digest,
        "issued_at": request.issued_at,
        "approved_at": approved_at,
        "expires_at": request.expires_at,
        "nonce": request.nonce,
        "approved_by": principal,
        "host_principal": principal,
        "trust_store_id": trust_store.store_id,
        "trust_store_generation": trust_store.generation,
    }
    signature = trust_store.sign_host_payload(unsigned)
    return HostApproval(**{key: value for key, value in unsigned.items() if key != "schema"}, signature=signature)


def validate_host_approval(
    approval: HostApproval,
    action_type: str,
    scope: dict[str, Any],
    trust_store: OwnerTrustStore,
    *,
    now: datetime | None = None,
    consume: bool = False,
) -> None:
    """Verify exact scope, local host signature, freshness, and optional single-use consumption."""
    if not isinstance(approval, HostApproval):
        raise TypeError("approval must be a HostApproval")
    if not isinstance(trust_store, OwnerTrustStore):
        raise TypeError("trust_store must be an OwnerTrustStore")
    if action_type != approval.action_type or _scope_digest(scope) != approval.scope_digest:
        raise HostApprovalError("host approval does not match the exact action scope")
    unsigned = approval.unsigned_dict()
    if not trust_store.verify_host_payload(unsigned, approval.signature):
        raise HostApprovalError("host approval signature is invalid")
    issued = _parse_utc(approval.issued_at, "issued_at")
    approved = _parse_utc(approval.approved_at, "approved_at")
    expiry = _parse_utc(approval.expires_at, "expires_at")
    instant = datetime.now(timezone.utc) if now is None else now
    current = _parse_utc(_utc(instant, "now"), "now")
    if approved < issued or current < approved or current >= expiry:
        raise HostApprovalError("host approval is not currently valid")
    nonce_digest = "sha256:" + hashlib.sha256(approval.nonce.encode("ascii")).hexdigest()
    if trust_store.is_nonce_consumed(nonce_digest):
        raise HostApprovalError("host approval nonce has already been consumed")
    trust_store.decisions()
    if (
        approval.trust_store_id != trust_store.store_id
        or approval.trust_store_generation != trust_store.generation
    ):
        raise HostApprovalError("owner trust store changed after host approval was issued")
    if consume:
        try:
            trust_store.consume_nonce(
                nonce_digest, reviewed_by=approval.host_principal,
                reviewed_at=current,
                rationale="Single-use host approval consumed at action boundary",
                expected_generation=approval.trust_store_generation,
            )
        except TrustStoreError as exc:
            raise HostApprovalError("host approval nonce replay was blocked") from exc


__all__ = [
    "HostApproval",
    "HostApprovalError",
    "HostApprovalRequest",
    "approve_host_request",
    "create_host_approval_request",
    "validate_host_approval",
]

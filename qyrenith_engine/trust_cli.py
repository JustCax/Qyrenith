"""Interactive owner trust-store administration commands."""
from __future__ import annotations

from datetime import datetime, timezone
import getpass
import hmac
import json
import re
import secrets
import sys
from typing import Any, TextIO

from .trust_store import OwnerTrustStore, TrustStoreError

_KINDS = {
    "KNOWLEDGE_CATALOG",
    "WORKER_MANIFEST",
    "WORKER_QUALIFICATION",
    "EXECUTION_POLICY",
}
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _parse_expiry(value: str | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ValueError("--expires-at must be a bounded ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("--expires-at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--expires-at must include a timezone")
    return parsed.astimezone(timezone.utc)


def run_trust_store_cli(
    args: Any,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    error_stream: TextIO | None = None,
    path: str | None = None,
) -> int:
    """Run init/list/trust/revoke. Mutating decisions require an interactive challenge."""
    source = sys.stdin if input_stream is None else input_stream
    output = sys.stdout if output_stream is None else output_stream
    errors = sys.stderr if error_stream is None else error_stream
    action = getattr(args, "trust_action", None)
    try:
        if action == "init":
            store = OwnerTrustStore.open(path, create=True)
            print(json.dumps({
                "status": "INITIALIZED",
                "store_id": store.store_id,
                "path": str(store.path),
                "generation": store.generation,
            }, indent=2), file=output)
            return 0
        if action == "list":
            store = OwnerTrustStore.open(path)
            print(json.dumps({
                "status": "OK",
                "store_id": store.store_id,
                "generation": store.generation,
                "events": [event.to_dict() for event in store.decisions()],
            }, indent=2), file=output)
            return 0
        if action not in {"trust", "revoke"}:
            raise ValueError("trust-store requires --trust-action init|list|trust|revoke")
        kind = getattr(args, "trust_kind", None)
        digest = getattr(args, "digest", None)
        rationale = getattr(args, "reason", None)
        if kind not in _KINDS:
            raise ValueError("--trust-kind is required and must be a supported subject kind")
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise ValueError("--digest must use sha256:<64 lowercase hex>")
        if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 1024:
            raise ValueError("--reason is required and must be at most 1024 characters")
        expiry = _parse_expiry(getattr(args, "expires_at", None))
        if action == "revoke" and expiry is not None:
            raise ValueError("--expires-at is valid only for trust decisions")
        if not source.isatty() or not output.isatty():
            raise TrustStoreError("trust and revoke operations require an interactive terminal")
        store = OwnerTrustStore.open(path)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        challenge = secrets.token_hex(12)
        verb = action.upper()
        expected = f"{verb} {kind} {digest} {challenge}"
        print("OWNER TRUST STORE DECISION", file=output)
        print(f"Action: {verb}", file=output)
        print(f"Subject kind: {kind}", file=output)
        print(f"Exact digest: {digest}", file=output)
        print(f"Rationale: {rationale}", file=output)
        print(f"Expiry: {expiry.isoformat() if expiry else 'none'}", file=output)
        print("This is a local trust decision, not publisher identity or sandbox approval.", file=output)
        print(f"To confirm, type exactly: {expected}", file=output)
        output.flush()
        supplied = source.readline().rstrip("\r\n")
        if not hmac.compare_digest(supplied, expected):
            print("CANCELLED: trust decision was not confirmed.", file=errors)
            return 3
        reviewer = getpass.getuser() or "local-owner"
        if action == "trust":
            event = store.trust(
                kind, digest, reviewed_by=reviewer, reviewed_at=now,
                expires_at=expiry, rationale=rationale,
            )
        else:
            event = store.revoke(
                kind, digest, reviewed_by=reviewer, reviewed_at=now,
                rationale=rationale,
            )
        print(json.dumps({
            "status": "RECORDED",
            "event": event.to_dict(),
            "store_id": store.store_id,
            "generation": store.generation,
        }, indent=2), file=output)
        return 0
    except (OSError, ValueError, TrustStoreError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=errors)
        return 2


__all__ = ["run_trust_store_cli"]

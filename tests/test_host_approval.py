from dataclasses import replace
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import tempfile
import unittest

from qyrenith_engine.approval import (
    HostApprovalError,
    approve_host_request,
    create_host_approval_request,
    validate_host_approval,
)
from qyrenith_engine.trust_store import OwnerTrustStore


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


class HostApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = OwnerTrustStore.open(
            Path(self.temporary.name) / "owner" / "trust-store.json",
            create=True,
        )
        self.scope = {
            "route_plan_digest": "a" * 64,
            "baseline_snapshot_digest": "b" * 64,
            "worker_manifest_digest": "c" * 64,
            "worker_qualification_digest": "d" * 64,
            "permissions": ["READ_PROJECT", "WRITE_PROJECT"],
            "limits": {"timeout_seconds": 60, "max_output_bytes": 4096},
            "target_workspace": "workspace-123",
        }

    def approve(self, request, *, answer=None, now=None):
        challenge = (
            f"APPROVE {request.action_type} {request.request_id} {request.nonce}"
            if answer is None else answer
        )
        output = FakeTTY()
        approval = approve_host_request(
            request, self.store, input_stream=FakeTTY(challenge + "\n"),
            output_stream=output, now=now,
        )
        return approval, output.getvalue()

    def test_exact_scope_approval_round_trips_and_verifies(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request(
            "MIGRATION_STEP", self.scope, lifetime_seconds=300, now=now
        )
        approval, output = self.approve(request, now=now)
        self.assertIn("QYRENITH HOST ACTION APPROVAL", output)
        restored = type(approval).from_json_bytes(approval.to_json_bytes())
        self.assertEqual(restored, approval)
        self.assertIsNone(validate_host_approval(
            restored, "MIGRATION_STEP", self.scope, self.store,
            now=now + timedelta(seconds=1),
        ))

    def test_scope_or_action_substitution_is_rejected(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request("MIGRATION_STEP", self.scope, now=now)
        approval, _ = self.approve(request, now=now)
        changed_scope = dict(self.scope, target_workspace="different-workspace")
        with self.assertRaisesRegex(HostApprovalError, "exact action scope"):
            validate_host_approval(
                approval, "MIGRATION_STEP", changed_scope, self.store,
                now=now + timedelta(seconds=1),
            )
        with self.assertRaisesRegex(HostApprovalError, "exact action scope"):
            validate_host_approval(
                approval, "QDAS_REPAIR", self.scope, self.store,
                now=now + timedelta(seconds=1),
            )

    def test_invalid_signature_is_rejected(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request("QDAS_REPAIR", self.scope, now=now)
        approval, _ = self.approve(request, now=now)
        forged = replace(approval, signature="0" * 64)
        with self.assertRaisesRegex(HostApprovalError, "signature is invalid"):
            validate_host_approval(
                forged, "QDAS_REPAIR", self.scope, self.store,
                now=now + timedelta(seconds=1),
            )

    def test_nonce_is_consumed_atomically_and_replay_is_rejected(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request("MIGRATION_STEP", self.scope, now=now)
        approval, _ = self.approve(request, now=now)
        self.assertIsNone(validate_host_approval(
            approval, "MIGRATION_STEP", self.scope, self.store,
            now=now + timedelta(seconds=1), consume=True,
        ))
        with self.assertRaisesRegex(HostApprovalError, "already been consumed"):
            validate_host_approval(
                approval, "MIGRATION_STEP", self.scope, self.store,
                now=now + timedelta(seconds=2), consume=True,
            )

    def test_expired_approval_is_rejected(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request(
            "MIGRATION_STEP", self.scope, lifetime_seconds=30, now=now
        )
        approval, _ = self.approve(request, now=now)
        with self.assertRaisesRegex(HostApprovalError, "not currently valid"):
            validate_host_approval(
                approval, "MIGRATION_STEP", self.scope, self.store,
                now=now + timedelta(seconds=31),
            )

    def test_wrong_challenge_is_rejected(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request("MIGRATION_STEP", self.scope, now=now)
        with self.assertRaisesRegex(HostApprovalError, "not confirmed"):
            self.approve(request, answer="APPROVE WRONG WRONG", now=now)

    def test_noninteractive_host_cannot_issue_approval(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request("MIGRATION_STEP", self.scope, now=now)
        with self.assertRaisesRegex(HostApprovalError, "interactive terminal"):
            approve_host_request(
                request, self.store, input_stream=io.StringIO(""),
                output_stream=io.StringIO(), now=now,
            )

    def test_future_approval_time_is_rejected(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        request = create_host_approval_request("MIGRATION_STEP", self.scope, now=now)
        approval, _ = self.approve(request, now=now)
        with self.assertRaisesRegex(HostApprovalError, "not currently valid"):
            validate_host_approval(
                approval, "MIGRATION_STEP", self.scope, self.store,
                now=now - timedelta(seconds=1),
            )


if __name__ == "__main__":
    unittest.main()

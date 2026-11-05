import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from qyrenith_engine.trust_store import (
    OwnerTrustStore,
    TrustStoreError,
)


NOW = datetime.now(timezone.utc).replace(microsecond=0)
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


class OwnerTrustStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "owner" / "trust-store.json"

    def test_initializes_private_store_and_reopens_with_same_identity(self):
        store = OwnerTrustStore.open(self.path, create=True)
        reopened = OwnerTrustStore.open(self.path)
        self.assertEqual(store.store_id, reopened.store_id)
        self.assertEqual(store.generation, 0)
        self.assertEqual(reopened.decisions(), ())
        if os.name != "nt":
            self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.path.with_name(self.path.name + ".key").stat().st_mode & 0o777, 0o600)

    def test_exact_digest_trust_expiry_and_revocation(self):
        store = OwnerTrustStore.open(self.path, create=True)
        expiry = NOW + timedelta(hours=1)
        store.trust(
            "WORKER_MANIFEST", DIGEST_A, reviewed_by="local-owner",
            reviewed_at=NOW, expires_at=expiry, rationale="Reviewed fixture worker",
        )
        self.assertTrue(store.is_trusted("WORKER_MANIFEST", DIGEST_A, now=NOW))
        self.assertFalse(store.is_trusted("WORKER_MANIFEST", DIGEST_B, now=NOW))
        self.assertFalse(
            store.is_trusted("WORKER_MANIFEST", DIGEST_A, now=expiry)
        )
        store.revoke(
            "WORKER_MANIFEST", DIGEST_A, reviewed_by="local-owner",
            reviewed_at=expiry, rationale="Worker was withdrawn",
        )
        self.assertFalse(store.is_trusted("WORKER_MANIFEST", DIGEST_A, now=expiry))
        self.assertEqual(store.generation, 2)

    def test_newer_trust_decision_can_explicitly_restore_revoked_digest(self):
        store = OwnerTrustStore.open(self.path, create=True)
        store.trust(
            "KNOWLEDGE_CATALOG", DIGEST_A, reviewed_by="owner",
            reviewed_at=NOW, rationale="Initial review",
        )
        store.revoke(
            "KNOWLEDGE_CATALOG", DIGEST_A, reviewed_by="owner",
            reviewed_at=NOW + timedelta(seconds=1), rationale="Conflicting evidence",
        )
        store.trust(
            "KNOWLEDGE_CATALOG", DIGEST_A, reviewed_by="owner",
            reviewed_at=NOW + timedelta(seconds=2), rationale="Re-reviewed and accepted",
        )
        self.assertTrue(
            store.is_trusted("KNOWLEDGE_CATALOG", DIGEST_A, now=NOW + timedelta(seconds=3))
        )

    def test_existing_instance_observes_external_revocation(self):
        first = OwnerTrustStore.open(self.path, create=True)
        second = OwnerTrustStore.open(self.path)
        first.trust(
            "WORKER_QUALIFICATION", DIGEST_A, reviewed_by="owner",
            reviewed_at=NOW, rationale="Reviewed qualification",
        )
        self.assertTrue(first.is_trusted("WORKER_QUALIFICATION", DIGEST_A, now=NOW))
        second.revoke(
            "WORKER_QUALIFICATION", DIGEST_A, reviewed_by="owner",
            reviewed_at=NOW + timedelta(seconds=1), rationale="Qualification withdrawn",
        )
        self.assertFalse(
            first.is_trusted(
                "WORKER_QUALIFICATION", DIGEST_A, now=NOW + timedelta(seconds=2)
            )
        )

    def test_tampered_store_fails_integrity_verification(self):
        store = OwnerTrustStore.open(self.path, create=True)
        store.trust(
            "EXECUTION_POLICY", DIGEST_A, reviewed_by="owner",
            reviewed_at=NOW, rationale="Reviewed policy",
        )
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["events"][0]["rationale"] = "silently changed"
        self.path.write_text(
            json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(TrustStoreError, "integrity verification"):
            OwnerTrustStore.open(self.path)

    def test_missing_integrity_key_fails_closed(self):
        OwnerTrustStore.open(self.path, create=True)
        self.path.with_name(self.path.name + ".key").unlink()
        with self.assertRaisesRegex(TrustStoreError, "must exist together"):
            OwnerTrustStore.open(self.path, create=True)

    def test_orphaned_key_fails_closed(self):
        OwnerTrustStore.open(self.path, create=True)
        self.path.unlink()
        with self.assertRaisesRegex(TrustStoreError, "must exist together"):
            OwnerTrustStore.open(self.path, create=True)

    def test_rejects_invalid_digest_and_unknown_subject_kind(self):
        store = OwnerTrustStore.open(self.path, create=True)
        with self.assertRaisesRegex(ValueError, "subject_digest"):
            store.trust(
                "WORKER_MANIFEST", "not-a-digest", reviewed_by="owner",
                reviewed_at=NOW, rationale="Invalid fixture",
            )
        with self.assertRaisesRegex(ValueError, "subject kind"):
            store.trust(
                "PROJECT", DIGEST_A, reviewed_by="owner",
                reviewed_at=NOW, rationale="Invalid fixture",
            )

    def test_rejects_expiry_before_review(self):
        store = OwnerTrustStore.open(self.path, create=True)
        with self.assertRaisesRegex(ValueError, "expiry must follow"):
            store.trust(
                "WORKER_MANIFEST", DIGEST_A, reviewed_by="owner",
                reviewed_at=NOW, expires_at=NOW, rationale="Invalid expiry",
            )

    def test_rejects_store_inside_git_worktree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repository"
            root.mkdir()
            (root / ".git").mkdir()
            with self.assertRaisesRegex(TrustStoreError, "inside a Git worktree"):
                OwnerTrustStore.open(root / ".qyrenith" / "trust-store.json", create=True)

    def test_rejects_symbolic_link_store_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real.json"
            alias = Path(temporary) / "alias.json"
            OwnerTrustStore.open(real, create=True)
            try:
                alias.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symbolic-link creation is unavailable")
            with self.assertRaisesRegex(TrustStoreError, "symbolic link"):
                OwnerTrustStore.open(alias)

    def test_rejects_duplicate_json_keys(self):
        OwnerTrustStore.open(self.path, create=True)
        self.path.write_text(
            '{"schema":1,"schema":1,"store_id":"00000000000000000000000000000000",'
            '"generation":0,"events":[],"hmac_sha256":"x"}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(TrustStoreError, "strict UTF-8 JSON"):
            OwnerTrustStore.open(self.path)


if __name__ == "__main__":
    unittest.main()

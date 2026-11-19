import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from qyrenith_engine.trust_cli import run_trust_store_cli
from qyrenith_engine.trust_store import OwnerTrustStore


DIGEST = "sha256:" + "d" * 64


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


def args(action, **values):
    defaults = {
        "trust_action": action,
        "trust_kind": "WORKER_MANIFEST",
        "digest": DIGEST,
        "reason": "Reviewed fixture worker",
        "expires_at": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


class TrustStoreCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "owner" / "trust-store.json"

    def test_init_and_list_are_readable_without_mutation_challenge(self):
        output = io.StringIO()
        errors = io.StringIO()
        result = run_trust_store_cli(
            args("init"), output_stream=output, error_stream=errors, path=str(self.path)
        )
        self.assertEqual(result, 0, errors.getvalue())
        self.assertIn("INITIALIZED", output.getvalue())

        output = io.StringIO()
        result = run_trust_store_cli(
            args("list"), output_stream=output, error_stream=errors, path=str(self.path)
        )
        self.assertEqual(result, 0, errors.getvalue())
        self.assertIn('"generation": 0', output.getvalue())

    def test_trust_requires_interactive_terminal(self):
        OwnerTrustStore.open(self.path, create=True)
        errors = io.StringIO()
        result = run_trust_store_cli(
            args("trust"), input_stream=io.StringIO(""),
            output_stream=io.StringIO(), error_stream=errors, path=str(self.path),
        )
        self.assertEqual(result, 2)
        self.assertIn("interactive terminal", errors.getvalue())
        self.assertEqual(OwnerTrustStore.open(self.path).decisions(), ())

    def test_exact_challenge_records_owner_trust(self):
        OwnerTrustStore.open(self.path, create=True)
        output = FakeTTY()
        errors = FakeTTY()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expiry = now + timedelta(days=1)
        expected = f"TRUST WORKER_MANIFEST {DIGEST} abcdef0123456789abcdef01\n"
        with mock.patch("qyrenith_engine.trust_cli.secrets.token_hex", return_value="abcdef0123456789abcdef01"):
            result = run_trust_store_cli(
                args("trust", expires_at=expiry.isoformat().replace("+00:00", "Z")),
                input_stream=FakeTTY(expected), output_stream=output,
                error_stream=errors, path=str(self.path),
            )
        self.assertEqual(result, 0, errors.getvalue())
        self.assertIn("RECORDED", output.getvalue())
        store = OwnerTrustStore.open(self.path)
        self.assertTrue(store.is_trusted("WORKER_MANIFEST", DIGEST, now=datetime.now(timezone.utc) + timedelta(seconds=1)))

    def test_wrong_challenge_does_not_change_store(self):
        store = OwnerTrustStore.open(self.path, create=True)
        output = FakeTTY()
        errors = FakeTTY()
        expected = f"TRUST WORKER_MANIFEST {DIGEST} abcdef0123456789abcdef01\n"
        with mock.patch("qyrenith_engine.trust_cli.secrets.token_hex", return_value="abcdef0123456789abcdef01"):
            result = run_trust_store_cli(
                args("trust"), input_stream=FakeTTY("TRUST WRONG\n"),
                output_stream=output, error_stream=errors, path=str(self.path),
            )
        self.assertEqual(result, 3)
        self.assertEqual(store.decisions(), ())
        self.assertIn("CANCELLED", errors.getvalue())

    def test_revoke_requires_exact_challenge_and_blocks_digest(self):
        store = OwnerTrustStore.open(self.path, create=True)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        store.trust(
            "WORKER_MANIFEST", DIGEST, reviewed_by="test-owner",
            reviewed_at=now, rationale="Initial test trust",
        )
        output = FakeTTY()
        errors = FakeTTY()
        challenge = "fedcba9876543210fedcba98"
        expected = f"REVOKE WORKER_MANIFEST {DIGEST} {challenge}\n"
        with mock.patch("qyrenith_engine.trust_cli.secrets.token_hex", return_value=challenge):
            result = run_trust_store_cli(
                args("revoke"), input_stream=FakeTTY(expected),
                output_stream=output, error_stream=errors, path=str(self.path),
            )
        self.assertEqual(result, 0, errors.getvalue())
        self.assertFalse(
            OwnerTrustStore.open(self.path).is_trusted(
                "WORKER_MANIFEST", DIGEST, now=datetime.now(timezone.utc)
            )
        )

    def test_revoke_rejects_expiry_argument(self):
        output = FakeTTY()
        errors = io.StringIO()
        result = run_trust_store_cli(
            args("revoke", expires_at="2026-12-01T00:00:00Z"),
            input_stream=FakeTTY(""), output_stream=output,
            error_stream=errors, path=str(self.path),
        )
        self.assertEqual(result, 2)
        self.assertIn("valid only for trust", errors.getvalue())


if __name__ == "__main__":
    unittest.main()

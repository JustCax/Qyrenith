"""Verify that the QDAS integrity gate is mandatory in the full self-test."""
import importlib.util
import io
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qyrenith_qdas_self_verification_test", ROOT / "qyrenith.py")
QYRENITH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QYRENITH)


class QdasSelfVerificationTests(unittest.TestCase):
    def _common_patches(self, calls):
        return (
            patch.object(QYRENITH, "run_full_tests", return_value=0),
            patch.object(QYRENITH, "cmd_security_test", side_effect=lambda args: calls.append("security") or 0),
            patch.object(QYRENITH, "cmd_recovery_test", side_effect=lambda args: calls.append("recovery") or 0),
            patch.object(QYRENITH, "cmd_git_test", side_effect=lambda args: calls.append("git") or 0),
            patch.object(QYRENITH, "cmd_fuzz_test", side_effect=lambda args: calls.append("fuzz") or 0),
            patch.object(QYRENITH, "cmd_benchmark", side_effect=lambda args: calls.append("benchmark") or 0),
        )

    def test_self_test_fails_closed_when_qdas_ledger_verification_fails(self):
        calls = []
        with ExitStack() as stack:
            for item in self._common_patches(calls):
                stack.enter_context(item)
            stack.enter_context(patch.object(
                QYRENITH, "cmd_qdas",
                side_effect=lambda args: calls.append(("qdas", args.extra)) or 2,
            ))
            public_audit = stack.enter_context(patch.object(QYRENITH, "public_audit"))
            with redirect_stdout(io.StringIO()):
                result = QYRENITH.self_test()
        self.assertEqual(result, 1)
        self.assertEqual(calls[-1], ("qdas", ["verify"]))
        public_audit.assert_not_called()

    def test_self_test_runs_public_audit_only_after_qdas_verification(self):
        calls = []
        with ExitStack() as stack:
            for item in self._common_patches(calls):
                stack.enter_context(item)
            stack.enter_context(patch.object(
                QYRENITH, "cmd_qdas",
                side_effect=lambda args: calls.append(("qdas", args.extra)) or 0,
            ))
            stack.enter_context(patch.object(
                QYRENITH, "public_audit",
                side_effect=lambda root: calls.append("public_audit") or {"status": "PASS"},
            ))
            with redirect_stdout(io.StringIO()):
                result = QYRENITH.self_test()
        self.assertEqual(result, 0)
        self.assertEqual(calls[-2:], [("qdas", ["verify"]), "public_audit"])


if __name__ == "__main__":
    unittest.main()

"""The --allow-missing-adapters opt-in for verify --ci.

By default `verify --ci` stays fail-closed: any detected-but-unavailable
adapter blocks. With --allow-missing-adapters such an adapter is downgraded to
SKIPPED_UNAVAILABLE and listed in skipped_adapters, never quietly dropped.
Zero available adapters must never become PASS (the vacuous-success guard).
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_allow_missing", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)


class TestAllowMissingAdapters(unittest.TestCase):
    """Review Focus item 1: zero capability must never read as verified,
    but a missing optional adapter must not block when opted out."""

    def _available_adapter_ids(self, root: Path):
        return {a["id"] for a in qyrenith.detect_generic_verification(root)["adapters"]}

    def test_default_ci_blocks_on_detected_but_unavailable_adapter(self):
        """This project has python-tests (not available without pytest) alongside
        available adapters. Default verify --ci must BLOCK on it."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            (root / "tests").mkdir()
            (root / "tests" / "test_placeholder.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n", encoding="utf-8")  # declares python-tests adapter; passes
            report = qyrenith.generic_verify(root, execute=True,
                                             allow_missing_adapters=False)
            # python-tests is declared but unavailable here (no pytest).
            unavailable = [a for a in report["adapters"]
                           if a["id"] == "python-tests"]
            self.assertTrue(unavailable, "precondition: this tree lacks pytest")
            self.assertEqual(report["status"], "BLOCKED",
                             "default ci must block on unavailable adapter")

    def test_opt_in_downgrades_unavailable_adapter_to_informational(self):
        """With --allow-missing-adapters the unavailable adapter becomes
        SKIPPED_UNAVAILABLE, appears in skipped_adapters, and does not block."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            (root / "tests").mkdir()
            (root / "tests" / "test_placeholder.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n", encoding="utf-8")
            report = qyrenith.generic_verify(root, execute=True,
                                             allow_missing_adapters=True)
            statuses = {a["id"]: a["status"] for a in report["adapters"]}
            self.assertEqual(statuses.get("python-tests"), "SKIPPED_UNAVAILABLE")
            self.assertIn("python-tests", report.get("skipped_adapters", []))
            # An available adapter still executes for real.
            self.assertIn("python-compile", statuses)
            self.assertIn(statuses["python-compile"], ("PASS", "FAIL"))

    def test_opt_in_zero_available_adapters_is_still_not_a_pass(self):
        """Vacuous-success guard: even with the flag, if nothing can run, it is
        NOT_AVAILABLE, never PASS."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            # Force zero adapters by removing every marker.
            for p in root.iterdir():
                if p.is_file():
                    p.unlink()
            report = qyrenith.generic_verify(root, execute=True,
                                             allow_missing_adapters=True)
            self.assertEqual(report["status"], "NOT_AVAILABLE")
            self.assertEqual(report["adapters"], [])
            self.assertEqual(report["skipped_adapters"], [])


if __name__ == "__main__":
    unittest.main()

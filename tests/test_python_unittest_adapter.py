"""Python/unittest verification adapter: real execution, standard library only.

``detect_generic_verification`` only offered a ``python-tests`` adapter that
requires an external ``pytest`` install. The standard library ships a real test
runner (``python -m unittest discover``), and this repository's own suite is
unittest-based, so a project with a ``tests/`` directory previously reported
``NOT_AVAILABLE`` even though its tests are runnable.

These tests pin the adapter's presence, availability and real execution.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_dom", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)


def make_python_project(root: Path):
    (root / "src").mkdir()
    (root / "src" / "mod.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_mod.py").write_text(
        "import unittest\nfrom src.mod import add\n\n\n"
        "class TestAdd(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n",
        encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    (root / ".qyrenith").mkdir()


class TestPythonUnittestAdapter(unittest.TestCase):
    def test_unittest_adapter_is_detected_for_python_project_with_tests(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_python_project(root)
            detection = qyrenith.detect_generic_verification(root)
            ids = {a["id"] for a in detection["adapters"]}
            self.assertIn("python-unittest", ids)

    def test_unittest_adapter_is_available_without_pytest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_python_project(root)
            detection = qyrenith.detect_generic_verification(root)
            adapter = next(a for a in detection["adapters"] if a["id"] == "python-unittest")
            # Standard library only: availability must not depend on an
            # external pytest install.
            self.assertTrue(adapter["available"])
            self.assertEqual(adapter["kind"], "test")
            self.assertEqual(
                adapter["command"],
                [qyrenith.sys.executable, "-m", "unittest", "discover", "-s", "tests"])

    def test_unittest_adapter_not_offered_without_test_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
            (root / ".qyrenith").mkdir()
            detection = qyrenith.detect_generic_verification(root)
            ids = {a["id"] for a in detection["adapters"]}
            self.assertNotIn("python-unittest", ids)

    def test_generic_verify_executes_unittest_adapter(self):
        """The adapter must actually run and pass — not merely be declared."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_python_project(root)
            report = qyrenith.generic_verify(root, execute=True)
            unittest_results = [
                a for a in report["adapters"] if a["id"] == "python-unittest"]
            self.assertTrue(unittest_results, "python-unittest is present")
            result = unittest_results[0]
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["exit_code"], 0)
            # The test genuinely ran (not a vacuous zero-exit "no tests").
            self.assertIn("Ran 1 test", result["output"])

    def test_failing_unittest_is_not_mistaken_for_success(self):
        """A verification gate must actually catch a failing test."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests").mkdir()
            (root / "tests" / "test_bad.py").write_text(
                "import unittest\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_broken(self):\n"
                "        self.assertEqual(1, 2)\n",
                encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
            (root / ".qyrenith").mkdir()
            report = qyrenith.generic_verify(root, execute=True)
            self.assertEqual(report["status"], "FAIL")
            result = next(
                a for a in report["adapters"] if a["id"] == "python-unittest")
            self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

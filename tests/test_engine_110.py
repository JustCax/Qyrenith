"""Regression tests for the additive Qyrenith engineering engine."""
import sys
import tempfile
import unittest
from pathlib import Path

from qyrenith_engine import (
    analyze_project, build_change_impact, compare_baselines,
    inspect_project_boundary, run_bounded_process,
)


class TestStaticAnalysis(unittest.TestCase):
    def test_analysis_extracts_imports_symbols_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "module.py").write_text("import json\nclass Example:\n    def run(self): pass\n", encoding="utf-8")
            report = analyze_project(root)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["files"][0]["imports"], ["json"])
            self.assertEqual([item["name"] for item in report["files"][0]["symbols"]], ["Example", "run"])
            self.assertFalse(report["execution_performed"])

    def test_syntax_error_is_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            self.assertEqual(analyze_project(root)["status"], "FAIL")

    def test_dynamic_execution_is_review_finding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "review.py").write_text("eval('1 + 1')\n", encoding="utf-8")
            report = analyze_project(root)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["files"][0]["findings"][0]["code"], "PY001")

    def test_file_limit_blocks_instead_of_truncating_as_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("pass\n", encoding="utf-8")
            (root / "b.py").write_text("pass\n", encoding="utf-8")
            self.assertEqual(analyze_project(root, max_files=1)["status"], "BLOCKED")

    def test_baseline_delta_and_syntax_regression(self):
        old = {"files": [{"path": "a.py", "sha256": "old", "syntax": "PASS"}]}
        new = {"files": [{"path": "a.py", "sha256": "new", "syntax": "FAIL"},
                          {"path": "b.py", "sha256": "b", "syntax": "PASS"}]}
        report = compare_baselines(old, new)
        self.assertEqual(report["changed"], ["a.py"])
        self.assertEqual(report["added"], ["b.py"])
        self.assertEqual(report["syntax_regressions"], ["a.py"])
        self.assertEqual(report["status"], "FAIL")

    def test_transitive_import_impact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "middle.py").write_text("import base\n", encoding="utf-8")
            (root / "top.py").write_text("import middle\n", encoding="utf-8")
            report = build_change_impact(root, ["base.py"])
            self.assertEqual(report["affected"], ["middle.py", "top.py"])

    def test_dotted_import_impact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "base.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "consumer.py").write_text("import package.base\n", encoding="utf-8")
            report = build_change_impact(root, ["package/base.py"])
            self.assertEqual(report["affected"], ["consumer.py"])


class TestBoundaryAndExecution(unittest.TestCase):
    def test_boundary_detects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            try:
                (root / "escape").symlink_to(Path(outside), target_is_directory=True)
            except OSError as exc:
                self.skipTest("symlink creation is unavailable: %s" % exc)
            report = inspect_project_boundary(root)
            self.assertEqual(report["status"], "REVIEW_REQUIRED")
            self.assertEqual(report["findings"][0]["code"], "FS001")

    def test_bounded_execution_success(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run_bounded_process([sys.executable, "-c", "print('ok')"], directory)
            self.assertEqual(report["status"], "PASS")
            self.assertFalse(report["shell"])

    def test_bounded_execution_rejects_unapproved_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_bounded_process([sys.executable, "-c", "pass"], directory,
                                    env_overrides={"PYTHONPATH": "untrusted"})

    def test_bounded_execution_timeout_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run_bounded_process([sys.executable, "-c", "import time; time.sleep(2)"],
                                         directory, timeout=1)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(report["timed_out"])


if __name__ == "__main__":
    unittest.main()

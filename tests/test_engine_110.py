"""Regression tests for the additive Qyrenith engineering engine."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from qyrenith_engine import (
    analyze_project, build_change_impact, compare_baselines,
    inspect_project_boundary, run_bounded_process, run_bounded_worker,
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

    def test_entry_limit_blocks_instead_of_returning_partial_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.txt").write_text("one", encoding="utf-8")
            (root / "two.txt").write_text("two", encoding="utf-8")
            report = analyze_project(root, max_entries=1)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["reason"], "max_entries limit exceeded")

    def test_symlinked_source_directory_blocks_incomplete_inventory(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (Path(outside) / "hidden.py").write_text("pass\\n", encoding="utf-8")
            try:
                (root / "external").symlink_to(Path(outside), target_is_directory=True)
            except OSError as exc:
                self.skipTest("symlink creation is unavailable: %s" % exc)
            report = analyze_project(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["skipped"][0]["reason"], "symlink_directory")

    def test_file_limit_blocks_instead_of_truncating_as_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("pass\n", encoding="utf-8")
            (root / "b.py").write_text("pass\n", encoding="utf-8")
            self.assertEqual(analyze_project(root, max_files=1)["status"], "BLOCKED")

    def test_baseline_delta_and_syntax_regression(self):
        old = {"schema": 1, "files": [{"path": "a.py", "sha256": "old", "syntax": "PASS"}]}
        new = {"schema": 1, "files": [{"path": "a.py", "sha256": "new", "syntax": "FAIL"},
                                      {"path": "b.py", "sha256": "b", "syntax": "PASS"}]}
        report = compare_baselines(old, new)
        self.assertEqual(report["changed"], ["a.py"])
        self.assertEqual(report["added"], ["b.py"])
        self.assertEqual(report["syntax_regressions"], ["a.py"])
        self.assertEqual(report["status"], "FAIL")

    def test_baseline_rejects_duplicate_or_incomplete_records(self):
        duplicate = {"schema": 1, "files": [
            {"path": "a.py", "sha256": "a", "syntax": "PASS"},
            {"path": "a.py", "sha256": "b", "syntax": "PASS"}]}
        valid = {"schema": 1, "files": []}
        self.assertEqual(compare_baselines(duplicate, valid)["status"], "UNKNOWN")

    def test_baseline_reports_new_syntax_failures(self):
        old = {"schema": 1, "status": "PASS", "files": []}
        new = {"schema": 1, "status": "FAIL", "files": [
            {"path": "new.py", "sha256": "x", "syntax": "FAIL"}]}
        report = compare_baselines(old, new)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["current_syntax_failures"], ["new.py"])

    def test_empty_impact_input_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "module.py").write_text("pass\\n", encoding="utf-8")
            self.assertEqual(build_change_impact(root, [])["status"], "UNKNOWN")

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

    def test_impact_rejects_parent_traversal_instead_of_normalizing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.py").write_text("VALUE = 1\n", encoding="utf-8")
            report = build_change_impact(root, ["../base.py"])
            self.assertEqual(report["status"], "UNKNOWN")
            self.assertEqual(report["invalid_paths"], ["../base.py"])


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

    @unittest.skipIf(os.name == "nt", "POSIX process-group semantics are not available on Windows")
    def test_bounded_execution_timeout_terminates_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "descendant-survived.txt"
            child = "import time; time.sleep(2); open(%r, 'w').write('alive')" % str(marker)
            parent = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', %r]); time.sleep(30)" % child
            report = run_bounded_process([sys.executable, "-c", parent], directory, timeout=1)
            self.assertEqual(report["status"], "BLOCKED")
            time.sleep(2.2)
            self.assertFalse(marker.exists(), "a child process survived the bounded execution timeout")

    def test_bounded_execution_enforces_output_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run_bounded_process(
                [sys.executable, "-c", "import sys; sys.stdout.write('x' * 1000000)"],
                directory, output_limit=256)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(report["output_truncated"])
            self.assertLessEqual(len(report["output"].encode("utf-8")), 256)


    def test_bounded_worker_times_out_when_child_does_not_read_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run_bounded_worker(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                directory,
                b"x" * (1024 * 1024),
                timeout=1,
            )
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(report["timed_out"])
            self.assertTrue(report["input_incomplete"])
            self.assertLess(report["duration_seconds"], 6)

    def test_bounded_worker_kills_output_flood_before_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            script = "import sys\nwhile True:\n sys.stdout.write('x' * 65536)\n sys.stdout.flush()\n"
            report = run_bounded_worker(
                [sys.executable, "-c", script],
                directory,
                b"{}\\n",
                timeout=30,
                output_limit=256,
            )
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(report["output_limited"])
            self.assertFalse(report["timed_out"])
            self.assertLess(report["duration_seconds"], 10)

    def test_bounded_worker_keeps_stdout_and_stderr_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            script = "import sys; sys.stdin.read(); print('protocol'); print('diagnostic', file=sys.stderr)"
            report = run_bounded_worker(
                [sys.executable, "-c", script], directory, b"request\\n", timeout=5
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["stdout"], "protocol\\n")
            self.assertEqual(report["stderr"], "diagnostic\\n")
            self.assertFalse(report["input_incomplete"])



if __name__ == "__main__":
    unittest.main()

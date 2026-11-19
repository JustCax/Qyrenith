from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qyrenith_engine.analysis import analyze_project, build_change_impact, compare_baselines


class StaticAnalysisTests(unittest.TestCase):
    def test_analyzes_source_without_importing_or_executing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "executed.txt"
            (root / "sample.py").write_text(
                "import os\n"
                "def inspect_value():\n"
                "    Path('executed.txt').write_text('bad')\n"
                "    eval('1')\n",
                encoding="utf-8",
            )
            report = analyze_project(root)
            self.assertEqual(report["status"], "PASS")
            self.assertFalse(report["execution_performed"])
            self.assertFalse(marker.exists())
            record = report["files"][0]
            self.assertEqual(record["syntax"], "PASS")
            self.assertIn("os", record["imports"])
            self.assertIn("inspect_value", [item["name"] for item in record["symbols"]])
            self.assertEqual(record["findings"][0]["code"], "PY001")

    def test_syntax_error_is_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "broken.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
            report = analyze_project(directory)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["syntax_failures"], 1)
            self.assertEqual(report["files"][0]["syntax"], "FAIL")

    def test_invalid_utf8_is_blocked_without_decoding_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "invalid.py").write_bytes(b"\xff\xfe")
            report = analyze_project(directory)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["unknown_files"], 1)
            self.assertEqual(report["files"][0]["syntax"], "UNKNOWN")

    def test_file_size_limit_is_reported_as_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "large.py").write_text("x = 12345\n", encoding="utf-8")
            report = analyze_project(directory, max_file_bytes=2)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["skipped"][0]["reason"], "file_size_limit")

    def test_file_count_limit_is_reported_as_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("a = 1\n", encoding="utf-8")
            (root / "b.py").write_text("b = 2\n", encoding="utf-8")
            report = analyze_project(root, max_files=1)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["files_seen"], 1)

    def test_entry_count_limit_is_reported_as_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("a = 1\n", encoding="utf-8")
            (root / "b.txt").write_text("data\n", encoding="utf-8")
            report = analyze_project(root, max_entries=1)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["entries_seen"], 1)

    def test_all_analysis_limits_require_positive_non_boolean_integers(self):
        invalid_values = (0, -1, True, 1.5, None, "10")
        with tempfile.TemporaryDirectory() as directory:
            for field in ("max_files", "max_file_bytes", "max_entries"):
                for value in invalid_values:
                    with self.subTest(field=field, value=value):
                        with self.assertRaises(ValueError):
                            analyze_project(directory, **{field: value})

    def test_symlinked_python_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.py"
            link = root / "linked.py"
            target.write_text("value = 1\n", encoding="utf-8")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this platform")
            report = analyze_project(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn(
                {"path": "linked.py", "reason": "symlink"},
                report["skipped"],
            )

    def test_compare_baselines_reports_syntax_regression(self):
        previous = {
            "schema": 1,
            "status": "PASS",
            "files": [{"path": "a.py", "sha256": "a" * 64, "syntax": "PASS"}],
        }
        current = {
            "schema": 1,
            "status": "FAIL",
            "files": [{"path": "a.py", "sha256": "b" * 64, "syntax": "FAIL"}],
        }
        report = compare_baselines(previous, current)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["syntax_regressions"], ["a.py"])

    def test_compare_baselines_rejects_duplicate_paths(self):
        baseline = {
            "schema": 1,
            "status": "PASS",
            "files": [
                {"path": "a.py", "sha256": "a" * 64, "syntax": "PASS"},
                {"path": "a.py", "sha256": "b" * 64, "syntax": "PASS"},
            ],
        }
        report = compare_baselines(baseline, baseline)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIn("duplicate paths", report["reason"])

    def test_compare_baselines_rejects_invalid_sha256(self):
        baseline = {
            "schema": 1,
            "status": "PASS",
            "files": [{"path": "a.py", "sha256": "not-a-digest", "syntax": "PASS"}],
        }
        report = compare_baselines(baseline, baseline)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIn("incomplete evidence", report["reason"])

    def test_compare_baselines_rejects_unsafe_paths(self):
        baseline = {
            "schema": 1,
            "status": "PASS",
            "files": [{"path": "../outside.py", "sha256": "a" * 64, "syntax": "PASS"}],
        }
        report = compare_baselines(baseline, baseline)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIn("unsafe file path", report["reason"])

    def test_compare_baselines_rejects_unknown_report_status(self):
        for raw_status in ("MYSTERY", ["PASS"], None):
            with self.subTest(raw_status=raw_status):
                baseline = {
                    "schema": 1,
                    "status": raw_status,
                    "files": [{"path": "a.py", "sha256": "a" * 64, "syntax": "PASS"}],
                }
                report = compare_baselines(baseline, baseline)
                self.assertEqual(report["status"], "UNKNOWN")
                self.assertIn("unsupported schema", report["reason"])

    def test_compare_baselines_rejects_non_string_syntax_status(self):
        baseline = {
            "schema": 1,
            "status": "PASS",
            "files": [{"path": "a.py", "sha256": "a" * 64, "syntax": ["PASS"]}],
        }
        report = compare_baselines(baseline, baseline)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIn("incomplete evidence", report["reason"])

    def test_change_impact_returns_transitive_importers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "b.py").write_text("import a\n", encoding="utf-8")
            (root / "c.py").write_text("import b\n", encoding="utf-8")
            report = build_change_impact(root, ["a.py"])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["direct_dependents"], ["b.py"])
            self.assertEqual(report["affected"], ["b.py", "c.py"])

    def test_change_impact_rejects_traversal_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            report = build_change_impact(directory, ["../outside.py"])
            self.assertEqual(report["status"], "UNKNOWN")
            self.assertEqual(report["invalid_paths"], ["../outside.py"])


if __name__ == "__main__":
    unittest.main()

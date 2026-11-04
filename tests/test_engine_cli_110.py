"""CLI contract tests for Qyrenith's additive engineering commands."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestEngineeringCLI(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run([sys.executable, str(ROOT / "qyrenith.py"), *arguments],
                              cwd=ROOT, capture_output=True, text=True, check=False)

    def test_help_lists_new_commands(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("source-analysis", "impact", "boundary-check", "bounded-check", "snapshot"):
            self.assertIn(command, result.stdout)

    def test_source_analysis_cli_emits_json(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "hello.py").write_text("print('hello')\n", encoding="utf-8")
            result = self.run_cli("source-analysis", "--project", directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "PASS")

    def test_empty_source_inventory_is_not_a_success_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("source-analysis", "--project", directory)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "UNKNOWN")

    def test_snapshot_capture_cli_emits_canonical_json_without_project_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("print('hello')\\n", encoding="utf-8")
            result = self.run_cli("snapshot", "capture", "--project", directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(result.stdout)
            self.assertEqual(document["schema"], 1)
            self.assertEqual(document["entries"][0]["path"], "main.py")
            self.assertFalse((root / ".qyrenith").exists())

    def test_snapshot_verify_cli_reports_match_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "main.py"
            source.write_text("before\\n", encoding="utf-8")
            captured = self.run_cli("snapshot", "capture", "--project", directory)
            self.assertEqual(captured.returncode, 0, captured.stderr)
            snapshot_file = root.parent / (root.name + ".snapshot.json")
            try:
                snapshot_file.write_text(captured.stdout, encoding="utf-8")
                matched = self.run_cli(
                    "snapshot", "verify", "--project", directory,
                    "--snapshot-file", str(snapshot_file),
                )
                self.assertEqual(matched.returncode, 0, matched.stderr)
                self.assertEqual(json.loads(matched.stdout)["status"], "MATCH")
                source.write_text("after\\n", encoding="utf-8")
                changed = self.run_cli(
                    "snapshot", "verify", "--project", directory,
                    "--snapshot-file", str(snapshot_file),
                )
                self.assertEqual(changed.returncode, 1, changed.stderr)
                report = json.loads(changed.stdout)
                self.assertEqual(report["status"], "CHANGED")
                self.assertIn("main.py", report["changed_paths"])
            finally:
                snapshot_file.unlink(missing_ok=True)

    def test_snapshot_custom_exclusion_preserves_default_exclusions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("ignored", encoding="utf-8")
            (root / "generated").mkdir()
            (root / "generated" / "bundle.bin").write_bytes(b"ignored")
            (root / "main.py").write_text("pass\\n", encoding="utf-8")
            result = self.run_cli(
                "snapshot", "capture", "--project", directory,
                "--snapshot-exclude", "generated",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(result.stdout)
            self.assertEqual([item["path"] for item in document["entries"]], ["main.py"])
            self.assertEqual(
                document["excluded_paths"],
                [".backups", ".git", ".qyrenith", "__pycache__", "generated"],
            )

    def test_snapshot_verify_requires_snapshot_file(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("snapshot", "verify", "--project", directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires --snapshot-file", result.stderr)

    def test_impact_cli_requires_changed_path(self):
        result = self.run_cli("impact", "--project", str(ROOT))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("impact requires", result.stderr)

    def test_source_analysis_cli_rejects_invalid_limits_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("source-analysis", "--project", directory, "--max-files", "0")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)

    def test_bounded_cli_rejects_invalid_output_limit_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli(
                "bounded-check", "--project", directory,
                "--check-command-one", "python -c pass", "--output-limit", "1")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)

    def test_bounded_cli_requires_explicit_command(self):
        result = self.run_cli("bounded-check", "--project", str(ROOT))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires an explicit", result.stderr)


if __name__ == "__main__":
    unittest.main()

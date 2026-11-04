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
        for command in ("source-analysis", "impact", "boundary-check", "bounded-check"):
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

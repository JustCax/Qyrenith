import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_external", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)

class TestExternalReadOnlyCheck(unittest.TestCase):
    def test_checks_external_project_without_qyrenith_or_state_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "external-project"
            root.mkdir()
            (root / "settings.gradle.kts").write_text("rootProject.name = \"demo\"\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "main.java").write_text("class Main {}\n", encoding="utf-8")
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            report = qyrenith.external_project_check(str(root))
            after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            self.assertEqual(report["mode"], "external_read_only_check")
            self.assertTrue(report["read_only"])
            self.assertTrue(report["target_modified"] is False)
            self.assertIn("gradle", report["build_systems"])
            self.assertNotIn("qyrenith.py", after)
            self.assertNotIn(".qyrenith", after)
            self.assertEqual(before, after)

    def test_cli_external_check_outputs_json_for_project_without_qyrenith(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "package.json").write_text('{"scripts":{"test":"echo test"}}\n', encoding="utf-8")
            # Exercise the command handler directly; it must not require Qyrenith in target.
            out = io.StringIO()
            with redirect_stdout(out):
                rc = qyrenith.cmd_external_check(type("Args", (), {"project": str(root)})())
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertTrue(data["read_only"])
            self.assertIn("node", data["build_systems"])


    def test_external_verify_runs_only_explicit_command_without_qyrenith_dependency(self):
        import sys
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = io.StringIO()
            args = type("Args", (), {
                "project": str(root), "check_command": [f'{sys.executable} -c "print(\'external-ok\')"'],
                "execute": True, "timeout": 10,
            })()
            with redirect_stdout(out):
                rc = qyrenith.cmd_external_verify(args)
            data = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(data["overall_status"], "PASS")
            self.assertIn("external-ok", data["results"][0]["output"])
            self.assertFalse((root / "qyrenith.py").exists())
            self.assertFalse((root / ".qyrenith").exists())

    def test_external_verify_windows_quoting_keeps_paths_intact(self):
        import sys
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = io.StringIO()
            args = type("Args", (), {
                "project": str(root),
                "check_command": [f'{sys.executable} -c "import sys; print(sys.argv[1])" "hello world"'],
                "execute": True, "timeout": 10,
            })()
            with redirect_stdout(out):
                rc = qyrenith.cmd_external_verify(args)
            data = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(data["overall_status"], "PASS")
            # The executable path must survive splitting byte-identical
            # (on Windows it contains backslashes; posix-style splitting
            # would eat them).
            self.assertEqual(data["results"][0]["command"][0], sys.executable)
            self.assertIn("hello world", data["results"][0]["output"])

    def test_external_verify_failing_command_stays_fail(self):
        import sys
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = io.StringIO()
            args = type("Args", (), {
                "project": str(root),
                "check_command": [f'{sys.executable} -c "import sys; sys.exit(3)"'],
                "execute": True, "timeout": 10,
            })()
            with redirect_stdout(out):
                rc = qyrenith.cmd_external_verify(args)
            data = json.loads(out.getvalue())
            self.assertEqual(rc, 1)
            self.assertEqual(data["overall_status"], "FAIL")
            self.assertEqual(data["results"][0]["exit_code"], 3)

    def test_external_verify_does_not_execute_without_opt_in(self):
        import sys
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = io.StringIO()
            args = type("Args", (), {
                "project": str(root), "check_command": [f'{sys.executable} -c "raise SystemExit(7)"'],
                "execute": False, "timeout": 10,
            })()
            with redirect_stdout(out):
                rc = qyrenith.cmd_external_verify(args)
            data = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(data["mode"], "external_verify_plan_only")
            self.assertFalse(data["commands_executed"] if "commands_executed" in data else False)

class TestExternalTurboChecks(unittest.TestCase):
    def _run_check(self, root):
        before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
        report = qyrenith.external_project_check(str(root))
        after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
        self.assertEqual(before, after, "external check must not modify the target")
        return report

    def test_secret_detected_with_path_and_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config.py").write_text('api_key = "123456789abcdef"\n', encoding="utf-8")
            report = self._run_check(root)
            secrets = [f for f in report["findings"] if f["code"] == "POSSIBLE_SECRET"]
            self.assertEqual(len(secrets), 1)
            self.assertEqual(secrets[0]["path"], "config.py")
            self.assertEqual(secrets[0]["line"], 1)
            self.assertEqual(secrets[0]["severity"], "HIGH")

    def test_placeholder_secret_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config.py").write_text('api_key = "REPLACE_ME"\n', encoding="utf-8")
            report = self._run_check(root)
            self.assertEqual([f for f in report["findings"] if f["code"] == "POSSIBLE_SECRET"], [])

    def test_private_key_is_critical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "deploy_key.pem").write_text("-----BEGIN RSA PRIVATE KEY-----\nAAAA\n", encoding="utf-8")
            report = self._run_check(root)
            keys = [f for f in report["findings"] if f["code"] == "PRIVATE_KEY_MATERIAL"]
            self.assertEqual(len(keys), 1)
            self.assertEqual(keys[0]["severity"], "CRITICAL")

    def test_dangerous_command_pattern_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "setup.sh").write_text("curl https://example.invalid/x.sh | sh\n", encoding="utf-8")
            report = self._run_check(root)
            cmds = [f for f in report["findings"] if f["code"] == "DANGEROUS_OR_NETWORK_COMMAND_PATTERN"]
            self.assertEqual(len(cmds), 1)
            self.assertEqual(cmds[0]["severity"], "HIGH")

    def test_residue_markers_aggregated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("# TODO one\n# TODO two\n# FIXME three\n", encoding="utf-8")
            report = self._run_check(root)
            self.assertEqual(report["residue_summary"].get("TODO"), 2)
            self.assertEqual(report["residue_summary"].get("FIXME"), 1)
            residue = [f for f in report["findings"] if f["code"] == "RESIDUE_MARKER"]
            self.assertEqual(len(residue), 3)

    def test_hygiene_on_empty_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = self._run_check(root)
            codes = {f["code"] for f in report["findings"]}
            self.assertIn("NO_LICENSE_FILE", codes)
            self.assertIn("NO_README", codes)
            self.assertIn("NO_CI_CONFIG", codes)
            self.assertFalse(report["hygiene"]["license_present"])
            self.assertFalse(report["hygiene"]["ci_systems"])

    def test_manifest_lists_files_with_sizes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("12345", encoding="utf-8")
            report = self._run_check(root)
            manifest = dict(report["file_manifest"])
            self.assertEqual(manifest.get("a.txt"), 5)

    def test_binary_file_skipped_safely(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "blob.bin").write_bytes(b"\x00\x01\x02api_key = \"123456789abcdef\"")
            report = self._run_check(root)
            self.assertEqual([f for f in report["findings"] if f["path"] == "blob.bin"], [])

    def test_baseline_diff_reports_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "keep.txt").write_text("same", encoding="utf-8")
            (root / "gone.txt").write_text("bye", encoding="utf-8")
            old = qyrenith.external_project_check(str(root))
            (root / "gone.txt").unlink()
            (root / "new.txt").write_text("hi", encoding="utf-8")
            (root / "keep.txt").write_text("same but longer", encoding="utf-8")
            new = qyrenith.external_project_check(str(root))
            diff = qyrenith.external_baseline_diff(old, new)
            self.assertTrue(diff["baseline_compared"])
            self.assertIn("new.txt", diff["added"]["items"])
            self.assertIn("gone.txt", diff["removed"]["items"])
            self.assertIn("keep.txt", diff["modified_size_changed"]["items"])

    def test_baseline_flag_on_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("x", encoding="utf-8")
            old = qyrenith.external_project_check(str(root))
            baseline_file = root / "baseline.json"
            baseline_file.write_text(json.dumps(old), encoding="utf-8")
            (root / "b.txt").write_text("y", encoding="utf-8")
            out = io.StringIO()
            args = type("Args", (), {"project": str(root), "baseline": str(baseline_file)})()
            with redirect_stdout(out):
                rc = qyrenith.cmd_external_check(args)
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertTrue(data["baseline_diff"]["baseline_compared"])
            self.assertIn("b.txt", data["baseline_diff"]["added"]["items"])

    def test_baseline_loader_tolerates_utf16(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("x", encoding="utf-8")
            old = qyrenith.external_project_check(str(root))
            baseline_file = root / "baseline.json"
            baseline_file.write_text(json.dumps(old), encoding="utf-16")
            loaded = qyrenith._load_baseline_report(str(baseline_file))
            self.assertEqual(loaded["mode"], "external_read_only_check")
            self.assertIn("file_manifest", loaded)


if __name__ == "__main__":
    unittest.main()

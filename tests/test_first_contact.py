"""Non-Minecraft quickstart: a plain Python project, no AI agent.

A visitor with a plain Python project (no Minecraft, no Gradle, no AI agent)
must be able to install, run doctor/verify/audit/explain, and understand the
result without reading any Minecraft material.
"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_first_contact", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)


def cli(cmd: str, cwd: Path, *extra):
    args = [sys.executable, str(ROOT / "qyrenith.py"), cmd, "--project", "."]
    return subprocess.run(args + list(extra), cwd=str(cwd), capture_output=True,
                          text=True, timeout=300)


class TestNonMinecraftQuickstart(unittest.TestCase):
    """A plain Python project must be verifiable without Minecraft knowledge."""

    def _python_project(self, root: Path):
        (root / "src").mkdir()
        (root / "src" / "mod.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests" / "test_mod.py").write_text(
            "import unittest\nfrom src.mod import add\n\n\n"
            "class TestAdd(unittest.TestCase):\n"
            "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n",
            encoding="utf-8")
        (root / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")

    def test_doctor_reports_usable_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._python_project(root)
            (root / "qyrenith.py").write_text(Path(ROOT / "qyrenith.py").read_text(encoding="utf-8"), encoding="utf-8")
            p = cli("doctor", root)
            text = p.stdout + p.stderr
            self.assertEqual(p.returncode, 0)
            self.assertIn("READY", text)

    def test_verify_discovers_python_adapters(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._python_project(root)
            (root / "qyrenith.py").write_text(Path(ROOT / "qyrenith.py").read_text(encoding="utf-8"), encoding="utf-8")
            p = cli("verify", root)
            text = p.stdout + p.stderr
            self.assertEqual(p.returncode, 0)
            self.assertIn("python-compile", text)

    def test_domain_is_not_minecraft(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._python_project(root)
            detection = qyrenith.detect_domain(root, "")
            self.assertNotEqual(detection["domain"], "minecraft")

    def test_explain_returns_exit_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._python_project(root)
            (root / "qyrenith.py").write_text(Path(ROOT / "qyrenith.py").read_text(encoding="utf-8"), encoding="utf-8")
            p = cli("explain", root, "UNKNOWN_API")
            self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()

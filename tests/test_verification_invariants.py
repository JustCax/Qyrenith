"""Invariant tests: adapter contamination, fail-closed state, and error routing.

Every test here names the defect it pins, so a future change that reintroduces it
fails the suite.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_invariants", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)

CONTROL_FILES = {"qyrenith.py", "qyrenith_launcher.py"}


def bare_python_project(root: Path):
    (root / "mod.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_mod.py").write_text(
        "import unittest\nfrom mod import add\n\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n",
        encoding="utf-8")


def cli(cmd: str, cwd: Path, *extra):
    args = [sys.executable, str(ROOT / "qyrenith.py"), cmd, "--project", "."]
    return subprocess.run(args + list(extra), cwd=str(cwd), capture_output=True,
                          text=True, timeout=300)


class TestCommandSurface(unittest.TestCase):
    """The command surface must stay routable and singly routed."""

    def _parsers_and_dispatch(self):
        import ast
        src = (ROOT / "qyrenith.py").read_text(encoding="utf-8")
        parser_cmds = set()
        for action in qyrenith.parser()._actions:
            if action.dest == "command":
                parser_cmds = set(action.choices)
        tree = ast.parse(src)
        dispatch, pre = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Dict):
                        for k in sub.keys:
                            if isinstance(k, ast.Constant):
                                dispatch.add(k.value)
                    if (isinstance(sub, ast.Compare) and isinstance(sub.left, ast.Attribute)
                            and sub.left.attr == "command"):
                        for c in sub.comparators:
                            if isinstance(c, ast.Constant):
                                pre.add(c.value)
        return parser_cmds, dispatch, pre

    def test_every_declared_command_is_routable(self):
        parser_cmds, dispatch, pre = self._parsers_and_dispatch()
        self.assertTrue(parser_cmds, "parser must declare commands")
        self.assertEqual(parser_cmds, dispatch | pre,
                         "every command must be reachable via dispatch dict or pre-block")

    def test_no_command_is_routed_twice(self):
        _, dispatch, pre = self._parsers_and_dispatch()
        self.assertEqual(dispatch & pre, set(),
                         "a command routed twice has one dead route")


class TestAdapterContamination(unittest.TestCase):
    """The control file alone must never make a project 'Python'.

    Previously `verify --execute` in such a directory ran `compileall` on the
    control file itself and reported a vacuous PASS.
    """

    def _adapters(self, root: Path):
        return {a["id"] for a in qyrenith.detect_generic_verification(root)["adapters"]}

    def test_control_file_alone_is_not_a_python_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            self.assertNotIn("python-compile", self._adapters(root))

    def test_control_file_with_readme_is_not_a_python_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            self.assertNotIn("python-compile", self._adapters(root))

    def test_minecraft_tree_is_not_a_python_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            (root / "build.gradle").write_text("plugins {}\n", encoding="utf-8")
            (root / "gradle.properties").write_text("minecraft_version=1.20.1\n", encoding="utf-8")
            self.assertNotIn("python-compile", self._adapters(root))

    def test_genuine_python_project_is_still_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")
            self.assertIn("python-compile", self._adapters(root))

    def test_python_project_detected_by_packaging_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            (root / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
            self.assertIn("python-compile", self._adapters(root))

    def test_python_project_detected_by_src_layout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            self.assertIn("python-compile", self._adapters(root))

    def test_no_adapters_and_no_execution_is_not_a_pass(self):
        """Zero capability must never read as verified."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            report = qyrenith.generic_verify(root, execute=True)
            self.assertNotEqual(report["status"], "PASS")
            self.assertEqual(report["status"], "NOT_AVAILABLE")
            self.assertEqual(report["adapters"], [])


class TestFailClosedStateDirectory(unittest.TestCase):
    """An unusable state directory must fail closed."""

    def test_state_path_occupied_by_a_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# fixture\n", encoding="utf-8")
            (root / ".qyrenith").write_text("not a directory\n", encoding="utf-8")
            with self.assertRaises(qyrenith.QyrenithError) as ctx:
                qyrenith.load_state(root)
            self.assertEqual(ctx.exception.code, "PREFLIGHT_FAILURE")

    def test_unwritable_state_directory_fails_closed(self):
        """An OSError while creating the state dir must become a fail-closed error.

        Tested by injection rather than ``chmod``: on Windows a read-only bit on a
        directory does not stop an elevated process, so a permission-based test
        would silently pass without exercising the path.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# fixture\n", encoding="utf-8")
            real_mkdir = Path.mkdir

            def denying_mkdir(self, *a, **k):
                raise PermissionError(13, "Permission denied")

            Path.mkdir = denying_mkdir
            try:
                with self.assertRaises(qyrenith.QyrenithError) as ctx:
                    qyrenith.ensure_state_dir(root)
            finally:
                Path.mkdir = real_mkdir
            self.assertEqual(ctx.exception.code, "PREFLIGHT_FAILURE")
            self.assertIn("state directory", ctx.exception.message.lower())


class TestMinecraftCommandsOnNonMinecraftProject(unittest.TestCase):
    """A non-Minecraft project must get an actionable error,
    never a Minecraft-flavoured one."""

    def _tree(self, root: Path):
        (root / "qyrenith.py").write_text("# fixture\n", encoding="utf-8")
        bare_python_project(root)

    def _first_stderr_line(self, p):
        return (p.stderr or p.stdout or "").strip().splitlines()[0:1]

    def test_dry_run_names_the_mismatch_and_points_at_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            p = cli("dry-run", root, "--target-mc", "1.21.1")
            text = p.stderr + p.stdout
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("verify", text.lower(),
                          "the error must point a non-Minecraft user at the generic path")
            self.assertNotIn("minecraft version or mod id", text.lower(),
                             "the error must not report a Minecraft identity problem")

    def test_build_does_not_name_a_minecraft_script_to_a_non_minecraft_user(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            p = cli("build", root)
            text = p.stderr + p.stdout
            self.assertNotEqual(p.returncode, 0)
            self.assertNotIn("minecraft-build", text,
                             "build must not name the Minecraft skill path for a non-Minecraft project")

    def test_port_states_the_project_shape_problem_first(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            p = cli("port", root, "--target-mc", "1.21.1", "--target-loader", "neoforge")
            text = p.stderr + p.stdout
            self.assertNotEqual(p.returncode, 0)
            self.assertNotIn("Target loader version is required", text,
                             "port must report the project-shape problem, not an argument problem")

    def test_minecraft_project_still_gets_the_specific_build_error(self):
        """The guard must not weaken the existing Minecraft message."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# fixture\n", encoding="utf-8")
            (root / "build.gradle").write_text("plugins {}\n", encoding="utf-8")
            (root / "gradle.properties").write_text("minecraft_version=1.20.1\nneoforge_version=21.0.167\n", encoding="utf-8")
            p = cli("build", root)
            text = p.stderr + p.stdout
            self.assertIn("minecraft-build", text)


if __name__ == "__main__":
    unittest.main()

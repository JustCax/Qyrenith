"""Node/JavaScript domain verification at L2.

Pins detection, real execution, failure detection, and the contamination
guard for the node-tests adapter. The adapter id stays `node-tests`; the
command is the Node built-in test runner, which executes cross-platform
without npm (the previous `["npm", "test"]` command cannot start under
shell=False on Windows, where npm is a .CMD script).
"""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_node_domain", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)

NODE = shutil.which("node")
needs_node = unittest.skipUnless(NODE, "node executable is required for this test")


def make_node_project(root: Path, failing: bool = False):
    (root / "package.json").write_text(
        '{"name":"demo","version":"1.0.0","scripts":{"test":"node --test"}}',
        encoding="utf-8")
    (root / "index.js").write_text(
        "function add(a, b) {\n  return a + b;\n}\n\nmodule.exports = { add };\n",
        encoding="utf-8")
    expected = "3" if failing else "2"
    (root / "index.test.js").write_text(
        "const { test } = require('node:test');\n"
        "const assert = require('node:assert');\n"
        "const { add } = require('./index.js');\n\n"
        "test('one plus one', () => {\n"
        f"  assert.strictEqual(add(1, 1), {expected});\n"
        "});\n",
        encoding="utf-8")
    (root / ".qyrenith").mkdir()


class TestNodeDomain(unittest.TestCase):
    def test_node_adapter_detected_with_real_availability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_node_project(root)
            detection = qyrenith.detect_generic_verification(root)
            adapter = next((a for a in detection["adapters"] if a["id"] == "node-tests"), None)
            self.assertIsNotNone(adapter, "node-tests adapter must be declared for a Node project")
            self.assertEqual(adapter["available"], NODE is not None)
            self.assertEqual(adapter["language"], "JavaScript/TypeScript/Node")
            self.assertEqual(adapter["kind"], "test")

    @needs_node
    def test_node_adapter_really_executes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_node_project(root)
            report = qyrenith.generic_verify(root, execute=True)
            result = next((a for a in report["adapters"] if a["id"] == "node-tests"), None)
            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["exit_code"], 0)
            # The test genuinely ran (not a vacuous zero-exit "no tests").
            self.assertIn("pass 1", result["output"])

    @needs_node
    def test_failing_node_test_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_node_project(root, failing=True)
            report = qyrenith.generic_verify(root, execute=True)
            self.assertEqual(report["status"], "FAIL")
            result = next(a for a in report["adapters"] if a["id"] == "node-tests")
            self.assertEqual(result["status"], "FAIL")

    def test_python_project_has_no_node_adapter(self):
        """Contamination guard: a Python-only project must not claim Node."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
            detection = qyrenith.detect_generic_verification(root)
            ids = {a["id"] for a in detection["adapters"]}
            self.assertNotIn("node-tests", ids)

    def test_control_file_alone_has_no_node_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            detection = qyrenith.detect_generic_verification(root)
            ids = {a["id"] for a in detection["adapters"]}
            self.assertNotIn("node-tests", ids)


if __name__ == "__main__":
    unittest.main()

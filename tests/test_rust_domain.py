"""Rust domain verification at L2.

Pins detection, real execution (`cargo check`), failure detection, and the
contamination guard for the rust-check adapter. The adapter id stays
`rust-check`; cargo resolves via PATH with a fallback to rustup's documented
default location (~/.cargo/bin), which is not always on PATH yet.
"""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_rust_domain", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)

CARGO_HOME_BIN = Path.home() / ".cargo" / "bin"
CARGO_EXE = CARGO_HOME_BIN / ("cargo.exe" if __import__("os").name == "nt" else "cargo")
HAS_CARGO = shutil.which("cargo") is not None or CARGO_EXE.is_file()
needs_cargo = unittest.skipUnless(HAS_CARGO, "cargo is required for this test")


def make_rust_project(root: Path, broken: bool = False):
    (root / "Cargo.toml").write_text(
        '[package]\nname = "demo"\nversion = "0.1.0"\nedition = "2021"\n',
        encoding="utf-8")
    (root / "src").mkdir()
    body = 'a + "x"' if broken else "a + b"
    (root / "src" / "lib.rs").write_text(
        f"pub fn add(a: i32, b: i32) -> i32 {{\n    {body}\n}}\n",
        encoding="utf-8")
    (root / ".qyrenith").mkdir()


class TestRustDomain(unittest.TestCase):
    def test_rust_adapter_detected_with_real_availability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_rust_project(root)
            detection = qyrenith.detect_generic_verification(root)
            adapter = next((a for a in detection["adapters"] if a["id"] == "rust-check"), None)
            self.assertIsNotNone(adapter, "rust-check adapter must be declared for a Rust project")
            self.assertEqual(adapter["available"], HAS_CARGO)
            self.assertEqual(adapter["language"], "Rust")
            self.assertEqual(adapter["kind"], "build-check")

    @needs_cargo
    def test_rust_adapter_really_executes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_rust_project(root)
            report = qyrenith.generic_verify(root, execute=True)
            result = next((a for a in report["adapters"] if a["id"] == "rust-check"), None)
            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["exit_code"], 0)

    @needs_cargo
    def test_broken_rust_code_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_rust_project(root, broken=True)
            report = qyrenith.generic_verify(root, execute=True)
            self.assertEqual(report["status"], "FAIL")
            result = next(a for a in report["adapters"] if a["id"] == "rust-check")
            self.assertEqual(result["status"], "FAIL")

    def test_python_project_has_no_rust_adapter(self):
        """Contamination guard: a Python-only project must not claim Rust."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
            detection = qyrenith.detect_generic_verification(root)
            ids = {a["id"] for a in detection["adapters"]}
            self.assertNotIn("rust-check", ids)

    def test_control_file_alone_has_no_rust_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "qyrenith.py").write_text("# placeholder\n", encoding="utf-8")
            detection = qyrenith.detect_generic_verification(root)
            ids = {a["id"] for a in detection["adapters"]}
            self.assertNotIn("rust-check", ids)


if __name__ == "__main__":
    unittest.main()

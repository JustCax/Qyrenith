"""Behaviour guard for the explicit project-map.json feature path.

``feature_inventory`` used to rebind its ``files`` parameter with a list of
strings, which would corrupt the single-walk file listing. This test pins the
explicit-declaration path (and the filesystem fallback) to correct behaviour.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_pm", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)


class TestExplicitProjectMap(unittest.TestCase):
    def test_explicit_features_win_over_filesystem_areas(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "F.java").write_text("public class F {}\n", encoding="utf-8")
            state = root / ".qyrenith"
            state.mkdir()
            (state / "project-map.json").write_text(
                '{"features":[{"name":"MyFoo","source_files":["src/F.java"],"status":"DECLARED"}]}',
                encoding="utf-8")
            features = qyrenith.feature_inventory(root, list(qyrenith.iter_project_files(root)))
            self.assertEqual([f["name"] for f in features], ["MyFoo"])
            self.assertEqual(features[0]["source"], "project-map.json")
            self.assertEqual(features[0]["source_files"], ["src/F.java"])

    def test_filesystem_fallback_uses_injected_listing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "A.java").write_text("public class A {}\n", encoding="utf-8")
            (root / ".qyrenith").mkdir()
            listing = list(qyrenith.iter_project_files(root))
            features = qyrenith.feature_inventory(root, listing)
            self.assertEqual(features[0]["source"], "filesystem")
            self.assertEqual(features[0]["source_files"], ["src/A.java"])

    def test_reality_map_keeps_explicit_features_with_single_walk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "F.java").write_text("public class F {}\n", encoding="utf-8")
            state = root / ".qyrenith"
            state.mkdir()
            (state / "project-map.json").write_text(
                '{"features":[{"name":"FeatureX","source_files":["src/F.java"]}]}', encoding="utf-8")
            calls = {"n": 0}
            real = qyrenith.iter_project_files

            def counting(r):
                calls["n"] += 1
                yield from real(r)

            qyrenith.iter_project_files = counting
            try:
                r = qyrenith.build_reality_map(root, qyrenith.initial_state(root), "bench")
            finally:
                qyrenith.iter_project_files = real
            self.assertEqual(calls["n"], 1)
            self.assertEqual(r["features"][0]["name"], "FeatureX")
            # The integrity check still resolves the declared file.
            self.assertEqual(r["feature_integrity"], [])


if __name__ == "__main__":
    unittest.main()

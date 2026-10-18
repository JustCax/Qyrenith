"""Performance tests for tree-walk pruning and the hashing cache.

These lock in two contracts:
1. ``iter_project_files`` must not descend into excluded directories
   (``.git``, ``node_modules``, ``build``, ``.qyrenith`` ...) — it must prune.
2. Hashing the same unchanged file within one process must happen once
   (per-key cache), while a real content change must still be detected.

The second group are guard tests for the ``SOURCE_CHANGE_DURING_BUILD``
invariant: the cache must never make a changed source look unchanged.
"""
import importlib.util
import os
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_perf", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)


def reference_files(root: Path):
    """Brute-force reference: every file not under an excluded directory."""
    root = root.resolve()
    out = []
    for p in root.rglob("*"):
        parts = p.relative_to(root).parts
        if any(part in qyrenith.EXCLUDES for part in parts):
            continue
        if p.is_symlink() or not p.is_file():
            continue
        out.append(p.relative_to(root).as_posix())
    return sorted(out)


class TestPrunedWalk(unittest.TestCase):
    def _tree(self, root: Path):
        (root / "src").mkdir()
        (root / "src" / "a.py").write_text("a", encoding="utf-8")
        (root / "src" / "b.txt").write_text("b", encoding="utf-8")
        (root / ".git").mkdir()
        (root / ".git" / "objects").mkdir()
        (root / ".git" / "objects" / "deadbeef").write_text("x", encoding="utf-8")
        (root / ".git" / "HEAD").write_text("ref", encoding="utf-8")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "f.js").write_text("x", encoding="utf-8")
        (root / "build").mkdir()
        (root / "build" / "out.jar").write_bytes(b"x")
        (root / ".qyrenith").mkdir()
        (root / ".qyrenith" / "state.json").write_text("{}", encoding="utf-8")

    def test_yields_only_non_excluded_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            got = sorted(p.relative_to(root).as_posix() for p in qyrenith.iter_project_files(root))
            self.assertEqual(got, reference_files(root))

    def test_does_not_scan_excluded_directories(self):
        # The walk must never list the contents of an excluded directory.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            scanned = []
            real_scandir = os.scandir

            def spy(path=".", *a, **k):
                scanned.append(os.fspath(path).replace("\\", "/"))
                return real_scandir(path, *a, **k)

            os.scandir = spy
            try:
                list(qyrenith.iter_project_files(root))
            finally:
                os.scandir = real_scandir
            joined = " ".join(scanned)
            self.assertNotIn(".git", joined)
            self.assertNotIn("node_modules", joined)
            self.assertNotIn("/build", joined)
            self.assertNotIn(".qyrenith", joined)

    def test_source_then_project_fingerprint_hashes_each_file_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            for i in range(5):
                (root / f"s{i}.py").write_text(f"value = {i}\n", encoding="utf-8")
            # Verify cache behavior: the cache should contain exactly 5 entries
            # after both fingerprint passes, meaning each file was hashed once.
            qyrenith._SHA256_CACHE.clear()
            qyrenith.source_fingerprint(root)
            after_first = len(qyrenith._SHA256_CACHE)
            qyrenith.project_fingerprint(root)
            after_second = len(qyrenith._SHA256_CACHE)
            self.assertEqual(after_first, 5, "first fingerprint should hash 5 files")
            self.assertEqual(after_second, 5, "second fingerprint should reuse cache, not add entries")


class TestSingleTreeTraversal(unittest.TestCase):
    """The reality map must traverse the project tree exactly once.

    ``build_reality_map`` previously ran six independent walks (fingerprints,
    file inventory, resources, security scan, baseline comparison, ...). Each walk
    costs a full ``scandir`` pass over the tree, which dominates on large projects.
    """

    def _tree(self, root: Path):
        (root / "src").mkdir()
        (root / "src" / "Feature.java").write_text("public class Feature {}\n", encoding="utf-8")
        (root / "src" / "Other.java").write_text("public class Other {}\n", encoding="utf-8")
        (root / ".qyrenith").mkdir()

    def test_build_reality_map_traverses_tree_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            calls = {"n": 0}
            real = qyrenith.iter_project_files

            def counting(r):
                calls["n"] += 1
                yield from real(r)

            qyrenith.iter_project_files = counting
            try:
                s = qyrenith.initial_state(root)
                qyrenith.build_reality_map(root, s, "bench")
            finally:
                qyrenith.iter_project_files = real
            self.assertEqual(calls["n"], 1, "reality map builds from a single tree walk")

    def test_reality_map_still_reports_every_file(self):
        """A single walk must not drop inventory entries."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            s = qyrenith.initial_state(root)
            r = qyrenith.build_reality_map(root, s, "bench")
            paths = {x["path"] for x in r["file_inventory"]}
            self.assertEqual(paths, {"src/Feature.java", "src/Other.java"})
            self.assertTrue(r["fingerprints"]["source"])
            self.assertTrue(r["fingerprints"]["project"])
            # A source-area feature is still derived from the same walk.
            self.assertTrue(r["features"], "features/source areas are still discovered")


class TestAuditHotPathWalk(unittest.TestCase):
    """The audit hot path must not descend into excluded directories."""

    def _tree(self, root: Path):
        (root / "src").mkdir()
        (root / "src" / "Feature.java").write_text(
            "public class Feature { DeferredRegister r; }\n", encoding="utf-8")
        (root / ".git").mkdir()
        (root / ".git" / "packed.java").write_text("DeferredRegister x;\n", encoding="utf-8")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "dep.java").write_text("EntityType x;\n", encoding="utf-8")
        (root / ".qyrenith").mkdir()

    def test_risk_scan_ignores_excluded_directories(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            scanned = []
            real_scandir = os.scandir

            def spy(path=".", *a, **k):
                scanned.append(os.fspath(path).replace("\\", "/"))
                return real_scandir(path, *a, **k)

            os.scandir = spy
            try:
                findings = qyrenith.risk_scan(root)
            finally:
                os.scandir = real_scandir
            joined = " ".join(scanned)
            self.assertNotIn(".git", joined)
            self.assertNotIn("node_modules", joined)
            paths = {f["file"] for f in findings}
            self.assertIn("src/Feature.java", paths)
            self.assertNotIn(".git/packed.java", paths)
            self.assertNotIn("node_modules/dep.java", paths)

    def test_audit_java_file_count_ignores_excluded_directories(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            counted = sum(
                1
                for p in qyrenith.iter_project_files(root)
                if p.suffix == ".java"
            )
            self.assertEqual(counted, 1)


    def test_iq_files_ignores_excluded_directories(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "Feature.java").write_text("public class F {}\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "packed.java").write_text("public class P {}\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "dep.java").write_text("public class D {}\n", encoding="utf-8")
            (root / ".qyrenith").mkdir()
            scanned = []
            real_scandir = os.scandir

            def spy(path=".", *a, **k):
                scanned.append(os.fspath(path).replace("\\", "/"))
                return real_scandir(path, *a, **k)

            os.scandir = spy
            try:
                files = qyrenith._iq_files(root, {".java"})
            finally:
                os.scandir = real_scandir
            joined = " ".join(scanned)
            self.assertNotIn(".git", joined)
            self.assertNotIn("node_modules", joined)
            paths = {p.relative_to(root).as_posix() for p in files}
            self.assertEqual(paths, {"src/Feature.java"})

    def test_public_audit_ignores_excluded_directories(self):
        """A forbidden token placed inside .git must not be seen or reported."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "Feature.java").write_text("public class F {}\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "packed.java").write_text(
                "# C:\\Users\\secret\npublic class P {}\n", encoding="utf-8")
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            (root / ".qyrenith").mkdir()
            scanned = []
            real_scandir = os.scandir

            def spy(path=".", *a, **k):
                scanned.append(os.fspath(path).replace("\\", "/"))
                return real_scandir(path, *a, **k)

            os.scandir = spy
            try:
                report = qyrenith.public_audit(root)
            finally:
                os.scandir = real_scandir
            joined = " ".join(scanned)
            self.assertNotIn(".git", joined, "excluded directory must not be scanned")
            self.assertGreater(report["files_scanned"], 0)
            # The planted token lives only in the excluded tree.
            self.assertEqual(report["forbidden_content"], [])
            self.assertTrue(
                any(x.endswith("RELEASE_NOTES") or x.endswith(".md")
                    for x in report["missing_required_docs"]),
                "bare fixture legitimately lacks required docs")


class TestHashCacheInvariant(unittest.TestCase):
    """The cache must never hide a real source change."""

    def test_fingerprint_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            f = root / "src.py"
            f.write_text("one", encoding="utf-8")
            before = qyrenith.project_fingerprint(root)
            time.sleep(0.02)
            f.write_text("two-longer", encoding="utf-8")
            after = qyrenith.project_fingerprint(root)
            self.assertNotEqual(before, after)

    def test_fingerprint_changes_when_same_size_content_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            f = root / "src.py"
            f.write_text("AAAA", encoding="utf-8")
            before = qyrenith.source_fingerprint(root)
            time.sleep(0.02)
            f.write_text("BBBB", encoding="utf-8")  # identical size
            after = qyrenith.source_fingerprint(root)
            self.assertNotEqual(before, after)

    def test_build_style_double_fingerprint_detects_mid_run_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            f = root / "src.py"
            f.write_text("before", encoding="utf-8")
            fp_before = qyrenith.project_fingerprint(root)
            time.sleep(0.02)
            f.write_text("after-build-mutation", encoding="utf-8")
            fp_after = qyrenith.project_fingerprint(root)
            self.assertNotEqual(fp_before, fp_after)


if __name__ == "__main__":
    unittest.main()
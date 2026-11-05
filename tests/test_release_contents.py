"""Verify public release archives and Python source distributions."""
import importlib.util
import subprocess
import sys
import tarfile
import tempfile
from unittest import mock
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def manifest_files():
    return {
        line.strip()
        for line in (ROOT / "PUBLIC_FILES.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


class TestReleaseContents(unittest.TestCase):
    def test_manifest_paths_are_present_and_safe(self):
        expected = manifest_files()
        self.assertIn("PUBLIC_FILES.txt", expected)
        self.assertIn("MANIFEST.in", expected)
        self.assertTrue(expected)
        for name in expected:
            path = ROOT / name
            self.assertFalse(Path(name).is_absolute())
            self.assertNotIn("..", Path(name).parts)
            self.assertTrue(path.is_file(), name)
            self.assertFalse(path.is_symlink(), name)

    def test_default_release_output_rejects_symlink(self):
        spec = importlib.util.spec_from_file_location(
            "qyrenith_release_script", ROOT / "scripts" / "release.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            module.ROOT = Path(directory)
            with mock.patch.object(Path, "is_symlink", autospec=True, return_value=True):
                with self.assertRaises(SystemExit):
                    module.resolve_output_dir(None)

    def test_setuptools_manifest_matches_public_file_list(self):
        expected = manifest_files()
        directives = {
            line.split(maxsplit=1)[1]
            for line in (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
            if line.startswith("include ")
        }
        self.assertEqual(directives, expected)

    def test_release_archives_contain_exactly_the_manifest(self):
        expected = manifest_files()
        version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        stem = "qyrenith-" + version
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/release.py"), str(output)],
                cwd=ROOT, check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + "\\n" + result.stderr)
            with zipfile.ZipFile(output / (stem + ".zip")) as archive:
                actual = {
                    name[len(stem) + 1:]
                    for name in archive.namelist()
                    if name.startswith(stem + "/") and not name.endswith("/")
                }
                self.assertEqual(actual, expected)
                for name in expected:
                    self.assertEqual(archive.read(stem + "/" + name), (ROOT / name).read_bytes())
                executable = archive.getinfo(stem + "/examples/example-neoforge-mod/gradlew")
                self.assertEqual((executable.external_attr >> 16) & 0o777, 0o755)
            with tarfile.open(output / (stem + ".tar.gz"), "r:gz") as archive:
                actual = {
                    member.name[len(stem) + 1:]
                    for member in archive.getmembers()
                    if member.isfile() and member.name.startswith(stem + "/")
                }
                self.assertEqual(actual, expected)
                for name in expected:
                    member = archive.getmember(stem + "/" + name)
                    self.assertEqual(archive.extractfile(member).read(), (ROOT / name).read_bytes())
                self.assertEqual(archive.getmember(stem + "/examples/example-neoforge-mod/gradlew").mode, 0o755)
            for suffix in (".zip.sha256", ".tar.gz.sha256"):
                checksum = (output / (stem + suffix)).read_text(encoding="utf-8")
                self.assertIn(stem, checksum)
                self.assertEqual(len(checksum.split()[0]), 64)

    @unittest.skipUnless(importlib.util.find_spec("setuptools"),
                         "setuptools is not installed; Python wheel build is not available")
    def test_wheel_contains_the_cli_and_native_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            output = Path(directory) / "dist"
            source.mkdir()
            output.mkdir()
            for name in manifest_files():
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            subprocess.run(
                [sys.executable, "-c",
                 "from setuptools.build_meta import build_wheel; import sys; build_wheel(sys.argv[1])",
                 str(output)],
                cwd=source, check=True, capture_output=True, text=True,
            )
            wheel_path = next(output.glob("*.whl"))
            with zipfile.ZipFile(wheel_path) as archive:
                names = set(archive.namelist())
            modules = {
                name for name in names
                if ".dist-info/" not in name and not name.endswith("/")
            }
            self.assertEqual(modules, {
                "qyrenith.py",
                "qyrenith_engine/__init__.py",
                "qyrenith_engine/approval.py",
                "qyrenith_engine/analysis.py",
                "qyrenith_engine/boundary.py",
                "qyrenith_engine/execution.py",
                "qyrenith_engine/trust_store.py",
                "qyrenith_engine/trust_cli.py",
                "qyrenith_engine/migration/__init__.py",
                "qyrenith_engine/qdas/__init__.py",
                "qyrenith_engine/qdas/events.py",
                "qyrenith_engine/qdas/collector.py",
                "qyrenith_engine/qdas/diagnosis.py",
                "qyrenith_engine/qdas/repair.py",
                "qyrenith_engine/qdas/ledger.py",
                "qyrenith_engine/qdas/lineage.py",
                "qyrenith_engine/migration/assurance.py",
                "qyrenith_engine/migration/authorization.py",
                "qyrenith_engine/migration/snapshot.py",
                "qyrenith_engine/migration/workspace.py",
                "qyrenith_engine/migration/preparation.py",
                "qyrenith_engine/migration/knowledge.py",
                "qyrenith_engine/migration/model.py",
                "qyrenith_engine/migration/planner.py",
                "qyrenith_engine/migration/worker.py",
            })
            entry_points = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
            with zipfile.ZipFile(wheel_path) as archive:
                self.assertIn("qyrenith = qyrenith:main", archive.read(entry_points).decode("utf-8"))

    @unittest.skipUnless(importlib.util.find_spec("setuptools"),
                         "setuptools is not installed; Python package build is not available")
    def test_python_source_distribution_respects_public_allowlist(self):
        expected = manifest_files()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            output = Path(directory) / "dist"
            source.mkdir()
            output.mkdir()
            for name in expected:
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            subprocess.run(
                [sys.executable, "-c",
                 "from setuptools.build_meta import build_sdist; import sys; build_sdist(sys.argv[1])",
                 str(output)],
                cwd=source, check=True, capture_output=True, text=True,
            )
            archive_path = next(output.glob("*.tar.gz"))
            with tarfile.open(archive_path, "r:gz") as archive:
                members = {
                    member.name.split("/", 1)[1]
                    for member in archive.getmembers()
                    if "/" in member.name and member.isfile()
                }
            self.assertTrue(expected.issubset(members))
            forbidden = {
                "AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONVENTIONS.md",
                "GITHUB_SETUP.md", "scripts/generate-client-entries.py", "tests/test_client_entrypoints.py",
                ".github/REPOSITORY_SETUP.md",
            }
            self.assertTrue(forbidden.isdisjoint(members))


if __name__ == "__main__":
    unittest.main()

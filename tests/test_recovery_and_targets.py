import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_recovery_targets", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)


def dead_pid():
    """Return a PID the controller's liveness probe classifies as dead.

    On POSIX a just-exited child is reported dead by ``os.kill(pid, 0)``. Some
    Windows builds never raise for a reaped PID, so fall back to an out-of-range
    PID that the probe reliably rejects. The helper proves exactly the branch the
    stale-lock recovery path depends on: a lock whose holder is not alive.
    """
    for _ in range(20):
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait()
        try:
            os.kill(proc.pid, 0)
        except (OSError, ProcessLookupError):
            return proc.pid
    for candidate in range(2_000_000_000, 1_999_999_000, -1):
        try:
            os.kill(candidate, 0)
        except (OSError, ProcessLookupError):
            return candidate
    return 2_000_000_000


class TestMultiversionJarDiscovery(unittest.TestCase):
    def test_finds_jar_in_versions_subdir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            libs = root / "versions" / "1.21.3" / "build" / "libs"
            libs.mkdir(parents=True)
            jar = libs / "mod-1.21.3.jar"
            jar.write_bytes(b"jar-bytes")
            found = qyrenith.newest_jar(root)
            self.assertIsNotNone(found)
            self.assertEqual(found.name, "mod-1.21.3.jar")

    def test_root_layout_still_wins_when_newer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root_libs = root / "build" / "libs"
            root_libs.mkdir(parents=True)
            ver_libs = root / "versions" / "9.9.9" / "build" / "libs"
            ver_libs.mkdir(parents=True)
            old = ver_libs / "old.jar"
            old.write_bytes(b"old")
            new = root_libs / "new.jar"
            new.write_bytes(b"newer-bytes!!")
            # Force mtimes: root jar is newer.
            os.utime(old, (1_000_000_000, 1_000_000_000))
            os.utime(new, (1_800_000_000, 1_800_000_000))
            self.assertEqual(qyrenith.newest_jar(root).name, "new.jar")

    def test_skips_sources_dev_and_empty(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            libs = root / "versions" / "1.21.3" / "build" / "libs"
            libs.mkdir(parents=True)
            (libs / "mod-sources.jar").write_bytes(b"x" * 10)
            (libs / "mod-dev.jar").write_bytes(b"x" * 10)
            (libs / "empty.jar").write_bytes(b"")
            self.assertIsNone(qyrenith.newest_jar(root))

    def test_configured_artifact_path_is_used(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            custom = root / "custom-out"
            custom.mkdir()
            (custom / "mod.jar").write_bytes(b"custom-bytes")
            state = root / ".qyrenith"
            state.mkdir()
            (state / "artifact-paths.json").write_text(json.dumps(["custom-out"]), encoding="utf-8")
            found = qyrenith.newest_jar(root)
            self.assertIsNotNone(found)
            self.assertEqual(found.name, "mod.jar")

    def test_configured_path_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outside = Path(td) / "outside"
            outside.mkdir()
            (outside / "evil.jar").write_bytes(b"evil-bytes!!")
            state = root / ".qyrenith"
            state.mkdir()
            (state / "artifact-paths.json").write_text(json.dumps(["../outside"]), encoding="utf-8")
            self.assertIsNone(qyrenith.newest_jar(root))


class TestStaleSameRunLock(unittest.TestCase):
    def test_dead_pid_same_run_lock_is_recoverable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            lock = root / ".qyrenith" / "run.lock"
            lock.write_text(json.dumps({"run_id": "run-1", "pid": dead_pid()}), encoding="utf-8")
            # Must not raise: the holder is dead, so the same run may resume.
            qyrenith.acquire_lock(root, "run-1")
            payload = json.loads(lock.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "run-1")
            self.assertEqual(payload["pid"], os.getpid())

    def test_live_other_run_still_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            lock = root / ".qyrenith" / "run.lock"
            lock.write_text(json.dumps({"run_id": "other-run", "pid": os.getpid()}),
                            encoding="utf-8")
            with self.assertRaises(qyrenith.MDocError):
                qyrenith.acquire_lock(root, "my-run")


class TestPortMatrixTargetReached(unittest.TestCase):
    def _port_tree(self, root):
        port = root / "port" / "neoforge-1.21.3"
        port.mkdir(parents=True)
        (port / "gradle.properties").write_text(
            "minecraft_version=1.21.3\nneoForge_version=21.3.97\n", encoding="utf-8")
        (root / "gradle.properties").write_text(
            "minecraft_version=1.21.1\nneoForge_version=21.1.233\n", encoding="utf-8")

    def test_port_dir_satisfies_step_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._port_tree(root)
            audit = {"target_loader": "neoforge"}
            self.assertTrue(qyrenith.step_target_reached(root, ["1.21.1", "1.21.3"], audit))

    def test_wrong_loader_does_not_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._port_tree(root)
            audit = {"target_loader": "forge"}
            self.assertFalse(qyrenith.step_target_reached(root, ["1.21.1", "1.21.3"], audit))

    def test_root_match_still_works_without_ports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "gradle.properties").write_text("minecraft_version=1.21.3\n",
                                                   encoding="utf-8")
            self.assertTrue(qyrenith.step_target_reached(root, ["1.21.1", "1.21.3"], {}))

    def test_nothing_matches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "gradle.properties").write_text("minecraft_version=1.21.1\n",
                                                   encoding="utf-8")
            self.assertFalse(qyrenith.step_target_reached(root, ["1.21.1", "1.21.3"], {}))


if __name__ == "__main__":
    unittest.main()

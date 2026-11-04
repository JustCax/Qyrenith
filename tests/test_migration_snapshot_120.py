"""Regression tests for deterministic, bounded project snapshots."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from qyrenith_engine.migration.snapshot import (
    ProjectSnapshot,
    SnapshotEntry,
    SnapshotError,
    SnapshotLimits,
    capture_project_snapshot,
    deserialize_project_snapshot,
    serialize_project_snapshot,
    verify_project_snapshot,
)


class TestProjectSnapshot(unittest.TestCase):
    def test_snapshot_digest_is_deterministic_and_excludes_capture_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text("print('hello')\n", encoding="utf-8")
            first = capture_project_snapshot(root)
            second = capture_project_snapshot(root)
            self.assertEqual(first.snapshot_digest, second.snapshot_digest)
            self.assertNotEqual(first.captured_at, second.captured_at)

    def test_snapshot_tracks_content_paths_modes_and_empty_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "empty").mkdir()
            source = root / "source.py"
            source.write_text("before", encoding="utf-8")
            first = capture_project_snapshot(root)
            source.write_text("after!", encoding="utf-8")
            second = capture_project_snapshot(root)
            self.assertNotEqual(first.snapshot_digest, second.snapshot_digest)
            entries = {item.path: item for item in first.entries}
            self.assertEqual(entries["empty"].kind, "directory")
            self.assertEqual(entries["source.py"].kind, "file")
            self.assertEqual(entries["source.py"].size, 6)

    def test_default_exclusions_omit_repository_and_runtime_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("private", encoding="utf-8")
            (root / ".qyrenith").mkdir()
            (root / "__pycache__").mkdir()
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("pass\n", encoding="utf-8")
            snapshot = capture_project_snapshot(root)
            self.assertEqual([item.path for item in snapshot.entries], ["src", "src/main.py"])
            self.assertEqual(snapshot.excluded_paths, (".backups", ".git", ".qyrenith", "__pycache__"))

    def test_custom_exclusions_are_bound_into_snapshot_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generated").mkdir()
            (root / "generated" / "output.bin").write_bytes(b"data")
            default = capture_project_snapshot(root)
            excluded = capture_project_snapshot(root, excluded_paths=("generated",))
            self.assertNotEqual(default.snapshot_digest, excluded.snapshot_digest)
            self.assertEqual(excluded.entries, ())

    def test_verification_detects_content_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "module.py"
            path.write_text("one", encoding="utf-8")
            snapshot = capture_project_snapshot(root)
            path.write_text("two", encoding="utf-8")
            result = verify_project_snapshot(root, snapshot)
            self.assertEqual(result.status, "CHANGED")
            self.assertFalse(result.matches)
            self.assertIn("module.py", result.changed_paths)

    def test_verification_detects_added_and_removed_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "old.txt").write_text("old", encoding="utf-8")
            snapshot = capture_project_snapshot(root)
            (root / "old.txt").unlink()
            (root / "new.txt").write_text("new", encoding="utf-8")
            result = verify_project_snapshot(root, snapshot)
            self.assertEqual(result.changed_paths, ("new.txt", "old.txt"))

    def test_verification_matches_unchanged_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("pass\n", encoding="utf-8")
            snapshot = capture_project_snapshot(root)
            result = verify_project_snapshot(root, snapshot)
            self.assertTrue(result.matches)
            self.assertEqual(result.status, "MATCH")
            self.assertEqual(result.expected_digest, result.actual_digest)

    def test_symlink_is_recorded_without_following_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = Path(directory).parent / (Path(directory).name + "-external")
            external.mkdir()
            (external / "secret.txt").write_text("not part of project", encoding="utf-8")
            try:
                os.symlink(str(external), root / "external-link", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this platform")
            try:
                snapshot = capture_project_snapshot(root)
                self.assertEqual(len(snapshot.entries), 1)
                link = snapshot.entries[0]
                self.assertEqual(link.kind, "symlink")
                self.assertEqual(link.path, "external-link")
                self.assertEqual(link.link_target, str(external))
            finally:
                (root / "external-link").unlink(missing_ok=True)
                (external / "secret.txt").unlink(missing_ok=True)
                external.rmdir()

    def test_root_must_not_be_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            target = Path(directory) / "target"
            target.mkdir()
            try:
                os.symlink(target, root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this platform")
            with self.assertRaisesRegex(SnapshotError, "real directory"):
                capture_project_snapshot(root)

    def test_special_files_are_rejected(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO is unavailable on this platform")
        with tempfile.TemporaryDirectory() as directory:
            os.mkfifo(Path(directory) / "pipe")
            with self.assertRaisesRegex(SnapshotError, "unsupported filesystem object"):
                capture_project_snapshot(directory)

    def test_entry_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a", encoding="utf-8")
            (root / "b").write_text("b", encoding="utf-8")
            with self.assertRaisesRegex(SnapshotError, "max_entries"):
                capture_project_snapshot(root, limits=SnapshotLimits(max_entries=1))

    def test_file_size_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "large.bin").write_bytes(b"12345")
            with self.assertRaisesRegex(SnapshotError, "max_file_bytes"):
                capture_project_snapshot(directory, limits=SnapshotLimits(max_file_bytes=4, max_total_bytes=8))

    def test_total_size_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.bin").write_bytes(b"1234")
            (root / "b.bin").write_bytes(b"5678")
            with self.assertRaisesRegex(SnapshotError, "max_total_bytes"):
                capture_project_snapshot(root, limits=SnapshotLimits(max_file_bytes=8, max_total_bytes=7))

    def test_depth_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            nested = Path(directory) / "a" / "b"
            nested.mkdir(parents=True)
            with self.assertRaisesRegex(SnapshotError, "max_depth"):
                capture_project_snapshot(directory, limits=SnapshotLimits(max_depth=1))

    def test_nonportable_paths_are_rejected(self):
        for path in ("../escape", "/absolute", "a\\b", "a//b", "a/../b", "C:/outside", "name."):
            with self.subTest(path=path), self.assertRaises(SnapshotError):
                SnapshotEntry(path, "directory", 0o755)

    def test_invalid_limit_types_are_rejected(self):
        with self.assertRaises(SnapshotError):
            SnapshotLimits(max_entries=True)
        with self.assertRaises(SnapshotError):
            SnapshotLimits(max_file_bytes=10, max_total_bytes=9)

    def test_snapshot_round_trip_preserves_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "file.txt").write_text("payload", encoding="utf-8")
            original = capture_project_snapshot(directory)
            encoded = serialize_project_snapshot(original)
            restored = deserialize_project_snapshot(encoded)
            self.assertEqual(restored.to_document(), original.to_document())
            self.assertEqual(restored.snapshot_digest, original.snapshot_digest)

    def test_snapshot_import_rejects_digest_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "file.txt").write_text("payload", encoding="utf-8")
            encoded = serialize_project_snapshot(capture_project_snapshot(directory))
            tampered = encoded.replace(b"file.txt", b"evil.txt")
            with self.assertRaisesRegex(SnapshotError, "digest mismatch"):
                deserialize_project_snapshot(tampered)

    def test_snapshot_import_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(SnapshotError, "invalid project snapshot JSON"):
            deserialize_project_snapshot(b'{"schema":1,"schema":1}')

    def test_snapshot_import_rejects_noncanonical_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            encoded = serialize_project_snapshot(capture_project_snapshot(directory))
            with self.assertRaisesRegex(SnapshotError, "not canonical"):
                deserialize_project_snapshot(encoded + b" ")

    def test_snapshot_import_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            document = capture_project_snapshot(directory).to_document()
            document["unexpected"] = True
            with self.assertRaisesRegex(SnapshotError, "missing or unexpected"):
                ProjectSnapshot.from_document(document)

    def test_snapshot_rejects_unsorted_or_duplicate_paths(self):
        first = SnapshotEntry("b.txt", "file", 0o644, 0, "a" * 64)
        second = SnapshotEntry("a.txt", "file", 0o644, 0, "b" * 64)
        with self.assertRaisesRegex(SnapshotError, "canonical path order"):
            ProjectSnapshot((first, second), (), SnapshotLimits(), "2026-11-04T00:00:00Z")

    def test_snapshot_rejects_noncanonical_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            document = capture_project_snapshot(directory).to_document()
            document["captured_at"] = "2026-11-04T00:00:00+00:00"
            document["snapshot_digest"] = ProjectSnapshot.from_document({
                **document,
                "snapshot_digest": capture_project_snapshot(directory).snapshot_digest,
            }).snapshot_digest if False else document["snapshot_digest"]
            with self.assertRaises(SnapshotError):
                ProjectSnapshot.from_document(document)


if __name__ == "__main__":
    unittest.main()

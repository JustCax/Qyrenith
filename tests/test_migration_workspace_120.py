"""Regression tests for snapshot-pinned isolated workspaces."""
import os
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from qyrenith_engine.migration.model import MigrationIdentity
from qyrenith_engine.migration.snapshot import (
    capture_project_snapshot,
)
from qyrenith_engine.migration.workspace import (
    WorkspaceDescriptor,
    WorkspaceError,
    create_isolated_workspace,
    deserialize_workspace_descriptor,
    serialize_workspace_descriptor,
    verify_workspace_baseline,
)


def target_identity(loader="fabric"):
    return MigrationIdentity(
        domain="minecraft",
        product="minecraft",
        product_version="1.21.1",
        platform="java",
        loader=loader,
        loader_version="0.16.0" if loader == "fabric" else "21.1.0",
        language="java",
        toolchain="jdk-21",
    )


class TestIsolatedWorkspace(unittest.TestCase):
    def source_tree(self, root):
        (root / "src" / "main").mkdir(parents=True)
        (root / "empty").mkdir()
        (root / "src" / "main" / "Main.java").write_text(
            "class Main { static final int VALUE = 1; }\n", encoding="utf-8"
        )
        (root / "README.md").write_text("source baseline\n", encoding="utf-8")
        (root / ".git").mkdir()
        (root / ".git" / "config").write_text("excluded\n", encoding="utf-8")

    def test_materializes_a_snapshot_pinned_independent_project(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            self.source_tree(source)
            snapshot = capture_project_snapshot(source)
            descriptor = create_isolated_workspace(source, snapshot, parent, target_identity())
            project = Path(descriptor.project_path)
            self.assertTrue(project.is_dir())
            self.assertEqual((project / "README.md").read_text(encoding="utf-8"), "source baseline\n")
            self.assertEqual(
                (project / "src" / "main" / "Main.java").read_text(encoding="utf-8"),
                "class Main { static final int VALUE = 1; }\n",
            )
            self.assertTrue((project / "empty").is_dir())
            self.assertFalse((project / ".git").exists())
            self.assertTrue((Path(descriptor.workspace_path) / "workspace.json").is_file())
            self.assertTrue(verify_workspace_baseline(descriptor, snapshot).matches)
            self.assertEqual(descriptor.source_snapshot_digest, snapshot.snapshot_digest)
            self.assertFalse((source / ".qyrenith").exists())

    def test_two_targets_receive_independent_workspace_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            self.source_tree(source)
            snapshot = capture_project_snapshot(source)
            fabric = create_isolated_workspace(source, snapshot, parent, target_identity("fabric"))
            forge = create_isolated_workspace(source, snapshot, parent, target_identity("forge"))
            self.assertNotEqual(fabric.workspace_id, forge.workspace_id)
            self.assertNotEqual(fabric.project_path, forge.project_path)
            Path(fabric.project_path, "README.md").write_text("fabric-only\n", encoding="utf-8")
            self.assertEqual(
                Path(forge.project_path, "README.md").read_text(encoding="utf-8"),
                "source baseline\n",
            )
            self.assertEqual((source / "README.md").read_text(encoding="utf-8"), "source baseline\n")
            self.assertTrue(verify_workspace_baseline(forge, snapshot).matches)
            self.assertEqual(verify_workspace_baseline(fabric, snapshot).status, "CHANGED")

    def test_empty_project_can_be_materialized(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            snapshot = capture_project_snapshot(source)
            descriptor = create_isolated_workspace(source, snapshot, parent, target_identity())
            self.assertEqual(descriptor.file_count, 0)
            self.assertEqual(descriptor.total_bytes, 0)
            self.assertTrue(verify_workspace_baseline(descriptor, snapshot).matches)

    def test_partial_workspace_is_removed_when_copy_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\\n", encoding="utf-8")
            snapshot = capture_project_snapshot(source)
            with patch(
                "qyrenith_engine.migration.workspace._copy_regular_file",
                side_effect=WorkspaceError("simulated copy failure"),
            ):
                with self.assertRaisesRegex(WorkspaceError, "simulated copy failure"):
                    create_isolated_workspace(source, snapshot, parent, target_identity())
            self.assertEqual(list(parent.iterdir()), [])

    def test_workspace_creation_rejects_a_stale_source_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("before\n", encoding="utf-8")
            snapshot = capture_project_snapshot(source)
            (source / "main.py").write_text("after\n", encoding="utf-8")
            with self.assertRaisesRegex(WorkspaceError, "does not match"):
                create_isolated_workspace(source, snapshot, parent, target_identity())
            self.assertEqual(list(parent.iterdir()), [])

    def test_workspace_parent_must_be_outside_source_project(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            parent = source / "workspaces"
            parent.mkdir()
            snapshot = capture_project_snapshot(source)
            with self.assertRaisesRegex(WorkspaceError, "outside the source project"):
                create_isolated_workspace(source, snapshot, parent, target_identity())

    def test_workspace_parent_must_not_be_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "parent"
            actual = base / "actual"
            source.mkdir()
            actual.mkdir()
            try:
                os.symlink(actual, parent, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this platform")
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            snapshot = capture_project_snapshot(source)
            with self.assertRaisesRegex(WorkspaceError, "real directory"):
                create_isolated_workspace(source, snapshot, parent, target_identity())

    def test_snapshots_containing_symlinks_are_not_materialized(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            target = base / "external"
            target.mkdir()
            (target / "secret.txt").write_text("outside\n", encoding="utf-8")
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            try:
                os.symlink(target, source / "external-link", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this platform")
            snapshot = capture_project_snapshot(source)
            with self.assertRaisesRegex(WorkspaceError, "symbolic links"):
                create_isolated_workspace(source, snapshot, parent, target_identity())
            self.assertEqual(list(parent.iterdir()), [])

    def test_workspace_baseline_verification_rejects_another_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            snapshot = capture_project_snapshot(source)
            descriptor = create_isolated_workspace(source, snapshot, parent, target_identity())
            altered = capture_project_snapshot(source, excluded_paths=(".git",))
            with self.assertRaisesRegex(WorkspaceError, "different source snapshot"):
                verify_workspace_baseline(descriptor, altered)

    def test_workspace_descriptor_round_trip_is_canonical(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            snapshot = capture_project_snapshot(source)
            descriptor = create_isolated_workspace(source, snapshot, parent, target_identity())
            encoded = serialize_workspace_descriptor(descriptor)
            restored = deserialize_workspace_descriptor(encoded)
            self.assertEqual(restored.to_document(), descriptor.to_document())
            self.assertEqual(restored.descriptor_digest, descriptor.descriptor_digest)

    def test_workspace_descriptor_path_is_bound_to_workspace_id(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\\n", encoding="utf-8")
            descriptor = create_isolated_workspace(
                source, capture_project_snapshot(source), parent, target_identity()
            )
            with self.assertRaisesRegex(WorkspaceError, "bound to workspace_id"):
                replace(descriptor, workspace_id="0" * 32)

    def test_workspace_descriptor_import_accepts_windows_terminal_crlf(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\\n", encoding="utf-8")
            descriptor = create_isolated_workspace(
                source, capture_project_snapshot(source), parent, target_identity()
            )
            encoded = serialize_workspace_descriptor(descriptor)
            restored = deserialize_workspace_descriptor(encoded.rstrip(b"\\n") + b"\\r\\n")
            self.assertEqual(restored.descriptor_digest, descriptor.descriptor_digest)

    def test_workspace_descriptor_rejects_digest_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            descriptor = create_isolated_workspace(source, capture_project_snapshot(source), parent, target_identity())
            tampered = serialize_workspace_descriptor(descriptor).replace(b"minecraft", b"unreal__")
            with self.assertRaisesRegex(WorkspaceError, "digest mismatch"):
                deserialize_workspace_descriptor(tampered)

    def test_workspace_descriptor_rejects_duplicate_json_keys(self):
        with self.assertRaisesRegex(WorkspaceError, "invalid workspace descriptor JSON"):
            deserialize_workspace_descriptor(b'{"schema":1,"schema":1}')

    def test_workspace_descriptor_rejects_noncanonical_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            descriptor = create_isolated_workspace(source, capture_project_snapshot(source), parent, target_identity())
            with self.assertRaisesRegex(WorkspaceError, "not canonical"):
                deserialize_workspace_descriptor(serialize_workspace_descriptor(descriptor) + b" ")

    def test_workspace_descriptor_rejects_schema_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            parent = base / "workspaces"
            source.mkdir()
            parent.mkdir()
            (source / "main.py").write_text("pass\n", encoding="utf-8")
            document = create_isolated_workspace(
                source, capture_project_snapshot(source), parent, target_identity()
            ).to_document()
            document["schema"] = True
            with self.assertRaises(WorkspaceError):
                WorkspaceDescriptor.from_document(document)


if __name__ == "__main__":
    unittest.main()

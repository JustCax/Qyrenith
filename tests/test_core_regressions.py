"""Regression tests for verified core fixes.

Covers:
- rename residue (MDocError alias, mdoc_version state-key migration)
- double-escaped regexes (candidate detection, evidence confidence, test discovery)
- dead ``or`` fallbacks in generated reports
- the wrong state-dir path for the security coverage dimension
- consolidated hashing
"""
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_core_regressions", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)


class TestRenameResidue(unittest.TestCase):
    def test_error_class_alias_is_same_class(self):
        self.assertIs(qyrenith.MDocError, qyrenith.QyrenithError)

    def test_error_alias_is_catchable(self):
        with self.assertRaises(qyrenith.MDocError):
            qyrenith.die("STOPPED", "fixture")

    def test_initial_state_uses_current_key(self):
        s = qyrenith.initial_state(Path("."))
        self.assertIn("qyrenith_version", s)
        self.assertNotIn("mdoc_version", s)

    def test_legacy_state_key_is_migrated(self):
        legacy = {"schema": 8, "mdoc_version": "0.9.0"}
        migrated = qyrenith.migrate_state(dict(legacy))
        self.assertEqual(migrated["qyrenith_version"], "0.9.0")
        self.assertNotIn("mdoc_version", migrated)


class TestDoubleEscapedRegexes(unittest.TestCase):
    def test_candidate_feature_detection_matches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Feature.java").write_text(
                "public class Feature implements Screen {}\n", encoding="utf-8")
            names = [c["name"] for c in qyrenith.candidate_feature_inventory(root)]
            self.assertTrue(names, "implements Screen should yield a candidate")

    def test_evidence_reference_confidence_high(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            refs = root / ".agents" / "skills" / "minecraft-porting" / "references"
            refs.mkdir(parents=True)
            (refs / "versions.md").write_text("1.20.1 -> 1.20.2 VERIFIED\n", encoding="utf-8")
            inventory = qyrenith.evidence_inventory(root)
            confidences = [e.get("confidence") for e in inventory if e.get("type") == "reference"]
            self.assertIn("HIGH", confidences)

    def test_root_level_test_file_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".qyrenith").mkdir()
            (root / "test_root_level.py").write_text("x = 1\n", encoding="utf-8")
            inv = qyrenith.semantic_inventory(root)
            self.assertIn("test_root_level.py", inv["tests"])

    def test_no_double_escaped_classes_remain(self):
        # Guard against reintroducing the exact double-escaped regex classes that
        # were fixed. Scoped to the specific regression sites so legitimate
        # escaped backslashes elsewhere (e.g. "\\server" fuzz atoms) do not trip it.
        source = (ROOT / "qyrenith.py").read_text(encoding="utf-8")
        self.assertNotIn(r"implements\\s", source)
        self.assertNotIn(r"extends\\s", source)
        self.assertNotIn(r"\\bVERIFIED", source)
        self.assertNotIn(r"test_[^/]+\\.", source)


class TestDeadOrFallbacks(unittest.TestCase):
    def _map(self, issues, evidence):
        return {
            "generated": "now", "reason": "test",
            "project_identity": {}, "versions": [], "features": [], "integrations": [],
            "issues": issues, "evidence": evidence, "graph": {},
            "current_state": {}, "baseline_comparison": {},
        }

    def test_empty_issues_show_placeholder(self):
        md = qyrenith.reality_map_markdown(self._map([], []))
        self.assertIn("- None recorded.", md)
        self.assertIn("- No evidence records available.", md)

    def test_present_issues_are_listed(self):
        md = qyrenith.reality_map_markdown(self._map(
            [{"type": "X", "status": "OPEN", "message": "boom"}],
            [{"confidence": "HIGH", "source": "s", "status": "VERIFIED"}]))
        self.assertIn("boom", md)
        self.assertNotIn("- None recorded.", md)


class TestCoverageAndHash(unittest.TestCase):
    def test_security_dimension_observes_state_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = root / ".qyrenith"
            state.mkdir()
            (state / "security-report.json").write_text('{"status":"PASS"}', encoding="utf-8")
            cov = qyrenith.verification_coverage(root)
            self.assertEqual(cov["dimensions"]["security"]["status"], "OBSERVED")

    def test_sha256_matches_sha256_full(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "x.bin"
            f.write_bytes(b"hello world")
            self.assertEqual(qyrenith.sha256(f), qyrenith.sha256_full(f))


if __name__ == "__main__":
    unittest.main()
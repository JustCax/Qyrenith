"""Version baseline gate: package, CLI, citation, and release notes must agree."""
import importlib.util
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_version_gate", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)

EXPECTED = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


class TestVersionConsistency(unittest.TestCase):
    def test_version_txt_is_release_baseline(self):
        self.assertEqual((ROOT / "VERSION.txt").read_text(encoding="utf-8").strip(), EXPECTED)

    def test_version_constant_matches(self):
        self.assertEqual(qyrenith.VERSION, EXPECTED)

    def test_citation_matches(self):
        text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        match = re.search(r'(?m)^version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)', text)
        self.assertIsNotNone(match, "CITATION.cff must carry a version field")
        self.assertEqual(match.group(1), EXPECTED)

    def test_package_metadata_matches_supported_baseline(self):
        with (ROOT / "pyproject.toml").open("rb") as source:
            metadata = tomllib.load(source)
        self.assertEqual(metadata["project"]["version"], EXPECTED)
        self.assertEqual(metadata["project"]["requires-python"], ">=3.11")

    def test_release_notes_and_changelog_exist(self):
        self.assertTrue((ROOT / "RELEASE_NOTES_1.1.0.md").is_file())
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 1.1.0", changelog)


    def test_all_github_actions_are_pinned_to_immutable_shas(self):
        workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        self.assertTrue(workflows, "GitHub Actions workflows must exist")
        for workflow in workflows:
            for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1):
                if re.match(r"^\s*uses\s*:", line):
                    self.assertRegex(
                        line,
                        r"^\s*uses\s*:\s*[^@\s]+@[0-9a-f]{40}(?:\s+#.*)?\s*$",
                        f"{workflow.relative_to(ROOT)}:{line_number} must pin its action to a full commit SHA",
                    )

    def test_all_surfaces_agree(self):
        version_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(version_txt, qyrenith.VERSION)


if __name__ == "__main__":
    unittest.main()

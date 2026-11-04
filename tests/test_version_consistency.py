"""Version baseline gate: package, CLI, citation, and release notes must agree."""
import hashlib
import importlib.util
import re
import subprocess
import sys
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


    def test_gradle_wrapper_binary_matches_pinned_checksum(self):
        # This checked-in bootstrap JAR is an older official wrapper artifact; the 8.14.2 distribution is pinned separately.
        wrapper = ROOT / "examples" / "example-neoforge-mod" / "gradle" / "wrapper" / "gradle-wrapper.jar"
        digest = hashlib.sha256(wrapper.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "2db75c40782f5e8ba1fc278a5574bab070adccb2d21ca5a6e5ed840888448046",
        )

    def test_gradle_distribution_checksum_is_pinned(self):
        properties = (
            ROOT / "examples" / "example-neoforge-mod" / "gradle" / "wrapper"
            / "gradle-wrapper.properties"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "distributionSha256Sum=7197a12f450794931532469d4ff21a59ea2c1cd59a3ec3f89c035c3c420a6999",
            properties,
        )

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

    def test_generated_client_instructions_are_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate-client-entries.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_surfaces_agree(self):
        version_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(version_txt, qyrenith.VERSION)


if __name__ == "__main__":
    unittest.main()

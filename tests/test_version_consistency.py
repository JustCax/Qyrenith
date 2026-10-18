"""Version baseline gate: VERSION.txt, VERSION, and CITATION.cff must agree.

The first public release is 1.0.0. This test fails the suite on any future
drift between the recorded version surfaces.
"""
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith_version_gate", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)

EXPECTED = "1.0.0"


class TestVersionConsistency(unittest.TestCase):
    def test_version_txt_is_release_baseline(self):
        self.assertEqual((ROOT / "VERSION.txt").read_text(encoding="utf-8").strip(), EXPECTED)

    def test_version_constant_matches(self):
        self.assertEqual(qyrenith.VERSION, EXPECTED)

    def test_citation_matches(self):
        text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        m = re.search(r'(?m)^version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)', text)
        self.assertIsNotNone(m, "CITATION.cff must carry a version field")
        self.assertEqual(m.group(1), EXPECTED)

    def test_all_surfaces_agree(self):
        version_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(version_txt, qyrenith.VERSION)


if __name__ == "__main__":
    unittest.main()

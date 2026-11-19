"""Character-set guard for the English-only policy; not a language detector."""

from __future__ import annotations

import unicodedata
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
}


class EnglishOnlyRepositoryPolicyTests(unittest.TestCase):
    def test_repository_text_contains_no_non_ascii_letters(self) -> None:
        violations: list[str] = []

        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(ROOT)
            if any(part in EXCLUDED_PARTS for part in relative.parts):
                continue

            try:
                text = path.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                continue

            for line_number, line in enumerate(text.splitlines(), start=1):
                if any(
                    ord(character) > 127
                    and unicodedata.category(character).startswith("L")
                    for character in line
                ):
                    violations.append(f"{relative}:{line_number}")

        self.assertEqual(
            violations,
            [],
            "Non-ASCII letters are forbidden; this character-set check does not prove semantic English.",
        )


if __name__ == "__main__":
    unittest.main()

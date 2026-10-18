"""Per-client entrypoints generated from the canonical skills.

The generator projects the two canonical skill sources into per-client files.
Generated files must never grant execution authority, and each must name the
real CLI commands and the state directory.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLIENT_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "GEMINI.md",
    ROOT / ".cursor" / "rules" / "qyrenith.mdc",
    ROOT / ".windsurf" / "rules" / "qyrenith.md",
    ROOT / ".clinerules",
    ROOT / "CONVENTIONS.md",
    ROOT / ".continue" / "rules" / "qyrenith.md",
]

FORBIDDEN = [
    "skip the build gate",
    "skip validation",
    "bypass",
    "you may declare success",
    "declare success",
    "ignore validation",
    "ignore the gate",
    "do not need verification",
    "without verification",
]

REQUIRED_COMMANDS = ["verify", "doctor", "inspect", "explain"]


class TestClientEntries(unittest.TestCase):
    def test_all_client_files_exist(self):
        missing = [str(p) for p in CLIENT_FILES if not p.is_file()]
        self.assertEqual(missing, [], "every client entrypoint must be generated")

    def test_generated_files_carry_the_header(self):
        for path in CLIENT_FILES:
            text = path.read_text(encoding="utf-8")
            self.assertIn("generated", text.lower(),
                          f"{path.name} must say it is generated, not hand-written")

    def test_no_client_file_grants_execution_authority(self):
        """Review Focus item 3: a skill file must never let an agent bypass a gate."""
        for path in CLIENT_FILES:
            text = path.read_text(encoding="utf-8").lower()
            for phrase in FORBIDDEN:
                self.assertNotIn(phrase, text,
                                 f"{path} must not contain authority-granting language: {phrase!r}")

    def test_each_client_file_names_the_real_commands(self):
        for path in CLIENT_FILES:
            text = path.read_text(encoding="utf-8")
            for cmd in REQUIRED_COMMANDS:
                self.assertRegex(text, rf"(?m)\b{re.escape(cmd)}\b",
                                 f"{path} must name the real `{cmd}` command")
            self.assertIn(".qyrenith", text,
                          f"{path} must reference the state directory")

    def test_each_client_file_names_both_skills(self):
        for path in CLIENT_FILES:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("verif", text, f"{path} must cover generic verification")
            self.assertIn("minecraft", text, f"{path} must cover the Minecraft path")


if __name__ == "__main__":
    unittest.main()

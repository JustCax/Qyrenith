#!/usr/bin/env python3
"""Generate per-client AI entrypoints from the canonical skill sources.

Reads `skills-source/generic-verification/SKILL.md` and
`skills-source/minecraft-porting/SKILL.md`, and projects them into the file
each AI client expects. Generated files carry a header and must never be
hand-edited; change the canonical sources and re-run this script.

Standard library only. Deterministic and idempotent.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERIC = ROOT / "skills-source" / "generic-verification" / "SKILL.md"
MINECRAFT = ROOT / "skills-source" / "minecraft-porting" / "SKILL.md"

HEADER = (
    "<!-- GENERATED from skills-source/ by scripts/generate-client-entries.py. "
    "Do not edit by hand; edit the canonical skill and re-run the generator. -->\n\n"
)


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            return text[end + len("\n---"):].lstrip("\n")
    return text


def shared_body() -> str:
    generic = strip_frontmatter(GENERIC.read_text(encoding="utf-8")).strip()
    minecraft = strip_frontmatter(MINECRAFT.read_text(encoding="utf-8")).strip()
    return (
        "# Qyrenith — verification and orchestration control plane\n"
        "\n"
        "`qyrenith.py` in the project root is the deterministic authority. "
        "The agent supplies expertise; only executed checks, observed artifacts, "
        "and recorded evidence advance any verdict. An agent statement is never "
        "proof of completion.\n"
        "\n"
        "## Generic verification (any project)\n"
        "\n"
        "```bash\n"
        "python qyrenith.py doctor --project .\n"
        "python qyrenith.py verify --project . --execute\n"
        "python qyrenith.py inspect --project .\n"
        "python qyrenith.py explain <BLOCKER_CODE>\n"
        "```\n"
        "\n"
        "State lives in `.qyrenith/`. A `NOT_AVAILABLE` result is an honest "
        "answer, never a reason to invent a check. A `BLOCKED` result names its "
        "blocker; resolve the named condition and re-run.\n"
        "\n"
        "## Hard invariants\n"
        "\n"
        "- `AUDIT_BEFORE_PATCH`\n"
        "- `BACKUP_BEFORE_PATCH`\n"
        "- `NO_GUESSING`\n"
        "- `MINIMAL_PATCH`\n"
        "- `VALIDATE_BEFORE_COMMIT`\n"
        "- `HONEST_FINAL_REPORT`\n"
        "\n"
        "## Minecraft migration (Minecraft projects only)\n"
        "\n"
        "```bash\n"
        "python qyrenith.py port --project . --target-mc <target> --target-loader <loader> --managed\n"
        "python qyrenith.py continue --project . --managed\n"
        "```\n"
        "\n"
        "One verified version step at a time, at most five fix iterations per "
        "step, build plus validation before every commit. Unknown APIs stop the "
        "workflow with `UNKNOWN_API` instead of being guessed.\n"
        "\n"
        "## Full contracts\n"
        "\n"
        "The text below is the canonical skill source. It is advisory routing "
        "and procedure; the CLI owns every gate.\n"
        "\n"
        "<details>\n<summary>Generic verification skill (canonical)</summary>\n"
        "\n" + generic + "\n\n</details>\n"
        "\n"
        "<details>\n<summary>Minecraft porting skill (canonical)</summary>\n"
        "\n" + minecraft + "\n\n</details>\n"
    )


def md_file(intro: str, install: str) -> str:
    return HEADER + intro + "\n\n" + install + "\n\n" + shared_body()


CLIENTS = {
    # OpenCode and Codex share the AGENTS.md convention.
    "AGENTS.md": (
        "# AGENTS.md — Qyrenith (OpenCode, Codex, and other AGENTS.md clients)\n"
        "\nPlace this file at the repository root. OpenCode and Codex read it "
        "automatically; other AGENTS.md-compatible clients do the same.",
        "## Install\n\nCopy `AGENTS.md` to the repository root. No other setup is required.",
    ),
    "CLAUDE.md": (
        "# CLAUDE.md — Qyrenith (Claude Code)\n"
        "\nPlace this file at the repository root. Claude Code reads it automatically.",
        "## Install\n\nCopy `CLAUDE.md` to the repository root. No other setup is required.",
    ),
    "GEMINI.md": (
        "# GEMINI.md — Qyrenith (Gemini CLI)\n"
        "\nPlace this file at the repository root. Gemini CLI reads it automatically.",
        "## Install\n\nCopy `GEMINI.md` to the repository root. No other setup is required.",
    ),
    ".cursor/rules/qyrenith.mdc": (
        "---\ndescription: Qyrenith verification and orchestration control plane\n"
        "globs: [qyrenith.py, .qyrenith/**/*]\n---\n"
        "\n# Qyrenith (Cursor)\n"
        "\nThis rule activates when the task touches verification, migration, or `qyrenith.py`.",
        "## Install\n\nCopy this file to `.cursor/rules/qyrenith.mdc` in the repository.",
    ),
    ".windsurf/rules/qyrenith.md": (
        "# Qyrenith (Windsurf)\n"
        "\nWindsurf reads workspace rules from `.windsurf/rules/`.",
        "## Install\n\nCopy this file to `.windsurf/rules/qyrenith.md` in the repository.",
    ),
    ".clinerules": (
        "# Qyrenith (Cline)\n"
        "\nCline reads `.clinerules` at the repository root.",
        "## Install\n\nCopy `.clinerules` to the repository root.",
    ),
    "CONVENTIONS.md": (
        "# Qyrenith (Aider)\n"
        "\nAider reads `CONVENTIONS.md` at the repository root.",
        "## Install\n\nCopy `CONVENTIONS.md` to the repository root.",
    ),
    ".continue/rules/qyrenith.md": (
        "# Qyrenith (Continue)\n"
        "\nContinue loads rules from `.continue/rules/`.",
        "## Install\n\nCopy this file to `.continue/rules/qyrenith.md` in the repository.",
    ),
}


def main() -> None:
    for rel, (intro, install) in CLIENTS.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md_file(intro, install), encoding="utf-8", newline="\n")
        print(f"wrote {rel}")


if __name__ == "__main__":
    main()

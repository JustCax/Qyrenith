#!/usr/bin/env python3
"""Check local Markdown links without requiring network access."""
from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
for doc in sorted(ROOT.rglob("*.md")):
    if any(x in {".git",".qyrenith",".backups","dist","__pycache__"} for x in doc.relative_to(ROOT).parts):
        continue
    text=doc.read_text(encoding="utf-8",errors="replace")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)",text):
        target=target.strip()
        if not target or target.startswith(("http://","https://","mailto:","#")):
            continue
        target=target.split("#",1)[0]
        if not target: continue
        candidate=(doc.parent/target).resolve()
        try: candidate.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{doc.relative_to(ROOT)} -> outside repository: {target}")
            continue
        if not candidate.exists(): errors.append(f"{doc.relative_to(ROOT)} -> missing: {target}")
if errors:
    print("Documentation links: FAIL")
    print("\n".join(errors))
    sys.exit(1)
print("Documentation links: PASS")

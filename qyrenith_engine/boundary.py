"""Read-only filesystem boundary checks for project inspection."""
from __future__ import annotations
from pathlib import Path
import os
from typing import Union, Dict, Any

_EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", ".qyrenith"}


def inspect_project_boundary(project: Union[str, Path], *, max_entries: int = 50000,
                             large_file_bytes: int = 100_000_000) -> Dict[str, Any]:
    if max_entries < 1 or large_file_bytes < 1:
        raise ValueError("inspection limits must be positive")
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project root must be a directory")
    findings = []
    inspected = 0
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in _EXCLUDED for part in relative.parts):
            continue
        inspected += 1
        if inspected > max_entries:
            return {"schema": 1, "status": "BLOCKED", "inspected_entries": inspected - 1,
                    "findings": findings, "reason": "entry limit exceeded"}
        try:
            if path.is_symlink():
                target = (path.parent / os.readlink(str(path))).resolve(strict=False)
                try:
                    target.relative_to(root)
                except ValueError:
                    findings.append({"path": relative.as_posix(), "code": "FS001", "severity": "high",
                                     "message": "Symlink target escapes project root."})
            elif path.is_file() and path.stat().st_size > large_file_bytes:
                findings.append({"path": relative.as_posix(), "code": "FS002", "severity": "review",
                                 "message": "File exceeds configured inspection threshold."})
        except OSError as exc:
            findings.append({"path": relative.as_posix(), "code": "FS003", "severity": "review",
                             "message": "Filesystem metadata unavailable: %s" % type(exc).__name__})
    return {"schema": 1, "status": "REVIEW_REQUIRED" if findings else "PASS",
            "project": str(root), "inspected_entries": inspected, "findings": findings,
            "read_only": True,
            "limitations": ["Does not replace OS sandboxing, malware scanning, or a full security audit."]}

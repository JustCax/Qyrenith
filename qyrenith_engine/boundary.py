"""Read-only filesystem boundary checks for project inspection."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Union

_EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", ".qyrenith"}


def inspect_project_boundary(project: Union[str, Path], *, max_entries: int = 50000,
                             large_file_bytes: int = 100_000_000) -> Dict[str, Any]:
    """Inspect entries without following symlinked directories or modifying the project."""
    if max_entries < 1 or large_file_bytes < 1:
        raise ValueError("inspection limits must be positive")
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project root must be a directory")

    findings = []
    inspected = 0
    pending = [root]
    errors = []
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            errors.append({"path": directory.relative_to(root).as_posix(),
                           "reason": type(exc).__name__})
            continue
        for entry in entries:
            relative = Path(entry.path).relative_to(root)
            if any(part in _EXCLUDED for part in relative.parts):
                continue
            inspected += 1
            if inspected > max_entries:
                return {"schema": 1, "status": "BLOCKED", "inspected_entries": inspected - 1,
                        "findings": findings, "errors": errors, "reason": "entry limit exceeded"}
            try:
                if entry.is_symlink():
                    target = (Path(entry.path).parent / os.readlink(entry.path)).resolve(strict=False)
                    try:
                        target.relative_to(root)
                    except ValueError:
                        findings.append({"path": relative.as_posix(), "code": "FS001", "severity": "high",
                                         "message": "Symlink target escapes project root."})
                    except (OSError, RuntimeError) as exc:
                        errors.append({"path": relative.as_posix(), "reason": type(exc).__name__})
                    continue
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    metadata = entry.stat(follow_symlinks=False)
                    if metadata.st_size > large_file_bytes:
                        findings.append({"path": relative.as_posix(), "code": "FS002", "severity": "review",
                                         "message": "File exceeds configured inspection threshold."})
            except (OSError, RuntimeError) as exc:
                errors.append({"path": relative.as_posix(), "reason": type(exc).__name__})

    status = "BLOCKED" if errors else ("REVIEW_REQUIRED" if findings else "PASS")
    return {"schema": 1, "status": status, "project": str(root), "inspected_entries": inspected,
            "findings": findings, "errors": errors, "read_only": True,
            "limitations": ["Does not replace OS sandboxing, malware scanning, or a full security audit."]}

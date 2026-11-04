"""Explicit, bounded subprocess execution; not an operating-system sandbox."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Sequence, Union, Dict, Any

_ALLOWED_ENV = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL"}


def run_bounded_process(argv: Sequence[str], project: Union[str, Path], *, timeout: int = 120,
                        output_limit: int = 16000,
                        env_overrides: Union[Dict[str, str], None] = None) -> Dict[str, Any]:
    if not isinstance(argv, (list, tuple)) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("argv must be a non-empty sequence of non-empty strings")
    if not 1 <= timeout <= 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds")
    if not 256 <= output_limit <= 1000000:
        raise ValueError("output_limit must be between 256 and 1000000 bytes")
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project must be a directory")
    env = {key: value for key, value in os.environ.items() if key in _ALLOWED_ENV}
    for key, value in (env_overrides or {}).items():
        if key not in _ALLOWED_ENV or not isinstance(value, str):
            raise ValueError("environment override is not allowlisted: %s" % key)
        env[key] = value
    try:
        completed = subprocess.run(list(argv), cwd=root, env=env, shell=False,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=timeout, check=False)
        raw = completed.stdout or b""
        truncated = len(raw) > output_limit
        return {"schema": 1, "status": "BLOCKED" if truncated else ("PASS" if completed.returncode == 0 else "FAIL"),
                "exit_code": completed.returncode, "argv": list(argv),
                "output": raw[:output_limit].decode("utf-8", "replace"),
                "output_bytes": len(raw), "output_truncated": truncated, "shell": False,
                "containment": "Process-level controls only; not an OS sandbox."}
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout or b""
        if isinstance(raw, str):
            raw = raw.encode()
        return {"schema": 1, "status": "BLOCKED", "exit_code": None, "argv": list(argv),
                "output": raw[:output_limit].decode("utf-8", "replace"), "output_bytes": len(raw),
                "output_truncated": len(raw) > output_limit, "timed_out": True,
                "containment": "Process-level controls only; not an OS sandbox."}

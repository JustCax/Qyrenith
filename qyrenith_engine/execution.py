"""Explicit bounded subprocess execution; this is not an operating-system sandbox."""
from __future__ import annotations

import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Sequence, Union

_ALLOWED_ENV = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL"}


def _terminate_process_group(process: subprocess.Popen) -> None:
    """Stop the launched process group on POSIX; Windows uses direct process termination."""
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # The group leader may exit while descendants remain alive in the group.
    try:
        if os.name == "nt":
            if process.poll() is None:
                process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
    process.wait()


def run_bounded_process(argv: Sequence[str], project: Union[str, Path], *, timeout: int = 120,
                        output_limit: int = 16000,
                        env_overrides: Union[Dict[str, str], None] = None) -> Dict[str, Any]:
    """Run an explicitly supplied argv with timeout and a hard in-memory output cap."""
    if not isinstance(argv, (list, tuple)) or not argv or any(
            not isinstance(item, str) or not item or "\x00" in item for item in argv):
        raise ValueError("argv must be a non-empty sequence of non-empty strings")
    if not 1 <= timeout <= 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds")
    if not 256 <= output_limit <= 1000000:
        raise ValueError("output_limit must be between 256 and 1000000 bytes")
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project must be a directory")
    if env_overrides is not None and not isinstance(env_overrides, dict):
        raise ValueError("env_overrides must be a dictionary")
    env = {key: value for key, value in os.environ.items() if key in _ALLOWED_ENV}
    for key, value in (env_overrides or {}).items():
        if key not in _ALLOWED_ENV or not isinstance(value, str) or "\x00" in value:
            raise ValueError("environment override is not allowlisted: %s" % key)
        env[key] = value

    kwargs: Dict[str, Any] = {
        "cwd": root, "env": env, "shell": False, "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(list(argv), **kwargs)
    except (OSError, ValueError) as exc:
        return {"schema": 1, "status": "ERROR", "exit_code": None, "argv": list(argv),
                "error": type(exc).__name__, "containment": "Process-level controls only; not an OS sandbox."}

    captured = bytearray()
    total = [0]
    overflow = threading.Event()

    def drain_output() -> None:
        assert process.stdout is not None
        try:
            while True:
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                total[0] += len(chunk)
                remaining = output_limit - len(captured)
                if remaining > 0:
                    captured.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    _terminate_process_group(process)
                    break
        except (OSError, ValueError):
            overflow.set()
        finally:
            try:
                process.stdout.close()
            except OSError:
                pass

    reader = threading.Thread(target=drain_output, name="qyrenith-output-reader", daemon=True)
    reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_group(process)
    reader.join(timeout=2)
    if reader.is_alive():
        # A descendant may have inherited the output pipe after the parent exited.
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        reader.join(timeout=1)
    output_incomplete = reader.is_alive()

    output = bytes(captured).decode("utf-8", "replace")
    truncated = overflow.is_set() or total[0] > output_limit
    status = "BLOCKED" if timed_out or truncated or output_incomplete else (
        "PASS" if process.returncode == 0 else "FAIL")
    return {"schema": 1, "status": status, "exit_code": process.returncode,
            "argv": list(argv), "output": output, "output_bytes": total[0],
            "output_truncated": truncated, "output_incomplete": output_incomplete,
            "timed_out": timed_out, "shell": False,
            "containment": "POSIX process-group cleanup and bounded capture; not an OS sandbox. Child code retains the invoking user's OS permissions."}

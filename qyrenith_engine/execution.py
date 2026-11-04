"""Shared bounded subprocess execution; this is not an operating-system sandbox."""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Union

_ALLOWED_ENV = {"PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "LANG", "LC_ALL"}
_MAX_OUTPUT_BYTES = 8 * 1024 * 1024
_MAX_WORKER_INPUT_BYTES = 1024 * 1024


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


def _environment(
    overrides: Mapping[str, str] | None,
    *,
    inherit: bool,
) -> dict[str, str]:
    if overrides is not None and not isinstance(overrides, Mapping):
        raise ValueError("env_overrides must be a mapping")
    result = dict(os.environ) if inherit else {
        key: value for key, value in os.environ.items() if key in _ALLOWED_ENV
    }
    for key, value in (overrides or {}).items():
        if key not in _ALLOWED_ENV or not isinstance(value, str) or "\x00" in value:
            raise ValueError("environment override is not allowlisted: %s" % key)
        result[key] = value
    return result


def _run_process(
    argv: Sequence[str],
    project: Union[str, Path],
    *,
    timeout: int,
    output_limit: int,
    env: Mapping[str, str],
    input_data: bytes | None,
    separate_stderr: bool,
) -> dict[str, Any]:
    if not isinstance(argv, (list, tuple)) or not argv or any(
        not isinstance(item, str) or not item or "\x00" in item for item in argv
    ):
        raise ValueError("argv must be a non-empty sequence of non-empty strings")
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds")
    if type(output_limit) is not int or not 256 <= output_limit <= _MAX_OUTPUT_BYTES:
        raise ValueError("output_limit must be between 256 and 8388608 bytes")
    if input_data is not None:
        if not isinstance(input_data, bytes):
            raise ValueError("input_data must be bytes")
        if len(input_data) > _MAX_WORKER_INPUT_BYTES:
            raise ValueError("input_data exceeds the 1 MiB limit")
    if not isinstance(env, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str)
        or "\x00" in key or "\x00" in value
        for key, value in env.items()
    ):
        raise ValueError("environment must contain string keys and values without NUL")
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project must be a directory")

    kwargs: Dict[str, Any] = {
        "cwd": root,
        "env": dict(env),
        "shell": False,
        "stdin": subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE if separate_stderr else subprocess.STDOUT,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True

    started = time.monotonic()
    try:
        process = subprocess.Popen(list(argv), **kwargs)
    except (OSError, ValueError) as exc:
        return {
            "schema": 1,
            "status": "ERROR",
            "exit_code": None,
            "error": type(exc).__name__,
            "stdout": "",
            "stderr": "",
            "output_bytes": 0,
            "output_limited": False,
            "output_incomplete": False,
            "input_incomplete": False,
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "shell": False,
        }

    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    totals = {"stdout": 0, "stderr": 0}
    overflow = threading.Event()
    read_error = threading.Event()
    input_error = threading.Event()
    termination_lock = threading.Lock()
    terminated = False

    def terminate_once() -> None:
        nonlocal terminated
        with termination_lock:
            if terminated:
                return
            terminated = True
        _terminate_process_group(process)

    def drain(stream, name: str) -> None:
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                totals[name] += len(chunk)
                remaining = output_limit - len(buffers[name])
                if remaining > 0:
                    buffers[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    terminate_once()
                    break
        except (OSError, ValueError):
            read_error.set()
        finally:
            try:
                stream.close()
            except OSError:
                pass

    readers = []
    assert process.stdout is not None
    readers.append(threading.Thread(
        target=drain, args=(process.stdout, "stdout"),
        name="qyrenith-stdout-reader", daemon=True,
    ))
    if separate_stderr:
        assert process.stderr is not None
        readers.append(threading.Thread(
            target=drain, args=(process.stderr, "stderr"),
            name="qyrenith-stderr-reader", daemon=True,
        ))
    for reader in readers:
        reader.start()

    writer = None
    if input_data is not None:
        def write_input() -> None:
            assert process.stdin is not None
            try:
                view = memoryview(input_data)
                while view:
                    written = process.stdin.write(view[:65536])
                    if written is None or written <= 0:
                        input_error.set()
                        break
                    view = view[written:]
                process.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                input_error.set()
            finally:
                try:
                    process.stdin.close()
                except (BrokenPipeError, OSError, ValueError):
                    input_error.set()

        writer = threading.Thread(
            target=write_input, name="qyrenith-stdin-writer", daemon=True
        )
        writer.start()

    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_once()

    if writer is not None:
        writer.join(timeout=1)
        if writer.is_alive():
            terminate_once()
            writer.join(timeout=1)
    for reader in readers:
        reader.join(timeout=2)
    if any(reader.is_alive() for reader in readers):
        # A descendant may have inherited a pipe after the direct child exited.
        terminate_once()
        for reader in readers:
            reader.join(timeout=1)

    output_incomplete = read_error.is_set() or any(reader.is_alive() for reader in readers)
    input_incomplete = input_error.is_set() or (writer is not None and writer.is_alive())
    output_limited = overflow.is_set()
    stdout = bytes(buffers["stdout"]).decode("utf-8", "replace")
    stderr = bytes(buffers["stderr"]).decode("utf-8", "replace")
    exit_code = process.returncode
    blocked = timed_out or output_limited or output_incomplete or input_incomplete
    status = "BLOCKED" if blocked else ("PASS" if exit_code == 0 else "FAIL")
    return {
        "schema": 1,
        "status": status,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "output_bytes": totals["stdout"] + totals["stderr"],
        "stdout_bytes": totals["stdout"],
        "stderr_bytes": totals["stderr"],
        "output_limited": output_limited,
        "output_incomplete": output_incomplete,
        "input_incomplete": input_incomplete,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 3),
        "shell": False,
        "containment": (
            "POSIX process-group cleanup and bounded capture; not an OS sandbox. "
            "Child code retains the invoking user's OS permissions."
        ),
    }


def run_bounded_process(
    argv: Sequence[str],
    project: Union[str, Path],
    *,
    timeout: int = 120,
    output_limit: int = 16000,
    env_overrides: Union[Dict[str, str], None] = None,
    inherit_environment: bool = False,
) -> Dict[str, Any]:
    """Run a command with bounded output and timeout; stdin is closed immediately.

    The default environment is an allowlist. Callers that intentionally need the
    controller's ambient environment must opt in with inherit_environment=True.
    """
    if not isinstance(inherit_environment, bool):
        raise ValueError("inherit_environment must be a boolean")
    env = _environment(env_overrides, inherit=inherit_environment)
    report = _run_process(
        argv, project, timeout=timeout, output_limit=output_limit, env=env,
        input_data=None, separate_stderr=False,
    )
    output = report["stdout"]
    truncated = report["output_limited"]
    return {
        "schema": 1,
        "status": report["status"],
        "exit_code": report["exit_code"],
        "argv": list(argv) if isinstance(argv, (list, tuple)) else [],
        "output": output,
        "output_bytes": report["output_bytes"],
        "output_truncated": truncated,
        "output_incomplete": report["output_incomplete"],
        "timed_out": report["timed_out"],
        "shell": False,
        "containment": report.get("containment", "Process-level controls only; not an OS sandbox."),
        **({"error": report["error"]} if "error" in report else {}),
    }


def run_bounded_worker(
    argv: Sequence[str],
    project: Union[str, Path],
    input_data: bytes,
    *,
    timeout: int = 120,
    output_limit: int = _MAX_WORKER_INPUT_BYTES,
    env: Mapping[str, str] | None = None,
) -> Dict[str, Any]:
    """Run a protocol worker with deadline-covered stdin, separate bounded streams.

    Input is written by a dedicated thread so a worker that never reads stdin
    cannot block the controller before its timeout starts. Output overflow kills
    the process group immediately and is always reported as BLOCKED.
    """
    if env is None:
        environment = _environment(None, inherit=False)
    else:
        environment = dict(env)
        if any(key not in _ALLOWED_ENV for key in environment):
            raise ValueError("worker environment contains a non-allowlisted key")
    return _run_process(
        argv, project, timeout=timeout, output_limit=output_limit,
        env=environment, input_data=input_data, separate_stderr=True,
    )

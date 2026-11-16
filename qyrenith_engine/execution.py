"""Shared bounded subprocess execution; this is not an operating-system sandbox."""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Union

_ALLOWED_ENV = {"PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "LANG", "LC_ALL", "PYTHONUNBUFFERED"}
_MAX_OUTPUT_BYTES = 8 * 1024 * 1024
_MAX_WORKER_INPUT_BYTES = 1024 * 1024


class _WindowsJob:
    """Contain a child process tree and terminate descendants when the job closes."""

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._wintypes = wintypes
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._ntdll = ctypes.WinDLL("ntdll")
        self._handle = wintypes.HANDLE()

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = self._kernel32
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        self._resume_process = self._ntdll.NtResumeProcess
        self._resume_process.argtypes = [wintypes.HANDLE]
        self._resume_process.restype = wintypes.LONG

        self._handle = kernel32.CreateJobObjectW(None, None)
        if not self._handle:
            raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")

        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = 0x00002000 | 0x00000008
        limits.BasicLimitInformation.ActiveProcessLimit = 64
        if not kernel32.SetInformationJobObject(
            self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "SetInformationJobObject failed")

    def assign_and_resume(self, process: subprocess.Popen) -> None:
        import ctypes

        process_handle = self._wintypes.HANDLE(int(process._handle))
        if not self._kernel32.AssignProcessToJobObject(self._handle, process_handle):
            raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed")
        status = self._resume_process(process_handle)
        if status < 0:
            raise OSError(status, "NtResumeProcess failed")

    def terminate_and_close(self) -> None:
        if not self._handle:
            return
        termination_error = None
        if not self._kernel32.TerminateJobObject(self._handle, 1):
            termination_error = OSError(
                self._ctypes.get_last_error(), "TerminateJobObject failed"
            )
        try:
            # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE remains the cleanup backstop.
            self.close()
        except OSError as close_error:
            if termination_error is not None:
                raise close_error from termination_error
            raise
        if termination_error is not None:
            raise termination_error

    def close(self) -> None:
        if self._handle:
            handle = self._handle
            if not self._kernel32.CloseHandle(handle):
                raise OSError(self._ctypes.get_last_error(), "CloseHandle(job) failed")
            self._handle = self._wintypes.HANDLE()


def _terminate_process_group(
    process: subprocess.Popen, windows_job: _WindowsJob | None = None
) -> None:
    """Stop the process tree using a Windows Job Object or POSIX process group."""
    try:
        if os.name == "nt":
            if windows_job is not None:
                windows_job.terminate_and_close()
            else:
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


def _environment_digest(environment: Mapping[str, str]) -> str:
    """Fingerprint non-secret effective environment values without returning them."""
    sensitive = re.compile(
        r"(?:TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|ACCESS[_-]?KEY|"
        r"PRIVATE[_-]?KEY|CREDENTIAL|AUTHORIZATION|COOKIE)",
        re.IGNORECASE,
    )
    safe = {
        key: value for key, value in environment.items()
        if not sensitive.search(key)
    }
    encoded = json.dumps(
        safe, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _decode_output(data: bytearray) -> str:
    """Decode captured text and normalize platform newline conventions to LF."""
    return bytes(data).decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")


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
    windows_job = None
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
        )
    else:
        kwargs["start_new_session"] = True

    started = time.monotonic()
    process = None
    try:
        if os.name == "nt":
            windows_job = _WindowsJob()
        process = subprocess.Popen(list(argv), **kwargs)
        if windows_job is not None:
            windows_job.assign_and_resume(process)
    except (OSError, ValueError, AttributeError) as exc:
        if windows_job is not None:
            try:
                windows_job.terminate_and_close()
            except OSError:
                pass
        if process is not None:
            try:
                process.kill()
                process.wait()
            except OSError:
                pass
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
            "environment_digest": _environment_digest(env),
        }

    assert process is not None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    totals = {"stdout": 0, "stderr": 0}
    captured_bytes = 0
    capture_lock = threading.Lock()
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
        _terminate_process_group(process, windows_job)

    def drain(stream, name: str) -> None:
        nonlocal captured_bytes
        read_chunk = getattr(stream, "read1", stream.read)
        try:
            while True:
                chunk = read_chunk(65536)
                if not chunk:
                    break
                totals[name] += len(chunk)
                nonlocal_capture_overflow = False
                with capture_lock:
                    remaining = max(0, output_limit - captured_bytes)
                    accepted = min(len(chunk), remaining)
                    if accepted:
                        buffers[name].extend(chunk[:accepted])
                        # The budget is shared by stdout and stderr, not per stream.
                        captured_bytes += accepted
                    nonlocal_capture_overflow = len(chunk) > remaining
                if nonlocal_capture_overflow:
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

    if windows_job is not None:
        try:
            windows_job.close()
        except OSError:
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
    stdout = _decode_output(buffers["stdout"])
    stderr = _decode_output(buffers["stderr"])
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
            "Windows Job Object process-tree containment and a 64-process cap; "
            "not filesystem/network isolation or a complete OS sandbox."
            if os.name == "nt"
            else "POSIX process-group cleanup and bounded capture; not an OS sandbox. "
            "Child code retains the invoking user's OS permissions."
        ),
        "environment_digest": _environment_digest(env),
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
        "stdout_bytes": report.get("stdout_bytes", report["output_bytes"]),
        "stderr_bytes": report.get("stderr_bytes", 0),
        "output_truncated": truncated,
        "output_incomplete": report["output_incomplete"],
        "input_incomplete": report.get("input_incomplete", False),
        "timed_out": report["timed_out"],
        "duration_seconds": report.get("duration_seconds", 0.0),
        "shell": False,
        "containment": report.get("containment", "Process-level controls only; not an OS sandbox."),
        "environment_digest": report.get("environment_digest", _environment_digest(env)),
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
    """Run a protocol worker with deadline-covered stdin and bounded output.

    Input is written by a dedicated thread so a worker that never reads stdin
    cannot block the controller before its timeout starts. Stdout and stderr are
    captured separately under one aggregate output budget. Output overflow kills
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

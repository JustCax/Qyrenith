"""Regression tests for bounded subprocess output accounting."""
from pathlib import Path
import os
import sys
import time
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from qyrenith_engine.execution import _WindowsJob, run_bounded_process, run_bounded_worker


class BoundedWorkerOutputTests(unittest.TestCase):
    def test_stdout_and_stderr_share_one_output_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            script = (
                "import os; "
                "os.write(1, b'o' * 256); "
                "os.write(2, b'e' * 256)"
            )
            report = run_bounded_worker(
                [sys.executable, "-c", script],
                project,
                b"",
                timeout=10,
                output_limit=256,
            )

        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(report["output_limited"])
        self.assertLessEqual(
            len(report["stdout"].encode("utf-8"))
            + len(report["stderr"].encode("utf-8")),
            256,
        )
        self.assertGreaterEqual(report["output_bytes"], 256)


class WindowsJobObjectTests(unittest.TestCase):
    def test_termination_api_failure_is_reported_after_close_fallback(self):
        job = _WindowsJob.__new__(_WindowsJob)
        job._handle = 123
        job._ctypes = SimpleNamespace(get_last_error=lambda: 5)
        job._kernel32 = SimpleNamespace(
            TerminateJobObject=lambda handle, exit_code: False
        )
        job.close = Mock()

        with self.assertRaisesRegex(OSError, "TerminateJobObject failed"):
            job.terminate_and_close()

        job.close.assert_called_once_with()

    @unittest.skipUnless(os.name == "nt", "Windows Job Object containment requires Windows")
    def test_descendant_is_terminated_when_root_process_exits(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = (
                "import subprocess,sys; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                "print(child.pid, flush=True)"
            )
            report = run_bounded_process(
                [sys.executable, "-c", script],
                Path(temporary),
                timeout=10,
                output_limit=1024,
            )

        self.assertEqual(report["status"], "PASS", report)
        child_pid = int(report["output"].strip())

        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)
        ]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        still_running = False
        for _ in range(30):
            handle = kernel32.OpenProcess(0x1000, False, child_pid)
            if not handle:
                still_running = False
                break
            try:
                exit_code = wintypes.DWORD()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    still_running = exit_code.value == 259
            finally:
                kernel32.CloseHandle(handle)
            if not still_running:
                break
            time.sleep(0.1)

        self.assertFalse(still_running, "Windows Job Object left a child process running")


if __name__ == "__main__":
    unittest.main()

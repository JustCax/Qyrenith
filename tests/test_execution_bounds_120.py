"""Regression tests for bounded subprocess output accounting."""
from pathlib import Path
import sys
import tempfile
import unittest

from qyrenith_engine.execution import run_bounded_worker


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


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta, timezone

from qyrenith_engine.qdas import (
    create_execution_event,
    create_repair_plan,
    diagnose_failure,
)


START = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)
FINISH = START + timedelta(seconds=1)


def event(output="ModuleNotFoundError: No module named 'fixture'"):
    return create_execution_event(
        {"status": "FAIL", "exit_code": 1, "duration_seconds": 1, "stdout": "", "stderr": output},
        project_id="repair-fixture",
        project_revision="git:repair",
        workspace_id="workspace-repair",
        event_kind="TEST",
        tool_name="fixture-tool",
        tool_version="1",
        argv=("fixture-tool",),
        working_directory=".",
        environment={},
        started_at=START,
        finished_at=FINISH,
    )


def hypothesis_for(
    item,
    output="ModuleNotFoundError: No module named 'fixture'",
):
    return diagnose_failure(item, stdout="", stderr=output)[0]


class QdasRepairPlanTests(unittest.TestCase):
    def test_creates_deterministic_propose_only_repair_plan(self):
        item = event()
        hypothesis = hypothesis_for(item)
        values = {
            "affected_paths": ("src/module.py", "tests/test_module.py"),
            "intended_change": "Restore the declared import path or dependency metadata after confirming the intended package boundary.",
            "expected_invariants": (
                "Existing tests remain unchanged and present.",
                "The declared runtime imports resolve in the pinned environment.",
            ),
            "risk": "MEDIUM",
            "required_permissions": ("READ_PROJECT", "WRITE_PROJECT", "EXECUTE_PROCESS"),
            "validation_commands": (
                ("python", "-m", "unittest", "tests.test_module"),
                ("python", "-m", "compileall", "src"),
            ),
            "rollback_strategy": "Discard the isolated proposal workspace and restore the exact source snapshot.",
            "created_at": START,
        }
        first = create_repair_plan(item, hypothesis, **values)
        second = create_repair_plan(item, hypothesis, **values)
        self.assertEqual(first.plan_id, second.plan_id)
        self.assertEqual(first.plan_digest, second.plan_digest)
        self.assertEqual(first.execution_mode, "PROPOSE_ONLY")
        self.assertTrue(first.human_review_required)
        self.assertEqual(first.affected_paths, ("src/module.py", "tests/test_module.py"))
        self.assertEqual(len(first.to_json_bytes()), len(first.to_json_bytes()))

    def test_rejects_hypothesis_from_another_event(self):
        item = event()
        other = event("SyntaxError: invalid syntax")
        other_hypothesis = hypothesis_for(other, "SyntaxError: invalid syntax")
        with self.assertRaisesRegex(ValueError, "different event"):
            create_repair_plan(
                item, other_hypothesis,
                affected_paths=("src/module.py",),
                intended_change="Inspect dependency metadata.",
                expected_invariants=("Existing tests remain unchanged.",),
                risk="LOW",
                validation_commands=(("python", "-m", "unittest"),),
                rollback_strategy="Discard the isolated proposal workspace.",
            )

    def test_rejects_plan_paths_that_escape_or_use_wildcards(self):
        item = event()
        hypothesis = hypothesis_for(item)
        for path in ("../outside.py", "/absolute/path.py", "src/*.py", "C:/outside.py"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    create_repair_plan(
                        item, hypothesis,
                        affected_paths=(path,),
                        intended_change="Inspect the affected source.",
                        expected_invariants=("Existing tests remain unchanged.",),
                        risk="LOW",
                        validation_commands=(("python", "-m", "unittest"),),
                        rollback_strategy="Discard the isolated proposal workspace.",
                    )

    def test_requires_explicit_expected_invariants(self):
        item = event()
        hypothesis = hypothesis_for(item)
        with self.assertRaisesRegex(ValueError, "expected_invariants"):
            create_repair_plan(
                item, hypothesis,
                affected_paths=("src/module.py",),
                intended_change="Inspect the import path.",
                expected_invariants=(),
                risk="LOW",
                validation_commands=(("python", "-m", "unittest"),),
                rollback_strategy="Discard the isolated proposal workspace.",
            )

    def test_requires_a_validation_command_and_rollback_strategy(self):
        item = event()
        hypothesis = hypothesis_for(item)
        with self.assertRaisesRegex(ValueError, "validation_commands"):
            create_repair_plan(
                item, hypothesis,
                affected_paths=("src/module.py",),
                intended_change="Inspect the import path.",
                expected_invariants=("Existing tests remain unchanged.",),
                risk="LOW",
                validation_commands=(),
                rollback_strategy="Discard the isolated proposal workspace.",
            )
        with self.assertRaisesRegex(ValueError, "rollback_strategy"):
            create_repair_plan(
                item, hypothesis,
                affected_paths=("src/module.py",),
                intended_change="Inspect the import path.",
                expected_invariants=("Existing tests remain unchanged.",),
                risk="LOW",
                validation_commands=(("python", "-m", "unittest"),),
                rollback_strategy="",
            )

    def test_rejects_non_command_string_sequence(self):
        item = event()
        hypothesis = hypothesis_for(item)
        with self.assertRaisesRegex(ValueError, "argument sequences"):
            create_repair_plan(
                item, hypothesis,
                affected_paths=("src/module.py",),
                intended_change="Inspect the import path.",
                expected_invariants=("Existing tests remain unchanged.",),
                risk="LOW",
                validation_commands=("python -m unittest",),
                rollback_strategy="Discard the isolated proposal workspace.",
            )

    def test_successful_event_cannot_receive_repair_plan(self):
        passed = create_execution_event(
            {"status": "PASS", "exit_code": 0, "duration_seconds": 0},
            project_id="repair-fixture",
            project_revision="git:repair",
            workspace_id="workspace-repair",
            event_kind="TEST",
            tool_name="fixture-tool",
            tool_version="1",
            argv=("fixture-tool",),
            working_directory=".",
            environment={},
            started_at=START,
            finished_at=FINISH,
        )
        with self.assertRaisesRegex(ValueError, "successful event"):
            create_repair_plan(
                passed,
                hypothesis_for(event()),
                affected_paths=("src/module.py",),
                intended_change="Fix something.",
                expected_invariants=("Tests remain unchanged.",),
                risk="LOW",
                validation_commands=(("python", "-m", "unittest"),),
                rollback_strategy="Discard the isolated proposal workspace.",
            )


if __name__ == "__main__":
    unittest.main()

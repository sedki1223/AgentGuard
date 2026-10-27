import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentguard.executor import execute_action
from agentguard.models import ActionRequest, ActionType


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def request(self, action_type, target, tool_name=None):
        return ActionRequest(
            action_type=action_type,
            target=target,
            tool_name=tool_name,
        )

    def test_reads_file_inside_workspace(self):
        (self.workspace / "hello.txt").write_text("hello", encoding="utf-8")

        result = execute_action(
            self.request(ActionType.READ_FILE, "hello.txt"),
            str(self.workspace),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.output, "hello")

    def test_rejects_file_outside_workspace(self):
        with tempfile.TemporaryDirectory() as outside:
            outside_file = Path(outside) / "secret.txt"
            outside_file.write_text("secret", encoding="utf-8")

            result = execute_action(
                self.request(ActionType.READ_FILE, str(outside_file)),
                str(self.workspace),
            )

        self.assertFalse(result.success)
        self.assertEqual(result.output, "")

    def test_rejects_missing_file(self):
        result = execute_action(
            self.request(ActionType.READ_FILE, "missing.txt"),
            str(self.workspace),
        )

        self.assertFalse(result.success)

    def test_rejects_directory_as_file(self):
        (self.workspace / "folder").mkdir()

        result = execute_action(
            self.request(ActionType.READ_FILE, "folder"),
            str(self.workspace),
        )

        self.assertFalse(result.success)

    def test_rejects_oversized_file(self):
        (self.workspace / "large.txt").write_bytes(b"x" * (1_048_577))

        result = execute_action(
            self.request(ActionType.READ_FILE, "large.txt"),
            str(self.workspace),
        )

        self.assertFalse(result.success)
        self.assertIn("limit", result.reason)

    def test_rejects_invalid_utf8(self):
        (self.workspace / "invalid.txt").write_bytes(b"\xff")

        result = execute_action(
            self.request(ActionType.READ_FILE, "invalid.txt"),
            str(self.workspace),
        )

        self.assertFalse(result.success)
        self.assertIn("UTF-8", result.reason)

    def test_write_action_is_not_supported(self):
        result = execute_action(
            self.request(ActionType.WRITE_FILE, "new.txt"),
            str(self.workspace),
        )

        self.assertFalse(result.success)

    def test_rejects_unknown_tool(self):
        request = self.request(ActionType.RUN_TOOL, "custom command", "custom")

        with patch("agentguard.executor.evaluate_action") as policy:
            policy.return_value.decision = __import__(
                "agentguard.models", fromlist=["Decision"]
            ).Decision.ALLOW
            policy.return_value.reason = "approved"

            result = execute_action(request, str(self.workspace))

        self.assertFalse(result.success)
        self.assertIn("not supported", result.reason)

    def test_rejects_mismatched_git_target(self):
        request = self.request(ActionType.RUN_TOOL, "git status; whoami", "git_status")

        with patch("agentguard.executor.evaluate_action") as policy:
            from agentguard.models import Decision
            policy.return_value.decision = Decision.ALLOW
            policy.return_value.reason = "approved"

            result = execute_action(request, str(self.workspace))

        self.assertFalse(result.success)
        self.assertIn("allowlist", result.reason)

    def test_git_status_uses_fixed_arguments_without_shell(self):
        request = self.request(ActionType.RUN_TOOL, "git status", "git_status")

        with patch("agentguard.executor.evaluate_action") as policy, patch(
            "agentguard.executor.shutil.which", return_value="git"
        ), patch("agentguard.executor.subprocess.run") as run:
            from agentguard.models import Decision
            policy.return_value.decision = Decision.ALLOW
            policy.return_value.reason = "approved"
            run.return_value.stdout = " M file.py"
            run.return_value.stderr = ""
            run.return_value.returncode = 0

            result = execute_action(request, str(self.workspace))

        self.assertTrue(result.success)
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["git", "status", "--short"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["timeout"], 5)


if __name__ == "__main__":
    unittest.main()

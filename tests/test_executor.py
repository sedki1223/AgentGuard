
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agentguard.executor import execute_action
from agentguard.models import ActionRequest, ActionType, Decision


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

    def allow_policy(self):
        policy = patch("agentguard.executor.evaluate_action")
        mocked = policy.start()
        self.addCleanup(policy.stop)
        mocked.return_value.decision = Decision.ALLOW
        mocked.return_value.reason = "approved"
        return mocked

    def mock_process(self, returncode=0):
        process = Mock()
        process.stdout = Mock()
        process.stdout.closed = False
        process.stderr = Mock()
        process.stderr.closed = False
        process.returncode = returncode
        process.poll.return_value = returncode
        process.wait.return_value = returncode
        return process

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
        (self.workspace / "large.txt").write_bytes(b"x" * 1_048_577)
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
        self.allow_policy()
        result = execute_action(
            self.request(ActionType.RUN_TOOL, "custom command", "custom"),
            str(self.workspace),
        )
        self.assertFalse(result.success)
        self.assertIn("not supported", result.reason)

    def test_file_read_is_bounded(self):
        path = self.workspace / "growing.txt"
        path.write_bytes(b"x")
        original_open = Path.open
        observed_sizes = []

        def controlled_open(target, *args, **kwargs):
            if target == path.resolve():

                class GrowingFile:
                    def __enter__(self):
                        self.file = original_open(target, *args, **kwargs)
                        return self

                    def __exit__(self, *exc):
                        return self.file.__exit__(*exc)

                    def read(self, size=-1):
                        observed_sizes.append(size)
                        return self.file.read(size)

                return GrowingFile()

            return original_open(target, *args, **kwargs)

        with patch.object(Path, "open", controlled_open):
            result = execute_action(
                self.request(ActionType.READ_FILE, "growing.txt"),
                str(self.workspace),
            )

        self.assertTrue(result.success)
        self.assertEqual(result.output, "x")
        self.assertEqual(observed_sizes, [1_048_577])

    def test_rejects_mismatched_git_target(self):
        self.allow_policy()
        result = execute_action(
            self.request(
                ActionType.RUN_TOOL, "git status; whoami", "git_status"
            ),
            str(self.workspace),
        )
        self.assertFalse(result.success)
        self.assertIn("allowlist", result.reason)

    def test_git_status_uses_fixed_arguments_without_shell(self):
        self.allow_policy()
        process = self.mock_process()

        with (
            patch("agentguard.executor.shutil.which", return_value="git"),
            patch(
                "agentguard.executor.subprocess.Popen",
                return_value=process,
            ) as popen,
            patch("agentguard.executor._drain_pipe"),
        ):
            result = execute_action(
                self.request(ActionType.RUN_TOOL, "git status", "git_status"),
                str(self.workspace),
            )

        self.assertTrue(result.success)
        args, kwargs = popen.call_args
        self.assertEqual(args[0], ["git", "status", "--short"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["stdout"], subprocess.PIPE)
        self.assertEqual(kwargs["stderr"], subprocess.PIPE)

    def test_git_missing(self):
        self.allow_policy()
        with patch("agentguard.executor.shutil.which", return_value=None):
            result = execute_action(
                self.request(ActionType.RUN_TOOL, "git status", "git_status"),
                str(self.workspace),
            )

        self.assertFalse(result.success)
        self.assertIn("not found", result.reason)

    def test_git_timeout(self):
        self.allow_policy()
        process = self.mock_process()
        poll_results = iter([None, None])
        process.poll.side_effect = lambda: next(poll_results, 0)

        with (
            patch("agentguard.executor.shutil.which", return_value="git"),
            patch(
                "agentguard.executor.subprocess.Popen",
                return_value=process,
            ),
            patch("agentguard.executor._drain_pipe"),
            patch(
                "agentguard.executor.time.monotonic",
                side_effect=[0, 10],
            ),
        ):
            result = execute_action(
                self.request(ActionType.RUN_TOOL, "git status", "git_status"),
                str(self.workspace),
            )

        self.assertFalse(result.success)
        self.assertIn("timed out", result.reason)

    def test_git_nonzero_exit_code(self):
        self.allow_policy()
        process = self.mock_process(returncode=128)

        with (
            patch("agentguard.executor.shutil.which", return_value="git"),
            patch(
                "agentguard.executor.subprocess.Popen",
                return_value=process,
            ),
            patch("agentguard.executor._drain_pipe"),
        ):
            result = execute_action(
                self.request(ActionType.RUN_TOOL, "git status", "git_status"),
                str(self.workspace),
            )

        self.assertFalse(result.success)
        self.assertEqual(result.reason, "Git operation failed")

    def test_git_output_limit(self):
        self.allow_policy()
        process = self.mock_process()

        def fake_drain(
            pipe, destination, output_lock, total_output, limit_reached
        ):
            with output_lock:
                remaining = 1_048_576 - total_output[0]
                if remaining > 0:
                    destination.extend(b"x" * remaining)
                    total_output[0] += remaining
                limit_reached.set()

        with (
            patch("agentguard.executor.shutil.which", return_value="git"),
            patch(
                "agentguard.executor.subprocess.Popen",
                return_value=process,
            ),
            patch(
                "agentguard.executor._drain_pipe",
                side_effect=fake_drain,
            ),
        ):
            result = execute_action(
                self.request(ActionType.RUN_TOOL, "git status", "git_status"),
                str(self.workspace),
            )

        self.assertFalse(result.success)
        self.assertIn("output exceeded", result.reason)
        self.assertLessEqual(len(result.output.encode("utf-8")), 1_048_576)


if __name__ == "__main__":
    unittest.main()

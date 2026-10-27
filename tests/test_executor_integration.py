import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentguard.executor import execute_action
from agentguard.models import ActionRequest, ActionType, Decision


class ExecutorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

        self.policy_patch = patch("agentguard.executor.evaluate_action")
        self.policy = self.policy_patch.start()
        self.addCleanup(self.policy_patch.stop)

        self.policy.return_value.decision = Decision.ALLOW
        self.policy.return_value.reason = "approved"

    def tearDown(self):
        self.temp_dir.cleanup()

    def request(self):
        return ActionRequest(
            action_type=ActionType.RUN_TOOL,
            target="git status",
            tool_name="git_status",
        )

    def run_python_process(self, code):
        with (
            patch(
                "agentguard.executor.shutil.which",
                return_value=sys.executable,
            ),
            patch.dict(
                "agentguard.executor.ALLOWED_EXECUTIONS",
                {"git_status": ("-c", code)},
            ),
        ):
            return execute_action(self.request(), str(self.workspace))

    def test_real_process_output_limit(self):
        code = (
            "import sys; "
            "sys.stdout.write('x' * 1200000); "
            "sys.stdout.flush()"
        )

        result = self.run_python_process(code)

        self.assertFalse(result.success)
        self.assertIn("output exceeded", result.reason)
        self.assertLessEqual(
            len(result.output.encode("utf-8")),
            1_048_576,
        )

    def test_real_process_timeout(self):
        started = time.monotonic()

        with patch("agentguard.executor.COMMAND_TIMEOUT_SECONDS", 0.25):
            result = self.run_python_process(
                "import time; time.sleep(15)"
            )

        elapsed = time.monotonic() - started

        self.assertFalse(result.success)
        self.assertIn("timed out", result.reason)
        self.assertLess(
            elapsed,
            3.0,
            f"Timeout handling took {elapsed:.2f}s instead of stopping promptly",
        )


if __name__ == "__main__":
    unittest.main()

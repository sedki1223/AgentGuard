import tempfile
import unittest
from pathlib import Path

from agentguard.models import ActionRequest, ActionType, Decision
from agentguard.policy import evaluate_action


class ActionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "README.md").write_text("AgentGuard", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def evaluate_read(self, target, workspace=None):
        return evaluate_action(
            ActionRequest(ActionType.READ_FILE, str(target)),
            workspace_root=str(workspace or self.workspace),
        )

    def test_read_file_inside_workspace_is_allowed(self):
        result = self.evaluate_read("README.md")
        self.assertEqual(result.decision, Decision.ALLOW)

    def test_path_traversal_is_blocked(self):
        result = self.evaluate_read("../secrets.txt")
        self.assertEqual(result.decision, Decision.BLOCK)

    def test_absolute_path_outside_workspace_is_blocked(self):
        outside = self.workspace.parent / "outside-secret.txt"
        result = self.evaluate_read(outside)
        self.assertEqual(result.decision, Decision.BLOCK)

    def test_missing_file_is_blocked(self):
        result = self.evaluate_read("missing.txt")
        self.assertEqual(result.decision, Decision.BLOCK)

    def test_directory_is_not_a_readable_file(self):
        result = self.evaluate_read(".")
        self.assertEqual(result.decision, Decision.BLOCK)

    def test_nonexistent_workspace_is_blocked(self):
        missing_workspace = self.workspace / "does-not-exist"
        result = self.evaluate_read("README.md", workspace=missing_workspace)
        self.assertEqual(result.decision, Decision.BLOCK)

    def test_symlink_escape_is_blocked(self):
        outside = self.workspace.parent / "outside-secret.txt"
        outside.write_text("secret", encoding="utf-8")
        link = self.workspace / "external-link.txt"

        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic link creation is unavailable on this system")

        result = self.evaluate_read("external-link.txt")
        self.assertEqual(result.decision, Decision.BLOCK)

    def test_write_file_requires_approval(self):
        result = evaluate_action(
            ActionRequest(ActionType.WRITE_FILE, "notes.txt"),
            workspace_root=str(self.workspace),
        )
        self.assertEqual(result.decision, Decision.REQUIRE_APPROVAL)

    def test_unknown_tool_requires_approval(self):
        result = evaluate_action(
            ActionRequest(
                ActionType.RUN_TOOL,
                "inspect repository",
                tool_name="unknown_tool",
            ),
            workspace_root=str(self.workspace),
        )
        self.assertEqual(result.decision, Decision.REQUIRE_APPROVAL)

    def test_invalid_request_object_is_blocked(self):
        result = evaluate_action(
            "not an action request",
            workspace_root=str(self.workspace),
        )

        self.assertEqual(result.decision, Decision.BLOCK)
        self.assertEqual(result.reason, "Invalid action request")

    def test_empty_target_is_blocked(self):
        result = evaluate_action(
            ActionRequest(ActionType.READ_FILE, "   "),
            workspace_root=str(self.workspace),
        )

        self.assertEqual(result.decision, Decision.BLOCK)
        self.assertEqual(result.reason, "Target must be a non-empty string")

    def test_invalid_action_type_is_blocked(self):
        result = evaluate_action(
            ActionRequest("read_file", "README.md"),
            workspace_root=str(self.workspace),
        )

        self.assertEqual(result.decision, Decision.BLOCK)
        self.assertEqual(result.reason, "Unknown action type")

if __name__ == "__main__":
    unittest.main()

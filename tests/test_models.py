import unittest
from dataclasses import FrozenInstanceError

from agentguard.models import (
    ActionRequest,
    ActionType,
    Decision,
    PolicyDecision,
)


class ModelTests(unittest.TestCase):
    def test_read_file_request(self):
        request = ActionRequest(ActionType.READ_FILE, "README.md")

        self.assertEqual(request.action_type, ActionType.READ_FILE)
        self.assertEqual(request.target, "README.md")
        self.assertIsNone(request.tool_name)

    def test_run_tool_request(self):
        request = ActionRequest(
            ActionType.RUN_TOOL,
            "git status",
            tool_name="git_status",
        )

        self.assertEqual(request.action_type, ActionType.RUN_TOOL)
        self.assertEqual(request.tool_name, "git_status")

    def test_policy_decision_has_reason(self):
        result = PolicyDecision(
            Decision.REQUIRE_APPROVAL,
            "No policy rule matched",
        )

        self.assertEqual(result.decision, Decision.REQUIRE_APPROVAL)
        self.assertTrue(result.reason)

    def test_request_fields_cannot_be_reassigned(self):
        request = ActionRequest(ActionType.READ_FILE, "README.md")

        with self.assertRaises(FrozenInstanceError):
            request.target = "other.txt"


if __name__ == "__main__":
    unittest.main()

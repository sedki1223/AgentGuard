import unittest

from agentguard.policy import Decision, evaluate_command


class PolicyTests(unittest.TestCase):
    def test_explicitly_allowed_command(self):
        self.assertEqual(evaluate_command("git status"), Decision.ALLOW)

    def test_allowed_command_with_trailing_whitespace(self):
        self.assertEqual(evaluate_command("git status "), Decision.ALLOW)

    def test_known_dangerous_command(self):
        self.assertEqual(evaluate_command("shutdown /s"), Decision.BLOCK)

    def test_unknown_command_requires_approval(self):
        self.assertEqual(
            evaluate_command("some-unknown-command"),
            Decision.REQUIRE_APPROVAL,
        )

    def test_empty_command_is_blocked(self):
        self.assertEqual(evaluate_command(""), Decision.BLOCK)

    def test_chained_command_requires_approval(self):
        self.assertEqual(
            evaluate_command("git status; python --version"),
            Decision.REQUIRE_APPROVAL,
        )

    def test_pipe_requires_approval(self):
        self.assertEqual(
            evaluate_command("git status | more"),
            Decision.REQUIRE_APPROVAL,
        )

    def test_command_substitution_requires_approval(self):
        self.assertEqual(
            evaluate_command("git status $(shutdown /s)"),
            Decision.REQUIRE_APPROVAL,
        )


if __name__ == "__main__":
    unittest.main()

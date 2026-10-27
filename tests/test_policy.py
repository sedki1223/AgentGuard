
import unittest

from agentguard.models import Decision
from agentguard.policy import evaluate_command


class PolicyTests(unittest.TestCase):
    def test_explicitly_allowed_command(self):
        self.assertEqual(evaluate_command("git status"), Decision.ALLOW)

    def test_allowed_command_with_trailing_whitespace(self):
        self.assertEqual(evaluate_command("git status "), Decision.ALLOW)

    def test_allowed_command_is_case_insensitive(self):
        self.assertEqual(evaluate_command("GIT STATUS"), Decision.ALLOW)

    def test_known_dangerous_command(self):
        self.assertEqual(evaluate_command("shutdown /s"), Decision.BLOCK)

    def test_dangerous_command_with_mixed_case_is_blocked(self):
        self.assertEqual(evaluate_command("ShUtDoWn /s"), Decision.BLOCK)

    def test_dangerous_command_with_leading_whitespace_is_blocked(self):
        self.assertEqual(evaluate_command("  shutdown /s"), Decision.BLOCK)

    def test_dangerous_command_with_extra_arguments_is_blocked(self):
        self.assertEqual(
            evaluate_command("rmdir /s /q temp"),
            Decision.BLOCK,
        )

    def test_unknown_command_requires_approval(self):
        self.assertEqual(
            evaluate_command("some-unknown-command"),
            Decision.REQUIRE_APPROVAL,
        )

    def test_empty_command_is_blocked(self):
        self.assertEqual(evaluate_command(""), Decision.BLOCK)

    def test_whitespace_only_command_is_blocked(self):
        self.assertEqual(evaluate_command("   "), Decision.BLOCK)

    def test_non_string_command_is_blocked(self):
        self.assertEqual(evaluate_command(None), Decision.BLOCK)

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

    def test_redirection_requires_approval(self):
        self.assertEqual(
            evaluate_command("git status > output.txt"),
            Decision.REQUIRE_APPROVAL,
        )

    def test_ampersand_requires_approval(self):
        self.assertEqual(
            evaluate_command("git status & python --version"),
            Decision.REQUIRE_APPROVAL,
        )

    def test_dangerous_command_after_semicolon_is_blocked(self):
        self.assertEqual(
            evaluate_command("git status; shutdown /s"),
            Decision.BLOCK,
        )

    def test_dangerous_command_after_pipe_is_blocked(self):
        self.assertEqual(
            evaluate_command("git status | shutdown /s"),
            Decision.BLOCK,
        )

    def test_dangerous_command_after_ampersand_is_blocked(self):
        self.assertEqual(
            evaluate_command("git status & rmdir /s /q temp"),
            Decision.BLOCK,
        )


if __name__ == "__main__":
    unittest.main()

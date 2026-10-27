import json
import tempfile
import unittest
from pathlib import Path

from agentguard.json_interface import evaluate_json


class JsonInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "README.md").write_text(
            "AgentGuard",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def evaluate(self, payload):
        output = evaluate_json(payload, str(self.workspace))
        return json.loads(output)

    def test_existing_file_returns_allow(self):
        result = self.evaluate(
            '{"action_type":"read_file","target":"README.md"}'
        )
        self.assertEqual(result["decision"], "allow")
        self.assertIn("executor checks", result["reason"])

    def test_write_file_requires_approval(self):
        result = self.evaluate(
            '{"action_type":"write_file","target":"notes.txt"}'
        )
        self.assertEqual(result["decision"], "require_approval")

    def test_invalid_json_returns_block(self):
        result = self.evaluate("not json")
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "Input must be valid JSON")

    def test_json_array_returns_block(self):
        result = self.evaluate("[]")
        self.assertEqual(result["decision"], "block")

    def test_unknown_action_type_returns_block(self):
        result = self.evaluate(
            '{"action_type":"delete_everything","target":"data"}'
        )
        self.assertEqual(result["decision"], "block")

    def test_missing_target_returns_block(self):
        result = self.evaluate('{"action_type":"read_file"}')
        self.assertEqual(result["decision"], "block")

    def test_non_string_target_returns_block(self):
        result = self.evaluate(
            '{"action_type":"read_file","target":123}'
        )
        self.assertEqual(result["decision"], "block")

    def test_unsupported_field_returns_block(self):
        result = self.evaluate(
            '{"action_type":"read_file","target":"README.md",'
            '"execute":true}'
        )
        self.assertEqual(result["decision"], "block")

    def test_path_traversal_returns_block(self):
        result = self.evaluate(
            '{"action_type":"read_file","target":"../secret.txt"}'
        )
        self.assertEqual(result["decision"], "block")

    def test_unknown_tool_requires_approval(self):
        result = self.evaluate(
            '{"action_type":"run_tool","target":"do something",'
            '"tool_name":"unknown_tool"}'
        )
        self.assertEqual(result["decision"], "require_approval")


if __name__ == "__main__":
    unittest.main()

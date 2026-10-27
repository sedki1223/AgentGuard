import json
import sys
from pathlib import Path
from typing import Any

from agentguard.models import ActionRequest, ActionType
from agentguard.policy import evaluate_action


def evaluate_json(payload: str, workspace_root: str) -> str:
    """Evaluate a JSON action request without executing it."""
    try:
        data: Any = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({
            "decision": "block",
            "reason": "Input must be valid JSON",
        })

    if not isinstance(data, dict):
        return json.dumps({
            "decision": "block",
            "reason": "Input must be a JSON object",
        })

    allowed_fields = {"action_type", "target", "tool_name"}
    if set(data) - allowed_fields:
        return json.dumps({
            "decision": "block",
            "reason": "Input contains unsupported fields",
        })

    action_type_value = data.get("action_type")
    target = data.get("target")
    tool_name = data.get("tool_name")

    if not isinstance(action_type_value, str):
        return json.dumps({
            "decision": "block",
            "reason": "action_type must be a string",
        })

    if not isinstance(target, str) or not target.strip():
        return json.dumps({
            "decision": "block",
            "reason": "target must be a non-empty string",
        })

    if tool_name is not None and not isinstance(tool_name, str):
        return json.dumps({
            "decision": "block",
            "reason": "tool_name must be a string when provided",
        })

    try:
        action_type = ActionType(action_type_value)
        request = ActionRequest(
            action_type=action_type,
            target=target,
            tool_name=tool_name,
        )
    except (ValueError, TypeError):
        return json.dumps({
            "decision": "block",
            "reason": "Invalid action request",
        })

    result = evaluate_action(request, workspace_root)

    return json.dumps({
        "decision": result.decision.value,
        "reason": result.reason,
    })


def main() -> None:
    """Read one JSON request from stdin and print its policy decision."""
    payload = sys.stdin.read()
    result = evaluate_json(payload, str(Path.cwd()))
    print(result)


if __name__ == "__main__":
    main()

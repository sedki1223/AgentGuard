
import re
from pathlib import Path

from agentguard.models import ActionRequest, ActionType, Decision, PolicyDecision


DANGEROUS_COMMANDS = {
    "format",
    "rmdir",
    "del",
    "remove-item",
    "shutdown",
    "restart-computer",
    "stop-computer",
}

ALLOWED_COMMANDS = {
    "git status",
    "git diff",
    "python --version",
    "py --version",
}

ALLOWED_TOOLS = {
    "git_status": "git status",
    "git_diff": "git diff",
}

SHELL_SYNTAX = re.compile(r"[;&|<>`$()]")


def evaluate_command(command: str) -> Decision:
    """Classify a command without executing it."""
    if not isinstance(command, str) or not command.strip():
        return Decision.BLOCK

    normalized = command.strip().lower()

    if SHELL_SYNTAX.search(normalized):
        return Decision.REQUIRE_APPROVAL

    first_token = normalized.split(maxsplit=1)[0]

    if first_token in DANGEROUS_COMMANDS:
        return Decision.BLOCK

    if normalized in ALLOWED_COMMANDS:
        return Decision.ALLOW

    return Decision.REQUIRE_APPROVAL


def evaluate_action(
    request: ActionRequest,
    workspace_root: str,
) -> PolicyDecision:
    """Evaluate a structured action without performing it."""
    if not isinstance(request, ActionRequest):
        return PolicyDecision(Decision.BLOCK, "Invalid action request")

    if not isinstance(request.action_type, ActionType):
        return PolicyDecision(Decision.BLOCK, "Unknown action type")

    if not isinstance(request.target, str) or not request.target.strip():
        return PolicyDecision(Decision.BLOCK, "Target must be a non-empty string")

    try:
        root = Path(workspace_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        return PolicyDecision(Decision.BLOCK, "Workspace root is invalid")

    if not root.is_dir():
        return PolicyDecision(Decision.BLOCK, "Workspace root is not a directory")

    if request.action_type == ActionType.READ_FILE:
        try:
            target = Path(request.target)

            if not target.is_absolute():
                target = root / target

            resolved_target = target.resolve(strict=True)
            resolved_target.relative_to(root)

            if not resolved_target.is_file():
                return PolicyDecision(
                    Decision.BLOCK,
                    "Read target is not an existing regular file",
                )

        except (OSError, RuntimeError, TypeError, ValueError):
            return PolicyDecision(
                Decision.BLOCK,
                "Read target is outside the workspace or invalid",
            )

        return PolicyDecision(
            Decision.ALLOW,
            "Existing file resolves inside the workspace; executor checks are still required",
        )

    if request.action_type == ActionType.WRITE_FILE:
        return PolicyDecision(
            Decision.REQUIRE_APPROVAL,
            "File writes require explicit approval in this prototype",
        )

    if request.action_type == ActionType.RUN_TOOL:
        expected_target = ALLOWED_TOOLS.get(request.tool_name)

        if expected_target is None:
            return PolicyDecision(
                Decision.REQUIRE_APPROVAL,
                "Tool is not on the predefined allowlist",
            )

        if request.target.strip().lower() != expected_target:
            return PolicyDecision(
                Decision.REQUIRE_APPROVAL,
                "Target does not match the predefined tool operation",
            )

        return PolicyDecision(
            Decision.ALLOW,
            "Tool and target match the predefined operation; executor validation is still required",
        )

    return PolicyDecision(Decision.BLOCK, "Unsupported action type")

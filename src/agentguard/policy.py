import re
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


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

SHELL_SYNTAX = re.compile(r"[;&|<>`$()]")


def evaluate_command(command: str) -> Decision:
    """Classify a command without executing it."""
    if not command or not command.strip():
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

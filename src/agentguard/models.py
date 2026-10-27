from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    RUN_TOOL = "run_tool"


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class ActionRequest:
    action_type: ActionType
    target: str
    tool_name: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str

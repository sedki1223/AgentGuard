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

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            raise TypeError("action_type must be an ActionType")

        if not isinstance(self.target, str):
            raise TypeError("target must be a string")

        if not self.target.strip():
            raise ValueError("target must not be empty")

        if self.tool_name is not None:
            if not isinstance(self.tool_name, str):
                raise TypeError("tool_name must be a string or None")

            if not self.tool_name.strip():
                raise ValueError("tool_name must not be empty")


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision, Decision):
            raise TypeError("decision must be a Decision")

        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string")

        if not self.reason.strip():
            raise ValueError("reason must not be empty")

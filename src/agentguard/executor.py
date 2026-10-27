
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentguard.models import ActionRequest, ActionType, Decision
from agentguard.policy import evaluate_action


MAX_READ_BYTES = 1_048_576
COMMAND_TIMEOUT_SECONDS = 5

ALLOWED_EXECUTIONS = {
    "git_status": ("status", "--short"),
    "git_diff": ("diff", "--no-ext-diff", "--"),
}


@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    output: str
    reason: str


def execute_action(
    request: ActionRequest,
    workspace_root: str,
) -> ExecutionResult:
    """Execute a narrow set of operations after independent validation."""
    if not isinstance(request, ActionRequest):
        return ExecutionResult(False, "", "Invalid action request")

    try:
        root = Path(workspace_root).resolve(strict=True)
        if not root.is_dir():
            return ExecutionResult(False, "", "Workspace root is not a directory")
    except (OSError, RuntimeError, TypeError, ValueError):
        return ExecutionResult(False, "", "Workspace root is invalid")

    policy_result = evaluate_action(request, str(root))
    if policy_result.decision != Decision.ALLOW:
        return ExecutionResult(
            False,
            "",
            f"Policy rejected execution: {policy_result.reason}",
        )

    if request.action_type == ActionType.READ_FILE:
        return _read_file(request.target, root)

    if request.action_type == ActionType.RUN_TOOL:
        return _run_allowed_tool(request, root)

    return ExecutionResult(False, "", "Requested action is not supported")


def _read_file(target: str, root: Path) -> ExecutionResult:
    """Read a bounded UTF-8 file after checking its resolved location."""
    try:
        path = Path(target)
        if not path.is_absolute():
            path = root / path

        resolved = path.resolve(strict=True)
        resolved.relative_to(root)

        if not resolved.is_file():
            return ExecutionResult(False, "", "Target is not a regular file")

        if resolved.stat().st_size > MAX_READ_BYTES:
            return ExecutionResult(False, "", "File exceeds the 1 MiB read limit")

        with resolved.open("rb") as file:
            content = file.read(MAX_READ_BYTES + 1)

        if len(content) > MAX_READ_BYTES:
            return ExecutionResult(False, "", "File exceeds the 1 MiB read limit")

        return ExecutionResult(
            True,
            content.decode("utf-8"),
            "File read successfully",
        )

    except UnicodeDecodeError:
        return ExecutionResult(False, "", "File is not valid UTF-8")
    except (OSError, RuntimeError, TypeError, ValueError):
        return ExecutionResult(
            False,
            "",
            "Read target is outside the workspace or invalid",
        )


def _run_allowed_tool(
    request: ActionRequest,
    root: Path,
) -> ExecutionResult:
    """Run fixed argument lists without invoking a shell."""
    if request.tool_name not in ALLOWED_EXECUTIONS:
        return ExecutionResult(False, "", "Tool is not supported by the executor")

    expected_target = {
        "git_status": "git status",
        "git_diff": "git diff",
    }[request.tool_name]

    if request.target.strip().lower() != expected_target:
        return ExecutionResult(False, "", "Tool target does not match its allowlist")

    git_executable = shutil.which("git")
    if git_executable is None:
        return ExecutionResult(False, "", "Git executable was not found")

    arguments = [git_executable, *ALLOWED_EXECUTIONS[request.tool_name]]

    try:
        completed = subprocess.run(
            arguments,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(False, "", "Tool execution timed out")
    except OSError:
        return ExecutionResult(False, "", "Tool execution failed")

    output = completed.stdout + completed.stderr

    if completed.returncode != 0:
        return ExecutionResult(False, output, "Git operation failed")

    return ExecutionResult(True, output, "Git operation completed successfully")


import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from agentguard.models import ActionRequest, ActionType, Decision
from agentguard.policy import evaluate_action


MAX_READ_BYTES = 1_048_576
MAX_TOOL_OUTPUT_BYTES = 1_048_576
COMMAND_TIMEOUT_SECONDS = 5
PROCESS_TERMINATION_GRACE_SECONDS = 0.5
OUTPUT_CHUNK_BYTES = 8192

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


def _terminate_process(process: subprocess.Popen) -> None:
    """Terminate and reap the direct child, escalating to kill if necessary."""
    if process.poll() is not None:
        return

    try:
        process.terminate()
    except OSError:
        pass

    try:
        process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass

        try:
            process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass


def _drain_pipe(
    pipe: BinaryIO,
    destination: bytearray,
    output_lock: threading.Lock,
    total_output: list[int],
    output_limit_reached: threading.Event,
) -> None:
    """Drain a pipe while retaining no more than the shared output budget."""
    try:
        while True:
            chunk = pipe.read(OUTPUT_CHUNK_BYTES)
            if not chunk:
                break

            with output_lock:
                remaining = MAX_TOOL_OUTPUT_BYTES - total_output[0]
                accepted = min(len(chunk), max(remaining, 0))

                if accepted:
                    destination.extend(chunk[:accepted])
                    total_output[0] += accepted

                if accepted < len(chunk):
                    output_limit_reached.set()
    except (OSError, ValueError):
        pass
    finally:
        try:
            pipe.close()
        except OSError:
            pass


def _run_allowed_tool(
    request: ActionRequest,
    root: Path,
) -> ExecutionResult:
    """Run fixed Git arguments without a shell and with bounded output."""
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

    popen_options = {
        "cwd": str(root),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "shell": False,
    }

    # On Windows, create a new process group so future process-tree
    # containment can be added without changing the command allowlist.
    if os.name == "nt":
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        process = subprocess.Popen(arguments, **popen_options)
    except OSError:
        return ExecutionResult(False, "", "Tool execution failed")

    if process.stdout is None or process.stderr is None:
        _terminate_process(process)
        return ExecutionResult(False, "", "Tool output pipes could not be created")

    stdout_data = bytearray()
    stderr_data = bytearray()
    output_lock = threading.Lock()
    total_output = [0]
    output_limit_reached = threading.Event()

    stdout_thread = threading.Thread(
        target=_drain_pipe,
        args=(
            process.stdout,
            stdout_data,
            output_lock,
            total_output,
            output_limit_reached,
        ),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_pipe,
        args=(
            process.stderr,
            stderr_data,
            output_lock,
            total_output,
            output_limit_reached,
        ),
        daemon=True,
    )

    stdout_thread.start()
    stderr_thread.start()

    deadline = time.monotonic() + COMMAND_TIMEOUT_SECONDS
    timed_out = False

    try:
        while process.poll() is None:
            if output_limit_reached.is_set():
                _terminate_process(process)
                break

            if time.monotonic() >= deadline:
                timed_out = True
                _terminate_process(process)
                break

            time.sleep(0.01)
    finally:
        if process.poll() is None:
            _terminate_process(process)

        # Closing the read ends helps unblock readers if a descendant
        # inherited a pipe and keeps it open after the direct child exits.
        for pipe in (process.stdout, process.stderr):
            if pipe is not None and not pipe.closed:
                try:
                    pipe.close()
                except OSError:
                    pass

        stdout_thread.join(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
        stderr_thread.join(timeout=PROCESS_TERMINATION_GRACE_SECONDS)

    output = (
        stdout_data.decode("utf-8", errors="replace")
        + stderr_data.decode("utf-8", errors="replace")
    )

    if timed_out:
        return ExecutionResult(False, output, "Tool execution timed out")

    if output_limit_reached.is_set():
        return ExecutionResult(
            False,
            output,
            "Tool output exceeded the 1 MiB limit",
        )

    if stdout_thread.is_alive() or stderr_thread.is_alive():
        return ExecutionResult(
            False,
            output,
            "Tool output could not be collected safely",
        )

    if process.returncode != 0:
        return ExecutionResult(False, output, "Git operation failed")

    return ExecutionResult(True, output, "Git operation completed successfully")

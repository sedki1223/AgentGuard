# AgentGuard — Security Architecture

## Goal

Build a policy enforcement layer for actions proposed by AI coding agents.

## Core principles

1. Evaluate structured actions rather than arbitrary shell strings.
2. Default to requiring approval when a request is not explicitly permitted.
3. Separate policy decisions from action execution.
4. Never treat a policy decision alone as proof that execution is safe.
5. Record the action, decision, reason, and execution outcome for auditing.

## Proposed action types

- ReadFile: read a file within an authorized workspace.
- WriteFile: write to an explicitly authorized destination.
- RunTool: invoke a named, predefined tool with validated arguments.

## Trust boundaries

- Agent requests are untrusted input.
- Policy evaluation must validate action types and parameters.
- The executor must independently enforce workspace and operating-system restrictions.
- Arbitrary shell execution is outside the initial MVP scope.

## Initial limitations

The current implementation classifies command strings only.
It does not execute commands or enforce a security boundary.
The existing policy is a prototype and is not production-secure.

## Next milestone

Define typed action requests and structured policy decisions,
then test the policy independently before implementing a restricted executor.


## Restricted Executor

AgentGuard includes a restricted executor that performs a narrow set of
operations after policy evaluation.

### Supported operations

- Read UTF-8 files located inside the configured workspace.
- Limit file reads to 1 MiB.
- Run predefined Git operations:
  - `git status --short`
  - `git diff --no-ext-diff --`

### Execution safeguards

- Structured action requests are checked by the policy engine before execution.
- File targets are resolved and checked against the workspace root.
- File reads are bounded to 1 MiB plus one byte, allowing oversized content
  to be rejected without reading the entire file.
- Git operations use predefined argument lists and `shell=False`.
- Git execution has a five-second timeout.
- Subprocess output is decoded as UTF-8, replacing invalid byte sequences.
- Unsupported tools and write operations are rejected.

### Limitations

This executor is a prototype, not a security sandbox.

Path resolution and subsequent file access are separate operations, so
filesystem changes between those operations may create race conditions.
The executor also does not provide operating-system-level isolation,
resource quotas, or a general defense against malicious processes.

Captured Git output is not currently bounded, so a command that produces
very large output could consume significant memory. A production version
would need stronger resource controls and OS-level isolation.

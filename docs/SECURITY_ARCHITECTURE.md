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

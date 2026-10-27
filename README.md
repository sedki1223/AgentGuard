# AgentGuard

**A prototype policy layer for AI coding-agent actions.**

AgentGuard evaluates proposed actions and returns a structured decision:
`ALLOW`, `BLOCK`, or `REQUIRE_APPROVAL`. It is designed to explore how an
AI coding agent's requests can be checked before a separate executor performs
any operation.

> **Security status:** This is an educational prototype, not a production
> security boundary. AgentGuard does not execute actions, and a policy
> decision alone cannot guarantee that an operation is safe.

## Why AgentGuard?

AI coding agents can propose actions that read files, modify a workspace,
or invoke tools. Those requests should not automatically be trusted.

AgentGuard explores a policy-first design with:

- Typed action requests and structured policy decisions.
- Explicit decisions with human-readable reasons.
- Workspace-boundary checks for existing files requested for reading.
- An allowlist for a small set of predefined tool operations.
- Conservative handling of writes and unrecognized tool requests.
- Automated tests for policy behavior and selected edge cases.

## Current capabilities

| Action | Current behavior |
| --- | --- |
| Read an existing file inside the workspace | `ALLOW`, if the resolved path passes the policy checks |
| Read a missing file, directory, or path outside the workspace | `BLOCK` |
| Write a file | `REQUIRE_APPROVAL` |
| Invoke a predefined tool with a matching target | `ALLOW`, subject to the policy's checks |
| Invoke an unknown tool or mismatched target | `REQUIRE_APPROVAL` |
| Classify a known dangerous command | `BLOCK` |
| Classify a command outside the explicit allowlist | Usually `REQUIRE_APPROVAL`; known dangerous commands are blocked |

These are policy classifications, not execution guarantees. In particular,
the command classifier is a lightweight string-based prototype, not a
complete shell parser.

## Project structure

```text
AgentGuard/
├── docs/
│   └── SECURITY_ARCHITECTURE.md
├── src/
│   └── agentguard/
│       ├── __init__.py
│       ├── models.py
│       └── policy.py
└── tests/
    ├── test_action_policy.py
    ├── test_models.py
    └── test_policy.py
```

## Requirements

- Python 3.10 or newer
- Git

The project currently uses Python's standard library for its implementation
and tests.

## Set up locally

Clone the repository and enter its directory:

```powershell
git clone https://github.com/sedki1223/AgentGuard.git
cd AgentGuard
```

Create and activate a virtual environment on Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

No third-party packages are currently required to run the test suite.

## Run the tests

```powershell
python -m unittest discover -s tests -v
```

The test suite covers model validation, workspace path checks, tool-policy
decisions, and command-classification behavior.

## Example

Evaluate a proposed action without executing it:

```python
from pathlib import Path

from agentguard.models import ActionRequest, ActionType
from agentguard.policy import evaluate_action

workspace = Path.cwd()

request = ActionRequest(
    action_type=ActionType.READ_FILE,
    target="README.md",
)

result = evaluate_action(
    request,
    workspace_root=str(workspace),
)

print(result.decision.value)
print(result.reason)
```

For this example, `README.md` must exist in the current workspace. The result
describes the policy's decision; it does not read or execute the requested
operation on behalf of an agent.

To run the example from the repository root before installing the package,
set the source directory on `PYTHONPATH` in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -c "from pathlib import Path; from agentguard.models import ActionRequest, ActionType; from agentguard.policy import evaluate_action; r = evaluate_action(ActionRequest(ActionType.READ_FILE, 'README.md'), str(Path.cwd())); print(r.decision.value); print(r.reason)"
```

## Security boundaries and limitations

AgentGuard is not production-secure and should not be used as the sole
protection for untrusted code or AI-generated actions.

- It does not execute commands or file operations.
- The command classifier does not fully parse shell syntax or cover every
  platform, interpreter, alias, or command equivalent.
- A resolved-path check does not by itself prevent time-of-check/time-of-use
  races or all filesystem attacks.
- A future executor must independently validate arguments and enforce
  operating-system permissions and workspace restrictions.
- Approval workflows, execution isolation, and audit logging of real
  execution outcomes are not implemented as a complete end-to-end system.

See [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) for the
design principles and trust boundaries.

## Roadmap

- [x] Typed action requests and structured policy decisions
- [x] Initial workspace and tool-policy checks
- [x] Automated tests for core policy behavior
- [ ] Add a user-facing policy evaluation interface
- [ ] Define a restricted executor with independent validation
- [ ] Add execution audit records and end-to-end tests
- [ ] Strengthen platform-specific security testing

## License

No license has been added yet. Until one is chosen and committed, reuse and
redistribution permissions should not be assumed.

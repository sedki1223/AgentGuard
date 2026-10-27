# AgentGuard

**A prototype policy layer for AI coding-agent actions.**

AgentGuard evaluates proposed actions and returns one of three decisions: `ALLOW`, `BLOCK`, or `REQUIRE_APPROVAL`.

It evaluates policy only. It does not execute commands or perform file operations.

## Features

- Typed action requests and structured policy decisions.
- Workspace-boundary checks for existing files requested for reading.
- Approval requirements for file writes.
- An allowlist for predefined tool operations.
- Conservative command classification.
- A JSON interface for machine-readable policy evaluation.
- Automated tests for policy behavior and invalid inputs.

## Current policy behavior

| Action                                              | Decision                   |
| --------------------------------------------------- | -------------------------- |
| Read an existing file inside the workspace          | `ALLOW`                    |
| Read a missing file or a path outside the workspace | `BLOCK`                    |
| Write a file                                        | `REQUIRE_APPROVAL`         |
| Invoke an allowlisted tool with its expected target | `ALLOW`                    |
| Invoke an unknown tool or use a mismatched target   | `REQUIRE_APPROVAL`         |
| Classify a known dangerous command                  | `BLOCK`                    |
| Classify an unrecognized command                    | Usually `REQUIRE_APPROVAL` |

These decisions are classifications, not execution guarantees. The command classifier is a lightweight prototype, not a complete shell parser.

## Project structure

```text
AgentGuard/
├── docs/
│   └── SECURITY_ARCHITECTURE.md
├── src/
│   └── agentguard/
│       ├── __init__.py
│       ├── json_interface.py
│       ├── models.py
│       └── policy.py
└── tests/
    ├── test_action_policy.py
    ├── test_json_interface.py
    ├── test_models.py
    └── test_policy.py
```

## Requirements

- Python 3.10 or newer
- Git

The project uses Python's standard library and requires no third-party packages.

## Setup

Clone the repository:

```powershell
git clone https://github.com/sedki1223/AgentGuard.git
cd AgentGuard
```

Create and activate a virtual environment on Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Set the source directory:

```powershell
$env:PYTHONPATH = "src"
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## JSON interface

The JSON interface reads one JSON request from standard input and prints a structured policy decision. It does not execute the requested action.

Example:

```powershell
$env:PYTHONPATH = "src"
@'
{"action_type":"read_file","target":"README.md"}
'@ | python -m agentguard.json_interface
```

Example response:

```json
{
  "decision": "allow",
  "reason": "Existing file resolves inside the workspace; executor checks are still required"
}
```

Supported action types:

- `read_file` — checks whether an existing file resolves inside the workspace.
- `write_file` — requires approval.
- `run_tool` — checks a predefined tool name and its expected target.

Malformed JSON, unsupported fields, and invalid requests return a `block` decision with a reason.

The interface uses the current working directory as its workspace root. Run it from the intended workspace.

## Python API

```python
from pathlib import Path

from agentguard.models import ActionRequest, ActionType
from agentguard.policy import evaluate_action

request = ActionRequest(
    action_type=ActionType.READ_FILE,
    target="README.md",
)

result = evaluate_action(request, workspace_root=str(Path.cwd()))

print(result.decision.value)
print(result.reason)
```

The example assumes `README.md` exists in the current workspace. The policy engine evaluates the request but does not read the file.

## Security limitations

AgentGuard is an educational prototype, not a production security boundary.

- It does not execute commands or file operations.
- Its command classifier does not fully parse shell syntax or detect every dangerous command equivalent.
- Path resolution alone does not prevent all filesystem attacks or time-of-check/time-of-use races.
- Any future executor must independently validate arguments and enforce operating-system permissions and workspace restrictions.
- Approval workflows, execution isolation, and complete audit logging are not implemented.
- An `ALLOW` decision is not proof that an operation is safe.

See [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) for the design principles and trust boundaries.

## Roadmap

- [x] Typed action requests and structured policy decisions
- [x] Workspace and tool-policy checks
- [x] Automated tests for core policy behavior
- [x] JSON policy evaluation interface
- [ ] Build a restricted executor with independent validation
- [ ] Add execution audit records and end-to-end tests
- [ ] Strengthen platform-specific security testing

## License

No license has been added yet. Until one is chosen and committed, reuse and redistribution permissions should not be assumed.

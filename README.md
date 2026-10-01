# WaxPrep

WaxPrep is a general-purpose computer agent.

The project is in early construction. The core idea is simple: the AI is the brain, while the real runtime and computer environment provide the hands through which the agent can act.

## Current Foundation

- Language: Python
- Runtime: Python 3.14.x
- Package/project manager: uv
- Project manifest: `pyproject.toml`

The architecture is intentionally being developed in stages. Application-specific behavior is not being added during this foundation phase.

## Repository Layout

- `src/` — source code will live here as the agent is built.
- `tests/` — automated tests will live here as testable capabilities are introduced.
- `docs/` — supporting project documentation will live here when documentation is needed.

## Development Checks

WaxPrep uses Ruff for formatting and linting, and mypy for static type checking.

Run the individual checks with:

```text
make format
make lint
make typecheck
```

The commands are intentionally kept simple so every later development stage uses the same quality checks.

## Development Rule

Each project stage should make only the changes required for that stage.

A stage is not considered complete until its intended changes have been verified and committed.

See `CONTRIBUTING.md` for the repository's basic contribution and commit conventions.

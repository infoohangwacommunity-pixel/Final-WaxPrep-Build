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

The standard local verification command is:

```text
make check
```

It runs, in order:

1. Ruff formatting verification (check only; does not rewrite files)
2. Ruff linting
3. mypy strict type checking
4. the complete unittest suite

Make stops if an earlier step fails. The GitHub Quality Gate uses the same `make check` for core verification, then runs package import validation and a dependency vulnerability audit.

Individual commands remain available when needed:

```text
make format
make lint
make typecheck
make test
```

## Development Rule

Each project stage should make only the changes required for that stage.

A stage is not considered complete until its intended changes have been verified and committed.

See `CONTRIBUTING.md` for the repository's basic contribution and commit conventions.

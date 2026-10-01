# Contributing to WaxPrep

WaxPrep is being built incrementally. Keep changes focused on the current stage and do not build future architecture ahead of its corresponding prompt.

## Commit Messages

Use a short, clear prefix describing the kind of change:

- `feat:` — new capability
- `fix:` — bug correction
- `docs:` — documentation
- `test:` — tests
- `refactor:` — structural code change without changing intended behavior
- `chore:` — project maintenance

Examples:

- `feat: add process execution primitive`
- `docs: record runtime decision`
- `test: verify workspace lifecycle`

## Secrets and Configuration

Real secrets must never be committed to the repository.

Secrets may only come from:

1. Environment variables provided to the runtime.
2. A secrets file stored outside the repository.

The following rules apply:

- `.env` files are ignored by Git.
- `.env.example` may contain variable names, comments, and fake placeholder values only.
- Real API keys, passwords, access tokens, database credentials, and similar secrets must never be placed in source code.
- Secrets must never be printed in logs, error messages, tests, or command output.
- Future capabilities should introduce their configuration variables only when those capabilities are actually built.
- Do not invent provider-specific credentials before the corresponding integration exists.

## Stage Completion

Every stage ends with a verified commit.

Before considering a stage complete:

1. Inspect the resulting repository.
2. Run the available project checks.
3. Confirm only intended files changed.
4. Confirm the requested behavior or structure.
5. Commit the verified result.

Do not claim a stage is complete without evidence.

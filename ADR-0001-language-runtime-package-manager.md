# ADR-0001: Language, Runtime, and Package Manager

- Status: Accepted
- Date: 2026-10-01

## Decision

Waza's core runtime will use:

- Language: Python
- Runtime: Python 3.14.x
- Package/project manager: uv
- Project manifest: `pyproject.toml`

The project will target Python 3.14 and will not depend on a second primary programming language for the core agent runtime.

## Why Python

Waza is a general-purpose computer agent.

Its core runtime will eventually need to:

- start and control processes
- work with files and directories
- interact with the operating system
- communicate over networks
- handle asynchronous work
- consume and stream model output
- execute long-running agent sessions
- observe real-world execution results
- remain understandable and maintainable by the project owner and future developers

Python provides a strong combination of operating-system access, asynchronous programming, networking, testing, typing support, and AI/LLM ecosystem support.

Python is also appropriate for the project's goal of keeping the core agent understandable rather than spreading the system across multiple language ecosystems.

## Why not TypeScript

TypeScript and Node.js are capable choices for agent systems, particularly for web services and streaming applications.

They were not selected as Waza's core language because the project is primarily a computer agent rather than a web application. Python provides a simpler single-language foundation for the operating-system, process, filesystem, networking, and AI-facing work Waza is expected to perform.

This does not prohibit TypeScript or JavaScript from being used in a future isolated component if a concrete requirement justifies it.

## Why not JavaScript

JavaScript without TypeScript was rejected for the same architectural reason as TypeScript, with the additional disadvantage of weaker compile-time type guarantees for a system expected to contain substantial state, process, filesystem, and execution logic.

Waza should not introduce a second language merely because a particular ecosystem is convenient.

## Why Python 3.14

Python 3.14 is the current stable feature series as of this decision.

The currently verified maintenance release is Python 3.14.8, released September 30, 2026.

Waza therefore targets:

    >=3.14,<3.15

The project targets the 3.14 feature series rather than a single patch release so that normal security and bug-fix releases within that series can be adopted without changing the project's language decision.

## Why uv

uv is the selected Python project and package manager.

It will eventually provide project environment management, dependency management, locking, and Python-version management.

Using one project tool avoids mixing multiple package-management systems.

The currently verified uv release is 0.12.21.

The repository does not yet declare runtime dependencies because this phase establishes the foundation only.

## Version Policy

Python:

    >=3.14,<3.15

uv:

    0.12.x series

At the time of this decision:

- Python 3.14.8 is the current 3.14 maintenance release.
- uv 0.12.21 is the current verified uv release.

Patch releases may advance within the selected major/minor series when appropriate.

## Project Manifest Policy

The initial `pyproject.toml` must remain intentionally minimal.

It may contain only the project identity, version, license placeholder, and Python runtime requirement required by this phase.

Dependencies, application packages, build configuration, scripts, and agent code will be introduced by later prompts when they are actually required.

## Hosting

Hosting is deliberately not part of this decision.

Waza is expected to run on a hosted environment such as Railway or another suitable platform later.

The application should therefore be designed around its runtime contract rather than around the developer's personal machine.

Hosting infrastructure will be decided in a later phase.

## Rejected Alternatives

### TypeScript + pnpm

Rejected as the core runtime because it would make Node.js/TypeScript the foundation for a system whose primary concern is general computer control rather than web application development.

### JavaScript + npm

Rejected because it provides no compelling advantage over TypeScript for this system and offers weaker type safety.

### Python + pip

Rejected as the primary project-management choice because uv provides a more integrated project workflow for the direction chosen here.

### Multiple core languages

Rejected because it would increase complexity, tooling requirements, testing surface, and maintenance cost before there is a concrete need.

## Consequence

Waza now has one clear foundation:

Python → Python 3.14 → uv → `pyproject.toml`

Future prompts should build on this decision rather than reopening the language choice unless new evidence creates a genuine architectural reason to reconsider it.

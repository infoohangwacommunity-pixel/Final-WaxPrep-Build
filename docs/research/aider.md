# Aider Research Notes

## Purpose

This document records architectural observations from Aider's current public repository and documentation.

WaxPrep is studying Aider for reusable ideas only. Aider is a coding-focused product with many features that should not be imported into WaxPrep's general foundation.

## Repository studied

- **Project:** Aider
- **Repository:** https://github.com/Aider-AI/aider
- **Primary areas:** repository mapping, context selection, chat history, repository state, extensibility.

**Key source locations:**

- `aider/repomap.py`
- `aider/coders/base_coder.py`
- `aider/history.py`
- `aider/repo.py`
- `aider/main.py`
- `aider/website/docs/repomap.md`

## 1. Agent loop

Aider is primarily an interactive coding assistant rather than a general autonomous runtime.

Its `Coder` owns the current coding conversation, model, files in context, repository map, commands, summarizer, lint/test configuration, and Git integration.

The useful cycle is:

1. Receive a user request.
2. Assemble model context.
3. Ask the model for a coding response.
4. Parse the response according to the selected edit format.
5. Apply edits or commands.
6. Optionally lint/test.
7. Report the result and continue.

Aider's strongest research value for WaxPrep is context management rather than its complete coding loop.

## 2. Repository map

Aider builds a concise map of the repository containing important files and symbols, including definitions and call signatures.

Its implementation in `aider/repomap.py`:

1. Collects candidate files.
2. Parses source with Tree-sitter.
3. Extracts definitions and references.
4. Builds a file/identifier relationship graph.
5. Personalizes relevance using files and identifiers mentioned in the current chat.
6. Ranks the graph with PageRank.
7. Selects definitions until a token budget is reached.
8. Formats the result as a compact map.

It also caches parsed tags and reuses them when file modification times have not changed.

The repo map is therefore a structural, source-aware summary—not a semantic database.

## 3. Context strategy

Aider separates:

- active conversation messages
- explicitly added editable files
- read-only files
- repository map
- mentioned files/identifiers
- Git/repository information
- optional command/URL/image context

The broad pattern is:

**compact structural context first → identify relevant areas → load detailed files when needed.**

The map is token-budgeted and can expand when no files have yet been added, because the model then needs a wider view.

This is useful to study without making it a mandatory WaxPrep retrieval subsystem.

## 4. Chat history and compaction

Aider can persist chat history to `.aider.chat.history.md`, input history to `.aider.input.history`, and optionally log LLM history.

Its `ChatSummary` mechanism counts message tokens and, when history becomes too large:

1. keeps a recent tail,
2. summarizes older messages,
3. combines summary + tail,
4. recursively summarizes if still too large.

Aider also summarizes old messages when switching edit formats when necessary, because old assistant-format output could confuse the new mode.

This reinforces the distinction between durable conversation history and the context actually sent to the model.

## 5. State and persistence

The active state is mainly in the `Coder` and related objects: current files, read-only files, messages, repo map, commands, Git state, token/cost counters, lint/test state, edit format, and model configuration.

Durable state includes chat/history files, repository-map cache, and Git repository state.

This differs from OpenHands' event-sourced physical history: Aider is centered on an interactive coding session plus Git as a durable code-change record.

## 6. Execution and real-world truth

Aider can edit files, run commands, lint, test, and commit.

Its Git integration bases commits on the actual repository diff, and its lint/test features inspect real results after edits.

Useful principle for WaxPrep:

**the world result—not the model's claim—is evidence that an operation happened.**

The Git-centric implementation itself should not be generalized beyond coding.

## 7. Extensibility

Aider extends its core through:

- models/providers
- edit formats
- in-chat commands
- configurable lint/test commands
- repository-map language support
- configuration files
- model metadata/settings
- Git integration

These are product extensions around the core, not proof that the core should become a catalogue of future capabilities.

## 8. Complexity to avoid

WaxPrep should not copy:

- coding-specific edit formats
- Git commit/attribution workflow
- Tree-sitter query catalogue
- PageRank implementation wholesale
- provider compatibility layer
- terminal UI
- coding-specific lint/test repair
- product analytics/configuration

## 9. What WaxPrep should learn

1. Provide a compact structural view when a world is too large for context.
2. Use current conversation signals to make broad context more relevant.
3. Separate broad structure from detailed content loading.
4. Treat context size as a managed resource.
5. Preserve recent context while summarizing older conversation.
6. Cache expensive structural analysis when inputs are unchanged.
7. Treat actual filesystem/Git/test observations as reality.

## 10. What WaxPrep should not copy

Aider's repository map, PageRank, Tree-sitter, edit formats, Git workflow, lint/test automation, provider machinery, and terminal UX should not become mandatory WaxPrep architecture.

## Research status

Verified against Aider's current public repository and public documentation during Prompt 13 research.

No Aider source code is copied into WaxPrep.

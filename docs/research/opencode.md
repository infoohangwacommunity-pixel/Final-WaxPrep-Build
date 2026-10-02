# OpenCode Research Notes

## Purpose

This document records architectural observations from the current public OpenCode repository and its current V2 session specification.

WaxPrep is studying OpenCode for patterns and ideas only. This is not a proposal to copy OpenCode or adopt its complete architecture.

## Repository studied

- **Project:** OpenCode
- **Repository:** https://github.com/anomalyco/opencode
- **Important current source areas:** `packages/opencode/`, `packages/core/`, and `specs/v2/`

The research focused on the session runner, durable prompt admission, provider turns, tool execution, permissions, context epochs, compaction, and skills.

## 1. Session model

OpenCode treats the session as the durable container for ongoing work.

The current V2 design separates several stages that are often incorrectly treated as one operation:

1. a client submits input
2. the input is durably admitted
3. the session runner receives the session
4. the input becomes visible conversation history
5. a provider turn executes
6. tools may execute
7. results are persisted
8. the runner continues or finishes

This means:

**message received ≠ message processed**

and:

**session ≠ single model call**

### Important source locations

- `specs/v2/session.md`
- `packages/opencode/src/session/`
- `packages/opencode/src/session/prompt.ts`

## 2. Durable prompt admission

The V2 session design introduces a durable admission step for incoming prompts.

An admitted prompt can remain queued before becoming part of model-visible conversation history.

The simplified flow is:

**client input → durable admission → runner → promotion into visible history → model processing**

This is useful for asynchronous agents because the system can distinguish an input that was received from an input that has actually been processed.

It also makes queued work recoverable after interruption.

### Important source location

- `specs/v2/session.md`

## 3. Provider turns

OpenCode's runner performs explicit provider turns.

A turn has a stable execution context while it is running.

Changes such as model or agent selection can be admitted at safe boundaries rather than changing the meaning of an already-running provider turn.

This provides a useful rule:

**a running turn should operate against a stable execution context.**

### Important source locations

- `specs/v2/session.md`
- `packages/opencode/src/session/prompt.ts`

## 4. Tool execution lifecycle

OpenCode's V2 design pays particular attention to durable tool execution.

Important tool calls can be recorded before execution begins.

The runner then starts execution, waits for started operations, records their settlement, reloads the resulting history, and continues.

If the process dies while a local tool is still marked as running, the next execution can recognize the abandoned operation and record that it was interrupted rather than silently replaying it or pretending it succeeded.

This establishes a strong lifecycle:

**projected → running → settled**

with interruption represented explicitly.

### Important source location

- `specs/v2/session.md`

## 5. Commands and patches

OpenCode has explicit tools for operations such as shell execution and file editing.

The `apply_patch` implementation demonstrates a useful separation.

It:

1. receives structured patch input
2. parses the patch
3. validates the affected files
4. resolves paths
5. checks external-directory authority
6. calculates the proposed changes
7. asks for the appropriate edit permission
8. applies the changes
9. emits filesystem events
10. updates related language-server state
11. reports the actual result

The important principle is:

**a proposed edit is not the same thing as an executed edit.**

### Important source location

- `packages/opencode/src/tool/apply_patch.ts`

## 6. Permission model

OpenCode has a dedicated permission system rather than making each tool independently responsible for all authorization decisions.

The V2 permission model supports effects such as:

- allow
- ask
- deny

Rules can be associated with actions and resources/patterns.

This allows the system to distinguish:

- what the tool wants to do
- whether policy allows it
- whether human approval is required

The tool then performs the operation only after the permission boundary has been satisfied.

### Important source locations

- `specs/v2/session.md`
- `packages/core/src/permission/`
- `packages/core/src/tool/`
- `packages/core/src/plugin/agent.ts`

## 7. Permission complexity to avoid

OpenCode's permission architecture is useful as a model of separation, but WaxPrep should not copy its entire implementation.

WaxPrep should not prematurely introduce:

- the complete OpenCode permission ruleset
- every tool-specific permission type
- its full plugin permission system
- its V2 compatibility machinery
- its complete permission UI/API surface

The reusable lesson is:

**authorization belongs between the agent's requested action and the runtime's physical execution.**

## 8. Context epochs

OpenCode V2 introduces a concept called a Context Epoch.

In practical terms, an epoch represents a stable baseline of context available to the model at a particular stage of a session.

The context can include things such as:

- environment facts
- host-local date
- project instructions
- selected-agent guidance
- available skills

When context changes, the runner can admit that change at a safe provider-turn boundary and represent it as chronological system context.

This avoids silently changing the meaning of an already-running turn.

### Important source location

- `specs/v2/session.md`

## 9. Context compaction

OpenCode separates durable history from the model-visible context used after compaction.

When context becomes too large, the system can:

1. preserve the durable transcript
2. identify older material for compaction
3. retain a recent tail of useful context
4. summarize older context
5. store the completed compaction result
6. rebuild the model-visible context
7. continue the original session

The compaction system also supports deterministic pruning of old tool outputs independently from the main summary.

This is important because a tool may have produced a very large output that is no longer useful to the model even though the fact that the tool ran remains part of the durable history.

### Important source locations

- `packages/opencode/src/session/compaction.ts`
- `packages/core/src/session/compaction.ts`
- `specs/v2/session.md`

## 10. Structured compaction

The current OpenCode compaction prompt asks for a structured continuation summary covering concepts such as:

- objective
- important details
- completed work
- active work
- blocked work
- next move
- relevant files

The exact format is an OpenCode implementation detail.

The more general lesson is:

**a useful compaction should preserve the state needed to continue the task, not merely produce a shorter transcript.**

WaxPrep should eventually design its own representation rather than copy OpenCode's exact summary template.

## 11. Full history versus current model context

OpenCode makes the distinction explicit:

**durable transcript ≠ active model representation**

The full history can remain available while the current model request uses a compacted representation containing the important older context plus recent turns.

This reinforces a principle already identified in OpenHands and Codex research.

The model does not need to be shown every byte that the system has ever recorded.

## 12. Skills

OpenCode provides a skill mechanism through which reusable instructions/capabilities can be loaded for the model.

The skill tool is a separate capability from the core session loop.

Skills can therefore provide additional guidance without requiring the fundamental session runner to contain application-specific decision trees.

This is potentially useful for WaxPrep later.

However, skills should remain supporting capabilities and guidance. The model should still decide when they are relevant.

### Important source locations

- `packages/core/src/tool/skill.ts`
- `packages/core/src/plugin/skill/`

## 13. Runtime failure and recovery

The V2 session design strongly emphasizes not losing the relationship between durable history and physical execution.

If a tool is left in an unfinished state after a process interruption, the system can settle that abandoned operation as interrupted rather than silently executing it again.

This is a valuable principle for any long-running agent:

**recovery should reconstruct reality, not invent success.**

## 14. What WaxPrep should borrow

1. Treat a session as a durable container for ongoing work.
2. Distinguish input admission from actual model processing.
3. Treat provider turns as explicit execution units.
4. Keep the execution context stable during a turn.
5. Record important tool lifecycle transitions durably.
6. Represent interrupted execution explicitly.
7. Keep permission enforcement separate from tool implementation.
8. Keep durable history separate from current model context.
9. Compact old context while preserving continuation-critical information.
10. Treat reusable skills as external guidance/capability rather than hardcoded application logic.
11. Rebuild state from actual recorded execution rather than assuming an abandoned action succeeded.

## 15. What WaxPrep should skip

WaxPrep should not copy:

- OpenCode's complete TypeScript/Effect architecture
- its V2 session implementation wholesale
- its Context Epoch implementation
- its entire database/event system
- its permission framework in full
- its complete tool catalogue
- its plugin architecture
- its TUI/client architecture
- its provider-specific implementation
- its exact compaction format
- coding-agent-specific behaviors
- compatibility layers that exist only because OpenCode is evolving an existing production system

The goal is to extract the architectural principles, not reproduce OpenCode.

## Research status

Verified against the current public OpenCode repository and its current V2 session specification during Prompt 12 research.

No OpenCode source code is copied into WaxPrep.

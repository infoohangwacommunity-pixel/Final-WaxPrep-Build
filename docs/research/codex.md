# OpenAI Codex Research Notes

## Purpose

This document records architectural observations from the current public OpenAI Codex repository.

WaxPrep is studying Codex for patterns and ideas only. This is not a proposal to copy Codex or adopt its complete architecture.

## Repository studied

- **Project:** OpenAI Codex
- **Repository:** https://github.com/openai/codex
- **Primary implementation studied:** `codex-rs/`

The current repository contains a substantial Rust workspace covering the core agent/session implementation, execution, configuration, history/state, tools, skills, app-server interfaces, permissions, patch application, protocol, and client-facing components.

The research for this document focuses on the parts relevant to session/turn structure, execution, lifecycle, permissions, context compaction, and skills.

## 1. Session and turn model

Codex distinguishes a longer-lived session/thread from an individual turn.

A useful simplified model is:

**session → user submission → turn → model/execution cycle → turn completion → session continues**

A single turn may involve multiple model decisions and multiple execution steps before the turn is complete.

This means a turn should not be treated as synonymous with an entire session.

### Important source locations

- `codex-rs/core/src/session/mod.rs`
- `codex-rs/core/src/state/session.rs`
- `codex-rs/core/src/session/step_settings.rs`
- `codex-rs/core/src/protocol.rs` and related protocol definitions

## 2. The execution cycle

The core agent behavior repeatedly connects model output to real execution.

A simplified representation is:

1. The session provides the current state and history.
2. The model receives the current model-visible context.
3. The model requests an action or command.
4. The action passes through execution and permission checks.
5. The runtime executes the permitted operation.
6. The result is captured.
7. The result becomes information available to the next model step.
8. The session continues until the current turn completes or execution terminates.

The important architectural boundary is:

**model request → permission/execution boundary → real runtime → observed result**

The model's requested action is not treated as proof that execution succeeded.

### Important source locations

- `codex-rs/core/src/session/mod.rs`
- `codex-rs/core/src/tools/handlers/`
- `codex-rs/core/src/exec_policy.rs`
- `codex-rs/exec/src/lib.rs`

## 3. Commands and patch execution

Codex separates the request to modify the world from the mechanism that actually performs the modification.

Command execution is handled through dedicated execution infrastructure.

File changes can also pass through a patch/application mechanism rather than being treated as implicit model behavior.

The general pattern is:

**model proposes change → executor validates/authorizes → filesystem/runtime changes → result returned**

This is useful for WaxPrep because it reinforces the rule that intelligence proposes actions while the world/runtime performs them.

## 4. Permission and approval model

Codex has multiple layers around execution authority.

Relevant concepts include:

- approval policy
- permission profiles
- filesystem sandbox policy
- network configuration
- environment policy
- workspace roots
- shell environment policy
- platform-specific sandbox settings

The execution approval request contains information about the command together with approval and permission policy.

This creates several distinct states:

- the model requested an action
- the policy allows or blocks it
- the user may need to approve it
- the runtime attempts it
- the runtime reports the actual result

These should not be collapsed into one state.

### Important source locations

- `codex-rs/core/src/exec_policy.rs`
- `codex-rs/core/src/config/mod.rs`
- `codex-rs/config/src/config_toml.rs`
- `codex-rs/prompts/src/permissions_instructions.rs`
- `codex-rs/core/src/context/world_state/permissions.rs`

## 5. Permission complexity to avoid

Codex's permission system is designed for a mature computer-use product and therefore contains significantly more policy machinery than WaxPrep currently needs.

WaxPrep should not copy:

- Codex's complete permission-profile system
- its platform-specific sandbox machinery
- its network policy implementation
- its approval UX
- its entire execution-policy language

The reusable lesson is simply:

**permissions belong at the boundary between intelligence and physical execution.**

## 6. Session state and history

Codex has explicit session state and history infrastructure.

The session state can expose token usage and other current session information, while history/rollout records preserve the events and information needed to continue or inspect a run.

This provides an important distinction:

- current session state describes where the session is now
- history records what has happened

The model-facing context is then assembled from the information needed for the next decision rather than being identical to every durable record.

### Important source locations

- `codex-rs/core/src/state/session.rs`
- `codex-rs/history/`
- `codex-rs/core/src/session/`

## 7. Context compaction

Codex has dedicated automatic compaction behavior.

Configuration includes:

- model context-window information
- automatic compaction token threshold
- scope for the compaction threshold
- post-turn compaction controls

The compaction subsystem advances through conversation/history windows so a long-running session can continue without requiring the entire historical context to remain in the active model request.

The general pattern is:

**large context → determine that compaction is needed → compact older context → preserve enough continuity → continue the same session**

Compaction therefore manages model context without being equivalent to deleting the durable session itself.

### Important source locations

- `codex-rs/core/src/compact.rs`
- `codex-rs/config/src/config_toml.rs`
- `codex-rs/core/src/config/mod.rs`

## 8. Why compaction matters for WaxPrep

A long-lived agent may eventually have a large amount of physical history.

The agent must distinguish:

- everything that physically happened
- information required for the next decision

WaxPrep should preserve durable history while allowing the model-facing representation to become smaller when context limits require it.

The important lesson is not Codex's exact compaction algorithm.

The lesson is:

**context management should preserve session continuity rather than silently turning a long-running agent into a new agent.**

## 9. Skills

Codex has a dedicated skills subsystem.

Relevant concepts include:

- skill metadata
- skill roots
- skill loading
- loaded skills
- skill policies
- plugin-provided skill roots

Skills provide a way to package reusable guidance/capabilities separately from the fundamental agent loop.

This is potentially useful for WaxPrep later because domain guidance can remain outside the general agent foundation.

### Important source locations

- `codex-rs/skills/src/lib.rs`
- `codex-rs/skills/src/loading.rs`
- `codex-rs/core-plugins/src/loader.rs`

## 10. Important lifecycle lesson

Codex's architecture reinforces several different lifecycle states around execution.

An operation can be:

- requested
- waiting for approval
- approved
- executing
- completed
- failed
- interrupted

WaxPrep should eventually be able to represent important physical lifecycle transitions without inventing a successful result when the runtime did not actually produce one.

This is especially important for long-running or asynchronous environments.

## 11. What WaxPrep should borrow

1. Treat a session as longer-lived than an individual turn.
2. Allow a turn to contain multiple model/action/execution cycles.
3. Keep requested actions separate from actual execution.
4. Put permission checks at the physical execution boundary.
5. Preserve durable session/history separately from the model's current context.
6. Design context compaction as continuation of the same session, not destruction and restart.
7. Treat execution lifecycle states as real information.
8. Keep reusable skills/guidance outside the fundamental agent loop.
9. Let actual runtime results, rather than model assumptions, determine what happened.

## 12. What WaxPrep should skip

WaxPrep should not copy:

- Codex's complete Rust workspace
- Codex's full product/client architecture
- its complete permission and sandbox subsystem
- its platform-specific security machinery
- its full tool catalogue
- its plugin ecosystem
- its multi-agent/product-specific infrastructure
- its TUI/application architecture
- its exact compaction implementation
- its provider-specific behavior
- coding-agent-specific workflows

The goal is to learn the architectural boundaries, not reproduce Codex.

## Research status

Verified against the current public OpenAI Codex repository during Prompt 12 research.

No Codex source code is copied into WaxPrep.

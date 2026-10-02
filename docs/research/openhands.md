# OpenHands Research Notes

## Purpose

This document records architectural observations from the current public OpenHands Software Agent SDK repository.

WaxPrep is studying OpenHands for patterns and ideas only. This is not a proposal to copy OpenHands or adopt its complete architecture.

## Repository studied

- **Project:** OpenHands Software Agent SDK
- **Repository:** https://github.com/OpenHands/software-agent-sdk

The repository currently describes itself as a modular SDK for building agents and says it owns agents, tools, conversations, workspaces, events, the Agent Server API, and typed client access to that API.

The repository also explicitly separates its responsibilities from related OpenHands repositories such as Agent Canvas and automation.

## 1. Agent loop

The central execution pattern is a repeated conversation/agent step.

A conversation runs repeatedly until it reaches an appropriate terminal condition. The conversation's `run()` method invokes the agent's `step()` method for each iteration.

Inside an agent step:

1. The agent obtains the current conversation state.
2. It prepares the messages that should be sent to the language model from the current state view.
3. It calls the language model.
4. The model response is classified.
5. If the response contains tool calls, those calls are converted into typed `ActionEvent` objects.
6. Actions are checked for blocking/confirmation requirements.
7. Allowed actions are executed against the workspace/tools.
8. Execution produces observations or error events.
9. Those events are emitted into the conversation.
10. The conversation continues from the updated state and observations.

This is a concrete implementation of:

**model decision → action → real execution → observation → next model decision.**

### Important source locations

- `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py` — `run()`, `_run()`, `send_message()`
- `openhands-sdk/openhands/sdk/agent/agent.py` — `step()`, `_step()`, `_execute_actions()`, `_execute_action_event()`
- `openhands-sdk/openhands/sdk/agent/response_dispatch.py` — conversion of model tool calls into action events

## 2. State

OpenHands separates conversation state from the event history.

`ConversationState` contains the current state of a conversation, including:

- conversation ID
- agent configuration
- workspace
- persistence directory
- execution status
- confirmation policy
- security analyzer
- activated skills/rules
- blocked actions/messages
- event-tree head
- conversation statistics
- secret registry
- user-defined tags

The agent itself is also persisted so that conversations can be resumed with knowledge of the agent configuration.

This gives a useful distinction:

- **State** answers: *where is the conversation now?*
- **Event history** answers: *what happened during the conversation?*

### Important source location

- `openhands-sdk/openhands/sdk/conversation/state.py`

## 3. Events and physical history

OpenHands represents important transitions as typed events.

The event system includes, among other types:

- user/message events
- system prompt events
- action events
- observation events
- agent error events
- pause/interrupt/state-related events

The important action/observation pair is:

**`ActionEvent` → actual execution → `ObservationEvent`**

An `ActionEvent` identifies the tool, tool-call ID, action, and originating LLM response.

An `ObservationEvent` identifies the tool and tool call it answers, and contains the structured observation returned by execution.

Errors can also become explicit events rather than being treated as successful execution.

### Important source locations

- `openhands-sdk/openhands/sdk/event/base.py`
- `openhands-sdk/openhands/sdk/event/llm_convertible/action.py`
- `openhands-sdk/openhands/sdk/event/llm_convertible/observation.py`

## 4. Persistent event log

OpenHands has an `EventLog` that persists events through its file-storage abstraction.

The current implementation provides:

- indexed event access
- event-ID lookup
- persistent disk storage
- locking for concurrent/process-safe writes
- event caching
- synchronization with disk
- parent/child relationships between events

The event log therefore acts as a durable record of what happened, rather than only an in-memory list.

The current implementation also supports an event tree. New events may identify their parent event, allowing conversation branches to be represented without destroying the previous branch.

This is useful as a research pattern for WaxPrep's future session/history model.

### Important source location

- `openhands-sdk/openhands/sdk/conversation/event_store.py`

## 5. Action and observation typing

OpenHands has a base `Action` schema and a base `Observation` schema.

Actions represent structured inputs to tools.

Observations represent structured outputs from tools.

The observation schema supports content and explicitly records whether the result represents an error.

This creates a clear boundary:

- AI asks for an action.
- The runtime/tool produces an observation.
- The two are not treated as the same thing.

This is useful for WaxPrep because it reinforces the rule that a requested action is not proof that the action succeeded.

### Important source location

- `openhands-sdk/openhands/sdk/tool/schema.py`

## 6. Workspace/environment abstraction

OpenHands defines `BaseWorkspace` as an abstraction for the environment where agent operations happen.

The workspace is responsible for general capabilities such as:

- command execution
- file operations
- workspace location
- other permitted environment operations

The SDK has different workspace implementations, including local and remote forms.

The agent therefore does not need to encode the details of how the environment was provisioned.

A useful general principle is:

**The agent needs an environment contract, not knowledge of the infrastructure behind that contract.**

### Important source locations

- `openhands-sdk/openhands/sdk/workspace/base.py`
- `openhands-sdk/openhands/sdk/workspace/local.py`
- `openhands-sdk/openhands/sdk/workspace/remote/base.py`
- `openhands-sdk/openhands/sdk/workspace/workspace.py`

## 7. History versus model view

OpenHands does not necessarily send the raw complete event store directly to the model on every turn.

The agent prepares an appropriate message view from conversation state and can use condensation when the context becomes too large.

This means the durable physical record and the model's immediate context can be separate concepts.

The important lesson is not to treat "everything that happened" and "everything the model must see right now" as automatically identical.

### Important source locations

- `openhands-sdk/openhands/sdk/context/view.py`
- `openhands-sdk/openhands/sdk/agent/utils.py`
- `openhands-sdk/openhands/sdk/context/condenser/`

## 8. Complexity to avoid

OpenHands has accumulated substantial machinery around the core loop, including:

- confirmation policies
- security analysis
- hooks
- stuck detection
- context condensation
- parallel execution
- skills
- observability
- MCP
- local/remote execution
- multiple agent types
- server/client boundaries
- recovery behavior
- streaming

This is appropriate for a production agent SDK, but WaxPrep should not reproduce all of it simply because OpenHands contains it.

The useful lesson is the boundary between:

- agent intelligence
- agent loop
- session/state
- events
- workspace/runtime

The complexity surrounding those boundaries should only be introduced when WaxPrep has a concrete requirement for it.

## 9. What WaxPrep should learn from OpenHands

1. Make action and observation explicit concepts.
2. Keep the real execution boundary separate from model reasoning.
3. Preserve a durable record of physical events.
4. Separate current session state from the historical event record.
5. Allow the model to receive a useful view of history rather than assuming the entire history must always be sent.
6. Keep the workspace behind a general environment boundary.
7. Treat execution errors as information that can feed the next agent decision.
8. Study event branching as a possible future capability without implementing it prematurely.

## 10. What WaxPrep should not copy

WaxPrep should not copy:

- OpenHands' complete package structure
- its server architecture
- its UI architecture
- its complete tool catalogue
- its MCP system
- its skill system
- its security subsystem
- its condenser implementation
- its production-specific orchestration
- its proprietary/application-specific behaviors

The goal is to extract reusable principles, not reproduce OpenHands.

## Research status

Verified against the current public OpenHands Software Agent SDK source and documentation available during Prompt 11 research.

No source code from OpenHands is copied into WaxPrep.

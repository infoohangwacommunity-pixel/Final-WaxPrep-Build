# Reference Comparison — Six Agent Systems

This is a research comparison for WaxPrep. It records documented/public patterns without ranking the projects.

| Project | Loop design | State storage | Permission model | Context strategy | Extensibility |
|---------|-------------|---------------|------------------|------------------|---------------|
| OpenHands | Repeated agent step: model → action → workspace → observation/event → next step | ConversationState + persistent event log/event tree | Confirmation/security policies | Model-facing context can be a view of durable events; condensation | Agents, tools, workspaces, events, skills |
| SWE-agent | Setup → model/history → action → environment → observation/state → history + trajectory → repeat | In-run history + environment state + trajectory records | Blocked/allowed actions and environment controls | History is shaped for the next model call; observations can be templated/truncated | Environment, commands, SWE-ReX |
| Codex | Durable session/thread containing turns; turns can contain multiple model/execution cycles | Session/thread state and durable history plus execution/world state | Approval policy + filesystem/network/environment sandboxing | Active context differs from all durable state; compaction | Skills, plugins, configuration, runtime |
| OpenCode | Durable prompt admission → runner/provider turn → tool execution → durable result → continuation | Durable session/message/tool records + execution state | Explicit allow/ask/deny boundary | Stable turn context, context epochs, compaction | Skills, plugins, tools, providers |
| Aider | Interactive coding loop: request → context assembly → model → edit/command → world result → next request | Active Coder state + history files + repo-map cache + Git | User confirmation/configuration around operations | Repo map + explicit files + chat history; graph-ranked/token-budgeted | Models, edit formats, commands, lint/test, config |
| Claude Code | Agentic session: model → permitted action → execution → observation → continued reasoning; subagents can delegate | Session transcript + instruction files + auto-memory + settings/subagent state | Enforced allow/ask/deny rules, modes, hooks, managed policy | CLAUDE.md/AGENTS.md + scoped rules + on-demand skills + memory index/topic files | Skills, subagents, plugins, hooks, MCP, settings |

## Cross-system observations

### 1. The common loop is smaller than the products

Across all six, the recurring mechanism is some form of:

**model decision → world/runtime action → observed result → next model input**

The production layers around it are not automatically part of the universal core.

### 2. Durable state and active model context differ

OpenHands, Codex, OpenCode, Aider, and Claude Code all demonstrate that the complete durable record does not have to equal what the model sees on every turn.

This supports WaxPrep's distinction:

**physical history ≠ current model context.**

### 3. Context is a resource

Aider's repo map, OpenHands/OpenCode condensation, Codex compaction, and Claude Code's scoped rules/skills/memory all address context pressure.

The mechanisms differ, but the shared lesson is to avoid injecting the entire world/history into every model request.

### 4. Permissions belong at the world boundary

OpenHands, Codex, OpenCode, and Claude Code make approval or permissions explicit. Aider also has user confirmation around operations.

The common principle is:

**a model request is not permission, and permission is not proof of successful execution.**

### 5. Extensions should sit outside the smallest loop

Skills, plugins, commands, subagents, providers, tools, and workspace implementations are generally extensions around the core loop.

WaxPrep should resist building the core as a catalogue of every future capability.

## WaxPrep research boundary

This comparison is a study artifact, not an architecture decision. Prompt 14 is where researched principles should be translated into a WaxPrep architecture.

No implementation from these projects is copied here.

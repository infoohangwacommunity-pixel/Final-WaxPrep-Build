# Claude Code Research Notes

## Purpose

This document records architectural observations from Claude Code's current public repository and official public documentation.

Claude Code is a commercial product, although its GitHub repository is public. WaxPrep is studying documented/public concepts only and is not copying its implementation or product architecture.

## Repository and documentation studied

- **Project:** Claude Code
- **Repository:** https://github.com/anthropics/claude-code
- **Official documentation:** https://code.claude.com/docs/
- **Primary areas:** memory, skills, subagents, permissions, settings.

The public repository currently contains plugins, commands, examples, security/configuration files, and extensive release history. For the requested behavior, the official documentation is the authoritative public description.

## 1. Agent loop

Claude Code is an agentic terminal coding system: the model can inspect a codebase, request tool actions, receive execution results, and continue reasoning.

The important general lesson is the separation between:

- model reasoning
- requested tool action
- permission enforcement
- actual execution
- returned observation
- continued reasoning

Subagents can introduce additional loops inside a larger session.

## 2. Memory

Claude Code documents two complementary mechanisms.

### CLAUDE.md / AGENTS.md

Persistent instruction/context files can exist at managed, user, project, and local scopes. They hold recurring project facts, conventions, commands, architecture decisions, and workflow guidance.

Claude Code explicitly treats these files as contextual guidance rather than hard enforcement.

### Auto memory

Claude Code can write its own persistent notes based on useful future-facing information such as:

- user preferences/role
- feedback/corrections
- project facts and decisions not derivable from the repository
- external references

Auto memory is stored per project under a memory directory. `MEMORY.md` is a compact index and topic files hold details that are read on demand.

The documented startup limit is the first 200 lines or 25KB of `MEMORY.md`.

Auto memory is machine-local and shared across worktrees/subdirectories of the same repository.

**Important distinction:** persistent instructions and learned memory are separate from the live session transcript.

## 3. Context strategy

Claude Code uses multiple scoped context layers:

- persistent instructions
- path-scoped rules
- active conversation
- on-demand skills
- auto-memory index/topic files
- subagent-specific context
- settings/permission policy

A key principle is loading only what belongs in the current task.

`CLAUDE.md` is for facts that should be present every session. Path rules apply only to matching files. Skills load when invoked or relevant. Auto-memory details are read on demand.

## 4. Skills

A skill is a directory containing `SKILL.md` and optional supporting files.

Documented behavior:

1. Metadata describes relevance.
2. Claude may invoke it or select it when relevant.
3. The body loads when used instead of always consuming context.
4. Supporting files can hold reference material.
5. Skills can be project, user, plugin, or managed scoped.
6. Invocation/permission controls can be applied.
7. Skills can run in a subagent.

This is useful as reusable guidance/capability packaging.

WaxPrep should not turn every future capability into a skill or command merely because Claude Code does.

## 5. Subagents

Claude Code supports project, user, managed, and plugin subagents.

A definition can specify:

- name/description
- allowed or denied tools
- model
- permission mode
- maximum turns
- skills to preload
- MCP servers
- hooks
- persistent memory scope
- background behavior
- instruction-file behavior
- optional worktree isolation

Built-in Explore is documented as a read-only codebase exploration agent.

The useful lesson is:

**subagents are higher-level specialization/isolation around the core agent loop, not the core loop itself.**

## 6. Permissions

Claude Code has a dedicated permission system enforced by the client rather than the model.

The documented outcomes are:

- allow
- ask
- deny

Rules can apply to tools and, for some tools, patterns or parameters.

Examples include:

- shell
- file operations
- web access
- MCP actions
- subagent actions

Permission modes include default/manual, acceptEdits, plan, auto, and dontAsk.

The strongest architectural lesson is:

**a model request is not permission, and permission is not proof of successful execution.**

Managed policy and project/local settings can establish different security scopes.

## 7. Settings

Claude Code uses layered settings:

- user
- shared project
- project local
- managed organization settings

Settings can control:

- models
- permissions
- hooks
- plugins
- environment variables
- memory behavior
- instruction loading
- other product configuration

The useful lesson is explicit configuration scope: team policy can be shared without forcing personal preferences into the repository, while managed policy can enforce organization requirements.

## 8. Instruction versus enforcement

One of Claude Code's clearest public principles is:

**context tells the model what it should do; enforcement controls what the system permits it to do.**

`CLAUDE.md`, `AGENTS.md`, skills, and memory guide the model.

Permissions, managed settings, and hooks can enforce boundaries independently of the model's natural-language compliance.

This maps closely to WaxPrep's brain/world-boundary philosophy.

## 9. Complexity to avoid

WaxPrep should not copy:

- complete Claude Code CLI/product architecture
- full settings schema
- plugin ecosystem
- MCP integration
- complete permission implementation
- authentication/account architecture
- built-in subagent catalogue
- exact memory formats
- terminal/UI behavior
- undocumented/proprietary internals

## 10. What WaxPrep should learn

1. Separate persistent instructions from learned memory.
2. Separate durable memory from live conversation.
3. Load detailed knowledge on demand.
4. Separate model guidance from hard permission enforcement.
5. Make permission scope explicit.
6. Add specialized subagents only for real context/isolation needs.
7. Keep reusable guidance outside the smallest reasoning loop.
8. Make configuration scopes explicit.
9. Enforce hard boundaries in the runtime/client layer.

## 11. What WaxPrep should not copy

Do not import Claude Code's product-specific commands, exact memory schema, account/settings architecture, full permission framework, plugin/MCP ecosystem, subagent taxonomy, CLI/UI, or undocumented internals.

## Research status

Verified against the current public Claude Code repository and official Claude Code documentation during Prompt 13 research.

No Claude Code source code is copied into WaxPrep.

# WaxPrep Architecture

## Status

This document is the architectural blueprint for WaxPrep.

It defines the boundaries that later implementation stages must respect. It is deliberately more concerned with responsibilities and contracts than with particular classes, packages, providers, databases, or product features.

WaxPrep is a general-purpose computer agent.

The central rule is:

**The model is the brain. The agent loop is the nervous system. The runtime and real computer environment are the body and hands. Session and event records preserve what physically happened.**

This document does not authorize application-specific behavior. It does not define a tutoring system, a website workflow, a PDF workflow, an audio workflow, a reminder workflow, or any other domain workflow.

Those belong to later, explicitly authorized domain stages.

---

## 1. Architectural Principles

### 1.1 Intelligence decides

The model is responsible for interpreting available information, reasoning about the situation, choosing actions, and deciding what to do next.

Infrastructure should not silently replace that intelligence with a collection of application-specific rules.

The architecture therefore provides a world in which intelligence can operate. It does not pre-decide the meaning of every possible user request.

### 1.2 The world is the source of execution truth

A requested action is an intention.

An executed action is an interaction with the runtime.

An observation is the result reported by the runtime.

Only the observed result establishes what actually happened.

The system must not turn an attempted action into a success merely because the model expected it to work.

### 1.3 The agent loop connects intelligence and reality

The smallest important cycle is:

**model decision → action request → world/runtime execution → observation → next model input**

The loop may repeat many times inside one turn or session.

The architecture does not assume that one model response equals one complete task.

### 1.4 Infrastructure provides capabilities, not application meaning

The runtime may provide general capabilities such as filesystem access, process execution, networking, time, storage, or other concrete world interfaces when those capabilities are later implemented.

The infrastructure does not decide that a particular file is a lesson, that a message is a reminder, or that a user is asking a particular domain question.

Those meanings belong to intelligence or to a later explicitly defined domain layer.

### 1.5 No forced behavior

WaxPrep should not be designed as a giant decision tree.

There should be no requirement that the model select from a hardcoded list of application intents before it can act.

There should be no hidden application-specific router whose job is to guess what the model meant and then choose a predefined workflow.

Where a capability exists, the model should be able to use it through a clear runtime contract.

### 1.6 Generality comes before domain behavior

The foundation must remain useful even if the eventual application changes.

Tutoring, education, business workflows, messaging channels, and other domain behavior are deliberately outside this foundation until a later prompt explicitly introduces them.

### 1.7 Hard boundaries belong at the world boundary

Some actions may require runtime-enforced boundaries for safety, isolation, or operational reasons.

Those boundaries are not application roles and are not a hidden intelligence layer.

They exist to describe what the runtime can physically permit.

WaxPrep does not define an admin-versus-user architecture here.

### 1.8 Durable reality and active context are different

The system may retain more information than it places into one model request.

Durable history records what happened.

Active model context is the subset of information currently needed for reasoning.

The architecture must not require the entire history to be sent to the model on every turn.

### 1.9 Extensions remain outside the smallest loop

Skills, subagents, providers, tools, and other extensions may be added when a real requirement exists.

They must not become a mandatory catalogue that controls the agent's reasoning.

The smallest useful architecture remains:

**model → action → world → observation → model**

---

## 2. Layer Diagram

The architecture is intentionally layered around responsibility rather than around a specific framework.

```text
                         ┌──────────────────────────┐
                         │          USER            │
                         │  input / external event  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │        SESSION           │
                         │ durable interaction      │
                         │ lifecycle                │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                    ┌────────────────────────────────────┐
                    │             AGENT LOOP              │
                    │                                    │
                    │  prepare model input               │
                    │          │                         │
                    │          ▼                         │
                    │       MODEL                        │
                    │      "brain"                       │
                    │          │                         │
                    │          ▼                         │
                    │      ACTION REQUEST                │
                    │          │                         │
                    │          ▼                         │
                    │   WORLD BOUNDARY                   │
                    │   permission / sandbox / policy    │
                    │          │                         │
                    │          ▼                         │
                    │      RUNTIME                       │
                    │    "body / hands"                  │
                    │          │                         │
                    │          ▼                         │
                    │      OBSERVATION                   │
                    │          │                         │
                    │          ▼                         │
                    │   record physical result           │
                    │          │                         │
                    │          └──────────────┐          │
                    │                         │          │
                    │                         ▼          │
                    │                    next model      │
                    │                      input         │
                    └────────────────────────────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │   DURABLE STATE / EVENTS │
                         │ what physically happened │
                         └──────────────────────────┘


             Optional/general extension boundaries
             ─────────────────────────────────────

              ┌──────────────┐   ┌──────────────┐
              │    SKILLS    │   │  SUBAGENTS   │
              │ guidance     │   │ delegation   │
              └──────┬───────┘   └──────┬───────┘
                     │                  │
                     └──────────┬───────┘
                                ▼
                           AGENT LOOP

              ┌──────────────────────────────────┐
              │     WORKSPACE / WORLD STATE      │
              │ files, processes, network, etc. │
              └──────────────────────────────────┘
                                │
                                ▼
                             RUNTIME
```

### 2.1 Layer responsibilities

**Layer 1 — Intelligence**

The model interprets context and decides.

It is not responsible for physically executing filesystem operations, starting processes, or changing the world directly.

**Layer 2 — Agent loop**

The agent loop carries decisions toward the world and carries observations back toward intelligence.

It owns the repeated control cycle.

It must not become an application workflow engine.

**Layer 3 — Session and state**

Session/state keeps enough durable information for an interaction to continue.

It records the lifecycle and references needed to reconstruct what happened.

It does not decide what the model should think.

**Layer 4 — World/runtime**

The runtime is the actual environment in which requested actions happen.

This may include a workspace, filesystem, processes, operating-system interfaces, network access, time, or other concrete capabilities as later stages require.

**Layer 5 — World boundary**

Permissions and sandboxing are runtime boundaries.

They describe what the environment will allow or restrict.

They are not an admin system.

They do not determine application intent.

**Layer 6 — Optional extensions**

Skills and subagents can extend the agent without becoming the foundation.

A skill is guidance/capability packaging.

A subagent is another agent loop used when delegation or isolation is genuinely useful.

Neither is required for every interaction.

---

## 3. Core Contracts

The architecture should be understood through contracts rather than through a fixed list of classes.

### 3.1 Model contract

**Input:**

- relevant user/session information;
- relevant world observations;
- relevant durable context;
- available guidance/capabilities when applicable.

**Output:**

- reasoning/result suitable for the interaction;
- optionally an action request.

The model is allowed to decide whether an action is necessary.

The infrastructure must not manufacture application actions because it recognizes a keyword.


#### Current normalized model-client interface

The initial model-client contract is defined in `src/waxprep/model_client.py`.

`ModelClient` is an asynchronous structural protocol. Its `complete` method accepts a `ModelRequest` and returns a `ModelResponse`.

The request and response use vendor-neutral message roles, content blocks, tool definitions, tool requests, settings, stop reasons, and optional token-usage information.

The contract uses standard-library types and does not require a concrete provider implementation. Future provider adapters must translate between this normalized contract and their provider-specific request and response formats.

The current content-block variants are text and image references. This is a type-level contract only; content normalization and provider-specific conversion are deferred to later prompts.

Tool requests describe what the model is asking the caller to consider doing. They do not execute tools and do not prove that an action occurred.

The interface does not implement the agent loop, network access, streaming, retries, provider selection, or application-specific behavior.

### 3.2 Agent-loop contract

The loop must:

1. obtain the current state needed for a decision;
2. provide appropriate context to the model;
3. accept the model's response;
4. identify any requested action;
5. pass the action through the world boundary;
6. execute permitted actions through the runtime;
7. capture the actual result;
8. record the result;
9. feed relevant observations back into the next model decision;
10. continue until the model/session reaches an appropriate stopping condition.

The loop must not assume that an action succeeded before receiving its result.

### 3.3 Runtime contract

The runtime receives a concrete request and interacts with the real environment.

It returns a concrete result.

The runtime should be as general as possible.

For example, if the runtime exposes filesystem operations, it provides filesystem reality. It does not decide why a file matters.

### 3.4 Session/state contract

Session state must make continuation possible.

It should allow the system to know:

- which interaction is being continued;
- what durable records belong to it;
- what lifecycle state it is in;
- what world/execution records are associated with it.

The exact storage technology is an implementation decision for a later stage.

### 3.5 Event contract

An event records something that happened or a meaningful state transition.

At minimum, the architecture distinguishes between:

**requested action** and **observed outcome**.

An event must not claim successful execution without evidence from the runtime.

### 3.6 Workspace contract

A workspace is the area in which an agent can operate.

A workspace may contain files, directories, generated artifacts, or other persistent world state.

The workspace is not itself a tutor, project manager, or application workflow.

### 3.7 Extension contract

Extensions should be discoverable or usable without rewriting the core agent loop.

However, the core must not require a large predefined extension registry merely to function.

---

## 4. Full Data Flow of One Turn

A turn is one unit of agent progress. A turn may contain more than one model/action/observation cycle.

```text
1. INPUT ARRIVES
       │
       ▼
2. SESSION ADMISSION
       │
       │ record that input exists
       ▼
3. CURRENT STATE IS ESTABLISHED
       │
       │ session + relevant history + world facts
       ▼
4. MODEL CONTEXT IS PREPARED
       │
       │ only relevant information is presented
       ▼
5. MODEL REASONS
       │
       ├──────────────► final response
       │
       └──────────────► action request
                              │
                              ▼
6. WORLD BOUNDARY
       │
       ├── permitted ───────────────┐
       │                            │
       └── rejected/blocked ────────┤
                                    ▼
7. RUNTIME EXECUTION
       │
       │ the real environment acts
       ▼
8. OBSERVATION
       │
       │ actual result / error / interruption
       ▼
9. DURABLE RECORD
       │
       │ record what physically happened
       ▼
10. MODEL RECEIVES RELEVANT OBSERVATION
       │
       ▼
11. MODEL DECIDES AGAIN
       │
       ├──────────────► final response
       │
       └──────────────► another action
                              │
                              └──────────────► repeat
```

### 4.1 Important distinctions

**Input is not processing**

A message or external event can be admitted into a session before the model has processed it.

**Action request is not execution**

The model can request an action without the runtime having executed it.

**Permission is not execution**

A runtime boundary can permit an action without that action necessarily succeeding.

**Execution is not success**

The runtime may execute an action and return an error.

**Model claim is not world truth**

If the model says an operation happened but the runtime did not report it, the system must not treat the model's statement as physical evidence.

**Durable history is not active context**

The system may retain a detailed history while presenting only relevant material to the model.

---

## 5. Glossary

**Session**

A durable container for an ongoing agent interaction.

A session can contain multiple turns and can survive beyond one immediate model call.

A session answers: *Which ongoing interaction are we continuing?*

**Conversation**

The interactional exchange between a user/external source and the agent.

A conversation may be represented through messages and events inside a session.

Conversation is primarily an interaction concept; session is the durable lifecycle container.

**Event**

A durable record of something that happened or a meaningful state transition.

Examples include input admission, an action request, an execution result, an observation, an interruption, or a session transition.

An event records reality; it does not replace reasoning.

**Turn**

One unit of agent progress inside a session.

A turn can contain multiple model decisions and multiple action/observation cycles.

Therefore:

**session ≠ turn**

and:

**one model response ≠ necessarily one complete task.**

**Action**

A request from the agent to change or inspect the world.

An action is an intention to perform an operation.

An action is not proof that the operation happened.

**Observation**

The result reported after an action interacts with the world.

An observation can represent success, failure, output, state, error, interruption, or another runtime result.

Observation is the bridge from attempted action to physical reality.

**Workspace**

The area of the world/runtime in which the agent is allowed to work.

It may contain files, directories, artifacts, source code, generated data, or other persistent state.

Workspace is a general environment concept, not a domain-specific project concept.

**Runtime**

The actual execution environment that carries out actions.

The runtime may provide processes, filesystem access, network access, time, operating-system interfaces, and other capabilities when implemented.

Runtime reports what actually happened.

**Tool**

A general interface through which the model can request an operation from the world/runtime.

A tool is an interface boundary, not an application intent.

WaxPrep does not require a giant predefined catalogue of tools.

A later capability may expose an appropriate general runtime interface when there is a concrete reason to do so.

**Permission**

A runtime-enforced decision about whether an attempted operation is allowed to cross a world boundary.

Permission is not an application role.

This architecture does not define admin permissions, student permissions, teacher permissions, or any other product-role hierarchy.

Permission exists only where a real execution boundary requires it.

**Sandbox**

A restriction around the runtime's access to the world.

A sandbox can constrain filesystem, process, network, or other resources.

A sandbox is an execution boundary, not an intelligence layer.

**Skill**

Reusable guidance or capability packaging that can be made available to the agent when relevant.

A skill should help intelligence perform a class of work without hardcoding that workflow into the core agent loop.

Skills are optional extensions.

**Subagent**

A separate agent execution context used when delegation, isolation, or specialization is genuinely useful.

A subagent is not a replacement for the primary agent loop.

Subagents should not be introduced merely because another project uses them.

**Memory**

Information retained beyond the immediate model context.

WaxPrep distinguishes at least two useful ideas:

1. **physical history** — records of what happened in the world;
2. **usable retained information** — information deliberately carried forward because it remains useful.

Memory must not be confused with a particular retrieval technology.

This architecture does not require embeddings, keyword matching, vector databases, or a hardcoded retrieval planner.

The mechanism used to make retained information available is an implementation decision for a later stage.

---

## 6. State Model

The architecture treats state as layered rather than as one giant object.

### 6.1 Session state

Answers: *Where is this interaction in its lifecycle?*

Examples may include session identity, lifecycle state, associated turns, and references to durable records.

### 6.2 Turn state

Answers: *What is happening during this unit of progress?*

A turn may contain several model decisions and several action/observation cycles.

### 6.3 World state

Answers: *What is actually present in the runtime right now?*

Examples may include filesystem state, running processes, generated artifacts, network results, or other concrete runtime facts.

### 6.4 Durable event history

Answers: *What did the system record as having happened?*

This is the historical record from which the system can understand the execution path.

### 6.5 Active model context

Answers: *What does the model need to see right now to make the next decision?*

Active context is a view over available information, not necessarily the complete durable history.

---

## 7. Truth and Recovery

WaxPrep must recover from the world, not from assumptions.

If an execution stops halfway through, the system must not silently convert the unfinished operation into success.

Useful lifecycle distinctions include:

```text
requested
   ↓
boundary decision
   ↓
executing
   ↓
observed result
   ├── succeeded
   ├── failed
   └── interrupted
```

The exact state machine is intentionally left for the implementation stage that requires it.

The architectural requirement is the distinction itself:

**requested ≠ permitted ≠ executing ≠ succeeded**

This follows the research across OpenHands, Codex, OpenCode, SWE-agent, Aider, and Claude Code.

---

## 8. Context Strategy

WaxPrep should not force the complete world into every model request.

The context system should eventually be able to provide the model with what is relevant for the current decision while retaining more complete information durably.

The architecture therefore permits:

- recent interaction context;
- relevant session state;
- relevant observations;
- relevant workspace/world facts;
- persistent instructions or guidance when explicitly configured;
- retained memory when relevant;
- extension guidance when relevant.

It does not prescribe:

- embeddings;
- vector search;
- keyword search;
- a fixed retrieval planner;
- a domain-specific context assembler;
- a hardcoded intent classifier.

A later implementation can choose a concrete mechanism if evidence shows that it is needed.

The mechanism must serve the model rather than become a second hidden intelligence layer.

---

## 9. Workspace and World Model

The world is deliberately broader than one application.

A runtime may expose:

- filesystem;
- processes;
- environment variables;
- standard input/output;
- network access;
- clocks/time;
- persistent storage;
- external services;
- other computer capabilities.

The architecture does not require all of these at the beginning.

A capability is introduced when a later stage has a concrete requirement for it.

The model should be able to reason about the results of capabilities rather than relying on infrastructure to translate every possible situation into a predefined application concept.

---

## 10. Permissions and Sandbox Boundary

Permissions are part of the world boundary, not part of application intelligence.

The architecture does not define:

- admin users;
- teacher roles;
- student roles;
- owner roles;
- application-specific authorization workflows.

Those are domain decisions and are intentionally outside this blueprint.

The generic concept is simpler:

```text
MODEL REQUEST
     ↓
WORLD BOUNDARY
     ↓
runtime may allow, require an external boundary decision,
or reject the operation
     ↓
RUNTIME
```

Where a boundary is required, it must be enforced outside the model's natural-language reasoning.

The model may request an action.

The runtime boundary decides whether that action can physically cross the boundary.

The model cannot declare itself authorized.

At the same time, the boundary must not decide what an action means for a domain.

---

## 11. Skills

Skills are optional reusable guidance.

They should be:

- external to the smallest model/world loop;
- loadable when relevant;
- understandable as guidance/capability packaging;
- independent of the core session lifecycle.

A skill should not become a hidden application router.

For example, the core should not contain:

```text
if message == X:
    load tutoring skill
```

unless a later explicit domain stage intentionally defines such behavior.

The preferred model is:

```text
available capability/guidance
          ↓
       model decides
          ↓
       use if useful
```

---

## 12. Subagents

Subagents are optional.

They may eventually be useful when a task genuinely benefits from:

- delegation;
- isolated context;
- separate execution state;
- specialized reasoning;
- parallel or background work.

A subagent is still an agent:

**model → action → runtime → observation → model**

The primary agent must not become a manager of a fixed catalogue of mandatory subagents.

No built-in tutoring subagents, subject agents, website agents, PDF agents, or similar application-specific agents belong in this architecture.

---

## 13. Memory Architecture

Memory is intentionally separated from immediate context.

The architecture recognizes:

```text
                  DURABLE RECORDS
                        │
             ┌──────────┴──────────┐
             │                     │
       physical history       retained information
             │                     │
             └──────────┬──────────┘
                        │
                        ▼
                relevant context
                        │
                        ▼
                      MODEL
```

The model may decide that something is important to retain, but the storage mechanism is infrastructure.

The infrastructure should store and return requested retained information.

It should not decide the semantic meaning of a user's life, education, files, preferences, or goals through hardcoded domain rules.

Any later memory implementation must preserve this separation.

---

## 14. External References and What WaxPrep Learns

The research notes are evidence and design input, not source code to merge.

### OpenHands

See: `docs/research/openhands.md`

**Relevant lessons:**

- repeated model/action/observation loop;
- separation of current state and event history;
- workspace as a runtime boundary;
- durable event records.

WaxPrep should not copy OpenHands' complete production machinery.

### SWE-agent

See: `docs/research/swe-agent.md`

**Relevant lessons:**

- separate reasoning history from durable trajectory;
- thin environment boundary;
- real environment results;
- explicit execution observations.

WaxPrep should not inherit SWE-bench-specific behavior.

### Codex

See: `docs/research/codex.md`

**Relevant lessons:**

- session versus turn;
- multiple execution cycles inside a turn;
- requested versus approved versus executed versus succeeded;
- durable state versus active context;
- compaction as continuity preservation.

WaxPrep should not copy Codex's Rust/product architecture.

### OpenCode

See: `docs/research/opencode.md`

**Relevant lessons:**

- durable input admission;
- explicit provider turns;
- durable execution lifecycle;
- interrupted execution;
- separate permission boundary;
- durable history versus active context;
- continuation-focused compaction;
- skills as external guidance.

WaxPrep should not copy OpenCode's full TypeScript/Effect architecture.

### Aider

See: `docs/research/aider.md`

**Relevant lessons:**

- compact structural context;
- context budgeting;
- separating broad structure from detailed content;
- summarizing older conversation;
- treating real filesystem results as evidence.

WaxPrep should not become an Aider-style coding product or require Aider's repository-map implementation.

### Claude Code

See: `docs/research/claude-code.md`

**Relevant lessons:**

- persistent guidance versus learned memory;
- durable memory versus live transcript;
- on-demand knowledge;
- model guidance versus runtime enforcement;
- optional skills and subagents;
- explicit configuration scope.

WaxPrep must not copy proprietary implementation details or reproduce Claude Code's product architecture.

### Cross-project comparison

See: `docs/research/comparison.md`

The strongest shared architectural lesson is:

**model decision → world action → observed reality → next model decision**

The second major lesson is:

**durable history is not the same thing as current model context.**

---

## 15. Explicit Non-Goals

The following are deliberately outside this architecture.

### 15.1 No application-specific workflows

The core must not contain hardcoded workflows for:

- tutoring;
- education;
- websites;
- PDFs;
- audio;
- reminders;
- messaging platforms;
- payments;
- admissions;
- business operations;
- any other single application domain.

### 15.2 No tutoring yet

WaxPrep must remain a general-purpose agent until a later prompt explicitly introduces tutoring.

The architecture supports a future domain layer but does not implement one.

### 15.3 No hardcoded application intent system

Do not create a giant list such as:

```text
intent = tutoring
intent = reminder
intent = pdf
intent = audio
intent = website
...
```

and use it to decide the agent's behavior.

The model is the decision-maker.

### 15.4 No infrastructure intelligence replacement

Do not create a hidden second AI whose purpose is to determine what the primary model meant.

Do not create a retrieval planner that owns the model's reasoning.

Do not create hardcoded context assemblers for specific application types.

### 15.5 No mandatory embedding/vector architecture

Embeddings, vector databases, semantic indexes, keyword search, or similar mechanisms are not architectural requirements.

A later stage may choose an information-retrieval mechanism only if there is a demonstrated need.

### 15.6 No giant tool catalogue

WaxPrep should not begin with dozens or hundreds of predeclared tools.

The architecture supports general world interfaces.

Capabilities should be added when the system actually needs them.

### 15.7 No admin-role architecture

This blueprint does not define admin, teacher, student, owner, or other product roles.

Runtime permissions are not application roles.

### 15.8 No merging reference codebases

OpenHands, SWE-agent, Codex, OpenCode, Aider, and Claude Code are research references.

WaxPrep is not a combination of those repositories.

No architecture should be produced by mechanically merging their source trees, modules, or internal abstractions.

### 15.9 No proprietary implementation copying

Claude Code's proprietary implementation is not a source for copied architecture or code.

The same principle applies to any external project whose license or terms do not permit the intended reuse.

### 15.10 No build-ahead

This document does not authorize implementation of:

- full agent runtime;
- model providers;
- memory database;
- messaging integration;
- tutoring;
- subagent framework;
- skill marketplace;
- production permissions;
- complete sandbox;
- application deployment.

Those belong to their respective later stages.

---

## 16. Future Phase Boundaries

The following phase map defines how the post-blueprint implementation stages should proceed without allowing one stage to silently absorb another.

**Phase 1 — Core agent loop**

Adds the smallest working model → action → runtime → observation → model cycle.

Must not add tutoring, messaging-platform workflows, domain-specific routing, or a giant tool catalogue.

**Phase 2 — Session and durable state**

Adds durable session lifecycle and the records required to continue an interaction.

Must not redesign the core decision loop or add application-specific memory meanings.

**Phase 3 — Event and execution history**

Adds reliable recording of action requests, runtime observations, failures, and interruptions.

Must not turn event history into a hidden reasoning engine.

**Phase 4 — World/runtime foundation**

Adds the concrete runtime interfaces through which the agent can interact with the computer environment.

Must not decide application intent or add domain workflows.

**Phase 5 — Workspace**

Adds persistent workspace handling and clear workspace boundaries.

Must not hardcode a particular project type, file type, or tutoring workflow.

**Phase 6 — World boundary**

Adds the minimum generic runtime enforcement required to safely operate the environment.

Must not create an admin/teacher/student role system or make infrastructure decide what the model means.

**Phase 7 — Context management**

Adds the mechanism for preparing useful model context from durable state and current world observations.

Must not become a domain-specific intent router, embedding requirement, or hidden second intelligence layer.

**Phase 8 — Continuation and compaction**

Adds a way to continue long sessions without requiring the entire durable history in every model request.

Must not erase durable reality or rewrite history into an invented success state.

**Phase 9 — Skills**

Adds reusable guidance/capability packaging when a concrete need exists.

Must not make skills mandatory for normal agent operation or use skills as a hardcoded application workflow engine.

**Phase 10 — Subagents**

Adds delegated agent contexts only where delegation or isolation provides a real benefit.

Must not introduce a fixed catalogue of application-specific agents.

**Phase 11 — Memory**

Adds retained information beyond the immediate active context.

Must not hardcode semantic categories such as "student memory", "tutoring memory", or other domain-specific interpretations before an explicit domain stage.

**Phase 12 — External interfaces**

Adds general interfaces to external systems when required.

Must not make one channel, website, file type, or business process part of the core architecture.

**Phase 13 — Domain/application layer**

Only at this stage may an explicitly authorized application domain be introduced.

If the future product is instructed to become a tutor, tutoring behavior belongs here or in a clearly separated domain layer.

This phase must consume the general agent foundation rather than rewriting the foundation into a tutoring-specific system.

---

## 17. Rules for Future Architectural Decisions

When a later prompt proposes a new component, ask:

1. Does this provide a general capability to the agent?
2. Does the model remain responsible for deciding what the capability means and when to use it?
3. Does the runtime remain responsible for reporting what actually happened?
4. Does durable history remain distinct from active model context?
5. Is the component required by the current phase rather than a future phase?
6. Can the same component make sense outside one application domain?
7. Does it avoid silently introducing a second decision-maker?
8. Does it preserve the distinction between action request, execution, and observation?

If the answer to these questions is no, the proposal should be reconsidered before implementation.

---

## 18. Architectural Invariants

These statements are intended to remain true unless a deliberate architecture decision explicitly changes them.

1. The model is the primary intelligence.
2. The agent loop connects intelligence to reality.
3. The runtime performs real-world execution.
4. Observations come from execution reality.
5. An attempted action is not proof of success.
6. A session can contain multiple turns.
7. A turn can contain multiple model/action/observation cycles.
8. Durable history is not identical to active model context.
9. Permissions and sandboxing are world boundaries, not application roles.
10. Skills and subagents are optional extensions, not the foundation.
11. The core does not hardcode application-specific workflows.
12. Tutoring is not part of the foundation until explicitly instructed.
13. Reference projects are studied for principles, not merged into WaxPrep.
14. Future capabilities should be introduced because the current system needs them, not because another agent project has them.
15. The infrastructure should make reality available to intelligence without silently taking over intelligence's job.

---

## 19. Relationship to Existing Project Decisions

This blueprint builds on, but does not replace:

- `PHILOSOPHY.md` — core product philosophy;
- `REFERENCES.md` — reference-study boundaries;
- `ADR-0001-language-runtime-package-manager.md` — Python 3.14 and uv decision;
- `CONTRIBUTING.md` — development and stage-completion rules;
- `LICENSES.md` and `THIRD_PARTY` — licensing and attribution boundaries.

`ARCHITECTURE.md` is the architectural interpretation of those decisions for later implementation.

It does not reopen the language/runtime decision.

It does not replace the philosophy.

It does not authorize application development that a later prompt has not requested.

---

## 20. Final Architectural Summary

WaxPrep is not intended to be a collection of hardcoded workflows.

It is an environment in which intelligence can operate.

The essential relationship is:

```text
             INTELLIGENCE
              (the model)
                   │
                   │ decides
                   ▼
              ACTION REQUEST
                   │
                   ▼
          WORLD / RUNTIME BOUNDARY
                   │
                   │ executes
                   ▼
               REAL WORLD
                   │
                   │ produces
                   ▼
              OBSERVATION
                   │
                   │ recorded
                   ▼
            DURABLE REALITY
                   │
                   │ relevant result
                   ▼
                MODEL
                   │
                   └──────────────► decide again
```



## Persistence and recovery (implemented foundation)

WaxPrep already persists sessions and events on the local filesystem when using
the file-backed stores.

### What is persisted

- Each session has a directory under an absolute caller-supplied `data_dir`.
- Session metadata is stored in `metadata.json`.
- Event history is stored as append-only `events.jsonl` (one `EventEnvelope` per
  line).
- Per-session operating-system write locks coordinate concurrent writers for the
  same session.

### How history is read

- `EventStore.read_from_sequence` and `read_range` return immutable
  `EventEnvelope` values in ascending sequence order.
- `event_history.query_events` / `paginate_events` filter that history without
  modifying storage.
- `replay_events` walks recorded events in order; it does not re-execute tools
  or contact a model.

### What Prompt 28 proves

An integration test starts a **separate Python process** that:

1. creates a session,
2. transitions lifecycle status,
3. appends varied event kinds,
4. writes an independent expected snapshot to disk,
5. exits.

A fresh process (the test runner) then reopens the same `data_dir` with new
`FileSessionStore` / `FileEventStore` instances, loads the session, reads the
event log, replays it, and asserts equality with the expected snapshot.

This demonstrates recovery of durable session metadata and ordered event history
after a genuine process restart. It does **not** claim distributed durability,
crash-atomic cross-store transactions, or model/agent-loop behavior.


The architecture therefore does not ask infrastructure to understand everything.

It asks infrastructure to provide a reliable world.

The model provides intelligence.

The loop provides continuity.

The runtime provides hands.

Events provide durable evidence of what happened.

Memory preserves useful information beyond the immediate context.

Extensions provide additional capabilities when genuinely needed.

Domain behavior comes later.

**AI decides. The world acts. The world reports. The agent continues from reality.**

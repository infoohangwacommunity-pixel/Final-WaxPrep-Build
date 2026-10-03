# WaxPrep Decision Log

This document records the major project decisions made during the foundation phase
(Prompts 1–14).

WaxPrep is being built first as a general-purpose computer agent. Application-specific
behavior, including tutoring, is intentionally postponed until the architecture is
ready for it.

---

## 1. Project Identity

**Decision:** The project is named WaxPrep.

**Reason:** The repository and architecture were intentionally established under the
WaxPrep name before implementation of the agent system begins.

---

## 2. Project Purpose

**Decision:** WaxPrep is a general-purpose computer agent foundation.

**Reason:** The foundation must be useful independently of any single application or
domain.

The eventual Waza educational tutor will be built on top of this foundation, but
tutoring behavior does not belong in the foundation itself.

---

## 3. Core Agent Philosophy

**Decision:** The AI model is the primary intelligence of the system.

The core relationship is:

    model decides
        ↓
    action request
        ↓
    real world / runtime
        ↓
    actual result
        ↓
    observation
        ↓
    model decides again

**Reason:** The model should interpret situations, choose actions, and reason about
results. Infrastructure should provide the environment in which those decisions can
be carried out.

The infrastructure must not secretly become a second intelligence layer.

---

## 4. Runtime as the Real World

**Decision:** The runtime is the physical execution layer of the agent.

The runtime may eventually provide general capabilities such as:

- filesystem access
- terminal execution
- processes
- network access
- clock/time
- workspace access

**Reason:** The agent needs a real environment in which actions can happen.

The runtime reports what actually happened. It does not decide what an action means.

---

## 5. Action and Observation

**Decision:** A requested action is not treated as proof that the action succeeded.

**Reason:** The model can request an action, but only the runtime can establish what
actually happened.

Therefore:

- requested is not the same as executed
- executed is not the same as successful
- permission is not the same as execution
- the runtime observation is the source of truth about execution

---

## 6. General Infrastructure Only

**Decision:** Foundation infrastructure must remain general-purpose.

The foundation must not contain workflows specifically designed for:

- websites
- PDFs
- audio
- reminders
- tutoring
- individual applications
- hardcoded user intents

**Reason:** Those decisions belong to the model or to later domain/application
layers, not to the general agent infrastructure.

---

## 7. No Hidden Intent Router

**Decision:** WaxPrep will not use a hidden application-specific intent-routing
layer.

**Reason:** An intent router would move part of the intelligence from the model into
infrastructure and could cause the infrastructure to decide what the user means.

The model remains responsible for interpreting the user's request.

---

## 8. No Mandatory Embedding or Vector Architecture

**Decision:** WaxPrep does not require embeddings, vector databases, or keyword
matching as a foundation requirement.

**Reason:** These are implementation techniques, not architectural requirements.

If a later capability genuinely requires one of them, that decision must be made
explicitly at that stage.

---

## 9. Sessions and Events

**Decision:** Durable sessions and event records represent what physically happened
during agent operation.

**Reason:** The system needs a reliable record of reality rather than relying only
on the model's current context.

A session may contain multiple turns, and a turn may contain multiple
model/action/observation cycles.

---

## 10. Durable History vs Active Context

**Decision:** Durable history and the model's active context are separate concepts.

**Reason:** The system may preserve a large amount of history without sending all of
that history to the model on every request.

Future context-management work will decide what information is relevant to a specific
model call.

---

## 11. Workspace

**Decision:** A workspace is an area in which the agent can operate.

**Reason:** The agent needs a defined place where real-world operations can occur.

Workspace design remains general-purpose and is not tied to a tutoring workflow.

---

## 12. Permissions and Sandboxing

**Decision:** Permissions and sandboxing are runtime/world boundaries.

**Reason:** They exist to control what the agent is physically allowed to do.

They are not an application-level role system such as:

- administrator
- teacher
- student

Those concepts belong to a future application/domain layer if they are ever needed.

---

## 13. Skills and Subagents

**Decision:** Skills and subagents are optional extensions around the core agent loop.

**Reason:** They can provide reusable guidance or isolated agent contexts without
changing the fundamental model → action → runtime → observation cycle.

They must not become hidden application routers.

---

## 14. Language and Runtime

**Decision:** WaxPrep uses Python 3.14.

**Reason:** Python 3.14 was selected as the project runtime during the foundation phase.

The supported Python range is:

    >=3.14,<3.15

---

## 15. Package and Environment Management

**Decision:** WaxPrep uses `uv` for Python environment and package management.

**Reason:** The project requires a deterministic and simple development workflow.

---

## 16. Code Quality

**Decision:** WaxPrep uses:

- Ruff for formatting and linting
- mypy in strict mode for type checking
- Python unittest for tests

**Reason:** These provide deterministic automated checks while keeping the foundation
small.

The standard project verification command is:

    make check

---

## 17. Continuous Integration

**Decision:** GitHub Actions runs the project's quality checks.

**Reason:** Changes should be automatically verified rather than relying only on a
developer's local environment.

Automated changes must still pass the project's quality gate.

---

## 18. Dependency Automation

**Decision:** Dependabot is used for dependency update management, with automated
merging governed by the repository's quality checks.

**Reason:** Dependency maintenance should remain controlled by automated verification
rather than bypassing project checks.

---

## 19. Licensing

**Decision:** WaxPrep uses the Apache License 2.0.

**Reason:** This is the repository's selected project license.

The repository also records third-party licensing policy separately.

---

## 20. Third-Party Code and Research

**Decision:** WaxPrep studies publicly documented architectures from:

- OpenHands
- OpenAI Codex
- OpenCode
- Aider
- SWE-agent
- Claude Code

**Reason:** These projects provide useful publicly documented patterns for reliable
computer-agent systems.

WaxPrep borrows architectural ideas, not entire codebases.

Third-party source code may only be reused when permitted by the repository's licensing
policy, and required attribution must be recorded.

---

## 21. Research Lessons

The shared architectural pattern identified during research is:

    model decision
        ↓
    action
        ↓
    real environment
        ↓
    observation
        ↓
    next model decision

Important lessons include:

- execution results must come from the real environment
- durable history should not automatically equal active model context
- sessions can contain multiple turns
- turns can contain multiple execution cycles
- permissions should remain separate from action implementation
- long-running agents need continuity
- context must be managed rather than blindly sending everything to the model

---

## 22. Architecture Boundary

**Decision:** The smallest important architectural boundary is between intelligence
and the real world.

The model decides.

The agent loop connects the decision to execution.

The runtime executes.

The runtime produces observations.

The model receives those observations and continues reasoning.

**Reason:** This boundary prevents infrastructure from silently becoming application
intelligence.

---

## 23. Tutoring Is Deferred

**Decision:** Tutoring and educational application behavior are intentionally postponed.

**Reason:** The general-purpose agent foundation must be reliable before domain-specific
behavior is introduced.

Tutoring is therefore a future application/domain phase, not part of the Phase 0
foundation.

---

## 24. Build Scope Discipline

**Decision:** Each implementation prompt should implement only the capability assigned
to that prompt.

**Reason:** Building future stages early makes the architecture harder to verify and
makes it difficult to identify which decision introduced a problem.

Future capabilities should be added only when their stage is explicitly reached.

---

## Phase 0 Status

Prompts 1–14 established the project foundation, research record, philosophy, and
architecture blueprint.

Prompt 15 is the Phase 0 review gate.

No identifier scheme, agent loop implementation, runtime implementation, tutoring
logic, or other later-stage capability belongs in this review.

The repository should proceed to the next prompt only after the Phase 0 checks pass
and the resulting repository state is tagged or otherwise recorded.

---

## 25. WAX ID Identifier Scheme

**Decision:** WaxPrep uses stable identifiers with the following general form:

    wax_<kind>_<uuidv7>

Examples include:

    wax_session_<uuidv7>
    wax_conversation_<uuidv7>
    wax_turn_<uuidv7>
    wax_event_<uuidv7>
    wax_action_<uuidv7>
    wax_observation_<uuidv7>

The UUID portion uses the UUIDv7 layout.

**Reason:** WaxPrep needs a stable identity for sessions, conversations, turns,
events, actions, and observations so records can be connected without relying
on human-readable names or database-generated incidental identifiers.

The identifier provides three useful properties:

- the `wax_` prefix identifies the WaxPrep namespace
- the kind prefix makes the object type immediately understandable
- UUIDv7 provides timestamp-based ordering together with a large random
  component for collision resistance

Wax IDs are therefore sortable by creation time across different milliseconds
while remaining suitable for distributed generation.

The identifier layer provides:

- generation
- parsing
- validation
- explicit rejection of malformed or unknown IDs

Invalid IDs must not silently pass as valid identifiers.

Prompt 16 intentionally uses the standard-library system time directly for
UUIDv7 timestamp generation. A replaceable Clock abstraction is deferred to
Prompt 17 and must not be introduced as part of this identifier implementation.

The identifier scheme is general infrastructure only. It does not contain
tutoring logic, application-specific workflows, intent routing, or agent
decision-making.

---

## 26. Clock Abstraction

**Decision:** All WaxPrep time access must go through one injectable Clock
abstraction.

The Clock provides two readings:

- `now()` for current wall-clock time;
- `monotonic()` for measuring elapsed time.

WaxPrep provides two implementations:

- `RealClock` for actual runtime operation;
- `FakeClock` for deterministic testing.

The FakeClock can be advanced without waiting for real time to pass.

**Reason:** Time-dependent behavior must be deterministic and testable. Tests
must be able to move time forward without waiting for the real world clock.

Direct use of system time APIs outside the Clock implementation is forbidden.
Ruff enforces this rule for common wall-clock and elapsed-time APIs.

The identifier generator now receives a Clock and therefore no longer reads
system time directly.

The Clock abstraction is general infrastructure. It does not implement
application-specific scheduling, reminders, tutoring behavior, messaging
behavior, or agent decisions.

Prompt 17 does not implement the Event Envelope from Prompt 18.

---

## 27. Event Envelope

**Decision:** WaxPrep records events using one immutable Event Envelope with
the following common fields:

- `id`
- `session_id`
- `sequence`
- `timestamp`
- `kind`
- `schema_version`
- `payload`
- optional `parent_id`
- optional `cause_id`

The event ID must be a valid `wax_event_<uuidv7>` WAX ID, and the session ID
must be a valid `wax_session_<uuidv7>` WAX ID.

Parent and cause references, when present, must reference valid event IDs.

The envelope is immutable after creation, including its nested JSON payload.

Events can be serialized to strict JSON and reconstructed from JSON only after
strict validation.

At this stage the only permitted event kind is the minimal `placeholder`
kind. Event taxonomy is intentionally deferred to Prompt 19.

**Reason:** Every durable event needs one consistent structure so future event
records can be validated, serialized, related, and reconstructed without
inventing different formats for different event types.

The envelope is general infrastructure. It does not define application-specific
events, tutoring behavior, agent-loop behavior, runtime behavior, event
storage, or an event bus.

Prompt 18 does not implement the Event Taxonomy from Prompt 19.

---

## 28. Event Taxonomy

**Decision:** WaxPrep recognizes the following general-purpose event kinds:

- `user_message`
- `model_message`
- `model_tool_request`
- `action_result`
- `error`
- `state_change`
- `system_notice`
- `permission_decision`

Each event kind has a typed payload contract and runtime validation.

**Reason:** The Event Envelope from Prompt 18 provides the common structure for
recording events, but the system also needs to distinguish what kind of thing
each event represents.

The taxonomy preserves the architectural distinction between:

- what the model requests;
- what the runtime actually reports;
- errors;
- state transitions;
- system-level notices; and
- permission decisions.

`model_tool_request` represents an intention/request and must not be treated as
proof of execution.

`action_result` represents the observation returned by the runtime and is the
source of truth about the result of an attempted action.

All event kinds remain domain-neutral. They must not encode tutoring,
education, examination, website-specific, reminder-specific, or other
application-specific workflows.

The permission decision event is only a placeholder at this stage. Prompt 19
does not implement a permission engine.

The event taxonomy does not implement an event bus, event store, agent loop,
runtime, application logic, or other later-stage infrastructure.

Prompt 19 defines the event kinds and their payload contracts only.


---

## 29. Event Schema Versioning and Immutable Migrations

**Decision:** WaxPrep event envelopes use an explicit current schema version,
and older event data is upgraded through a version-keyed migration chain before
current-schema validation.

The current event schema version introduced by Prompt 20 is:

    2

Migrations are keyed by their source version:

    v1 → v2
    v2 → v3
    v3 → v4

Each migration must advance the event to the next supported schema version.

**Reason:** Durable event records must remain readable as the event contract
evolves.

Prompt 18 created schema version 1 with a temporary `placeholder` event kind.
Prompt 19 replaced that placeholder with the domain-neutral event taxonomy.
Prompt 20 therefore provides the compatibility migration from the historical
version 1 placeholder event into the current version 2 taxonomy.

The version 1 placeholder payload is preserved as deterministic JSON inside a
current `system_notice` payload rather than restoring the deprecated
placeholder event kind to the current taxonomy.

Old migrations are immutable compatibility history.

Once released, an existing migration must never be edited. Future schema
changes must add a new migration step instead.

Events with a schema version newer than the supported current version are
rejected rather than silently downgraded.

Migration occurs in memory during event deserialization. Storage concerns
remain outside this prompt and belong to the later storage abstraction stage.

This decision remains domain-neutral and does not introduce tutoring,
application workflows, an event bus, persistence infrastructure, or agent-loop
behavior.


---

## 30. Storage Abstraction and Persistence Contracts

**Decision:** WaxPrep separates storage interfaces from storage implementations.

The foundation defines two domain-neutral protocols:

- `EventStore`
- `SessionStore`

`EventStore` provides:

- append
- read range
- read from sequence
- count

`SessionStore` provides:

- create
- get
- list
- update metadata

**Reason:** Agent/session code must not become coupled to a particular
persistence technology.

Event storage is append-only and immutable. Events within a session use a
strict, gap-free sequence beginning at `1`, and reads return events in
ascending sequence order.

A single event append is atomic: it either becomes visible completely or
leaves the event history unchanged.

Session creation is also atomic. Metadata updates replace the complete
metadata snapshot.

The interface does not prescribe the implementation mechanism. Locks,
transactions, optimistic concurrency, files, databases, or memory are
implementation concerns.

Prompt 21 intentionally provides no storage backend.

Reusable storage contract tests are defined separately so every future
implementation can be checked against the same observable behavior.

This decision remains domain-neutral and does not introduce an event bus,
agent loop, runtime behavior, database technology, or tutoring/application
logic.


---

## 31. In-Memory Storage Backend

**Decision:** WaxPrep's first concrete storage implementation is an in-memory
`EventStore` and `SessionStore`.

**Reason:** A process-local backend provides a fast implementation for tests
and experiments while allowing the storage contracts to be exercised before
durable persistence is introduced.

The `InMemoryEventStore` maintains independent, append-only event histories
per session. Event sequences begin at `1` and must advance by exactly one.
Invalid, duplicate, or gapped sequences are rejected atomically.

The `InMemorySessionStore` maintains immutable session identities and replaces
metadata as complete snapshots.

The backend is process-local and intentionally non-durable. Data disappears
when the process exits.

Prompt 22 does not introduce file persistence, databases, an event bus,
agent-loop behavior, model integration, or application-specific logic.

---

## 32. Durable File-Based Storage Backend

**Decision:** WaxPrep's first durable storage implementation uses an external,
configurable filesystem data directory.

Each session has:

- an append-only `events.jsonl` event log;
- a separate `metadata.json` session metadata file.

**Reason:** The storage contracts from Prompt 21 need a durable implementation
before higher-level session behavior is introduced.

JSON Lines preserves the append-only event-history model while keeping each
event independently serialized using the existing `EventEnvelope` schema and
migration system.

The data directory is supplied explicitly as an absolute path so durable
runtime data is not implicitly mixed into the source workspace.

Event appends remain gap-free and atomic at the storage contract level.
Successful event records are flushed to durable storage.

Session metadata is replaced using an atomic temporary-file write followed by
replacement of the existing metadata file.

A partially written final JSONL record is treated as recoverable corruption.
The backend reports it through `StorageCorruptionWarning` and preserves all
earlier valid events instead of allowing a raw JSON decoding failure to escape.

Corruption in a non-final event-log record is treated as unrecoverable
`StorageCorruptionError` because the ordered history can no longer be trusted.

Prompt 23 does not introduce the session lifecycle, agent loop, runtime,
database technology, event bus, tutoring logic, or application-specific
behavior.


---

## 33. Session Model and Lifecycle

**Decision:** WaxPrep defines a domain-neutral session model with six statuses
(`created`, `running`, `waiting`, `finished`, `failed`, `cancelled`) and an
explicit transition table.

Successful transitions append a durable `state_change` event and then update
session metadata. Session creation establishes the initial `created` state
without emitting a synthetic state-change event.

**Reason:** Higher-level agent behavior needs a durable work container with
clear lifecycle rules and an audit trail of status changes.

The session reuses existing WAX IDs, Clock, EventEnvelope, SessionStore, and
EventStore contracts rather than introducing parallel systems.

Write ordering prefers recording the transition event before advancing
metadata so a failed metadata update does not claim success without evidence.
The current storage abstractions do not provide a transaction spanning both
stores; that limitation is accepted and documented rather than papered over.

Prompt 24 does not implement conversations, turns, the agent loop, model
providers, tools, workspace management, or application-specific logic.


---

## 34. Conversation Model

**Decision:** WaxPrep represents a conversation as an immutable ordered view of
`user_message` and `model_message` events belonging to a session.

Conversation identity uses the existing WAX conversation identifier kind.
Reconstruction filters the durable event log by session and message kinds and
orders messages by event sequence.

**Reason:** The event log is the source of truth for what was said. A
conversation view must be rebuildable from stored events without introducing a
second intelligence layer or changing historical message payloads.

Message payloads remain `{"text": ...}` for compatibility with already stored
events. Conversation association is via session identity on the conversation
object. Embedding conversation IDs into message payloads is deferred until a
schema migration is justified by multi-conversation needs.

Prompt 25 does not implement context assembly, memory retrieval, the agent
loop, model providers, tools, or application-specific behavior.

---

## 35. Conversation Identity Boundary (Prompt 25 clarification)

**Decision:** For the current conversation model, the **session** is the durable
grouping for user and model messages. The **conversation ID** identifies the
conversation view/object and is supplied by the caller when reconstructing a
conversation; it is not stored on message event payloads.

**Reason:** Message events still use payload `{"text": ...}` so historical
events remain valid without a schema migration. The event log can recover which
messages belong to a session and in what order. It cannot independently recover
a conversation ID that was never recorded on those events.

**Consequence:**

- One conversation view per session is the supported contract.
- Multiple independently recoverable conversations per session are not supported
  yet.
- Future multi-conversation support requires a dedicated prompt and a durable
  association design that preserves compatibility with existing message events.

This clarification does not change event payloads, migrations, storage
backends, or agent-loop behavior.


---

## 36. Event Reading, Replay and Queries

**Decision:** WaxPrep provides a domain-neutral event-history query layer over the
existing `EventStore`.

The query layer supports filtering by:

- event kind
- timestamp range
- sequence range

Time and sequence ranges use inclusive starts and exclusive ends.

Pagination uses event sequence as the continuation cursor rather than introducing
a separate storage-specific paging model.

WaxPrep also provides a simple visitor-based replay operation that walks already
recorded events in ascending sequence order without executing actions or contacting
the runtime or model.

A human-readable timeline formatter is provided for debugging and inspection.

**Reason:** Durable event history is useful only if humans and future recovery
logic can efficiently read and interpret what actually happened.

This keeps reading and inspection separate from storage implementation while
preserving the existing EventStore and EventEnvelope contracts.

The replay mechanism is intentionally an ordered event walk. It is not a full
workflow-reconstruction engine such as deterministic workflow replay.

Prompt 26 does not introduce the agent loop, model providers, runtime execution,
context assembly, memory retrieval, databases, concurrency infrastructure,
hosting-specific code, or application-specific tutoring behavior.

---

## 37. Cross-Process Session Write Locks

**Decision:** File-backed session writes use a per-session operating-system file
lock in addition to the existing in-process `RLock`.

The lock is non-blocking. Competing writers for the same session receive
`StorageConflictError` and must retry. Sequence validation for event appends
occurs while the cross-process lock is held.

**Reason:** In-process locks do not coordinate independent Python processes that
share the same durable data directory. Without a cross-process lock, two store
instances could both approve the same next event sequence.

Different sessions remain independent. The mechanism targets local filesystems
and does not claim distributed or network-filesystem locking.

Prompt 27 does not introduce the agent loop, model providers, concurrency
frameworks beyond session write coordination, databases, or application logic.

---

## 38. Persistence Recovery Integration Test (Prompt 28)

**Decision:** WaxPrep verifies durable session and event recovery with an
integration test that writes history in one process and recovers it in another
after the writer exits.

**Reason:** Creating a second store object in the same process does not prove
that persisted data survives process termination. A subprocess writer that exits
cleanly, followed by recovery from disk-only state, exercises the real file
backend, locking path, event serialization, and session metadata reload.

The test establishes expected results from the writer's inputs before exit, then
compares recovered session status, event sequences, kinds, and payloads in the
parent process. Replay and timeline helpers are exercised on recovered history
only as secondary checks.

Prompt 28 does not implement model providers, the agent loop, tutoring, or new
storage backends.

---

## 39. Vendor-Neutral Model Client Contract (Prompt 29)

**Decision:** WaxPrep defines normalized model request and response value types and an asynchronous `ModelClient` structural protocol.

The request contains normalized messages, optional tool definitions, and common model settings. The response contains normalized content blocks, optional tool requests, a stop reason, and usage information that may be unavailable.

The contract is independent of any concrete model vendor. Its initial content-block types represent text and image references.

**Reason:** The rest of WaxPrep should communicate through a stable model contract rather than depend directly on any provider's SDK or API schema.

The implementation follows the project's existing use of standard-library `Protocol` interfaces and typed, immutable value objects. It introduces no runtime dependency.

The contract does not implement provider adapters, message or content normalization, network requests, tool execution, the agent loop, or application-specific behavior.

Prompt 29 establishes the interface only. Provider implementations and normalization logic remain deferred to their own prompts.

---

## 40. Event-to-Model-Message Normalization (Prompt 30)

**Decision:** WaxPrep converts existing durable conversation events into
the vendor-neutral `ModelMessage` types established in Prompt 29.

User events become user messages, model text events become assistant
messages, model tool requests become assistant messages containing
`ToolRequest` values, and action results become tool-result messages.

The originating tool-request event ID becomes the normalized tool request
ID. An action result must reference exactly one preceding, unresolved
tool request through the existing `parent_id` or `cause_id` event-envelope
fields.

Ambiguous, orphaned, out-of-order, and duplicate results are rejected
instead of being paired by proximity or by choosing the latest request.

**Reason:** Model messages must accurately represent recorded history.
A real action result must be associated with the request that caused it,
without inventing relationships or changing historical payload formats.

**Compatibility:** The implementation reuses the existing event envelope,
event payloads, storage contracts, and Prompt 29 model types. No event
schema migration or provider dependency is introduced.

Prompt 30 does not implement a mock model, a provider adapter, tool
execution, the agent loop, or application-specific behavior.

---

## 41. Deterministic Scripted Model Client (Prompt 31)

**Decision:** WaxPrep provides a scripted mock implementation of the existing
asynchronous `ModelClient` protocol for deterministic tests.

The mock consumes `ModelResponse` values and exceptions in explicit sequence.
It records received requests, returns scripted responses, raises scripted
exceptions, and raises a clear error if the script is exhausted.

Small helpers create text responses, tool-request responses, and validated
scripts from the existing vendor-neutral model types.

**Reason:** Tests must be able to exercise model-facing code without provider
credentials, network access, usage costs, or nondeterministic model output.
Unexpected additional model calls must fail visibly rather than repeat an
arbitrary response.

**Compatibility:** The implementation reuses `ModelClient`, `ModelRequest`,
`ModelResponse`, `ToolRequest`, `StopReason`, and existing content types.
It adds no production dependency and does not modify earlier contracts.

Prompt 31 does not define the tool schema, execute tools, implement the agent
loop, contact model providers, add retries, or introduce application-specific
behavior.

---

## 42. Tool Definition Schema and Argument Validation (Prompt 32)

**Decision:** WaxPrep reuses its existing ToolDefinition contract and
validates tool input schemas using JSON Schema Draft 2020-12.

Each tool input schema must describe a top-level JSON object. Schemas are
validated when tool definitions are constructed. Schema data is copied
and recursively frozen so later mutation of the caller's original data
cannot silently change the declared contract.

A reusable argument-validation function checks proposed tool arguments
against the corresponding definition. Invalid schemas raise
ModelContractError at definition time. Invalid argument values raise
ToolArgumentsError during argument validation.

**Reason:** Tool definitions need a consistent, standards-based input
contract. Reimplementing a partial JSON Schema validator would create
inconsistent behavior and require WaxPrep to maintain its own schema rules.

**Compatibility:** The implementation reuses the existing vendor-neutral
ToolDefinition and ToolRequest contracts. JSON Schema validation does
not execute tools, grant permissions, or establish that an action succeeded.

The JSON Schema library is an explicit runtime dependency and is managed
through the project manifest and lockfile.

Prompt 32 does not implement provider-specific schema conversion, real
provider adapters, tool registration or dispatch, tool execution, the agent
loop, a permission engine, or application-specific behavior.

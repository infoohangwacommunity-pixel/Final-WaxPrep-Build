# Conversation Model

## Purpose

A conversation is an ordered view of recorded user and model messages.

The durable event log is the source of truth. A conversation representation can
be reconstructed from stored events without any second intelligence layer.

## Representation

- `Conversation.id` — a WAX conversation identifier (`wax_conversation_<uuidv7>`)
- `Conversation.session_id` — the session the conversation belongs to
- `Conversation.messages` — ordered `ConversationMessage` values

Each message carries:

- role (`user` or `model`)
- text
- source event id
- event sequence
- timestamp

## Relationship to events

User and model messages are stored as existing event kinds:

- `user_message` with payload `{"text": "..."}`
- `model_message` with payload `{"text": "..."}`

Reconstruction includes only those kinds for the requested session and orders
them by ascending event sequence. Other event kinds (tool requests, state
changes, errors, notices, etc.) are ignored for the conversation view.

## Compatibility

Existing message payloads contain only `text`. Prompt 25 does not change that
schema and does not require a new event schema version for conversation
association.

Historical events that already validate as `user_message` / `model_message`
remain readable and reconstructable.

## Conversation identity boundary

**The session is the durable grouping for messages.**

The event log records which session a message belongs to (`session_id` on the
envelope). Reconstruction therefore recovers the ordered user/model messages for
a session from stored events.

**The conversation ID is supplied externally.**

`conversation_from_events` and `conversation_from_event_store` take
`conversation_id` as an argument. That ID is the identity of the conversation
*view/object*. It is **not** stored on message events today, so it **cannot be
recovered from the event log alone**.

### Current contract

- One conversation view per session is the supported model.
- Multiple independently recoverable conversations inside a single session are
  **not** supported yet.
- Do not assume a conversation ID can be derived by reading message events.

### Future work (explicitly deferred)

If multiple conversations per session become a real requirement, a dedicated
prompt must add a durable association (for example a schema migration that adds
an optional `conversation_id` to message payloads, or a separate durable
conversation record). That change must preserve compatibility with historical
`{"text": ...}` payloads. It is not part of Prompt 25.

## What this is not

- Not a context assembler or relevance selector
- Not a memory retrieval system
- Not an agent loop or model provider
- Not tutoring/application logic

Infrastructure records and reconstructs. The model decides what matters.

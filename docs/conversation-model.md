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

Conversation identity lives on the conversation object and is associated with a
session. Message-level conversation IDs inside event payloads are deferred until
a real multi-conversation-per-session requirement forces a schema migration.

Historical events that already validate as `user_message` / `model_message`
remain readable and reconstructable.

## What this is not

- Not a context assembler or relevance selector
- Not a memory retrieval system
- Not an agent loop or model provider
- Not tutoring/application logic

Infrastructure records and reconstructs. The model decides what matters.

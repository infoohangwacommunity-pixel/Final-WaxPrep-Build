# Model Message Normalization

## Purpose

Prompt 30 converts WaxPrep's durable event history into the normalized
model-message contract defined in Prompt 29.

The event log remains the source of truth. Normalization does not change
recorded events, execute actions, contact a model provider, or introduce
application-specific workflows.

## Conversion rules

| Event kind | Normalized output |
|---|---|
| `user_message` | `USER` message with a text content block |
| `model_message` | `ASSISTANT` message with a text content block |
| `model_tool_request` | `ASSISTANT` message containing a `ToolRequest` |
| `action_result` | `TOOL` message linked to the originating request |
| Other event kinds | Ignored by this conversion |

Events are returned in ascending sequence order. All input events must
belong to one session and must have unique sequence numbers.

## Tool request and result pairing

Every event already has a unique event ID. A normalized `ToolRequest.id`
uses the ID of its originating `model_tool_request` event.

An `action_result` must reference exactly one preceding, unresolved
`model_tool_request` through `parent_id` or `cause_id`.

The request ID is copied into the normalized tool-result message's
`tool_call_id`. This preserves the relationship between the requested
action and the actual observation.

The converter never pairs a result with the most recent request merely
because it appears nearby in the event history.

The following histories are rejected:

- A result without a request link.
- A result linked to an unrelated event.
- A result linked to a request that appears later in event sequence.
- A result with conflicting links to multiple pending requests.
- A second result for a request that has already been completed.

Multiple outstanding requests are supported. Their results may arrive in
a different order from their requests when explicit event links identify
the correct origin.

A history may end with unresolved tool requests. Those requests are
preserved because the available history may be incomplete.

## Action result content

Tool-result content preserves the action status and the observed result.

Strings are retained as readable text. Other JSON-compatible values are
rendered as deterministic JSON, using sorted object keys.

The converter does not claim that a requested action succeeded. It
passes through the status and result actually recorded in the event.

## Compatibility

Prompt 30 does not change:

- `EventEnvelope` or its schema version
- Existing event payload schemas
- Existing event IDs or session IDs
- Storage backends or migrations
- Prompt 29's model contract

The existing `parent_id` and `cause_id` envelope fields are reused for
request/result correlation. No new payload field or database is introduced.

## Scope boundaries

This module does not execute tools, contact a model provider, implement
the agent loop, or decide which historical messages are relevant.

Those responsibilities remain separate from event-to-message
normalization.

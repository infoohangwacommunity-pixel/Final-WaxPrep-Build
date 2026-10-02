# WaxPrep Storage Abstraction

Prompt 21 defines the persistence boundary for WaxPrep.

This stage defines **what storage must provide**, not how storage is implemented.

There is intentionally no database, filesystem store, cache, or in-memory
backend in this stage.

## Why the abstraction exists

WaxPrep's agent/session code should not depend directly on a particular
persistence technology.

The dependency direction is:

```text
agent/session code
        |
        v
 EventStore / SessionStore
        |
        v
 concrete storage implementation
```

A later implementation can therefore change without changing the code that uses the storage contract.

## EventStore

`EventStore` represents durable event history.

It provides:

- `append`
- `read_range`
- `read_from_sequence`
- `count`

### append

Adds exactly one `EventEnvelope`.

The append is atomic:

- either the event becomes visible;
- or the store remains unchanged.

Events are append-only. The contract has no update or delete operation.

### Ordering

Each session has its own event sequence.

The first event has sequence `1`. Each following event must use the next sequence number.

Events returned by reads are ordered by ascending sequence.

### read_range

The range uses `start <= sequence < end` (inclusive start, exclusive end).

### read_from_sequence

The starting sequence is inclusive through the current end of the session history.

### count

Returns the number of events belonging to the specified session.

## SessionStore

`SessionStore` represents durable session identity and metadata.

It provides:

- `create`
- `get`
- `list`
- `update_metadata`

### create

Creates a new `SessionRecord`. Creating an existing session is a conflict.

### get

Returns the session record when it exists, or `None` when it does not.

### list

Returns all sessions in deterministic session-ID order.

### update_metadata

Replaces the complete metadata snapshot. Updating a missing session raises
`StorageNotFoundError`.

## Current scope

Prompt 21 defines interfaces, session record shape, exceptions, guarantees,
reusable contract tests, and documentation.

Prompt 21 does **not** define an in-memory backend, SQLite, PostgreSQL, an
event bus, subscriptions, projections, snapshots, agent-loop behavior, or
application logic.

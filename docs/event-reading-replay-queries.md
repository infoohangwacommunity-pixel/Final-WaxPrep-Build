# Event Reading, Replay and Queries

Prompt 26 adds a read/query layer over WaxPrep's existing EventStore.

The event history itself remains the responsibility of EventStore. This stage
does not create a second storage mechanism.

## Event queries

`EventQuery` represents filters over one session's event history.

Supported filters:

- event kind
- start timestamp
- end timestamp
- start sequence
- end sequence

Time boundaries use:

```text
start_time <= timestamp < end_time

Sequence boundaries use:

start_sequence <= sequence < end_sequence

An omitted end boundary means the query continues through the available history.

Event kinds can be supplied either as EventKind values or as their string forms.

Invalid kinds, invalid sequence values, naive timestamps, and inverted ranges are rejected with EventQueryError.

Query execution

query_events(...) reads from the existing EventStore and returns matching events in ascending sequence order.

The query layer does not modify events.

It does not manufacture missing events.

It does not execute actions.

The durable event log remains the source of truth.

Pagination

paginate_events(...) returns:

a tuple of matching events

an optional next_start_sequence cursor


Pagination uses event sequence as the continuation cursor.

The caller can pass the returned cursor into the next call:

page 1
    ↓
next_start_sequence
    ↓
page 2

The cursor is based on event sequence rather than a hidden database offset.

This means events can be paged without changing the underlying EventStore contract.

When the requested history range has been exhausted, the cursor is None.

A page can contain fewer events than the page size when matching events are sparse.

Replay

replay_events(...) is a simple ordered visitor mechanism.

It:

1. accepts already-recorded EventEnvelope values;


2. checks that they belong to one session;


3. requires strictly ascending sequence order;


4. calls the visitor once for each event.



Replay does not mean:

rerunning tools

re-executing actions

contacting the model

contacting the real runtime

reproducing a Temporal-style deterministic workflow


It is simply a way to walk recorded history deterministically.

Human-readable timeline

format_event_timeline(...) converts an ordered set of events into a readable timeline.

The timeline shows:

session ID

event count

sequence

timestamp

event kind

concise event-specific information


Tool requests show the tool name and argument keys rather than dumping the entire argument object.

This keeps the debugging representation smaller and avoids blindly printing arbitrary payload contents.

Relationship to EventStore

The dependency direction is:

Event history query/replay layer
            |
            v
        EventStore
            |
            v
  InMemoryEventStore / FileEventStore

Prompt 26 does not modify the existing EventStore interface.

The existing storage guarantees remain authoritative:

append-only events

immutable EventEnvelope values

gap-free session sequence

ascending read order

inclusive-start/exclusive-end sequence reads


Scope boundary

Prompt 26 does not implement:

the agent loop

model providers

runtime/tool execution

context assembly

memory retrieval

concurrency/locking improvements

databases

hosting

tutoring or educational application logic


Those belong to later stages.

# File Storage

## Purpose

Prompt 23 introduces WaxPrep's first durable storage implementation.

The backend stores data on the filesystem while implementing the existing
`EventStore` and `SessionStore` contracts.

It remains domain-neutral.

It does not implement sessions, conversations, turns, the agent loop,
runtime execution, model providers, tutoring, or application workflows.

## Data directory

The caller provides an absolute `data_dir`.

The storage implementation does not choose a directory inside the source
workspace.

A typical external layout is:

    /some/external/waxprep-data/
        wax_session_<uuidv7>/
            events.jsonl
            metadata.json

The exact parent directory is deployment-specific and must be supplied by the
caller.

## Event storage

Each session has an `events.jsonl` file.

Each line contains one complete serialized `EventEnvelope`.

Example:

    {"cause_id":null,"id":"wax_event_...","kind":"system_notice","parent_id":null,"payload":{"message":"hello"},"schema_version":2,"sequence":1,"session_id":"wax_session_...","timestamp":"2026-10-02T00:00:00Z"}
    {"cause_id":null,"id":"wax_event_...","kind":"system_notice","parent_id":null,"payload":{"message":"world"},"schema_version":2,"sequence":2,"session_id":"wax_session_...","timestamp":"2026-10-02T00:00:00Z"}

Events are append-only.

A successful append is written as one JSONL record and flushed to the
operating system with `fsync`.

The storage backend does not modify an existing event.

## Event sequence

The existing `EventStore` contract remains authoritative.

For each session:

    1
    2
    3
    4
    ...

A new event must use exactly the next sequence number.

Gaps, duplicates, and out-of-order appends are rejected.


## Concurrent writers and session locks

File-backed writes use a per-session operating-system file lock.

Before appending an event or changing session metadata, a writer must acquire
the lock associated with that session. The event sequence is checked while the
lock is held, so independent store instances cannot both approve the same next
sequence number.

The lock is non-blocking. If another writer holds the same session lock, the
attempt raises `StorageConflictError` with a message explaining that the session
is currently locked. The caller can retry the operation later.

Different sessions have separate locks and do not block one another.

The operating system releases a process-owned lock when its owning process exits.
Lock files are retained rather than deleted after each operation, because deleting
a lock file while another process is waiting or holding it can undermine
coordination.

This mechanism is intended for supported local filesystems. It does not claim to
provide distributed locking or guarantees for every network filesystem. Only one
writer should modify a given session at a time; competing writers must handle
`StorageConflictError` rather than assume their writes succeeded.

## Partial final-line recovery

A process can theoretically be interrupted while writing the final JSONL
record.

For example:

    {"sequence":1,...}
    {"sequence":2,"payload":

The incomplete final line is detected during reading.

WaxPrep:

1. preserves all earlier valid events;
2. reports the corrupted final line through `StorageCorruptionWarning`;
3. ignores that incomplete final record;
4. does not raise an unhandled JSON decoding exception.

Corruption in a non-final line is different. It cannot safely be interpreted
as a simple partial final write and therefore raises `StorageCorruptionError`.

## Session metadata

Each session has a separate `metadata.json` file.

The file contains:

    {
      "id": "wax_session_<uuidv7>",
      "metadata": {
        ...
      }
    }

Metadata replacement uses an atomic temporary-file write followed by
replacement of the existing metadata file.

## Durability

Event appends flush and `fsync` the event file.

Metadata writes use a temporary file, `fsync`, and atomic replacement.

These mechanisms reduce the risk of losing successfully written records when
the process or operating system is interrupted.

They do not claim to provide a distributed database, multi-process transaction
system, or network filesystem guarantee.

## Relationship to the storage contracts

The file backend must obey the same observable contracts as the in-memory
backend.

The reusable contract tests in `tests/storage_contracts.py` are therefore
executed against both implementations.

This keeps higher layers independent of the persistence technology.

## Scope boundary

Prompt 23 does not introduce:

- a session lifecycle;
- conversation or turn management;
- an agent loop;
- model providers;
- runtime execution;
- a database;
- an event bus;
- tutoring logic;
- application-specific workflows;
- deployment configuration.

Those capabilities belong to later stages.


---

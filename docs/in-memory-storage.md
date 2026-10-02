# WaxPrep In-Memory Storage

Prompt 22 provides the first concrete implementation of the storage
abstractions defined in Prompt 21.

## Purpose

The in-memory backend exists for:

- tests;
- local experiments;
- fast development;
- exercising the storage contracts before durable persistence exists.

It is not durable storage.

All records disappear when the Python process exits.

## Implementations

The module `waxprep.in_memory_storage` provides:

- `InMemoryEventStore`
- `InMemorySessionStore`

Both implement the interfaces from `waxprep.storage`.

## Event storage

`InMemoryEventStore` keeps event histories separately for each session.

For every session:

1. the first event must have sequence `1`;
2. every following event must use the next sequence;
3. gaps are rejected;
4. duplicate or out-of-order sequences are rejected;
5. failed appends leave the existing history unchanged;
6. reads return events in ascending sequence order.

A lock protects each store instance so individual operations observe a
consistent state.

## Session storage

`InMemorySessionStore` keeps session records indexed by their immutable
session ID.

It supports:

- create;
- get;
- deterministic list;
- complete metadata replacement.

Returned records are immutable snapshots.

## Contract testing

The reusable tests in `tests/storage_contracts.py` are run against both
in-memory implementations.

This is important because the in-memory backend must obey the same observable
behavior required of future storage implementations.

## Scope boundary

This stage intentionally does not add:

- SQLite;
- PostgreSQL;
- filesystem persistence;
- event buses;
- subscriptions;
- projections;
- snapshots;
- agent-loop behavior;
- model integration;
- tutoring/application logic.

Durable file-based storage belongs to the next explicitly authorized stage.

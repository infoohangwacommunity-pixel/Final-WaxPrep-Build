# WaxPrep Event Schema Versioning

WaxPrep events are durable records. Their structure may evolve as the project
develops, but older records must remain readable.

## Current version

The current event schema version is:

```text
2
```

Every newly created `EventEnvelope` uses the current schema version.

## Loading an older event

Older events are migrated in memory before they are validated as current events.

The loading flow is:

```text
JSON event
    ↓
parse
    ↓
read schema_version
    ↓
run migrations
    ↓
current schema
    ↓
validate EventEnvelope
```

Migration happens during deserialization. The original stored event is not silently rewritten as part of loading.

## Migration chain

Migrations are keyed by the schema version they migrate from.

For example:

```text
v1 → v2
v2 → v3
v3 → v4
```

When an event is loaded from version 1 while the current version is 4, the system applies:

```text
v1 → v2 → v3 → v4
```

one migration at a time.

Each migration must advance the schema version.

## Current migration

Prompt 18 used a temporary placeholder event kind.

Prompt 19 replaced that placeholder with the domain-neutral event taxonomy.

The Prompt 20 migration therefore converts a version 1 placeholder event into a version 2 system_notice event.

The old placeholder payload is preserved as deterministic JSON inside the system notice message.

This keeps the historical event readable without adding the old placeholder kind back into the current event taxonomy.

## Never edit old migrations

Once a migration has been released, never edit it.

If the schema changes again, add a new migration:

```text
v1 → v2   existing migration; do not edit
v2 → v3   new migration
```

Old migrations are part of the historical compatibility contract.

Changing an old migration could make previously readable records behave differently after an upgrade.

## Future schema versions

If an event has a schema version newer than the running WaxPrep version, loading fails.

WaxPrep must not silently downgrade or discard fields from a newer event format.

A future version should be handled by adding support for the new migration chain before attempting to load those records.

## Scope

This document covers event schema evolution only.

It does not define:

- event storage;
- databases;
- an event bus;
- agent-loop behavior;
- runtime execution;
- permissions;
- application workflows;
- tutoring behavior.

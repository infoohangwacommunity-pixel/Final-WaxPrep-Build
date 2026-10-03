# Session Lifecycle

## What a session is

A session is the durable container for one piece of ongoing agent work.

It records:

- identity (`wax_session_<uuidv7>`)
- creation time
- current status
- configuration snapshot at creation
- optional workspace reference

Conversation, turns, model providers, and the agent loop are deliberately out of
scope for this stage (Prompt 25+).

## Statuses

| Status | Meaning |
|--------|---------|
| `created` | Session exists; work has not started |
| `running` | Session is actively progressing |
| `waiting` | Session is blocked on external input or a condition |
| `finished` | Work completed successfully (terminal) |
| `failed` | Work ended due to failure (terminal) |
| `cancelled` | Work was intentionally stopped (terminal) |

## Transition table

| From | Allowed to |
|------|------------|
| `created` | `running`, `failed`, `cancelled` |
| `running` | `waiting`, `finished`, `failed`, `cancelled` |
| `waiting` | `running`, `failed`, `cancelled` |
| `finished` | _(none)_ |
| `failed` | _(none)_ |
| `cancelled` | _(none)_ |

Rules:

- Terminal statuses never leave their state.
- A status cannot transition to itself.
- `created` cannot jump directly to `finished` or `waiting`.
- `waiting` cannot jump directly to `finished`; it must resume `running` first.

## Creation versus transitions

Creating a session establishes the initial `created` status in the session store.

Creation does **not** emit a `state_change` event (there is no previous status).

Every successful transition after creation:

1. Appends a `state_change` event (`state=session.status`, previous/new values).
2. Updates session metadata with the new status.

## Persistence ordering and limitations

Write order for a transition:

1. EventStore append
2. SessionStore metadata update

If the event append fails, neither side is advanced by the lifecycle call.

If the metadata update fails after a successful event append, the event history
contains the transition while metadata may still show the previous status. The
service raises an error and does not report success. The current storage
interfaces do not provide a cross-store transaction.

In-process locking serializes transitions within one service instance. This does
not claim cross-process safety.

## Event/metadata mismatch recovery

If an event append succeeds and the following metadata update fails, the event
history is ahead of the session metadata. Operators can:

1. Read the latest `state_change` event for the session.
2. Re-apply the metadata update to match `new_value`.
3. Or surface the inconsistency for manual repair.

The lifecycle service does not hide the failure and does not claim a cross-store
transaction.

## Deferred

- Conversations and turns (Prompt 25+)
- Agent loop, model providers, tools
- Workspace subsystem
- Cross-store distributed transactions

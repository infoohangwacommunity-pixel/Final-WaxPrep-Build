# WaxPrep Event Taxonomy

WaxPrep records durable events using the common Event Envelope.

The Event Envelope provides the shared structure for every event. This document
defines the event kinds that are currently recognized by the foundation.

All event kinds are domain-neutral. They do not describe tutoring, education,
websites, reminders, or any other application-specific workflow.

| Event kind | Meaning | Emitted when |
|---|---|---|
| `user_message` | Message received from an external user/source | A user or external interaction sends a message into the agent |
| `model_message` | Message produced by the model | The model produces a message intended for the interaction |
| `model_tool_request` | Action requested by the model | The model asks the runtime/world boundary to perform an action |
| `action_result` | Result observed from an action | The runtime reports what happened after an action was attempted |
| `error` | Error information | A component reports an error relevant to the recorded interaction |
| `state_change` | Change in tracked state | A tracked system state changes from one value to another |
| `system_notice` | System-generated notice | The system needs to record a general system-level notice |
| `permission_decision` | Permission decision placeholder | A permission boundary records a permission decision or pending decision |

## Important distinction

A `model_tool_request` records what the model requested.

It does not prove that the action happened or succeeded.

An `action_result` records the result reported by the runtime.

Therefore:

```text
model_tool_request
        ↓
world/runtime
        ↓
action_result
```

The action result is the execution observation.

## Domain neutrality

Event kinds describe general agent activity.

They must not contain application-specific concepts such as:

- student
- teacher
- lesson
- examination
- JAMB
- WAEC
- tutoring workflow
- product-specific intent

Those belong to later application/domain layers.

## Scope

This taxonomy does not define:

- an event bus
- an event database
- an agent loop
- runtime execution
- a permission system
- application workflows
- serialization version migrations

Those capabilities belong to later implementation stages.

"""Convert durable WaxPrep events into normalized model messages.

The event log remains the source of truth. This module transforms recorded
messages and tool execution observations into the vendor-neutral model contract.

Tool results must explicitly reference their originating tool-request event
through parent_id or cause_id. No positional or most-recent-request matching
is permitted.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.model_client import (
    ModelMessage,
    ModelMessageRole,
    TextContentBlock,
    ToolRequest,
)


class ModelMessageNormalizationError(ValueError):
    """Raised when event history cannot safely become model messages."""


def _json_compatible(value: object) -> Any:
    """Convert frozen event payload values into JSON-compatible values."""

    if isinstance(value, Mapping):
        return {key: _json_compatible(item) for key, item in value.items()}

    if isinstance(value, (tuple, list)):
        return [_json_compatible(item) for item in value]

    if value is None or isinstance(value, (str, bool, int, float)):
        return value

    raise ModelMessageNormalizationError(
        f"Unsupported event result value: {type(value).__name__}."
    )


def _result_text(status: str, result: object) -> str:
    """Render an observed action result without losing its status."""

    normalized_result = _json_compatible(result)

    if isinstance(normalized_result, str):
        rendered_result = normalized_result
    else:
        rendered_result = json.dumps(
            normalized_result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    return f"Status: {status}\nResult: {rendered_result}"


def model_messages_from_events(
    events: Sequence[EventEnvelope],
) -> tuple[ModelMessage, ...]:
    """Convert recorded events into normalized model messages.

    Events must belong to one session and have unique sequence numbers.
    Input order does not matter; output follows ascending event sequence.

    User messages become USER messages. Model messages and tool requests
    become ASSISTANT messages. Action results become TOOL messages.

    An action result must link to exactly one preceding, unresolved
    model_tool_request through parent_id or cause_id. The originating
    request's event ID becomes both ToolRequest.id and tool_call_id.

    Non-message events other than action_result are ignored. Unresolved
    tool requests are preserved in the output because a history may end
    after a request but before its execution result has been recorded.

    Raises:
        ModelMessageNormalizationError: If events cross session boundaries,
            sequence numbers repeat, or an action result has no unambiguous
            preceding tool request.
    """

    if not isinstance(events, Sequence):
        raise ModelMessageNormalizationError(
            "events must be a sequence of EventEnvelope values."
        )

    ordered_events: list[EventEnvelope] = []

    for event in events:
        if not isinstance(event, EventEnvelope):
            raise ModelMessageNormalizationError(
                "events must contain EventEnvelope values."
            )
        ordered_events.append(event)

    if not ordered_events:
        return ()

    session_ids = {event.session_id for event in ordered_events}
    if len(session_ids) != 1:
        raise ModelMessageNormalizationError(
            "All events must belong to the same session."
        )

    ordered_events.sort(key=lambda event: event.sequence)

    sequences = [event.sequence for event in ordered_events]
    if len(sequences) != len(set(sequences)):
        raise ModelMessageNormalizationError(
            "Event sequence numbers must be unique within the history."
        )

    messages: list[ModelMessage] = []
    pending_requests: dict[str, ToolRequest] = {}

    for event in ordered_events:
        kind = EventKind(event.kind)
        payload = event.payload

        if kind is EventKind.USER_MESSAGE:
            messages.append(
                ModelMessage(
                    role=ModelMessageRole.USER,
                    content=(TextContentBlock(text=payload["text"]),),
                )
            )
            continue

        if kind is EventKind.MODEL_MESSAGE:
            messages.append(
                ModelMessage(
                    role=ModelMessageRole.ASSISTANT,
                    content=(TextContentBlock(text=payload["text"]),),
                )
            )
            continue

        if kind is EventKind.MODEL_TOOL_REQUEST:
            request = ToolRequest(
                id=event.id,
                name=payload["tool_name"],
                arguments=payload["arguments"],
            )

            pending_requests[event.id] = request

            messages.append(
                ModelMessage(
                    role=ModelMessageRole.ASSISTANT,
                    content=(),
                    tool_requests=(request,),
                )
            )
            continue

        if kind is not EventKind.ACTION_RESULT:
            continue

        linked_ids = {
            linked_id
            for linked_id in (event.parent_id, event.cause_id)
            if linked_id is not None
        }

        matching_ids = linked_ids.intersection(pending_requests)

        if len(matching_ids) != 1:
            raise ModelMessageNormalizationError(
                f"Action result event {event.id!r} must link through "
                "parent_id or cause_id to exactly one preceding, "
                "unresolved model_tool_request event."
            )

        request_id = next(iter(matching_ids))
        request = pending_requests.pop(request_id)

        messages.append(
            ModelMessage(
                role=ModelMessageRole.TOOL,
                name=request.name,
                tool_call_id=request.id,
                content=(
                    TextContentBlock(
                        text=_result_text(
                            status=payload["status"],
                            result=payload["result"],
                        )
                    ),
                ),
            )
        )

    return tuple(messages)


__all__ = [
    "ModelMessageNormalizationError",
    "model_messages_from_events",
]

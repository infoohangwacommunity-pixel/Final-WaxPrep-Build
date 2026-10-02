"""Typed event payloads and taxonomy for WaxPrep."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, TypedDict


class InvalidEventEnvelope(ValueError):
    """Raised when event-envelope data fails validation."""


class EventKind(StrEnum):
    """Kinds of events that WaxPrep can record."""

    USER_MESSAGE = "user_message"
    MODEL_MESSAGE = "model_message"
    MODEL_TOOL_REQUEST = "model_tool_request"
    ACTION_RESULT = "action_result"
    ERROR = "error"
    STATE_CHANGE = "state_change"
    SYSTEM_NOTICE = "system_notice"
    PERMISSION_DECISION = "permission_decision"


class UserMessagePayload(TypedDict):
    """Payload emitted when a user message is received."""

    text: str


class ModelMessagePayload(TypedDict):
    """Payload emitted when the model produces a message."""

    text: str


class ModelToolRequestPayload(TypedDict):
    """Payload emitted when the model requests an action through a tool."""

    tool_name: str
    arguments: dict[str, object]


class ActionResultPayload(TypedDict):
    """Payload emitted when an action execution produces an observation."""

    status: str
    result: object


class ErrorPayload(TypedDict):
    """Payload emitted when an operation or component reports an error."""

    error_type: str
    message: str


class StateChangePayload(TypedDict):
    """Payload emitted when tracked system state changes."""

    state: str
    previous_value: object
    new_value: object


class SystemNoticePayload(TypedDict):
    """Payload emitted when the system reports a system-level notice."""

    message: str


class PermissionDecisionPayload(TypedDict):
    """Placeholder payload for a permission decision."""

    decision: str


EVENT_KINDS: Final[tuple[EventKind, ...]] = (
    EventKind.USER_MESSAGE,
    EventKind.MODEL_MESSAGE,
    EventKind.MODEL_TOOL_REQUEST,
    EventKind.ACTION_RESULT,
    EventKind.ERROR,
    EventKind.STATE_CHANGE,
    EventKind.SYSTEM_NOTICE,
    EventKind.PERMISSION_DECISION,
)


def validate_event_payload(
    kind: EventKind,
    payload: object,
) -> None:
    """Validate the payload shape required by an event kind."""

    if not isinstance(payload, dict):
        raise InvalidEventEnvelope("event payload must be an object.")

    if kind is EventKind.USER_MESSAGE:
        _require_exact_fields(payload, {"text"})
        _require_string(payload, "text")
        return

    if kind is EventKind.MODEL_MESSAGE:
        _require_exact_fields(payload, {"text"})
        _require_string(payload, "text")
        return

    if kind is EventKind.MODEL_TOOL_REQUEST:
        _require_exact_fields(payload, {"tool_name", "arguments"})
        _require_string(payload, "tool_name")

        arguments = payload["arguments"]
        if not isinstance(arguments, dict):
            raise InvalidEventEnvelope(
                "model tool request arguments must be an object."
            )
        return

    if kind is EventKind.ACTION_RESULT:
        _require_exact_fields(payload, {"status", "result"})
        _require_string(payload, "status")
        return

    if kind is EventKind.ERROR:
        _require_exact_fields(payload, {"error_type", "message"})
        _require_string(payload, "error_type")
        _require_string(payload, "message")
        return

    if kind is EventKind.STATE_CHANGE:
        _require_exact_fields(payload, {"state", "previous_value", "new_value"})
        _require_string(payload, "state")
        return

    if kind is EventKind.SYSTEM_NOTICE:
        _require_exact_fields(payload, {"message"})
        _require_string(payload, "message")
        return

    if kind is EventKind.PERMISSION_DECISION:
        _require_exact_fields(payload, {"decision"})
        _require_string(payload, "decision")
        return

    raise InvalidEventEnvelope(f"unsupported event kind: {kind!s}.")


def _require_exact_fields(
    payload: dict[str, object],
    expected: set[str],
) -> None:
    """Require exactly the declared payload fields."""

    if set(payload) != expected:
        raise InvalidEventEnvelope(
            "event payload fields do not exactly match the required schema."
        )


def _require_string(
    payload: dict[str, object],
    field_name: str,
) -> None:
    """Require a string payload field."""

    if not isinstance(payload[field_name], str):
        raise InvalidEventEnvelope(
            f"event payload field {field_name!r} must be a string."
        )

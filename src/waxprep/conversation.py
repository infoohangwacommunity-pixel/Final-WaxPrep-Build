"""Conversation representation for WaxPrep.

A conversation is an ordered view of recorded user and model messages.
The durable event log is the source of truth; a conversation is reconstructed
from stored ``user_message`` and ``model_message`` events.

Message payloads remain ``{"text": ...}`` for compatibility with existing
stored events. Conversation identity is carried by the conversation object and
its association to a session, not by altering historical message schemas.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.identifiers import InvalidWaxId, WaxIdKind, parse_wax_id
from waxprep.storage import EventStore

_MESSAGE_KINDS: Final[frozenset[EventKind]] = frozenset(
    {
        EventKind.USER_MESSAGE,
        EventKind.MODEL_MESSAGE,
    }
)


class MessageRole(StrEnum):
    """Role of a conversation message."""

    USER = "user"
    MODEL = "model"


class InvalidConversation(ValueError):
    """Raised when conversation data fails validation."""


def _validate_conversation_id(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidConversation("conversation id must be a string.")

    try:
        parsed = parse_wax_id(value)
    except InvalidWaxId as exc:
        raise InvalidConversation(
            "conversation id must be a valid WaxPrep conversation ID."
        ) from exc

    if parsed.kind is not WaxIdKind.CONVERSATION:
        raise InvalidConversation("conversation id must be a WaxPrep conversation ID.")

    return value


def _validate_session_id(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidConversation("session_id must be a string.")

    try:
        parsed = parse_wax_id(value)
    except InvalidWaxId as exc:
        raise InvalidConversation(
            "session_id must be a valid WaxPrep session ID."
        ) from exc

    if parsed.kind is not WaxIdKind.SESSION:
        raise InvalidConversation("session_id must be a WaxPrep session ID.")

    return value


def _role_for_kind(kind: EventKind) -> MessageRole:
    if kind is EventKind.USER_MESSAGE:
        return MessageRole.USER
    if kind is EventKind.MODEL_MESSAGE:
        return MessageRole.MODEL
    raise InvalidConversation(f"event kind is not a conversation message: {kind!s}.")


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    """One user or model message reconstructed from a durable event."""

    role: MessageRole
    text: str
    event_id: str
    sequence: int
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.role, MessageRole):
            raise InvalidConversation("message role must be a MessageRole.")

        if not isinstance(self.text, str):
            raise InvalidConversation("message text must be a string.")

        if not isinstance(self.event_id, str):
            raise InvalidConversation("message event_id must be a string.")

        try:
            parsed = parse_wax_id(self.event_id)
        except InvalidWaxId as exc:
            raise InvalidConversation(
                "message event_id must be a valid WaxPrep event ID."
            ) from exc

        if parsed.kind is not WaxIdKind.EVENT:
            raise InvalidConversation("message event_id must be a WaxPrep event ID.")

        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 1
        ):
            raise InvalidConversation("message sequence must be a positive integer.")

        if not isinstance(self.timestamp, datetime):
            raise InvalidConversation("message timestamp must be a datetime.")

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise InvalidConversation("message timestamp must be timezone-aware.")


# fix typo from exc -> exc after write


@dataclass(frozen=True, slots=True)
class Conversation:
    """Ordered conversation view reconstructed from durable events."""

    id: str
    session_id: str
    messages: tuple[ConversationMessage, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_conversation_id(self.id))
        object.__setattr__(self, "session_id", _validate_session_id(self.session_id))

        if not isinstance(self.messages, tuple):
            raise InvalidConversation("messages must be a tuple.")

        for message in self.messages:
            if not isinstance(message, ConversationMessage):
                raise InvalidConversation(
                    "messages must contain ConversationMessage values."
                )


def conversation_from_events(
    events: Sequence[EventEnvelope],
    *,
    conversation_id: str,
    session_id: str,
) -> Conversation:
    """Rebuild an ordered conversation from durable session events.

    Only ``user_message`` and ``model_message`` events belonging to
    ``session_id`` are included. Order follows ascending event sequence.
    Other event kinds are ignored.

    Message payloads are expected to contain ``text`` (schema versions that
    already validate this). Historical events with only ``text`` remain valid.
    """

    conversation_id = _validate_conversation_id(conversation_id)
    session_id = _validate_session_id(session_id)

    messages: list[ConversationMessage] = []

    for event in events:
        if not isinstance(event, EventEnvelope):
            raise InvalidConversation("events must contain EventEnvelope values.")

        if event.session_id != session_id:
            continue

        kind = (
            event.kind if isinstance(event.kind, EventKind) else EventKind(event.kind)
        )
        if kind not in _MESSAGE_KINDS:
            continue

        text = event.payload.get("text")
        if not isinstance(text, str):
            raise InvalidConversation(
                f"message event {event.id!r} is missing string text."
            )

        messages.append(
            ConversationMessage(
                role=_role_for_kind(kind),
                text=text,
                event_id=event.id,
                sequence=event.sequence,
                timestamp=event.timestamp,
            )
        )

    messages.sort(key=lambda message: message.sequence)

    return Conversation(
        id=conversation_id,
        session_id=session_id,
        messages=tuple(messages),
    )


def conversation_from_event_store(
    event_store: EventStore,
    *,
    conversation_id: str,
    session_id: str,
) -> Conversation:
    """Rebuild a conversation by reading the full event history for a session."""

    events = event_store.read_from_sequence(session_id, 1)
    return conversation_from_events(
        events,
        conversation_id=conversation_id,
        session_id=session_id,
    )


__all__ = [
    "Conversation",
    "ConversationMessage",
    "InvalidConversation",
    "MessageRole",
    "conversation_from_event_store",
    "conversation_from_events",
]

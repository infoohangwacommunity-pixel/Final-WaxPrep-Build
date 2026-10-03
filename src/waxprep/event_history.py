"""Read, filter, replay, and display WaxPrep event history."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TextIO

from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.storage import EventStore


class EventQueryError(ValueError):
    """Raised when an event-history query is invalid."""


class EventReplayError(ValueError):
    """Raised when an event sequence cannot be replayed safely."""


@dataclass(frozen=True, slots=True)
class EventQuery:
    """Immutable filters for a session's event history.

    Sequence and time ranges use an inclusive start and exclusive end.
    """

    kind: EventKind | str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    start_sequence: int = 1
    end_sequence: int | None = None

    def __post_init__(self) -> None:
        normalized_kind: EventKind | None = None

        if self.kind is not None:
            try:
                normalized_kind = EventKind(self.kind)
            except ValueError as exc:
                raise EventQueryError(f"unknown event kind: {self.kind!r}.") from exc

        start_time = _normalize_time(self.start_time, "start_time")
        end_time = _normalize_time(self.end_time, "end_time")

        start_sequence = _validate_sequence(
            self.start_sequence,
            "start_sequence",
        )

        end_sequence = self.end_sequence

        if end_sequence is not None:
            end_sequence = _validate_sequence(
                end_sequence,
                "end_sequence",
            )

            if end_sequence < start_sequence:
                raise EventQueryError("end_sequence must be >= start_sequence.")

        if start_time is not None and end_time is not None and end_time < start_time:
            raise EventQueryError("end_time must be >= start_time.")

        object.__setattr__(self, "kind", normalized_kind)
        object.__setattr__(self, "start_time", start_time)
        object.__setattr__(self, "end_time", end_time)
        object.__setattr__(self, "start_sequence", start_sequence)
        object.__setattr__(self, "end_sequence", end_sequence)

    def matches(self, event: EventEnvelope) -> bool:
        """Return whether one event satisfies every configured filter."""

        if event.sequence < self.start_sequence:
            return False

        if self.end_sequence is not None and event.sequence >= self.end_sequence:
            return False

        if self.kind is not None:
            event_kind = (
                event.kind
                if isinstance(event.kind, EventKind)
                else EventKind(event.kind)
            )
            if event_kind is not self.kind:
                return False

        if self.start_time is not None and event.timestamp < self.start_time:
            return False

        return not (self.end_time is not None and event.timestamp >= self.end_time)


@dataclass(frozen=True, slots=True)
class EventPage:
    """One page of matching events and an optional sequence cursor."""

    events: tuple[EventEnvelope, ...]
    next_start_sequence: int | None


def query_events(
    event_store: EventStore,
    session_id: str,
    *,
    kind: EventKind | str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    start_sequence: int = 1,
    end_sequence: int | None = None,
) -> tuple[EventEnvelope, ...]:
    """Return matching events from one session in ascending sequence order."""

    query = EventQuery(
        kind=kind,
        start_time=start_time,
        end_time=end_time,
        start_sequence=start_sequence,
        end_sequence=end_sequence,
    )

    events = event_store.read_from_sequence(
        session_id,
        query.start_sequence,
    )

    return tuple(event for event in events if query.matches(event))


def paginate_events(
    event_store: EventStore,
    session_id: str,
    *,
    page_size: int,
    start_sequence: int = 1,
    end_sequence: int | None = None,
    kind: EventKind | str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> EventPage:
    """Return up to ``page_size`` matching events from one session.

    Pagination uses the event sequence as its cursor. The returned cursor is
    the first sequence that was not scanned, so callers can continue without
    duplicating or skipping matching events. ``None`` means the query range
    has been exhausted.
    """

    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
        raise EventQueryError("page_size must be a positive integer.")

    query = EventQuery(
        kind=kind,
        start_time=start_time,
        end_time=end_time,
        start_sequence=start_sequence,
        end_sequence=end_sequence,
    )

    history_count = event_store.count(session_id)

    effective_end = history_count + 1

    if query.end_sequence is not None:
        effective_end = min(
            effective_end,
            query.end_sequence,
        )

    cursor = query.start_sequence

    if cursor >= effective_end:
        return EventPage(
            events=(),
            next_start_sequence=None,
        )

    matches: list[EventEnvelope] = []

    while cursor < effective_end:
        scan_end = min(
            cursor + max(page_size, 64),
            effective_end,
        )

        events = event_store.read_range(
            session_id,
            cursor,
            scan_end,
        )

        if not events:
            return EventPage(
                events=tuple(matches),
                next_start_sequence=None,
            )

        for event in events:
            if not query.matches(event):
                continue

            matches.append(event)

            if len(matches) >= page_size:
                candidate = event.sequence + 1
                next_start = None if candidate >= effective_end else candidate

                return EventPage(
                    events=tuple(matches),
                    next_start_sequence=next_start,
                )

        cursor = scan_end

    return EventPage(
        events=tuple(matches),
        next_start_sequence=None,
    )


EventVisitor = Callable[[EventEnvelope], None]


def replay_events(
    events: Iterable[EventEnvelope],
    visitor: EventVisitor,
) -> None:
    """Visit events in ascending order without executing actions."""

    previous_sequence = 0
    session_id: str | None = None

    for event in events:
        if not isinstance(event, EventEnvelope):
            raise EventReplayError("replay input must contain EventEnvelope values.")

        if session_id is None:
            session_id = event.session_id
        elif event.session_id != session_id:
            raise EventReplayError("replay input contains multiple session IDs.")

        if event.sequence <= previous_sequence:
            raise EventReplayError(
                "replay input must be in strictly ascending sequence order."
            )

        visitor(event)
        previous_sequence = event.sequence


def format_event_timeline(
    events: Iterable[EventEnvelope],
    *,
    session_id: str | None = None,
) -> str:
    """Format an ordered event sequence as a human-readable timeline."""

    event_list = tuple(events)

    _validate_replay_input(event_list)

    resolved_session_id = session_id

    if resolved_session_id is None and event_list:
        resolved_session_id = event_list[0].session_id

    lines = [
        "WaxPrep Session Timeline",
        f"Session: {resolved_session_id or '<unknown>'}",
        f"Events: {len(event_list)}",
    ]

    if not event_list:
        lines.append("(no events)")
        return "\n".join(lines)

    for event in event_list:
        timestamp = event.timestamp.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        kind_label = (
            event.kind.value if isinstance(event.kind, EventKind) else event.kind
        )
        lines.append(f"#{event.sequence:<4} {timestamp}  {kind_label}")
        lines.append(f"    {_summarize_event(event)}")

    return "\n".join(lines)


def print_event_timeline(
    events: Iterable[EventEnvelope],
    *,
    session_id: str | None = None,
    file: TextIO | None = None,
) -> None:
    """Print a human-readable event timeline."""

    print(
        format_event_timeline(
            events,
            session_id=session_id,
        ),
        file=file,
    )


def _validate_replay_input(
    events: Iterable[EventEnvelope],
) -> None:
    """Validate ordering and session consistency."""

    previous_sequence = 0
    session_id: str | None = None

    for event in events:
        if not isinstance(event, EventEnvelope):
            raise EventReplayError("replay input must contain EventEnvelope values.")

        if session_id is None:
            session_id = event.session_id
        elif event.session_id != session_id:
            raise EventReplayError("replay input contains multiple session IDs.")

        if event.sequence <= previous_sequence:
            raise EventReplayError(
                "replay input must be in strictly ascending sequence order."
            )

        previous_sequence = event.sequence


def _validate_sequence(
    value: object,
    field_name: str,
) -> int:
    """Validate a positive integer sequence value."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EventQueryError(f"{field_name} must be a positive integer.")

    return value


def _normalize_time(
    value: datetime | None,
    field_name: str,
) -> datetime | None:
    """Normalize a timezone-aware filter boundary to UTC."""

    if value is None:
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        raise EventQueryError(f"{field_name} must be timezone-aware.")

    return value.astimezone(UTC)


def _summarize_event(event: EventEnvelope) -> str:
    """Create a concise, kind-aware event summary."""

    payload = event.payload

    if not isinstance(payload, Mapping):
        return "Payload: <unavailable>"

    kind = event.kind if isinstance(event.kind, EventKind) else EventKind(event.kind)

    if kind in {
        EventKind.USER_MESSAGE,
        EventKind.MODEL_MESSAGE,
    }:
        return f"Message: {_preview(payload['text'])}"

    if kind is EventKind.MODEL_TOOL_REQUEST:
        arguments = payload["arguments"]

        if isinstance(arguments, Mapping):
            keys = ", ".join(sorted(str(key) for key in arguments))
        else:
            keys = "<invalid>"

        return f"Tool: {payload['tool_name']}; argument_keys=[{keys}]"

    if kind is EventKind.ACTION_RESULT:
        return f"Status: {payload['status']}"

    if kind is EventKind.ERROR:
        return f"Error: {payload['error_type']}; {_preview(payload['message'])}"

    if kind is EventKind.STATE_CHANGE:
        return (
            f"State: {payload['state']}; "
            f"{payload['previous_value']} -> "
            f"{payload['new_value']}"
        )

    if kind is EventKind.SYSTEM_NOTICE:
        return f"Notice: {_preview(payload['message'])}"

    if kind is EventKind.PERMISSION_DECISION:
        return f"Decision: {payload['decision']}"

    return "Payload: <unknown event kind>"


def _preview(
    value: object,
    limit: int = 200,
) -> str:
    """Render one field without allowing unbounded output."""

    text = str(value).replace(
        "\n",
        "\\n",
    )

    if len(text) <= limit:
        return text

    return f"{text[: limit - 1]}…"


__all__ = [
    "EventPage",
    "EventQuery",
    "EventQueryError",
    "EventReplayError",
    "EventVisitor",
    "format_event_timeline",
    "paginate_events",
    "print_event_timeline",
    "query_events",
    "replay_events",
]

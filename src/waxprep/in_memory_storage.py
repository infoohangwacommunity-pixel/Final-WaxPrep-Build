"""In-memory storage implementations for WaxPrep.

This module provides a temporary, process-local implementation of the
EventStore and SessionStore contracts.

The data is intentionally non-durable: it disappears when the Python process
ends. Durable storage belongs to a later implementation stage.
"""

from __future__ import annotations

from collections.abc import Mapping
from threading import RLock

from waxprep.event import EventEnvelope
from waxprep.storage import (
    SessionRecord,
    StorageConflictError,
    StorageNotFoundError,
    _validate_session_id,
)


def _validate_sequence(sequence: object, field_name: str) -> int:
    """Validate a positive integer sequence value."""

    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValueError(f"{field_name} must be a positive integer.")

    return sequence


class InMemoryEventStore:
    """Process-local append-only event store.

    Events are stored separately for each session. Every session's sequence
    must begin at 1 and advance by exactly one for each successful append.

    A re-entrant lock protects all mutations and reads so each public
    operation observes a consistent store state.
    """

    def __init__(self) -> None:
        self._events: dict[str, list[EventEnvelope]] = {}
        self._lock = RLock()

    def append(self, event: EventEnvelope) -> None:
        """Atomically append one event at the next required sequence."""

        if not isinstance(event, EventEnvelope):
            raise TypeError("event must be an EventEnvelope.")

        session_id = _validate_session_id(event.session_id)

        with self._lock:
            session_events = self._events.setdefault(session_id, [])
            expected_sequence = len(session_events) + 1

            if event.sequence != expected_sequence:
                raise StorageConflictError(
                    "event sequence must be the next gap-free sequence "
                    f"for session {session_id!r}: expected "
                    f"{expected_sequence}, got {event.sequence}."
                )

            session_events.append(event)

    def read_range(
        self,
        session_id: str,
        start_sequence: int,
        end_sequence: int,
    ) -> tuple[EventEnvelope, ...]:
        """Read ``start_sequence <= sequence < end_sequence``."""

        session_id = _validate_session_id(session_id)
        start_sequence = _validate_sequence(start_sequence, "start_sequence")
        end_sequence = _validate_sequence(end_sequence, "end_sequence")

        if end_sequence < start_sequence:
            raise ValueError("end_sequence must be >= start_sequence.")

        with self._lock:
            session_events = self._events.get(session_id, ())
            return tuple(
                event
                for event in session_events
                if start_sequence <= event.sequence < end_sequence
            )

    def read_from_sequence(
        self,
        session_id: str,
        start_sequence: int,
    ) -> tuple[EventEnvelope, ...]:
        """Read from ``start_sequence`` through the current session end."""

        session_id = _validate_session_id(session_id)
        start_sequence = _validate_sequence(start_sequence, "start_sequence")

        with self._lock:
            session_events = self._events.get(session_id, ())
            return tuple(
                event for event in session_events if event.sequence >= start_sequence
            )

    def count(self, session_id: str) -> int:
        """Return the number of events stored for one session."""

        session_id = _validate_session_id(session_id)

        with self._lock:
            return len(self._events.get(session_id, ()))

    def __len__(self) -> int:
        """Return the total number of events across all sessions."""

        with self._lock:
            return sum(len(events) for events in self._events.values())


class InMemorySessionStore:
    """Process-local session store.

    Session records are kept by immutable session ID. Metadata replacement
    creates a new immutable SessionRecord snapshot.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = RLock()

    def create(self, session: SessionRecord) -> None:
        """Atomically create a session unless its ID already exists."""

        if not isinstance(session, SessionRecord):
            raise TypeError("session must be a SessionRecord.")

        with self._lock:
            if session.id in self._sessions:
                raise StorageConflictError(f"session already exists: {session.id!r}.")

            self._sessions[session.id] = SessionRecord(
                id=session.id,
                metadata=session.metadata,
            )

    def get(self, session_id: str) -> SessionRecord | None:
        """Return a session snapshot, or None when it does not exist."""

        session_id = _validate_session_id(session_id)

        with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                return None

            return SessionRecord(
                id=session.id,
                metadata=session.metadata,
            )

    def list(self) -> tuple[SessionRecord, ...]:
        """Return all sessions in deterministic ID order."""

        with self._lock:
            return tuple(
                SessionRecord(
                    id=session.id,
                    metadata=session.metadata,
                )
                for session in sorted(
                    self._sessions.values(),
                    key=lambda item: item.id,
                )
            )

    def update_metadata(
        self,
        session_id: str,
        metadata: Mapping[str, object],
    ) -> SessionRecord:
        """Replace a session's complete metadata snapshot."""

        session_id = _validate_session_id(session_id)

        with self._lock:
            if session_id not in self._sessions:
                raise StorageNotFoundError(f"session does not exist: {session_id!r}.")

            updated = SessionRecord(
                id=session_id,
                metadata=metadata,
            )
            self._sessions[session_id] = updated

            return SessionRecord(
                id=updated.id,
                metadata=updated.metadata,
            )

    def __len__(self) -> int:
        """Return the number of stored sessions."""

        with self._lock:
            return len(self._sessions)


__all__ = [
    "InMemoryEventStore",
    "InMemorySessionStore",
]

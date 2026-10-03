"""Session lifecycle transitions for WaxPrep.

Creates sessions, enforces status transition rules, and records successful
transitions as durable ``state_change`` events.
"""

from __future__ import annotations

from collections.abc import Mapping
from threading import RLock
from typing import Any

from waxprep.clock import Clock, RealClock
from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.session import (
    TERMINAL_STATUSES,
    InvalidSession,
    Session,
    SessionStatus,
)
from waxprep.storage import (
    EventStore,
    SessionRecord,
    SessionStore,
    StorageError,
    StorageNotFoundError,
)

# Authoritative transition table: from_status -> allowed to_status values.
ALLOWED_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.CREATED: frozenset(
        {
            SessionStatus.RUNNING,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        }
    ),
    SessionStatus.RUNNING: frozenset(
        {
            SessionStatus.WAITING,
            SessionStatus.FINISHED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        }
    ),
    SessionStatus.WAITING: frozenset(
        {
            SessionStatus.RUNNING,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        }
    ),
    SessionStatus.FINISHED: frozenset(),
    SessionStatus.FAILED: frozenset(),
    SessionStatus.CANCELLED: frozenset(),
}


class InvalidSessionTransition(ValueError):
    """Raised when a requested session status transition is not allowed."""


class SessionLifecycleError(Exception):
    """Raised when a lifecycle operation cannot complete successfully."""


class SessionLifecycleService:
    """Create sessions and apply validated status transitions."""

    def __init__(
        self,
        session_store: SessionStore,
        event_store: EventStore,
        clock: Clock | None = None,
    ) -> None:
        self._sessions = session_store
        self._events = event_store
        self._clock = clock if clock is not None else RealClock()
        self._lock = RLock()

    def create(
        self,
        *,
        config_snapshot: Mapping[str, Any],
        workspace_ref: str | None = None,
        session_id: str | None = None,
    ) -> Session:
        """Create a session in the ``created`` status.

        Creation is the initial state. No state-change event is emitted for
        the act of creation itself.
        """

        with self._lock:
            session_id = session_id or generate_wax_id(
                WaxIdKind.SESSION,
                self._clock,
            )

            session = Session(
                id=session_id,
                created=self._clock.now(),
                status=SessionStatus.CREATED,
                config_snapshot=dict(config_snapshot),
                workspace_ref=workspace_ref,
            )

            try:
                self._sessions.create(
                    SessionRecord(
                        id=session.id,
                        metadata=session.to_metadata(),
                    )
                )
            except StorageError as exc:
                raise SessionLifecycleError(
                    f"unable to persist new session: {session.id!r}"
                ) from exc

            return session

    def get(self, session_id: str) -> Session | None:
        """Load a session, or return None when it does not exist."""

        record = self._sessions.get(session_id)
        if record is None:
            return None

        return Session.from_metadata(record.metadata)

    def transition(
        self,
        session_id: str,
        new_status: SessionStatus | str,
    ) -> Session:
        """Apply a validated status transition and record a state-change event.

        Write order:
        1. Append the state-change event to the event store.
        2. Update session metadata with the new status.

        If the event append fails, neither the event history nor the session
        metadata is advanced by this call.

        If the metadata update fails after a successful event append, the
        event history contains the transition evidence while metadata may
        still show the previous status. Callers must treat that as a
        recoverable inconsistency; the service does not report success when
        the metadata write fails.

        Recovery from an event/metadata mismatch is an operational
        concern outside this service: inspect the latest state_change
        event for the session and re-apply the metadata update, or
        surface the inconsistency to an operator. This service does
        not invent a second journal or cross-store transaction.
        """

        if isinstance(new_status, SessionStatus):
            pass
        elif isinstance(new_status, str):
            try:
                new_status = SessionStatus(new_status)
            except ValueError as exc:
                raise InvalidSessionTransition(
                    f"unknown session status: {new_status!r}."
                ) from exc
        else:
            raise InvalidSessionTransition(
                "new_status must be a SessionStatus or status string."
            )

        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                raise StorageNotFoundError(f"session does not exist: {session_id!r}.")

            try:
                session = Session.from_metadata(record.metadata)
            except InvalidSession as exc:
                raise SessionLifecycleError(
                    f"stored session metadata is invalid: {session_id!r}"
                ) from exc

            previous = session.status

            if previous is new_status:
                raise InvalidSessionTransition(
                    f"session {session_id!r} is already {previous.value}."
                )

            if previous in TERMINAL_STATUSES:
                raise InvalidSessionTransition(
                    f"session {session_id!r} is terminal ({previous.value}) "
                    "and cannot transition."
                )

            allowed = ALLOWED_TRANSITIONS.get(previous, frozenset())
            if new_status not in allowed:
                raise InvalidSessionTransition(
                    f"transition {previous.value} → {new_status.value} "
                    f"is not allowed for session {session_id!r}."
                )

            next_sequence = self._events.count(session_id) + 1

            event = EventEnvelope(
                id=generate_wax_id(WaxIdKind.EVENT, self._clock),
                session_id=session_id,
                sequence=next_sequence,
                timestamp=self._clock.now(),
                kind=EventKind.STATE_CHANGE,
                payload={
                    "state": "session.status",
                    "previous_value": previous.value,
                    "new_value": new_status.value,
                },
            )

            try:
                self._events.append(event)
            except StorageError as exc:
                raise SessionLifecycleError(
                    f"unable to append state-change event for {session_id!r}"
                ) from exc

            updated = Session(
                id=session.id,
                created=session.created,
                status=new_status,
                config_snapshot=_thaw_config(session.config_snapshot),
                workspace_ref=session.workspace_ref,
            )

            # Preserve any extra metadata keys not owned by the lifecycle.
            merged = dict(record.metadata)
            merged.update(updated.to_metadata())

            try:
                self._sessions.update_metadata(session_id, merged)
            except StorageError as exc:
                raise SessionLifecycleError(
                    f"state-change event was recorded but session metadata "
                    f"update failed for {session_id!r}"
                ) from exc

            return updated


def _thaw_config(value: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a frozen config snapshot back into a plain dict for Session."""

    from waxprep.session import _thaw_value

    thawed = _thaw_value(value)
    if not isinstance(thawed, dict):
        return {}
    return thawed


def is_transition_allowed(
    current: SessionStatus,
    new_status: SessionStatus,
) -> bool:
    """Return whether ``current → new_status`` is a legal transition."""

    if current is new_status:
        return False
    return new_status in ALLOWED_TRANSITIONS.get(current, frozenset())


__all__ = [
    "ALLOWED_TRANSITIONS",
    "InvalidSessionTransition",
    "SessionLifecycleError",
    "SessionLifecycleService",
    "is_transition_allowed",
]

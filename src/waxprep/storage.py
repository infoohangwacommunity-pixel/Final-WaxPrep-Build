"""Persistence contracts for WaxPrep.

This module defines storage interfaces only. It intentionally contains no
database, filesystem, cache, or in-memory storage implementation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from waxprep.event import EventEnvelope
from waxprep.identifiers import InvalidWaxId, WaxIdKind, parse_wax_id


class StorageError(Exception):
    """Base exception for storage contract failures."""


class StorageConflictError(StorageError):
    """Raised when an append or create conflicts with existing state."""


class StorageNotFoundError(StorageError):
    """Raised when a requested mutable storage record does not exist."""


def _freeze_metadata(metadata: Mapping[str, object]) -> Mapping[str, object]:
    """Copy metadata so returned session records cannot mutate store state."""

    if not isinstance(metadata, Mapping):
        raise TypeError("session metadata must be a mapping.")

    copied = dict(metadata)

    if any(not isinstance(key, str) for key in copied):
        raise ValueError("session metadata keys must be strings.")

    return MappingProxyType(copied)


def _validate_session_id(session_id: object) -> str:
    """Validate a WaxPrep session identifier."""

    if not isinstance(session_id, str):
        raise ValueError("session_id must be a string.")

    try:
        parsed = parse_wax_id(session_id)
    except InvalidWaxId as exc:
        raise ValueError("session_id must be a valid WaxPrep session ID.") from exc

    if parsed.kind is not WaxIdKind.SESSION:
        raise ValueError("session_id must be a WaxPrep session ID.")

    return session_id


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """The domain-neutral durable identity and metadata of a session."""

    id: str
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_session_id(self.id))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class EventStore(Protocol):
    """Store contract for immutable, ordered session event history.

    Guarantees required from every implementation:

    - ``append`` is atomic: either the supplied event becomes visible or the
      store remains unchanged.
    - Events are append-only and immutable. There is no update or delete
      operation in this contract.
    - Event sequence numbers are strictly increasing within each session and
      gap-free. The first event has sequence ``1``; each later append must use
      the next sequence number.
    - Successful appends become visible to subsequent reads as one committed
      unit. A failed append must not leave a partial event.
    - Reads return events in ascending sequence order.
    - ``read_range`` uses an inclusive start and exclusive end, matching
      Python's normal range convention.
    - ``read_from_sequence`` includes the requested starting sequence.
    - Reads for a session with no events return an empty tuple.
    - ``count`` counts stored events for exactly one session.

    Concurrency details such as locking strategy, transactions, or optimistic
    concurrency mechanisms are implementation concerns. The observable
    guarantees above are the interface contract.
    """

    def append(self, event: EventEnvelope) -> None:
        """Atomically append one event to its session's history."""

    def read_range(
        self,
        session_id: str,
        start_sequence: int,
        end_sequence: int,
    ) -> tuple[EventEnvelope, ...]:
        """Read ``start_sequence <= sequence < end_sequence`` in order."""

    def read_from_sequence(
        self,
        session_id: str,
        start_sequence: int,
    ) -> tuple[EventEnvelope, ...]:
        """Read from ``start_sequence`` through the current end in order."""

    def count(self, session_id: str) -> int:
        """Return the number of stored events belonging to ``session_id``."""


class SessionStore(Protocol):
    """Store contract for durable session records.

    Guarantees required from every implementation:

    - ``create`` is atomic: a successful call creates the complete session
      record; a conflicting create changes nothing.
    - Session identity is immutable.
    - Metadata is replaced as one complete snapshot by ``update_metadata``.
    - Returned records are snapshots; callers cannot mutate store-owned state
      through a returned metadata mapping.
    - ``list`` returns a deterministic ordering by session ID.
    - ``get`` returns ``None`` when the session does not exist.
    - Updating a missing session raises ``StorageNotFoundError``.
    - There is intentionally no delete operation in this contract.
    """

    def create(self, session: SessionRecord) -> None:
        """Atomically create a new session record."""

    def get(self, session_id: str) -> SessionRecord | None:
        """Return a session record, or ``None`` when it does not exist."""

    def list(self) -> tuple[SessionRecord, ...]:
        """Return all session records in deterministic ID order."""

    def update_metadata(
        self,
        session_id: str,
        metadata: Mapping[str, object],
    ) -> SessionRecord:
        """Replace metadata and return the resulting session snapshot."""


__all__ = [
    "EventStore",
    "SessionRecord",
    "SessionStore",
    "StorageConflictError",
    "StorageError",
    "StorageNotFoundError",
]

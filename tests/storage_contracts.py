"""Reusable contract tests for WaxPrep storage implementations.

This module deliberately does not contain a concrete storage backend. Future
implementations should subclass the appropriate mixin alongside
``unittest.TestCase`` and provide the required factories.
"""

from __future__ import annotations

from datetime import UTC, datetime

from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.storage import (
    EventStore,
    SessionRecord,
    SessionStore,
    StorageConflictError,
    StorageNotFoundError,
)


class EventStoreContractMixin:
    """Behavioral contract that every EventStore implementation must satisfy."""

    def make_event_store(self) -> EventStore:
        """Return a fresh implementation under test."""

        raise NotImplementedError

    def make_event(self, session_id: str, sequence: int) -> EventEnvelope:
        """Return a valid event for contract testing."""

        raise NotImplementedError

    def make_session_id(self) -> str:
        """Return a fresh valid session ID for contract testing."""

        counter = getattr(self, "_contract_id_counter", 0) + 1
        self._contract_id_counter = counter

        clock = FakeClock(
            datetime(2026, 10, 2, tzinfo=UTC),
        )
        clock.advance(counter / 1000)

        return generate_wax_id(WaxIdKind.SESSION, clock)

    def test_append_and_read_preserve_order(self) -> None:
        store = self.make_event_store()
        session_id = self.make_session_id()

        events = tuple(self.make_event(session_id, sequence) for sequence in (1, 2, 3))

        for event in events:
            store.append(event)

        assert store.count(session_id) == 3
        assert store.read_from_sequence(session_id, 1) == events
        assert store.read_range(session_id, 2, 4) == events[1:]

    def test_read_range_uses_inclusive_start_exclusive_end(self) -> None:
        store = self.make_event_store()
        session_id = self.make_session_id()

        events = tuple(self.make_event(session_id, sequence) for sequence in (1, 2, 3))

        for event in events:
            store.append(event)

        assert store.read_range(session_id, 1, 1) == ()
        assert store.read_range(session_id, 1, 3) == events[:2]
        assert store.read_range(session_id, 3, 4) == events[2:]

    def test_read_from_sequence_is_inclusive(self) -> None:
        store = self.make_event_store()
        session_id = self.make_session_id()

        events = tuple(self.make_event(session_id, sequence) for sequence in (1, 2, 3))

        for event in events:
            store.append(event)

        assert store.read_from_sequence(session_id, 2) == events[1:]
        assert store.read_from_sequence(session_id, 4) == ()

    def test_sessions_are_isolated(self) -> None:
        store = self.make_event_store()

        first_session = self.make_session_id()
        second_session = self.make_session_id()

        first_event = self.make_event(first_session, 1)
        second_event = self.make_event(second_session, 1)

        store.append(first_event)
        store.append(second_event)

        assert store.count(first_session) == 1
        assert store.count(second_session) == 1
        assert store.read_from_sequence(first_session, 1) == (first_event,)
        assert store.read_from_sequence(second_session, 1) == (second_event,)

    def test_invalid_sequence_append_is_atomic(self) -> None:
        store = self.make_event_store()
        session_id = self.make_session_id()

        first_event = self.make_event(session_id, 1)
        store.append(first_event)

        try:
            store.append(self.make_event(session_id, 3))
        except StorageConflictError:
            pass
        else:
            raise AssertionError("gap append must raise StorageConflictError")

        assert store.count(session_id) == 1
        assert store.read_from_sequence(session_id, 1) == (first_event,)


class SessionStoreContractMixin:
    """Behavioral contract that every SessionStore implementation must satisfy."""

    def make_session_store(self) -> SessionStore:
        """Return a fresh implementation under test."""

        raise NotImplementedError

    def make_valid_session(self, name: str) -> SessionRecord:
        """Return a valid session record with a unique identity."""

        counter = getattr(self, "_contract_id_counter", 0) + 1
        self._contract_id_counter = counter

        clock = FakeClock(
            datetime(2026, 10, 2, tzinfo=UTC),
        )
        clock.advance(counter / 1000)

        session_id = generate_wax_id(WaxIdKind.SESSION, clock)

        return SessionRecord(
            id=session_id,
            metadata={"name": name},
        )

    def test_create_and_get_round_trip(self) -> None:
        store = self.make_session_store()
        session = self.make_valid_session("one")

        store.create(session)

        assert store.get(session.id) == session

    def test_duplicate_create_is_atomic(self) -> None:
        store = self.make_session_store()
        session = self.make_valid_session("one")

        store.create(session)

        try:
            store.create(
                SessionRecord(
                    id=session.id,
                    metadata={"name": "replacement"},
                )
            )
        except StorageConflictError:
            pass
        else:
            raise AssertionError("duplicate create must raise StorageConflictError")

        assert store.get(session.id) == session

    def test_update_metadata_replaces_snapshot(self) -> None:
        store = self.make_session_store()
        session = self.make_valid_session("one")

        store.create(session)

        updated = store.update_metadata(
            session.id,
            {"name": "two", "active": True},
        )

        assert updated.id == session.id
        assert dict(updated.metadata) == {
            "name": "two",
            "active": True,
        }
        assert store.get(session.id) == updated

    def test_update_missing_session_fails(self) -> None:
        store = self.make_session_store()
        session = self.make_valid_session("missing")

        try:
            store.update_metadata(
                session.id,
                {"name": "nowhere"},
            )
        except StorageNotFoundError:
            pass
        else:
            raise AssertionError(
                "updating a missing session must raise StorageNotFoundError",
            )

    def test_list_is_deterministic(self) -> None:
        store = self.make_session_store()

        first = self.make_valid_session("first")
        second = self.make_valid_session("second")

        store.create(second)
        store.create(first)

        listed = store.list()

        assert tuple(item.id for item in listed) == tuple(
            sorted((first.id, second.id)),
        )

    def test_get_missing_session_returns_none(self) -> None:
        store = self.make_session_store()
        session = self.make_valid_session("missing")

        assert store.get(session.id) is None

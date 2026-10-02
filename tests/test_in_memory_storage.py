"""Contract tests for WaxPrep's in-memory storage backend."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from storage_contracts import (
    EventStoreContractMixin,
    SessionStoreContractMixin,
)
from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.in_memory_storage import (
    InMemoryEventStore,
    InMemorySessionStore,
)
from waxprep.storage import (
    StorageConflictError,
)


class InMemoryEventStoreContractTests(
    EventStoreContractMixin,
    unittest.TestCase,
):
    """Run the reusable EventStore contract against the memory backend."""

    def make_event_store(self) -> InMemoryEventStore:
        return InMemoryEventStore()

    def make_event(
        self,
        session_id: str,
        sequence: int,
    ) -> EventEnvelope:
        clock = FakeClock(
            datetime(2026, 10, 2, tzinfo=UTC),
        )
        clock.advance(sequence / 1000)

        return EventEnvelope(
            id=generate_wax_id(WaxIdKind.EVENT, clock),
            session_id=session_id,
            sequence=sequence,
            timestamp=clock.now(),
            kind=EventKind.SYSTEM_NOTICE,
            payload={"message": f"event {sequence}"},
        )

    def test_duplicate_sequence_is_rejected_atomically(self) -> None:
        store = self.make_event_store()
        session_id = self.make_session_id()

        first = self.make_event(session_id, 1)
        store.append(first)

        duplicate = self.make_event(session_id, 1)

        with self.assertRaises(StorageConflictError):
            store.append(duplicate)

        self.assertEqual(store.count(session_id), 1)
        self.assertEqual(
            store.read_from_sequence(session_id, 1),
            (first,),
        )

    def test_sequence_must_remain_gap_free(self) -> None:
        store = self.make_event_store()
        session_id = self.make_session_id()

        store.append(self.make_event(session_id, 1))

        with self.assertRaises(StorageConflictError):
            store.append(self.make_event(session_id, 3))

        store.append(self.make_event(session_id, 2))

        events = store.read_from_sequence(session_id, 1)

        self.assertEqual(
            tuple(event.sequence for event in events),
            (1, 2),
        )


class InMemorySessionStoreContractTests(
    SessionStoreContractMixin,
    unittest.TestCase,
):
    """Run the reusable SessionStore contract against the memory backend."""

    def make_session_store(self) -> InMemorySessionStore:
        return InMemorySessionStore()


class InMemoryStorageDirectTests(unittest.TestCase):
    """Additional backend-specific behavior tests."""

    def test_empty_event_store_reads_are_empty(self) -> None:
        store = InMemoryEventStore()

        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        session_id = generate_wax_id(WaxIdKind.SESSION, clock)

        self.assertEqual(store.read_range(session_id, 1, 2), ())
        self.assertEqual(store.read_from_sequence(session_id, 1), ())
        self.assertEqual(store.count(session_id), 0)

    def test_event_stores_are_isolated_instances(self) -> None:
        first_store = InMemoryEventStore()
        second_store = InMemoryEventStore()

        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        session_id = generate_wax_id(WaxIdKind.SESSION, clock)

        event = EventEnvelope(
            id=generate_wax_id(WaxIdKind.EVENT, clock),
            session_id=session_id,
            sequence=1,
            timestamp=clock.now(),
            kind=EventKind.SYSTEM_NOTICE,
            payload={"message": "isolated"},
        )

        first_store.append(event)

        self.assertEqual(first_store.count(session_id), 1)
        self.assertEqual(second_store.count(session_id), 0)

    def test_session_store_returns_immutable_snapshots(self) -> None:
        store = InMemorySessionStore()

        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        session_id = generate_wax_id(WaxIdKind.SESSION, clock)

        session = self._make_session(session_id)

        store.create(session)

        returned = store.get(session_id)

        self.assertIsNotNone(returned)
        assert returned is not None

        with self.assertRaises(TypeError):
            returned.metadata["changed"] = True  # type: ignore[index]

        self.assertEqual(
            dict(store.get(session_id).metadata),  # type: ignore[union-attr]
            {"name": "WaxPrep"},
        )

    @staticmethod
    def _make_session(session_id: str):
        from waxprep.storage import SessionRecord

        return SessionRecord(
            id=session_id,
            metadata={"name": "WaxPrep"},
        )


if __name__ == "__main__":
    unittest.main()

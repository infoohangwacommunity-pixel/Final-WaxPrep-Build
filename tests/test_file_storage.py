"""Contract and durability tests for WaxPrep's file storage backend."""

from __future__ import annotations

import tempfile
import unittest
import warnings
from datetime import UTC, datetime
from pathlib import Path

from storage_contracts import (
    EventStoreContractMixin,
    SessionStoreContractMixin,
)
from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.file_storage import (
    FileEventStore,
    FileSessionStore,
    StorageCorruptionWarning,
)
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.session_lock import session_write_lock
from waxprep.storage import SessionRecord, StorageConflictError


class FileEventStoreContractTests(
    EventStoreContractMixin,
    unittest.TestCase,
):
    """Run the reusable EventStore contract against the file backend."""

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def make_event_store(self) -> FileEventStore:
        return FileEventStore(
            Path(self._temporary_directory.name).resolve(),
        )

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


class FileSessionStoreContractTests(
    SessionStoreContractMixin,
    unittest.TestCase,
):
    """Run the reusable SessionStore contract against the file backend."""

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def make_session_store(self) -> FileSessionStore:
        return FileSessionStore(
            Path(self._temporary_directory.name).resolve(),
        )


class FileStorageDurabilityTests(unittest.TestCase):
    """Verify filesystem persistence and corruption handling."""

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self._data_dir = Path(self._temporary_directory.name).resolve()

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def _make_event(
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

    def _make_session(self) -> SessionRecord:
        clock = FakeClock(
            datetime(2026, 10, 2, tzinfo=UTC),
        )

        return SessionRecord(
            id=generate_wax_id(WaxIdKind.SESSION, clock),
            metadata={"name": "WaxPrep"},
        )

    def test_events_survive_store_recreation(self) -> None:
        session_id = self._make_session().id

        first_store = FileEventStore(self._data_dir)

        first = self._make_event(session_id, 1)
        second = self._make_event(session_id, 2)

        first_store.append(first)
        first_store.append(second)

        second_store = FileEventStore(self._data_dir)

        self.assertEqual(
            second_store.read_from_sequence(session_id, 1),
            (first, second),
        )

    def test_sessions_survive_store_recreation(self) -> None:
        session = self._make_session()

        first_store = FileSessionStore(self._data_dir)
        first_store.create(session)

        second_store = FileSessionStore(self._data_dir)

        self.assertEqual(
            second_store.get(session.id),
            session,
        )

    def test_event_log_is_json_lines(self) -> None:
        session = self._make_session()
        event = self._make_event(session.id, 1)

        store = FileEventStore(self._data_dir)
        store.append(event)

        events_path = self._data_dir / session.id / "events.jsonl"

        content = events_path.read_text(encoding="utf-8")

        self.assertEqual(
            content,
            event.to_json() + "\n",
        )

    def test_metadata_is_stored_separately(self) -> None:
        session = self._make_session()

        store = FileSessionStore(self._data_dir)
        store.create(session)

        metadata_path = self._data_dir / session.id / "metadata.json"

        self.assertTrue(metadata_path.exists())
        self.assertNotIn(
            "events.jsonl",
            metadata_path.name,
        )

    def test_truncated_final_line_is_detected_and_ignored(self) -> None:
        session = self._make_session()

        first = self._make_event(session.id, 1)
        second = self._make_event(session.id, 2)

        store = FileEventStore(self._data_dir)

        store.append(first)
        store.append(second)

        events_path = self._data_dir / session.id / "events.jsonl"

        original = events_path.read_text(encoding="utf-8")

        complete_first_line, complete_second_line = original.splitlines(
            keepends=True,
        )

        truncated_second_line = complete_second_line[:20]

        events_path.write_text(
            complete_first_line + truncated_second_line,
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            recovered = store.read_from_sequence(
                session.id,
                1,
            )

        self.assertEqual(
            recovered,
            (first,),
        )

        self.assertTrue(
            any(
                issubclass(
                    warning.category,
                    StorageCorruptionWarning,
                )
                for warning in caught
            ),
        )

    def test_corruption_warning_does_not_hide_valid_history(self) -> None:
        session = self._make_session()

        first = self._make_event(session.id, 1)
        second = self._make_event(session.id, 2)
        third = self._make_event(session.id, 3)

        store = FileEventStore(self._data_dir)

        store.append(first)
        store.append(second)

        events_path = self._data_dir / session.id / "events.jsonl"

        content = events_path.read_text(encoding="utf-8")

        events_path.write_text(
            content + '{"sequence":',
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            recovered = store.read_from_sequence(
                session.id,
                1,
            )

        self.assertEqual(
            recovered,
            (first, second),
        )

        self.assertEqual(len(caught), 1)

        # A subsequent valid append remains possible because the corrupted
        # final line is recoverable and is ignored during the next read.
        store.append(third)

        self.assertEqual(
            store.read_from_sequence(session.id, 1),
            (first, second, third),
        )

    def test_session_write_lock_rejects_competing_writers(self) -> None:
        session = self._make_session()
        other_session = self._make_session()

        store = FileEventStore(self._data_dir)
        competing_store = FileEventStore(self._data_dir)

        for sequence in range(1, 11):
            event = self._make_event(session.id, sequence)

            with session_write_lock(self._data_dir, session.id):
                with self.assertRaisesRegex(
                    StorageConflictError,
                    "another writer currently holds the lock",
                ):
                    competing_store.append(event)

                # A different session has a different lock and can proceed.
                other_event = self._make_event(other_session.id, sequence)
                competing_store.append(other_event)

            # After the lock is released, the original session can be written.
            store.append(event)

        self.assertEqual(store.count(session.id), 10)
        self.assertEqual(store.count(other_session.id), 10)

    def test_data_directory_must_be_absolute(self) -> None:
        with self.assertRaises(ValueError):
            FileEventStore("relative/path")

        with self.assertRaises(ValueError):
            FileSessionStore("relative/path")


if __name__ == "__main__":
    unittest.main()

"""Tests for the WaxPrep storage contracts."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from waxprep.clock import FakeClock
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.storage import (
    EventStore,
    SessionRecord,
    SessionStore,
)


class StorageInterfaceTests(unittest.TestCase):
    """Verify the Prompt 21 storage API shape."""

    def test_event_store_is_a_protocol(self) -> None:
        self.assertTrue(getattr(EventStore, "_is_protocol", False))

    def test_session_store_is_a_protocol(self) -> None:
        self.assertTrue(getattr(SessionStore, "_is_protocol", False))

    def test_event_store_has_required_methods(self) -> None:
        required = {
            "append",
            "read_range",
            "read_from_sequence",
            "count",
        }

        self.assertTrue(required.issubset(EventStore.__dict__))

    def test_session_store_has_required_methods(self) -> None:
        required = {
            "create",
            "get",
            "list",
            "update_metadata",
        }

        self.assertTrue(required.issubset(SessionStore.__dict__))

    def test_session_record_copies_metadata(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        session_id = generate_wax_id(WaxIdKind.SESSION, clock)

        original = {"name": "WaxPrep"}
        session = SessionRecord(
            id=session_id,
            metadata=original,
        )

        original["name"] = "changed"

        self.assertEqual(
            dict(session.metadata),
            {"name": "WaxPrep"},
        )

    def test_session_record_metadata_is_immutable(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        session_id = generate_wax_id(WaxIdKind.SESSION, clock)

        session = SessionRecord(
            id=session_id,
            metadata={"name": "WaxPrep"},
        )

        with self.assertRaises(TypeError):
            session.metadata["name"] = "changed"  # type: ignore[index]

    def test_session_record_rejects_non_session_id(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        event_id = generate_wax_id(WaxIdKind.EVENT, clock)

        with self.assertRaises(ValueError):
            SessionRecord(
                id=event_id,
                metadata={},
            )

    def test_session_record_is_immutable(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        session_id = generate_wax_id(WaxIdKind.SESSION, clock)

        session = SessionRecord(
            id=session_id,
            metadata={},
        )

        with self.assertRaises(AttributeError):
            session.id = "changed"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()

"""Tests for WaxPrep event schema migrations."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime

from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.migrations import (
    CURRENT_EVENT_SCHEMA_VERSION,
    EventMigrationError,
    migrate_event_data,
)


class EventMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        self.session_id = generate_wax_id(WaxIdKind.SESSION, clock)
        self.event_id = generate_wax_id(WaxIdKind.EVENT, clock)

    def make_v1_event_json(self) -> str:
        return json.dumps(
            {
                "id": self.event_id,
                "session_id": self.session_id,
                "sequence": 1,
                "timestamp": "2026-10-02T02:30:00Z",
                "kind": "placeholder",
                "schema_version": 1,
                "payload": {
                    "answer": [1, True, None],
                },
                "parent_id": None,
                "cause_id": None,
            }
        )

    def test_hand_written_v1_event_loads_and_upgrades(self) -> None:
        restored = EventEnvelope.from_json(self.make_v1_event_json())

        self.assertEqual(
            restored.schema_version,
            CURRENT_EVENT_SCHEMA_VERSION,
        )
        self.assertEqual(restored.kind.value, "system_notice")
        self.assertEqual(
            restored.payload,
            {
                "message": (
                    'Legacy placeholder event payload: {"answer":[1,true,null]}'
                ),
            },
        )

    def test_migration_does_not_mutate_input(self) -> None:
        original = {
            "id": self.event_id,
            "session_id": self.session_id,
            "sequence": 1,
            "timestamp": "2026-10-02T02:30:00Z",
            "kind": "placeholder",
            "schema_version": 1,
            "payload": {"answer": [1, True, None]},
            "parent_id": None,
            "cause_id": None,
        }

        migrated = migrate_event_data(original)

        self.assertEqual(original["schema_version"], 1)
        self.assertEqual(original["kind"], "placeholder")
        self.assertEqual(
            migrated["schema_version"],
            CURRENT_EVENT_SCHEMA_VERSION,
        )
        self.assertEqual(migrated["kind"], "system_notice")

    def test_current_events_require_no_migration(self) -> None:
        data = {
            "id": self.event_id,
            "session_id": self.session_id,
            "sequence": 1,
            "timestamp": "2026-10-02T02:30:00Z",
            "kind": "user_message",
            "schema_version": CURRENT_EVENT_SCHEMA_VERSION,
            "payload": {"text": "Hello"},
            "parent_id": None,
            "cause_id": None,
        }

        migrated = migrate_event_data(data)

        self.assertEqual(migrated, data)

    def test_future_schema_version_is_rejected(self) -> None:
        data = {
            "id": self.event_id,
            "session_id": self.session_id,
            "sequence": 1,
            "timestamp": "2026-10-02T02:30:00Z",
            "kind": "user_message",
            "schema_version": CURRENT_EVENT_SCHEMA_VERSION + 1,
            "payload": {"text": "Hello"},
            "parent_id": None,
            "cause_id": None,
        }

        with self.assertRaisesRegex(
            EventMigrationError,
            "newer than the supported schema",
        ):
            migrate_event_data(data)

    def test_unknown_older_schema_without_migration_is_rejected(self) -> None:
        data = {
            "schema_version": 0,
        }

        with self.assertRaisesRegex(
            EventMigrationError,
            "must be a positive integer",
        ):
            migrate_event_data(data)


if __name__ == "__main__":
    unittest.main()

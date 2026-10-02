"""Tests for the WaxPrep event envelope."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime

from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope, EventKind, InvalidEventEnvelope
from waxprep.identifiers import WaxIdKind, generate_wax_id


class EventEnvelopeTests(unittest.TestCase):
    def setUp(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, tzinfo=UTC))
        self.session_id = generate_wax_id(WaxIdKind.SESSION, clock)
        self.event_id = generate_wax_id(WaxIdKind.EVENT, clock)
        self.related_event_id = generate_wax_id(WaxIdKind.EVENT, clock)

    def make_event(self, **overrides: object) -> EventEnvelope:
        values: dict[str, object] = {
            "id": self.event_id,
            "session_id": self.session_id,
            "sequence": 1,
            "timestamp": datetime(
                2026,
                10,
                2,
                2,
                30,
                tzinfo=UTC,
            ),
            "kind": EventKind.PLACEHOLDER,
            "schema_version": 1,
            "payload": {"answer": [1, True, None]},
            "parent_id": None,
            "cause_id": None,
        }

        values.update(overrides)

        return EventEnvelope(**values)  # type: ignore[arg-type]

    def test_round_trip_serialization(self) -> None:
        original = self.make_event(
            parent_id=self.related_event_id,
            cause_id=self.related_event_id,
        )

        restored = EventEnvelope.from_json(original.to_json())

        self.assertEqual(restored, original)

    def test_json_contains_all_envelope_fields(self) -> None:
        data = json.loads(self.make_event().to_json())

        self.assertEqual(
            set(data),
            {
                "id",
                "session_id",
                "sequence",
                "timestamp",
                "kind",
                "schema_version",
                "payload",
                "parent_id",
                "cause_id",
            },
        )

    def test_envelope_is_immutable(self) -> None:
        event = self.make_event()

        with self.assertRaises(AttributeError):
            event.sequence = 2  # type: ignore[misc]

        with self.assertRaises(TypeError):
            event.payload["new"] = "value"  # type: ignore[index]

        with self.assertRaises(TypeError):
            event.payload["answer"][0] = 2  # type: ignore[index]

    def test_invalid_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "id must be a valid WaxPrep event ID",
        ):
            self.make_event(id="not-an-id")

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "session_id must be a WaxPrep session ID",
        ):
            self.make_event(session_id=self.event_id)

    def test_invalid_sequence_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "sequence must be a positive integer",
        ):
            self.make_event(sequence=0)

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "sequence must be a positive integer",
        ):
            self.make_event(sequence=True)

    def test_invalid_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "timestamp must be timezone-aware",
        ):
            self.make_event(
                timestamp=datetime(2026, 10, 2, 2, 30),
            )

    def test_only_placeholder_kind_is_allowed_at_this_stage(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "current placeholder kind",
        ):
            self.make_event(kind="session.started")

    def test_invalid_schema_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "schema_version must be a positive integer",
        ):
            self.make_event(schema_version=0)

    def test_invalid_parent_and_cause_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "parent_id must be a WaxPrep event ID",
        ):
            self.make_event(parent_id=self.session_id)

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "cause_id must be a valid WaxPrep event ID",
        ):
            self.make_event(cause_id="not-an-id")

    def test_invalid_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "unsupported value type",
        ):
            self.make_event(payload={"value": object()})

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "non-finite number",
        ):
            self.make_event(payload={"value": float("nan")})

    def test_json_with_missing_or_extra_fields_is_rejected(self) -> None:
        data = json.loads(self.make_event().to_json())

        data.pop("payload")

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "fields do not exactly match",
        ):
            EventEnvelope.from_json(json.dumps(data))

        data["payload"] = {}
        data["unexpected"] = True

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "fields do not exactly match",
        ):
            EventEnvelope.from_json(json.dumps(data))

    def test_duplicate_json_keys_are_rejected(self) -> None:
        json_text = self.make_event().to_json()
        duplicate = json_text[:-1] + f',"id":"{self.event_id}"}}'

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "duplicate JSON object key",
        ):
            EventEnvelope.from_json(duplicate)

    def test_non_object_and_malformed_json_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "must be an object",
        ):
            EventEnvelope.from_json("[]")

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "invalid JSON event envelope",
        ):
            EventEnvelope.from_json("{not-json}")


if __name__ == "__main__":
    unittest.main()

"""Tests for the WaxPrep event envelope."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime

from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope, InvalidEventEnvelope
from waxprep.event_types import EventKind
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.migrations import CURRENT_EVENT_SCHEMA_VERSION


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
            "kind": EventKind.USER_MESSAGE,
            "schema_version": CURRENT_EVENT_SCHEMA_VERSION,
            "payload": {"text": "hello"},
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

    def test_json_uses_current_schema_version(self) -> None:
        data = json.loads(self.make_event().to_json())

        self.assertEqual(
            data["schema_version"],
            CURRENT_EVENT_SCHEMA_VERSION,
        )

    def test_envelope_is_immutable(self) -> None:
        event = self.make_event()

        with self.assertRaises(AttributeError):
            event.sequence = 2  # type: ignore[misc]

        with self.assertRaises(TypeError):
            event.payload["new"] = "value"  # type: ignore[index]

        with self.assertRaises(TypeError):
            event.payload["text"] = "changed"  # type: ignore[index]

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

    def test_all_taxonomy_kinds_are_allowed(self) -> None:
        payloads = {
            EventKind.USER_MESSAGE: {"text": "Hello"},
            EventKind.MODEL_MESSAGE: {"text": "Hello from the model"},
            EventKind.MODEL_TOOL_REQUEST: {
                "tool_name": "read_file",
                "arguments": {"path": "example.txt"},
            },
            EventKind.ACTION_RESULT: {
                "status": "success",
                "result": "example result",
            },
            EventKind.ERROR: {
                "error_type": "ExampleError",
                "message": "Something went wrong.",
            },
            EventKind.STATE_CHANGE: {
                "state": "session",
                "previous_value": "active",
                "new_value": "completed",
            },
            EventKind.SYSTEM_NOTICE: {
                "message": "The system is shutting down.",
            },
            EventKind.PERMISSION_DECISION: {
                "decision": "pending",
            },
        }

        for kind, payload in payloads.items():
            with self.subTest(kind=kind):
                event = self.make_event(
                    kind=kind,
                    payload=payload,
                )

                self.assertEqual(event.kind, kind)
                self.assertEqual(event.to_dict()["kind"], kind.value)

    def test_taxonomy_payload_remains_immutable(self) -> None:
        event = self.make_event(
            kind=EventKind.USER_MESSAGE,
            payload={"text": "Hello"},
        )

        with self.assertRaises(TypeError):
            event.payload["text"] = "Changed"  # type: ignore[index]

    def test_unsupported_kind_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "unsupported event kind",
        ):
            self.make_event(kind="session.started", payload={"text": "x"})

    def test_non_current_schema_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "schema_version must match the current event schema version",
        ):
            self.make_event(schema_version=1)

    def test_invalid_schema_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "schema_version must match the current event schema version",
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
            "must be a string",
        ):
            self.make_event(
                kind=EventKind.USER_MESSAGE,
                payload={"text": object()},
            )

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "fields do not exactly match",
        ):
            self.make_event(
                kind=EventKind.USER_MESSAGE,
                payload={"text": "ok", "extra": True},
            )

        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "non-finite number",
        ):
            self.make_event(
                kind=EventKind.ACTION_RESULT,
                payload={"status": "ok", "result": float("nan")},
            )

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

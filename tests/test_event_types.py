"""Tests for the WaxPrep event taxonomy."""

from __future__ import annotations

import unittest

from waxprep.event_types import (
    EVENT_KINDS,
    EventKind,
    InvalidEventEnvelope,
    validate_event_payload,
)


class EventTaxonomyTests(unittest.TestCase):
    def test_taxonomy_contains_exactly_eight_kinds(self) -> None:
        self.assertEqual(
            EVENT_KINDS,
            (
                EventKind.USER_MESSAGE,
                EventKind.MODEL_MESSAGE,
                EventKind.MODEL_TOOL_REQUEST,
                EventKind.ACTION_RESULT,
                EventKind.ERROR,
                EventKind.STATE_CHANGE,
                EventKind.SYSTEM_NOTICE,
                EventKind.PERMISSION_DECISION,
            ),
        )

    def test_user_message_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.USER_MESSAGE,
            {"text": "Hello"},
        )

    def test_model_message_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.MODEL_MESSAGE,
            {"text": "Hello from the model"},
        )

    def test_model_tool_request_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.MODEL_TOOL_REQUEST,
            {
                "tool_name": "read_file",
                "arguments": {"path": "example.txt"},
            },
        )

    def test_action_result_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.ACTION_RESULT,
            {
                "status": "success",
                "result": "example result",
            },
        )

    def test_error_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.ERROR,
            {
                "error_type": "ExampleError",
                "message": "Something went wrong.",
            },
        )

    def test_state_change_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.STATE_CHANGE,
            {
                "state": "session",
                "previous_value": "active",
                "new_value": "completed",
            },
        )

    def test_system_notice_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.SYSTEM_NOTICE,
            {
                "message": "System notice.",
            },
        )

    def test_permission_decision_payload_is_valid(self) -> None:
        validate_event_payload(
            EventKind.PERMISSION_DECISION,
            {
                "decision": "pending",
            },
        )

    def test_unknown_kind_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EventKind("unknown_event")

    def test_user_message_rejects_missing_text(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "fields do not exactly match",
        ):
            validate_event_payload(
                EventKind.USER_MESSAGE,
                {},
            )

    def test_user_message_rejects_non_string_text(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "must be a string",
        ):
            validate_event_payload(
                EventKind.USER_MESSAGE,
                {"text": 123},
            )

    def test_tool_request_requires_arguments_object(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "arguments must be an object",
        ):
            validate_event_payload(
                EventKind.MODEL_TOOL_REQUEST,
                {
                    "tool_name": "read_file",
                    "arguments": "not-an-object",
                },
            )

    def test_extra_payload_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidEventEnvelope,
            "fields do not exactly match",
        ):
            validate_event_payload(
                EventKind.ERROR,
                {
                    "error_type": "ExampleError",
                    "message": "Something went wrong.",
                    "unexpected": True,
                },
            )


if __name__ == "__main__":
    unittest.main()

"""Tests for event-to-model-message normalization."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.model_client import (
    ModelMessageRole,
    TextContentBlock,
)
from waxprep.model_messages import (
    ModelMessageNormalizationError,
    model_messages_from_events,
)


class ModelMessageNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        self.session_id = generate_wax_id(
            WaxIdKind.SESSION,
            self.clock,
        )

    def _event(
        self,
        *,
        kind: EventKind,
        sequence: int,
        payload: dict[str, object],
        session_id: str | None = None,
        parent_id: str | None = None,
        cause_id: str | None = None,
    ) -> EventEnvelope:
        self.clock.advance(0.001)

        return EventEnvelope(
            id=generate_wax_id(WaxIdKind.EVENT, self.clock),
            session_id=session_id or self.session_id,
            sequence=sequence,
            timestamp=self.clock.now(),
            kind=kind,
            payload=payload,
            parent_id=parent_id,
            cause_id=cause_id,
        )

    def _user(self, sequence: int, text: str) -> EventEnvelope:
        return self._event(
            kind=EventKind.USER_MESSAGE,
            sequence=sequence,
            payload={"text": text},
        )

    def _model(self, sequence: int, text: str) -> EventEnvelope:
        return self._event(
            kind=EventKind.MODEL_MESSAGE,
            sequence=sequence,
            payload={"text": text},
        )

    def _request(
        self,
        sequence: int,
        *,
        name: str = "read_file",
        arguments: dict[str, object] | None = None,
    ) -> EventEnvelope:
        return self._event(
            kind=EventKind.MODEL_TOOL_REQUEST,
            sequence=sequence,
            payload={
                "tool_name": name,
                "arguments": arguments or {"path": "example.txt"},
            },
        )

    def _result(
        self,
        sequence: int,
        *,
        request: EventEnvelope | None = None,
        parent_id: str | None = None,
        cause_id: str | None = None,
        status: str = "success",
        result: object = "file contents",
        session_id: str | None = None,
    ) -> EventEnvelope:
        if request is not None:
            cause_id = request.id

        return self._event(
            kind=EventKind.ACTION_RESULT,
            sequence=sequence,
            payload={"status": status, "result": result},
            session_id=session_id,
            parent_id=parent_id,
            cause_id=cause_id,
        )

    def test_converts_user_and_model_messages(self) -> None:
        user = self._user(1, "Hello")
        model = self._model(2, "Hi there")

        messages = model_messages_from_events((user, model))

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, ModelMessageRole.USER)
        self.assertEqual(
            messages[0].content,
            (TextContentBlock(text="Hello"),),
        )
        self.assertEqual(messages[1].role, ModelMessageRole.ASSISTANT)
        self.assertEqual(
            messages[1].content,
            (TextContentBlock(text="Hi there"),),
        )

    def test_converts_tool_request_and_linked_result(self) -> None:
        user = self._user(1, "Read the file")
        request = self._request(2)
        result = self._result(
            3,
            request=request,
            status="success",
            result="hello from disk",
        )

        messages = model_messages_from_events((user, request, result))

        self.assertEqual(len(messages), 3)

        assistant_tool_message = messages[1]
        self.assertEqual(
            assistant_tool_message.role,
            ModelMessageRole.ASSISTANT,
        )
        self.assertEqual(len(assistant_tool_message.tool_requests), 1)

        normalized_request = assistant_tool_message.tool_requests[0]
        self.assertEqual(normalized_request.id, request.id)
        self.assertEqual(normalized_request.name, "read_file")
        self.assertEqual(
            dict(normalized_request.arguments),
            {"path": "example.txt"},
        )

        tool_result = messages[2]
        self.assertEqual(tool_result.role, ModelMessageRole.TOOL)
        self.assertEqual(tool_result.name, "read_file")
        self.assertEqual(tool_result.tool_call_id, request.id)
        self.assertEqual(
            tool_result.content,
            (TextContentBlock(text="Status: success\nResult: hello from disk"),),
        )

    def test_accepts_parent_id_as_request_link(self) -> None:
        request = self._request(1)
        result = self._result(2, parent_id=request.id)

        messages = model_messages_from_events((request, result))

        self.assertEqual(messages[1].tool_call_id, request.id)

    def test_sorts_events_by_sequence(self) -> None:
        user = self._user(1, "Hello")
        model = self._model(2, "Hi")

        messages = model_messages_from_events((model, user))

        self.assertEqual(
            tuple(message.role for message in messages),
            (ModelMessageRole.USER, ModelMessageRole.ASSISTANT),
        )

    def test_ignores_unrelated_event_kinds(self) -> None:
        user = self._user(1, "Hello")
        notice = self._event(
            kind=EventKind.SYSTEM_NOTICE,
            sequence=2,
            payload={"message": "System notice"},
        )
        model = self._model(3, "Hi")

        messages = model_messages_from_events((user, notice, model))

        self.assertEqual(len(messages), 2)

    def test_empty_history_returns_empty_tuple(self) -> None:
        self.assertEqual(model_messages_from_events(()), ())

    def test_preserves_unresolved_tool_request(self) -> None:
        request = self._request(1)

        messages = model_messages_from_events((request,))

        self.assertEqual(len(messages), 1)
        self.assertEqual(len(messages[0].tool_requests), 1)

    def test_rejects_action_result_without_request_link(self) -> None:
        result = self._result(1, result="unlinked result")

        with self.assertRaisesRegex(
            ModelMessageNormalizationError,
            "exactly one preceding",
        ):
            model_messages_from_events((result,))

    def test_rejects_result_linked_to_non_request_event(self) -> None:
        user = self._user(1, "Hello")
        result = self._result(2, parent_id=user.id)

        with self.assertRaises(ModelMessageNormalizationError):
            model_messages_from_events((user, result))

    def test_rejects_result_that_precedes_its_request(self) -> None:
        request = self._request(2)
        result = self._result(1, request=request)

        with self.assertRaises(ModelMessageNormalizationError):
            model_messages_from_events((request, result))

    def test_rejects_conflicting_request_links(self) -> None:
        first = self._request(1, name="read_file")
        second = self._request(2, name="list_files")
        result = self._result(
            3,
            parent_id=first.id,
            cause_id=second.id,
        )

        with self.assertRaises(ModelMessageNormalizationError):
            model_messages_from_events((first, second, result))

    def test_rejects_second_result_for_completed_request(self) -> None:
        request = self._request(1)
        first_result = self._result(2, request=request)
        second_result = self._result(3, request=request)

        with self.assertRaises(ModelMessageNormalizationError):
            model_messages_from_events((request, first_result, second_result))

    def test_pairs_multiple_pending_requests_correctly(self) -> None:
        first = self._request(1, name="read_file")
        second = self._request(2, name="list_files")
        second_result = self._result(
            3,
            request=second,
            result=["a.txt", "b.txt"],
        )
        first_result = self._result(
            4,
            request=first,
            result="contents",
        )

        messages = model_messages_from_events(
            (first, second, second_result, first_result)
        )

        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[2].tool_call_id, second.id)
        self.assertEqual(messages[3].tool_call_id, first.id)

    def test_rejects_events_from_multiple_sessions(self) -> None:
        user = self._user(1, "Hello")
        other_session = generate_wax_id(WaxIdKind.SESSION, self.clock)
        model = self._event(
            kind=EventKind.MODEL_MESSAGE,
            sequence=2,
            payload={"text": "Hi"},
            session_id=other_session,
        )

        with self.assertRaisesRegex(
            ModelMessageNormalizationError,
            "same session",
        ):
            model_messages_from_events((user, model))

    def test_rejects_duplicate_event_sequences(self) -> None:
        first = self._user(1, "First")
        second = self._model(1, "Second")

        with self.assertRaisesRegex(
            ModelMessageNormalizationError,
            "sequence numbers must be unique",
        ):
            model_messages_from_events((first, second))

    def test_preserves_failure_status_in_tool_result(self) -> None:
        request = self._request(1)
        result = self._result(
            2,
            request=request,
            status="error",
            result={"message": "Permission denied"},
        )

        messages = model_messages_from_events((request, result))

        self.assertEqual(
            messages[1].content,
            (
                TextContentBlock(
                    text='Status: error\nResult: {"message":"Permission denied"}'
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()

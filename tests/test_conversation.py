"""Tests for the WaxPrep conversation model."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from waxprep.clock import FakeClock
from waxprep.conversation import (
    Conversation,
    ConversationMessage,
    InvalidConversation,
    MessageRole,
    conversation_from_event_store,
    conversation_from_events,
)
from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.file_storage import FileEventStore
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.in_memory_storage import InMemoryEventStore


class ConversationModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        self.session_id = generate_wax_id(WaxIdKind.SESSION, self.clock)
        self.conversation_id = generate_wax_id(WaxIdKind.CONVERSATION, self.clock)
        self.event_id = generate_wax_id(WaxIdKind.EVENT, self.clock)

    def _message(self, role: MessageRole = MessageRole.USER) -> ConversationMessage:
        return ConversationMessage(
            role=role,
            text="hello",
            event_id=self.event_id,
            sequence=1,
            timestamp=self.clock.now(),
        )

    def test_valid_conversation(self) -> None:
        conversation = Conversation(
            id=self.conversation_id,
            session_id=self.session_id,
            messages=(self._message(),),
        )
        self.assertEqual(conversation.id, self.conversation_id)
        self.assertEqual(conversation.session_id, self.session_id)
        self.assertEqual(len(conversation.messages), 1)

    def test_rejects_non_conversation_id(self) -> None:
        with self.assertRaises(InvalidConversation):
            Conversation(
                id=self.session_id,
                session_id=self.session_id,
                messages=(),
            )

    def test_rejects_non_session_id(self) -> None:
        with self.assertRaises(InvalidConversation):
            Conversation(
                id=self.conversation_id,
                session_id=self.conversation_id,
                messages=(),
            )

    def test_empty_conversation(self) -> None:
        conversation = Conversation(
            id=self.conversation_id,
            session_id=self.session_id,
            messages=(),
        )
        self.assertEqual(conversation.messages, ())


class ConversationReconstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        self.session_id = generate_wax_id(WaxIdKind.SESSION, self.clock)
        self.conversation_id = generate_wax_id(WaxIdKind.CONVERSATION, self.clock)

    def _event(
        self,
        *,
        kind: EventKind,
        sequence: int,
        payload: dict,
        session_id: str | None = None,
    ) -> EventEnvelope:
        self.clock.advance(sequence / 1000)
        return EventEnvelope(
            id=generate_wax_id(WaxIdKind.EVENT, self.clock),
            session_id=session_id or self.session_id,
            sequence=sequence,
            timestamp=self.clock.now(),
            kind=kind,
            payload=payload,
        )

    def test_reconstructs_user_and_model_messages_in_order(self) -> None:
        events = (
            self._event(
                kind=EventKind.USER_MESSAGE,
                sequence=1,
                payload={"text": "Open this file."},
            ),
            self._event(
                kind=EventKind.SYSTEM_NOTICE,
                sequence=2,
                payload={"message": "noise"},
            ),
            self._event(
                kind=EventKind.MODEL_MESSAGE,
                sequence=3,
                payload={"text": "I'll inspect the file."},
            ),
            self._event(
                kind=EventKind.STATE_CHANGE,
                sequence=4,
                payload={
                    "state": "session.status",
                    "previous_value": "created",
                    "new_value": "running",
                },
            ),
            self._event(
                kind=EventKind.USER_MESSAGE,
                sequence=5,
                payload={"text": "Check the second section."},
            ),
        )

        conversation = conversation_from_events(
            events,
            conversation_id=self.conversation_id,
            session_id=self.session_id,
        )

        self.assertEqual(len(conversation.messages), 3)
        self.assertEqual(
            tuple(message.role for message in conversation.messages),
            (MessageRole.USER, MessageRole.MODEL, MessageRole.USER),
        )
        self.assertEqual(
            tuple(message.text for message in conversation.messages),
            (
                "Open this file.",
                "I'll inspect the file.",
                "Check the second section.",
            ),
        )
        self.assertEqual(
            tuple(message.sequence for message in conversation.messages),
            (1, 3, 5),
        )

    def test_excludes_other_sessions(self) -> None:
        other_session = generate_wax_id(WaxIdKind.SESSION, self.clock)
        events = (
            self._event(
                kind=EventKind.USER_MESSAGE,
                sequence=1,
                payload={"text": "mine"},
            ),
            self._event(
                kind=EventKind.USER_MESSAGE,
                sequence=1,
                payload={"text": "theirs"},
                session_id=other_session,
            ),
        )

        conversation = conversation_from_events(
            events,
            conversation_id=self.conversation_id,
            session_id=self.session_id,
        )

        self.assertEqual(len(conversation.messages), 1)
        self.assertEqual(conversation.messages[0].text, "mine")

    def test_in_memory_store_reconstruction_matches_live_view(self) -> None:
        store = InMemoryEventStore()

        first = self._event(
            kind=EventKind.USER_MESSAGE,
            sequence=1,
            payload={"text": "hello"},
        )
        second = self._event(
            kind=EventKind.MODEL_MESSAGE,
            sequence=2,
            payload={"text": "hi"},
        )

        store.append(first)
        store.append(second)

        live = conversation_from_events(
            (first, second),
            conversation_id=self.conversation_id,
            session_id=self.session_id,
        )
        rebuilt = conversation_from_event_store(
            store,
            conversation_id=self.conversation_id,
            session_id=self.session_id,
        )

        self.assertEqual(rebuilt, live)

    def test_file_store_reconstruction(self) -> None:

        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary).resolve()
            store = FileEventStore(data_dir)

            first = self._event(
                kind=EventKind.USER_MESSAGE,
                sequence=1,
                payload={"text": "from disk"},
            )
            second = self._event(
                kind=EventKind.MODEL_MESSAGE,
                sequence=2,
                payload={"text": "loaded"},
            )
            store.append(first)
            store.append(second)

            reopened = FileEventStore(data_dir)
            conversation = conversation_from_event_store(
                reopened,
                conversation_id=self.conversation_id,
                session_id=self.session_id,
            )

            self.assertEqual(
                tuple(message.text for message in conversation.messages),
                ("from disk", "loaded"),
            )

    def test_compatibility_with_text_only_payloads(self) -> None:
        # Existing stored message events only carry {"text": ...}.
        event = self._event(
            kind=EventKind.USER_MESSAGE,
            sequence=1,
            payload={"text": "legacy message"},
        )
        self.assertEqual(set(event.payload), {"text"})

        conversation = conversation_from_events(
            (event,),
            conversation_id=self.conversation_id,
            session_id=self.session_id,
        )
        self.assertEqual(conversation.messages[0].text, "legacy message")


if __name__ == "__main__":
    unittest.main()

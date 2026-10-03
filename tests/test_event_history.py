"""Tests for WaxPrep event history queries, replay, and timelines."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope
from waxprep.event_history import (
    EventQuery,
    EventQueryError,
    EventReplayError,
    format_event_timeline,
    paginate_events,
    print_event_timeline,
    query_events,
    replay_events,
)
from waxprep.event_types import EventKind
from waxprep.file_storage import FileEventStore
from waxprep.identifiers import (
    WaxIdKind,
    generate_wax_id,
)
from waxprep.in_memory_storage import InMemoryEventStore


class EventHistoryTests(unittest.TestCase):
    """Test event querying, replay, and timeline formatting."""

    def setUp(self) -> None:
        self.base_time = datetime(
            2026,
            10,
            3,
            10,
            0,
            0,
            tzinfo=UTC,
        )

        clock = FakeClock(self.base_time)

        self.session_id = generate_wax_id(
            WaxIdKind.SESSION,
            clock,
        )

        self.events = tuple(
            self._make_event(
                sequence=sequence,
                kind=(
                    EventKind.ERROR
                    if sequence in {2, 5, 7}
                    else EventKind.SYSTEM_NOTICE
                ),
            )
            for sequence in range(1, 8)
        )

        self.store = InMemoryEventStore()

        for event in self.events:
            self.store.append(event)

    def _make_event(
        self,
        *,
        sequence: int,
        kind: EventKind,
    ) -> EventEnvelope:
        timestamp = self.base_time + timedelta(
            seconds=sequence,
        )

        clock = FakeClock(timestamp)

        payload: dict[str, object]

        if kind in {
            EventKind.USER_MESSAGE,
            EventKind.MODEL_MESSAGE,
            EventKind.SYSTEM_NOTICE,
        }:
            payload = {
                "message": f"event {sequence}",
            }

            if kind in {
                EventKind.USER_MESSAGE,
                EventKind.MODEL_MESSAGE,
            }:
                payload = {
                    "text": f"event {sequence}",
                }

        elif kind is EventKind.ERROR:
            payload = {
                "error_type": "TestError",
                "message": f"problem {sequence}",
            }

        else:
            payload = {
                "message": f"event {sequence}",
            }

        return EventEnvelope(
            id=generate_wax_id(
                WaxIdKind.EVENT,
                clock,
            ),
            session_id=self.session_id,
            sequence=sequence,
            timestamp=timestamp,
            kind=kind,
            payload=payload,
        )

    def test_query_by_kind(self) -> None:
        results = query_events(
            self.store,
            self.session_id,
            kind=EventKind.ERROR,
        )

        self.assertEqual(
            tuple(event.sequence for event in results),
            (2, 5, 7),
        )

    def test_query_accepts_string_kind(self) -> None:
        results = query_events(
            self.store,
            self.session_id,
            kind="error",
        )

        self.assertEqual(
            tuple(event.sequence for event in results),
            (2, 5, 7),
        )

    def test_query_by_time_uses_inclusive_start_and_exclusive_end(
        self,
    ) -> None:
        results = query_events(
            self.store,
            self.session_id,
            start_time=self.events[1].timestamp,
            end_time=self.events[4].timestamp,
        )

        self.assertEqual(
            tuple(event.sequence for event in results),
            (2, 3, 4),
        )

    def test_query_by_sequence_uses_inclusive_start_and_exclusive_end(
        self,
    ) -> None:
        results = query_events(
            self.store,
            self.session_id,
            start_sequence=2,
            end_sequence=5,
        )

        self.assertEqual(
            tuple(event.sequence for event in results),
            (2, 3, 4),
        )

    def test_query_combines_multiple_filters(self) -> None:
        results = query_events(
            self.store,
            self.session_id,
            kind=EventKind.ERROR,
            start_sequence=4,
            end_sequence=8,
        )

        self.assertEqual(
            tuple(event.sequence for event in results),
            (5, 7),
        )

    def test_query_empty_result(self) -> None:
        results = query_events(
            self.store,
            self.session_id,
            kind=EventKind.ACTION_RESULT,
        )

        self.assertEqual(
            results,
            (),
        )

    def test_invalid_event_kind_is_rejected(self) -> None:
        with self.assertRaises(EventQueryError):
            EventQuery(kind="does_not_exist")

    def test_naive_time_is_rejected(self) -> None:
        with self.assertRaises(EventQueryError):
            EventQuery(
                start_time=datetime(
                    2026,
                    10,
                    3,
                ),
            )

    def test_inverted_time_range_is_rejected(self) -> None:
        with self.assertRaises(EventQueryError):
            EventQuery(
                start_time=self.base_time + timedelta(seconds=5),
                end_time=self.base_time + timedelta(seconds=2),
            )

    def test_invalid_sequence_range_is_rejected(self) -> None:
        with self.assertRaises(EventQueryError):
            EventQuery(
                start_sequence=5,
                end_sequence=2,
            )

    def test_non_positive_sequence_is_rejected(self) -> None:
        with self.assertRaises(EventQueryError):
            EventQuery(start_sequence=0)

    def test_pagination_returns_matching_events_and_cursor(
        self,
    ) -> None:
        first_page = paginate_events(
            self.store,
            self.session_id,
            page_size=2,
            kind=EventKind.ERROR,
        )

        self.assertEqual(
            tuple(event.sequence for event in first_page.events),
            (2, 5),
        )

        self.assertEqual(
            first_page.next_start_sequence,
            6,
        )

    def test_pagination_has_no_duplicates_or_skipped_matches(
        self,
    ) -> None:
        first_page = paginate_events(
            self.store,
            self.session_id,
            page_size=2,
            kind=EventKind.ERROR,
        )

        second_page = paginate_events(
            self.store,
            self.session_id,
            page_size=2,
            kind=EventKind.ERROR,
            start_sequence=first_page.next_start_sequence or 1,
        )

        self.assertEqual(
            tuple(event.sequence for event in first_page.events)
            + tuple(event.sequence for event in second_page.events),
            (2, 5, 7),
        )

        self.assertIsNone(
            second_page.next_start_sequence,
        )

    def test_pagination_with_no_matches_returns_empty_page(
        self,
    ) -> None:
        page = paginate_events(
            self.store,
            self.session_id,
            page_size=3,
            kind=EventKind.ACTION_RESULT,
        )

        self.assertEqual(
            page.events,
            (),
        )

        self.assertIsNone(
            page.next_start_sequence,
        )

    def test_invalid_page_size_is_rejected(self) -> None:
        with self.assertRaises(EventQueryError):
            paginate_events(
                self.store,
                self.session_id,
                page_size=0,
            )

    def test_replay_visits_events_in_order(self) -> None:
        visited: list[int] = []

        replay_events(
            self.events,
            lambda event: visited.append(
                event.sequence,
            ),
        )

        self.assertEqual(
            visited,
            [1, 2, 3, 4, 5, 6, 7],
        )

    def test_replay_rejects_descending_sequence(self) -> None:
        with self.assertRaises(EventReplayError):
            replay_events(
                (
                    self.events[1],
                    self.events[0],
                ),
                lambda event: None,
            )

    def test_replay_rejects_multiple_sessions(self) -> None:
        other_clock = FakeClock(
            self.base_time + timedelta(seconds=20),
        )

        other_session_id = generate_wax_id(
            WaxIdKind.SESSION,
            other_clock,
        )

        other_event = EventEnvelope(
            id=generate_wax_id(
                WaxIdKind.EVENT,
                other_clock,
            ),
            session_id=other_session_id,
            sequence=1,
            timestamp=other_clock.now(),
            kind=EventKind.SYSTEM_NOTICE,
            payload={
                "message": "other session",
            },
        )

        with self.assertRaises(EventReplayError):
            replay_events(
                (
                    self.events[0],
                    other_event,
                ),
                lambda event: None,
            )

    def test_empty_timeline(self) -> None:
        output = format_event_timeline(
            (),
            session_id=self.session_id,
        )

        self.assertIn(
            "WaxPrep Session Timeline",
            output,
        )

        self.assertIn(
            f"Session: {self.session_id}",
            output,
        )

        self.assertIn(
            "Events: 0",
            output,
        )

        self.assertIn(
            "(no events)",
            output,
        )

    def test_timeline_contains_readable_event_details(self) -> None:
        clock = FakeClock(self.base_time)

        events = (
            EventEnvelope(
                id=generate_wax_id(
                    WaxIdKind.EVENT,
                    clock,
                ),
                session_id=self.session_id,
                sequence=1,
                timestamp=self.base_time,
                kind=EventKind.USER_MESSAGE,
                payload={
                    "text": "Create a notes file.",
                },
            ),
            EventEnvelope(
                id=generate_wax_id(
                    WaxIdKind.EVENT,
                    clock,
                ),
                session_id=self.session_id,
                sequence=2,
                timestamp=self.base_time + timedelta(seconds=1),
                kind=EventKind.MODEL_TOOL_REQUEST,
                payload={
                    "tool_name": "write_file",
                    "arguments": {
                        "path": "notes.txt",
                        "content": "hello",
                    },
                },
            ),
            EventEnvelope(
                id=generate_wax_id(
                    WaxIdKind.EVENT,
                    clock,
                ),
                session_id=self.session_id,
                sequence=3,
                timestamp=self.base_time + timedelta(seconds=2),
                kind=EventKind.ACTION_RESULT,
                payload={
                    "status": "success",
                    "result": "written",
                },
            ),
            EventEnvelope(
                id=generate_wax_id(
                    WaxIdKind.EVENT,
                    clock,
                ),
                session_id=self.session_id,
                sequence=4,
                timestamp=self.base_time + timedelta(seconds=3),
                kind=EventKind.ERROR,
                payload={
                    "error_type": "ExampleError",
                    "message": "example failure",
                },
            ),
        )

        output = format_event_timeline(
            events,
            session_id=self.session_id,
        )

        self.assertIn(
            "user_message",
            output,
        )

        self.assertIn(
            "Create a notes file.",
            output,
        )

        self.assertIn(
            "model_tool_request",
            output,
        )

        self.assertIn(
            "Tool: write_file",
            output,
        )

        self.assertIn(
            "argument_keys=[content, path]",
            output,
        )

        self.assertNotIn(
            "notes.txt",
            output,
        )

        self.assertIn(
            "action_result",
            output,
        )

        self.assertIn(
            "Status: success",
            output,
        )

        self.assertIn(
            "error",
            output,
        )

        self.assertIn(
            "ExampleError",
            output,
        )

    def test_print_event_timeline_writes_to_supplied_stream(
        self,
    ) -> None:
        output = StringIO()

        print_event_timeline(
            self.events[:1],
            session_id=self.session_id,
            file=output,
        )

        self.assertIn(
            "WaxPrep Session Timeline",
            output.getvalue(),
        )

    def test_file_store_query_survives_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary).resolve()

            first_store = FileEventStore(data_dir)

            for event in self.events:
                first_store.append(event)

            reopened_store = FileEventStore(data_dir)

            results = query_events(
                reopened_store,
                self.session_id,
                kind=EventKind.ERROR,
            )

            self.assertEqual(
                tuple(event.sequence for event in results),
                (2, 5, 7),
            )

    def test_file_store_pagination_after_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary).resolve()

            store = FileEventStore(data_dir)

            for event in self.events:
                store.append(event)

            reopened_store = FileEventStore(data_dir)

            first_page = paginate_events(
                reopened_store,
                self.session_id,
                page_size=2,
                kind=EventKind.ERROR,
            )

            second_page = paginate_events(
                reopened_store,
                self.session_id,
                page_size=2,
                kind=EventKind.ERROR,
                start_sequence=(first_page.next_start_sequence or 1),
            )

            self.assertEqual(
                tuple(event.sequence for event in first_page.events),
                (2, 5),
            )

            self.assertEqual(
                tuple(event.sequence for event in second_page.events),
                (7,),
            )

            self.assertIsNone(
                second_page.next_start_sequence,
            )


if __name__ == "__main__":
    unittest.main()

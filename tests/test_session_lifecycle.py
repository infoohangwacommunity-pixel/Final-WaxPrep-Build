"""Tests for WaxPrep session lifecycle transitions."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from waxprep.clock import FakeClock
from waxprep.event_types import EventKind
from waxprep.in_memory_storage import InMemoryEventStore, InMemorySessionStore
from waxprep.session import TERMINAL_STATUSES, SessionStatus
from waxprep.session_lifecycle import (
    ALLOWED_TRANSITIONS,
    InvalidSessionTransition,
    SessionLifecycleService,
)
from waxprep.storage import StorageError


class SessionLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        self.sessions = InMemorySessionStore()
        self.events = InMemoryEventStore()
        self.service = SessionLifecycleService(
            self.sessions,
            self.events,
            self.clock,
        )

    def test_create_persists_created_session(self) -> None:
        session = self.service.create(config_snapshot={"a": 1})

        self.assertEqual(session.status, SessionStatus.CREATED)
        loaded = self.service.get(session.id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.status, SessionStatus.CREATED)
        self.assertEqual(self.events.count(session.id), 0)

    def test_all_allowed_transitions(self) -> None:
        for current, allowed in ALLOWED_TRANSITIONS.items():
            for new_status in allowed:
                with self.subTest(current=current, new_status=new_status):
                    sessions = InMemorySessionStore()
                    events = InMemoryEventStore()
                    service = SessionLifecycleService(
                        sessions, events, FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
                    )
                    session = service.create(config_snapshot={})
                    # Force current status via successive transitions where needed
                    path = self._path_to(current)
                    for step in path:
                        session = service.transition(session.id, step)

                    self.assertEqual(session.status, current)
                    before_count = events.count(session.id)

                    session = service.transition(session.id, new_status)

                    self.assertEqual(session.status, new_status)
                    self.assertEqual(events.count(session.id), before_count + 1)

                    history = events.read_from_sequence(session.id, 1)
                    last = history[-1]
                    self.assertEqual(last.kind, EventKind.STATE_CHANGE)
                    self.assertEqual(last.session_id, session.id)
                    self.assertEqual(
                        dict(last.payload),
                        {
                            "state": "session.status",
                            "previous_value": current.value,
                            "new_value": new_status.value,
                        },
                    )

    def _path_to(self, target: SessionStatus) -> list[SessionStatus]:
        if target is SessionStatus.CREATED:
            return []
        if target is SessionStatus.RUNNING:
            return [SessionStatus.RUNNING]
        if target is SessionStatus.WAITING:
            return [SessionStatus.RUNNING, SessionStatus.WAITING]
        if target is SessionStatus.FINISHED:
            return [SessionStatus.RUNNING, SessionStatus.FINISHED]
        if target is SessionStatus.FAILED:
            return [SessionStatus.FAILED]
        if target is SessionStatus.CANCELLED:
            return [SessionStatus.CANCELLED]
        return []

    def test_illegal_transitions(self) -> None:
        cases = [
            (SessionStatus.CREATED, SessionStatus.WAITING),
            (SessionStatus.CREATED, SessionStatus.FINISHED),
            (SessionStatus.RUNNING, SessionStatus.CREATED),
            (SessionStatus.RUNNING, SessionStatus.RUNNING),
            (SessionStatus.WAITING, SessionStatus.CREATED),
            (SessionStatus.WAITING, SessionStatus.FINISHED),
            (SessionStatus.WAITING, SessionStatus.WAITING),
            (SessionStatus.FINISHED, SessionStatus.RUNNING),
            (SessionStatus.FAILED, SessionStatus.RUNNING),
            (SessionStatus.CANCELLED, SessionStatus.RUNNING),
        ]

        for current, new_status in cases:
            with self.subTest(current=current, new_status=new_status):
                sessions = InMemorySessionStore()
                events = InMemoryEventStore()
                service = SessionLifecycleService(
                    sessions, events, FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
                )
                session = service.create(config_snapshot={})
                for step in self._path_to(current):
                    session = service.transition(session.id, step)

                before_count = events.count(session.id)
                before_status = session.status

                with self.assertRaises(InvalidSessionTransition):
                    service.transition(session.id, new_status)

                loaded = service.get(session.id)
                assert loaded is not None
                self.assertEqual(loaded.status, before_status)
                self.assertEqual(events.count(session.id), before_count)

    def test_terminal_statuses_reject_all_outgoing(self) -> None:
        for terminal in TERMINAL_STATUSES:
            for candidate in SessionStatus:
                if candidate is terminal:
                    continue
                with self.subTest(terminal=terminal, candidate=candidate):
                    sessions = InMemorySessionStore()
                    events = InMemoryEventStore()
                    service = SessionLifecycleService(
                        sessions, events, FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
                    )
                    session = service.create(config_snapshot={})
                    for step in self._path_to(terminal):
                        session = service.transition(session.id, step)

                    with self.assertRaises(InvalidSessionTransition):
                        service.transition(session.id, candidate)

    def test_transition_survives_store_recreation(self) -> None:
        session = self.service.create(config_snapshot={"k": "v"})
        self.service.transition(session.id, SessionStatus.RUNNING)

        # New service instances over same stores
        service2 = SessionLifecycleService(self.sessions, self.events, self.clock)
        loaded = service2.get(session.id)
        assert loaded is not None
        self.assertEqual(loaded.status, SessionStatus.RUNNING)
        self.assertEqual(self.events.count(session.id), 1)

    def test_sequence_is_gap_free_across_transitions(self) -> None:
        session = self.service.create(config_snapshot={})
        self.service.transition(session.id, SessionStatus.RUNNING)
        self.service.transition(session.id, SessionStatus.WAITING)
        self.service.transition(session.id, SessionStatus.RUNNING)
        self.service.transition(session.id, SessionStatus.FINISHED)

        events = self.events.read_from_sequence(session.id, 1)
        self.assertEqual(tuple(e.sequence for e in events), (1, 2, 3, 4))

    def test_invalid_transition_input_type_is_rejected(self) -> None:
        session = self.service.create(config_snapshot={})
        before = self.events.count(session.id)

        with self.assertRaises(InvalidSessionTransition):
            self.service.transition(session.id, 123)  # type: ignore[arg-type]

        with self.assertRaises(InvalidSessionTransition):
            self.service.transition(session.id, None)  # type: ignore[arg-type]

        loaded = self.service.get(session.id)
        assert loaded is not None
        self.assertEqual(loaded.status, SessionStatus.CREATED)
        self.assertEqual(self.events.count(session.id), before)

    def test_event_append_failure_leaves_session_unchanged(self) -> None:
        class FailingEventStore(InMemoryEventStore):
            def append(self, event):  # type: ignore[no-untyped-def]
                raise StorageError("simulated append failure")


        sessions = InMemorySessionStore()
        events = FailingEventStore()
        service = SessionLifecycleService(
            sessions, events, FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        )
        session = service.create(config_snapshot={})

        from waxprep.session_lifecycle import SessionLifecycleError

        with self.assertRaises(SessionLifecycleError):
            service.transition(session.id, SessionStatus.RUNNING)

        loaded = service.get(session.id)
        assert loaded is not None
        self.assertEqual(loaded.status, SessionStatus.CREATED)
        self.assertEqual(events.count(session.id), 0)

    def test_metadata_update_failure_after_event_append(self) -> None:
        from waxprep.session_lifecycle import SessionLifecycleError

        class FailingSessionStore(InMemorySessionStore):
            def __init__(self) -> None:
                super().__init__()
                self.fail_next_update = False

            def update_metadata(self, session_id, metadata):  # type: ignore[no-untyped-def]
                if self.fail_next_update:
                    raise StorageError("simulated metadata failure")
                return super().update_metadata(session_id, metadata)

        sessions = FailingSessionStore()
        events = InMemoryEventStore()
        service = SessionLifecycleService(
            sessions, events, FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        )
        session = service.create(config_snapshot={})
        sessions.fail_next_update = True

        with self.assertRaises(SessionLifecycleError):
            service.transition(session.id, SessionStatus.RUNNING)

        # Event was written; metadata still shows created
        self.assertEqual(events.count(session.id), 1)
        loaded = service.get(session.id)
        assert loaded is not None
        self.assertEqual(loaded.status, SessionStatus.CREATED)


class FileSessionLifecycleTests(unittest.TestCase):
    """Durable file-storage proof for session lifecycle."""

    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        from waxprep.file_storage import FileEventStore, FileSessionStore

        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name).resolve()
        self.clock = FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        self.sessions = FileSessionStore(self.data_dir)
        self.events = FileEventStore(self.data_dir)
        self.service = SessionLifecycleService(self.sessions, self.events, self.clock)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_session_and_events_survive_file_store_recreation(self) -> None:

        from waxprep.file_storage import FileEventStore, FileSessionStore

        session = self.service.create(
            config_snapshot={"mode": "durable"},
            workspace_ref="/tmp/ws",
        )
        self.service.transition(session.id, SessionStatus.RUNNING)
        self.service.transition(session.id, SessionStatus.WAITING)

        # Recreate stores and service from the same directory
        sessions2 = FileSessionStore(self.data_dir)
        events2 = FileEventStore(self.data_dir)
        service2 = SessionLifecycleService(sessions2, events2, self.clock)

        loaded = service2.get(session.id)
        assert loaded is not None
        self.assertEqual(loaded.status, SessionStatus.WAITING)
        self.assertEqual(dict(loaded.config_snapshot), {"mode": "durable"})
        self.assertEqual(loaded.workspace_ref, "/tmp/ws")

        history = events2.read_from_sequence(session.id, 1)
        self.assertEqual(len(history), 2)
        self.assertEqual(
            tuple(e.payload["new_value"] for e in history),
            ("running", "waiting"),
        )


if __name__ == "__main__":
    unittest.main()

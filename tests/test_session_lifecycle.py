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


if __name__ == "__main__":
    unittest.main()

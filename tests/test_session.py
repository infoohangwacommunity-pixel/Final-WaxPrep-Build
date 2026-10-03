"""Tests for the WaxPrep session model."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta, timezone

from waxprep.clock import FakeClock
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.session import InvalidSession, Session, SessionStatus


class SessionModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(datetime(2026, 10, 3, tzinfo=UTC))
        self.session_id = generate_wax_id(WaxIdKind.SESSION, self.clock)

    def test_valid_session_in_created_state(self) -> None:
        session = Session(
            id=self.session_id,
            created=self.clock.now(),
            status=SessionStatus.CREATED,
            config_snapshot={"model": "test"},
            workspace_ref=None,
        )

        self.assertEqual(session.status, SessionStatus.CREATED)
        self.assertEqual(session.config_snapshot["model"], "test")

    def test_rejects_non_session_id(self) -> None:
        event_id = generate_wax_id(WaxIdKind.EVENT, self.clock)

        with self.assertRaises(InvalidSession):
            Session(
                id=event_id,
                created=self.clock.now(),
                status=SessionStatus.CREATED,
                config_snapshot={},
            )

    def test_rejects_invalid_status(self) -> None:
        with self.assertRaises(InvalidSession):
            Session(
                id=self.session_id,
                created=self.clock.now(),
                status="banana",  # type: ignore[arg-type]
                config_snapshot={},
            )

    def test_rejects_naive_timestamp(self) -> None:
        with self.assertRaises(InvalidSession):
            Session(
                id=self.session_id,
                created=datetime(2026, 10, 3),
                status=SessionStatus.CREATED,
                config_snapshot={},
            )

    def test_normalizes_aware_timestamp_to_utc(self) -> None:
        offset = timezone(timedelta(hours=1))
        local = datetime(2026, 10, 3, 1, 0, tzinfo=offset)

        session = Session(
            id=self.session_id,
            created=local,
            status=SessionStatus.CREATED,
            config_snapshot={},
        )

        self.assertEqual(session.created, datetime(2026, 10, 3, 0, 0, tzinfo=UTC))

    def test_config_snapshot_is_immutable(self) -> None:
        original = {"nested": {"a": 1}, "list": [1, 2]}
        session = Session(
            id=self.session_id,
            created=self.clock.now(),
            status=SessionStatus.CREATED,
            config_snapshot=original,
        )

        original["nested"]["a"] = 99
        original["list"].append(3)

        self.assertEqual(dict(session.config_snapshot["nested"]), {"a": 1})
        self.assertEqual(list(session.config_snapshot["list"]), [1, 2])

        with self.assertRaises(TypeError):
            session.config_snapshot["x"] = 1  # type: ignore[index]

    def test_rejects_unsupported_config_types(self) -> None:
        with self.assertRaises(InvalidSession):
            Session(
                id=self.session_id,
                created=self.clock.now(),
                status=SessionStatus.CREATED,
                config_snapshot={"bad": object()},
            )

    def test_workspace_ref_validation(self) -> None:
        session = Session(
            id=self.session_id,
            created=self.clock.now(),
            status=SessionStatus.CREATED,
            config_snapshot={},
            workspace_ref="/tmp/workspace",
        )
        self.assertEqual(session.workspace_ref, "/tmp/workspace")

        with self.assertRaises(InvalidSession):
            Session(
                id=self.session_id,
                created=self.clock.now(),
                status=SessionStatus.CREATED,
                config_snapshot={},
                workspace_ref="",
            )

    def test_metadata_round_trip(self) -> None:
        session = Session(
            id=self.session_id,
            created=self.clock.now(),
            status=SessionStatus.CREATED,
            config_snapshot={"k": "v"},
            workspace_ref=None,
        )

        restored = Session.from_metadata(session.to_metadata())
        self.assertEqual(restored, session)


if __name__ == "__main__":
    unittest.main()

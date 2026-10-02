"""Tests for the WaxPrep clock abstraction."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from waxprep.clock import FakeClock


class FakeClockTests(unittest.TestCase):
    def test_advance_moves_wall_clock_forward(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, 2, 0, tzinfo=UTC))

        clock.advance(5)

        self.assertEqual(
            clock.now(),
            datetime(2026, 10, 2, 2, 0, 5, tzinfo=UTC),
        )

    def test_advance_moves_monotonic_time_by_same_amount(self) -> None:
        clock = FakeClock(
            datetime(2026, 10, 2, 2, 0, tzinfo=UTC),
            monotonic_start=100.0,
        )

        clock.advance(7.5)

        self.assertEqual(clock.monotonic(), 107.5)

    def test_multiple_advances_accumulate(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, 2, 0, tzinfo=UTC))

        clock.advance(2)
        clock.advance(3.5)

        self.assertEqual(
            clock.now(),
            datetime(
                2026,
                10,
                2,
                2,
                0,
                5,
                500_000,
                tzinfo=UTC,
            ),
        )
        self.assertEqual(clock.monotonic(), 5.5)

    def test_negative_advance_is_rejected(self) -> None:
        clock = FakeClock(datetime(2026, 10, 2, 2, 0, tzinfo=UTC))

        with self.assertRaises(ValueError):
            clock.advance(-1)

    def test_start_time_must_be_timezone_aware(self) -> None:
        with self.assertRaises(ValueError):
            FakeClock(datetime(2026, 10, 2, 2, 0))

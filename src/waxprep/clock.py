"""Injectable wall-clock and monotonic time for WaxPrep."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Provide the two kinds of time WaxPrep needs."""

    def now(self) -> datetime:
        """Return the current timezone-aware wall-clock time."""

    def monotonic(self) -> float:
        """Return a continuously increasing elapsed-time reading."""


class RealClock:
    """Read time from the operating system."""

    def now(self) -> datetime:
        """Return the current UTC wall-clock time."""

        return datetime.fromtimestamp(time.time(), tz=UTC)

    def monotonic(self) -> float:
        """Return the operating system's monotonic elapsed-time reading."""

        return time.monotonic()


class FakeClock:
    """A controllable clock for deterministic tests."""

    def __init__(
        self,
        start: datetime,
        monotonic_start: float = 0.0,
    ) -> None:
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("FakeClock start time must be timezone-aware.")
        self._now = start
        self._monotonic = monotonic_start

    def now(self) -> datetime:
        """Return the fake wall-clock time."""

        return self._now

    def monotonic(self) -> float:
        """Return the fake elapsed-time reading."""

        return self._monotonic

    def advance(self, seconds: float) -> None:
        """Advance both fake time readings by the same number of seconds."""

        if seconds < 0:
            raise ValueError("FakeClock cannot move backwards.")
        self._now += timedelta(seconds=seconds)
        self._monotonic += seconds

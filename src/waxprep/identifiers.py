"""Stable, time-sortable identifiers for WaxPrep.

WaxPrep IDs identify durable or observable objects without encoding
application-specific meaning into the identifier itself.

The generated identifier has the form::

    wax_<kind>_<uuid7>

For example::

    wax_session_0199d2f4-7a4c-7a31-9f2e-4f7a9b7f5d10

The UUID portion follows the UUIDv7 layout: its leading 48 bits contain the
Unix timestamp in milliseconds, while the remaining bits provide randomness.
This makes IDs sortable by creation time across different milliseconds while
keeping collision probability extremely small.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from enum import StrEnum
from uuid import RFC_4122, UUID

from waxprep.clock import Clock, RealClock


class WaxIdKind(StrEnum):
    """Generic object kinds that may receive a WaxPrep ID."""

    SESSION = "session"
    CONVERSATION = "conversation"
    TURN = "turn"
    EVENT = "event"
    ACTION = "action"
    OBSERVATION = "observation"


@dataclass(frozen=True, slots=True)
class ParsedWaxId:
    """The validated parts of a WaxPrep ID."""

    kind: WaxIdKind
    uuid: UUID


class InvalidWaxId(ValueError):
    """Raised when a value is not a valid WaxPrep ID."""


_ID_PATTERN = re.compile(
    r"^wax_(?P<kind>[a-z]+)_(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})$"
)


def _timestamp_milliseconds(clock: Clock) -> int:
    """Return the clock's current Unix timestamp in milliseconds."""

    return int(clock.now().timestamp() * 1_000)


def _uuid7_from_timestamp(timestamp_ms: int) -> UUID:
    """Build a UUIDv7 value for a supplied Unix timestamp in milliseconds."""

    if timestamp_ms < 0 or timestamp_ms >= 1 << 48:
        raise ValueError("UUIDv7 timestamp must fit in 48 bits.")

    random_bits = secrets.randbits(74)

    random_a = (random_bits >> 62) & ((1 << 12) - 1)
    random_b = random_bits & ((1 << 62) - 1)

    value = timestamp_ms << 80
    value |= 0b0111 << 76
    value |= random_a << 64
    value |= 0b10 << 62
    value |= random_b

    return UUID(int=value)


def generate_wax_id(
    kind: WaxIdKind | str,
    clock: Clock | None = None,
) -> str:
    """Generate a new stable, time-sortable WaxPrep ID."""

    normalized_kind = _normalize_kind(kind)
    active_clock = clock if clock is not None else RealClock()
    identifier = _uuid7_from_timestamp(_timestamp_milliseconds(active_clock))
    return f"wax_{normalized_kind.value}_{identifier}"


def parse_wax_id(value: str) -> ParsedWaxId:
    """Parse and validate a WaxPrep ID."""

    if not isinstance(value, str):
        raise InvalidWaxId("Wax ID must be a string.")

    match = _ID_PATTERN.fullmatch(value)
    if match is None:
        raise InvalidWaxId("Malformed Wax ID.")

    try:
        kind = WaxIdKind(match.group("kind"))
        identifier = UUID(match.group("uuid"))
    except ValueError as exc:
        raise InvalidWaxId("Wax ID contains an unknown kind or invalid UUID.") from exc

    if identifier.version != 7 or identifier.variant != RFC_4122:
        raise InvalidWaxId("Wax ID must contain a UUIDv7 value.")

    return ParsedWaxId(kind=kind, uuid=identifier)


def is_valid_wax_id(value: object) -> bool:
    """Return whether ``value`` is a valid WaxPrep ID."""

    if not isinstance(value, str):
        return False

    try:
        parse_wax_id(value)
    except InvalidWaxId:
        return False

    return True


def _normalize_kind(kind: WaxIdKind | str) -> WaxIdKind:
    """Normalize and validate an identifier kind."""

    if isinstance(kind, WaxIdKind):
        return kind

    if not isinstance(kind, str):
        raise ValueError("Wax ID kind must be a string or WaxIdKind.")

    try:
        return WaxIdKind(kind.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in WaxIdKind)
        raise ValueError(f"Unknown Wax ID kind. Expected one of: {allowed}.") from exc

"""Immutable, validated event envelopes for WaxPrep."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, NoReturn

from waxprep.event_types import EventKind, InvalidEventEnvelope, validate_event_payload
from waxprep.identifiers import InvalidWaxId, WaxIdKind, parse_wax_id

_EVENT_FIELDS = frozenset(
    {
        "id",
        "session_id",
        "sequence",
        "timestamp",
        "kind",
        "schema_version",
        "payload",
        "parent_id",
        "cause_id",
    }
)


def _freeze_payload(value: Any) -> Any:
    """Convert JSON-compatible mutable values into immutable values."""

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidEventEnvelope("payload contains a non-finite number.")
        return value

    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise InvalidEventEnvelope("payload object keys must be strings.")
        return MappingProxyType(
            {key: _freeze_payload(item) for key, item in value.items()}
        )

    if isinstance(value, list):
        return tuple(_freeze_payload(item) for item in value)

    raise InvalidEventEnvelope(
        f"payload contains an unsupported value type: {type(value).__name__}."
    )


def _thaw_payload(value: Any) -> Any:
    """Convert the internal immutable payload back to JSON-compatible values."""

    if isinstance(value, MappingProxyType):
        return {key: _thaw_payload(item) for key, item in value.items()}

    if isinstance(value, tuple):
        return [_thaw_payload(item) for item in value]

    return value


def _validate_id(value: object, kind: WaxIdKind, field_name: str) -> str:
    """Validate a WAX ID and require the expected kind."""

    if not isinstance(value, str):
        raise InvalidEventEnvelope(f"{field_name} must be a WaxPrep ID string.")

    try:
        parsed = parse_wax_id(value)
    except InvalidWaxId as exc:
        raise InvalidEventEnvelope(
            f"{field_name} must be a valid WaxPrep {kind.value} ID."
        ) from exc

    if parsed.kind is not kind:
        raise InvalidEventEnvelope(f"{field_name} must be a WaxPrep {kind.value} ID.")

    return value


def _validate_timestamp(value: object) -> datetime:
    """Validate and normalize an event timestamp to UTC."""

    if not isinstance(value, datetime):
        raise InvalidEventEnvelope("timestamp must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidEventEnvelope("timestamp must be timezone-aware.")

    return value.astimezone(UTC)


def _parse_timestamp(value: object) -> datetime:
    """Parse and validate an ISO 8601 event timestamp."""

    if not isinstance(value, str):
        raise InvalidEventEnvelope("timestamp must be an ISO 8601 string.")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEventEnvelope(
            "timestamp must be a valid ISO 8601 timestamp."
        ) from exc

    return _validate_timestamp(parsed)


def _reject_invalid_json_number(value: str) -> NoReturn:
    """Reject JSON extensions such as NaN and Infinity."""

    raise InvalidEventEnvelope(f"invalid JSON number: {value}.")


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Reject duplicate keys instead of silently keeping the last value."""

    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise InvalidEventEnvelope(f"duplicate JSON object key: {key}.")
        result[key] = value

    return result


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """The common immutable wrapper around every recorded WaxPrep event."""

    id: str
    session_id: str
    sequence: int
    timestamp: datetime
    kind: EventKind | str
    schema_version: int
    payload: Any
    parent_id: str | None = None
    cause_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            _validate_id(self.id, WaxIdKind.EVENT, "id"),
        )

        object.__setattr__(
            self,
            "session_id",
            _validate_id(self.session_id, WaxIdKind.SESSION, "session_id"),
        )

        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 1
        ):
            raise InvalidEventEnvelope("sequence must be a positive integer.")

        object.__setattr__(self, "timestamp", _validate_timestamp(self.timestamp))

        try:
            event_kind = EventKind(self.kind)
        except ValueError as exc:
            raise InvalidEventEnvelope(
                f"unsupported event kind: {self.kind!r}."
            ) from exc

        object.__setattr__(self, "kind", event_kind)

        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version < 1
        ):
            raise InvalidEventEnvelope("schema_version must be a positive integer.")

        validate_event_payload(event_kind, self.payload)
        object.__setattr__(self, "payload", _freeze_payload(self.payload))

        if self.parent_id is not None:
            object.__setattr__(
                self,
                "parent_id",
                _validate_id(self.parent_id, WaxIdKind.EVENT, "parent_id"),
            )

        if self.cause_id is not None:
            object.__setattr__(
                self,
                "cause_id",
                _validate_id(self.cause_id, WaxIdKind.EVENT, "cause_id"),
            )

    def to_dict(self) -> dict[str, Any]:
        """Return the envelope as JSON-compatible Python values."""

        kind_value = self.kind.value if isinstance(self.kind, EventKind) else self.kind

        return {
            "id": self.id,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
            "kind": kind_value,
            "schema_version": self.schema_version,
            "payload": _thaw_payload(self.payload),
            "parent_id": self.parent_id,
            "cause_id": self.cause_id,
        }

    def to_json(self) -> str:
        """Serialize the envelope to strict JSON."""

        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @classmethod
    def from_json(cls, json_text: str) -> EventEnvelope:
        """Deserialize and strictly validate an event envelope from JSON."""

        if not isinstance(json_text, str):
            raise InvalidEventEnvelope("JSON input must be a string.")

        try:
            data = json.loads(
                json_text,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_invalid_json_number,
            )
        except InvalidEventEnvelope:
            raise
        except (json.JSONDecodeError, TypeError) as exc:
            raise InvalidEventEnvelope("invalid JSON event envelope.") from exc

        if not isinstance(data, dict):
            raise InvalidEventEnvelope("event envelope JSON must be an object.")

        if set(data) != _EVENT_FIELDS:
            raise InvalidEventEnvelope(
                "event envelope fields do not exactly match the required schema."
            )

        return cls(
            id=data["id"],
            session_id=data["session_id"],
            sequence=data["sequence"],
            timestamp=_parse_timestamp(data["timestamp"]),
            kind=data["kind"],
            schema_version=data["schema_version"],
            payload=data["payload"],
            parent_id=data["parent_id"],
            cause_id=data["cause_id"],
        )


# Re-export for existing imports
__all__ = [
    "EventEnvelope",
    "EventKind",
    "InvalidEventEnvelope",
]

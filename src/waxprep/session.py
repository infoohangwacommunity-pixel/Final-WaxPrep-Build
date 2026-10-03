"""Session model for WaxPrep.

A session is the durable container for one piece of ongoing agent work.
This module defines the session fields and status values only. Lifecycle
transitions live in ``session_lifecycle``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from waxprep.identifiers import InvalidWaxId, WaxIdKind, parse_wax_id


class SessionStatus(StrEnum):
    """Lifecycle status of a session."""

    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES: frozenset[SessionStatus] = frozenset(
    {
        SessionStatus.FINISHED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    }
)


class InvalidSession(ValueError):
    """Raised when session data fails validation."""


def _validate_session_id(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidSession("session id must be a string.")

    try:
        parsed = parse_wax_id(value)
    except InvalidWaxId as exc:
        raise InvalidSession("session id must be a valid WaxPrep session ID.") from exc

    if parsed.kind is not WaxIdKind.SESSION:
        raise InvalidSession("session id must be a WaxPrep session ID.")

    return value


def _validate_created(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise InvalidSession("created must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidSession("created must be timezone-aware.")

    return value.astimezone(UTC)


def _freeze_config(value: object) -> Mapping[str, Any]:
    """Deep-freeze a JSON-compatible configuration snapshot."""

    if not isinstance(value, Mapping):
        raise InvalidSession("config_snapshot must be a mapping.")

    if any(not isinstance(key, str) for key in value):
        raise InvalidSession("config_snapshot keys must be strings.")

    return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: object) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidSession("config_snapshot cannot contain non-finite numbers.")
        return value

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise InvalidSession("config_snapshot nested keys must be strings.")
        return MappingProxyType(
            {key: _freeze_value(item) for key, item in value.items()}
        )

    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)

    raise InvalidSession(
        f"config_snapshot contains unsupported type: {type(value).__name__}."
    )


def _thaw_value(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _validate_workspace_ref(value: object) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise InvalidSession("workspace_ref must be a string or None.")

    if not value.strip():
        raise InvalidSession("workspace_ref must not be empty.")

    return value


@dataclass(frozen=True, slots=True)
class Session:
    """Immutable domain-neutral session record."""

    id: str
    created: datetime
    status: SessionStatus
    config_snapshot: Mapping[str, Any]
    workspace_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_session_id(self.id))
        object.__setattr__(self, "created", _validate_created(self.created))

        if isinstance(self.status, SessionStatus):
            status = self.status
        elif isinstance(self.status, str):
            try:
                status = SessionStatus(self.status)
            except ValueError as exc:
                raise InvalidSession(
                    f"unknown session status: {self.status!r}."
                ) from exc
        else:
            raise InvalidSession("status must be a SessionStatus or status string.")

        object.__setattr__(self, "status", status)
        object.__setattr__(
            self, "config_snapshot", _freeze_config(self.config_snapshot)
        )
        object.__setattr__(
            self,
            "workspace_ref",
            _validate_workspace_ref(self.workspace_ref),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Serialize session fields for SessionStore metadata."""

        return {
            "id": self.id,
            "created": self.created.isoformat().replace("+00:00", "Z"),
            "status": self.status.value,
            "config_snapshot": _thaw_value(self.config_snapshot),
            "workspace_ref": self.workspace_ref,
        }

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any]) -> Session:
        """Reconstruct a Session from SessionStore metadata."""

        required = {"id", "created", "status", "config_snapshot", "workspace_ref"}
        if not required.issubset(set(metadata)):
            raise InvalidSession(
                "session metadata is missing required lifecycle fields."
            )

        created_raw = metadata["created"]
        if isinstance(created_raw, str):
            try:
                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except ValueError as exc:
                raise InvalidSession("session created timestamp is invalid.") from exc
        else:
            created = created_raw

        return cls(
            id=metadata["id"],
            created=created,
            status=metadata["status"],
            config_snapshot=metadata["config_snapshot"],
            workspace_ref=metadata["workspace_ref"],
        )


__all__ = [
    "InvalidSession",
    "Session",
    "SessionStatus",
    "TERMINAL_STATUSES",
]

"""Versioned event-schema migrations for WaxPrep."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any, Final

CURRENT_EVENT_SCHEMA_VERSION: Final = 2


class EventMigrationError(ValueError):
    """Raised when an event cannot be migrated to the current schema."""


EventData = dict[str, Any]
Migration = Callable[[EventData], EventData]


def _migrate_v1_to_v2(data: EventData) -> EventData:
    """Migrate the Prompt 18 placeholder event format to Prompt 19."""

    if data.get("kind") != "placeholder":
        raise EventMigrationError(
            "schema version 1 events must use the placeholder event kind."
        )

    payload = data.get("payload")

    try:
        legacy_payload = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise EventMigrationError(
            "schema version 1 payload cannot be represented in the current schema."
        ) from exc

    migrated = dict(data)
    migrated["kind"] = "system_notice"
    migrated["payload"] = {
        "message": f"Legacy placeholder event payload: {legacy_payload}",
    }
    migrated["schema_version"] = 2

    return migrated


# The dictionary key is the schema version being migrated FROM.
#
# Never edit an existing migration after it has been released.
# Add a new entry for each new schema transition instead.
MIGRATIONS: Final[dict[int, Migration]] = {
    1: _migrate_v1_to_v2,
}


def migrate_event_data(data: Mapping[str, Any]) -> EventData:
    """Upgrade event data to the current schema version."""

    if not isinstance(data, Mapping):
        raise EventMigrationError("event data must be an object.")

    migrated: EventData = dict(data)

    version = migrated.get("schema_version")

    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise EventMigrationError("event schema_version must be a positive integer.")

    if version > CURRENT_EVENT_SCHEMA_VERSION:
        raise EventMigrationError(
            "event schema_version is newer than the supported schema."
        )

    while version < CURRENT_EVENT_SCHEMA_VERSION:
        migration = MIGRATIONS.get(version)

        if migration is None:
            raise EventMigrationError(
                f"no migration exists from event schema version {version}."
            )

        migrated = migration(migrated)

        new_version = migrated.get("schema_version")

        if (
            isinstance(new_version, bool)
            or not isinstance(new_version, int)
            or new_version <= version
        ):
            raise EventMigrationError(
                f"migration from schema version {version} "
                "did not advance the schema version."
            )

        version = new_version

    return migrated


__all__ = [
    "CURRENT_EVENT_SCHEMA_VERSION",
    "EventMigrationError",
    "MIGRATIONS",
    "migrate_event_data",
]

"""Durable file-based storage implementations for WaxPrep.

This module provides a filesystem-backed implementation of the existing
EventStore and SessionStore contracts.

Event history is stored as append-only JSON Lines, one event per line.
Session metadata is stored separately as JSON.

The caller must provide the data directory explicitly. The storage layer never
chooses a path inside the source workspace implicitly.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import warnings
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from threading import RLock
from typing import Any

from waxprep.event import EventEnvelope, InvalidEventEnvelope
from waxprep.session_lock import session_write_lock
from waxprep.storage import (
    EventStore,
    SessionRecord,
    SessionStore,
    StorageConflictError,
    StorageError,
    StorageNotFoundError,
    _validate_session_id,
)

_LOGGER = logging.getLogger(__name__)

_EVENTS_FILENAME = "events.jsonl"
_METADATA_FILENAME = "metadata.json"


class StorageCorruptionWarning(UserWarning):
    """Warning emitted when a recoverable final JSONL line is corrupted."""


class StorageCorruptionError(StorageError):
    """Raised when durable storage contains unrecoverable corruption."""


def _validate_sequence(sequence: object, field_name: str) -> int:
    """Validate a positive integer sequence value."""

    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValueError(f"{field_name} must be a positive integer.")

    return sequence


def _coerce_data_dir(data_dir: str | Path) -> Path:
    """Return a validated absolute data directory path."""

    path = Path(data_dir).expanduser()

    if not path.is_absolute():
        raise ValueError("data_dir must be an absolute path outside the workspace.")

    path.mkdir(parents=True, exist_ok=True)

    if not path.is_dir():
        raise ValueError("data_dir must be a directory.")

    return path


def _session_directory(data_dir: Path, session_id: str) -> Path:
    """Return the filesystem directory belonging to one valid session."""

    return data_dir / _validate_session_id(session_id)


def _events_path(data_dir: Path, session_id: str) -> Path:
    """Return the JSONL event-log path for one session."""

    return _session_directory(data_dir, session_id) / _EVENTS_FILENAME


def _metadata_path(data_dir: Path, session_id: str) -> Path:
    """Return the metadata JSON path for one session."""

    return _session_directory(data_dir, session_id) / _METADATA_FILENAME


def _strict_json_dumps(value: Any) -> str:
    """Serialize JSON without allowing non-standard JSON values."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _read_event_lines(path: Path) -> tuple[tuple[EventEnvelope, ...], int]:
    """Read a JSONL event log while tolerating a corrupted final line.

    A malformed final line is treated as a recoverable partial-write condition.
    It is reported through StorageCorruptionWarning and ignored.

    A malformed non-final line is unrecoverable because later records can no
    longer be trusted to represent a complete ordered history.
    """

    if not path.exists():
        return (), 0

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StorageError(f"unable to read event log: {path}") from exc

    if not raw:
        return (), 0

    lines = raw.splitlines(keepends=True)
    events: list[EventEnvelope] = []

    for index, raw_line in enumerate(lines):
        is_final_line = index == len(lines) - 1

        if not raw_line.strip():
            if is_final_line:
                continue

            raise StorageCorruptionError(f"blank line found inside event log: {path}")

        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError as exc:
            if is_final_line:
                _report_final_line_corruption(path, index + 1, "invalid UTF-8")
                break

            raise StorageCorruptionError(
                f"invalid UTF-8 inside event log {path} at line {index + 1}"
            ) from exc

        line = line.rstrip("\r\n")

        try:
            event = EventEnvelope.from_json(line)
        except (InvalidEventEnvelope, ValueError, TypeError) as exc:
            if is_final_line:
                _report_final_line_corruption(
                    path,
                    index + 1,
                    "incomplete or invalid final JSON event",
                )
                break

            raise StorageCorruptionError(
                f"invalid event record inside {path} at line {index + 1}"
            ) from exc

        events.append(event)

    _validate_event_history(path, events)

    # Byte offset of the last fully accepted line (for truncating a corrupt tail).
    valid_end = 0
    for index, raw_line in enumerate(lines):
        if index >= len(events):
            break
        valid_end += len(raw_line)

    return tuple(events), valid_end


def _report_final_line_corruption(
    path: Path,
    line_number: int,
    reason: str,
) -> None:
    """Report recoverable corruption without raising an exception."""

    message = (
        f"ignored corrupted final event-log line {line_number} in {path}: {reason}."
    )

    warnings.warn(
        message,
        StorageCorruptionWarning,
        stacklevel=3,
    )

    _LOGGER.warning(message)


def _validate_event_history(
    path: Path,
    events: list[EventEnvelope],
) -> None:
    """Ensure the readable portion of a log remains a valid event history."""

    previous_session_id: str | None = None

    for expected_sequence, event in enumerate(events, start=1):
        if previous_session_id is None:
            previous_session_id = event.session_id
        elif event.session_id != previous_session_id:
            raise StorageCorruptionError(
                f"event log {path} contains multiple session IDs."
            )

        if event.sequence != expected_sequence:
            raise StorageCorruptionError(
                f"event log {path} has invalid sequence at event "
                f"{event.sequence}; expected {expected_sequence}."
            )


def _append_event_line(path: Path, event: EventEnvelope) -> None:
    """Atomically append one complete JSONL record and flush it to disk."""

    serialized = event.to_json() + "\n"
    encoded = serialized.encode("utf-8")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("ab") as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
    except OSError as exc:
        raise StorageError(f"unable to append event to {path}") from exc


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a text file with durable contents."""

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, path)

        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None

        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        temporary_path = None
    except OSError as exc:
        raise StorageError(f"unable to write durable file: {path}") from exc
    finally:
        if temporary_path is not None:
            with suppress(FileNotFoundError):
                temporary_path.unlink()


def _read_metadata(path: Path) -> SessionRecord:
    """Read and validate a durable session metadata file."""

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StorageCorruptionError(
            f"unable to read session metadata: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise StorageCorruptionError(f"session metadata must be a JSON object: {path}")

    if set(data) != {"id", "metadata"}:
        raise StorageCorruptionError(f"session metadata fields are invalid: {path}")

    session_id = data["id"]
    metadata = data["metadata"]

    if not isinstance(session_id, str):
        raise StorageCorruptionError(f"session metadata id must be a string: {path}")

    if not isinstance(metadata, dict):
        raise StorageCorruptionError(
            f"session metadata value must be an object: {path}"
        )

    return SessionRecord(
        id=session_id,
        metadata=metadata,
    )


def _write_metadata(path: Path, session: SessionRecord) -> None:
    """Write a session metadata record durably."""

    data = {
        "id": session.id,
        "metadata": dict(session.metadata),
    }

    try:
        serialized = _strict_json_dumps(data)
    except (TypeError, ValueError) as exc:
        raise StorageError(
            f"session metadata is not JSON serializable: {session.id!r}"
        ) from exc

    _atomic_write_text(path, serialized + "\n")


class FileEventStore(EventStore):
    """Durable append-only filesystem implementation of EventStore."""

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = _coerce_data_dir(data_dir)
        self._lock = RLock()

    @property
    def data_dir(self) -> Path:
        """Return the configured durable data directory."""

        return self._data_dir

    def append(self, event: EventEnvelope) -> None:
        """Append one event using the next required sequence number."""

        if not isinstance(event, EventEnvelope):
            raise TypeError("event must be an EventEnvelope.")

        session_id = _validate_session_id(event.session_id)

        with self._lock, session_write_lock(self._data_dir, session_id):
            path = _events_path(self._data_dir, session_id)
            events, valid_end = _read_event_lines(path)
            expected_sequence = len(events) + 1

            if event.sequence != expected_sequence:
                raise StorageConflictError(
                    "event sequence must be the next gap-free sequence "
                    f"for session {session_id!r}: expected "
                    f"{expected_sequence}, got {event.sequence}."
                )

            # Drop a recoverable corrupt final line before appending.
            if path.exists() and path.stat().st_size > valid_end:
                with path.open("r+b") as file:
                    file.truncate(valid_end)
                    file.flush()
                    os.fsync(file.fileno())

            _append_event_line(path, event)

    def read_range(
        self,
        session_id: str,
        start_sequence: int,
        end_sequence: int,
    ) -> tuple[EventEnvelope, ...]:
        """Read ``start_sequence <= sequence < end_sequence``."""

        session_id = _validate_session_id(session_id)
        start_sequence = _validate_sequence(start_sequence, "start_sequence")
        end_sequence = _validate_sequence(end_sequence, "end_sequence")

        if end_sequence < start_sequence:
            raise ValueError("end_sequence must be >= start_sequence.")

        with self._lock:
            events, _ = _read_event_lines(
                _events_path(self._data_dir, session_id),
            )

            return tuple(
                event
                for event in events
                if start_sequence <= event.sequence < end_sequence
            )

    def read_from_sequence(
        self,
        session_id: str,
        start_sequence: int,
    ) -> tuple[EventEnvelope, ...]:
        """Read from ``start_sequence`` through the current session end."""

        session_id = _validate_session_id(session_id)
        start_sequence = _validate_sequence(start_sequence, "start_sequence")

        with self._lock:
            events, _ = _read_event_lines(
                _events_path(self._data_dir, session_id),
            )

            return tuple(event for event in events if event.sequence >= start_sequence)

    def count(self, session_id: str) -> int:
        """Return the number of readable events for one session."""

        session_id = _validate_session_id(session_id)

        with self._lock:
            events, _ = _read_event_lines(
                _events_path(self._data_dir, session_id),
            )
            return len(events)

    def __len__(self) -> int:
        """Return the total number of readable events across sessions."""

        total = 0

        with self._lock:
            if not self._data_dir.exists():
                return 0

            for session_directory in self._data_dir.iterdir():
                if not session_directory.is_dir():
                    continue

                events_path = session_directory / _EVENTS_FILENAME

                if events_path.exists():
                    events, _ = _read_event_lines(events_path)
                    total += len(events)

        return total


class FileSessionStore(SessionStore):
    """Durable filesystem implementation of SessionStore."""

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = _coerce_data_dir(data_dir)
        self._lock = RLock()

    @property
    def data_dir(self) -> Path:
        """Return the configured durable data directory."""

        return self._data_dir

    def create(self, session: SessionRecord) -> None:
        """Atomically create a session metadata record."""

        if not isinstance(session, SessionRecord):
            raise TypeError("session must be a SessionRecord.")

        with self._lock, session_write_lock(self._data_dir, session.id):
            session_directory = _session_directory(
                self._data_dir,
                session.id,
            )
            metadata_path = session_directory / _METADATA_FILENAME

            session_directory.mkdir(parents=True, exist_ok=True)

            try:
                with metadata_path.open(
                    mode="x",
                    encoding="utf-8",
                ) as file:
                    content = _strict_json_dumps(
                        {
                            "id": session.id,
                            "metadata": dict(session.metadata),
                        }
                    )
                    file.write(content)
                    file.write("\n")
                    file.flush()
                    os.fsync(file.fileno())
            except FileExistsError as exc:
                raise StorageConflictError(
                    f"session already exists: {session.id!r}."
                ) from exc
            except (OSError, TypeError, ValueError) as exc:
                raise StorageError(f"unable to create session: {session.id!r}") from exc

    def get(self, session_id: str) -> SessionRecord | None:
        """Return a session snapshot, or None when it does not exist."""

        session_id = _validate_session_id(session_id)

        with self._lock:
            path = _metadata_path(self._data_dir, session_id)

            if not path.exists():
                return None

            return _read_metadata(path)

    def list(self) -> tuple[SessionRecord, ...]:
        """Return all sessions in deterministic ID order."""

        with self._lock:
            if not self._data_dir.exists():
                return ()

            sessions: list[SessionRecord] = []

            for session_directory in self._data_dir.iterdir():
                if not session_directory.is_dir():
                    continue

                metadata_path = session_directory / _METADATA_FILENAME

                if metadata_path.exists():
                    sessions.append(_read_metadata(metadata_path))

            sessions.sort(key=lambda session: session.id)

            return tuple(sessions)

    def update_metadata(
        self,
        session_id: str,
        metadata: Mapping[str, object],
    ) -> SessionRecord:
        """Replace a session's complete metadata snapshot."""

        session_id = _validate_session_id(session_id)

        with self._lock, session_write_lock(self._data_dir, session_id):
            path = _metadata_path(self._data_dir, session_id)

            if not path.exists():
                raise StorageNotFoundError(f"session does not exist: {session_id!r}.")

            updated = SessionRecord(
                id=session_id,
                metadata=metadata,
            )

            _write_metadata(path, updated)

            return _read_metadata(path)

    def __len__(self) -> int:
        """Return the number of stored sessions."""

        return len(self.list())


__all__ = [
    "FileEventStore",
    "FileSessionStore",
    "StorageCorruptionError",
    "StorageCorruptionWarning",
]

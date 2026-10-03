"""Cross-process write locks for individual WaxPrep sessions."""

from __future__ import annotations

import errno
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from waxprep.storage import StorageConflictError, StorageError

_LOCK_FILENAME = ".waxprep-write.lock"


def _acquire_os_lock(file_descriptor: int) -> None:
    """Acquire a non-blocking exclusive operating-system file lock."""

    if os.name == "nt":
        import msvcrt

        os.lseek(file_descriptor, 0, os.SEEK_SET)
        msvcrt.locking(file_descriptor, msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
        return

    import fcntl

    fcntl.flock(
        file_descriptor,
        fcntl.LOCK_EX | fcntl.LOCK_NB,
    )


def _release_os_lock(file_descriptor: int) -> None:
    """Release the operating-system file lock."""

    if os.name == "nt":
        import msvcrt

        os.lseek(file_descriptor, 0, os.SEEK_SET)
        msvcrt.locking(file_descriptor, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return

    import fcntl

    fcntl.flock(file_descriptor, fcntl.LOCK_UN)


def _is_lock_contention(error: OSError) -> bool:
    """Return whether the operating system reports an occupied lock."""

    contention_errors = {
        errno.EACCES,
        errno.EAGAIN,
        errno.EDEADLK,
        errno.EWOULDBLOCK,
    }

    return error.errno in contention_errors


@contextmanager
def session_write_lock(
    data_dir: Path,
    session_id: str,
) -> Iterator[None]:
    """Protect one session's write operation across processes.

    The lock is non-blocking. If another writer currently owns the same
    session lock, raise ``StorageConflictError`` immediately.

    Different sessions use different lock files and remain independent.
    The operating system releases the lock when its owning process exits.
    """

    session_directory = data_dir / session_id

    try:
        session_directory.mkdir(parents=True, exist_ok=True)
        lock_path = session_directory / _LOCK_FILENAME

        with lock_path.open("a+b") as lock_file:
            try:
                lock_file.seek(0, os.SEEK_END)

                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()

                _acquire_os_lock(lock_file.fileno())

            except OSError as exc:
                if _is_lock_contention(exc):
                    raise StorageConflictError(
                        "another writer currently holds the lock for "
                        f"session {session_id!r}; retry the operation."
                    ) from exc

                raise StorageError(
                    f"unable to acquire write lock for session {session_id!r}."
                ) from exc

            try:
                yield
            finally:
                try:
                    _release_os_lock(lock_file.fileno())
                except OSError as exc:
                    raise StorageError(
                        f"unable to release write lock for session {session_id!r}."
                    ) from exc

    except StorageConflictError, StorageError:
        raise
    except OSError as exc:
        raise StorageError(
            f"unable to prepare write lock for session {session_id!r}."
        ) from exc


__all__ = ["session_write_lock"]

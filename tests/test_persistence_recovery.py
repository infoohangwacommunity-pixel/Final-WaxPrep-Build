"""Integration test: session/event history survives a genuine process restart."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from waxprep.event_history import format_event_timeline, query_events, replay_events
from waxprep.event_types import EventKind
from waxprep.file_storage import FileEventStore, FileSessionStore
from waxprep.session_lifecycle import SessionLifecycleService

# Writer runs in a separate process and exits. It must only leave durable files.
_WRITER_SCRIPT = r"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from waxprep.clock import FakeClock
from waxprep.event import EventEnvelope
from waxprep.event_types import EventKind
from waxprep.file_storage import FileEventStore, FileSessionStore
from waxprep.identifiers import WaxIdKind, generate_wax_id
from waxprep.session import SessionStatus
from waxprep.session_lifecycle import SessionLifecycleService


def main() -> int:
    data_dir = Path(sys.argv[1]).resolve()
    expected_path = Path(sys.argv[2]).resolve()

    clock = FakeClock(datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC))
    sessions = FileSessionStore(data_dir)
    events = FileEventStore(data_dir)
    lifecycle = SessionLifecycleService(sessions, events, clock)

    session = lifecycle.create(
        config_snapshot={"mode": "persistence-test", "version": 1},
        workspace_ref="/tmp/waxprep-persistence-test",
    )
    lifecycle.transition(session.id, SessionStatus.RUNNING)

    # Append additional non-lifecycle events with the next sequences.
    next_sequence = events.count(session.id) + 1
    varied = [
        (
            EventKind.USER_MESSAGE,
            {"text": "Create notes.txt with the word hello."},
        ),
        (
            EventKind.MODEL_MESSAGE,
            {"text": "I will write the file."},
        ),
        (
            EventKind.MODEL_TOOL_REQUEST,
            {
                "tool_name": "write_file",
                "arguments": {"path": "notes.txt", "content": "hello"},
            },
        ),
        (
            EventKind.ACTION_RESULT,
            {"status": "success", "result": "written"},
        ),
        (
            EventKind.SYSTEM_NOTICE,
            {"message": "persistence checkpoint"},
        ),
    ]

    for offset, (kind, payload) in enumerate(varied):
        clock.advance(0.001)
        events.append(
            EventEnvelope(
                id=generate_wax_id(WaxIdKind.EVENT, clock),
                session_id=session.id,
                sequence=next_sequence + offset,
                timestamp=clock.now(),
                kind=kind,
                payload=payload,
            )
        )

    lifecycle.transition(session.id, SessionStatus.FINISHED)

    # Expected state is established from the writer's own inputs, not from
    # the recovery path under test in the parent process.
    def plain(value):
        if isinstance(value, dict) or hasattr(value, "items"):
            return {str(k): plain(v) for k, v in dict(value).items()}
        if isinstance(value, (list, tuple)):
            return [plain(v) for v in value]
        return value

    history = events.read_from_sequence(session.id, 1)
    expected = {
        "session_id": session.id,
        "status": SessionStatus.FINISHED.value,
        "config_snapshot": {"mode": "persistence-test", "version": 1},
        "workspace_ref": "/tmp/waxprep-persistence-test",
        "event_count": len(history),
        "sequences": [event.sequence for event in history],
        "kinds": [
            event.kind.value if hasattr(event.kind, "value") else str(event.kind)
            for event in history
        ],
        "payloads": [plain(event.payload) for event in history],
    }
    expected_path.write_text(json.dumps(expected, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


class PersistenceRecoveryTests(unittest.TestCase):
    """Prove durable history survives process exit and reopen."""

    def test_session_and_events_survive_genuine_process_restart(self) -> None:
        repo_src = Path(__file__).resolve().parents[1] / "src"
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(repo_src) if not existing else f"{repo_src}{os.pathsep}{existing}"
        )

        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary).resolve()
            expected_path = data_dir / "expected.json"

            writer = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    _WRITER_SCRIPT,
                    str(data_dir),
                    str(expected_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                check=False,
            )
            self.assertEqual(
                writer.returncode,
                0,
                msg=(
                    "writer process failed:\n"
                    f"stdout:\n{writer.stdout}\n"
                    f"stderr:\n{writer.stderr}"
                ),
            )
            self.assertTrue(expected_path.exists())

            expected = json.loads(expected_path.read_text(encoding="utf-8"))

            # Fresh store objects in this process — no objects from the writer.
            sessions = FileSessionStore(data_dir)
            events = FileEventStore(data_dir)
            lifecycle = SessionLifecycleService(sessions, events)

            session_id = expected["session_id"]
            recovered = lifecycle.get(session_id)
            self.assertIsNotNone(recovered)
            assert recovered is not None

            self.assertEqual(recovered.id, session_id)
            self.assertEqual(recovered.status.value, expected["status"])
            self.assertEqual(
                dict(recovered.config_snapshot),
                expected["config_snapshot"],
            )
            self.assertEqual(recovered.workspace_ref, expected["workspace_ref"])

            history = events.read_from_sequence(session_id, 1)
            self.assertEqual(len(history), expected["event_count"])
            self.assertEqual(
                [event.sequence for event in history],
                expected["sequences"],
            )
            self.assertEqual(
                [
                    event.kind.value
                    if hasattr(event.kind, "value")
                    else str(event.kind)
                    for event in history
                ],
                expected["kinds"],
            )

            def plain(value):
                if isinstance(value, dict) or hasattr(value, "items"):
                    return {str(k): plain(v) for k, v in dict(value).items()}
                if isinstance(value, (list, tuple)):
                    return [plain(v) for v in value]
                return value

            self.assertEqual(
                [plain(event.payload) for event in history],
                expected["payloads"],
            )

            # Gap-free sequences starting at 1.
            self.assertEqual(
                expected["sequences"],
                list(range(1, expected["event_count"] + 1)),
            )

            # Replay visits every recovered event in order.
            visited: list[int] = []
            replay_events(history, lambda event: visited.append(event.sequence))
            self.assertEqual(visited, expected["sequences"])

            # Query and timeline operate on recovered durable history.
            notices = query_events(
                events,
                session_id,
                kind=EventKind.SYSTEM_NOTICE,
            )
            self.assertEqual(len(notices), 1)
            self.assertEqual(
                dict(notices[0].payload).get("message"),
                "persistence checkpoint",
            )

            timeline = format_event_timeline(history, session_id=session_id)
            self.assertIn(session_id, timeline)
            self.assertIn("user_message", timeline)
            self.assertIn("Create notes.txt", timeline)
            self.assertIn("finished", timeline)


if __name__ == "__main__":
    unittest.main()

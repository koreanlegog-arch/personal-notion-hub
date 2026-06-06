#!/usr/bin/env python3
"""Smoke check for dispatch-state cleanup archiving."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "cleanup-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        state = temp / "state.json"
        archive = temp / "archive.json"
        out = temp / "cleanup.json"
        state.write_text(
            json.dumps(
                {
                    "complete": {
                        "githubIssueUrl": "https://github.com/example/repo/issues/1",
                        "discordThreadId": "123",
                        "workerSessionId": "worker:1",
                        "workerStatus": "done",
                        "workerEvidenceRef": "ops/runs/a.json",
                        "privateNote": PRIVATE_MARKER,
                    },
                    "incomplete": {
                        "workerSessionId": "worker:2",
                        "workerStatus": "done",
                        "workerEvidenceRef": "ops/runs/b.json",
                        "privateNote": PRIVATE_MARKER,
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        dry = run_cleanup(state, archive, out)
        assert_true(dry.returncode == 0, dry.stderr)
        assert_true(PRIVATE_MARKER not in dry.stdout + out.read_text(encoding="utf-8"), "private_marker_leaked=true")
        plan = json.loads(out.read_text(encoding="utf-8"))
        assert_true(plan["selectedCount"] == 1, "selected_count_mismatch=true")

        applied = run_cleanup(state, archive, out, apply=True)
        assert_true(applied.returncode == 0, applied.stderr)
        active = json.loads(state.read_text(encoding="utf-8"))
        archived = json.loads(archive.read_text(encoding="utf-8"))
        assert_true("complete" in active and "incomplete" not in active, "active_state_cleanup_failed=true")
        assert_true(len(archived["events"]) == 1, "archive_event_missing=true")

    print("pnh_dispatch_state_cleanup_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def run_cleanup(state: Path, archive: Path, out: Path, *, apply: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_dispatch_state_cleanup.py"),
        "--state-file",
        str(state),
        "--archive-file",
        str(archive),
        "--out",
        str(out),
    ]
    if apply:
        command.append("--apply")
    return subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smoke check for unattended retry/backoff planning."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "retry-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        state = temp / "state.json"
        history = temp / "history.json"
        out = temp / "retry.json"
        state.write_text(
            json.dumps(
                {
                    "failed-packet": {"workerStatus": "failed", "privateNote": PRIVATE_MARKER},
                    "done-packet": {"workerStatus": "done", "privateNote": PRIVATE_MARKER},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        history.write_text(json.dumps({"attempts": {"failed-packet": 1}}, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_retry_backoff.py"),
                "--state-file",
                str(state),
                "--history-json",
                str(history),
                "--out",
                str(out),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(len(payload["retryCandidates"]) == 1, "retry_candidate_count_mismatch=true")
        assert_true(payload["retryCandidates"][0]["nextAction"] == "retry_after_backoff", "retry_action_mismatch=true")

    print("pnh_unattended_retry_backoff_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

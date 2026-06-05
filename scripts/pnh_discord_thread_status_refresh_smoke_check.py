#!/usr/bin/env python3
"""Smoke check for Discord thread status refresh fixture path."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-discord-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        state = temp_path / "state.json"
        fixture = temp_path / "fixture.json"
        out = temp_path / "out.json"
        state.write_text(
            json.dumps(
                {
                    "capture-discord-refresh-smoke-001": {
                        "discordThreadId": "1512295718054793419",
                        "privateNote": PRIVATE_MARKER,
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        fixture.write_text(
            json.dumps({"payload": {"messages": [{"id": "1", "content": PRIVATE_MARKER}, {"id": "2"}]}}),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_discord_thread_status_refresh.py"),
                "--state-file",
                str(state),
                "--fixture-json",
                str(fixture),
                "--out",
                str(out),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"discord_thread_status_refresh_failed={result.stderr.strip()}")
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["discordThreadStatusRefresh"] is True, "refresh_flag_missing=true")
        assert_true(payload["recordsRefreshed"] == 1, "refresh_count_mismatch=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")
        assert_true(payload["messageContentStored"] is False, "message_content_stored=true")

    print("pnh_discord_thread_status_refresh_smoke_check_pass=true")
    print("private_values_printed=false")
    print("external_writes_performed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

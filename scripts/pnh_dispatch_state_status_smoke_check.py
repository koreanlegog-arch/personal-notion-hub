#!/usr/bin/env python3
"""Smoke check for redacted PNH dispatch state status."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-state-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        state_path = Path(temp_dir) / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "capture-state-smoke-001": {
                        "githubIssueNumber": 7,
                        "githubIssueUrl": "https://github.com/example/private/issues/7",
                        "discordThreadId": "1234567890",
                        "updatedAt": "2026-06-05T00:00:00+00:00",
                        "privateNote": PRIVATE_MARKER,
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_state_status.py"),
                "--state-file",
                str(state_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"state_status_failed={result.stderr.strip()}")
        assert_true(PRIVATE_MARKER not in result.stdout, "private_marker_leaked=true")
        payload = json.loads(result.stdout)
        assert_true(payload["dispatchStateStatus"] is True, "status_flag_missing=true")
        assert_true(payload["totalRecords"] == 1, "record_count_mismatch=true")
        assert_true(payload["githubLinked"] == 1, "github_link_count_mismatch=true")
        assert_true(payload["discordLinked"] == 1, "discord_link_count_mismatch=true")
        assert_true(payload["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true("githubIssueUrl" not in payload["records"][0], "url_included_without_flag=true")

    print("pnh_dispatch_state_status_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

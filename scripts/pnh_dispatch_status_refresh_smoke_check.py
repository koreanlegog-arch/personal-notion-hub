#!/usr/bin/env python3
"""Smoke check for PNH dispatch status refresh."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-refresh-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        state = temp_path / "state.json"
        out = temp_path / "refresh.json"
        fixture = temp_path / "issue.json"
        state.write_text(
            json.dumps(
                {
                    "capture-refresh-smoke-001": {
                        "githubIssueNumber": 11,
                        "githubIssueUrl": "https://github.com/example/private-ledger/issues/11",
                        "discordThreadId": "1234567890",
                        "workerStatus": "done",
                        "workerEvidenceRef": "ops/runs/example/worker.json",
                        "privateNote": PRIVATE_MARKER,
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        fixture.write_text(
            json.dumps(
                {
                    "number": 11,
                    "state": "open",
                    "updated_at": "2026-06-05T00:00:00Z",
                    "closed_at": None,
                    "labels": [{"name": "pnh"}, {"name": "dispatch:worker-done"}],
                    "body": PRIVATE_MARKER,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_status_refresh.py"),
                "--state-file",
                str(state),
                "--fixture-issue-json",
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
        assert_true(result.returncode == 0, f"status_refresh_failed={result.stderr.strip()}")
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["dispatchStatusRefresh"] is True, "refresh_flag_missing=true")
        assert_true(payload["fixtureUsed"] is True, "fixture_flag_missing=true")
        assert_true(payload["recordsRefreshed"] == 1, "refresh_count_mismatch=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")
        refreshed_state = json.loads(state.read_text(encoding="utf-8"))
        record = refreshed_state["capture-refresh-smoke-001"]
        assert_true(record["githubIssueState"] == "open", "github_issue_state_not_saved=true")
        assert_true("dispatch:worker-done" in record["githubIssueLabels"], "github_issue_labels_not_saved=true")
        assert_true("githubStatusCheckedAt" in record, "github_status_checked_at_missing=true")

    print("pnh_dispatch_status_refresh_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

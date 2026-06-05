#!/usr/bin/env python3
"""Smoke check for the guarded PNH single command packet wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import insert_capture  # noqa: E402


PRIVATE_TITLE = "synthetic-single-packet-private-title"
PRIVATE_BODY = "synthetic-single-packet-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "private" / "pnh_private_inbox.sqlite"
        state_path = temp_path / "state.json"
        history_path = temp_path / "history.json"
        run_dir = temp_path / "run"
        inserted = insert_capture(
            db_path,
            {
                "source": "mobile_web",
                "kind": "project_brief",
                "title": PRIVATE_TITLE,
                "body": PRIVATE_BODY,
                "sensitivity": "highly_sensitive",
                "payloadType": "pnh_mobile_command_packet",
                "commandType": "project_brief",
                "dispatchState": "not_dispatched",
            },
            allow_external=True,
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_single_command_packet.py"),
                "--db",
                str(db_path),
                "--state-file",
                str(state_path),
                "--history-json",
                str(history_path),
                "--run-dir",
                str(run_dir),
                "--repo",
                "example/private-ledger",
                "--discord-target",
                "channel:123",
                "--allow-plaintext",
                "--allow-external-db",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_true(result.returncode == 0, f"single_packet_dry_run_failed={result.stderr.strip()}")
        payload = json.loads(result.stdout)
        assert_true(payload["pnhSingleCommandPacket"] is True, "single_packet_flag_missing=true")
        assert_true(payload["mode"] == "dry-run", "dry_run_mode_missing=true")
        assert_true(payload["queuedCount"] == 1, "queued_count_unexpected=true")
        assert_true(payload["externalWritesPerformed"] is False, "dry_run_performed_external_write=true")
        assert_true(payload["workerRunPerformed"] is False, "dry_run_performed_worker_run=true")
        assert_true(payload["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(payload["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
        combined = "\n".join(
            [
                result.stdout,
                (run_dir / "queue_plan.json").read_text(encoding="utf-8"),
                (run_dir / "dispatch_pilot" / "pilot_result.json").read_text(encoding="utf-8"),
                (run_dir / "single_command_packet_summary.json").read_text(encoding="utf-8"),
                (run_dir / "evidence_log.md").read_text(encoding="utf-8"),
            ]
        )
        assert_true(inserted["id"] in combined, "selected_capture_missing=true")
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")

    print("pnh_single_command_packet_smoke_check_pass=true")
    print("external_writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

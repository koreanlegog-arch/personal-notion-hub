#!/usr/bin/env python3
"""Smoke check for guarded browser-triggered single command packet runs."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import insert_capture  # noqa: E402
from companion.single_command_packet_runner import (  # noqa: E402
    SingleCommandPacketRunError,
    run_single_command_packet_from_browser,
)


PRIVATE_TITLE = "synthetic-browser-run-private-title"
PRIVATE_BODY = "synthetic-browser-run-private-body"


def main() -> int:
    try:
        run_single_command_packet_from_browser(mode="apply")
    except SingleCommandPacketRunError as exc:
        assert_true(exc.code == "browser_apply_not_enabled", "apply_gate_not_enforced=true")
    else:
        raise SystemExit("apply_gate_missing=true")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "private" / "pnh_private_inbox.sqlite"
        state_path = temp_path / "state.json"
        history_path = temp_path / "history.json"
        run_dir = temp_path / "browser-run"
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
        result = run_single_command_packet_from_browser(
            mode="dry-run",
            timeout=30,
            extra_args=[
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
        )
        combined = json.dumps(result, ensure_ascii=False, sort_keys=True)
        combined += "\n" + (run_dir / "single_command_packet_summary.json").read_text(encoding="utf-8")
        assert_true(result["ok"] is True, "browser_dry_run_failed=true")
        assert_true(result["mode"] == "dry-run", "browser_dry_run_mode_mismatch=true")
        assert_true(result["externalWritesPerformed"] is False, "browser_dry_run_external_write=true")
        assert_true(result["workerRunPerformed"] is False, "browser_dry_run_worker_run=true")
        assert_true(result["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(result["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
        assert_true(inserted["id"] in combined, "selected_capture_missing=true")
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")

    print("pnh_single_command_packet_browser_run_smoke_check_pass=true")
    print("browser_apply_gate_enforced=true")
    print("external_writes_performed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

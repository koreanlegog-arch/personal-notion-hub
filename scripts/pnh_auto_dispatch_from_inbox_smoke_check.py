#!/usr/bin/env python3
"""Smoke check for PNH auto-dispatch from local private inbox."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import insert_capture  # noqa: E402


PRIVATE_TITLE = "synthetic-auto-dispatch-private-title"
PRIVATE_BODY = "synthetic-auto-dispatch-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "private" / "pnh_private_inbox.sqlite"
        state_path = temp_path / "state.json"
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
        dry_run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_auto_dispatch_from_inbox.py"),
                "--db",
                str(db_path),
                "--capture-id",
                inserted["id"],
                "--state-file",
                str(state_path),
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
        assert_true(dry_run.returncode == 0, f"auto_dispatch_dry_run_failed={dry_run.stderr.strip()}")
        combined = "\n".join(
            [
                dry_run.stdout,
                (run_dir / "dispatch_candidate.json").read_text(encoding="utf-8"),
                (run_dir / "dispatch_plan.json").read_text(encoding="utf-8"),
                (run_dir / "auto_dispatch_summary.json").read_text(encoding="utf-8"),
            ]
        )
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")
        summary = json.loads((run_dir / "auto_dispatch_summary.json").read_text(encoding="utf-8"))
        assert_true(summary["pnhAutoDispatchFromInbox"] is True, "auto_dispatch_flag_missing=true")
        assert_true(summary["mode"] == "dry-run", "dry_run_mode_missing=true")
        assert_true(summary["writesPerformed"] is False, "dry_run_performed_write=true")
        assert_true(summary["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(summary["liveApplyGate"]["requiredForApply"] is True, "live_apply_gate_missing=true")

        state_path.write_text(
            json.dumps(
                {
                    inserted["id"]: {
                        "taskStatus": "worker_done",
                        "workerStatus": "done",
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        already_dispatched = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_auto_dispatch_from_inbox.py"),
                "--db",
                str(db_path),
                "--capture-id",
                inserted["id"],
                "--state-file",
                str(state_path),
                "--run-dir",
                str(run_dir / "already-dispatched"),
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
        assert_true(already_dispatched.returncode == 2, "already_dispatched_capture_exported=true")
        assert_true("already present in dispatch state" in already_dispatched.stderr, "already_dispatched_message_missing=true")
        state_path.unlink()

        blocked_apply = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_auto_dispatch_from_inbox.py"),
                "--db",
                str(db_path),
                "--capture-id",
                inserted["id"],
                "--state-file",
                str(state_path),
                "--run-dir",
                str(run_dir / "blocked"),
                "--repo",
                "example/private-ledger",
                "--discord-target",
                "channel:123",
                "--allow-plaintext",
                "--allow-external-db",
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_true(blocked_apply.returncode == 2, "apply_without_live_dispatch_gate_allowed=true")
        assert_true("approve-live-dispatch" in blocked_apply.stderr, "live_dispatch_gate_message_missing=true")

    print("pnh_auto_dispatch_from_inbox_smoke_check_pass=true")
    print("writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

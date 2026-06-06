#!/usr/bin/env python3
"""Smoke check for PNH unattended dispatch queue planning."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import insert_capture  # noqa: E402


PRIVATE_TITLE = "synthetic-unattended-queue-private-title"
PRIVATE_BODY = "synthetic-unattended-queue-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "private" / "pnh_private_inbox.sqlite"
        state_path = temp_path / "state.json"
        history_path = temp_path / "history.json"
        out = temp_path / "queue_plan.json"
        inserted = insert_capture(
            db_path,
            {
                "source": "mobile_web",
                "kind": "project_brief",
                "title": PRIVATE_TITLE,
                "body": PRIVATE_BODY,
                "sensitivity": "private",
            },
            allow_external=True,
        )
        state_path.write_text(json.dumps({}, ensure_ascii=False), encoding="utf-8")
        history_path.write_text(json.dumps({"events": []}, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_dispatch_queue_plan.py"),
                "--db",
                str(db_path),
                "--state-file",
                str(state_path),
                "--history-json",
                str(history_path),
                "--out",
                str(out),
                "--allow-plaintext",
                "--allow-external-db",
                "--max-jobs-per-run",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"queue_plan_failed={result.stderr.strip()}")
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["pnhUnattendedDispatchQueuePlan"] is True, "queue_plan_flag_missing=true")
        assert_true(payload["queuedCount"] == 1, "queued_count_mismatch=true")
        assert_true(payload["queued"][0]["captureId"] == inserted["id"], "queued_capture_id_mismatch=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")
        assert_true(payload["queueActivationGateRequired"] is False, "delegated_gate_not_reflected=true")
        assert_true(payload["delegationScope"] == "bounded_pnh_test_implementation_pilot", "delegation_scope_missing=true")

    print("pnh_unattended_dispatch_queue_plan_smoke_check_pass=true")
    print("external_writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

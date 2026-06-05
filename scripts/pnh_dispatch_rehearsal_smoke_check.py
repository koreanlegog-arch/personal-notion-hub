#!/usr/bin/env python3
"""Smoke check for local-only PNH dispatch rehearsal."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import insert_capture  # noqa: E402


PRIVATE_TITLE = "synthetic-rehearsal-private-title"
PRIVATE_BODY = "synthetic-rehearsal-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        db_path = temp_root / "private" / "pnh_private_inbox.sqlite"
        state_path = temp_root / "state.json"
        candidate_out = temp_root / "candidate.json"
        plan_out = temp_root / "plan.json"
        status_out = temp_root / "status.json"
        inserted = insert_capture(
            db_path,
            {
                "source": "mobile_web",
                "kind": "task_request",
                "title": PRIVATE_TITLE,
                "body": PRIVATE_BODY,
                "sensitivity": "highly_sensitive",
            },
            allow_external=True,
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_rehearsal.py"),
                "--db",
                str(db_path),
                "--capture-id",
                inserted["id"],
                "--state-file",
                str(state_path),
                "--candidate-out",
                str(candidate_out),
                "--plan-out",
                str(plan_out),
                "--status-out",
                str(status_out),
                "--allow-plaintext",
                "--allow-external-db",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_true(result.returncode == 0, f"dispatch_rehearsal_failed={result.stderr.strip()}")
        combined = "\n".join(
            [
                result.stdout,
                candidate_out.read_text(encoding="utf-8"),
                plan_out.read_text(encoding="utf-8"),
                status_out.read_text(encoding="utf-8"),
            ]
        )
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")
        payload = json.loads(result.stdout)
        assert_true(payload["pnhDispatchRehearsal"] is True, "rehearsal_flag_missing=true")
        assert_true(payload["writesPerformed"] is False, "rehearsal_performed_write=true")
        assert_true(payload["privateValuesPrinted"] is False, "private_values_printed=true")

    print("pnh_dispatch_rehearsal_smoke_check_pass=true")
    print("writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

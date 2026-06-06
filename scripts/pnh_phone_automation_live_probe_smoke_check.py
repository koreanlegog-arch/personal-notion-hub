#!/usr/bin/env python3
"""Smoke check for phone automation live probe."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.private_store import insert_capture, init_private_store  # noqa: E402


PRIVATE_MARKER = "SMOKE_PRIVATE_PHONE_VALUE_DO_NOT_PRINT"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db_path = temp / "private" / "pnh_private_inbox.sqlite"
        out = temp / "live_probe.json"
        init_private_store(db_path, allow_external=True)
        vault = init_encrypted_vault(db_path, "synthetic-live-probe-passphrase-0001")
        insert_capture(
            db_path,
            {
                "source": "phone_call_log",
                "kind": "call_note",
                "title": f"Synthetic title {PRIVATE_MARKER}",
                "body": f"Synthetic body {PRIVATE_MARKER}",
                "sensitivity": "highly_sensitive",
                "createdAt": "2026-06-06T00:00:00Z",
            },
            allow_external=True,
            vault=vault,
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_phone_automation_live_probe.py"),
                "--db",
                str(db_path),
                "--allow-external-db",
                "--baseline-count",
                "0",
                "--timeout-seconds",
                "1",
                "--poll-seconds",
                "0.25",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        evidence = out.read_text(encoding="utf-8")
        payload = json.loads(evidence)
        combined = result.stdout + result.stderr + evidence
        assert_true(payload["verdict"] == "new_phone_capture_detected", "live_probe_verdict_wrong=true")
        assert_true(payload["latestPhoneCapture"]["title"] == "[encrypted]", "encrypted_title_not_redacted=true")
        assert_true(payload["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")

    print("pnh_phone_automation_live_probe_smoke_check_pass=true")
    print("private_values_printed=false")
    print("raw_private_body_read=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

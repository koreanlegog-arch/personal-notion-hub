#!/usr/bin/env python3
"""Smoke check for owner phone capture session runner."""

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


PRIVATE_MARKER = "OWNER_PHONE_SESSION_PRIVATE_MARKER"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db_path = temp / "private" / "pnh_private_inbox.sqlite"
        out = temp / "session.json"
        init_private_store(db_path, allow_external=True)
        vault = init_encrypted_vault(db_path, "synthetic-owner-phone-session-passphrase-0001")
        insert_capture(
            db_path,
            {
                "source": "phone_call_log",
                "kind": "call_note",
                "title": f"Synthetic session title {PRIVATE_MARKER}",
                "body": f"Synthetic session body {PRIVATE_MARKER}",
                "sensitivity": "highly_sensitive",
            },
            allow_external=True,
            vault=vault,
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_owner_phone_capture_session.py"),
                "--db",
                str(db_path),
                "--baseline-count",
                "0",
                "--timeout-seconds",
                "1",
                "--poll-seconds",
                "0.25",
                "--allow-external-db",
                "--skip-post-checks",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(out.read_text(encoding="utf-8"))
        combined = result.stdout + result.stderr + out.read_text(encoding="utf-8")
        assert_true(payload["success"] is True, "session_success_false=true")
        assert_true(payload["probe"]["delta"] == 1, "session_delta_wrong=true")
        assert_true(payload["probe"]["latestPhoneCapture"]["title"] == "[encrypted]", "title_not_redacted=true")
        assert_true(payload["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")

    print("pnh_owner_phone_capture_session_smoke_check_pass=true")
    print("private_values_printed=false")
    print("raw_private_body_read=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

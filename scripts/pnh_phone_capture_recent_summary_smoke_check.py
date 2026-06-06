#!/usr/bin/env python3
"""Smoke check for recent phone capture metadata summary."""

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


PRIVATE_MARKER = "PHONE_RECENT_SUMMARY_PRIVATE_MARKER"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db_path = temp / "private" / "pnh_private_inbox.sqlite"
        out = temp / "summary.json"
        init_private_store(db_path, allow_external=True)
        vault = init_encrypted_vault(db_path, "synthetic-phone-recent-summary-passphrase-0001")
        for source, kind in (
            ("phone_contacts", "contact"),
            ("phone_calendar", "calendar"),
            ("phone_call_log", "call_note"),
            ("phone_recording", "voice_note"),
        ):
            insert_capture(
                db_path,
                {
                    "source": source,
                    "kind": kind,
                    "title": f"Synthetic {source} {PRIVATE_MARKER}",
                    "body": f"Synthetic body {PRIVATE_MARKER}",
                    "sensitivity": "highly_sensitive" if source in {"phone_call_log", "phone_recording"} else "private",
                },
                allow_external=True,
                vault=vault,
            )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_phone_capture_recent_summary.py"),
                "--db",
                str(db_path),
                "--allow-external-db",
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
        assert_true(payload["phoneCaptureCount"] == 4, "phone_capture_count_wrong=true")
        assert_true(payload["plaintextPhoneCaptureCount"] == 0, "plaintext_phone_capture_seen=true")
        assert_true(payload["coverageNote"] == "all_supported_phone_sources_seen_in_recent_window", "coverage_wrong=true")
        assert_true(payload["latestPhoneCapture"]["title"] == "[encrypted]", "title_not_redacted=true")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")

    print("pnh_phone_capture_recent_summary_smoke_check_pass=true")
    print("private_values_printed=false")
    print("raw_private_body_read=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

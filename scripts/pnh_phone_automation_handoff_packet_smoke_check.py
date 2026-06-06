#!/usr/bin/env python3
"""Smoke check for owner phone automation handoff packet."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "handoff.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_phone_automation_handoff_packet.py"),
                "--skip-runtime-checks",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(out.read_text(encoding="utf-8"))
        combined = result.stdout + result.stderr + out.read_text(encoding="utf-8")
        assert_true(payload["tokenPlaceholderOnly"] is True, "token_placeholder_flag_missing=true")
        assert_true(payload["exactOwnerNetworkUrlPersisted"] is False, "owner_url_persisted_flag_wrong=true")
        assert_true(payload["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
        assert_true(len(payload["profiles"]) == 4, "profile_count_wrong=true")
        assert_true("Bearer <PNH_PRIVATE_INBOX_TOKEN>" in combined, "placeholder_missing=true")
        assert_true("Bearer test-token" not in combined, "token_like_value_leaked=true")
        assert_true("100.64.0.1" not in combined, "tailnet_ip_leaked=true")

    print("pnh_phone_automation_handoff_packet_smoke_check_pass=true")
    print("private_values_printed=false")
    print("token_value_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

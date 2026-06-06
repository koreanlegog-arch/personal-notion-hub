#!/usr/bin/env python3
"""Smoke check for phone automation profile templates."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "profile.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_phone_automation_profile_template.py"),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["tokenPlaceholderOnly"] is True, "token_placeholder_flag_missing=true")
        assert_true(len(payload["profiles"]) == 4, "profile_count_mismatch=true")
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true("Bearer <PNH_PRIVATE_INBOX_TOKEN>" in combined, "token_placeholder_missing=true")
        assert_true("Bearer test-token" not in combined, "real_token_like_value_printed=true")

        rejected = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_phone_automation_profile_template.py"),
                "--base-url",
                "http://example.invalid?token=bad",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(rejected.returncode != 0, "secret_like_base_url_accepted=true")

    print("pnh_phone_automation_profile_template_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

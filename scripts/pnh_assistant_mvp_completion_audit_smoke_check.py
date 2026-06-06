#!/usr/bin/env python3
"""Smoke check for PNH assistant MVP completion audit."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "completion_audit.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_assistant_mvp_completion_audit.py"),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert_true(result.returncode in {0, 1}, result.stderr)
        payload = json.loads(out.read_text(encoding="utf-8"))
        combined = result.stdout + result.stderr + out.read_text(encoding="utf-8")
        assert_true(payload["pnhAssistantMvpCompletionAudit"] is True, "audit_flag_missing=true")
        assert_true(payload["checksTotal"] >= 10, "audit_checks_too_small=true")
        assert_true(payload["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
        assert_true(payload["tokenValuePrinted"] is False, "token_value_printed=true")
        assert_true("Bearer test-token" not in combined, "token_like_value_leaked=true")
        assert_true("100.64.0.1" not in combined, "tailnet_ip_leaked=true")

    print("pnh_assistant_mvp_completion_audit_smoke_check_pass=true")
    print("private_values_printed=false")
    print("raw_private_body_read=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

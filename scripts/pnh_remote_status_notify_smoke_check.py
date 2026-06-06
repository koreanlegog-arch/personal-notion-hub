#!/usr/bin/env python3
"""Smoke check for metadata-only remote owner status notification."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="pnh-remote-status-smoke-"))
    try:
        out_path = temp_root / "remote_status_notify.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_remote_status_notify.py"),
                "--owner-target",
                "user:1234567890",
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        combined = result.stdout + "\n" + result.stderr
        if result.returncode != 0:
            raise AssertionError(combined)
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        if payload.get("privateValuesPrinted") or payload.get("tokenValuePrinted") or payload.get("messageContentStored"):
            raise AssertionError("remote status notification redaction policy failed")
        if payload.get("mode") != "dry-run":
            raise AssertionError("smoke check must not send external notification")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    print("pnh_remote_status_notify_smoke_check_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smoke check for owner-only remote pairing handoff redaction."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_CODE = "synthetic-pairing-code-do-not-leak-123"


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="pnh-remote-pairing-smoke-"))
    try:
        event_path = temp_root / "pairing_handoff.json"
        out_path = temp_root / "pairing_handoff_out.json"
        event_path.write_text(
            json.dumps(
                {
                    "pnhPairingHandoff": True,
                    "status": "issued",
                    "pairingCode": SECRET_CODE,
                    "ttlSeconds": 300,
                    "ownerTargetSet": True,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_remote_pairing_handoff.py"),
                "--event-file",
                str(event_path),
                "--owner-target",
                "user:1234567890",
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        combined = result.stdout + "\n" + result.stderr + "\n" + out_path.read_text(encoding="utf-8")
        if result.returncode != 0:
            raise AssertionError(combined)
        if SECRET_CODE in combined:
            raise AssertionError("pairing code leaked in dry-run output")
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        if payload.get("pairingCodeStoredInEvidence"):
            raise AssertionError("pairing code stored in evidence")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    print("pnh_remote_pairing_handoff_smoke_check_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

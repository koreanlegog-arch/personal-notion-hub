#!/usr/bin/env python3
"""Smoke check for Discord/OpenClaw thread readiness probe."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "probe.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_discord_thread_readiness_probe.py"),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert_true(result.returncode == 0, f"discord_thread_readiness_probe_failed={result.stderr.strip()}")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["discordThreadReadinessProbe"] is True, "probe_flag_missing=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")
        assert_true(payload["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(payload["liveRead"]["performed"] is False, "live_read_unexpected=true")

    print("pnh_discord_thread_readiness_probe_smoke_check_pass=true")
    print("private_values_printed=false")
    print("external_writes_performed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

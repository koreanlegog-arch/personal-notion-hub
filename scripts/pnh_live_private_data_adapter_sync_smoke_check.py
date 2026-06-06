#!/usr/bin/env python3
"""Smoke check for live private data adapter sync framework."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "010-7777-0000"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        fixture = temp / "contacts.json"
        out = temp / "live.json"
        fixture.write_text(f'[{{"name":"Tester","phone":"{PRIVATE_MARKER}"}}]', encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_live_private_data_adapter_sync.py"),
                "--adapter",
                "live-contacts-json-url",
                "--fixture-file",
                str(fixture),
                "--fetch",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        assert_true('"recordsParsed": 1' in combined, "records_not_parsed=true")

    print("pnh_live_private_data_adapter_sync_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

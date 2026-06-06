#!/usr/bin/env python3
"""Smoke check for private data adapter batch planning."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "010-8888-0000"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        input_dir = temp / "imports"
        input_dir.mkdir()
        (input_dir / "contacts.csv").write_text("name,phone\nTester,010-8888-0000\n", encoding="utf-8")
        (input_dir / "calendar.ics").write_text(
            "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Fixture\nDTSTART:20260606T090000\nEND:VEVENT\nEND:VCALENDAR\n",
            encoding="utf-8",
        )
        out = temp / "batch.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_private_data_adapter_batch_plan.py"),
                "--input-dir",
                str(input_dir),
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
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["filesInspected"] == 2, "file_count_mismatch=true")
        assert_true(payload["recordsWritten"] == 0, "dry_run_wrote_records=true")
        assert_true(payload["externalServicesContacted"] is False, "external_service_contacted=true")

    print("pnh_private_data_adapter_batch_plan_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smoke check for local private data adapter import."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PASSPHRASE = "synthetic-adapter-passphrase-0001"
PRIVATE_MARKER = "010-9999-0000"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db = temp / "private" / "inbox.sqlite"
        out = temp / "adapter.json"
        contacts = temp / "contacts.csv"
        call_json = temp / "call-log.json"
        contacts.write_text("name,phone,email\nTester,010-9999-0000,tester@example.invalid\n", encoding="utf-8")
        call_json.write_text(
            json.dumps(
                {
                    "calls": [
                        {
                            "name": "Tester",
                            "phone": PRIVATE_MARKER,
                            "timestamp": "2026-06-06T00:00:00Z",
                            "summary": "synthetic call summary",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PNH_ADAPTER_TEST_PASSPHRASE"] = PASSPHRASE

        dry = run_import(db, "contacts-csv", contacts, out, env)
        assert_true(dry.returncode == 0, dry.stderr)
        assert_true(PRIVATE_MARKER not in dry.stdout + out.read_text(encoding="utf-8"), "private_marker_leaked_dry_run=true")
        plan = json.loads(out.read_text(encoding="utf-8"))
        assert_true(plan["recordsParsed"] == 1 and plan["recordsWritten"] == 0, "dry_run_plan_invalid=true")

        applied = run_import(db, "contacts-csv", contacts, out, env, apply=True)
        assert_true(applied.returncode == 0, applied.stderr)
        combined = applied.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked_apply=true")
        result = json.loads(out.read_text(encoding="utf-8"))
        assert_true(result["recordsWritten"] == 1, "adapter_record_not_written=true")

        json_dry = run_import(db, "call-log-json", call_json, out, env)
        assert_true(json_dry.returncode == 0, json_dry.stderr)
        assert_true(PRIVATE_MARKER not in json_dry.stdout + out.read_text(encoding="utf-8"), "json_private_marker_leaked=true")
        json_plan = json.loads(out.read_text(encoding="utf-8"))
        assert_true(json_plan["adapter"] == "call-log-json", "json_adapter_not_used=true")
        assert_true(json_plan["recordKinds"] == ["call_note"], "json_record_kind_wrong=true")

    print("pnh_private_data_adapter_import_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def run_import(db: Path, adapter: str, input_file: Path, out: Path, env: dict[str, str], *, apply: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_private_data_adapter_import.py"),
        "--adapter",
        adapter,
        "--input",
        str(input_file),
        "--db",
        str(db),
        "--out",
        str(out),
        "--allow-external-db",
        "--vault-passphrase-env",
        "PNH_ADAPTER_TEST_PASSPHRASE",
    ]
    if apply:
        command.extend(["--apply", "--approve-real-data-adapter"])
    return subprocess.run(command, capture_output=True, text=True, timeout=20, check=False, env=env)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

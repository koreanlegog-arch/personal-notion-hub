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
        contacts.write_text("name,phone,email\nTester,010-9999-0000,tester@example.invalid\n", encoding="utf-8")
        env = os.environ.copy()
        env["PNH_ADAPTER_TEST_PASSPHRASE"] = PASSPHRASE

        dry = run_import(db, contacts, out, env)
        assert_true(dry.returncode == 0, dry.stderr)
        assert_true(PRIVATE_MARKER not in dry.stdout + out.read_text(encoding="utf-8"), "private_marker_leaked_dry_run=true")
        plan = json.loads(out.read_text(encoding="utf-8"))
        assert_true(plan["recordsParsed"] == 1 and plan["recordsWritten"] == 0, "dry_run_plan_invalid=true")

        applied = run_import(db, contacts, out, env, apply=True)
        assert_true(applied.returncode == 0, applied.stderr)
        combined = applied.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked_apply=true")
        result = json.loads(out.read_text(encoding="utf-8"))
        assert_true(result["recordsWritten"] == 1, "adapter_record_not_written=true")

    print("pnh_private_data_adapter_import_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def run_import(db: Path, contacts: Path, out: Path, env: dict[str, str], *, apply: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_private_data_adapter_import.py"),
        "--adapter",
        "contacts-csv",
        "--input",
        str(contacts),
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

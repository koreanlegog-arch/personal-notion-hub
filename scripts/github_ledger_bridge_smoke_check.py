#!/usr/bin/env python3
"""Smoke check for GitHub ledger bridge dry-run behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_TITLE = "synthetic-private-github-ledger-title"
PRIVATE_BODY = "synthetic-private-github-ledger-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        packet_path = temp_root / "packet.json"
        out_path = temp_root / "issue.json"
        packet_path.write_text(
            json.dumps(
                {
                    "id": "capture-test-001",
                    "payloadType": "pnh_mobile_command_packet",
                    "commandType": "task_request",
                    "commandStatus": "queued",
                    "dispatchState": "not_dispatched",
                    "priority": "high",
                    "sensitivity": "highly_sensitive",
                    "title": PRIVATE_TITLE,
                    "body": PRIVATE_BODY,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "github_ledger_bridge.py"),
                "--input-json",
                str(packet_path),
                "--repo",
                "example/private-ledger",
                "--out",
                str(out_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"bridge_dry_run_failed={result.stderr.strip()}")
        assert_true(out_path.exists(), "dry_run_output_missing=true")
        combined = result.stdout + out_path.read_text(encoding="utf-8")
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")
        output = json.loads(out_path.read_text(encoding="utf-8"))
        assert_true(output["writesPerformed"] is False, "dry_run_performed_write=true")
        assert_true(output["tokenValuePrinted"] is False, "token_value_printed=true")
        assert_true(output["privateValuesIncluded"] is False, "private_values_included_by_default=true")
        assert_true(output["issue"]["title"].startswith("[PNH] task_request"), "safe_issue_title_missing=true")
        assert_true("Worker dispatch: blocked" in output["issue"]["body"], "dispatch_gate_missing=true")

        apply_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "github_ledger_bridge.py"),
                "--input-json",
                str(packet_path),
                "--repo",
                "example/private-ledger",
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(apply_result.returncode == 2, "apply_without_approval_allowed=true")
        assert_true("approve-external-write" in apply_result.stderr, "apply_gate_message_missing=true")

        sensitive_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "github_ledger_bridge.py"),
                "--input-json",
                str(packet_path),
                "--repo",
                "example/private-ledger",
                "--include-sensitive-fields",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(sensitive_result.returncode == 2, "sensitive_fields_without_approval_allowed=true")
        assert_true("approve-sensitive-github-body" in sensitive_result.stderr, "sensitive_gate_message_missing=true")

    print("github_ledger_bridge_smoke_check_pass=true")
    print("writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

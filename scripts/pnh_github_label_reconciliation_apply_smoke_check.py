#!/usr/bin/env python3
"""Smoke check for GitHub label reconciliation apply script dry-run path."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        plan = temp_path / "plan.json"
        out = temp_path / "out.json"
        plan.write_text(
            json.dumps(
                {
                    "plannedExternalWrites": [
                        {
                            "system": "github",
                            "operation": "replace_dispatch_status_labels",
                            "githubIssueNumber": "2",
                            "addLabels": ["dispatch:worker-done"],
                            "removeLabels": ["dispatch:not-dispatched"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_github_label_reconciliation_apply.py"),
                "--plan-json",
                str(plan),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"github_label_reconciliation_smoke_failed={result.stderr.strip()}")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["githubLabelReconciliation"] is True, "reconciliation_flag_missing=true")
        assert_true(payload["mode"] == "dry-run", "dry_run_missing=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")
        assert_true(payload["plannedActionCount"] == 1, "planned_action_count_mismatch=true")

    print("pnh_github_label_reconciliation_apply_smoke_check_pass=true")
    print("external_writes_performed=false")
    print("token_value_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

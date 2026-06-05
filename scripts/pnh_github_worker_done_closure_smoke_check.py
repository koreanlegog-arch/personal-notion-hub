#!/usr/bin/env python3
"""Smoke check the PNH GitHub worker-done closure planner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    fixture = {
        "records": [
            {
                "packetId": "capture-fixture-closed-ready",
                "taskStatus": "worker_done",
                "evidenceCompleteness": 100,
                "missingEvidence": [],
                "githubIssueNumber": 123,
                "githubIssueState": "open",
                "discordThreadId": "1510000000000000000",
                "workerSessionId": "pnh:capture-fixture-closed-ready:qa",
            },
            {
                "packetId": "capture-fixture-missing-evidence",
                "taskStatus": "worker_done",
                "evidenceCompleteness": 33,
                "missingEvidence": ["github_issue"],
                "githubIssueNumber": 124,
                "githubIssueState": "open",
                "discordThreadId": "",
                "workerSessionId": "pnh:capture-fixture-missing-evidence:qa",
            },
        ]
    }
    with tempfile.TemporaryDirectory(prefix="pnh-worker-done-closure-") as tmp:
        fixture_path = Path(tmp) / "evidence.json"
        out_path = Path(tmp) / "closure.json"
        fixture_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "scripts/pnh_github_worker_done_closure.py",
                "--evidence",
                str(fixture_path),
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
            return result.returncode
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        if payload.get("mode") != "dry-run":
            print("expected dry-run mode", file=sys.stderr)
            return 1
        if payload.get("plannedActionCount") != 1:
            print(f"expected one planned action, got {payload.get('plannedActionCount')}", file=sys.stderr)
            return 1
        action = payload["actions"][0]
        if str(action.get("githubIssueNumber")) != "123":
            print("unexpected issue selected", file=sys.stderr)
            return 1
        if payload.get("externalWritesPerformed"):
            print("dry-run must not perform external writes", file=sys.stderr)
            return 1
        if payload.get("privateValuesPrinted") or payload.get("tokenValuePrinted") or payload.get("rawPrivateBodyRead"):
            print("privacy flags must remain false", file=sys.stderr)
            return 1
    print("pnh_github_worker_done_closure_smoke_check_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

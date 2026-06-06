#!/usr/bin/env python3
"""Run one local PNH scheduler tick."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-SCHEDULER-20260606" / "scheduler_tick.json"


JOBS = {
    "private-status": ["scripts/private_inbox_status.py"],
    "queue-plan": ["scripts/pnh_unattended_dispatch_queue_plan.py"],
    "retry-backoff": ["scripts/pnh_unattended_retry_backoff.py"],
    "dispatch-evidence": ["scripts/pnh_dispatch_evidence_summary.py"],
    "adapter-status": ["scripts/pnh_private_data_adapter_status.py"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one PNH scheduler tick.")
    parser.add_argument("--jobs", default="private-status,queue-plan,retry-backoff,dispatch-evidence,adapter-status")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    selected = [item.strip() for item in args.jobs.split(",") if item.strip()]
    results = []
    for job in selected:
        if job not in JOBS:
            results.append({"job": job, "status": "unknown_job", "returnCode": 2})
            continue
        results.append(run_job(job, JOBS[job]))
    payload = {
        "pnhSchedulerTick": True,
        "generatedAt": utc_now(),
        "jobsRun": len(results),
        "failedJobs": [item for item in results if item["returnCode"] != 0],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "results": results,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**payload, "results": results[:3], "out": safe_path_label(out_path)}, ensure_ascii=False, sort_keys=True))
    return 0 if not payload["failedJobs"] else 2


def run_job(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run([sys.executable, *command], cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
    return {
        "job": name,
        "returnCode": result.returncode,
        "status": "ok" if result.returncode == 0 else "failed",
        "stdoutFirstLine": first_line(result.stdout),
        "stderrFirstLine": first_line(result.stderr),
    }


def first_line(value: str) -> str:
    return value.strip().splitlines()[0][:240] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

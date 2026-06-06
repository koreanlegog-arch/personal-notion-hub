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
    "live-adapter-status": ["scripts/pnh_live_private_data_adapter_batch_sync.py"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one PNH scheduler tick.")
    parser.add_argument("--jobs", default="private-status,queue-plan,retry-backoff,dispatch-evidence,adapter-status,live-adapter-status")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    parser.add_argument("--runtime-dir", default="", help="Optional ignored runtime dir for child job outputs.")
    args = parser.parse_args()

    selected = [item.strip() for item in args.jobs.split(",") if item.strip()]
    runtime_dir = Path(args.runtime_dir) if args.runtime_dir else None
    results = []
    for job in selected:
        if job not in JOBS:
            results.append({"job": job, "status": "unknown_job", "returnCode": 2})
            continue
        results.append(run_job(job, build_job_command(job, JOBS[job], runtime_dir)))
    payload = {
        "pnhSchedulerTick": True,
        "generatedAt": utc_now(),
        "jobsRun": len(results),
        "failedJobs": [item for item in results if item["returnCode"] != 0],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "runtimeDir": safe_path_label(runtime_dir) if runtime_dir else "",
        "results": results,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**payload, "results": results[:3], "out": safe_path_label(out_path)}, ensure_ascii=False, sort_keys=True))
    return 0 if not payload["failedJobs"] else 2


def build_job_command(name: str, command: list[str], runtime_dir: Path | None) -> list[str]:
    if runtime_dir is None:
        return command
    runtime_dir.mkdir(parents=True, exist_ok=True)
    out_map = {
        "queue-plan": "queue_plan.json",
        "retry-backoff": "retry_backoff_plan.json",
        "dispatch-evidence": "dispatch_evidence_summary.json",
        "live-adapter-status": "live_adapter_batch_sync.json",
    }
    if name not in out_map:
        return command
    return [*command, "--out", str(runtime_dir / out_map[name])]


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

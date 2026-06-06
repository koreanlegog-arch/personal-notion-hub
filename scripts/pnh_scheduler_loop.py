#!/usr/bin/env python3
"""Run a bounded local PNH scheduler loop."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = ROOT / "ops" / "runs" / "PNH-SCHEDULER-20260606"
DEFAULT_LOCK = ROOT / "companion" / "private" / "pnh_scheduler.lock"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded PNH scheduler loop.")
    parser.add_argument("--iterations", type=int, default=1, help="Bounded loop iterations.")
    parser.add_argument("--interval-seconds", type=int, default=60, help="Sleep between iterations.")
    parser.add_argument("--jobs", default="private-status,queue-plan,retry-backoff,dispatch-evidence,adapter-status,live-adapter-status")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    parser.add_argument("--lock-file", default=str(DEFAULT_LOCK))
    parser.add_argument("--runtime-dir", default="", help="Optional ignored runtime dir for child job outputs.")
    args = parser.parse_args()

    lock = Path(args.lock_file)
    try:
        acquire_lock(lock)
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        events = []
        iterations = min(max(int(args.iterations), 1), 24)
        interval = min(max(int(args.interval_seconds), 1), 3600)
        for index in range(iterations):
            tick_out = run_dir / f"scheduler_tick_{index + 1}.json"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "pnh_scheduler_tick.py"),
                "--jobs",
                args.jobs,
                "--out",
                str(tick_out),
            ]
            if args.runtime_dir:
                command.extend(["--runtime-dir", str(Path(args.runtime_dir) / f"iteration_{index + 1}")])
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
            events.append({"iteration": index + 1, "returnCode": result.returncode, "out": safe_path_label(tick_out)})
            if index < iterations - 1:
                time.sleep(interval)
        summary = {
            "pnhSchedulerLoop": True,
            "generatedAt": utc_now(),
            "iterations": iterations,
            "intervalSeconds": interval,
            "externalWritesPerformed": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "events": events,
        }
        out_path = run_dir / "scheduler_loop.json"
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finally:
        release_lock(lock)
    print(json.dumps({**summary, "out": safe_path_label(out_path)}, ensure_ascii=False, sort_keys=True))
    return 0


def acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "createdAt": utc_now()}, sort_keys=True) + "\n")


def release_lock(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

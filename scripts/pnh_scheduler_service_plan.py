#!/usr/bin/env python3
"""Plan PNH user-systemd scheduler service files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_NAME = "pnh-scheduler.service"
TIMER_NAME = "pnh-scheduler.timer"
DEFAULT_RUNTIME_OUT = ROOT / "companion" / "private" / "scheduler" / "scheduler_tick.json"
DEFAULT_RUNTIME_DIR = ROOT / "companion" / "private" / "scheduler" / "jobs"
RUNTIME_SCRIPT = ROOT / "scripts" / "pnh_scheduler_runtime_tick.sh"


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan PNH scheduler user systemd service.")
    parser.add_argument("--interval-minutes", type=int, default=10, help="Timer interval minutes.")
    parser.add_argument("--runtime-out", default=str(DEFAULT_RUNTIME_OUT), help="Ignored runtime output path.")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR), help="Ignored runtime dir for child job outputs.")
    args = parser.parse_args()

    interval = min(max(int(args.interval_minutes), 1), 1440)
    service_text = build_service(Path(args.runtime_out), Path(args.runtime_dir))
    timer_text = build_timer(interval)
    payload = {
        "pnhSchedulerServicePlan": True,
        "serviceName": SERVICE_NAME,
        "timerName": TIMER_NAME,
        "intervalMinutes": interval,
        "workingDirectory": str(ROOT),
        "runtimeOut": safe_path_label(Path(args.runtime_out)),
        "runtimeDir": safe_path_label(Path(args.runtime_dir)),
        "runtimeScript": safe_path_label(RUNTIME_SCRIPT),
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "serviceText": service_text,
        "timerText": timer_text,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_service(runtime_out: Path, runtime_dir: Path) -> str:
    return "\n".join(
        [
            "[Unit]",
            "Description=Personal Notion Hub bounded scheduler tick",
            "Documentation=file:%s" % (ROOT / "docs" / "PNH_UNATTENDED_DISPATCH_RUNBOOK.md"),
            "",
            "[Service]",
            "Type=oneshot",
            f"WorkingDirectory={ROOT}",
            f"Environment=PNH_SCHEDULER_RUNTIME_OUT={runtime_out}",
            f"Environment=PNH_SCHEDULER_RUNTIME_DIR={runtime_dir}",
            f"ExecStart=/bin/bash {RUNTIME_SCRIPT}",
            "PrivateTmp=true",
            "NoNewPrivileges=true",
            "",
        ]
    )


def build_timer(interval_minutes: int) -> str:
    return "\n".join(
        [
            "[Unit]",
            "Description=Run Personal Notion Hub bounded scheduler periodically",
            "",
            "[Timer]",
            "OnBootSec=2min",
            f"OnUnitActiveSec={interval_minutes}min",
            "AccuracySec=30s",
            "Persistent=false",
            f"Unit={SERVICE_NAME}",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )

def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())

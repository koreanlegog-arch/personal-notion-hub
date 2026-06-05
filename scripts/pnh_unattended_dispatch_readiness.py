#!/usr/bin/env python3
"""Assess PNH unattended dispatch readiness without enabling automation."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_PLAN = ROOT / "ops" / "runs" / "PNH-UNATTENDED-DISPATCH-READINESS-20260605" / "queue_plan.json"
DEFAULT_RECONCILIATION = ROOT / "ops" / "runs" / "PNH-EXTERNAL-RECONCILIATION-PLAN-20260605" / "external_reconciliation_plan.json"
DEFAULT_DISCORD_REFRESH = ROOT / "ops" / "runs" / "PNH-DISCORD-THREAD-STATUS-REFRESH-20260605" / "discord_thread_status_refresh.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-UNATTENDED-DISPATCH-READINESS-20260605" / "readiness.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess PNH unattended dispatch readiness.")
    parser.add_argument("--queue-plan", default=str(DEFAULT_QUEUE_PLAN), help="Queue plan JSON.")
    parser.add_argument("--reconciliation-json", default=str(DEFAULT_RECONCILIATION), help="External reconciliation plan JSON.")
    parser.add_argument("--discord-refresh-json", default=str(DEFAULT_DISCORD_REFRESH), help="Discord status refresh JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    args = parser.parse_args()

    queue_plan = load_json(Path(args.queue_plan))
    reconciliation = load_json(Path(args.reconciliation_json))
    discord_refresh = load_json(Path(args.discord_refresh_json))
    result = build_readiness(queue_plan, reconciliation, discord_refresh)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def build_readiness(queue_plan: dict[str, Any], reconciliation: dict[str, Any], discord_refresh: dict[str, Any]) -> dict[str, Any]:
    checks = [
        check("queue_plan_available", bool(queue_plan.get("pnhUnattendedDispatchQueuePlan")), "queue dry-run output exists"),
        check("queue_is_dry_run", queue_plan.get("mode") == "dry-run", "queue planner did not enable dispatch"),
        check("no_pending_external_reconciliation", reconciliation.get("plannedExternalWriteCount", 0) == 0, "external reconciliation still has pending writes"),
        check("discord_refresh_available", bool(discord_refresh.get("discordThreadStatusRefresh")), "Discord metadata refresh evidence exists"),
        check("discord_refresh_does_not_store_content", discord_refresh.get("messageContentStored") is False, "Discord refresh must not store content"),
        check("gh_available", bool(shutil.which("gh")), "GitHub CLI is available"),
        check("openclaw_available", bool(shutil.which("openclaw")), "OpenClaw CLI is available"),
    ]
    failed = [item for item in checks if not item["pass"]]
    return {
        "pnhUnattendedDispatchReadiness": True,
        "generatedAt": utc_now(),
        "verdict": "ready_for_approval_gated_pilot" if not failed else "not_ready",
        "checks": checks,
        "failedChecks": failed,
        "activationGate": {
            "required": True,
            "name": "APPROVE_PNH_UNATTENDED_DISPATCH_PILOT",
            "reason": "pilot activation would allow queued mobile captures to create external GitHub/Discord/OpenClaw records without per-item operator confirmation.",
        },
        "pilotLimits": {
            "maxJobsPerRun": queue_plan.get("policy", {}).get("maxJobsPerRun", 1),
            "maxExternalWritesPerHour": queue_plan.get("policy", {}).get("maxExternalWritesPerHour", 3),
            "cooldownMinutes": queue_plan.get("policy", {}).get("cooldownMinutes", 10),
        },
        "rollbackRequired": True,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhUnattendedDispatchReadiness": True,
        "verdict": result["verdict"],
        "out": safe_path_label(out_path),
        "activationGateRequired": result["activationGate"]["required"],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

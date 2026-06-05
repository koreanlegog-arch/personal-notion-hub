#!/usr/bin/env python3
"""Run the local PNH dispatch rehearsal pipeline.

This command performs no external writes. It exports a metadata-only dispatch
candidate, generates a dispatch dry-run plan, and prints redacted local dispatch
state status.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "ops" / "runs" / "PNH-DISPATCH-LOCAL-REHEARSAL-20260605"
DEFAULT_CANDIDATE_OUT = RUN_DIR / "dispatch_candidate.json"
DEFAULT_PLAN_OUT = RUN_DIR / "dispatch_plan.json"
DEFAULT_STATUS_OUT = RUN_DIR / "dispatch_state_status.json"


class RehearsalError(ValueError):
    """Raised when the local rehearsal cannot complete safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local-only PNH dispatch rehearsal.")
    parser.add_argument("--db", default="", help="Private inbox DB path override.")
    parser.add_argument("--capture-id", default="", help="Specific capture id to export.")
    parser.add_argument("--repo", default="koreanlegog-arch/personal-notion-hub", help="GitHub owner/repo for dry-run plan.")
    parser.add_argument("--discord-target", default="channel:1511691320136306718", help="Discord target for dry-run plan.")
    parser.add_argument("--state-file", default="", help="Dispatch state file override.")
    parser.add_argument("--candidate-out", default=str(DEFAULT_CANDIDATE_OUT))
    parser.add_argument("--plan-out", default=str(DEFAULT_PLAN_OUT))
    parser.add_argument("--status-out", default=str(DEFAULT_STATUS_OUT))
    parser.add_argument("--allow-plaintext", action="store_true", help="Allow plaintext inbox rows for fixture compatibility.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow DB outside companion/private for fixture tests.")
    args = parser.parse_args()

    try:
        candidate = run_candidate_export(args)
        plan = run_dispatch_plan(args, args.candidate_out)
        status = run_state_status(args)
        summary = {
            "pnhDispatchRehearsal": True,
            "writesPerformed": False,
            "privateValuesPrinted": False,
            "candidate": {
                "captureId": candidate.get("captureId", ""),
                "commandType": candidate.get("commandType", ""),
                "storageMode": candidate.get("storageMode", ""),
            },
            "plan": {
                "packetId": plan.get("packetId", ""),
                "discordTargetSet": bool(plan.get("discordTargetSet")),
                "githubIssueTitle": plan.get("planned", {}).get("githubIssue", {}).get("title", ""),
            },
            "state": {
                "totalRecords": status.get("totalRecords", 0),
                "githubLinked": status.get("githubLinked", 0),
                "discordLinked": status.get("discordLinked", 0),
            },
            "outputs": {
                "candidate": args.candidate_out,
                "plan": args.plan_out,
                "status": args.status_out,
            },
        }
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    except RehearsalError as exc:
        print(f"pnh_dispatch_rehearsal=false error={exc}", file=sys.stderr)
        return 2


def run_candidate_export(args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_dispatch_candidate_export.py"),
        "--out",
        args.candidate_out,
    ]
    if args.db:
        command.extend(["--db", args.db])
    if args.capture_id:
        command.extend(["--capture-id", args.capture_id])
    if args.allow_plaintext:
        command.append("--allow-plaintext")
    if args.allow_external_db:
        command.append("--allow-external-db")
    run_command(command, "candidate export")
    return load_json(Path(args.candidate_out), "candidate")


def run_dispatch_plan(args: argparse.Namespace, candidate_path: str) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_dispatch_job.py"),
        "--input-json",
        candidate_path,
        "--repo",
        args.repo,
        "--discord-target",
        args.discord_target,
        "--out",
        args.plan_out,
    ]
    if args.state_file:
        command.extend(["--state-file", args.state_file])
    run_command(command, "dispatch plan")
    return load_json(Path(args.plan_out), "dispatch plan")


def run_state_status(args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_dispatch_state_status.py"),
    ]
    if args.state_file:
        command.extend(["--state-file", args.state_file])
    result = run_command(command, "state status")
    status = json.loads(result.stdout)
    Path(args.status_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.status_out).write_text(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return status


def run_command(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RehearsalError(f"{label} failed: {first_line(result.stderr) or first_line(result.stdout)}")
    return result


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RehearsalError(f"{label} JSON could not be read") from exc
    if not isinstance(payload, dict):
        raise RehearsalError(f"{label} JSON must be an object")
    return payload


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


if __name__ == "__main__":
    raise SystemExit(main())

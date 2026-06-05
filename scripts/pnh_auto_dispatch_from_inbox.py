#!/usr/bin/env python3
"""Prepare or apply a PNH dispatch job from the local private inbox.

Dry-run is the default. It exports a metadata-only command packet from the
private inbox, generates a dispatch plan, and writes redacted evidence files.
Apply mode can create GitHub/Discord/OpenClaw records and therefore requires
explicit approval flags.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = ROOT / "ops" / "runs" / "PNH-AUTO-DISPATCH-FROM-INBOX-20260605"
DEFAULT_REPO = "koreanlegog-arch/personal-notion-hub"
DEFAULT_DISCORD_TARGET = "channel:1511691320136306718"


class AutoDispatchError(ValueError):
    """Raised when auto-dispatch cannot safely proceed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PNH auto-dispatch from a stored local command packet.")
    parser.add_argument("--db", default="", help="Private inbox DB path override.")
    parser.add_argument("--capture-id", default="", help="Specific capture id to dispatch.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repo.")
    parser.add_argument("--discord-target", default=DEFAULT_DISCORD_TARGET, help="Discord target, e.g. channel:123.")
    parser.add_argument("--state-file", default="", help="Dispatch state file override.")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR), help="Run evidence directory.")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN", help="GitHub token env var name.")
    parser.add_argument("--openclaw-env", default=str(Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"))
    parser.add_argument("--allow-plaintext", action="store_true", help="Allow plaintext inbox rows for fixture compatibility.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow DB outside companion/private for fixture tests.")
    parser.add_argument("--omit-labels", action="store_true", help="Do not include labels in GitHub issue payload.")
    parser.add_argument("--detect-existing-github", action="store_true", help="Read GitHub Issues and reuse an exact-title match in the dispatch job.")
    parser.add_argument("--apply", action="store_true", help="Create missing external records.")
    parser.add_argument("--approve-live-dispatch", action="store_true", help="Required with --apply.")
    parser.add_argument("--approve-external-write", action="store_true", help="Passed to dispatch job apply mode.")
    parser.add_argument("--approve-discord-dispatch", action="store_true", help="Passed to dispatch job apply mode.")
    args = parser.parse_args()

    try:
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        candidate_out = run_dir / "dispatch_candidate.json"
        plan_out = run_dir / ("dispatch_apply_result.json" if args.apply else "dispatch_plan.json")
        if args.apply and not args.approve_live_dispatch:
            raise AutoDispatchError("--apply requires --approve-live-dispatch")
        candidate_result = run_candidate_export(args, candidate_out)
        dispatch_result = run_dispatch_job(args, candidate_out, plan_out)
        candidate = load_json(candidate_out, "candidate")
        plan = load_json(plan_out, "dispatch result")
        summary = build_summary(args, candidate_result, dispatch_result, candidate, plan, candidate_out, plan_out)
        summary_out = run_dir / "auto_dispatch_summary.json"
        summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({**summary, "candidate": redacted_candidate(summary["candidate"])}, ensure_ascii=False, sort_keys=True))
        return 0
    except AutoDispatchError as exc:
        print(f"pnh_auto_dispatch_from_inbox=false error={exc}", file=sys.stderr)
        return 2


def run_candidate_export(args: argparse.Namespace, out_path: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_dispatch_candidate_export.py"),
        "--out",
        str(out_path),
    ]
    if args.db:
        command.extend(["--db", args.db])
    if args.capture_id:
        command.extend(["--capture-id", args.capture_id])
    if args.state_file:
        command.extend(["--state-file", args.state_file])
    if args.allow_plaintext:
        command.append("--allow-plaintext")
    if args.allow_external_db:
        command.append("--allow-external-db")
    result = run_command(command, "candidate export")
    return parse_json_stdout(result.stdout, "candidate export")


def run_dispatch_job(args: argparse.Namespace, candidate_out: Path, result_out: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_dispatch_job.py"),
        "--input-json",
        str(candidate_out),
        "--repo",
        args.repo,
        "--discord-target",
        args.discord_target,
        "--github-token-env",
        args.github_token_env,
        "--openclaw-env",
        args.openclaw_env,
        "--out",
        str(result_out),
    ]
    if args.state_file:
        command.extend(["--state-file", args.state_file])
    if args.omit_labels:
        command.append("--omit-labels")
    if args.detect_existing_github:
        command.append("--detect-existing-github")
    if args.apply:
        command.append("--apply")
        if args.approve_external_write:
            command.append("--approve-external-write")
        if args.approve_discord_dispatch:
            command.append("--approve-discord-dispatch")
    result = run_command(command, "dispatch job")
    payload = parse_json_stdout(result.stdout, "dispatch job")
    if args.apply:
        result_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def run_command(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise AutoDispatchError(f"{label} failed: {first_line(result.stderr) or first_line(result.stdout)}")
    return result


def build_summary(
    args: argparse.Namespace,
    candidate_result: dict[str, Any],
    dispatch_result: dict[str, Any],
    candidate: dict[str, Any],
    plan: dict[str, Any],
    candidate_out: Path,
    plan_out: Path,
) -> dict[str, Any]:
    return {
        "pnhAutoDispatchFromInbox": True,
        "mode": "apply" if args.apply else "dry-run",
        "writesPerformed": bool(dispatch_result.get("writesPerformed")),
        "externalWritePerformed": bool(args.apply and dispatch_result.get("writesPerformed")),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "liveApplyGate": {
            "requiredForApply": True,
            "reason": "apply mode can create GitHub Issues, Discord threads, GitHub comments, and OpenClaw messages",
            "requiredFlags": [
                "--apply",
                "--approve-live-dispatch",
                "--approve-external-write",
                "--approve-discord-dispatch",
            ],
        },
        "candidate": {
            "captureId": candidate_result.get("captureId") or candidate.get("captureId", ""),
            "commandType": candidate_result.get("commandType") or candidate.get("commandType", ""),
            "storageMode": candidate_result.get("storageMode") or candidate.get("storageMode", ""),
            "encrypted": bool(candidate.get("encrypted")),
        },
        "dispatch": {
            "packetId": dispatch_result.get("packetId") or plan.get("packetId", ""),
            "repo": dispatch_result.get("repo") or plan.get("repo", ""),
            "discordTargetSet": bool(dispatch_result.get("discordTargetSet") or plan.get("discordTargetSet")),
            "existingGitHubIssue": bool(plan.get("idempotency", {}).get("existingGitHubIssue")),
            "existingDiscordThread": bool(plan.get("idempotency", {}).get("existingDiscordThread")),
            "githubIssueSet": bool(dispatch_result.get("githubIssueUrl")),
            "discordThreadSet": bool(dispatch_result.get("discordThreadId")),
        },
        "outputs": {
            "candidate": safe_path_label(candidate_out),
            "dispatchPlan": safe_path_label(plan_out),
        },
    }


def redacted_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "captureId": candidate.get("captureId", ""),
        "commandType": candidate.get("commandType", ""),
        "storageMode": candidate.get("storageMode", ""),
        "encrypted": bool(candidate.get("encrypted")),
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutoDispatchError(f"{label} JSON could not be read") from exc
    if not isinstance(payload, dict):
        raise AutoDispatchError(f"{label} JSON must be an object")
    return payload


def parse_json_stdout(stdout: str, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise AutoDispatchError(f"{label} returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise AutoDispatchError(f"{label} output must be an object")
    return payload


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


if __name__ == "__main__":
    raise SystemExit(main())

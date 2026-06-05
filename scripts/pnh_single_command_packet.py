#!/usr/bin/env python3
"""Run one PNH command packet through the guarded dispatch-to-worker flow.

Dry-run is the default and stops after queue planning plus pilot planning. Apply
mode executes the bounded PNH workflow delegated in project AGENTS.md:
dispatch, metadata-only worker capture, label reconciliation, refresh, and
supervisor summary. Raw private command bodies are never read or printed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_HISTORY = ROOT / "companion" / "private" / "pnh_unattended_dispatch_history.json"
DEFAULT_LOCK = ROOT / "companion" / "private" / "pnh_single_command_packet.lock"
DEFAULT_REPO = "koreanlegog-arch/personal-notion-hub"
DEFAULT_DISCORD_TARGET = "channel:1511691320136306718"
DEFAULT_OPENCLAW_ENV = Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"
SECRET_SCAN_PATTERN = (
    r"OPENCLAW_GATEWAY_TOKEN|DISCORD_BOT_TOKEN|GITHUB_TOKEN=|Bearer [A-Za-z0-9_\-]+|"
    r"gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9]|password\s*[=:]|secret\s*[=:]"
)


class SinglePacketError(ValueError):
    """Raised when the single packet workflow cannot safely continue."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one PNH command packet through dispatch and worker capture.")
    parser.add_argument("--run-id", default="", help="Run id. Default: PNH-COMMAND-PACKET-<utc>.")
    parser.add_argument("--run-dir", default="", help="Run evidence directory. Default: ops/runs/<run-id>.")
    parser.add_argument("--db", default="", help="Private inbox DB override.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--history-json", default=str(DEFAULT_HISTORY), help="Unattended dispatch history JSON.")
    parser.add_argument("--lock-file", default=str(DEFAULT_LOCK), help="Single packet apply lock.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repo.")
    parser.add_argument("--discord-target", default=DEFAULT_DISCORD_TARGET, help="Discord target channel.")
    parser.add_argument("--agent", default="qa", help="OpenClaw worker agent.")
    parser.add_argument("--thinking", default="low", help="OpenClaw thinking level.")
    parser.add_argument("--timeout", type=int, default=300, help="OpenClaw worker timeout seconds.")
    parser.add_argument("--openclaw-env", default=str(DEFAULT_OPENCLAW_ENV), help="OpenClaw env file.")
    parser.add_argument("--max-jobs-per-run", type=int, default=1, help="Queue planner max jobs.")
    parser.add_argument("--max-external-writes-per-hour", type=int, default=3, help="Queue planner hourly write limit.")
    parser.add_argument("--cooldown-minutes", type=int, default=10, help="Queue planner cooldown.")
    parser.add_argument("--allow-plaintext", action="store_true", help="Fixture-only plaintext inbox compatibility.")
    parser.add_argument("--allow-external-db", action="store_true", help="Fixture-only DB outside companion/private.")
    parser.add_argument("--no-detect-existing-github", action="store_true", help="Disable duplicate detection in apply mode.")
    parser.add_argument("--apply", action="store_true", help="Execute bounded external writes and worker capture.")
    args = parser.parse_args()

    lock_path = Path(args.lock_file)
    acquired_lock = False
    commands_run: list[dict[str, Any]] = []
    try:
        run_id, run_dir = resolve_run(args.run_id, args.run_dir)
        paths = make_paths(run_dir)
        for path in paths.values():
            if path.name:
                path.mkdir(parents=True, exist_ok=True)
        if args.apply:
            acquire_lock(lock_path)
            acquired_lock = True

        queue = run_queue_plan(args, paths, commands_run)
        run_readiness(paths, commands_run)
        if not queue.get("queued"):
            result = build_empty_result(args, run_id, run_dir, paths, queue, commands_run)
            write_outputs(run_dir, result, commands_run)
            print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
            return 0

        pilot = run_pilot(args, paths, commands_run)
        packet_id = str(pilot.get("selectedCaptureId") or "").strip()
        if not packet_id:
            result = build_empty_result(args, run_id, run_dir, paths, queue, commands_run)
            result["message"] = "pilot_selected_no_packet"
            write_outputs(run_dir, result, commands_run)
            print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
            return 0

        if not args.apply:
            result = build_dry_run_result(args, run_id, run_dir, paths, queue, pilot, commands_run)
            write_outputs(run_dir, result, commands_run)
            print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
            return 0

        refresh_state(commands_run)
        prompt_path = write_worker_prompt(paths["worker"], Path(args.state_file), packet_id)
        run_worker_capture(args, paths, packet_id, prompt_path, commands_run, apply=False)
        worker = run_worker_capture(args, paths, packet_id, prompt_path, commands_run, apply=True)
        refresh_state(commands_run)
        label_plan = run_label_reconciliation(paths, commands_run)
        final_summary = run_final_summary(paths, commands_run)
        result = build_apply_result(
            args,
            run_id,
            run_dir,
            paths,
            queue,
            pilot,
            worker,
            label_plan,
            final_summary,
            commands_run,
        )
        write_outputs(run_dir, result, commands_run)
        print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, SinglePacketError) as exc:
        print(f"pnh_single_command_packet=false error={exc}", file=sys.stderr)
        return 2
    finally:
        if acquired_lock:
            release_lock(lock_path)


def resolve_run(run_id_arg: str, run_dir_arg: str) -> tuple[str, Path]:
    run_id = compact(run_id_arg) or f"PNH-COMMAND-PACKET-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = Path(run_dir_arg) if run_dir_arg else ROOT / "ops" / "runs" / run_id
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    return run_id, unique_dir(run_dir)


def unique_dir(base: Path) -> Path:
    if not base.exists():
        return base
    for index in range(2, 100):
        candidate = Path(f"{base}-{index}")
        if not candidate.exists():
            return candidate
    raise SinglePacketError("could not allocate unique run directory")


def make_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "root": run_dir,
        "queue": run_dir,
        "pilot": run_dir / "dispatch_pilot",
        "worker": run_dir / "worker_capture",
        "labels": run_dir / "label_reconciliation",
    }


def run_queue_plan(args: argparse.Namespace, paths: dict[str, Path], commands_run: list[dict[str, Any]]) -> dict[str, Any]:
    out = paths["queue"] / "queue_plan.json"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_unattended_dispatch_queue_plan.py"),
        "--out",
        str(out),
        "--state-file",
        args.state_file,
        "--history-json",
        args.history_json,
        "--max-jobs-per-run",
        str(args.max_jobs_per_run),
        "--max-external-writes-per-hour",
        str(args.max_external_writes_per_hour),
        "--cooldown-minutes",
        str(args.cooldown_minutes),
    ]
    if args.db:
        command.extend(["--db", args.db])
    if args.allow_plaintext:
        command.append("--allow-plaintext")
    if args.allow_external_db:
        command.append("--allow-external-db")
    run_command(command, "queue_plan", commands_run)
    return load_json_object(out, "queue plan")


def run_readiness(paths: dict[str, Path], commands_run: list[dict[str, Any]]) -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_unattended_dispatch_readiness.py"),
        "--queue-plan",
        str(paths["queue"] / "queue_plan.json"),
        "--out",
        str(paths["queue"] / "readiness.json"),
    ]
    run_command(command, "readiness", commands_run)


def run_pilot(args: argparse.Namespace, paths: dict[str, Path], commands_run: list[dict[str, Any]]) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_unattended_dispatch_pilot.py"),
        "--queue-plan",
        str(paths["queue"] / "queue_plan.json"),
        "--run-dir",
        str(paths["pilot"]),
        "--state-file",
        args.state_file,
        "--history-json",
        args.history_json,
        "--repo",
        args.repo,
        "--discord-target",
        args.discord_target,
    ]
    if not args.no_detect_existing_github:
        command.append("--detect-existing-github")
    if args.apply:
        command.extend(["--apply", "--approve-unattended-pilot"])
    run_command(command, "dispatch_pilot", commands_run, timeout=150)
    return load_json_object(paths["pilot"] / "pilot_result.json", "pilot result")


def refresh_state(commands_run: list[dict[str, Any]]) -> None:
    run_command(
        [sys.executable, str(ROOT / "scripts" / "pnh_dispatch_status_refresh.py"), "--github-read", "--apply"],
        "github_status_refresh",
        commands_run,
        timeout=60,
    )
    run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "pnh_discord_thread_status_refresh.py"),
            "--openclaw-read",
            "--approve-discord-read",
            "--apply",
            "--limit",
            "10",
        ],
        "discord_thread_refresh",
        commands_run,
        timeout=90,
    )
    run_command(
        [sys.executable, str(ROOT / "scripts" / "pnh_dispatch_status_refresh.py"), "--github-read", "--apply"],
        "github_status_refresh_after_discord",
        commands_run,
        timeout=60,
    )


def write_worker_prompt(worker_dir: Path, state_path: Path, packet_id: str) -> Path:
    state = load_json_object(state_path, "dispatch state", missing_ok=True)
    record = state.get(packet_id, {})
    if not isinstance(record, dict):
        record = {}
    labels = record.get("githubIssueLabels", [])
    if not isinstance(labels, list):
        labels = []
    prompt = f"""You are the QA worker for Personal_Notion_Hub.

Task:
Review the metadata-only PNH dispatch record for packet {packet_id} and provide a concise QA status for the supervisor.

Important boundaries:
- Do not request or expose raw private command body content.
- Treat the private command body as local-vault only.
- Use only metadata-safe facts from dispatch state.
- Do not deliver a Discord reply; this run is metadata capture only.

Metadata:
- GitHub Issue: {compact(record.get("githubIssueNumber"))}
- Discord thread: {compact(record.get("discordThreadId"))}
- current worker status: {compact(record.get("workerStatus"))}
- current GitHub label state: {", ".join(compact(label) for label in labels if compact(label))}

Expected output:
- session status
- readiness for supervisor review after worker metadata capture
- remaining risks or next action
"""
    worker_dir.mkdir(parents=True, exist_ok=True)
    path = worker_dir / "worker_prompt.txt"
    path.write_text(prompt, encoding="utf-8")
    return path


def run_worker_capture(
    args: argparse.Namespace,
    paths: dict[str, Path],
    packet_id: str,
    prompt_path: Path,
    commands_run: list[dict[str, Any]],
    *,
    apply: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_openclaw_worker_capture.py"),
        "--packet-id",
        packet_id,
        "--agent",
        args.agent,
        "--message-file",
        str(prompt_path),
        "--thinking",
        args.thinking,
        "--timeout",
        str(args.timeout),
        "--openclaw-env",
        args.openclaw_env,
        "--state-file",
        args.state_file,
        "--run-dir",
        str(paths["worker"]),
    ]
    if apply:
        command.extend(["--apply", "--approve-openclaw-agent-run"])
    run_command(command, "worker_capture_apply" if apply else "worker_capture_dry_run", commands_run, timeout=args.timeout + 30)
    return load_json_object(paths["worker"] / "openclaw_worker_capture_metadata.json", "worker capture metadata")


def run_label_reconciliation(paths: dict[str, Path], commands_run: list[dict[str, Any]]) -> dict[str, Any]:
    plan = paths["labels"] / "external_reconciliation_plan.json"
    dry_run = paths["labels"] / "github_label_reconciliation_dry_run.json"
    applied = paths["labels"] / "github_label_reconciliation_apply.json"
    post = paths["labels"] / "post_reconciliation_plan.json"
    run_command(
        [sys.executable, str(ROOT / "scripts" / "pnh_external_reconciliation_plan.py"), "--out", str(plan)],
        "label_plan",
        commands_run,
    )
    run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "pnh_github_label_reconciliation_apply.py"),
            "--plan-json",
            str(plan),
            "--out",
            str(dry_run),
        ],
        "label_apply_dry_run",
        commands_run,
    )
    run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "pnh_github_label_reconciliation_apply.py"),
            "--plan-json",
            str(plan),
            "--out",
            str(applied),
            "--apply",
            "--approve-external-write",
        ],
        "label_apply",
        commands_run,
        timeout=60,
    )
    run_command(
        [sys.executable, str(ROOT / "scripts" / "pnh_dispatch_status_refresh.py"), "--github-read", "--apply"],
        "github_status_refresh_after_label",
        commands_run,
        timeout=60,
    )
    run_command(
        [sys.executable, str(ROOT / "scripts" / "pnh_external_reconciliation_plan.py"), "--out", str(post)],
        "post_label_plan",
        commands_run,
    )
    return load_json_object(post, "post reconciliation plan")


def run_final_summary(paths: dict[str, Path], commands_run: list[dict[str, Any]]) -> dict[str, Any]:
    run_command(
        [sys.executable, str(ROOT / "scripts" / "pnh_dispatch_state_status.py"), "--include-urls"],
        "dispatch_state_status",
        commands_run,
    )
    run_command([sys.executable, str(ROOT / "scripts" / "pnh_dispatch_evidence_summary.py")], "evidence_summary", commands_run)
    run_command([sys.executable, str(ROOT / "scripts" / "pnh_supervisor_review_summary.py")], "supervisor_review", commands_run)
    return {
        "dispatchEvidenceSummary": safe_path_label(ROOT / "ops/runs/PNH-DISPATCH-EVIDENCE-SUMMARY-20260605/dispatch_evidence_summary.json"),
        "supervisorReviewSummary": safe_path_label(ROOT / "ops/runs/PNH-SUPERVISOR-REVIEW-SUMMARY-20260605/supervisor_review_summary.md"),
    }


def run_command(command: list[str], step: str, commands_run: list[dict[str, Any]], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    entry = {
        "step": step,
        "command": redact_command(command),
        "returnCode": result.returncode,
        "stdoutBytes": len(result.stdout.encode("utf-8")),
        "stderrBytes": len(result.stderr.encode("utf-8")),
    }
    commands_run.append(entry)
    if result.returncode != 0:
        raise SinglePacketError(f"{step} failed: {first_line(result.stderr) or first_line(result.stdout)}")
    return result


def build_empty_result(
    args: argparse.Namespace,
    run_id: str,
    run_dir: Path,
    paths: dict[str, Path],
    queue: dict[str, Any],
    commands_run: list[dict[str, Any]],
) -> dict[str, Any]:
    return base_result(args, run_id, run_dir, paths, commands_run) | {
        "message": "queue_empty",
        "selectedCaptureId": "",
        "queuedCount": int(queue.get("queuedCount", 0) or 0),
        "externalWritesPerformed": False,
        "workerRunPerformed": False,
    }


def build_dry_run_result(
    args: argparse.Namespace,
    run_id: str,
    run_dir: Path,
    paths: dict[str, Path],
    queue: dict[str, Any],
    pilot: dict[str, Any],
    commands_run: list[dict[str, Any]],
) -> dict[str, Any]:
    return base_result(args, run_id, run_dir, paths, commands_run) | {
        "selectedCaptureId": compact(pilot.get("selectedCaptureId")),
        "queuedCount": int(queue.get("queuedCount", 0) or 0),
        "wouldApply": bool(pilot.get("wouldApply")),
        "externalWritesPerformed": False,
        "workerRunPerformed": False,
    }


def build_apply_result(
    args: argparse.Namespace,
    run_id: str,
    run_dir: Path,
    paths: dict[str, Path],
    queue: dict[str, Any],
    pilot: dict[str, Any],
    worker: dict[str, Any],
    label_plan: dict[str, Any],
    final_summary: dict[str, Any],
    commands_run: list[dict[str, Any]],
) -> dict[str, Any]:
    return base_result(args, run_id, run_dir, paths, commands_run) | {
        "selectedCaptureId": compact(pilot.get("selectedCaptureId")),
        "queuedCount": int(queue.get("queuedCount", 0) or 0),
        "githubIssueSet": bool(pilot.get("dispatchSummary", {}).get("dispatch", {}).get("githubIssueSet")),
        "discordThreadSet": bool(pilot.get("dispatchSummary", {}).get("dispatch", {}).get("discordThreadSet")),
        "workerRunPerformed": bool(worker.get("externalAgentRunPerformed")),
        "workerSessionId": compact(worker.get("workerSessionId")),
        "workerStatus": compact(worker.get("workerStatus")),
        "pendingExternalWriteCount": len(label_plan.get("plannedExternalWrites", [])),
        "externalWritesPerformed": bool(pilot.get("externalWritesPerformed")) or bool(worker.get("externalAgentRunPerformed")),
        "finalSummary": final_summary,
    }


def base_result(args: argparse.Namespace, run_id: str, run_dir: Path, paths: dict[str, Path], commands_run: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "pnhSingleCommandPacket": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "dry-run",
        "runId": run_id,
        "runDir": safe_path_label(run_dir),
        "paths": {name: safe_path_label(path) for name, path in paths.items()},
        "commandsRun": commands_run,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
        "discordReplyDelivered": False,
    }


def write_outputs(run_dir: Path, result: dict[str, Any], commands_run: list[dict[str, Any]]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "single_command_packet_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence = [
        "# Evidence Log: PNH Single Command Packet",
        "",
        f"Date: {utc_now()}",
        "",
        "## Result",
        "",
        f"- mode: `{result['mode']}`",
        f"- selected capture: `{result.get('selectedCaptureId', '')}`",
        f"- external writes performed: `{str(bool(result.get('externalWritesPerformed'))).lower()}`",
        f"- worker run performed: `{str(bool(result.get('workerRunPerformed'))).lower()}`",
        f"- private values printed: `false`",
        f"- token values printed: `false`",
        f"- raw private body read: `false`",
        f"- Discord reply delivered: `false`",
        "",
        "## Commands Run",
        "",
    ]
    for item in commands_run:
        evidence.append(f"- `{item['step']}` returnCode=`{item['returnCode']}`")
    evidence.extend(
        [
            "",
            "## Safety",
            "",
            "- Worker prompts are generated from dispatch metadata only.",
            "- Subcommand stdout/stderr byte counts are recorded; raw output bodies are not embedded here.",
            "- Secret values and raw private command bodies are not printed or stored in tracked evidence.",
        ]
    )
    (run_dir / "evidence_log.md").write_text("\n".join(evidence) + "\n", encoding="utf-8")


def redact_stdout(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhSingleCommandPacket": True,
        "mode": result["mode"],
        "runDir": result["runDir"],
        "selectedCaptureId": result.get("selectedCaptureId", ""),
        "queuedCount": result.get("queuedCount", 0),
        "externalWritesPerformed": bool(result.get("externalWritesPerformed")),
        "workerRunPerformed": bool(result.get("workerRunPerformed")),
        "pendingExternalWriteCount": result.get("pendingExternalWriteCount", 0),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SinglePacketError("single command packet lock already exists") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "createdAt": utc_now()}, sort_keys=True) + "\n")


def release_lock(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def load_json_object(path: Path, label: str, *, missing_ok: bool = False) -> dict[str, Any]:
    if not path.exists():
        if missing_ok:
            return {}
        raise SinglePacketError(f"{label} is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SinglePacketError(f"{label} JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SinglePacketError(f"{label} JSON must be an object")
    return payload


def redact_command(command: list[str]) -> list[str]:
    redacted = [safe_command_arg(item) for item in command]
    for flag in ("--message", "--message-file"):
        if flag in redacted:
            index = redacted.index(flag) + 1
            if index < len(redacted):
                redacted[index] = "[redacted-message]"
    return redacted


def safe_command_arg(value: str) -> str:
    text = str(value)
    if text == sys.executable:
        return "python3"
    root_text = str(ROOT)
    if text.startswith(root_text + os.sep):
        return text[len(root_text) + 1 :]
    return text


def compact(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

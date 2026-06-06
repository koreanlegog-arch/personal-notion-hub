#!/usr/bin/env python3
"""Finalize worker-done PNH dispatch records without terminal follow-up.

This script is the post-worker completion lane for already captured worker
metadata. It does not read raw private command bodies. Apply mode can close
worker-done GitHub Issues and refresh local metadata through existing guarded
PNH scripts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_REPO = "koreanlegog-arch/personal-notion-hub"
DEFAULT_RUN_DIR = ROOT / "ops" / "runs" / "PNH-WORKER-COMPLETION-AUTO-20260606" / "auto"
MAX_LIMIT = 25


class WorkerCompletionAutoError(ValueError):
    """Raised when worker completion cannot safely continue."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize completed PNH worker dispatch records.")
    parser.add_argument("--packet-id", action="append", default=[], help="Packet id to finalize. Repeatable.")
    parser.add_argument("--issue-number", action="append", default=[], help="GitHub Issue number to finalize. Repeatable.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repo.")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR), help="Evidence output directory.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum ready records to finalize.")
    parser.add_argument("--skip-github-read", action="store_true", help="Skip post-apply GitHub status refresh.")
    parser.add_argument("--apply", action="store_true", help="Close worker-done issues and refresh local state.")
    parser.add_argument("--approve-worker-completion-auto", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    commands_run: list[dict[str, Any]] = []
    try:
        if args.apply and not args.approve_worker_completion_auto:
            raise WorkerCompletionAutoError("--apply requires --approve-worker-completion-auto")
        run_dir = unique_dir(resolve_path(args.run_dir))
        run_dir.mkdir(parents=True, exist_ok=True)
        state_path = resolve_path(args.state_file)
        state = load_state(state_path)
        candidates = select_candidates(
            state,
            packet_ids=args.packet_id,
            issue_numbers=args.issue_number,
            limit=args.limit,
        )
        selected_state_path = run_dir / "selected_dispatch_state.json"
        selected_evidence_path = run_dir / "selected_dispatch_evidence_summary.json"
        selected_state_path.write_text(
            json.dumps(selected_state(candidates), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_evidence_summary.py"),
                "--state-file",
                str(selected_state_path),
                "--out",
                str(selected_evidence_path),
            ],
            "selected_evidence_summary",
            commands_run,
        )
        closure_path = run_dir / "github_worker_done_closure.json"
        closure_command = [
            sys.executable,
            str(ROOT / "scripts" / "pnh_github_worker_done_closure.py"),
            "--evidence",
            str(selected_evidence_path),
            "--repo",
            args.repo,
            "--out",
            str(closure_path),
        ]
        if args.apply:
            closure_command.extend(["--apply", "--approve-external-write"])
        run_command(closure_command, "github_worker_done_closure", commands_run, timeout=90)
        closure = load_json_object(closure_path, "closure output")

        refresh_path = run_dir / "dispatch_status_refresh.json"
        if args.apply and not args.skip_github_read:
            run_command(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "pnh_dispatch_status_refresh.py"),
                    "--state-file",
                    str(state_path),
                    "--repo",
                    args.repo,
                    "--github-read",
                    "--apply",
                    "--out",
                    str(refresh_path),
                    "--limit",
                    str(min(max(int(args.limit), 1), MAX_LIMIT)),
                ],
                "github_status_refresh",
                commands_run,
                timeout=90,
            )

        final_summary_path = run_dir / "final_dispatch_evidence_summary.json"
        run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_evidence_summary.py"),
                "--state-file",
                str(state_path),
                "--out",
                str(final_summary_path),
            ],
            "final_evidence_summary",
            commands_run,
        )

        result = {
            "pnhWorkerCompletionAuto": True,
            "generatedAt": utc_now(),
            "mode": "apply" if args.apply else "dry-run",
            "runDir": safe_path_label(run_dir),
            "stateFile": safe_path_label(state_path),
            "selectedCandidateCount": len(candidates),
            "selectedPacketIds": [item["packetId"] for item in candidates],
            "selectedIssueNumbers": [item["githubIssueNumber"] for item in candidates if item["githubIssueNumber"]],
            "closurePlannedActionCount": int(closure.get("plannedActionCount", 0) or 0),
            "closureAppliedActionCount": int(closure.get("appliedActionCount", 0) or 0),
            "externalWritesPerformed": bool(closure.get("externalWritesPerformed")),
            "githubStatusRefreshPerformed": bool(args.apply and not args.skip_github_read),
            "commandsRun": commands_run,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "rawPrivateBodyRead": False,
        }
        (run_dir / "worker_completion_auto_summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_evidence_log(run_dir, result)
    except (OSError, WorkerCompletionAutoError) as exc:
        print(f"pnh_worker_completion_auto=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
    return 0


def select_candidates(
    state: dict[str, Any],
    *,
    packet_ids: list[str],
    issue_numbers: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    wanted_packets = {compact(item) for item in packet_ids if compact(item)}
    wanted_issues = {compact(item) for item in issue_numbers if compact(item)}
    selected = []
    for packet_id, record in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if len(selected) >= min(max(int(limit), 1), MAX_LIMIT):
            break
        if not isinstance(record, dict):
            continue
        issue_number = compact(record.get("githubIssueNumber"))
        if wanted_packets and str(packet_id) not in wanted_packets:
            continue
        if wanted_issues and issue_number not in wanted_issues:
            continue
        if not wanted_packets and not wanted_issues and not ready_for_completion(record):
            continue
        if (wanted_packets or wanted_issues) and not ready_for_completion(record):
            continue
        selected.append(safe_record(str(packet_id), record))
    return selected


def ready_for_completion(record: dict[str, Any]) -> bool:
    return all(
        [
            compact(record.get("workerStatus")) == "done",
            compact(record.get("workerSessionId")),
            compact(record.get("workerEvidenceRef")),
            compact(record.get("githubIssueNumber")),
            compact(record.get("discordThreadId")),
        ]
    )


def safe_record(packet_id: str, record: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "packetId": packet_id,
        "githubIssueNumber": record.get("githubIssueNumber", ""),
        "githubIssueUrl": compact(record.get("githubIssueUrl")),
        "githubIssueState": compact(record.get("githubIssueState")),
        "githubIssueLabels": list_of_strings(record.get("githubIssueLabels")),
        "discordThreadId": compact(record.get("discordThreadId")),
        "workerSessionId": compact(record.get("workerSessionId")),
        "workerStatus": compact(record.get("workerStatus")),
        "workerEvidenceRef": compact(record.get("workerEvidenceRef")),
        "workerResultRecordedAt": compact(record.get("workerResultRecordedAt")),
        "updatedAt": compact(record.get("updatedAt")),
    }
    semantic = record.get("semanticProgress")
    if isinstance(semantic, dict):
        allowed["semanticProgress"] = {
            "status": compact(semantic.get("status")),
            "stage": compact(semantic.get("stage")),
            "confidence": int(semantic.get("confidence", 0) or 0),
            "evidenceStrength": compact(semantic.get("evidenceStrength")),
            "requiresSupervisorAction": bool(semantic.get("requiresSupervisorAction")),
            "recommendedNextAction": compact(semantic.get("recommendedNextAction")),
            "messageContentStored": False,
            "updatedAt": compact(semantic.get("updatedAt")),
        }
    return allowed


def selected_state(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {item["packetId"]: {key: value for key, value in item.items() if key != "packetId"} for item in candidates}


def run_command(command: list[str], step: str, commands_run: list[dict[str, Any]], *, timeout: int = 30) -> None:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
    commands_run.append(
        {
            "step": step,
            "command": redact_command(command),
            "returnCode": result.returncode,
            "stdoutBytes": len(result.stdout.encode("utf-8")),
            "stderrBytes": len(result.stderr.encode("utf-8")),
            "stdoutFirstLines": safe_lines(result.stdout),
            "stderrFirstLines": safe_lines(result.stderr),
        }
    )
    if result.returncode != 0:
        raise WorkerCompletionAutoError(f"{step} failed: {first_line(result.stderr) or first_line(result.stdout)}")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkerCompletionAutoError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise WorkerCompletionAutoError("dispatch state must be an object")
    return payload


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkerCompletionAutoError(f"{label} JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise WorkerCompletionAutoError(f"{label} must be an object")
    return payload


def write_evidence_log(run_dir: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Evidence Log: PNH Worker Completion Auto",
        "",
        f"Date: {result['generatedAt']}",
        f"Mode: `{result['mode']}`",
        "",
        "## Result",
        "",
        f"- selected candidates: `{result['selectedCandidateCount']}`",
        f"- closure planned actions: `{result['closurePlannedActionCount']}`",
        f"- closure applied actions: `{result['closureAppliedActionCount']}`",
        f"- external writes performed: `{str(result['externalWritesPerformed']).lower()}`",
        f"- private values printed: `false`",
        f"- raw private body read: `false`",
        "",
        "## Commands",
        "",
    ]
    for item in result["commandsRun"]:
        lines.append(f"- `{item['step']}` returnCode=`{item['returnCode']}`")
    (run_dir / "evidence_log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def unique_dir(base: Path) -> Path:
    if not base.exists():
        return base
    for index in range(2, 100):
        candidate = Path(f"{base}-{index}")
        if not candidate.exists():
            return candidate
    raise WorkerCompletionAutoError("could not allocate run directory")


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def redact_command(command: list[str]) -> list[str]:
    redacted = []
    for item in command:
        text = str(item)
        if text == sys.executable:
            redacted.append("python3")
        elif text.startswith(str(ROOT) + "/"):
            redacted.append(text[len(str(ROOT)) + 1 :])
        else:
            redacted.append(text)
    return redacted


def safe_lines(value: str) -> list[str]:
    return [line[:400] for line in value.splitlines()[:5]]


def list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [compact(item) for item in value if compact(item)]


def compact(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def redact_stdout(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhWorkerCompletionAuto": True,
        "mode": result["mode"],
        "runDir": result["runDir"],
        "selectedCandidateCount": result["selectedCandidateCount"],
        "selectedIssueNumbers": result["selectedIssueNumbers"],
        "closurePlannedActionCount": result["closurePlannedActionCount"],
        "closureAppliedActionCount": result["closureAppliedActionCount"],
        "externalWritesPerformed": result["externalWritesPerformed"],
        "githubStatusRefreshPerformed": result["githubStatusRefreshPerformed"],
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

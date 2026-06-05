#!/usr/bin/env python3
"""Dispatch a PNH command packet to ledger and worker-routing targets.

Dry-run is the default. Apply mode requires explicit flags and records local
state so repeated runs do not create duplicate external ledger/thread records.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from github_ledger_bridge import build_issue_payload, load_packet  # noqa: E402


DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_DRY_RUN_OUT = ROOT / "ops" / "runs" / "PNH-IDEMPOTENT-DISPATCH-JOB-20260605" / "dispatch_plan.json"


class DispatchJobError(ValueError):
    """Raised when dispatch job input or approval state is unsafe."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a PNH ledger-to-worker dispatch job.")
    parser.add_argument("--input-json", required=True, help="PNH command packet JSON.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""), help="GitHub owner/repo.")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN", help="GitHub token env var.")
    parser.add_argument("--discord-target", default="", help="Discord target, e.g. channel:123.")
    parser.add_argument("--openclaw-env", default=str(Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state file.")
    parser.add_argument("--out", default=str(DEFAULT_DRY_RUN_OUT), help="Dry-run output path.")
    parser.add_argument("--apply", action="store_true", help="Create missing external records.")
    parser.add_argument("--approve-external-write", action="store_true", help="Required with --apply.")
    parser.add_argument("--approve-discord-dispatch", action="store_true", help="Required with --apply and Discord dispatch.")
    parser.add_argument("--omit-labels", action="store_true", help="Do not include labels in GitHub issue payload.")
    parser.add_argument("--detect-existing-github", action="store_true", help="Read GitHub Issues and reuse an exact-title match before creating a new issue.")
    args = parser.parse_args()

    try:
        packet = load_packet(Path(args.input_json))
        packet_id = packet_identifier(packet)
        state_path = Path(args.state_file)
        state = load_state(state_path)
        existing = state.get(packet_id, {})
        issue = build_issue_payload(
            packet,
            include_sensitive_fields=False,
            approve_sensitive=False,
            omit_labels=args.omit_labels,
        )
        github_detection = detect_existing_github_issue(args.repo, args.github_token_env, issue) if args.detect_existing_github else {"enabled": False}
        effective_existing = dict(existing)
        if github_detection.get("match") and not effective_existing.get("githubIssueUrl"):
            effective_existing.update(
                {
                    "githubIssueNumber": github_detection.get("issueNumber", ""),
                    "githubIssueUrl": github_detection.get("issueUrl", ""),
                }
            )
        result: dict[str, Any] = {
            "generatedAt": utc_now(),
            "mode": "apply" if args.apply else "dry-run",
            "packetId": packet_id,
            "repo": args.repo or "unset",
            "discordTargetSet": bool(args.discord_target),
            "stateFile": str(state_path),
            "writesPerformed": False,
            "tokenValuePrinted": False,
            "privateValuesIncluded": False,
            "idempotency": {
                "existingGitHubIssue": bool(effective_existing.get("githubIssueUrl")),
                "existingDiscordThread": bool(effective_existing.get("discordThreadId")),
                "githubDuplicateDetection": github_detection,
            },
            "planned": {
                "githubIssue": redact_issue(issue),
                "discordThreadName": thread_name(packet_id),
                "discordMessages": dispatch_messages(packet_id, effective_existing.get("githubIssueUrl", "")),
            },
        }
        if args.apply:
            apply_result = apply_dispatch(args, packet_id, issue, state, state_path, github_detection=github_detection)
            result.update(apply_result)
        else:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
        return 0
    except DispatchJobError as exc:
        print(f"pnh_dispatch_job=false error={exc}", file=sys.stderr)
        return 2


def packet_identifier(packet: dict[str, Any]) -> str:
    value = compact(packet.get("captureId") or packet.get("id") or "")
    if not value:
        raise DispatchJobError("packet id or captureId is required")
    return value


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DispatchJobError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise DispatchJobError("dispatch state must be an object")
    return value


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def apply_dispatch(
    args: argparse.Namespace,
    packet_id: str,
    issue: dict[str, Any],
    state: dict[str, Any],
    state_path: Path,
    github_detection: dict[str, Any],
) -> dict[str, Any]:
    if not args.approve_external_write:
        raise DispatchJobError("--apply requires --approve-external-write")
    record = dict(state.get(packet_id, {}))
    writes: list[str] = []
    reused: list[str] = []
    if not record.get("githubIssueUrl"):
        if github_detection.get("match"):
            record.update(
                {
                    "githubIssueNumber": github_detection.get("issueNumber", ""),
                    "githubIssueUrl": github_detection.get("issueUrl", ""),
                }
            )
            reused.append("github_issue")
        else:
            if args.detect_existing_github and github_detection.get("error"):
                raise DispatchJobError(f"github duplicate detection failed: {github_detection.get('error')}")
            created = create_issue(args.repo, args.github_token_env, issue)
            record.update(
                {
                    "githubIssueNumber": created["number"],
                    "githubIssueUrl": created["html_url"],
                }
            )
            writes.append("github_issue")
    if args.discord_target and not record.get("discordThreadId"):
        if not args.approve_discord_dispatch:
            raise DispatchJobError("Discord dispatch requires --approve-discord-dispatch")
        thread_id = create_discord_thread(args.openclaw_env, args.discord_target, packet_id, record.get("githubIssueUrl", ""))
        record["discordThreadId"] = thread_id
        writes.append("discord_thread")
        post_dispatch_messages(args.openclaw_env, thread_id, packet_id, record.get("githubIssueUrl", ""))
        if record.get("githubIssueNumber"):
            comment_issue(
                args.repo,
                args.github_token_env,
                int(record["githubIssueNumber"]),
                f"Discord/OpenClaw dispatch job linked thread `{thread_id}`.\n\nRaw private command body was not posted.",
            )
            writes.append("github_comment")
    record["updatedAt"] = utc_now()
    state[packet_id] = record
    save_state(state_path, state)
    return {
        "writesPerformed": bool(writes),
        "writes": writes,
        "reused": reused,
        "githubIssueUrl": record.get("githubIssueUrl", ""),
        "discordThreadId": record.get("discordThreadId", ""),
    }


def detect_existing_github_issue(repo: str, token_env: str, issue: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "enabled": True,
        "tokenSet": bool(os.environ.get(token_env, "").strip()),
        "match": False,
        "issueNumber": "",
        "issueUrl": "",
        "labelsUsed": issue.get("labels", [])[:5] if isinstance(issue.get("labels"), list) else [],
        "privateValuesIncluded": False,
    }
    if not repo or "/" not in repo:
        result["error"] = "repo_unset"
        return result
    token = os.environ.get(token_env, "").strip()
    if not token:
        return detect_existing_github_issue_with_gh(repo, issue, result)
    title = str(issue.get("title") or "").strip()
    if not title:
        result["error"] = "issue_title_missing"
        return result
    labels = issue.get("labels", []) if isinstance(issue.get("labels"), list) else []
    query = {
        "state": "all",
        "per_page": "30",
    }
    if labels:
        query["labels"] = ",".join(str(label) for label in labels[:5])
    endpoint = f"https://api.github.com/repos/{repo.strip().strip('/')}/issues?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        endpoint,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "pnh-dispatch-job",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        payload = github_request_json(request, "github issue duplicate detection")
    except DispatchJobError as exc:
        result["error"] = str(exc)
        return result
    if not isinstance(payload, list):
        result["error"] = "github_issue_list_unexpected_payload"
        return result
    result["candidatesChecked"] = len(payload)
    for item in payload:
        if not isinstance(item, dict) or "pull_request" in item:
            continue
        if str(item.get("title") or "").strip() == title:
            result.update(
                {
                    "match": True,
                    "issueNumber": item.get("number", ""),
                    "issueUrl": item.get("html_url", ""),
                    "issueState": item.get("state", ""),
                    "issueUpdatedAt": item.get("updated_at", ""),
                }
            )
            break
    return result


def create_issue(repo: str, token_env: str, issue: dict[str, Any]) -> dict[str, Any]:
    if not repo or "/" not in repo:
        raise DispatchJobError("--repo owner/repo is required in apply mode")
    token = os.environ.get(token_env, "").strip()
    if not token:
        return create_issue_with_gh(repo, issue)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo.strip().strip('/')}/issues",
        data=json.dumps(issue, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pnh-dispatch-job",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    return github_json(request, "github issue create")


def comment_issue(repo: str, token_env: str, issue_number: int, body: str) -> None:
    token = os.environ.get(token_env, "").strip()
    if not token:
        comment_issue_with_gh(repo, issue_number, body)
        return
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo.strip().strip('/')}/issues/{issue_number}/comments",
        data=json.dumps({"body": body}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pnh-dispatch-job",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    github_json(request, "github issue comment")


def github_json(request: urllib.request.Request, label: str) -> dict[str, Any]:
    payload = github_request_json(request, label)
    if not isinstance(payload, dict):
        raise DispatchJobError(f"{label} returned unexpected payload")
    return payload


def github_request_json(request: urllib.request.Request, label: str) -> Any:
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise DispatchJobError(f"{label} failed with HTTP {exc.code}") from exc
    return payload


def detect_existing_github_issue_with_gh(repo: str, issue: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if not gh_available():
        result["error"] = "GITHUB_TOKEN_not_set_and_gh_unavailable"
        return result
    title = str(issue.get("title") or "").strip()
    if not title:
        result["error"] = "issue_title_missing"
        return result
    labels = issue.get("labels", []) if isinstance(issue.get("labels"), list) else []
    endpoint = f"repos/{repo.strip().strip('/')}/issues"
    args = ["gh", "api", endpoint, "--method", "GET", "-f", "state=all", "-f", "per_page=30"]
    if labels:
        args.extend(["-f", f"labels={','.join(str(label) for label in labels[:5])}"])
    payload = gh_json(args, "github issue duplicate detection via gh")
    if not isinstance(payload, list):
        result["error"] = "github_issue_list_unexpected_payload"
        return result
    result["tokenSet"] = False
    result["ghAuthUsed"] = True
    result["candidatesChecked"] = len(payload)
    for item in payload:
        if not isinstance(item, dict) or "pull_request" in item:
            continue
        if str(item.get("title") or "").strip() == title:
            result.update(
                {
                    "match": True,
                    "issueNumber": item.get("number", ""),
                    "issueUrl": item.get("html_url", ""),
                    "issueState": item.get("state", ""),
                    "issueUpdatedAt": item.get("updated_at", ""),
                }
            )
            break
    return result


def create_issue_with_gh(repo: str, issue: dict[str, Any]) -> dict[str, Any]:
    if not gh_available():
        raise DispatchJobError("GITHUB_TOKEN is not set and gh auth is unavailable")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
        json.dump(issue, handle, ensure_ascii=False)
        issue_path = handle.name
    try:
        payload = gh_json(["gh", "api", f"repos/{repo.strip().strip('/')}/issues", "-X", "POST", "--input", issue_path], "github issue create via gh")
    finally:
        try:
            os.unlink(issue_path)
        except OSError:
            pass
    if not isinstance(payload, dict):
        raise DispatchJobError("github issue create via gh returned unexpected payload")
    return payload


def comment_issue_with_gh(repo: str, issue_number: int, body: str) -> None:
    if not gh_available():
        raise DispatchJobError("GITHUB_TOKEN is not set and gh auth is unavailable")
    payload = gh_json(
        [
            "gh",
            "api",
            f"repos/{repo.strip().strip('/')}/issues/{issue_number}/comments",
            "-X",
            "POST",
            "-f",
            f"body={body}",
        ],
        "github issue comment via gh",
    )
    if not isinstance(payload, dict):
        raise DispatchJobError("github issue comment via gh returned unexpected payload")


def gh_available() -> bool:
    if not shutil.which("gh"):
        return False
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=15, check=False)
    return result.returncode == 0


def gh_json(command: list[str], label: str) -> Any:
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise DispatchJobError(f"{label} failed: {first_line(result.stderr) or first_line(result.stdout)}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DispatchJobError(f"{label} returned invalid JSON") from exc


def create_discord_thread(openclaw_env: str, target: str, packet_id: str, issue_url: str) -> str:
    result = run_openclaw(
        openclaw_env,
        [
            "openclaw",
            "message",
            "thread",
            "create",
            "--channel",
            "discord",
            "--target",
            target,
            "--thread-name",
            thread_name(packet_id),
            "--message",
            f"PNH dispatch job for packet `{packet_id}`.\nLedger: {issue_url}\nScope: routing only unless a scoped worker task is approved.",
            "--json",
        ],
    )
    payload = parse_json_stdout(result.stdout)
    thread_id = payload.get("payload", {}).get("thread", {}).get("id", "")
    if not thread_id:
        raise DispatchJobError("OpenClaw thread create did not return thread id")
    return thread_id


def post_dispatch_messages(openclaw_env: str, thread_id: str, packet_id: str, issue_url: str) -> None:
    for message in dispatch_messages(packet_id, issue_url):
        run_openclaw(
            openclaw_env,
            ["openclaw", "message", "send", "--channel", "discord", "--target", f"channel:{thread_id}", "--message", message, "--json"],
        )


def run_openclaw(openclaw_env: str, command: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(read_env_file(Path(openclaw_env)))
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False, env=env)
    if result.returncode != 0:
        raise DispatchJobError(f"OpenClaw command failed: {first_line(result.stderr) or first_line(result.stdout)}")
    return result


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise DispatchJobError("OpenClaw env file does not exist")
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def parse_json_stdout(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise DispatchJobError("OpenClaw command returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise DispatchJobError("OpenClaw command returned unexpected JSON")
    return payload


def dispatch_messages(packet_id: str, issue_url: str) -> list[str]:
    issue_line = f"\nLedger: {issue_url}" if issue_url else ""
    return [
        f"`/task create`\nTask ID: `{packet_id}`{issue_line}\nObjective: route PNH command packet through ledger-backed worker control.",
        "`/task assign`\nAssigned: `worker-orchestrator`\nGate: implementation starts only from a scoped task packet.",
        "`/review`\nCheck: private body is not posted; ledger and thread references are present.",
        "`/qa`\nCheck: duplicate dispatch is prevented by local dispatch state.",
        "`/task done`\nResult: dispatch job reached ledger/thread routing stage.",
    ]


def thread_name(packet_id: str) -> str:
    return f"PNH-{packet_id}-dispatch"


def redact_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": issue.get("title", ""),
        "bodyLength": len(issue.get("body", "")),
        "labels": issue.get("labels", []),
    }


def redact_stdout(result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(result)
    safe["stateFile"] = "local-private-state"
    return safe


def compact(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

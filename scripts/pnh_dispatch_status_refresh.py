#!/usr/bin/env python3
"""Refresh redacted external dispatch status into local PNH dispatch state.

Default mode is dry-run and local-state only. GitHub reads require
`--github-read` or a local fixture JSON. Apply mode updates only the ignored
local dispatch state file; it does not write to GitHub, Discord, or OpenClaw.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-DISPATCH-STATUS-REFRESH-20260605" / "dispatch_status_refresh.json"
GITHUB_ISSUE_RE = re.compile(r"github\.com/([^/]+/[^/]+)/issues/([0-9]+)")


class DispatchStatusRefreshError(ValueError):
    """Raised when refresh input or external read state is invalid."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh PNH dispatch status without printing private values.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""), help="GitHub owner/repo fallback.")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN", help="GitHub token env var for read-only issue status checks.")
    parser.add_argument("--github-read", action="store_true", help="Read GitHub issue state for linked records.")
    parser.add_argument("--fixture-issue-json", default="", help="Local fixture issue JSON for smoke tests; no network.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Refresh result output JSON.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum records to inspect.")
    parser.add_argument("--apply", action="store_true", help="Update local dispatch state with refreshed metadata.")
    args = parser.parse_args()

    try:
        state_path = Path(args.state_file)
        state = load_state(state_path)
        fixture = load_fixture(Path(args.fixture_issue_json)) if args.fixture_issue_json else None
        result = build_refresh(args, state, fixture=fixture)
        if args.apply:
            apply_refresh(state_path, state, result)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, DispatchStatusRefreshError) as exc:
        print(f"pnh_dispatch_status_refresh=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DispatchStatusRefreshError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DispatchStatusRefreshError("dispatch state must be an object")
    return payload


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DispatchStatusRefreshError(f"fixture JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DispatchStatusRefreshError("fixture issue JSON must be an object")
    return payload


def build_refresh(args: argparse.Namespace, state: dict[str, Any], *, fixture: dict[str, Any] | None) -> dict[str, Any]:
    records = []
    inspected = 0
    for packet_id, record in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if inspected >= min(max(int(args.limit), 1), 200):
            break
        if not isinstance(record, dict):
            continue
        inspected += 1
        records.append(refresh_record(str(packet_id), record, args, fixture=fixture))
    return {
        "dispatchStatusRefresh": True,
        "mode": "apply" if args.apply else "dry-run",
        "githubReadRequested": bool(args.github_read),
        "fixtureUsed": fixture is not None,
        "recordsInspected": inspected,
        "recordsWithGitHub": sum(1 for item in records if item["githubIssueSet"]),
        "recordsRefreshed": sum(1 for item in records if item["githubStatusRefreshed"]),
        "recordsNeedingFollowUp": sum(1 for item in records if item["needsFollowUp"]),
        "writesPerformed": bool(args.apply),
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "records": records,
    }


def refresh_record(packet_id: str, record: dict[str, Any], args: argparse.Namespace, *, fixture: dict[str, Any] | None) -> dict[str, Any]:
    issue_ref = issue_reference(record, args.repo)
    refreshed: dict[str, Any] = {}
    error = ""
    if fixture is not None and issue_ref["issueNumber"]:
        refreshed = redacted_issue_status(fixture)
    elif args.github_read and issue_ref["issueNumber"]:
        try:
            refreshed = read_github_issue(issue_ref["repo"], issue_ref["issueNumber"], args.github_token_env)
        except DispatchStatusRefreshError as exc:
            error = str(exc)
    elif args.github_read and not issue_ref["issueNumber"]:
        error = "github_issue_reference_missing"
    needs_follow_up = bool(error or (record.get("workerStatus") == "done" and not record.get("workerEvidenceRef")))
    if refreshed.get("state") == "closed" and record.get("workerStatus") != "done":
        needs_follow_up = True
    return {
        "packetId": packet_id,
        "githubIssueSet": bool(issue_ref["issueNumber"]),
        "githubIssueNumber": issue_ref["issueNumber"],
        "githubStatusRefreshed": bool(refreshed),
        "githubIssueState": refreshed.get("state", ""),
        "githubIssueLabels": refreshed.get("labels", []),
        "githubIssueUpdatedAt": refreshed.get("updatedAt", ""),
        "githubIssueClosedAt": refreshed.get("closedAt", ""),
        "discordThreadSet": bool(record.get("discordThreadId")),
        "workerStatus": record.get("workerStatus", ""),
        "needsFollowUp": needs_follow_up,
        "error": error,
    }


def issue_reference(record: dict[str, Any], fallback_repo: str) -> dict[str, str]:
    number = str(record.get("githubIssueNumber") or "").strip()
    repo = fallback_repo.strip().strip("/")
    url = str(record.get("githubIssueUrl") or "")
    match = GITHUB_ISSUE_RE.search(url)
    if match:
        repo = match.group(1)
        number = match.group(2)
    return {"repo": repo, "issueNumber": number}


def read_github_issue(repo: str, issue_number: str, token_env: str) -> dict[str, Any]:
    if not repo or "/" not in repo:
        raise DispatchStatusRefreshError("repo_unset")
    token = os.environ.get(token_env, "").strip()
    if not token:
        return read_github_issue_with_gh(repo, issue_number)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "pnh-dispatch-status-refresh",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise DispatchStatusRefreshError(f"github issue read failed with HTTP {exc.code}") from exc
    if not isinstance(payload, dict):
        raise DispatchStatusRefreshError("github issue read returned unexpected payload")
    return redacted_issue_status(payload)


def read_github_issue_with_gh(repo: str, issue_number: str) -> dict[str, Any]:
    if not shutil.which("gh"):
        raise DispatchStatusRefreshError("GITHUB_TOKEN_not_set_and_gh_unavailable")
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{issue_number}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise DispatchStatusRefreshError(f"github issue read via gh failed: {first_line(result.stderr)}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DispatchStatusRefreshError("github issue read via gh returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise DispatchStatusRefreshError("github issue read via gh returned unexpected payload")
    return redacted_issue_status(payload)


def redacted_issue_status(issue: dict[str, Any]) -> dict[str, Any]:
    labels = issue.get("labels", [])
    label_names = []
    if isinstance(labels, list):
        for label in labels[:12]:
            if isinstance(label, dict):
                name = str(label.get("name") or "").strip()
            else:
                name = str(label or "").strip()
            if name:
                label_names.append(name)
    return {
        "state": str(issue.get("state") or ""),
        "labels": label_names,
        "updatedAt": str(issue.get("updated_at") or issue.get("updatedAt") or ""),
        "closedAt": str(issue.get("closed_at") or issue.get("closedAt") or ""),
    }


def apply_refresh(state_path: Path, state: dict[str, Any], result: dict[str, Any]) -> None:
    checked_at = utc_now()
    for item in result["records"]:
        record = state.get(item["packetId"])
        if not isinstance(record, dict):
            continue
        if item["githubStatusRefreshed"]:
            record.update(
                {
                    "githubIssueState": item["githubIssueState"],
                    "githubIssueLabels": item["githubIssueLabels"],
                    "githubIssueUpdatedAt": item["githubIssueUpdatedAt"],
                    "githubIssueClosedAt": item["githubIssueClosedAt"],
                    "githubStatusCheckedAt": checked_at,
                    "updatedAt": checked_at,
                }
            )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(state_path, 0o600)
    except OSError:
        pass


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "dispatchStatusRefresh": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "githubReadRequested": result["githubReadRequested"],
        "fixtureUsed": result["fixtureUsed"],
        "recordsInspected": result["recordsInspected"],
        "recordsWithGitHub": result["recordsWithGitHub"],
        "recordsRefreshed": result["recordsRefreshed"],
        "recordsNeedingFollowUp": result["recordsNeedingFollowUp"],
        "writesPerformed": result["writesPerformed"],
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


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


if __name__ == "__main__":
    raise SystemExit(main())

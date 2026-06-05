#!/usr/bin/env python3
"""Close GitHub Issues for completed PNH worker-done dispatch records.

The script reads redacted local dispatch evidence and mutates only GitHub Issue
state for records that are already worker_done with complete evidence. It never
reads private command bodies or token values.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "ops" / "runs" / "PNH-DISPATCH-EVIDENCE-SUMMARY-20260605" / "dispatch_evidence_summary.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-GITHUB-WORKER-DONE-CLOSURE-20260605" / "github_worker_done_closure.json"
DEFAULT_REPO = "koreanlegog-arch/personal-notion-hub"
MAX_APPLY = 10


class GitHubWorkerDoneClosureError(ValueError):
    """Raised when closure cannot be performed safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Close PNH worker-done GitHub Issues safely.")
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--limit", type=int, default=MAX_APPLY)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--approve-external-write", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_evidence(Path(args.evidence))
        result = build_or_apply(args, evidence)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, GitHubWorkerDoneClosureError) as exc:
        print(f"pnh_github_worker_done_closure=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def load_evidence(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GitHubWorkerDoneClosureError(f"evidence JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise GitHubWorkerDoneClosureError("evidence JSON must contain records list")
    return payload


def build_or_apply(args: argparse.Namespace, evidence: dict[str, Any]) -> dict[str, Any]:
    actions = planned_actions(evidence, limit=args.limit)
    result: dict[str, Any] = {
        "githubWorkerDoneClosure": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "dry-run",
        "repo": args.repo,
        "plannedActionCount": len(actions),
        "actions": actions,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
        "approvalSource": "project AGENTS.md bounded GitHub Issue update delegation" if args.apply else "",
    }
    if not args.apply:
        return result
    if not args.approve_external_write:
        raise GitHubWorkerDoneClosureError("--apply requires --approve-external-write")
    ensure_gh_ready()
    applied = []
    for action in actions:
        applied.append(close_issue(args.repo, action))
    result.update(
        {
            "externalWritesPerformed": bool(applied),
            "appliedActionCount": len(applied),
            "applied": applied,
        }
    )
    return result


def planned_actions(evidence: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    actions = []
    for record in evidence.get("records", []):
        if len(actions) >= min(max(int(limit), 1), MAX_APPLY):
            break
        if not isinstance(record, dict):
            continue
        issue_number = compact(record.get("githubIssueNumber"))
        if not issue_number:
            continue
        if compact(record.get("githubIssueState")).lower() == "closed":
            continue
        if record.get("taskStatus") != "worker_done":
            continue
        if int(record.get("evidenceCompleteness") or 0) < 100:
            continue
        missing = record.get("missingEvidence", [])
        if isinstance(missing, list) and missing:
            continue
        if not compact(record.get("discordThreadId")) or not compact(record.get("workerSessionId")):
            continue
        actions.append(
            {
                "operation": "close_worker_done_issue",
                "githubIssueNumber": issue_number,
                "packetId": compact(record.get("packetId")),
                "taskStatus": "worker_done",
                "evidenceCompleteness": 100,
                "discordThreadId": compact(record.get("discordThreadId")),
                "workerSessionId": compact(record.get("workerSessionId")),
            }
        )
    return actions


def ensure_gh_ready() -> None:
    if not shutil.which("gh"):
        raise GitHubWorkerDoneClosureError("gh CLI is not installed")
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=15, check=False)
    if result.returncode != 0:
        raise GitHubWorkerDoneClosureError("gh auth is not available")


def close_issue(repo: str, action: dict[str, Any]) -> dict[str, Any]:
    issue_number = action["githubIssueNumber"]
    before = read_issue_state(repo, issue_number)
    if before.get("state", "").lower() != "closed":
        body = (
            "PNH dispatch record reached worker_done with 100% redacted evidence completeness. "
            f"Worker session: {action['workerSessionId']}. Discord thread: {action['discordThreadId']}."
        )
        result = subprocess.run(
            ["gh", "issue", "close", issue_number, "--repo", repo, "--comment", body],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise GitHubWorkerDoneClosureError(f"gh issue close failed: {first_line(result.stderr)}")
    after = read_issue_state(repo, issue_number)
    return {
        "githubIssueNumber": issue_number,
        "beforeState": before.get("state", ""),
        "afterState": after.get("state", ""),
        "commentBodyPrivate": False,
        "contentPrinted": False,
    }


def read_issue_state(repo: str, issue_number: str) -> dict[str, str]:
    result = subprocess.run(
        ["gh", "issue", "view", issue_number, "--repo", repo, "--json", "state,closedAt,updatedAt"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise GitHubWorkerDoneClosureError(f"gh issue view failed: {first_line(result.stderr)}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GitHubWorkerDoneClosureError("gh issue view returned invalid JSON") from exc
    return {
        "state": compact(payload.get("state")),
        "closedAt": compact(payload.get("closedAt")),
        "updatedAt": compact(payload.get("updatedAt")),
    }


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "githubWorkerDoneClosure": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "plannedActionCount": result["plannedActionCount"],
        "appliedActionCount": result.get("appliedActionCount", 0),
        "externalWritesPerformed": result["externalWritesPerformed"],
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def compact(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def first_line(value: str) -> str:
    return compact(value).splitlines()[0] if value else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Apply approved GitHub dispatch label reconciliation.

Dry-run is the default. Apply mode requires explicit approval flags because it
mutates GitHub Issue labels. Authentication is delegated to GitHub CLI so token
values are never read or printed by this script.
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
DEFAULT_PLAN = ROOT / "ops" / "runs" / "PNH-EXTERNAL-RECONCILIATION-PLAN-20260605" / "external_reconciliation_plan.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-GITHUB-LABEL-RECONCILIATION-APPLY-20260605" / "github_label_reconciliation_apply.json"
DEFAULT_REPO = "koreanlegog-arch/personal-notion-hub"


class GitHubLabelReconciliationError(ValueError):
    """Raised when label reconciliation cannot be safely applied."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply approved PNH GitHub Issue label reconciliation.")
    parser.add_argument("--plan-json", default=str(DEFAULT_PLAN), help="External reconciliation plan JSON.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repo.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    parser.add_argument("--apply", action="store_true", help="Apply GitHub label changes.")
    parser.add_argument("--approve-external-write", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    try:
        plan = load_plan(Path(args.plan_json))
        result = build_or_apply(args, plan)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, GitHubLabelReconciliationError) as exc:
        print(f"pnh_github_label_reconciliation_apply=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def load_plan(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GitHubLabelReconciliationError(f"plan JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise GitHubLabelReconciliationError("plan JSON must be an object")
    return payload


def build_or_apply(args: argparse.Namespace, plan: dict[str, Any]) -> dict[str, Any]:
    actions = planned_github_label_actions(plan)
    result: dict[str, Any] = {
        "githubLabelReconciliation": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "dry-run",
        "repo": args.repo,
        "plannedActionCount": len(actions),
        "actions": actions,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }
    if not args.apply:
        return result
    if not args.approve_external_write:
        raise GitHubLabelReconciliationError("--apply requires --approve-external-write")
    ensure_gh_ready()
    applied = []
    for action in actions:
        applied.append(apply_action(args.repo, action))
    result.update(
        {
            "externalWritesPerformed": bool(applied),
            "appliedActionCount": len(applied),
            "applied": applied,
        }
    )
    return result


def planned_github_label_actions(plan: dict[str, Any]) -> list[dict[str, Any]]:
    actions = []
    for item in plan.get("plannedExternalWrites", []):
        if not isinstance(item, dict):
            continue
        if item.get("system") != "github" or item.get("operation") != "replace_dispatch_status_labels":
            continue
        issue_number = compact(item.get("githubIssueNumber"))
        if not issue_number:
            continue
        actions.append(
            {
                "operation": "replace_dispatch_status_labels",
                "githubIssueNumber": issue_number,
                "addLabels": list_of_strings(item.get("addLabels")),
                "removeLabels": list_of_strings(item.get("removeLabels")),
            }
        )
    return actions


def ensure_gh_ready() -> None:
    if not shutil.which("gh"):
        raise GitHubLabelReconciliationError("gh CLI is not installed")
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=15, check=False)
    if result.returncode != 0:
        raise GitHubLabelReconciliationError("gh auth is not available")


def apply_action(repo: str, action: dict[str, Any]) -> dict[str, Any]:
    issue_number = action["githubIssueNumber"]
    before = read_issue_labels(repo, issue_number)
    created_labels = ensure_labels(repo, action["addLabels"])
    command = ["gh", "issue", "edit", issue_number, "--repo", repo]
    for label in action["addLabels"]:
        command.extend(["--add-label", label])
    for label in action["removeLabels"]:
        command.extend(["--remove-label", label])
    if len(command) > 5:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            raise GitHubLabelReconciliationError(f"gh issue edit failed: {first_line(result.stderr)}")
    after = read_issue_labels(repo, issue_number)
    return {
        "githubIssueNumber": issue_number,
        "beforeLabels": before,
        "afterLabels": after,
        "addLabels": action["addLabels"],
        "removeLabels": action["removeLabels"],
        "createdLabels": created_labels,
        "contentPrinted": False,
    }


def ensure_labels(repo: str, labels: list[str]) -> list[str]:
    existing = set(read_repo_labels(repo))
    created = []
    for label in labels:
        if label in existing:
            continue
        result = subprocess.run(
            [
                "gh",
                "label",
                "create",
                label,
                "--repo",
                repo,
                "--color",
                label_color(label),
                "--description",
                label_description(label),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0 and "already exists" not in result.stderr.lower():
            raise GitHubLabelReconciliationError(f"gh label create failed: {first_line(result.stderr)}")
        created.append(label)
        existing.add(label)
    return created


def read_repo_labels(repo: str) -> list[str]:
    result = subprocess.run(
        ["gh", "label", "list", "--repo", repo, "--limit", "200", "--json", "name", "--jq", "[.[].name]"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise GitHubLabelReconciliationError(f"gh label list failed: {first_line(result.stderr)}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GitHubLabelReconciliationError("gh label list returned invalid JSON") from exc
    return list_of_strings(payload)


def label_color(label: str) -> str:
    if label == "dispatch:worker-done":
        return "0E8A16"
    if label == "dispatch:dispatched-to-worker":
        return "1D76DB"
    if label.startswith("dispatch:"):
        return "1D76DB"
    return "C5DEF5"


def label_description(label: str) -> str:
    if label == "dispatch:worker-done":
        return "PNH dispatch worker session finished and evidence was captured"
    if label == "dispatch:dispatched-to-worker":
        return "PNH dispatch created the worker thread and is awaiting worker evidence"
    if label.startswith("dispatch:"):
        return "PNH dispatch status"
    return "PNH automation label"


def read_issue_labels(repo: str, issue_number: str) -> list[str]:
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{issue_number}",
            "--jq",
            "[.labels[].name]",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise GitHubLabelReconciliationError(f"gh issue label read failed: {first_line(result.stderr)}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GitHubLabelReconciliationError("gh issue label read returned invalid JSON") from exc
    return list_of_strings(payload)


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "githubLabelReconciliation": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "plannedActionCount": result["plannedActionCount"],
        "appliedActionCount": result.get("appliedActionCount", 0),
        "externalWritesPerformed": result["externalWritesPerformed"],
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

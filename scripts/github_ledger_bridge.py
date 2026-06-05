#!/usr/bin/env python3
"""Create a privacy-preserving GitHub Issue draft from a PNH command packet.

Dry-run is the default. Live GitHub mutation requires explicit apply flags and
a runtime token. Secret values are never printed by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-GITHUB-LEDGER-BRIDGE-20260605" / "github_issue_dry_run.json"
SAFE_LABEL_RE = re.compile(r"[^a-zA-Z0-9_.:/ -]+")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or apply a GitHub Issue ledger entry from a PNH command packet.")
    parser.add_argument("--input-json", required=True, help="Path to a command packet JSON file.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""), help="Target owner/repo.")
    parser.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable that holds the GitHub token.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Dry-run output path.")
    parser.add_argument("--apply", action="store_true", help="Create the GitHub Issue. Requires approval flag and token.")
    parser.add_argument("--approve-external-write", action="store_true", help="Required with --apply.")
    parser.add_argument("--include-sensitive-fields", action="store_true", help="Include raw title/body. Requires approval flag.")
    parser.add_argument("--approve-sensitive-github-body", action="store_true", help="Required with --include-sensitive-fields.")
    args = parser.parse_args()

    try:
        packet = load_packet(Path(args.input_json))
        issue = build_issue_payload(
            packet,
            include_sensitive_fields=args.include_sensitive_fields,
            approve_sensitive=args.approve_sensitive_github_body,
        )
        result = {
            "generatedAt": utc_now(),
            "mode": "apply" if args.apply else "dry-run",
            "repo": redact_repo(args.repo),
            "writesPerformed": False,
            "tokenValuePrinted": False,
            "privateValuesIncluded": bool(args.include_sensitive_fields),
            "issue": issue,
            "approvalGate": approval_gate(args),
        }
        if args.apply:
            apply_result = create_issue(args.repo, args.token_env, issue, args.approve_external_write)
            result.update(apply_result)
        else:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(redact_result_for_stdout(result), ensure_ascii=False, sort_keys=True))
        return 0
    except LedgerBridgeError as exc:
        print(f"github_ledger_bridge=false error={exc}", file=sys.stderr)
        return 2


class LedgerBridgeError(ValueError):
    """Raised when bridge input or approval state is unsafe."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_packet(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise LedgerBridgeError("input JSON does not exist")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerBridgeError(f"input JSON is invalid: {exc.msg}") from exc
    if not isinstance(packet, dict):
        raise LedgerBridgeError("input JSON must be an object")
    return packet


def build_issue_payload(packet: dict[str, Any], *, include_sensitive_fields: bool, approve_sensitive: bool) -> dict[str, Any]:
    if include_sensitive_fields and not approve_sensitive:
        raise LedgerBridgeError("--include-sensitive-fields requires --approve-sensitive-github-body")
    command_type = compact(packet.get("commandType") or packet.get("kind") or "project_brief")
    capture_id = compact(packet.get("captureId") or packet.get("id") or "local-packet")
    priority = compact(packet.get("priority") or "normal")
    sensitivity = compact(packet.get("sensitivity") or "private")
    dispatch_state = compact(packet.get("dispatchState") or "not_dispatched")
    command_status = compact(packet.get("commandStatus") or "queued")
    title = build_title(packet, command_type, capture_id, include_sensitive_fields=include_sensitive_fields)
    body = build_body(
        packet,
        command_type=command_type,
        capture_id=capture_id,
        priority=priority,
        sensitivity=sensitivity,
        dispatch_state=dispatch_state,
        command_status=command_status,
        include_sensitive_fields=include_sensitive_fields,
    )
    labels = sanitize_labels(
        [
            "pnh",
            "mobile-command",
            f"command:{command_type}",
            f"priority:{priority}",
            "dispatch:not-dispatched",
        ]
    )
    return {"title": title, "body": body, "labels": labels}


def build_title(packet: dict[str, Any], command_type: str, capture_id: str, *, include_sensitive_fields: bool) -> str:
    if include_sensitive_fields:
        raw_title = compact(packet.get("title") or packet.get("summary") or "")
        if raw_title:
            return truncate(f"[PNH] {raw_title}", 120)
    return truncate(f"[PNH] {command_type} command packet ({capture_id})", 120)


def build_body(
    packet: dict[str, Any],
    *,
    command_type: str,
    capture_id: str,
    priority: str,
    sensitivity: str,
    dispatch_state: str,
    command_status: str,
    include_sensitive_fields: bool,
) -> str:
    lines = [
        "## PNH Mobile Command Packet",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Command type | `{escape_table(command_type)}` |",
        f"| Local capture ref | `{escape_table(capture_id)}` |",
        f"| Priority | `{escape_table(priority)}` |",
        f"| Sensitivity | `{escape_table(sensitivity)}` |",
        f"| Command status | `{escape_table(command_status)}` |",
        f"| Dispatch state | `{escape_table(dispatch_state)}` |",
        "",
        "## Privacy Boundary",
        "",
        "The private command body remains in the local encrypted vault by default.",
        "Do not request raw private contents in GitHub unless the supervisor approves repository privacy and data exposure.",
        "",
    ]
    if include_sensitive_fields:
        lines.extend(
            [
                "## Approved Sensitive Fields",
                "",
                f"Title: {compact(packet.get('title') or '')}",
                "",
                "Body:",
                "",
                compact(packet.get("body") or packet.get("objective") or ""),
                "",
            ]
        )
    lines.extend(
        [
            "## Acceptance Criteria",
            "",
            "- [ ] Scope is clarified.",
            "- [ ] Implementation packet is created or linked.",
            "- [ ] QA/security evidence is attached before completion.",
            "- [ ] Supervisor approval is recorded before external dispatch or delivery.",
            "",
            "## Next Routing",
            "",
            "- Ledger status: queued",
            "- Worker dispatch: blocked until Discord/OpenClaw gate is approved",
        ]
    )
    return "\n".join(lines)


def create_issue(repo: str, token_env: str, issue: dict[str, Any], approve_external_write: bool) -> dict[str, Any]:
    if not approve_external_write:
        raise LedgerBridgeError("--apply requires --approve-external-write")
    if not repo or "/" not in repo:
        raise LedgerBridgeError("--repo owner/repo is required for apply mode")
    token = os.environ.get(token_env, "").strip()
    if not token:
        raise LedgerBridgeError(f"{token_env} is not set")
    owner_repo = repo.strip().strip("/")
    endpoint = f"https://api.github.com/repos/{owner_repo}/issues"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(issue, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pnh-github-ledger-bridge",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LedgerBridgeError(f"github issue create failed with HTTP {exc.code}") from exc
    return {
        "writesPerformed": True,
        "githubIssueNumber": payload.get("number"),
        "githubIssueUrl": payload.get("html_url"),
    }


def approval_gate(args: argparse.Namespace) -> str:
    if args.apply:
        return "external_github_issue_write_requested"
    return "dry_run_only_no_external_write"


def compact(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def sanitize_labels(labels: list[str]) -> list[str]:
    clean: list[str] = []
    for label in labels:
        compacted = compact(label).lower()
        sanitized = SAFE_LABEL_RE.sub("", compacted).strip()
        if sanitized and sanitized not in clean:
            clean.append(sanitized[:50])
    return clean


def escape_table(value: str) -> str:
    return value.replace("|", "/")


def redact_repo(repo: str) -> str:
    return repo if repo else "unset"


def redact_result_for_stdout(result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(result)
    if "issue" in safe:
        issue = dict(safe["issue"])
        issue["bodyLength"] = len(issue.get("body", ""))
        issue.pop("body", None)
        safe["issue"] = issue
    return safe


if __name__ == "__main__":
    raise SystemExit(main())

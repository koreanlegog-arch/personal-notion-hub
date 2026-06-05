#!/usr/bin/env python3
"""Create a redacted supervisor review summary from PNH dispatch evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "ops" / "runs" / "PNH-DISPATCH-EVIDENCE-SUMMARY-20260605" / "dispatch_evidence_summary.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-SUPERVISOR-REVIEW-SUMMARY-20260605" / "supervisor_review_summary.md"


class SupervisorReviewSummaryError(ValueError):
    """Raised when supervisor review summary input is invalid."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a redacted PNH supervisor review summary.")
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE), help="Dispatch evidence summary JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Markdown output path.")
    parser.add_argument("--packet-id", default="", help="Optional packet id filter.")
    args = parser.parse_args()

    try:
        evidence_path = Path(args.evidence)
        evidence = load_evidence(evidence_path)
        summary = build_markdown(evidence, packet_id=args.packet_id)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(summary, encoding="utf-8")
    except (OSError, SupervisorReviewSummaryError) as exc:
        print(f"pnh_supervisor_review_summary=false error={exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "pnhSupervisorReviewSummary": True,
                "out": safe_path_label(out_path),
                "privateValuesPrinted": False,
                "recordsIncluded": count_included(summary),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def load_evidence(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SupervisorReviewSummaryError(f"evidence JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SupervisorReviewSummaryError("evidence must be an object")
    records = payload.get("records")
    if not isinstance(records, list):
        raise SupervisorReviewSummaryError("evidence.records must be a list")
    return payload


def build_markdown(evidence: dict[str, Any], *, packet_id: str) -> str:
    records = [item for item in evidence.get("records", []) if isinstance(item, dict)]
    if packet_id:
        records = [item for item in records if str(item.get("packetId", "")) == packet_id]
    lines = [
        "# PNH Supervisor Review Summary",
        "",
        "This summary is generated from redacted dispatch evidence. It must not include private command bodies, tokens, or secret values.",
        "",
        "## Rollup",
        "",
        f"- total records: {evidence.get('totalRecords', 0)}",
        f"- included records: {len(records)}",
        f"- worker done records: {count_by_status(records, 'worker_done')}",
        f"- complete review ready: {count_complete_review_ready(records)}",
        f"- needs follow-up: {count_needs_follow_up(records)}",
        f"- blocked or failed: {count_blocked_or_failed(records)}",
        f"- average evidence completeness: {evidence.get('averageEvidenceCompleteness', 0)}%",
        f"- private values printed: {str(bool(evidence.get('privateValuesPrinted'))).lower()}",
        "",
        "## Records",
        "",
    ]
    if not records:
        lines.extend(["No matching dispatch records were included.", ""])
    for record in records:
        lines.extend(record_lines(record))
    lines.extend(
        [
            "## Supervisor Checks",
            "",
            "- Confirm the linked GitHub Issue and Discord thread show only metadata-safe content.",
            "- Confirm `worker_done` records with 100% evidence completeness are ready for product-level review.",
            "- Keep raw private command body inside the local encrypted vault unless a separate exposure gate is approved.",
            "",
        ]
    )
    return "\n".join(lines)


def record_lines(record: dict[str, Any]) -> list[str]:
    missing = record.get("missingEvidence", [])
    missing_label = ", ".join(str(item) for item in missing) if isinstance(missing, list) and missing else "none"
    return [
        f"### {record.get('packetId', 'unknown-packet')}",
        "",
        f"- task status: {record.get('taskStatus', 'unknown')}",
        f"- evidence completeness: {record.get('evidenceCompleteness', 0)}%",
        f"- missing evidence: {missing_label}",
        f"- next action: {record.get('nextAction', 'review_dispatch_evidence')}",
        f"- GitHub issue: #{record.get('githubIssueNumber') or '-'}",
        f"- GitHub issue state: {record.get('githubIssueState') or '-'}",
        f"- GitHub status checked at: {record.get('githubStatusCheckedAt') or '-'}",
        f"- Discord thread id: {record.get('discordThreadId') or '-'}",
        f"- worker session id: {record.get('workerSessionId') or '-'}",
        f"- worker status: {record.get('workerStatus') or '-'}",
        f"- updated at: {record.get('updatedAt') or '-'}",
        "",
    ]


def count_by_status(records: list[dict[str, Any]], status: str) -> int:
    return sum(1 for item in records if item.get("taskStatus") == status)


def count_blocked_or_failed(records: list[dict[str, Any]]) -> int:
    return sum(1 for item in records if item.get("taskStatus") in {"worker_blocked", "worker_failed"})


def count_complete_review_ready(records: list[dict[str, Any]]) -> int:
    return sum(1 for item in records if is_complete_review_ready(item))


def count_needs_follow_up(records: list[dict[str, Any]]) -> int:
    return sum(1 for item in records if not is_complete_review_ready(item))


def is_complete_review_ready(record: dict[str, Any]) -> bool:
    missing = record.get("missingEvidence", [])
    return record.get("taskStatus") == "worker_done" and int(record.get("evidenceCompleteness") or 0) >= 100 and not missing


def count_included(summary: str) -> int:
    return summary.count("\n### ")


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Parse redacted worker progress text into dispatch-state metadata.

This script accepts operator-provided or fixture text. It stores only semantic
status, stage, confidence, and redacted signal labels. It does not store message
content and does not contact Discord/OpenClaw.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-WORKER-PROGRESS-PARSE-20260606" / "worker_progress_parse.json"

SECRET_PATTERN = re.compile(
    r"(Bearer\s+[A-Za-z0-9_.-]{8,}|gh[opsu]_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{8,}|"
    r"password\s*[=:]|secret\s*[=:]|token\s*[=:])",
    re.IGNORECASE,
)

STATUS_RULES = [
    ("failed", "failed", "failed", re.compile(r"\b(failed|error|exception|traceback|cannot complete)\b", re.I)),
    ("blocked", "blocked", "blocked", re.compile(r"\b(blocked|waiting|cannot proceed|needs approval|needs input)\b", re.I)),
    ("done", "done", "done", re.compile(r"\b(done|completed|complete|worker_done|finished)\b", re.I)),
    ("qa", "qa", "qa", re.compile(r"\b(qa|test|tested|verified|verification|playwright|smoke)\b", re.I)),
    ("review", "review", "review", re.compile(r"\b(review|diff|finding|regression)\b", re.I)),
    ("running", "running", "implementation", re.compile(r"\b(running|working|implementing|in progress)\b", re.I)),
]

ARTIFACT_RULES = [
    ("tests_passed", re.compile(r"\b(test|tests|smoke|playwright|qa)\b.{0,80}\b(pass|passed|ok|green|verified)\b", re.I)),
    ("tests_failed", re.compile(r"\b(test|tests|smoke|playwright|qa)\b.{0,80}\b(fail|failed|red)\b", re.I)),
    ("evidence_recorded", re.compile(r"\b(evidence|artifact|log|report|screenshot)\b.{0,80}\b(recorded|captured|written|saved|attached)\b", re.I)),
    ("issue_updated", re.compile(r"\b(issue|github)\b.{0,80}\b(updated|closed|created|linked)\b", re.I)),
    ("discord_updated", re.compile(r"\b(discord|thread|channel)\b.{0,80}\b(updated|posted|created|linked)\b", re.I)),
    ("commit_pushed", re.compile(r"\b(commit|committed|push|pushed)\b", re.I)),
    ("rollback_ready", re.compile(r"\b(rollback|backup|snapshot)\b.{0,80}\b(ready|created|recorded|available)\b", re.I)),
    ("docs_updated", re.compile(r"\b(doc|docs|documentation|runbook|release notes)\b.{0,80}\b(updated|written|added)\b", re.I)),
]

RISK_RULES = [
    ("approval_needed", re.compile(r"\b(needs approval|approval required|requires supervisor|human decision)\b", re.I)),
    ("blocked", re.compile(r"\b(blocked|waiting|cannot proceed|needs input)\b", re.I)),
    ("failure", re.compile(r"\b(failed|error|exception|traceback|cannot complete)\b", re.I)),
    ("secret_risk", re.compile(r"\b(secret|token|credential|private key|password)\b", re.I)),
    ("external_write", re.compile(r"\b(external write|github issue|discord post|openclaw dispatch|public exposure)\b", re.I)),
]


class ProgressParseError(ValueError):
    """Raised when progress input is invalid or unsafe."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse redacted worker progress into PNH dispatch state.")
    parser.add_argument("--packet-id", required=True, help="Dispatch packet id to update.")
    parser.add_argument("--text", default="", help="Short redacted progress text.")
    parser.add_argument("--text-file", default="", help="Text file to parse.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Dispatch state JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Dry-run output JSON.")
    parser.add_argument("--apply", action="store_true", help="Update dispatch state with semantic progress metadata.")
    args = parser.parse_args()

    try:
        packet_id = compact(args.packet_id, "packet id", 160)
        text = load_text(args.text, args.text_file)
        progress = parse_progress(text)
        state_path = Path(args.state_file)
        state = load_object(state_path)
        record = dict(state.get(packet_id, {}))
        planned = attach_progress(record, progress)
        result = {
            "pnhWorkerProgressParse": True,
            "mode": "apply" if args.apply else "dry-run",
            "packetId": packet_id,
            "stateFile": safe_path_label(state_path),
            "progress": progress,
            "writesPerformed": False,
        "messageContentStored": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
        }
        if args.apply:
            state[packet_id] = planned
            save_object(state_path, state)
            result["writesPerformed"] = True
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ProgressParseError) as exc:
        print(f"pnh_worker_progress_parse=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "out": safe_path_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def parse_progress(text: str) -> dict[str, Any]:
    if SECRET_PATTERN.search(text):
        raise ProgressParseError("progress input appears to contain a secret-like value")
    compacted = " ".join(text.split())
    if not compacted:
        raise ProgressParseError("progress text is required")
    if len(compacted) > 5000:
        raise ProgressParseError("progress text is too long")
    matched = []
    for label, status, stage, pattern in STATUS_RULES:
        if pattern.search(compacted):
            matched.append((label, status, stage))
    if not matched:
        status, stage, confidence = "running", "unknown", 30
        status_labels = ["generic-progress"]
    else:
        label, status, stage = matched[0]
        status_labels = [item[0] for item in matched]
        confidence = confidence_for(status, status_labels, artifact_signals(compacted), risk_signals(compacted))
    artifacts = artifact_signals(compacted)
    risks = risk_signals(compacted)
    evidence_strength = evidence_strength_for(artifacts, status)
    requires_supervisor = status in {"blocked", "failed"} or "approval_needed" in risks
    next_action = next_action_hint_for(
        status=status,
        evidence_strength=evidence_strength,
        requires_supervisor=requires_supervisor,
        risks=risks,
    )
    return {
        "parserVersion": 2,
        "status": status,
        "stage": stage,
        "confidence": confidence,
        "signals": dedupe([*status_labels, *artifacts, *risks])[:12],
        "artifactSignals": artifacts,
        "riskSignals": risks,
        "evidenceStrength": evidence_strength,
        "requiresSupervisorAction": requires_supervisor,
        "recommendedNextAction": next_action,
        "messageContentStored": False,
        "updatedAt": utc_now(),
    }


def attach_progress(record: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    updated = dict(record)
    updated["semanticProgress"] = progress
    updated["updatedAt"] = progress["updatedAt"]
    return updated


def artifact_signals(text: str) -> list[str]:
    return [label for label, pattern in ARTIFACT_RULES if pattern.search(text)]


def risk_signals(text: str) -> list[str]:
    return [label for label, pattern in RISK_RULES if pattern.search(text)]


def confidence_for(status: str, status_labels: list[str], artifacts: list[str], risks: list[str]) -> int:
    base = {
        "failed": 80,
        "blocked": 75,
        "done": 65,
        "qa": 60,
        "review": 55,
        "running": 45,
    }.get(status, 35)
    evidence_bonus = min(20, len(artifacts) * 5)
    risk_bonus = 10 if risks and status in {"failed", "blocked"} else 0
    signal_bonus = min(10, max(0, len(status_labels) - 1) * 3)
    return min(95, base + evidence_bonus + risk_bonus + signal_bonus)


def evidence_strength_for(artifacts: list[str], status: str) -> str:
    strong = {"tests_passed", "evidence_recorded", "issue_updated", "discord_updated", "commit_pushed"}
    if status == "done" and len(strong & set(artifacts)) >= 2:
        return "high"
    if status in {"done", "qa", "review"} and artifacts:
        return "medium"
    if status in {"failed", "blocked"} and artifacts:
        return "medium"
    return "low"


def next_action_hint_for(
    *,
    status: str,
    evidence_strength: str,
    requires_supervisor: bool,
    risks: list[str],
) -> str:
    if status == "failed":
        return "inspect_failure_evidence_and_plan_retry"
    if requires_supervisor and "approval_needed" in risks:
        return "route_to_supervisor_decision"
    if status == "blocked":
        return "resolve_blocker_or_mark_blocked"
    if status == "done" and evidence_strength == "high":
        return "record_worker_result_and_close_dispatch"
    if status == "done":
        return "capture_missing_evidence_before_close"
    if status == "qa":
        return "wait_for_or_record_qa_result"
    if status == "review":
        return "wait_for_or_record_review_result"
    return "continue_progress_monitoring"


def dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def load_text(text: str, text_file: str) -> str:
    if text_file:
        return Path(text_file).read_text(encoding="utf-8")
    return text


def load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProgressParseError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ProgressParseError("dispatch state must be an object")
    return payload


def save_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def compact(value: Any, label: str, max_len: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        raise ProgressParseError(f"{label} is required")
    if len(text) > max_len:
        raise ProgressParseError(f"{label} is too long")
    return text


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

"""Redacted dispatch-state summary helpers for Personal Notion Hub."""

from __future__ import annotations

from typing import Any


def summarize_dispatch_record(packet_id: str, value: dict[str, Any]) -> dict[str, Any]:
    """Return metadata-only status fields for one dispatch-state record."""
    github_issue_set = bool(value.get("githubIssueUrl"))
    discord_thread_set = bool(value.get("discordThreadId"))
    worker_result_set = bool(value.get("workerSessionId"))
    worker_evidence_ref_set = bool(value.get("workerEvidenceRef"))
    worker_status = str(value.get("workerStatus") or "")
    task_status = task_status_for(
        github_issue_set=github_issue_set,
        discord_thread_set=discord_thread_set,
        worker_result_set=worker_result_set,
        worker_status=worker_status,
    )
    missing = missing_evidence_for(
        github_issue_set=github_issue_set,
        discord_thread_set=discord_thread_set,
        worker_result_set=worker_result_set,
        worker_evidence_ref_set=worker_evidence_ref_set,
    )
    return {
        "packetId": str(packet_id),
        "githubIssueNumber": value.get("githubIssueNumber", ""),
        "githubIssueSet": github_issue_set,
        "discordThreadId": value.get("discordThreadId", ""),
        "discordThreadSet": discord_thread_set,
        "workerSessionId": value.get("workerSessionId", ""),
        "workerStatus": worker_status,
        "workerResultSet": worker_result_set,
        "workerEvidenceRefSet": worker_evidence_ref_set,
        "workerResultRecordedAt": value.get("workerResultRecordedAt", ""),
        "taskStatus": task_status,
        "evidenceCompleteness": evidence_completeness(missing),
        "missingEvidence": missing,
        "nextAction": next_action_for(task_status, missing),
        "updatedAt": value.get("updatedAt", ""),
    }


def task_status_for(
    *,
    github_issue_set: bool,
    discord_thread_set: bool,
    worker_result_set: bool,
    worker_status: str,
) -> str:
    if worker_status == "failed":
        return "worker_failed"
    if worker_status == "blocked":
        return "worker_blocked"
    if worker_result_set and worker_status == "done":
        return "worker_done"
    if worker_result_set:
        return "worker_result_recorded"
    if discord_thread_set:
        return "dispatched_to_worker_thread"
    if github_issue_set:
        return "ledger_ready"
    return "captured_not_dispatched"


def missing_evidence_for(
    *,
    github_issue_set: bool,
    discord_thread_set: bool,
    worker_result_set: bool,
    worker_evidence_ref_set: bool,
) -> list[str]:
    missing = []
    if not github_issue_set:
        missing.append("github_issue")
    if not discord_thread_set:
        missing.append("discord_thread")
    if not worker_result_set:
        missing.append("worker_session")
    if worker_result_set and not worker_evidence_ref_set:
        missing.append("worker_evidence_ref")
    return missing


def evidence_completeness(missing: list[str]) -> int:
    expected = 3
    missing_core = sum(1 for item in missing if item in {"github_issue", "discord_thread", "worker_session"})
    return max(0, min(100, round(((expected - missing_core) / expected) * 100)))


def next_action_for(task_status: str, missing: list[str]) -> str:
    if task_status == "worker_failed":
        return "review_worker_evidence_and_retry_or_mark_blocked"
    if task_status == "worker_blocked":
        return "resolve_blocker_or_request_supervisor_decision"
    if task_status == "worker_done":
        if "github_issue" in missing or "discord_thread" in missing:
            return "link_ledger_and_thread_before_delivery"
        return "summarize_worker_result_for_supervisor_review"
    if task_status == "worker_result_recorded":
        return "inspect_worker_status_before_delivery"
    if task_status == "dispatched_to_worker_thread":
        return "capture_worker_session_result"
    if task_status == "ledger_ready":
        return "dispatch_to_worker_thread"
    return "export_candidate_and_create_ledger"

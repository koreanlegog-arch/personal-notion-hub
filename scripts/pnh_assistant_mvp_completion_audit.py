#!/usr/bin/env python3
"""Evidence-based completion audit for the PNH private assistant MVP.

This audit aggregates the current backend/private-ingress/dispatch automation
state. It does not read private bodies, does not print token values, and does
not persist exact owner network URLs.
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
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-ASSISTANT-MVP-COMPLETION-AUDIT-20260606" / "completion_audit.json"
sys.path.insert(0, str(ROOT))


COMMANDS = {
    "privateInbox": ["scripts/private_inbox_status.py"],
    "privacyGate": ["scripts/pnh_real_data_privacy_gate.py"],
    "phoneSetupReadiness": ["scripts/pnh_phone_automation_setup_readiness.py"],
    "phoneLiveProbe": ["scripts/pnh_phone_automation_live_probe.py"],
    "phoneHandoff": ["scripts/pnh_phone_automation_handoff_packet.py"],
    "unattendedStatus": ["scripts/pnh_unattended_automation_status.py"],
    "schedulerTick": ["scripts/pnh_scheduler_tick.py"],
    "dispatchState": ["scripts/pnh_dispatch_state_status.py"],
    "dispatchEvidence": ["scripts/pnh_dispatch_evidence_summary.py"],
    "localAdapterStatus": ["scripts/pnh_private_data_adapter_status.py"],
    "liveAdapterStatus": ["scripts/pnh_live_private_data_adapter_batch_sync.py"],
    "phoneRecentSummary": ["scripts/pnh_phone_capture_recent_summary.py"],
    "phoneSourceCoverage": [
        "scripts/pnh_phone_source_coverage_session.py",
        "--out",
        "ops/runs/PNH-PHONE-SOURCE-COVERAGE-SESSION-20260606/phone_source_coverage_status.json",
    ],
    "docScriptDrift": ["scripts/pnh_doc_script_drift_check.py"],
}

COMMAND_OUTPUTS = {
    "schedulerTick": ROOT / "ops" / "runs" / "PNH-SCHEDULER-20260606" / "scheduler_tick.json",
    "dispatchEvidence": ROOT / "ops" / "runs" / "PNH-DISPATCH-EVIDENCE-SUMMARY-20260605" / "dispatch_evidence_summary.json",
    "liveAdapterStatus": ROOT / "ops" / "runs" / "PNH-LIVE-PRIVATE-DATA-ADAPTER-20260606" / "live_adapter_batch_sync.json",
    "phoneRecentSummary": ROOT / "ops" / "runs" / "PNH-PHONE-CAPTURE-RECENT-SUMMARY-20260606" / "phone_capture_recent_summary.json",
    "phoneSourceCoverage": ROOT / "ops" / "runs" / "PNH-PHONE-SOURCE-COVERAGE-SESSION-20260606" / "phone_source_coverage_status.json",
    "docScriptDrift": ROOT / "ops" / "runs" / "PNH-DOC-SCRIPT-DRIFT-CHECK-20260606" / "doc_script_drift_check.json",
}


class CompletionAuditError(ValueError):
    """Raised when the completion audit cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit PNH private assistant MVP completion state.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    parser.add_argument("--skip-refresh", action="store_true", help="Read existing evidence files instead of running commands.")
    args = parser.parse_args()

    try:
        evidence = load_existing_evidence() if args.skip_refresh else run_evidence_commands()
        payload = build_audit(evidence)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, CompletionAuditError) as exc:
        print(f"pnh_assistant_mvp_completion_audit=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps(redact_stdout(payload, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0 if payload["readyForOwnerControlledMvpUse"] else 1


def run_evidence_commands() -> dict[str, dict[str, Any]]:
    evidence = {}
    for name, command in COMMANDS.items():
        evidence[name] = run_json(command, name)
        output_path = COMMAND_OUTPUTS.get(name)
        if output_path is not None and output_path.exists():
            evidence[name] = load_json_file(output_path, name)
    return evidence


def load_existing_evidence() -> dict[str, dict[str, Any]]:
    paths = {
        "privateInbox": None,
        "privacyGate": ROOT / "ops" / "runs" / "PNH-REAL-DATA-PRIVACY-GATE-20260606" / "privacy_gate.json",
        "phoneSetupReadiness": ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-SETUP-READINESS-20260606" / "setup_readiness.json",
        "phoneLiveProbe": ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-LIVE-PROBE-20260606" / "live_probe.json",
        "phoneHandoff": ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-HANDOFF-20260606" / "phone_automation_handoff.json",
        "unattendedStatus": ROOT / "ops" / "runs" / "PNH-UNATTENDED-AUTOMATION-STATUS-20260606" / "unattended_status.json",
        "schedulerTick": ROOT / "ops" / "runs" / "PNH-SCHEDULER-20260606" / "scheduler_tick.json",
        "dispatchState": None,
        "dispatchEvidence": ROOT / "ops" / "runs" / "PNH-DISPATCH-EVIDENCE-SUMMARY-20260605" / "dispatch_evidence_summary.json",
        "localAdapterStatus": None,
        "liveAdapterStatus": ROOT / "ops" / "runs" / "PNH-LIVE-PRIVATE-DATA-ADAPTER-20260606" / "live_adapter_batch_sync.json",
        "phoneRecentSummary": ROOT / "ops" / "runs" / "PNH-PHONE-CAPTURE-RECENT-SUMMARY-20260606" / "phone_capture_recent_summary.json",
        "phoneSourceCoverage": ROOT / "ops" / "runs" / "PNH-PHONE-SOURCE-COVERAGE-SESSION-20260606" / "phone_source_coverage_status.json",
        "docScriptDrift": ROOT / "ops" / "runs" / "PNH-DOC-SCRIPT-DRIFT-CHECK-20260606" / "doc_script_drift_check.json",
    }
    result: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        if path is None:
            result[name] = load_local_metadata_evidence(name)
            continue
        if not path.exists():
            result[name] = {"ok": False, "missing": safe_path_label(path)}
            continue
        result[name] = load_json_file(path, name)
    return result


def load_local_metadata_evidence(name: str) -> dict[str, Any]:
    if name == "privateInbox":
        from companion.private_store import DEFAULT_DB_PATH, store_summary  # noqa: PLC0415

        return {
            "privateInbox": store_summary(DEFAULT_DB_PATH, create_if_missing=False),
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "ok": True,
        }
    if name == "dispatchState":
        from scripts.pnh_dispatch_state_status import DEFAULT_STATE, load_state, summarize_state  # noqa: PLC0415

        payload = summarize_state(load_state(DEFAULT_STATE), DEFAULT_STATE, limit=100, include_urls=False)
        payload["ok"] = True
        return payload
    if name == "localAdapterStatus":
        from companion.private_adapter_registry import registry_summary  # noqa: PLC0415

        return {
            "pnhPrivateDataAdapterStatus": True,
            "mode": "local-owner-exported-only",
            "liveExternalAdaptersEnabled": False,
            "externalServicesContacted": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "adapters": registry_summary(),
            "ok": True,
        }
    return {"ok": False, "error": f"unsupported local metadata evidence: {name}"}


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"{label} invalid JSON: {exc.msg}"}
    if not isinstance(payload, dict):
        return {"ok": False, "error": f"{label} non-object JSON"}
    payload["ok"] = True
    return payload


def run_json(command: list[str], label: str) -> dict[str, Any]:
    result = subprocess.run([sys.executable, *command], cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
    if result.returncode != 0:
        return {
            "ok": False,
            "returnCode": result.returncode,
            "stdoutFirstLine": first_line(result.stdout),
            "stderrFirstLine": first_line(result.stderr),
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CompletionAuditError(f"{label} returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise CompletionAuditError(f"{label} returned non-object JSON")
    payload.pop("tailnetUrl", None)
    payload["ok"] = True
    return payload


def build_audit(evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    checks = build_checks(evidence)
    failed = [item for item in checks if not item["pass"]]
    user_actions = required_user_actions(evidence)
    ready = not failed
    if ready and user_actions:
        verdict = "backend_mvp_ready_owner_action_required"
    elif ready:
        verdict = "assistant_mvp_ready_for_controlled_operation"
    else:
        verdict = "not_ready"
    return {
        "pnhAssistantMvpCompletionAudit": True,
        "generatedAt": utc_now(),
        "verdict": verdict,
        "readyForOwnerControlledMvpUse": ready,
        "checksPassed": len(checks) - len(failed),
        "checksTotal": len(checks),
        "completionPercent": round(((len(checks) - len(failed)) / len(checks)) * 100, 1) if checks else 0,
        "failedChecks": failed,
        "userActionsRequired": user_actions,
        "axisStatus": axis_status(evidence),
        "checks": checks,
        "evidenceSummary": summarize_evidence(evidence),
        "workMode": {
            "mode": "normal-harness",
            "efficiencyNote": (
                "The audit aggregates specialist evidence from private ingress, phone automation, "
                "scheduler, dispatch, and adapter checks instead of reimplementing their logic."
            ),
        },
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
        "exactOwnerNetworkUrlPersisted": False,
        "rawPrivateBodyRead": False,
    }


def build_checks(evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    inbox = evidence["privateInbox"].get("privateInbox", {})
    privacy = evidence["privacyGate"]
    phone_setup = evidence["phoneSetupReadiness"]
    live_probe = evidence["phoneLiveProbe"]
    handoff = evidence["phoneHandoff"]
    unattended = evidence["unattendedStatus"]
    scheduler = evidence["schedulerTick"]
    dispatch_state = evidence["dispatchState"]
    dispatch_evidence = evidence["dispatchEvidence"]
    local_adapters = evidence["localAdapterStatus"]
    live_adapters = evidence["liveAdapterStatus"]
    phone_recent = evidence["phoneRecentSummary"]
    phone_coverage = evidence["phoneSourceCoverage"]
    doc_drift = evidence["docScriptDrift"]
    dispatch_records = dispatch_state.get("records") if isinstance(dispatch_state.get("records"), list) else []
    semantic_records = [item for item in dispatch_records if isinstance(item, dict) and item.get("semanticProgressSet")]
    phone_jobs = [
        item
        for item in scheduler.get("results", [])
        if isinstance(item, dict) and str(item.get("job", "")).startswith("phone-automation")
    ]
    checks = [
        check("encrypted_private_inbox_ready", inbox.get("byStorageMode", {}).get("encrypted-vault", 0) > 0),
        check("plaintext_private_inbox_zero", inbox.get("byStorageMode", {}).get("plaintext-inbox", -1) == 0),
        check("privacy_gate_ready", privacy.get("verdict") == "ready_for_controlled_real_phone_adapter_run"),
        check("phone_setup_ready", phone_setup.get("verdict") == "ready_for_owner_phone_tool_configuration"),
        check("phone_live_probe_available", live_probe.get("success") is True),
        check("phone_handoff_placeholder_only", handoff.get("tokenPlaceholderOnly") is True and handoff.get("exactOwnerNetworkUrlPersisted") is False),
        check("unattended_status_ready_or_idle", unattended.get("decision") in {"idle_ready", "ready_to_run_bounded_pilot", "retry_candidates_waiting"}),
        check("scheduler_runs_phone_jobs", scheduler.get("pnhSchedulerTick") is True and len(phone_jobs) >= 2 and not scheduler.get("failedJobs")),
        check("dispatch_state_linked", dispatch_state.get("totalRecords", 0) > 0 and dispatch_state.get("githubLinked") == dispatch_state.get("totalRecords") and dispatch_state.get("discordLinked") == dispatch_state.get("totalRecords")),
        check("semantic_progress_complete", bool(dispatch_records) and len(semantic_records) == len(dispatch_records) and not any(item.get("semanticProgressRequiresSupervisorAction") for item in semantic_records)),
        check("dispatch_evidence_complete", dispatch_evidence.get("averageEvidenceCompleteness", 0) >= 100 and dispatch_evidence.get("blockedOrFailed", 1) == 0),
        check("local_private_adapters_available", len(local_adapters.get("adapters", [])) >= 8),
        check("live_adapter_framework_ready", live_adapters.get("adapterCount", 0) >= 4 and not live_adapters.get("failedAdapters")),
        check("phone_capture_sources_covered", phone_recent.get("phoneCaptureCount", 0) > 0 and not phone_recent.get("missingPhoneSourcesInRecentWindow") and phone_coverage.get("verdict") == "all_phone_sources_covered"),
        check("current_doc_script_refs_ok", doc_drift.get("verdict") == "current_docs_script_refs_ok" and doc_drift.get("missingScriptRefCount") == 0),
        check("private_ingest_dedup_evidence_exists", (ROOT / "ops" / "runs" / "PNH-PRIVATE-INGEST-DEDUP-20260606" / "evidence_log.md").exists()),
        check("no_private_or_token_values_printed", no_sensitive_flags(evidence)),
    ]
    return checks


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed)}


def required_user_actions(evidence: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    actions = []
    handoff = evidence["phoneHandoff"]
    setup_ready = evidence["phoneSetupReadiness"].get("verdict") == "ready_for_owner_phone_tool_configuration"
    phone_live_probe_ready = evidence["phoneLiveProbe"].get("success") is True
    recent_phone_count = int(evidence["phoneRecentSummary"].get("phoneCaptureCount") or 0)
    phone_payload_observed = phone_live_probe_ready or recent_phone_count > 0
    phone_sources_covered = (
        evidence["phoneSourceCoverage"].get("verdict") == "all_phone_sources_covered"
        and not evidence["phoneSourceCoverage"].get("missingAfter")
    )
    privacy_ready = evidence["privacyGate"].get("verdict") == "ready_for_controlled_real_phone_adapter_run"

    if handoff.get("verdict") == "ready_for_owner_phone_tool_configuration" and not phone_payload_observed:
        actions.append(
            {
                "action": "configure_owner_phone_automation_tool",
                "reason": "The repo can generate placeholder-only profiles, but the owner must copy the local token and endpoint into the phone tool outside chat/Git.",
            }
        )
        actions.append(
            {
                "action": "send_first_owner_synthetic_or_real_phone_payload",
                "reason": "The live probe is ready, but actual phone-tool delivery must be initiated from the owner-controlled phone app.",
            }
        )
    elif not setup_ready:
        actions.append(
            {
                "action": "fix_owner_phone_automation_setup",
                "reason": "Phone automation setup readiness did not pass.",
            }
        )
    elif not phone_sources_covered:
        actions.append(
            {
                "action": "complete_phone_source_adapter_configuration",
                "reason": "At least one supported phone source has not been observed in recent encrypted-vault metadata.",
            }
        )

    if phone_payload_observed and not privacy_ready:
        actions.append(
            {
                "action": "rerun_final_privacy_gate_after_first_real_payload",
                "reason": "Phone payload metadata is present, but the final privacy gate is not currently passing.",
            }
        )
    return actions


def axis_status(evidence: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        "documentScriptDrift": "ready" if evidence["docScriptDrift"].get("verdict") == "current_docs_script_refs_ok" else "needs_attention",
        "dispatchState": "ready" if evidence["dispatchEvidence"].get("averageEvidenceCompleteness", 0) >= 100 else "needs_attention",
        "semanticWorkerProgress": "ready" if evidence["dispatchState"].get("totalRecords", 0) > 0 else "needs_attention",
        "unattendedAutomation": str(evidence["unattendedStatus"].get("decision") or "unknown"),
        "realPrivateDataAdapters": "covered_metadata_ready" if evidence["phoneSourceCoverage"].get("verdict") == "all_phone_sources_covered" else "ready_for_owner_configured_inputs" if evidence["phoneSetupReadiness"].get("verdict") == "ready_for_owner_phone_tool_configuration" else "needs_attention",
    }


def summarize_evidence(evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    inbox = evidence["privateInbox"].get("privateInbox", {})
    scheduler = evidence["schedulerTick"]
    dispatch = evidence["dispatchEvidence"]
    live_adapters = evidence["liveAdapterStatus"]
    phone_recent = evidence["phoneRecentSummary"]
    phone_coverage = evidence["phoneSourceCoverage"]
    doc_drift = evidence["docScriptDrift"]
    return {
        "privateInboxTotal": inbox.get("totalCaptures"),
        "encryptedVaultRows": inbox.get("byStorageMode", {}).get("encrypted-vault"),
        "plaintextInboxRows": inbox.get("byStorageMode", {}).get("plaintext-inbox"),
        "privacyGateVerdict": evidence["privacyGate"].get("verdict"),
        "phoneSetupVerdict": evidence["phoneSetupReadiness"].get("verdict"),
        "phoneLiveProbeVerdict": evidence["phoneLiveProbe"].get("verdict"),
        "phoneCaptureCount": phone_recent.get("phoneCaptureCount"),
        "phoneMissingSourceCount": len(phone_recent.get("missingPhoneSourcesInRecentWindow", [])) if isinstance(phone_recent.get("missingPhoneSourcesInRecentWindow"), list) else None,
        "phoneSourceCoverageVerdict": phone_coverage.get("verdict"),
        "phoneHandoffVerdict": evidence["phoneHandoff"].get("verdict"),
        "docScriptDriftVerdict": doc_drift.get("verdict"),
        "docScriptMissingRefs": doc_drift.get("missingScriptRefCount"),
        "unattendedDecision": evidence["unattendedStatus"].get("decision"),
        "schedulerJobsRun": scheduler.get("jobsRun"),
        "schedulerFailedJobs": len(scheduler.get("failedJobs", [])) if isinstance(scheduler.get("failedJobs"), list) else None,
        "dispatchAverageEvidenceCompleteness": dispatch.get("averageEvidenceCompleteness"),
        "dispatchBlockedOrFailed": dispatch.get("blockedOrFailed"),
        "liveAdapterCount": live_adapters.get("adapterCount"),
        "liveAdapterFailedCount": len(live_adapters.get("failedAdapters", [])) if isinstance(live_adapters.get("failedAdapters"), list) else None,
    }


def no_sensitive_flags(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("privateValuesPrinted") is True:
            return False
        if value.get("tokenValuePrinted") is True or value.get("secretValuePrinted") is True:
            return False
        if value.get("baseUrlValuePrinted") is True or value.get("exactOwnerNetworkUrlPersisted") is True:
            return False
        if value.get("rawPrivateBodyRead") is True or value.get("messageContentStored") is True:
            return False
        return all(no_sensitive_flags(item) for item in value.values())
    if isinstance(value, list):
        return all(no_sensitive_flags(item) for item in value)
    return True


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhAssistantMvpCompletionAudit": True,
        "verdict": payload["verdict"],
        "readyForOwnerControlledMvpUse": payload["readyForOwnerControlledMvpUse"],
        "completionPercent": payload["completionPercent"],
        "checksPassed": payload["checksPassed"],
        "checksTotal": payload["checksTotal"],
        "userActionCount": len(payload["userActionsRequired"]),
        "out": safe_path_label(out_path),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def first_line(value: str) -> str:
    return value.strip().splitlines()[0][:240] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

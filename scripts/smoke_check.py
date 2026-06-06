#!/usr/bin/env python3
"""Static smoke checks for Personal Notion Hub.

This script intentionally avoids external dependencies.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "index.html",
    "favicon.ico",
    "AGENTS.md",
    "assets/css/styles.css",
    "assets/js/app.js",
    "assets/js/companion-bridge.js",
    "assets/js/assistant-storage.js",
    "assets/js/assistant-import.js",
    "assets/js/assistant-rules.js",
    "assets/img/workspace-visual.png",
    "data/seed.json",
    "README.md",
    "docs/TEST_PLAN.md",
    "docs/SECURITY_NOTES.md",
    "docs/PASSPHRASE_KEYCHAIN_BACKEND_DESIGN.md",
    "docs/PASSPHRASE_RECOVERY_POLICY.md",
    "docs/REAL_DATA_ADAPTER_PRIVACY_GATE.md",
    "docs/PHONE_INGRESS_SECURITY.md",
    "docs/GITHUB_LEDGER_BRIDGE_DESIGN.md",
    "docs/PNH_DISPATCH_JOB_RUNBOOK.md",
    "docs/PNH_SINGLE_COMMAND_PACKET_RUNBOOK.md",
    "docs/PHONE_AUTOMATION_ADAPTER_RUNBOOK.md",
    "ops/templates/PRIVATE_DATA_ADAPTER_BRIEF_TEMPLATE.md",
    "ops/templates/PRIVATE_DATA_ADAPTER_SECURITY_GATE_TEMPLATE.md",
    "ops/checklists/PRIVATE_DATA_ADAPTER_QA_CHECKLIST.md",
    ".github/workflows/pages.yml",
    "companion/encrypted_vault.py",
    "companion/passphrase_provider.py",
    "companion/private_store.py",
    "companion/private_adapter_registry.py",
    "companion/phone_adapter_ingest.py",
    "companion/secret_backends.py",
    "companion/command_packet_status.py",
    "companion/single_command_packet_runner.py",
    "companion/server.py",
    "scripts/private_inbox_init.py",
    "scripts/simulate_mobile_capture.py",
    "scripts/private_inbox_status.py",
    "scripts/encrypted_vault_backup.py",
    "scripts/encrypted_vault_restore.py",
    "scripts/encrypted_vault_delete.py",
    "scripts/encrypted_vault_rotate_passphrase.py",
    "scripts/encrypted_vault_metadata_audit.py",
    "scripts/encrypted_backup_envelope_audit.py",
    "scripts/keychain_readiness.py",
    "scripts/passphrase_provider_smoke_check.py",
    "scripts/vault_secret_store.py",
    "scripts/vault_secret_status.py",
    "scripts/vault_secret_delete.py",
    "scripts/vault_secret_smoke_check.py",
    "scripts/plaintext_migration_audit.py",
    "scripts/plaintext_migration_apply.py",
    "scripts/redacted_browser_qa_check.py",
    "scripts/sensitive_owner_readiness_check.py",
    "scripts/run_playwright_redacted_ui_qa.sh",
    "scripts/phone_ingress_smoke_check.py",
    "scripts/phone_adapter_ingress_smoke_check.py",
    "scripts/pnh_phone_adapter_payload_template.py",
    "scripts/pnh_phone_adapter_send.py",
    "scripts/pnh_phone_adapter_send_smoke_check.py",
    "scripts/pnh_phone_automation_profile_template.py",
    "scripts/pnh_phone_automation_profile_template_smoke_check.py",
    "scripts/pnh_phone_automation_setup_readiness.py",
    "scripts/pnh_phone_automation_setup_readiness_smoke_check.py",
    "scripts/pnh_phone_automation_rehearsal.py",
    "scripts/pnh_phone_automation_rehearsal_smoke_check.py",
    "scripts/pnh_phone_automation_live_probe.py",
    "scripts/pnh_phone_automation_live_probe_smoke_check.py",
    "scripts/pnh_owner_phone_capture_session.py",
    "scripts/pnh_owner_phone_capture_session_smoke_check.py",
    "scripts/pnh_phone_capture_recent_summary.py",
    "scripts/pnh_phone_capture_recent_summary_smoke_check.py",
    "scripts/pnh_phone_source_coverage_session.py",
    "scripts/pnh_phone_source_coverage_session_smoke_check.py",
    "scripts/pnh_phone_automation_handoff_packet.py",
    "scripts/pnh_phone_automation_handoff_packet_smoke_check.py",
    "scripts/phone_ingress_lan_info.py",
    "scripts/phone_ingress_reachability_check.py",
    "scripts/tailnet_ingress_smoke_check.py",
    "scripts/github_ledger_bridge.py",
    "scripts/github_ledger_bridge_smoke_check.py",
    "scripts/pnh_dispatch_job.py",
    "scripts/pnh_dispatch_job_smoke_check.py",
    "scripts/pnh_dispatch_candidate_export.py",
    "scripts/pnh_dispatch_candidate_export_smoke_check.py",
    "scripts/pnh_dispatch_state_status.py",
    "scripts/pnh_dispatch_state_status_smoke_check.py",
    "scripts/pnh_dispatch_state_cleanup.py",
    "scripts/pnh_dispatch_state_cleanup_smoke_check.py",
    "scripts/pnh_worker_progress_parse.py",
    "scripts/pnh_worker_progress_parse_smoke_check.py",
    "scripts/pnh_worker_progress_backfill_from_state.py",
    "scripts/pnh_worker_progress_backfill_from_state_smoke_check.py",
    "scripts/pnh_dispatch_status_refresh.py",
    "scripts/pnh_dispatch_status_refresh_smoke_check.py",
    "scripts/pnh_external_reconciliation_plan.py",
    "scripts/pnh_external_reconciliation_plan_smoke_check.py",
    "scripts/pnh_github_label_reconciliation_apply.py",
    "scripts/pnh_github_label_reconciliation_apply_smoke_check.py",
    "scripts/pnh_github_worker_done_closure.py",
    "scripts/pnh_github_worker_done_closure_smoke_check.py",
    "scripts/pnh_discord_thread_readiness_probe.py",
    "scripts/pnh_discord_thread_readiness_probe_smoke_check.py",
    "scripts/pnh_discord_thread_status_refresh.py",
    "scripts/pnh_discord_thread_status_refresh_smoke_check.py",
    "scripts/pnh_dispatch_rehearsal.py",
    "scripts/pnh_dispatch_rehearsal_smoke_check.py",
    "scripts/pnh_worker_result_record.py",
    "scripts/pnh_worker_result_record_smoke_check.py",
    "scripts/pnh_openclaw_worker_capture.py",
    "scripts/pnh_openclaw_worker_capture_smoke_check.py",
    "scripts/pnh_dispatch_evidence_summary.py",
    "scripts/pnh_dispatch_evidence_summary_smoke_check.py",
    "scripts/pnh_auto_dispatch_from_inbox.py",
    "scripts/pnh_auto_dispatch_from_inbox_smoke_check.py",
    "scripts/pnh_unattended_dispatch_queue_plan.py",
    "scripts/pnh_unattended_dispatch_queue_plan_smoke_check.py",
    "scripts/pnh_unattended_dispatch_readiness.py",
    "scripts/pnh_unattended_dispatch_readiness_smoke_check.py",
    "scripts/pnh_unattended_dispatch_pilot.py",
    "scripts/pnh_unattended_dispatch_pilot_smoke_check.py",
    "scripts/pnh_unattended_automation_status.py",
    "scripts/pnh_unattended_automation_status_smoke_check.py",
    "scripts/pnh_single_command_packet.py",
    "scripts/pnh_single_command_packet_smoke_check.py",
    "scripts/pnh_command_packet_status_smoke_check.py",
    "scripts/pnh_single_command_packet_browser_run_smoke_check.py",
    "scripts/pnh_supervisor_review_summary.py",
    "scripts/pnh_supervisor_review_summary_smoke_check.py",
    "scripts/pnh_private_data_adapter_import.py",
    "scripts/pnh_private_data_adapter_import_smoke_check.py",
    "scripts/pnh_private_ingest_dedup_smoke_check.py",
    "scripts/pnh_private_data_adapter_status.py",
    "scripts/pnh_private_data_adapter_batch_plan.py",
    "scripts/pnh_private_data_adapter_batch_plan_smoke_check.py",
    "scripts/pnh_live_private_data_adapter_sync.py",
    "scripts/pnh_live_private_data_adapter_sync_smoke_check.py",
    "scripts/pnh_live_private_data_adapter_batch_sync.py",
    "scripts/pnh_live_private_data_adapter_batch_sync_smoke_check.py",
    "scripts/pnh_unattended_retry_backoff.py",
    "scripts/pnh_unattended_retry_backoff_smoke_check.py",
    "scripts/pnh_worker_progress_batch_import.py",
    "scripts/pnh_worker_progress_batch_import_smoke_check.py",
    "scripts/pnh_scheduler_tick.py",
    "scripts/pnh_scheduler_runtime_tick.sh",
    "scripts/pnh_scheduler_loop.py",
    "scripts/pnh_scheduler_smoke_check.py",
    "scripts/pnh_scheduler_service_plan.py",
    "scripts/pnh_scheduler_service_plan_smoke_check.py",
    "scripts/pnh_scheduler_service_status.py",
    "scripts/pnh_scheduler_install_user_service.sh",
    "scripts/pnh_scheduler_uninstall_user_service.sh",
    "scripts/pnh_companion_runtime_server.sh",
    "scripts/pnh_companion_service_plan.py",
    "scripts/pnh_companion_service_plan_smoke_check.py",
    "scripts/pnh_companion_service_status.py",
    "scripts/pnh_companion_install_user_service.sh",
    "scripts/pnh_companion_uninstall_user_service.sh",
    "scripts/pnh_benchmark_acceptance_contract.py",
    "scripts/pnh_benchmark_model_catalog_runner.py",
    "scripts/start_tailnet_session.sh",
    "scripts/stop_tailnet_session.sh",
    "scripts/pnh_tailnet_companion_api_start.sh",
    "scripts/pnh_tailnet_companion_api_stop.sh",
    "scripts/pnh_tailnet_companion_api_status.py",
    "scripts/pnh_tailnet_companion_api_smoke_check.py",
    "scripts/pnh_real_data_privacy_gate.py",
    "scripts/pnh_real_data_privacy_gate_smoke_check.py",
    "scripts/pnh_assistant_mvp_completion_audit.py",
    "scripts/pnh_assistant_mvp_completion_audit_smoke_check.py",
    "tests/redacted-ui.spec.cjs",
    "tests/launch-status-sync.spec.cjs",
    "scripts/run_playwright_launch_status_sync_qa.sh",
    "scripts/encrypted_vault_backup_restore_smoke_check.py",
    "scripts/encrypted_vault_delete_smoke_check.py",
    "scripts/encrypted_vault_rotation_smoke_check.py",
    "scripts/encrypted_vault_metadata_audit_smoke_check.py",
    "scripts/encrypted_backup_envelope_audit_smoke_check.py",
    "scripts/encrypted_vault_smoke_check.py",
    "scripts/plaintext_migration_audit_smoke_check.py",
    "scripts/plaintext_migration_apply_smoke_check.py",
    "scripts/private_inbox_smoke_check.py",
]


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []
        self.has_csp = False
        self.csp_content = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "link" and data.get("rel") == "stylesheet" and data.get("href"):
            self.assets.append(data["href"])
        if tag == "script" and data.get("src"):
            self.assets.append(data["src"])
        if tag == "meta" and data.get("http-equiv", "").lower() == "content-security-policy":
            self.has_csp = True
            self.csp_content = data.get("content") or ""


def assert_required_files() -> None:
    for rel in REQUIRED:
        path = ROOT / rel
        if not path.exists() or path.stat().st_size == 0:
            raise SystemExit(f"missing_or_empty={rel}")


def assert_private_data_adapter_governance_contracts() -> None:
    contracts = {
        "ops/templates/PRIVATE_DATA_ADAPTER_BRIEF_TEMPLATE.md": [
            "## Adapter Summary",
            "## Data Scope",
            "## Storage And Security",
            "## Approval Gates",
            "## Residual Risks",
        ],
        "ops/templates/PRIVATE_DATA_ADAPTER_SECURITY_GATE_TEMPLATE.md": [
            "## Adapter Summary",
            "## Data Handling Requirements",
            "Approved local encrypted vault",
            "## Approval Gates",
            "## Validation Plan",
            "## Rollback Plan",
            "## Residual Risks",
        ],
        "ops/checklists/PRIVATE_DATA_ADAPTER_QA_CHECKLIST.md": [
            "## 1. Fixture-Only Validation",
            "## 2. No-Secret / No-Private-Value Evidence",
            "## 3. Local Encrypted Vault Path",
            "## 4. Redacted Browser QA",
            "## 5. Rollback / Backup Checks",
            "## 6. Approval Gates",
            "## 7. Release-Readiness Verdict",
            "Acceptance Matrix",
        ],
    }
    for rel, tokens in contracts.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                raise SystemExit(f"missing_private_adapter_governance_contract={rel}:{token}")
    security_gate = (ROOT / "ops/templates/PRIVATE_DATA_ADAPTER_SECURITY_GATE_TEMPLATE.md").read_text(
        encoding="utf-8"
    )
    if "Storage Mode | No storage / Local cache / Local database / Export file" in security_gate:
        raise SystemExit("unsafe_private_adapter_storage_mode_contract=true")


def assert_secret_backend_contracts() -> None:
    backend = (ROOT / "companion/secret_backends.py").read_text(encoding="utf-8")
    provider = (ROOT / "companion/passphrase_provider.py").read_text(encoding="utf-8")
    scripts = "\n".join(
        [
            (ROOT / "scripts/vault_secret_store.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/vault_secret_status.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/vault_secret_delete.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/vault_secret_smoke_check.py").read_text(encoding="utf-8"),
        ]
    )
    expected = [
        "windows-dpapi-file",
        "ConvertFrom-SecureString",
        "ConvertTo-SecureString",
        "EncodedCommand",
        "DELETE_VAULT_SECRET",
        "secretValuePrinted",
        "vault_secret_smoke_check_pass=true",
    ]
    combined = "\n".join([backend, provider, scripts])
    for token in expected:
        if token not in combined:
            raise SystemExit(f"missing_secret_backend_contract={token}")
    if "cmdkey" in backend or "/pass:" in combined:
        raise SystemExit("unsafe_secret_backend_cmdkey_contract=true")


def assert_github_ledger_bridge_contracts() -> None:
    design = (ROOT / "docs/GITHUB_LEDGER_BRIDGE_DESIGN.md").read_text(encoding="utf-8")
    dispatch_runbook = (ROOT / "docs/PNH_DISPATCH_JOB_RUNBOOK.md").read_text(encoding="utf-8")
    bridge = (ROOT / "scripts/github_ledger_bridge.py").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts/github_ledger_bridge_smoke_check.py").read_text(encoding="utf-8")
    dispatch_job = (ROOT / "scripts/pnh_dispatch_job.py").read_text(encoding="utf-8")
    dispatch_smoke = (ROOT / "scripts/pnh_dispatch_job_smoke_check.py").read_text(encoding="utf-8")
    candidate_export = (ROOT / "scripts/pnh_dispatch_candidate_export.py").read_text(encoding="utf-8")
    candidate_smoke = (ROOT / "scripts/pnh_dispatch_candidate_export_smoke_check.py").read_text(encoding="utf-8")
    state_status = (ROOT / "scripts/pnh_dispatch_state_status.py").read_text(encoding="utf-8")
    state_smoke = (ROOT / "scripts/pnh_dispatch_state_status_smoke_check.py").read_text(encoding="utf-8")
    status_refresh = (ROOT / "scripts/pnh_dispatch_status_refresh.py").read_text(encoding="utf-8")
    status_refresh_smoke = (ROOT / "scripts/pnh_dispatch_status_refresh_smoke_check.py").read_text(encoding="utf-8")
    reconciliation_plan = (ROOT / "scripts/pnh_external_reconciliation_plan.py").read_text(encoding="utf-8")
    reconciliation_plan_smoke = (ROOT / "scripts/pnh_external_reconciliation_plan_smoke_check.py").read_text(
        encoding="utf-8"
    )
    github_label_apply = (ROOT / "scripts/pnh_github_label_reconciliation_apply.py").read_text(encoding="utf-8")
    github_label_apply_smoke = (ROOT / "scripts/pnh_github_label_reconciliation_apply_smoke_check.py").read_text(
        encoding="utf-8"
    )
    github_worker_done_closure = (ROOT / "scripts/pnh_github_worker_done_closure.py").read_text(encoding="utf-8")
    github_worker_done_closure_smoke = (
        ROOT / "scripts/pnh_github_worker_done_closure_smoke_check.py"
    ).read_text(encoding="utf-8")
    discord_thread_probe = (ROOT / "scripts/pnh_discord_thread_readiness_probe.py").read_text(encoding="utf-8")
    discord_thread_probe_smoke = (ROOT / "scripts/pnh_discord_thread_readiness_probe_smoke_check.py").read_text(
        encoding="utf-8"
    )
    discord_thread_status = (ROOT / "scripts/pnh_discord_thread_status_refresh.py").read_text(encoding="utf-8")
    discord_thread_status_smoke = (ROOT / "scripts/pnh_discord_thread_status_refresh_smoke_check.py").read_text(
        encoding="utf-8"
    )
    rehearsal = (ROOT / "scripts/pnh_dispatch_rehearsal.py").read_text(encoding="utf-8")
    rehearsal_smoke = (ROOT / "scripts/pnh_dispatch_rehearsal_smoke_check.py").read_text(encoding="utf-8")
    worker_result = (ROOT / "scripts/pnh_worker_result_record.py").read_text(encoding="utf-8")
    worker_result_smoke = (ROOT / "scripts/pnh_worker_result_record_smoke_check.py").read_text(encoding="utf-8")
    openclaw_capture = (ROOT / "scripts/pnh_openclaw_worker_capture.py").read_text(encoding="utf-8")
    openclaw_capture_smoke = (ROOT / "scripts/pnh_openclaw_worker_capture_smoke_check.py").read_text(encoding="utf-8")
    evidence_summary = (ROOT / "scripts/pnh_dispatch_evidence_summary.py").read_text(encoding="utf-8")
    evidence_summary_smoke = (ROOT / "scripts/pnh_dispatch_evidence_summary_smoke_check.py").read_text(encoding="utf-8")
    auto_dispatch = (ROOT / "scripts" / "pnh_auto_dispatch_from_inbox.py").read_text(encoding="utf-8")
    auto_dispatch_smoke = (ROOT / "scripts" / "pnh_auto_dispatch_from_inbox_smoke_check.py").read_text(encoding="utf-8")
    unattended_queue = (ROOT / "scripts" / "pnh_unattended_dispatch_queue_plan.py").read_text(encoding="utf-8")
    unattended_queue_smoke = (ROOT / "scripts" / "pnh_unattended_dispatch_queue_plan_smoke_check.py").read_text(
        encoding="utf-8"
    )
    unattended_readiness = (ROOT / "scripts" / "pnh_unattended_dispatch_readiness.py").read_text(encoding="utf-8")
    unattended_readiness_smoke = (
        ROOT / "scripts" / "pnh_unattended_dispatch_readiness_smoke_check.py"
    ).read_text(encoding="utf-8")
    unattended_pilot = (ROOT / "scripts" / "pnh_unattended_dispatch_pilot.py").read_text(encoding="utf-8")
    unattended_pilot_smoke = (ROOT / "scripts" / "pnh_unattended_dispatch_pilot_smoke_check.py").read_text(
        encoding="utf-8"
    )
    single_packet_runbook = (ROOT / "docs" / "PNH_SINGLE_COMMAND_PACKET_RUNBOOK.md").read_text(encoding="utf-8")
    single_packet = (ROOT / "scripts" / "pnh_single_command_packet.py").read_text(encoding="utf-8")
    single_packet_smoke = (ROOT / "scripts" / "pnh_single_command_packet_smoke_check.py").read_text(encoding="utf-8")
    command_packet_status = (ROOT / "companion" / "command_packet_status.py").read_text(encoding="utf-8")
    command_packet_status_smoke = (ROOT / "scripts" / "pnh_command_packet_status_smoke_check.py").read_text(
        encoding="utf-8"
    )
    app_js = (ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    app_css = (ROOT / "assets" / "css" / "styles.css").read_text(encoding="utf-8")
    single_packet_browser_runner = (ROOT / "companion" / "single_command_packet_runner.py").read_text(
        encoding="utf-8"
    )
    single_packet_browser_smoke = (ROOT / "scripts" / "pnh_single_command_packet_browser_run_smoke_check.py").read_text(
        encoding="utf-8"
    )
    companion_server = (ROOT / "companion" / "server.py").read_text(encoding="utf-8")
    supervisor_review = (ROOT / "scripts" / "pnh_supervisor_review_summary.py").read_text(encoding="utf-8")
    supervisor_review_smoke = (ROOT / "scripts" / "pnh_supervisor_review_summary_smoke_check.py").read_text(encoding="utf-8")
    expected = [
        "Dry-run is allowed",
        "APPROVE_PNH_GITHUB_ISSUE_LEDGER_APPLY",
        "--approve-external-write",
        "--approve-sensitive-github-body",
        "--approve-discord-dispatch",
        "companion/private/pnh_dispatch_state.json",
        "writesPerformed",
        "private_values_printed=false",
        "pnh_dispatch_job_smoke_check_pass=true",
        "pnh_dispatch_candidate_export_smoke_check_pass=true",
        "--allow-plaintext",
        "--allow-external-db",
        "Private command body remains in the local vault",
        "pnh_dispatch_state_status_smoke_check_pass=true",
        "--include-urls",
        "pnh_dispatch_status_refresh_smoke_check_pass=true",
        "dispatchStatusRefresh",
        "--github-read",
        "externalWritesPerformed",
        "githubIssueState",
        "pnh_external_reconciliation_plan_smoke_check_pass=true",
        "externalReconciliationPlan",
        "replace_dispatch_status_labels",
        "approvalRequiredBeforeExternalWrite",
        "pnh_github_label_reconciliation_apply_smoke_check_pass=true",
        "githubLabelReconciliation",
        "gh auth",
        "pnh_github_worker_done_closure_smoke_check_pass=true",
        "githubWorkerDoneClosure",
        "close_worker_done_issue",
        "rawPrivateBodyRead",
        "pnh_discord_thread_readiness_probe_smoke_check_pass=true",
        "discordThreadReadinessProbe",
        "--approve-discord-read",
        "implement_approval_gated_discord_thread_read_refresh",
        "pnh_discord_thread_status_refresh_smoke_check_pass=true",
        "discordThreadStatusRefresh",
        "messageContentStored",
        "discordMessagesObserved",
        "githubDuplicateDetection",
        "--detect-existing-github",
        "pnh_dispatch_rehearsal_smoke_check_pass=true",
        "pnhDispatchRehearsal",
        "pnh_worker_result_record_smoke_check_pass=true",
        "workerResultSet",
        "workerSessionId",
        "pnh_openclaw_worker_capture_smoke_check_pass=true",
        "--approve-openclaw-agent-run",
        "replyDelivered",
        "externalAgentRunPerformed",
        "pnh_dispatch_evidence_summary_smoke_check_pass=true",
        "dispatchEvidenceSummary",
        "readyForSupervisorReview",
        "evidenceCompleteness",
        "missingEvidence",
        "nextAction",
        "pnh_auto_dispatch_from_inbox_smoke_check_pass=true",
        "pnhAutoDispatchFromInbox",
        "--approve-live-dispatch",
        "liveApplyGate",
        "pnh_unattended_dispatch_queue_plan_smoke_check_pass=true",
        "pnhUnattendedDispatchQueuePlan",
        "queueActivationGateRequired",
        "maxExternalWritesPerHour",
        "rollbackRequiredBeforeApply",
        "pnh_unattended_dispatch_readiness_smoke_check_pass=true",
        "pnhUnattendedDispatchReadiness",
        "APPROVE_PNH_UNATTENDED_DISPATCH_PILOT",
        "pnh_unattended_dispatch_pilot_smoke_check_pass=true",
        "pnhUnattendedDispatchPilot",
        "--approve-unattended-pilot",
        "pnh_unattended_dispatch.lock",
        "pnh_single_command_packet_smoke_check_pass=true",
        "pnhSingleCommandPacket",
        "pnh_single_command_packet.lock",
        "metadata-safe worker prompt",
        "single_command_packet_summary.json",
        "--detect-existing-github",
        "--no-auto-recover-partial-dispatch",
        "partial_dispatch_recovery_policy.json",
        "dispatch_pilot_recovery",
        "lastDispatchCheckpoint",
        "pnh_command_packet_status_smoke_check_pass=true",
        "build_command_packet_status",
        "metadata-only",
        "stageSteps",
        "Review ready",
        "command-packet-stage-rail",
        "/api/private/command-packet-status",
        "/api/private/single-command-packet/run",
        "/api/private/phone-adapter-captures",
        "pnh_single_command_packet_browser_run_smoke_check_pass=true",
        "browser_apply_gate_enforced=true",
        "PNH_BROWSER_SINGLE_PACKET_APPLY_ENABLED",
        "RUN_EXTERNAL_WRITES_AND_WORKER",
        "pnh_supervisor_review_summary_smoke_check_pass=true",
        "pnhSupervisorReviewSummary",
        "Supervisor Checks",
    ]
    combined = "\n".join(
        [
            design,
            dispatch_runbook,
            bridge,
            smoke,
            dispatch_job,
            dispatch_smoke,
            candidate_export,
            candidate_smoke,
            state_status,
            state_smoke,
            status_refresh,
            status_refresh_smoke,
            reconciliation_plan,
            reconciliation_plan_smoke,
            github_label_apply,
            github_label_apply_smoke,
            github_worker_done_closure,
            github_worker_done_closure_smoke,
            discord_thread_probe,
            discord_thread_probe_smoke,
            discord_thread_status,
            discord_thread_status_smoke,
            rehearsal,
            rehearsal_smoke,
            worker_result,
            worker_result_smoke,
            openclaw_capture,
            openclaw_capture_smoke,
            evidence_summary,
            evidence_summary_smoke,
            auto_dispatch,
            auto_dispatch_smoke,
            unattended_queue,
            unattended_queue_smoke,
            unattended_readiness,
            unattended_readiness_smoke,
            unattended_pilot,
            unattended_pilot_smoke,
            single_packet_runbook,
            single_packet,
            single_packet_smoke,
            command_packet_status,
            command_packet_status_smoke,
            app_js,
            app_css,
            single_packet_browser_runner,
            single_packet_browser_smoke,
            companion_server,
            supervisor_review,
            supervisor_review_smoke,
        ]
    )
    for token in expected:
        if token not in combined:
            raise SystemExit(f"missing_github_ledger_bridge_contract={token}")
    if "print(token)" in bridge or "print(token)" in dispatch_job or "GITHUB_TOKEN=" in design:
        raise SystemExit("unsafe_github_ledger_token_contract=true")


def assert_private_data_policy_contracts() -> None:
    docs = {
        "docs/PASSPHRASE_RECOVERY_POLICY.md": [
            "no cryptographic recovery mechanism",
            "Recovery Drill",
            "Never paste recovery material",
        ],
        "docs/REAL_DATA_ADAPTER_PRIVACY_GATE.md": [
            "Live external real-data adapters are disabled",
            "owner-exported local import adapters",
            "approved local encrypted vault",
            "Stop Conditions",
            "Ready for local import MVP",
        ],
        "docs/PHONE_INGRESS_SECURITY.md": [
            "Phone ingress is disabled by default",
            "--enable-phone-ingress",
            "http://<LAN_IP>:8765/",
            "Sensitive Data Mode",
            "Stop Conditions",
        ],
    }
    for rel, tokens in docs.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                raise SystemExit(f"missing_private_data_policy_contract={rel}:{token}")


def assert_agent_approval_override_contracts() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    expected = [
        "Do not ask for approval for:",
        "routine `git add`, `git commit`, and `git push`",
        "local dry-runs and read-only status refreshes",
        "bounded GitHub Issue, Discord/OpenClaw thread/message",
        "OpenClaw worker/model execution",
        "Do not append \"next efficient work\" suggestions to routine final reports.",
        "Report approval-required items, blockers, residual risks, and completed",
        "If no material gate, blocker, or explicit supervisor status request exists,",
        "If the supervisor replies with `진행해`, `쭉 진행해`, or equivalent continuation language",
        "Do not ask whether to run smoke checks, browser QA, dry-runs, scoped commits, or pushes",
        "Do not stop with a final-style report after each small slice",
        "Use final-style reports only when at least one of these is true:",
        "the active phase is complete and no immediate next scoped task is apparent",
        "progress is blocked by missing external state or supervisor-only action",
        "the supervisor explicitly asks for status, summary, or review",
        "If a final-style report stops work, it must clearly identify either:",
        "approval-required item(s)",
        "an actual blocker",
        "phase completion with no current scoped task remaining",
        "When a material gate is opened, state why the gate is material",
        "If reporting because of a material gate or blocker, state the exact reason work must",
    ]
    for token in expected:
        if token not in agents:
            raise SystemExit(f"missing_agent_approval_override_contract={token}")


def assert_html_assets() -> None:
    parser = AssetParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    if not parser.has_csp:
        raise SystemExit("missing_meta_csp=true")
    if "connect-src 'self' http://127.0.0.1:8765" not in parser.csp_content:
        raise SystemExit("missing_loopback_connect_src=true")
    forbidden_connect = ["localhost", "0.0.0.0", "*", "127.0.0.1:"]
    for token in forbidden_connect:
        if token == "127.0.0.1:" and "http://127.0.0.1:8765" in parser.csp_content:
            remaining = parser.csp_content.replace("http://127.0.0.1:8765", "")
            if token not in remaining:
                continue
        if token in parser.csp_content:
            raise SystemExit(f"forbidden_csp_connect_token={token}")
    for asset in parser.assets:
        asset_path = (ROOT / asset.replace("./", "", 1)).resolve()
        if not asset_path.exists():
            raise SystemExit(f"missing_asset={asset}")


def assert_no_inline_handlers() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    if re.search(r"\son[a-zA-Z]+\s*=", html):
        raise SystemExit("inline_event_handler_found=true")


def assert_expected_app_contracts() -> None:
    js = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")
    expected = [
        "localStorage.getItem",
        "localStorage.setItem",
        "readStoredState",
        "writeStoredState",
        "JSON.parse",
        "JSON.stringify",
        "exportState",
        "handleImport",
        "validateImportedState",
        "renderAssistant",
        "renderLaunch",
        "buildLaunchPacket",
        "buildDiscordDispatchDraft",
        "buildGithubIssueDraft",
        "launches",
        "loadAssistantCaptures",
        "PNHAssistantStorage",
        "PNHAssistantImport",
        "PNHAssistantRules",
        "PNHCompanionBridge",
        "launchCompanionPanel",
        "launchDispatchStatusPanel",
        "commandPacketStatusCard",
        "commandPacketOperatorAction",
        "operatorActionBanner",
        "refreshDispatchState",
        "refreshCommandPacketStatus",
        "runSingleCommandPacketDryRun",
        "dispatchRecordForLaunch",
        "dispatchRecordLabel",
        "confirmDispatchMappingForLaunch",
        "confirmTaskStatusForLaunch",
        "syncLaunchProgressToBoards",
        "ensureLaunchProgressProject",
        "ensureLaunchProgressTask",
        "projectStatusForDispatchRecord",
        "taskStatusForDispatchRecord",
        "buildDispatchProgressNotes",
        "dispatch-progress",
        "progressSyncedAt",
        "progressTaskId",
        "ledger_and_discord_linked",
        "dispatchConfirmedAt",
        "taskStatusConfirmedAt",
        "githubIssueNumber",
        "discordThreadId",
        "workerResults",
        "commandPacketStatus",
        "Single command packet",
        "Operator action",
        "Review ready",
        "Packet queued",
        "Queue clear",
        "Run Dry-Run",
        "Apply Locked",
        "workerResultSet",
        "workerStatus",
        "taskStatus",
        "evidenceCompleteness",
        "nextAction",
        "sendLatestLaunchToCompanion",
        "assistantWorkspacePanel",
        "sendLatestAssistantToCompanion",
        "sendAssistantCaptureToCompanion",
        "companionPayloadForAssistantCapture",
        "ASSISTANT_DISPATCH_INTENTS",
        "assistantDispatchIntentLabel",
        "normalizeAssistantDispatchIntent",
        "isCommandDispatchIntent",
        "dispatchIntent",
        "\"pnh_assistant_capture\"",
        "payloadType: commandIntent ? \"pnh_mobile_command_packet\"",
        "sendMobileCommandPacket || bridge.sendAssistantCapture",
        "toggleScreenshotRedaction",
        "data-sensitive",
        "normalizeHttpUrl",
        "textContent",
        "rel = \"noopener noreferrer\"",
    ]
    for token in expected:
        if token not in js:
            raise SystemExit(f"missing_app_contract={token}")
    assistant_import = (ROOT / "assets/js/assistant-import.js").read_text(encoding="utf-8")
    for token in ["dispatchIntents", "normalizeDispatchIntent", "dispatchIntent: normalizeDispatchIntent"]:
        if token not in assistant_import:
            raise SystemExit(f"missing_assistant_import_contract={token}")
    assistant_intent_spec = (ROOT / "tests/assistant-dispatch-intent.spec.cjs").read_text(encoding="utf-8")
    for token in ["daily_command", "pnh_mobile_command_packet", "pnh_assistant_capture", "__assistantWorkspaceCalls"]:
        if token not in assistant_intent_spec:
            raise SystemExit(f"missing_assistant_dispatch_intent_qa_contract={token}")
    if "innerHTML" in js:
        raise SystemExit("innerHTML_found=true")


def assert_js_security_contracts() -> None:
    forbidden = ["innerHTML", "XMLHttpRequest("]
    for path in sorted((ROOT / "assets/js").glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                raise SystemExit(f"forbidden_js_token={path.relative_to(ROOT)}:{token}")
        if path.name != "companion-bridge.js" and "fetch(" in text:
            raise SystemExit(f"forbidden_fetch_token={path.relative_to(ROOT)}")


def assert_companion_bridge_contracts() -> None:
    bridge = (ROOT / "assets/js/companion-bridge.js").read_text(encoding="utf-8")
    expected = [
        "http://127.0.0.1:8765",
        "function validatedBaseUrl",
        "async function controlledFetch",
        "validCompanionOrigin",
        "target.origin !== baseUrl",
        "let sessionToken = \"\"",
        "Authorization",
        "sendCapture",
        "sendAssistantCapture",
        "sendLaunchPacket",
        "dispatchState",
        "commandPacketStatus",
        "runSingleCommandPacket",
    ]
    for token in expected:
        if token not in bridge:
            raise SystemExit(f"missing_companion_bridge_contract={token}")
    if bridge.count("fetch(") != 1 or "await fetch(target.href" not in bridge:
        raise SystemExit("uncontrolled_companion_fetch=true")
    forbidden_storage = ["localStorage", "sessionStorage", "indexedDB", "indexedDB.open", "document.cookie"]
    for token in forbidden_storage:
        if token in bridge:
            raise SystemExit(f"companion_secret_storage_token={token}")
    server = (ROOT / "companion/server.py").read_text(encoding="utf-8")
    for token in [
        "--enable-phone-ingress",
        "/api/private/dispatch-state",
        "/api/private/command-packet-status",
        "/api/private/single-command-packet/run",
        "/api/private/phone-adapter-captures",
        "phone_ingress_enabled",
        "phone ingress requires --enable-browser-bridge",
        "phone ingress allowed origin must use loopback or private LAN host",
        "STATIC_ALLOWED_PREFIXES",
    ]:
        if token not in server:
            raise SystemExit(f"missing_phone_ingress_contract={token}")


def assert_encrypted_vault_contracts() -> None:
    vault = (ROOT / "companion/encrypted_vault.py").read_text(encoding="utf-8")
    server = (ROOT / "companion/server.py").read_text(encoding="utf-8")
    provider = (ROOT / "companion/passphrase_provider.py").read_text(encoding="utf-8")
    init_script = (ROOT / "scripts/private_inbox_init.py").read_text(encoding="utf-8")
    status_script = (ROOT / "scripts/private_inbox_status.py").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts/encrypted_vault_smoke_check.py").read_text(encoding="utf-8")
    expected_vault = [
        "AES-256-GCM",
        "PBKDF2-HMAC-SHA256",
        "pnh.encrypted-vault-backup",
        "encrypted_mobile_captures",
        "export_encrypted_backup",
        "restore_encrypted_backup",
        "delete_encrypted_capture",
        "rotate_vault_passphrase",
        "EncryptedVaultError",
        "cryptography_available",
        "load_vault_from_env",
        "MIN_PASSPHRASE_LENGTH = 16",
        "associated_data",
    ]
    for token in expected_vault:
        if token not in vault:
            raise SystemExit(f"missing_encrypted_vault_contract={token}")
    expected_runtime = [
        "--enable-encrypted-vault",
        "--vault-passphrase-env",
        "--backup-passphrase-env",
        "--prompt-vault-passphrase",
        "--prompt-backup-passphrase",
        "--confirm-backup-passphrase",
        "--prompt-new-vault-passphrase",
        "--confirm-new-vault-passphrase",
        "--vault-passphrase-provider",
        "ROTATE_VAULT_PASSPHRASE",
        "MIGRATE_PLAINTEXT_TO_ENCRYPTED",
        "PNH_NEW_VAULT_PASSPHRASE",
        "PNH_VAULT_PASSPHRASE",
        "PNH_BACKUP_PASSPHRASE",
        "encrypted_vault_enabled",
        "private_storage_mode",
        "plaintextRowsDetected",
        "encryptedVaultMetadataAudit",
        "encryptedBackupEnvelopeAudit",
        "keychainReadiness",
        "recommendedMode",
        "secretValuePrinted",
    ]
    lifecycle_scripts = "\n".join(
        [
            (ROOT / "scripts/encrypted_vault_backup.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_restore.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_delete.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_rotate_passphrase.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_metadata_audit.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_backup_envelope_audit.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/keychain_readiness.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/plaintext_migration_audit.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/plaintext_migration_apply.py").read_text(encoding="utf-8"),
        ]
    )
    runtime_text = "\n".join([server, provider, init_script, status_script, lifecycle_scripts])
    for token in expected_runtime:
        if token not in runtime_text:
            raise SystemExit(f"missing_encrypted_runtime_contract={token}")
    expected_smoke = [
        "plaintext_found_in_db=false",
        "wrong_passphrase_accepted=true",
        "tampered_ciphertext_accepted=true",
        "secret_value_printed=false",
        "encrypted_vault_backup_restore_smoke_check_pass=true",
        "encrypted_vault_delete_smoke_check_pass=true",
        "encrypted_vault_rotation_smoke_check_pass=true",
        "encrypted_vault_metadata_audit_smoke_check_pass=true",
        "encrypted_backup_envelope_audit_smoke_check_pass=true",
        "plaintext_migration_audit_smoke_check_pass=true",
        "plaintext_migration_apply_smoke_check_pass=true",
        "passphrase_provider_smoke_check_pass=true",
    ]
    smoke_text = "\n".join(
        [
            smoke,
            (ROOT / "scripts/encrypted_vault_backup_restore_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_delete_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_rotation_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_metadata_audit_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_backup_envelope_audit_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/plaintext_migration_audit_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/plaintext_migration_apply_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/passphrase_provider_smoke_check.py").read_text(encoding="utf-8"),
        ]
    )
    for token in expected_smoke:
        if token not in smoke_text:
            raise SystemExit(f"missing_encrypted_smoke_contract={token}")


def assert_redaction_contracts() -> None:
    css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
    playwright = (ROOT / "tests/redacted-ui.spec.cjs").read_text(encoding="utf-8")
    runner = (ROOT / "scripts/run_playwright_redacted_ui_qa.sh").read_text(encoding="utf-8")
    launch_sync = (ROOT / "tests/launch-status-sync.spec.cjs").read_text(encoding="utf-8")
    launch_sync_runner = (ROOT / "scripts/run_playwright_launch_status_sync_qa.sh").read_text(encoding="utf-8")
    expected = [
        "body.screenshot-redaction [data-sensitive=\"true\"]",
        "color: transparent",
        "text-shadow",
        "caret-color: transparent",
    ]
    for token in expected:
        if token not in css:
            raise SystemExit(f"missing_redaction_contract={token}")
    for token in [
        "SYNTHETIC_REDACTED_QA_BODY_NEVER_REAL_PRIVATE_DATA",
        "assistant-redacted-desktop.png",
        "screenshot-redaction",
        "sessionStorage",
        "localStorage",
    ]:
        if token not in playwright:
            raise SystemExit(f"missing_playwright_redaction_contract={token}")
    for token in [
        "npx --no-install playwright",
        "playwright_chromium_binary_unavailable",
        "npx_playwright_install_chromium",
    ]:
        if token not in runner:
            raise SystemExit(f"missing_playwright_runner_contract={token}")
    for token in [
        "Confirm Task Status",
        "ledger_and_discord_linked",
        "worker_done",
        "evidenceCompleteness",
        "dispatch-progress",
        "Private command body",
    ]:
        if token not in launch_sync:
            raise SystemExit(f"missing_launch_status_sync_contract={token}")
    for token in [
        "npx --no-install playwright",
        "playwright_launch_status_sync_qa_pass=true",
        "playwright_chromium_binary_unavailable",
    ]:
        if token not in launch_sync_runner:
            raise SystemExit(f"missing_launch_status_sync_runner_contract={token}")


def assert_workflow_permissions() -> None:
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    expected = ["contents: read", "pages: write", "id-token: write", "actions/upload-pages-artifact@v4", "actions/deploy-pages@v4"]
    for token in expected:
        if token not in workflow:
            raise SystemExit(f"missing_workflow_contract={token}")


def assert_benchmark_acceptance_contracts() -> None:
    if os.environ.get("PNH_SKIP_BENCHMARK_ACCEPTANCE_IN_SMOKE") == "1":
        return
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/pnh_benchmark_acceptance_contract.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "benchmark_acceptance_contract_failed")


def main() -> int:
    assert_required_files()
    assert_private_data_adapter_governance_contracts()
    assert_secret_backend_contracts()
    assert_github_ledger_bridge_contracts()
    assert_private_data_policy_contracts()
    assert_agent_approval_override_contracts()
    assert_html_assets()
    assert_no_inline_handlers()
    assert_expected_app_contracts()
    assert_js_security_contracts()
    assert_companion_bridge_contracts()
    assert_encrypted_vault_contracts()
    assert_redaction_contracts()
    assert_workflow_permissions()
    assert_benchmark_acceptance_contracts()
    print("smoke_check_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

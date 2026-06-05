#!/usr/bin/env python3
"""Static smoke checks for Personal Notion Hub.

This script intentionally avoids external dependencies.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "index.html",
    "favicon.ico",
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
    "ops/templates/PRIVATE_DATA_ADAPTER_BRIEF_TEMPLATE.md",
    "ops/templates/PRIVATE_DATA_ADAPTER_SECURITY_GATE_TEMPLATE.md",
    "ops/checklists/PRIVATE_DATA_ADAPTER_QA_CHECKLIST.md",
    ".github/workflows/pages.yml",
    "companion/encrypted_vault.py",
    "companion/passphrase_provider.py",
    "companion/private_store.py",
    "companion/secret_backends.py",
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
    "scripts/phone_ingress_lan_info.py",
    "scripts/phone_ingress_reachability_check.py",
    "scripts/tailnet_ingress_smoke_check.py",
    "scripts/github_ledger_bridge.py",
    "scripts/github_ledger_bridge_smoke_check.py",
    "scripts/pnh_dispatch_job.py",
    "scripts/pnh_dispatch_job_smoke_check.py",
    "scripts/start_tailnet_session.sh",
    "scripts/stop_tailnet_session.sh",
    "tests/redacted-ui.spec.cjs",
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
    ]
    combined = "\n".join([design, dispatch_runbook, bridge, smoke, dispatch_job, dispatch_smoke])
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
            "Real-data adapters are disabled",
            "approved local encrypted vault",
            "Stop Conditions",
            "Blocked",
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
        "sendLatestLaunchToCompanion",
        "assistantWorkspacePanel",
        "sendLatestAssistantToCompanion",
        "sendAssistantCaptureToCompanion",
        "companionPayloadForAssistantCapture",
        "payloadType: \"pnh_assistant_capture\"",
        "toggleScreenshotRedaction",
        "data-sensitive",
        "normalizeHttpUrl",
        "textContent",
        "rel = \"noopener noreferrer\"",
    ]
    for token in expected:
        if token not in js:
            raise SystemExit(f"missing_app_contract={token}")
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


def assert_workflow_permissions() -> None:
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    expected = ["contents: read", "pages: write", "id-token: write", "actions/upload-pages-artifact@v4", "actions/deploy-pages@v4"]
    for token in expected:
        if token not in workflow:
            raise SystemExit(f"missing_workflow_contract={token}")


def main() -> int:
    assert_required_files()
    assert_private_data_adapter_governance_contracts()
    assert_secret_backend_contracts()
    assert_github_ledger_bridge_contracts()
    assert_private_data_policy_contracts()
    assert_html_assets()
    assert_no_inline_handlers()
    assert_expected_app_contracts()
    assert_js_security_contracts()
    assert_companion_bridge_contracts()
    assert_encrypted_vault_contracts()
    assert_redaction_contracts()
    assert_workflow_permissions()
    print("smoke_check_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

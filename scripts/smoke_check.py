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
    ".github/workflows/pages.yml",
    "companion/encrypted_vault.py",
    "companion/private_store.py",
    "companion/server.py",
    "scripts/private_inbox_init.py",
    "scripts/simulate_mobile_capture.py",
    "scripts/private_inbox_status.py",
    "scripts/encrypted_vault_backup.py",
    "scripts/encrypted_vault_restore.py",
    "scripts/encrypted_vault_delete.py",
    "scripts/plaintext_migration_audit.py",
    "scripts/encrypted_vault_backup_restore_smoke_check.py",
    "scripts/encrypted_vault_delete_smoke_check.py",
    "scripts/encrypted_vault_smoke_check.py",
    "scripts/plaintext_migration_audit_smoke_check.py",
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
        "target.origin !== EXPECTED_ORIGIN",
        "let sessionToken = \"\"",
        "Authorization",
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


def assert_encrypted_vault_contracts() -> None:
    vault = (ROOT / "companion/encrypted_vault.py").read_text(encoding="utf-8")
    server = (ROOT / "companion/server.py").read_text(encoding="utf-8")
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
        "PNH_VAULT_PASSPHRASE",
        "PNH_BACKUP_PASSPHRASE",
        "encrypted_vault_enabled",
        "private_storage_mode",
        "plaintextRowsDetected",
    ]
    lifecycle_scripts = "\n".join(
        [
            (ROOT / "scripts/encrypted_vault_backup.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_restore.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_delete.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/plaintext_migration_audit.py").read_text(encoding="utf-8"),
        ]
    )
    runtime_text = "\n".join([server, init_script, status_script, lifecycle_scripts])
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
        "plaintext_migration_audit_smoke_check_pass=true",
    ]
    smoke_text = "\n".join(
        [
            smoke,
            (ROOT / "scripts/encrypted_vault_backup_restore_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/encrypted_vault_delete_smoke_check.py").read_text(encoding="utf-8"),
            (ROOT / "scripts/plaintext_migration_audit_smoke_check.py").read_text(encoding="utf-8"),
        ]
    )
    for token in expected_smoke:
        if token not in smoke_text:
            raise SystemExit(f"missing_encrypted_smoke_contract={token}")


def assert_redaction_contracts() -> None:
    css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
    expected = [
        "body.screenshot-redaction [data-sensitive=\"true\"]",
        "color: transparent",
        "text-shadow",
        "caret-color: transparent",
    ]
    for token in expected:
        if token not in css:
            raise SystemExit(f"missing_redaction_contract={token}")


def assert_workflow_permissions() -> None:
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    expected = ["contents: read", "pages: write", "id-token: write", "actions/upload-pages-artifact@v4", "actions/deploy-pages@v4"]
    for token in expected:
        if token not in workflow:
            raise SystemExit(f"missing_workflow_contract={token}")


def main() -> int:
    assert_required_files()
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

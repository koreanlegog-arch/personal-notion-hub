#!/usr/bin/env python3
"""Summarize PNH sensitive-owner readiness without printing private values."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def run_json(args: list[str]) -> tuple[dict[str, Any], str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return {}, "failed"
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}, "invalid_json"
    return parsed, "ok"


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def main() -> int:
    keychain, keychain_status = run_json(["python3", "scripts/keychain_readiness.py"])
    vault_secret, vault_secret_status = run_json(
        ["python3", "scripts/vault_secret_status.py", "--provider", "windows-dpapi-file"]
    )
    migration, migration_status = run_json(["python3", "scripts/plaintext_migration_audit.py"])
    inbox, inbox_status = run_json(["python3", "scripts/private_inbox_status.py"])

    keychain_ready = bool(nested(keychain, "keychainReadiness", "keychainStorageImplemented", default=False))
    recommended_mode = nested(keychain, "keychainReadiness", "recommendedMode", default="")
    vault_passphrase_stored = bool(nested(vault_secret, "vaultSecretStatus", "set", default=False))
    plaintext_rows = int(nested(migration, "plaintextMigrationAudit", "plaintextRowCount", default=0) or 0)
    encrypted_rows = int(nested(migration, "plaintextMigrationAudit", "encryptedRowCount", default=0) or 0)
    private_total = int(nested(inbox, "privateInbox", "totalCaptures", default=0) or 0)
    values_printed = any(
        [
            bool(nested(keychain, "keychainReadiness", "secretValuePrinted", default=False)),
            bool(nested(vault_secret, "vaultSecretStatus", "secretValuePrinted", default=False)),
            bool(nested(migration, "plaintextMigrationAudit", "valuesPrinted", default=False)),
            bool(inbox.get("privateValuesPrinted", False)),
        ]
    )

    blockers: list[str] = []
    if not keychain_ready:
        blockers.append("keychain_storage_not_ready")
    if recommended_mode != "windows-dpapi-file":
        blockers.append("windows_dpapi_file_not_recommended")
    if not vault_passphrase_stored:
        blockers.append("vault_passphrase_not_stored")
    if plaintext_rows:
        blockers.append("plaintext_inbox_rows_present")
    if values_printed:
        blockers.append("private_or_secret_value_printed")

    next_actions: list[str] = []
    if not vault_passphrase_stored:
        next_actions.append("Store vault passphrase locally with windows-dpapi-file using an interactive prompt.")
    if plaintext_rows:
        next_actions.append("Create an encrypted backup before any plaintext migration apply.")
        next_actions.append("Migrate or delete plaintext inbox rows before routine sensitive use.")
    if blockers:
        next_actions.append("Run this readiness check again and require verdict=ready_for_sensitive_local_owner_mode.")
    else:
        next_actions.append("Use encrypted vault mode for future sensitive local capture.")

    verdict = "ready_for_sensitive_local_owner_mode" if not blockers else "not_ready"
    payload = {
        "sensitiveOwnerReadiness": {
            "verdict": verdict,
            "commandStatus": {
                "keychain_readiness": keychain_status,
                "vault_secret_status": vault_secret_status,
                "plaintext_migration_audit": migration_status,
                "private_inbox_status": inbox_status,
            },
            "keychainReady": keychain_ready,
            "recommendedSecretMode": recommended_mode,
            "vaultPassphraseStored": vault_passphrase_stored,
            "plaintextInboxRows": plaintext_rows,
            "encryptedVaultRows": encrypted_rows,
            "privateInboxTotalCaptures": private_total,
            "privateOrSecretValuePrinted": values_printed,
            "blockers": blockers,
            "nextActions": next_actions,
            "secretValuePrinted": False,
        }
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not values_printed else 2


if __name__ == "__main__":
    raise SystemExit(main())

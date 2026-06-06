#!/usr/bin/env python3
"""Final privacy gate for first controlled real phone-adapter data run."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-REAL-DATA-PRIVACY-GATE-20260606" / "privacy_gate.json"


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    checks = {
        "sensitiveOwner": run_json(["scripts/sensitive_owner_readiness_check.py"]),
        "companionService": run_json(["scripts/pnh_companion_service_status.py"]),
        "schedulerService": run_json(["scripts/pnh_scheduler_service_status.py"]),
        "tailnetApi": run_json(["scripts/pnh_tailnet_companion_api_status.py"]),
        "privateInbox": run_json(["scripts/private_inbox_status.py", "--include-recent"]),
    }
    assertions = build_assertions(checks)
    blockers = [item for item in assertions if not item["pass"]]
    payload = {
        "pnhRealDataPrivacyGate": True,
        "generatedAt": utc_now(),
        "verdict": "ready_for_controlled_real_phone_adapter_run" if not blockers else "not_ready",
        "blockers": blockers,
        "assertions": assertions,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
        "checks": summarize_checks(checks),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "checks"} | {"out": safe_path_label(out)}, ensure_ascii=False, sort_keys=True))
    return 0 if not blockers else 2


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run([sys.executable, *command], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        return {
            "ok": False,
            "returnCode": result.returncode,
            "stdoutFirstLine": first_line(result.stdout),
            "stderrFirstLine": first_line(result.stderr),
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "returnCode": result.returncode, "stdoutFirstLine": first_line(result.stdout)}
    payload["ok"] = True
    return payload


def build_assertions(checks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    sensitive = checks["sensitiveOwner"].get("sensitiveOwnerReadiness", {})
    companion = checks["companionService"]
    scheduler = checks["schedulerService"]
    tailnet = checks["tailnetApi"]
    inbox = checks["privateInbox"].get("privateInbox", {})
    return [
        check("sensitive_owner_ready", sensitive.get("verdict") == "ready_for_sensitive_local_owner_mode"),
        check("plaintext_rows_zero", int(sensitive.get("plaintextInboxRows", -1)) == 0 and inbox.get("byStorageMode", {}).get("plaintext-inbox", -1) == 0),
        check("encrypted_vault_has_rows", int(sensitive.get("encryptedVaultRows", 0)) > 0),
        check("vault_passphrase_stored", sensitive.get("vaultPassphraseStored") is True),
        check("companion_service_active", companion.get("service", {}).get("active") == "active"),
        check("companion_encrypted_vault_health", companion.get("health", {}).get("ok") is True and companion.get("health", {}).get("encryptedVaultEnabled") is True),
        check("companion_browser_bridge_disabled", companion.get("health", {}).get("browserBridgeEnabled") is False),
        check("scheduler_timer_active", scheduler.get("timer", {}).get("active") == "active"),
        check("scheduler_runtime_output_exists", scheduler.get("runtimeOutExists") is True),
        check("tailnet_health_ok", tailnet.get("health", {}).get("ok") is True),
        check("tailnet_owner_path_available", tailnet.get("tailnetRunning") is True and tailnet.get("tailnetIpv4Set") is True),
        check("no_private_values_printed", no_private_values_printed(checks)),
        check("no_token_values_printed", no_token_values_printed(checks)),
    ]


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed)}


def no_private_values_printed(value: Any) -> bool:
    if isinstance(value, dict):
        return all(no_private_values_printed(item) for item in value.values()) and value.get("privateValuesPrinted", False) is not True
    if isinstance(value, list):
        return all(no_private_values_printed(item) for item in value)
    return True


def no_token_values_printed(value: Any) -> bool:
    if isinstance(value, dict):
        return all(no_token_values_printed(item) for item in value.values()) and value.get("tokenValuePrinted", False) is not True and value.get("secretValuePrinted", False) is not True
    if isinstance(value, list):
        return all(no_token_values_printed(item) for item in value)
    return True


def summarize_checks(checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "sensitiveOwnerVerdict": checks["sensitiveOwner"].get("sensitiveOwnerReadiness", {}).get("verdict", ""),
        "plaintextInboxRows": checks["sensitiveOwner"].get("sensitiveOwnerReadiness", {}).get("plaintextInboxRows", ""),
        "encryptedVaultRows": checks["sensitiveOwner"].get("sensitiveOwnerReadiness", {}).get("encryptedVaultRows", ""),
        "companionServiceActive": checks["companionService"].get("service", {}).get("active", ""),
        "companionEncryptedVaultEnabled": checks["companionService"].get("health", {}).get("encryptedVaultEnabled", ""),
        "schedulerTimerActive": checks["schedulerService"].get("timer", {}).get("active", ""),
        "tailnetRunning": checks["tailnetApi"].get("tailnetRunning", ""),
        "tailnetIpv4Set": checks["tailnetApi"].get("tailnetIpv4Set", ""),
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

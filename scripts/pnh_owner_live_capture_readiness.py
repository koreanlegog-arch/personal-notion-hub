#!/usr/bin/env python3
"""Assess readiness for a real owner live command capture session.

This script does not start the companion, expose a port, create external
records, or read private command bodies. It only checks metadata-safe local
state and writes a readiness packet.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-OWNER-LIVE-CAPTURE-READINESS-20260605" / "readiness.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess PNH owner live capture readiness.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    args = parser.parse_args()

    commands: list[dict[str, Any]] = []
    sensitive = run_json(["python3", "scripts/sensitive_owner_readiness_check.py"], "sensitive_owner", commands)
    inbox = run_json(["python3", "scripts/private_inbox_status.py"], "private_inbox", commands)
    queue = run_json(["python3", "scripts/pnh_unattended_dispatch_queue_plan.py"], "queue_plan", commands)
    reconciliation = run_json(["python3", "scripts/pnh_external_reconciliation_plan.py"], "reconciliation_plan", commands)
    dispatch = run_json(["python3", "scripts/pnh_dispatch_state_status.py", "--include-urls"], "dispatch_state", commands)
    lan = run_json(["python3", "scripts/phone_ingress_lan_info.py"], "phone_lan_info", commands)
    tailnet = tailnet_status()

    result = build_readiness(sensitive, inbox, queue, reconciliation, dispatch, lan, tailnet, commands)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0 if result["ownerLiveCaptureReadiness"]["verdict"] in {"ready_for_owner_action", "ready_for_local_only_owner_action"} else 2


def run_json(command: list[str], step: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    commands.append(
        {
            "step": step,
            "command": command,
            "returnCode": result.returncode,
            "stdoutBytes": len(result.stdout.encode("utf-8")),
            "stderrBytes": len(result.stderr.encode("utf-8")),
        }
    )
    if result.returncode != 0:
        return {"_commandFailed": True}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_invalidJson": True}
    return payload if isinstance(payload, dict) else {"_invalidJson": True}


def tailnet_status() -> dict[str, Any]:
    executable = shutil.which("powershell.exe")
    tailscale_windows_path = r"C:\Program Files\Tailscale\tailscale.exe"
    if not executable:
        return {
            "available": False,
            "backendState": "",
            "tailnetIpv4Set": False,
            "dnsNameSet": False,
            "secretValuePrinted": False,
        }
    script = (
        "$ErrorActionPreference='Stop'; "
        f"$exe='{tailscale_windows_path}'; "
        "if (-not (Test-Path -LiteralPath $exe)) { "
        "  [Console]::Out.Write('{\"available\":false}') "
        "} else { "
        "  $raw=& $exe status --json; "
        "  $obj=$raw | ConvertFrom-Json; "
        "  $ipSet=($obj.TailscaleIPs | Where-Object { $_ -like '100.*' } | Select-Object -First 1) -ne $null; "
        "  $dnsSet=[bool]$obj.Self.DNSName; "
        "  [PSCustomObject]@{available=$true; backendState=$obj.BackendState; tailnetIpv4Set=$ipSet; dnsNameSet=$dnsSet; secretValuePrinted=$false} | ConvertTo-Json -Compress "
        "}"
    )
    try:
        raw = subprocess.run(
            [executable, "-NoProfile", "-Command", script],
            capture_output=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "backendState": "", "tailnetIpv4Set": False, "dnsNameSet": False, "secretValuePrinted": False}
    if raw.returncode != 0:
        return {"available": False, "backendState": "", "tailnetIpv4Set": False, "dnsNameSet": False, "secretValuePrinted": False}
    try:
        payload = json.loads(raw.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"available": False, "backendState": "", "tailnetIpv4Set": False, "dnsNameSet": False, "secretValuePrinted": False}
    return payload if isinstance(payload, dict) else {"available": False, "backendState": "", "tailnetIpv4Set": False, "dnsNameSet": False, "secretValuePrinted": False}


def build_readiness(
    sensitive: dict[str, Any],
    inbox: dict[str, Any],
    queue: dict[str, Any],
    reconciliation: dict[str, Any],
    dispatch: dict[str, Any],
    lan: dict[str, Any],
    tailnet: dict[str, Any],
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    sensitive_payload = nested(sensitive, "sensitiveOwnerReadiness", default={})
    inbox_payload = nested(inbox, "privateInbox", default={})
    lan_payload = nested(lan, "phoneIngressLanInfo", default={})

    checks = [
        check("sensitive_owner_ready", sensitive_payload.get("verdict") == "ready_for_sensitive_local_owner_mode"),
        check("encrypted_vault_enabled", bool(inbox_payload.get("encryptedVaultEnabled"))),
        check("no_plaintext_inbox_rows", int(nested(inbox_payload, "byStorageMode", "plaintext-inbox", default=0) or 0) == 0),
        check("queue_currently_empty", int(queue.get("queuedCount", 0) or 0) == 0),
        check("no_pending_external_reconciliation", int(reconciliation.get("plannedExternalWriteCount", 0) or 0) == 0),
        check("dispatch_state_available", bool(dispatch.get("dispatchStateStatus"))),
        check("owner_only_access_path_available", bool(lan_payload.get("safePhoneUrls")) or bool(tailnet.get("tailnetIpv4Set"))),
        check("secret_values_not_printed", not any_secret_or_private_printed(sensitive, inbox, queue, reconciliation, dispatch, lan, tailnet)),
    ]
    failed = [item for item in checks if not item["pass"]]
    tailnet_ready = bool(tailnet.get("available")) and str(tailnet.get("backendState", "")).lower() == "running" and bool(tailnet.get("tailnetIpv4Set"))
    lan_ready = bool(lan_payload.get("safePhoneUrls"))
    access_mode = "tailnet" if tailnet_ready else "private_lan" if lan_ready else "local_only"
    if failed and failed != [item for item in checks if item["name"] == "owner_only_access_path_available" and not item["pass"]]:
        verdict = "not_ready"
    elif access_mode == "local_only":
        verdict = "ready_for_local_only_owner_action"
    else:
        verdict = "ready_for_owner_action"
    return {
        "ownerLiveCaptureReadiness": {
            "generatedAt": utc_now(),
            "verdict": verdict,
            "accessMode": access_mode,
            "checks": checks,
            "failedChecks": failed,
            "privateInbox": {
                "totalCaptures": inbox_payload.get("totalCaptures", 0),
                "storageModeCounts": inbox_payload.get("byStorageMode", {}),
                "statusCounts": inbox_payload.get("byStatus", {}),
            },
            "dispatch": {
                "totalRecords": dispatch.get("totalRecords", 0),
                "githubLinked": dispatch.get("githubLinked", 0),
                "discordLinked": dispatch.get("discordLinked", 0),
                "workerResults": dispatch.get("workerResults", 0),
            },
            "phoneAccess": {
                "safePhoneUrlCount": len(lan_payload.get("safePhoneUrls", [])) if isinstance(lan_payload.get("safePhoneUrls"), list) else 0,
                "tailnetAvailable": bool(tailnet.get("available")),
                "tailnetRunning": str(tailnet.get("backendState", "")).lower() == "running",
                "tailnetIpv4Set": bool(tailnet.get("tailnetIpv4Set")),
                "tailnetDnsNameSet": bool(tailnet.get("dnsNameSet")),
            },
            "nextOperatorAction": next_operator_action(access_mode),
            "materialGateReached": True,
            "materialGateReason": (
                "The next step requires the human owner to pair a browser session and enter real private command content. "
                "Codex must not receive or print the pairing code, session token, or raw private body."
            ),
            "commandsRun": commands,
            "externalWritesPerformed": False,
            "privateValuesPrinted": False,
            "secretValuePrinted": False,
        }
    }


def next_operator_action(access_mode: str) -> str:
    if access_mode == "tailnet":
        return "Start the approved tailnet session, pair locally, enter the owner command in the phone browser, then run the single command packet wrapper."
    if access_mode == "private_lan":
        return "Start the encrypted phone-ingress companion on the trusted private LAN, pair locally, enter the owner command, then run the single command packet wrapper."
    return "Use the local browser companion flow on this machine, pair locally, enter the owner command, then run the single command packet wrapper."


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed)}


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def any_secret_or_private_printed(*payloads: dict[str, Any]) -> bool:
    text = json.dumps(payloads, ensure_ascii=False)
    return any(
        marker in text
        for marker in (
            '"privateValuesPrinted": true',
            '"secretValuePrinted": true',
            '"tokenValuePrinted": true',
            '"privateOrSecretValuePrinted": true',
        )
    )


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    payload = result["ownerLiveCaptureReadiness"]
    return {
        "ownerLiveCaptureReadiness": True,
        "verdict": payload["verdict"],
        "accessMode": payload["accessMode"],
        "out": safe_path_label(out_path),
        "materialGateReached": payload["materialGateReached"],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "secretValuePrinted": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Report PNH companion user service status and loopback health."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request


SERVICE_NAME = "pnh-companion.service"
HEALTH_URL = "http://127.0.0.1:8765/api/health"


def main() -> int:
    health = companion_health()
    payload = {
        "pnhCompanionServiceStatus": True,
        "systemctlUserAvailable": command_ok(["systemctl", "--user", "show-environment"]),
        "service": systemctl_state(SERVICE_NAME),
        "healthUrl": "http://127.0.0.1:8765/api/health",
        "health": health,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if health.get("ok") is True else 1


def companion_health() -> dict[str, object]:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {
                "ok": bool(payload.get("ok")),
                "status": response.status,
                "storageMode": payload.get("storageMode", ""),
                "encryptedVaultEnabled": bool(payload.get("encryptedVault", {}).get("enabled")),
                "browserBridgeEnabled": bool(payload.get("browserBridge", {}).get("enabled")),
            }
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": exc.__class__.__name__}


def systemctl_state(unit: str) -> dict[str, object]:
    if not command_ok(["systemctl", "--user", "show-environment"]):
        return {"unit": unit, "available": False, "active": "unknown", "enabled": "unknown"}
    return {
        "unit": unit,
        "available": True,
        "active": command_output(["systemctl", "--user", "is-active", unit]),
        "enabled": command_output(["systemctl", "--user", "is-enabled", unit]),
    }


def command_ok(command: list[str]) -> bool:
    return subprocess.run(command, capture_output=True, text=True, check=False).returncode == 0


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else "unknown"


if __name__ == "__main__":
    raise SystemExit(main())

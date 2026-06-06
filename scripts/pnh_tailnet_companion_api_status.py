#!/usr/bin/env python3
"""Report owner-only tailnet forwarding status for the PNH companion API."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any


TAILSCALE_EXE = r"C:\Program Files\Tailscale\tailscale.exe"
PORT = 8765


def main() -> int:
    tailnet = tailscale_status()
    url = f"http://{tailnet.get('tailnetIpv4', '')}:{PORT}/api/health" if tailnet.get("tailnetIpv4") else ""
    health = fetch_health(url) if url else {"ok": False, "error": "tailnet_ip_missing"}
    payload = {
        "pnhTailnetCompanionApiStatus": True,
        "tailscaleAvailable": tailnet["available"],
        "tailnetRunning": tailnet["running"],
        "tailnetIpv4Set": bool(tailnet.get("tailnetIpv4")),
        "tailnetUrl": f"http://{tailnet.get('tailnetIpv4')}:{PORT}/" if tailnet.get("tailnetIpv4") else "",
        "health": health,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if health.get("ok") is True else 1


def tailscale_status() -> dict[str, Any]:
    script = f"& '{TAILSCALE_EXE}' status --json"
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        return {"available": False, "running": False, "tailnetIpv4": ""}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"available": False, "running": False, "tailnetIpv4": ""}
    tailnet_ip = ""
    for item in payload.get("TailscaleIPs", []):
        if isinstance(item, str) and item.startswith("100."):
            tailnet_ip = item
            break
    return {
        "available": True,
        "running": str(payload.get("BackendState", "")).lower() == "running",
        "tailnetIpv4": tailnet_ip,
    }


def fetch_health(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {
                "ok": bool(payload.get("ok")),
                "status": response.status,
                "storageMode": payload.get("storageMode", ""),
                "encryptedVaultEnabled": bool(payload.get("encryptedVault", {}).get("enabled")),
            }
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": exc.__class__.__name__}


if __name__ == "__main__":
    raise SystemExit(main())

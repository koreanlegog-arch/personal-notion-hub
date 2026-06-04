#!/usr/bin/env python3
"""Diagnose WSL/Windows reachability for PNH phone ingress without secrets."""

from __future__ import annotations

import json
import socket
import subprocess
from ipaddress import ip_address


PORT = 8765


def run(args: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
    raw = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    return subprocess.CompletedProcess(
        args=raw.args,
        returncode=raw.returncode,
        stdout=raw.stdout.decode("utf-8", errors="replace"),
        stderr=raw.stderr.decode("utf-8", errors="replace"),
    )


def private_ip(value: str) -> bool:
    try:
        parsed = ip_address(value)
    except ValueError:
        return False
    return parsed.version == 4 and parsed.is_private and not parsed.is_loopback


def public_ip(value: str) -> bool:
    try:
        parsed = ip_address(value)
    except ValueError:
        return False
    return parsed.version == 4 and not parsed.is_private and not parsed.is_loopback


def wsl_ips() -> list[str]:
    result = run(["hostname", "-I"])
    return [token for token in result.stdout.split() if token.count(".") == 3]


def windows_ipv4s() -> list[dict[str, object]]:
    command = (
        "Get-NetIPConfiguration | ForEach-Object { "
        "$ip=$_.IPv4Address.IPAddress; "
        "if ($ip) { [PSCustomObject]@{InterfaceAlias=$_.InterfaceAlias; IPv4Address=$ip; PrefixLength=$_.IPv4Address.PrefixLength} } "
        "} | ConvertTo-Json -Compress"
    )
    result = run(["powershell.exe", "-NoProfile", "-Command", command])
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        parsed = [parsed]
    return [item for item in parsed if isinstance(item, dict)]


def phone_reachable_interface(item: dict[str, object]) -> bool:
    alias = str(item.get("InterfaceAlias", "")).lower()
    if "wsl" in alias or "vethernet" in alias or "hyper-v" in alias:
        return False
    return private_ip(str(item.get("IPv4Address", "")))


def windows_localhost_status() -> str:
    command = (
        f"try {{ (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:{PORT}/api/health).StatusCode }} "
        "catch { 'blocked' }"
    )
    result = run(["powershell.exe", "-NoProfile", "-Command", command])
    return result.stdout.strip() or "unknown"


def windows_ip_status(ip: str) -> str:
    command = (
        f"try {{ (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://{ip}:{PORT}/api/health).StatusCode }} "
        "catch { 'blocked' }"
    )
    result = run(["powershell.exe", "-NoProfile", "-Command", command])
    return result.stdout.strip() or "unknown"


def portproxy_rules() -> str:
    result = run(["powershell.exe", "-NoProfile", "-Command", "netsh interface portproxy show v4tov4"])
    return "\n".join(line.rstrip() for line in result.stdout.splitlines() if line.strip())


def listening_in_wsl() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=2):
            return True
    except OSError:
        return False


def main() -> int:
    wsl = wsl_ips()
    windows = windows_ipv4s()
    private_windows = [item for item in windows if phone_reachable_interface(item)]
    internal_windows = [
        item
        for item in windows
        if private_ip(str(item.get("IPv4Address", ""))) and not phone_reachable_interface(item)
    ]
    public_windows = [item for item in windows if public_ip(str(item.get("IPv4Address", "")))]
    safe_urls = [f"http://{item['IPv4Address']}:{PORT}/" for item in private_windows]
    first_wsl_ip = next((ip for ip in wsl if private_ip(ip)), "")
    portproxy_examples = []
    for item in private_windows:
        ip = item["IPv4Address"]
        portproxy_examples.append(
            {
                "listenAddress": ip,
                "addPortProxy": (
                    f"netsh interface portproxy add v4tov4 listenaddress={ip} listenport={PORT} "
                    f"connectaddress={first_wsl_ip or '<WSL_IP>'} connectport={PORT}"
                ),
                "addFirewallRule": (
                    "New-NetFirewallRule -DisplayName \"PNH Phone Ingress 8765\" "
                    f"-Direction Inbound -Action Allow -Protocol TCP -LocalAddress {ip} -LocalPort {PORT}"
                ),
                "allowedOrigin": f"http://{ip}:{PORT}",
                "phoneUrl": f"http://{ip}:{PORT}/",
            }
        )

    payload = {
        "phoneIngressReachability": {
            "wslListeningOnPort": listening_in_wsl(),
            "wslIpv4": wsl,
            "windowsIpv4": windows,
            "windowsLocalhostStatus": windows_localhost_status(),
            "windowsIpStatus": [
                {"ip": item.get("IPv4Address"), "status": windows_ip_status(str(item.get("IPv4Address")))}
                for item in windows
            ],
            "safePhoneUrls": safe_urls,
            "internalPrivateIpsNotPhoneReachable": internal_windows,
            "publicWindowsIpsRejectedByPolicy": public_windows,
            "portproxyRulesPresent": bool(portproxy_rules()),
            "portproxyRulesSummary": "[present]" if portproxy_rules() else "[none]",
            "adminCommandExamplesForPrivateIpsOnly": portproxy_examples,
            "verdict": "ready_for_private_lan_portproxy" if safe_urls else "blocked_no_phone_reachable_private_windows_lan_ip",
            "secretValuePrinted": False,
        }
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

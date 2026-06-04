#!/usr/bin/env python3
"""Print non-secret LAN candidates and phone ingress commands.

On WSL, `hostname -I` often returns a WSL NAT address that is private but not
reachable from a phone. Prefer Windows non-WSL private LAN addresses when
PowerShell is available.
"""

from __future__ import annotations

import json
import socket
import subprocess
from ipaddress import ip_address


PORT = 8765


def private_ipv4_candidates() -> list[str]:
    candidates: set[str] = set()
    try:
        output = subprocess.run(
            ["hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
        for token in output.split():
            add_candidate(candidates, token)
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        hostname = socket.gethostname()
        for _family, _type, _proto, _canon, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_INET):
            add_candidate(candidates, sockaddr[0])
    except OSError:
        pass
    return sorted(candidates)


def run(args: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
    raw = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    return subprocess.CompletedProcess(
        args=raw.args,
        returncode=raw.returncode,
        stdout=raw.stdout.decode("utf-8", errors="replace"),
        stderr=raw.stderr.decode("utf-8", errors="replace"),
    )


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


def phone_reachable_windows_private(item: dict[str, object]) -> bool:
    alias = str(item.get("InterfaceAlias", "")).lower()
    if "wsl" in alias or "vethernet" in alias or "hyper-v" in alias:
        return False
    return is_private_ipv4(str(item.get("IPv4Address", "")))


def is_private_ipv4(value: str) -> bool:
    try:
        parsed = ip_address(value)
    except ValueError:
        return False
    return parsed.version == 4 and parsed.is_private and not parsed.is_loopback


def add_candidate(candidates: set[str], value: str) -> None:
    if is_private_ipv4(value):
        candidates.add(value)


def main() -> int:
    wsl_candidates = private_ipv4_candidates()
    windows_ips = windows_ipv4s()
    windows_private_candidates = [
        str(item.get("IPv4Address"))
        for item in windows_ips
        if phone_reachable_windows_private(item)
    ]
    candidate_source = "windows_private_lan" if windows_private_candidates else "none"
    payload = {
        "phoneIngressLanInfo": {
            "candidateLanIps": windows_private_candidates,
            "candidateSource": candidate_source,
            "wslPrivateIpsNotPhoneReachableByDefault": wsl_candidates,
            "windowsIpv4": windows_ips,
            "safePhoneUrls": [f"http://{ip}:{PORT}/" for ip in windows_private_candidates],
            "secretValuePrinted": False,
            "exampleCompanionCommand": (
                "python3 companion/server.py --host 0.0.0.0 --port 8765 "
                "--enable-private-inbox --enable-browser-bridge --enable-phone-ingress "
                "--allowed-origin http://<LAN_IP>:8765"
            ),
            "examplePhoneUrl": "http://<LAN_IP>:8765/",
            "notes": [
                "Use only a phone-reachable Windows private LAN IP from the candidate list.",
                "WSL NAT addresses are private but usually not reachable from a phone.",
                "Do not use 0.0.0.0 in the phone browser URL or allowed origin.",
                "Use synthetic or low-risk data until encrypted vault mode is enabled and verified.",
            ],
        }
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

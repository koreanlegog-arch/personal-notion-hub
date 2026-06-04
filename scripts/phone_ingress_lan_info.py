#!/usr/bin/env python3
"""Print non-secret LAN candidates and phone ingress commands."""

from __future__ import annotations

import json
import socket
import subprocess
from ipaddress import ip_address


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


def add_candidate(candidates: set[str], value: str) -> None:
    try:
        parsed = ip_address(value)
    except ValueError:
        return
    if parsed.version == 4 and parsed.is_private and not parsed.is_loopback:
        candidates.add(str(parsed))


def main() -> int:
    candidates = private_ipv4_candidates()
    payload = {
        "phoneIngressLanInfo": {
            "candidateLanIps": candidates,
            "secretValuePrinted": False,
            "exampleCompanionCommand": (
                "python3 companion/server.py --host 0.0.0.0 --port 8765 "
                "--enable-private-inbox --enable-browser-bridge --enable-phone-ingress "
                "--allowed-origin http://<LAN_IP>:8765"
            ),
            "examplePhoneUrl": "http://<LAN_IP>:8765/",
            "notes": [
                "Use a private LAN IP from the candidate list.",
                "Do not use 0.0.0.0 in the phone browser URL or allowed origin.",
                "Use synthetic or low-risk data until encrypted vault mode is enabled and verified.",
            ],
        }
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

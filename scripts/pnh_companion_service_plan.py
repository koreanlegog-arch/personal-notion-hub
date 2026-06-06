#!/usr/bin/env python3
"""Plan PNH headless companion user-systemd service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_NAME = "pnh-companion.service"
RUNTIME_SCRIPT = ROOT / "scripts" / "pnh_companion_runtime_server.sh"
SERVICE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/mnt/c/Windows/System32/WindowsPowerShell/v1.0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan PNH headless companion service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    service_text = build_service(args.host, args.port)
    payload = {
        "pnhCompanionServicePlan": True,
        "serviceName": SERVICE_NAME,
        "host": args.host,
        "port": int(args.port),
        "runtimeScript": safe_path_label(RUNTIME_SCRIPT),
        "browserBridgeEnabled": False,
        "pairingCodePrinted": False,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "serviceText": service_text,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_service(host: str, port: int) -> str:
    return "\n".join(
        [
            "[Unit]",
            "Description=Personal Notion Hub headless private companion API",
            "Documentation=file:%s" % (ROOT / "docs" / "LOCAL_COMPANION_ARCHITECTURE.md"),
            "After=default.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={ROOT}",
            f"Environment=PNH_COMPANION_HOST={host}",
            f"Environment=PNH_COMPANION_PORT={int(port)}",
            "Environment=PNH_VAULT_PASSPHRASE_PROVIDER=windows-dpapi-file",
            "Environment=PNH_VAULT_PASSPHRASE_NAME=vault-passphrase",
            f"Environment=PATH={SERVICE_PATH}",
            f"ExecStart=/bin/bash {RUNTIME_SCRIPT}",
            "Restart=on-failure",
            "RestartSec=5s",
            "PrivateTmp=true",
            "NoNewPrivileges=true",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())

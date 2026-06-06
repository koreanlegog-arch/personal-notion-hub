#!/usr/bin/env python3
"""Run guarded live private data adapter readiness or sync in batch."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.pnh_live_private_data_adapter_sync import LIVE_ADAPTERS  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-LIVE-PRIVATE-DATA-ADAPTER-20260606" / "live_adapter_batch_sync.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live private data adapter readiness/sync in batch.")
    parser.add_argument("--adapters", default=",".join(sorted(LIVE_ADAPTERS)), help="Comma-separated live adapter names.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum records per adapter.")
    parser.add_argument("--timeout-seconds", type=int, default=15, help="HTTP timeout for live fetch.")
    parser.add_argument("--fetch", action="store_true", help="Fetch configured live adapters without writing.")
    parser.add_argument("--apply", action="store_true", help="Fetch configured live adapters and write encrypted vault rows.")
    parser.add_argument("--approve-live-adapter", action="store_true", help="Required for live fetch/apply.")
    parser.add_argument("--vault-passphrase-env", default="", help="Optional passphrase env var.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Passphrase provider such as windows-dpapi-file.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider secret file path.")
    args = parser.parse_args()

    selected = parse_adapters(args.adapters)
    results = []
    for adapter in selected:
        results.append(run_adapter(adapter, args))

    payload = {
        "pnhLivePrivateDataAdapterBatchSync": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "fetch" if args.fetch else "readiness",
        "adapterCount": len(results),
        "failedAdapters": [item for item in results if item["returnCode"] != 0],
        "recordsParsed": sum(int(item.get("recordsParsed", 0)) for item in results),
        "recordsWritten": sum(int(item.get("recordsWritten", 0)) for item in results),
        "externalServicesContacted": any(bool(item.get("externalServicesContacted")) for item in results),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "results": results,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**payload, "results": results[:4], "out": safe_path_label(out_path)}, ensure_ascii=False, sort_keys=True))
    return 0 if not payload["failedAdapters"] else 2


def parse_adapters(value: str) -> list[str]:
    names = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in names if item not in LIVE_ADAPTERS]
    if unknown:
        raise SystemExit(f"unknown_live_adapters={','.join(unknown)}")
    return names


def run_adapter(adapter: str, args: argparse.Namespace) -> dict[str, Any]:
    out_path = Path(args.out).with_name(f"live_adapter_{safe_file_stem(adapter)}.json")
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_live_private_data_adapter_sync.py"),
        "--adapter",
        adapter,
        "--out",
        str(out_path),
        "--limit",
        str(args.limit),
        "--timeout-seconds",
        str(args.timeout_seconds),
    ]
    if args.fetch:
        command.append("--fetch")
    if args.apply:
        command.append("--apply")
    if args.approve_live_adapter:
        command.append("--approve-live-adapter")
    if args.vault_passphrase_env:
        command.extend(["--vault-passphrase-env", args.vault_passphrase_env])
    if args.prompt_vault_passphrase:
        command.append("--prompt-vault-passphrase")
    if args.vault_passphrase_provider:
        command.extend(["--vault-passphrase-provider", args.vault_passphrase_provider])
    if args.vault_passphrase_name:
        command.extend(["--vault-passphrase-name", args.vault_passphrase_name])
    if args.vault_passphrase_file:
        command.extend(["--vault-passphrase-file", args.vault_passphrase_file])

    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
    parsed = parse_stdout(result.stdout)
    return {
        "adapter": adapter,
        "returnCode": result.returncode,
        "status": "ok" if result.returncode == 0 else "failed",
        "urlEnv": LIVE_ADAPTERS[adapter]["urlEnv"],
        "urlSet": bool(parsed.get("urlSet", False)),
        "tokenEnv": LIVE_ADAPTERS[adapter]["tokenEnv"],
        "tokenSet": bool(parsed.get("tokenSet", False)),
        "recordsParsed": int(parsed.get("recordsParsed", 0)),
        "recordsWritten": int(parsed.get("recordsWritten", 0)),
        "externalServicesContacted": bool(parsed.get("externalServicesContacted", False)),
        "out": safe_path_label(out_path),
        "stdoutFirstLine": first_line(result.stdout),
        "stderrFirstLine": first_line(result.stderr),
    }


def parse_stdout(value: str) -> dict[str, Any]:
    first = first_line(value)
    if not first.startswith("{"):
        return {}
    try:
        payload = json.loads(first)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def first_line(value: str) -> str:
    return value.strip().splitlines()[0][:240] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def safe_file_stem(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_") or "adapter"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

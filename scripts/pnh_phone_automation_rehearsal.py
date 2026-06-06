#!/usr/bin/env python3
"""Run a synthetic phone automation POST rehearsal.

The rehearsal sends one synthetic phone adapter payload through the configured
companion endpoint and records metadata-only evidence. It never prints bearer
token values, private payload values, or exact tailnet URLs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.phone_adapter_ingest import PHONE_ADAPTERS  # noqa: E402
from companion.private_store import DEFAULT_TOKEN_PATH  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-REHEARSAL-20260606" / "phone_automation_rehearsal.json"


class RehearsalError(ValueError):
    """Raised when phone automation rehearsal cannot proceed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a synthetic PNH phone automation rehearsal.")
    parser.add_argument("--adapter", default="phone-call-log-json", choices=sorted(PHONE_ADAPTERS), help="Phone adapter.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765", help="Companion base URL.")
    parser.add_argument("--use-tailnet", action="store_true", help="Use current owner tailnet URL from status command.")
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_PATH), help="Bearer token file.")
    parser.add_argument("--allow-owner-network", action="store_true", help="Allow owner LAN/tailnet URL.")
    parser.add_argument("--allow-external-token-file", action="store_true", help="Allow external token file in fixture tests.")
    parser.add_argument("--skip-inbox-delta", action="store_true", help="Skip default private inbox before/after count check.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    try:
        base_url, base_url_mode = resolve_base_url(args)
        before = inbox_count() if not args.skip_inbox_delta else None
        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "phone_payload.json"
            run_template(args.adapter, payload_path)
            send_result = run_send(args, base_url, payload_path)
        after = inbox_count() if not args.skip_inbox_delta else None
        result = build_result(args, base_url_mode, send_result, before, after)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, RehearsalError) as exc:
        print(f"pnh_phone_automation_rehearsal=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0 if result["success"] else 1


def resolve_base_url(args: argparse.Namespace) -> tuple[str, str]:
    if not args.use_tailnet:
        return args.base_url, "loopback" if args.base_url.startswith("http://127.0.0.1:") else "owner_network"
    result = subprocess.run(
        [sys.executable, "scripts/pnh_tailnet_companion_api_status.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RehearsalError("tailnet status is not ready")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RehearsalError(f"tailnet status returned invalid JSON: {exc.msg}") from exc
    url = str(payload.get("tailnetUrl") or "").strip()
    if not url:
        raise RehearsalError("tailnet URL is unavailable")
    return url.rstrip("/"), "owner_tailnet"


def run_template(adapter: str, payload_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/pnh_phone_adapter_payload_template.py",
            "--adapter",
            adapter,
            "--out",
            str(payload_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        raise RehearsalError(first_line(result.stderr) or "payload template failed")


def run_send(args: argparse.Namespace, base_url: str, payload_path: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/pnh_phone_adapter_send.py",
        "--base-url",
        base_url,
        "--token-file",
        args.token_file,
        "--payload",
        str(payload_path),
    ]
    if args.allow_owner_network or args.use_tailnet or not base_url.startswith("http://127.0.0.1:"):
        command.append("--allow-owner-network")
    if args.allow_external_token_file:
        command.append("--allow-external-token-file")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RehearsalError(first_line(result.stderr) or first_line(result.stdout) or "phone adapter send failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RehearsalError(f"phone adapter send returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise RehearsalError("phone adapter send returned non-object JSON")
    return payload


def inbox_count() -> int:
    result = subprocess.run(
        [sys.executable, "scripts/private_inbox_status.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        raise RehearsalError(first_line(result.stderr) or "private inbox status failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RehearsalError(f"private inbox status returned invalid JSON: {exc.msg}") from exc
    return int(payload.get("privateInbox", {}).get("totalCaptures") or 0)


def build_result(
    args: argparse.Namespace,
    base_url_mode: str,
    send_result: dict[str, Any],
    before: int | None,
    after: int | None,
) -> dict[str, Any]:
    records_accepted = int(send_result.get("recordsAccepted") or 0)
    delta = None if before is None or after is None else after - before
    success = bool(send_result.get("pnhPhoneAdapterSend")) and records_accepted > 0
    if delta is not None:
        success = success and delta >= records_accepted
    return {
        "pnhPhoneAutomationRehearsal": True,
        "success": success,
        "adapter": args.adapter,
        "baseUrlMode": base_url_mode,
        "recordsAccepted": records_accepted,
        "captureIds": send_result.get("captureIds", []),
        "inboxCountBefore": before,
        "inboxCountAfter": after,
        "inboxCountDelta": delta,
        "payloadSynthetic": True,
        "externalServicesContacted": base_url_mode == "owner_tailnet",
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
    }


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhPhoneAutomationRehearsal": True,
        "success": result["success"],
        "adapter": result["adapter"],
        "baseUrlMode": result["baseUrlMode"],
        "recordsAccepted": result["recordsAccepted"],
        "inboxCountDelta": result["inboxCountDelta"],
        "out": safe_path_label(out_path),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
    }


def first_line(value: str) -> str:
    return value.strip().splitlines()[0][:240] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())

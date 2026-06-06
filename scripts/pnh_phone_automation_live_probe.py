#!/usr/bin/env python3
"""Probe whether phone automation input reached the encrypted private vault.

The probe reads metadata only. It does not decrypt encrypted captures, does not
read private bodies, and does not print tokens or owner network URLs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, list_captures, store_summary  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-LIVE-PROBE-20260606" / "live_probe.json"
PHONE_SOURCE_PREFIX = "phone_"


class LiveProbeError(ValueError):
    """Raised when phone automation live probe cannot proceed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe PNH phone automation encrypted-vault ingress.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox DB path.")
    parser.add_argument("--baseline-count", type=int, default=None, help="Expected total count before owner send.")
    parser.add_argument("--timeout-seconds", type=float, default=0.0, help="Wait up to this many seconds for a new capture.")
    parser.add_argument("--poll-seconds", type=float, default=2.0, help="Polling interval while waiting.")
    parser.add_argument("--source-prefix", default=PHONE_SOURCE_PREFIX, help="Required phone source prefix.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow fixture DB path outside companion/private.")
    parser.add_argument("--allow-plaintext", action="store_true", help="Allow plaintext rows for fixture diagnostics.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    args = parser.parse_args()

    try:
        result = probe(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PrivateStoreError, LiveProbeError) as exc:
        print(f"pnh_phone_automation_live_probe=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps(redact_stdout(result, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0 if result["success"] else 1


def probe(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db)
    timeout_seconds = max(float(args.timeout_seconds), 0.0)
    poll_seconds = min(max(float(args.poll_seconds), 0.25), 10.0)
    baseline_count = args.baseline_count
    if baseline_count is not None and baseline_count < 0:
        raise LiveProbeError("baseline count must be zero or greater")

    deadline = time.monotonic() + timeout_seconds
    observations: list[dict[str, Any]] = []
    while True:
        observation = observe(
            db_path,
            baseline_count=baseline_count,
            source_prefix=args.source_prefix,
            allow_external=args.allow_external_db,
            allow_plaintext=args.allow_plaintext,
        )
        observations.append(observation)
        if observation["success"] or timeout_seconds <= 0 or time.monotonic() >= deadline:
            return {
                **observation,
                "mode": "wait" if timeout_seconds > 0 else "status",
                "timeoutSeconds": timeout_seconds,
                "pollSeconds": poll_seconds,
                "observationCount": len(observations),
                "privateValuesPrinted": False,
                "tokenValuePrinted": False,
                "baseUrlValuePrinted": False,
                "rawPrivateBodyRead": False,
                "messageContentStored": False,
            }
        time.sleep(poll_seconds)


def observe(
    db_path: Path,
    *,
    baseline_count: int | None,
    source_prefix: str,
    allow_external: bool,
    allow_plaintext: bool,
) -> dict[str, Any]:
    summary = store_summary(db_path, create_if_missing=False, allow_external=allow_external)
    captures = list_captures(
        db_path,
        limit=50,
        include_body=False,
        create_if_missing=False,
        allow_external=allow_external,
    )
    current_count = int(summary.get("totalCaptures") or 0)
    latest_phone = latest_phone_capture(captures, source_prefix)
    delta = None if baseline_count is None else current_count - baseline_count
    encrypted_ready = bool(latest_phone and latest_phone["storageMode"] == "encrypted-vault" and latest_phone["encrypted"])
    plaintext_allowed = bool(allow_plaintext and latest_phone and latest_phone["storageMode"] == "plaintext-inbox")
    encrypted_or_allowed = encrypted_ready or plaintext_allowed

    if baseline_count is None:
        success = bool(latest_phone and encrypted_or_allowed)
        verdict = "latest_phone_capture_available" if success else "no_phone_capture_detected"
    else:
        success = bool(delta is not None and delta > 0 and latest_phone and encrypted_or_allowed)
        if success:
            verdict = "new_phone_capture_detected"
        elif delta is not None and delta > 0 and not latest_phone:
            verdict = "new_capture_detected_but_not_phone_source"
        elif latest_phone and not encrypted_or_allowed:
            verdict = "phone_capture_detected_but_not_encrypted"
        else:
            verdict = "waiting_or_no_new_capture"

    return {
        "pnhPhoneAutomationLiveProbe": True,
        "success": success,
        "verdict": verdict,
        "sourcePrefix": source_prefix,
        "baselineCount": baseline_count,
        "currentCount": current_count,
        "delta": delta,
        "byStorageMode": summary.get("byStorageMode", {}),
        "latestPhoneCapture": sanitize_capture(latest_phone),
        "requireEncryptedVault": not allow_plaintext,
    }


def latest_phone_capture(captures: list[dict[str, Any]], source_prefix: str) -> dict[str, Any] | None:
    for capture in captures:
        source = str(capture.get("source") or "")
        if source.startswith(source_prefix):
            return capture
    return None


def sanitize_capture(capture: dict[str, Any] | None) -> dict[str, Any] | None:
    if capture is None:
        return None
    return {
        "id": capture.get("id"),
        "source": capture.get("source"),
        "kind": capture.get("kind"),
        "sensitivity": capture.get("sensitivity"),
        "status": capture.get("status"),
        "createdAt": capture.get("createdAt"),
        "storedAt": capture.get("storedAt"),
        "storageMode": capture.get("storageMode"),
        "encrypted": bool(capture.get("encrypted")),
        "title": "[encrypted]" if capture.get("encrypted") else "[redacted]",
    }


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    latest = result.get("latestPhoneCapture") or {}
    return {
        "pnhPhoneAutomationLiveProbe": True,
        "success": result["success"],
        "verdict": result["verdict"],
        "mode": result["mode"],
        "baselineCount": result["baselineCount"],
        "currentCount": result["currentCount"],
        "delta": result["delta"],
        "latestPhoneCaptureId": latest.get("id"),
        "latestPhoneCaptureSource": latest.get("source"),
        "latestPhoneCaptureStorageMode": latest.get("storageMode"),
        "out": safe_path_label(out_path),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())

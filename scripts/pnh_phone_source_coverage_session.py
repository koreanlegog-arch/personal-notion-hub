#!/usr/bin/env python3
"""Verify phone adapter source coverage without reading private bodies.

By default, this script only summarizes recent source coverage. With
``--rehearse-missing`` it sends synthetic payloads for missing phone adapter
sources through the existing rehearsal path, then rechecks metadata-only
coverage. It never prints bearer token values, exact owner-network URLs, or
private payload values.
"""

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

from scripts.pnh_phone_capture_recent_summary import summarize as summarize_recent  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PHONE-SOURCE-COVERAGE-SESSION-20260606" / "phone_source_coverage_session.json"

SOURCE_TO_ADAPTER = {
    "phone_contacts": "phone-contacts-json",
    "phone_calendar": "phone-calendar-json",
    "phone_call_log": "phone-call-log-json",
    "phone_recording": "phone-recording-transcript-json",
}


class SourceCoverageError(ValueError):
    """Raised when phone source coverage cannot be assessed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PNH phone source coverage session.")
    parser.add_argument("--db", default="", help="Private inbox DB path. Defaults to project private DB.")
    parser.add_argument("--limit", type=int, default=50, help="Recent captures to inspect.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow fixture DB outside companion/private.")
    parser.add_argument("--rehearse-missing", action="store_true", help="Send synthetic payloads for missing phone sources.")
    parser.add_argument("--use-tailnet", action="store_true", help="Use owner tailnet for synthetic rehearsals.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765", help="Loopback/owner endpoint for rehearsals.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    try:
        payload = run_session(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, SourceCoverageError) as exc:
        print(f"pnh_phone_source_coverage_session=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps(redact_stdout(payload, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0 if payload["success"] else 1


def run_session(args: argparse.Namespace) -> dict[str, Any]:
    before = run_summary(args)
    rehearsals = []
    missing_before = list(before.get("missingPhoneSourcesInRecentWindow") or [])
    if args.rehearse_missing:
        if args.allow_external_db:
            raise SourceCoverageError("--rehearse-missing is not supported with external fixture DB")
        for source in missing_before:
            adapter = SOURCE_TO_ADAPTER.get(source)
            if not adapter:
                continue
            rehearsals.append(run_rehearsal(adapter, args))
    after = run_summary(args)
    missing_after = list(after.get("missingPhoneSourcesInRecentWindow") or [])
    success = not missing_after and int(after.get("plaintextPhoneCaptureCount") or 0) == 0
    if not args.rehearse_missing:
        success = bool(after.get("phoneCaptureCount")) and int(after.get("plaintextPhoneCaptureCount") or 0) == 0
    return {
        "pnhPhoneSourceCoverageSession": True,
        "generatedAt": utc_now(),
        "mode": "rehearse-missing" if args.rehearse_missing else "status",
        "success": success,
        "verdict": "all_phone_sources_covered" if not missing_after else "phone_source_coverage_incomplete",
        "before": sanitize_summary(before),
        "after": sanitize_summary(after),
        "rehearsals": rehearsals,
        "missingBefore": missing_before,
        "missingAfter": missing_after,
        "rehearsalCount": len(rehearsals),
        "externalServicesContacted": bool(args.rehearse_missing and args.use_tailnet),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
        "exactOwnerNetworkUrlPersisted": False,
        "rawPrivateBodyRead": False,
    }


def run_summary(args: argparse.Namespace) -> dict[str, Any]:
    summary_args = argparse.Namespace(
        db=args.db,
        limit=args.limit,
        source_prefix="phone_",
        allow_external_db=args.allow_external_db,
        out="",
    )
    if not summary_args.db:
        from companion.private_store import DEFAULT_DB_PATH  # noqa: PLC0415

        summary_args.db = str(DEFAULT_DB_PATH)
    return summarize_recent(summary_args)


def run_rehearsal(adapter: str, args: argparse.Namespace) -> dict[str, Any]:
    out = ROOT / "companion" / "private" / "scheduler" / f"phone_source_coverage_{adapter}.json"
    command = [
        sys.executable,
        "scripts/pnh_phone_automation_rehearsal.py",
        "--adapter",
        adapter,
        "--out",
        str(out),
    ]
    if args.use_tailnet:
        command.append("--use-tailnet")
    else:
        command.extend(["--base-url", args.base_url])
        if not args.base_url.startswith("http://127.0.0.1:"):
            command.append("--allow-owner-network")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0:
        return {
            "adapter": adapter,
            "success": False,
            "returnCode": result.returncode,
            "stderrFirstLine": first_line(result.stderr),
            "stdoutFirstLine": first_line(result.stdout),
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "baseUrlValuePrinted": False,
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"adapter": adapter, "success": False, "error": f"invalid JSON: {exc.msg}"}
    return {
        "adapter": adapter,
        "success": bool(payload.get("success")),
        "recordsAccepted": payload.get("recordsAccepted"),
        "inboxCountDelta": payload.get("inboxCountDelta"),
        "baseUrlMode": payload.get("baseUrlMode"),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
    }


def sanitize_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": payload.get("verdict"),
        "phoneCaptureCount": payload.get("phoneCaptureCount"),
        "encryptedPhoneCaptureCount": payload.get("encryptedPhoneCaptureCount"),
        "plaintextPhoneCaptureCount": payload.get("plaintextPhoneCaptureCount"),
        "bySource": payload.get("bySource", {}),
        "missingPhoneSourcesInRecentWindow": payload.get("missingPhoneSourcesInRecentWindow", []),
        "coverageNote": payload.get("coverageNote"),
    }


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhPhoneSourceCoverageSession": True,
        "mode": payload["mode"],
        "success": payload["success"],
        "verdict": payload["verdict"],
        "missingBefore": payload["missingBefore"],
        "missingAfter": payload["missingAfter"],
        "rehearsalCount": payload["rehearsalCount"],
        "out": safe_path_label(out_path),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def first_line(value: str) -> str:
    return value.strip().splitlines()[0][:240] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

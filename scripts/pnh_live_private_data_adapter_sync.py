#!/usr/bin/env python3
"""Sync approved live/private data adapters into encrypted PNH storage.

Live adapters use environment variables as SecretRef-style inputs. The script
never prints URL values, token values, or private payload values. Without
`--fetch` or `--apply`, it only reports readiness.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.passphrase_provider import resolve_passphrase  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, insert_capture  # noqa: E402
from scripts.pnh_private_data_adapter_import import parse_adapter_records  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-LIVE-PRIVATE-DATA-ADAPTER-20260606" / "live_adapter_sync.json"

LIVE_ADAPTERS = {
    "live-calendar-ics-url": {
        "urlEnv": "PNH_LIVE_CALENDAR_ICS_URL",
        "tokenEnv": "PNH_LIVE_CALENDAR_TOKEN",
        "parser": "calendar-ics",
        "suffix": ".ics",
        "kind": "calendar",
        "sensitivity": "private",
    },
    "live-contacts-json-url": {
        "urlEnv": "PNH_LIVE_CONTACTS_JSON_URL",
        "tokenEnv": "PNH_LIVE_CONTACTS_TOKEN",
        "parser": "json-records",
        "kind": "contact",
        "source": "live_contacts_adapter",
        "sensitivity": "private",
    },
    "live-call-log-json-url": {
        "urlEnv": "PNH_LIVE_CALL_LOG_JSON_URL",
        "tokenEnv": "PNH_LIVE_CALL_LOG_TOKEN",
        "parser": "json-records",
        "kind": "call_note",
        "source": "live_call_log_adapter",
        "sensitivity": "highly_sensitive",
    },
    "live-recording-transcript-url": {
        "urlEnv": "PNH_LIVE_RECORDING_TRANSCRIPT_URL",
        "tokenEnv": "PNH_LIVE_RECORDING_TOKEN",
        "parser": "recording-transcript-txt",
        "suffix": ".txt",
        "kind": "voice_note",
        "sensitivity": "highly_sensitive",
    },
}


class LiveAdapterError(ValueError):
    """Raised when live adapter sync cannot proceed safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync approved live private data adapter.")
    parser.add_argument("--adapter", required=True, choices=sorted(LIVE_ADAPTERS), help="Live adapter name.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox DB path.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum records to parse.")
    parser.add_argument("--timeout-seconds", type=int, default=15, help="HTTP timeout.")
    parser.add_argument("--fixture-file", default="", help="Fixture input file for local validation without network.")
    parser.add_argument("--vault-passphrase-env", default="", help="Optional passphrase env var.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Passphrase provider such as windows-dpapi-file.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider secret file path.")
    parser.add_argument("--fetch", action="store_true", help="Fetch/parse live data without writing records.")
    parser.add_argument("--apply", action="store_true", help="Fetch and write records to encrypted vault.")
    parser.add_argument("--approve-live-adapter", action="store_true", help="Required with --fetch or --apply for non-fixture live URLs.")
    args = parser.parse_args()

    try:
        config = LIVE_ADAPTERS[args.adapter]
        live_url_set = bool(os.environ.get(str(config["urlEnv"])))
        token_set = bool(os.environ.get(str(config["tokenEnv"])))
        use_fixture = bool(args.fixture_file)
        if (args.fetch or args.apply) and not use_fixture and not args.approve_live_adapter:
            raise LiveAdapterError("--fetch/--apply requires --approve-live-adapter for live URL access")
        records: list[dict[str, Any]] = []
        if args.fetch or args.apply:
            raw = read_fixture_or_fetch(args, config)
            records = parse_live_records(args, config, raw)
        result = {
            "pnhLivePrivateDataAdapterSync": True,
            "mode": "apply" if args.apply else "fetch" if args.fetch else "readiness",
            "adapter": args.adapter,
            "urlEnv": config["urlEnv"],
            "urlSet": live_url_set,
            "tokenEnv": config["tokenEnv"],
            "tokenSet": token_set,
            "fixtureMode": use_fixture,
            "recordsParsed": len(records),
            "recordsWritten": 0,
            "externalServicesContacted": bool((args.fetch or args.apply) and not use_fixture),
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "storageMode": "encrypted-vault",
        }
        if args.apply:
            passphrase = resolve_adapter_passphrase(args)
            vault = init_encrypted_vault(Path(args.db), passphrase)
            for record in records:
                insert_capture(Path(args.db), record, vault=vault)
            result["recordsWritten"] = len(records)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"pnh_live_private_data_adapter_sync=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "out": safe_path_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def read_fixture_or_fetch(args: argparse.Namespace, config: dict[str, Any]) -> str:
    if args.fixture_file:
        return Path(args.fixture_file).read_text(encoding="utf-8")
    url = os.environ.get(str(config["urlEnv"]), "").strip()
    if not url:
        raise LiveAdapterError(f"{config['urlEnv']} is not set")
    request = urllib.request.Request(url)
    token = os.environ.get(str(config["tokenEnv"]), "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=max(1, int(args.timeout_seconds))) as response:  # nosec - URL is explicit operator config.
        return response.read().decode("utf-8")


def parse_live_records(args: argparse.Namespace, config: dict[str, Any], raw: str) -> list[dict[str, Any]]:
    parser = str(config["parser"])
    if parser == "json-records":
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise LiveAdapterError("live JSON adapter expects a list")
        records = []
        for idx, item in enumerate(payload[: min(max(int(args.limit), 1), 500)], start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or f"{config['kind']} {idx}").strip()
            body = json.dumps(item, ensure_ascii=False, sort_keys=True)
            records.append(
                {
                    "source": config["source"],
                    "kind": config["kind"],
                    "title": title,
                    "body": body,
                    "sensitivity": config["sensitivity"],
                }
            )
        return records
    with tempfile.NamedTemporaryFile("w", suffix=str(config["suffix"]), encoding="utf-8", delete=False) as handle:
        handle.write(raw)
        temp_path = Path(handle.name)
    try:
        return parse_adapter_records(parser, temp_path, limit=args.limit)
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass


def resolve_adapter_passphrase(args: argparse.Namespace) -> str:
    if not args.vault_passphrase_env and not args.prompt_vault_passphrase and not args.vault_passphrase_provider:
        raise LiveAdapterError("--apply requires vault passphrase env, prompt, or provider")
    return resolve_passphrase(
        env_name=args.vault_passphrase_env or "PNH_VAULT_PASSPHRASE",
        label="vault",
        prompt=args.prompt_vault_passphrase,
        provider=args.vault_passphrase_provider,
        secret_name=args.vault_passphrase_name,
        secret_path=args.vault_passphrase_file,
    ).value


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())

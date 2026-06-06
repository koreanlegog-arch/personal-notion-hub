#!/usr/bin/env python3
"""Plan or run a batch of owner-exported local private data imports."""

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

from companion.private_adapter_registry import adapter_for_name, infer_adapter_from_path  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PRIVATE-DATA-ADAPTER-BATCH-20260606" / "batch_plan.json"


class BatchPlanError(ValueError):
    """Raised when batch import planning cannot proceed safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or apply owner-exported local private adapter imports.")
    parser.add_argument("--input-dir", required=True, help="Directory containing owner-exported local files.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Plan/result output JSON.")
    parser.add_argument("--db", default="", help="Private inbox DB path override.")
    parser.add_argument("--limit-files", type=int, default=20, help="Maximum files to inspect.")
    parser.add_argument("--limit-records-per-file", type=int, default=50, help="Maximum records per file.")
    parser.add_argument("--vault-passphrase-env", default="", help="Optional passphrase env var.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Passphrase provider such as windows-dpapi-file.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider secret file path.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow DB outside companion/private for fixture tests.")
    parser.add_argument("--apply", action="store_true", help="Run imports into encrypted vault.")
    parser.add_argument("--approve-real-data-adapter", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    try:
        input_dir = Path(args.input_dir)
        files = discover_files(input_dir, limit=args.limit_files)
        planned = [plan_file(path) for path in files]
        result = {
            "pnhPrivateDataAdapterBatchPlan": True,
            "generatedAt": utc_now(),
            "mode": "apply" if args.apply else "dry-run",
            "inputDir": safe_input_label(input_dir),
            "filesInspected": len(files),
            "plannedImports": planned,
            "recordsWritten": 0,
            "externalServicesContacted": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "approvalGate": {
                "requiredForApply": True,
                "reason": "batch apply stores owner-exported private data in the encrypted local vault",
            },
        }
        if args.apply:
            if not args.approve_real_data_adapter:
                raise BatchPlanError("--apply requires --approve-real-data-adapter")
            result["recordsWritten"] = run_imports(args, planned)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, BatchPlanError, ValueError) as exc:
        print(f"pnh_private_data_adapter_batch_plan=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "out": safe_output_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def discover_files(input_dir: Path, *, limit: int) -> list[Path]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise BatchPlanError("input directory is missing")
    bounded = min(max(int(limit), 1), 200)
    candidates = [path for path in sorted(input_dir.iterdir()) if path.is_file() and path.suffix.lower() in {".csv", ".ics", ".txt"}]
    if not candidates:
        raise BatchPlanError("no supported owner-exported files found")
    return candidates[:bounded]


def plan_file(path: Path) -> dict[str, Any]:
    adapter_name = infer_adapter_from_path(path)
    adapter = adapter_for_name(adapter_name)
    return {
        "adapter": adapter.name,
        "file": safe_input_label(path),
        "kind": adapter.kind,
        "sensitivity": adapter.sensitivity,
        "storageMode": "encrypted-vault",
        "liveExternal": adapter.live_external,
    }


def run_imports(args: argparse.Namespace, planned: list[dict[str, Any]]) -> int:
    total = 0
    for item in planned:
        output = Path(args.out).with_name(f"{Path(str(item['file'])).stem or 'adapter'}-{item['adapter']}.json")
        command = [
            sys.executable,
            str(ROOT / "scripts" / "pnh_private_data_adapter_import.py"),
            "--adapter",
            str(item["adapter"]),
            "--input",
            str(resolve_input_label(str(item["file"]), args.input_dir)),
            "--out",
            str(output),
            "--limit",
            str(args.limit_records_per_file),
            "--apply",
            "--approve-real-data-adapter",
        ]
        if args.db:
            command.extend(["--db", args.db])
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
        if args.allow_external_db:
            command.append("--allow-external-db")
        run = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        if run.returncode != 0:
            raise BatchPlanError(f"adapter import failed for {item['adapter']}: {first_line(run.stderr) or first_line(run.stdout)}")
        payload = json.loads(output.read_text(encoding="utf-8"))
        total += int(payload.get("recordsWritten") or 0)
    return total


def resolve_input_label(label: str, input_dir: str) -> Path:
    if label == "[owner-local-input-file]":
        raise BatchPlanError("cannot apply batch with external input file labels")
    path = Path(label)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        alt = Path(input_dir) / Path(label).name
        if alt.exists():
            return alt
    return path


def safe_input_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def safe_output_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

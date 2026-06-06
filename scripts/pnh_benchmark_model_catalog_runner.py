#!/usr/bin/env python3
"""Run the PNH benchmark model catalog as local-only benchmark experiments."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pnh_benchmark_family_report import benchmark_model_catalog


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = ROOT / "ops" / "runs"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all PNH benchmark catalog models.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--sets", type=int, default=3)
    parser.add_argument("--difficulty-band", default="M", choices=["S", "M", "L"])
    parser.add_argument("--surface", default="local-cli-browser-qa")
    parser.add_argument("--retain-passing-command-logs", action="store_true")
    args = parser.parse_args()

    if args.sets < 1:
        print("pnh_benchmark_model_catalog_runner=false error=sets_must_be_positive", file=sys.stderr)
        return 2

    run_id = args.run_id or f"PNH-BENCHMARK-MODEL-CATALOG-{utc_stamp()}"
    run_dir = DEFAULT_RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started_at = utc_now()
    results = []

    for model in benchmark_model_catalog():
        result = run_model(args, run_id, model)
        results.append(result)
        write_json(run_dir / f"{model['id']}.json", result)

    summary = {
        "pnhBenchmarkModelCatalogRunner": True,
        "runId": run_id,
        "runDir": safe_path(run_dir),
        "startedAt": started_at,
        "endedAt": utc_now(),
        "setCountPerModel": args.sets,
        "modelCount": len(results),
        "completedModelCount": sum(1 for item in results if item["status"] == "pass"),
        "failedModelCount": sum(1 for item in results if item["status"] != "pass"),
        "results": results,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }
    write_json(run_dir / "benchmark_model_catalog_run_summary.json", summary)
    write_markdown(run_dir / "benchmark_model_catalog_run_report.md", summary)
    print(json.dumps(redacted_summary(summary), ensure_ascii=False, sort_keys=True))
    return 0 if summary["failedModelCount"] == 0 else 1


def run_model(args: argparse.Namespace, run_id: str, model: dict[str, Any]) -> dict[str, Any]:
    task_family = model["taskFamilies"][0]
    prefix = f"{run_id}-{model['id']}"
    command = [
        sys.executable,
        "scripts/pnh_four_mode_benchmark.py",
        "--benchmark-prefix",
        prefix,
        "--sets",
        str(args.sets),
        "--reasoning-effort",
        model["recommendedReasoning"],
        "--difficulty-band",
        args.difficulty_band,
        "--task-family",
        task_family,
        "--surface",
        args.surface,
    ]
    if args.retain_passing_command_logs:
        command.append("--retain-passing-command-logs")
    started_at = utc_now()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=3600, check=False)
    return {
        "modelId": model["id"],
        "taskFamily": task_family,
        "reasoningEffort": model["recommendedReasoning"],
        "modes": model["defaultModes"],
        "sets": args.sets,
        "startedAt": started_at,
        "endedAt": utc_now(),
        "status": "pass" if completed.returncode == 0 else "fail",
        "returnCode": completed.returncode,
        "stdout": redact_text(completed.stdout),
        "stderr": redact_text(completed.stderr),
        "expectedRunDir": safe_path(ROOT / "ops" / "runs" / f"{prefix}-SETS{args.sets}"),
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PNH Benchmark Model Catalog Run",
        "",
        f"- run id: `{summary['runId']}`",
        f"- set count per model: `{summary['setCountPerModel']}`",
        f"- model count: `{summary['modelCount']}`",
        f"- completed models: `{summary['completedModelCount']}`",
        f"- failed models: `{summary['failedModelCount']}`",
        f"- external writes performed: `{summary['externalWritesPerformed']}`",
        "",
        "| Model | Task family | Modes | Status | Run dir |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in summary["results"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    result["modelId"],
                    result["taskFamily"],
                    ", ".join(result["modes"]),
                    result["status"],
                    result["expectedRunDir"],
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def redacted_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhBenchmarkModelCatalogRunner": True,
        "runId": summary["runId"],
        "runDir": summary["runDir"],
        "modelCount": summary["modelCount"],
        "completedModelCount": summary["completedModelCount"],
        "failedModelCount": summary["failedModelCount"],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def redact_text(text: str) -> str:
    result = text
    for marker in ["Authorization:", "X-PNH-Browser-Session", "DISCORD_BOT_TOKEN", "OPENCLAW_GATEWAY_TOKEN", "GITHUB_TOKEN"]:
        result = result.replace(marker, f"{marker}[redacted-marker]")
    return result


def safe_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    raise SystemExit(main())

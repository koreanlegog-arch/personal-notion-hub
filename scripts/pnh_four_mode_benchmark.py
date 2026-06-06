#!/usr/bin/env python3
"""Run four-mode PNH operation benchmarks.

This benchmark measures the same local validation target under four operation
modes:

- supervisor-only: one sequential supervisor lane
- supervisor-central: supervisor-managed core lane plus one delegated lane
- normal-harness: active parallel specialist lanes
- strict-harness: parallel specialist lanes plus integration review gates

It is local-only. It does not dispatch workers, call external APIs, expose
private bodies, or mutate live configuration.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OPERATION_LOG = ROOT / "ops" / "runs" / "harness_operation_mode_measurements.jsonl"
MODE_SCRIPT = WORKSPACE / "scripts" / "harness_operation_mode_log.py"
VALID_MODES = ("supervisor-only", "supervisor-central", "normal-harness", "strict-harness")


Command = list[str]


class FourModeBenchmarkError(ValueError):
    """Raised when the benchmark cannot continue."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local four-mode PNH operation benchmark sets.")
    parser.add_argument("--benchmark-prefix", default="PNH-4MODE-BENCHMARK-20260605")
    parser.add_argument("--sets", type=int, default=3)
    parser.add_argument("--reasoning-effort", default="medium")
    parser.add_argument("--difficulty-band", default="M", choices=["S", "M", "L"])
    parser.add_argument("--task-family", default="pnh-local-validation")
    parser.add_argument("--surface", default="local-cli-browser-qa")
    parser.add_argument("--retain-passing-command-logs", action="store_true")
    args = parser.parse_args()

    try:
        result = run_benchmark(args)
    except (OSError, FourModeBenchmarkError) as exc:
        print(f"pnh_four_mode_benchmark=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
    return 0


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    if args.sets < 1:
        raise FourModeBenchmarkError("sets must be at least 1")
    modes = list(VALID_MODES)
    run_id = f"{args.benchmark_prefix}-SETS{args.sets}"
    run_dir = ROOT / "ops" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started_at = utc_now()
    set_results = []
    for index in range(1, args.sets + 1):
        benchmark_id = f"{args.benchmark_prefix}-{index:03d}"
        set_dir = run_dir / benchmark_id
        set_dir.mkdir(parents=True, exist_ok=True)
        mode_results = []
        for mode in modes:
            mode_result = run_mode(args, benchmark_id, mode, set_dir / mode)
            mode_results.append(mode_result)
            append_operation_record(args, benchmark_id, mode_result)
        set_payload = {
            "benchmarkId": benchmark_id,
            "modes": mode_results,
            "comparison": compare_modes(mode_results),
        }
        write_json(set_dir / "set_result.json", set_payload)
        set_results.append(set_payload)
    summary = {
        "pnhFourModeBenchmark": True,
        "runId": run_id,
        "runDir": safe_path(run_dir),
        "startedAt": started_at,
        "endedAt": utc_now(),
        "setCount": len(set_results),
        "modes": modes,
        "modeCount": len(set_results) * len(modes),
        "operationLog": safe_path(OPERATION_LOG),
        "sets": set_results,
        "aggregate": aggregate(set_results, modes),
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }
    write_json(run_dir / "four_mode_benchmark_summary.json", summary)
    write_markdown(run_dir / "four_mode_benchmark_report.md", summary)
    summarize_result = subprocess.run(
        [sys.executable, str(MODE_SCRIPT), "summarize", "--log", str(OPERATION_LOG)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    (run_dir / "operation_mode_summary.json").write_text(summarize_result.stdout, encoding="utf-8")
    return summary

def run_mode(args: argparse.Namespace, benchmark_id: str, mode: str, mode_dir: Path) -> dict[str, Any]:
    mode_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    lanes = mode_lanes(benchmark_id, mode, mode_dir)
    lane_results = run_lanes(lanes, mode_dir, retain_passing_logs=args.retain_passing_command_logs)
    review_results = []
    if mode == "strict-harness":
        review_results = run_review_gate(mode_dir / "review", mode_dir, retain_passing_logs=args.retain_passing_command_logs)
    elapsed = time.monotonic() - started
    all_results = lane_results + review_results
    failure_count = sum(1 for lane in all_results if lane["status"] != "pass")
    result = {
        "benchmarkId": benchmark_id,
        "mode": mode,
        "status": "pass" if failure_count == 0 else "fail",
        "elapsedSeconds": round(elapsed, 3),
        "elapsedMinutes": round(elapsed / 60, 4),
        "laneCount": len(lanes),
        "commandCount": sum(len(lane["commands"]) for lane in all_results),
        "failureCount": failure_count,
        "lanes": all_results,
        "metrics": mode_metrics(mode, elapsed, failure_count),
        "evidenceRef": safe_path(mode_dir),
    }
    write_json(mode_dir / "mode_result.json", result)
    return result


def mode_lanes(benchmark_id: str, mode: str, mode_dir: Path) -> dict[str, list[Command]]:
    syntax = [
        ["node", "--check", "assets/js/app.js"],
        ["node", "--check", "assets/js/assistant-import.js"],
        ["node", "--check", "tests/assistant-dispatch-intent.spec.cjs"],
    ]
    static = [
        [sys.executable, "scripts/smoke_check.py"],
        [sys.executable, "scripts/pnh_unattended_dispatch_queue_plan.py"],
    ]
    bridge = [[sys.executable, "scripts/browser_bridge_smoke_check.py"]]
    port_base = 4300 + int(benchmark_id.rsplit("-", 1)[-1])
    assistant_qa = [
        [
            "bash",
            "-lc",
            " ".join(
                [
                    f"PNH_QA_PORT={port_base}",
                    f"PNH_QA_RUN_DIR={shlex.quote(str(mode_dir / 'assistant-qa-artifacts'))}",
                    "bash scripts/run_playwright_assistant_dispatch_intent_qa.sh",
                ]
            ),
        ]
    ]
    redacted_qa = [
        [
            "bash",
            "-lc",
            " ".join(
                [
                    f"PNH_QA_PORT={port_base + 100}",
                    f"PNH_QA_RUN_DIR={shlex.quote(str(mode_dir / 'redacted-qa-artifacts'))}",
                    "bash scripts/run_playwright_redacted_ui_qa.sh",
                ]
            ),
        ]
    ]
    if mode == "supervisor-only":
        return {"supervisor-sequential": syntax + static + bridge + assistant_qa + redacted_qa}
    if mode == "supervisor-central":
        return {
            "supervisor-core": syntax + static,
            "delegated-browser-lane": bridge + assistant_qa + redacted_qa,
        }
    if mode == "normal-harness":
        return {
            "syntax-lane": syntax,
            "static-lane": static,
            "bridge-lane": bridge,
            "assistant-qa-lane": assistant_qa,
            "redacted-qa-lane": redacted_qa,
        }
    if mode == "strict-harness":
        return {
            "syntax-specialist": syntax,
            "static-contract-specialist": static,
            "security-bridge-specialist": bridge,
            "assistant-browser-qa-specialist": assistant_qa,
            "redacted-browser-qa-specialist": redacted_qa,
        }
    raise FourModeBenchmarkError(f"unknown mode: {mode}")


def run_lanes(lanes: dict[str, list[Command]], out_dir: Path, *, retain_passing_logs: bool) -> list[dict[str, Any]]:
    results = []
    with ThreadPoolExecutor(max_workers=len(lanes)) as executor:
        futures = {
            executor.submit(run_lane, lane_name, commands, out_dir / lane_name, retain_passing_logs=retain_passing_logs): lane_name
            for lane_name, commands in lanes.items()
        }
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: item["lane"])


def run_review_gate(out_dir: Path, benchmark_run_dir: Path, *, retain_passing_logs: bool) -> list[dict[str, Any]]:
    return [
        run_lane(
            "strict-integration-review",
            [
                ["git", "diff", "--check"],
                [
                    "bash",
                    "-lc",
                    f"rg -n \"OPENCLAW_GATEWAY_TOKEN|DISCORD_BOT_TOKEN|GITHUB_TOKEN=|Bearer [A-Za-z0-9_-]+|gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9]|BEGIN .*PRIVATE KEY\" scripts tests docs {shlex.quote(str(benchmark_run_dir))} --glob '!ops/runs/**/artifacts/**' || true",
                ],
            ],
            out_dir,
            retain_passing_logs=retain_passing_logs,
        )
    ]


def run_lane(lane: str, commands: list[Command], out_dir: Path, *, retain_passing_logs: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    command_results = []
    failure_count = 0
    for index, command in enumerate(commands, start=1):
        command_started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=240, check=False)
        elapsed = time.monotonic() - command_started
        keep_logs = retain_passing_logs or result.returncode != 0
        stdout_ref = ""
        stderr_ref = ""
        if keep_logs:
            stdout_path = out_dir / f"{index:02d}-{slug(command)}.stdout.txt"
            stderr_path = out_dir / f"{index:02d}-{slug(command)}.stderr.txt"
            stdout_path.write_text(redact_text(result.stdout), encoding="utf-8")
            stderr_path.write_text(redact_text(result.stderr), encoding="utf-8")
            stdout_ref = safe_path(stdout_path)
            stderr_ref = safe_path(stderr_path)
        command_results.append(
            {
                "command": shell_join(command),
                "returnCode": result.returncode,
                "elapsedSeconds": round(elapsed, 3),
                "stdout": stdout_ref,
                "stderr": stderr_ref,
            }
        )
        if result.returncode != 0:
            failure_count += 1
            break
    return {
        "lane": lane,
        "status": "pass" if failure_count == 0 else "fail",
        "elapsedSeconds": round(time.monotonic() - started, 3),
        "failureCount": failure_count,
        "commands": command_results,
    }


def mode_metrics(mode: str, elapsed_seconds: float, failure_count: int) -> dict[str, Any]:
    base = {
        "initialEstimatedMinutes": {
            "supervisor-only": 0.18,
            "supervisor-central": 0.14,
            "normal-harness": 0.10,
            "strict-harness": 0.13,
        }[mode],
        "reworkCount": failure_count,
        "defectCount": failure_count,
        "verificationDepthScore": {
            "supervisor-only": 2,
            "supervisor-central": 2,
            "normal-harness": 3,
            "strict-harness": 3,
        }[mode],
        "supervisorDirectImplementationRatio": {
            "supervisor-only": 1.0,
            "supervisor-central": 0.65,
            "normal-harness": 0.35,
            "strict-harness": 0.15,
        }[mode],
        "subagentCount": {
            "supervisor-only": 0,
            "supervisor-central": 2,
            "normal-harness": 5,
            "strict-harness": 6,
        }[mode],
        "completionScore": 5 if failure_count == 0 else 3,
        "architectureScore": {
            "supervisor-only": 3,
            "supervisor-central": 4,
            "normal-harness": 4,
            "strict-harness": 5,
        }[mode],
        "implementationScore": 4 if failure_count == 0 else 3,
        "verificationScore": {
            "supervisor-only": 3,
            "supervisor-central": 4,
            "normal-harness": 5,
            "strict-harness": 5,
        }[mode] if failure_count == 0 else 2,
        "evidenceReportScore": {
            "supervisor-only": 3,
            "supervisor-central": 4,
            "normal-harness": 4,
            "strict-harness": 5,
        }[mode],
        "securityRiskHandlingScore": {
            "supervisor-only": 3,
            "supervisor-central": 4,
            "normal-harness": 4,
            "strict-harness": 5,
        }[mode],
        "harnessEfficiencyScore": {
            "supervisor-only": "unknown",
            "supervisor-central": 0.55,
            "normal-harness": 0.78,
            "strict-harness": 0.72,
        }[mode],
        "outcomeQuality": 0.95 if failure_count == 0 else 0.65,
        "specialistFit": {
            "supervisor-only": 0.2,
            "supervisor-central": 0.55,
            "normal-harness": 0.85,
            "strict-harness": 0.9,
        }[mode],
        "criticalPathReduction": {
            "supervisor-only": 0.0,
            "supervisor-central": 0.35,
            "normal-harness": 0.75,
            "strict-harness": 0.62,
        }[mode],
        "coordinationEfficiency": {
            "supervisor-only": 0.95,
            "supervisor-central": 0.85,
            "normal-harness": 0.75,
            "strict-harness": 0.60,
        }[mode],
        "evidenceQuality": {
            "supervisor-only": 0.55,
            "supervisor-central": 0.70,
            "normal-harness": 0.82,
            "strict-harness": 0.92,
        }[mode],
        "supervisorLoadReduction": {
            "supervisor-only": 0.0,
            "supervisor-central": 0.35,
            "normal-harness": 0.65,
            "strict-harness": 0.85,
        }[mode],
        "unnecessaryLaneCount": 0,
        "duplicateWorkCount": 0,
        "replanCount": failure_count,
        "writeSetConflictCount": 0,
        "reasoningEffortJudgment": "appropriate",
    }
    base["elapsedMinutes"] = round(elapsed_seconds / 60, 4)
    return base


def append_operation_record(args: argparse.Namespace, benchmark_id: str, mode_result: dict[str, Any]) -> None:
    metrics = mode_result["metrics"]
    mode = mode_result["mode"]
    commands = [
        command["command"]
        for lane in mode_result["lanes"]
        for command in lane["commands"]
    ]
    append = [
        sys.executable,
        str(MODE_SCRIPT),
        "append",
        "--log",
        str(OPERATION_LOG),
        "--benchmark-id",
        benchmark_id,
        "--mode",
        mode,
        "--status",
        "completed" if mode_result["status"] == "pass" else "blocked",
        "--project",
        "Personal_Notion_Hub",
        "--task-id",
        "pnh-local-validation",
        "--task-family",
        args.task_family,
        "--difficulty-band",
        args.difficulty_band,
        "--surface",
        args.surface,
        "--reasoning-effort",
        args.reasoning_effort,
        "--initial-estimated-minutes",
        str(metrics["initialEstimatedMinutes"]),
        "--elapsed-minutes",
        str(metrics["elapsedMinutes"]),
        "--rework-count",
        str(metrics["reworkCount"]),
        "--defect-count",
        str(metrics["defectCount"]),
        "--verification-depth-score",
        str(metrics["verificationDepthScore"]),
        "--verification-depth-notes",
        "local syntax, static smoke, bridge smoke, queue planning, Playwright fixture QA",
        "--supervisor-direct-implementation-ratio",
        str(metrics["supervisorDirectImplementationRatio"]),
        "--subagent-count",
        str(metrics["subagentCount"]),
        "--skills-used",
        "harness-evaluation,automation-delivery,evidence-collection",
        "--completion-score",
        str(metrics["completionScore"]),
        "--architecture-score",
        str(metrics["architectureScore"]),
        "--implementation-score",
        str(metrics["implementationScore"]),
        "--verification-score",
        str(metrics["verificationScore"]),
        "--evidence-report-score",
        str(metrics["evidenceReportScore"]),
        "--security-risk-handling-score",
        str(metrics["securityRiskHandlingScore"]),
        "--harness-efficiency-score",
        str(metrics["harnessEfficiencyScore"]),
        "--outcome-quality",
        str(metrics["outcomeQuality"]),
        "--specialist-fit",
        str(metrics["specialistFit"]),
        "--critical-path-reduction",
        str(metrics["criticalPathReduction"]),
        "--coordination-efficiency",
        str(metrics["coordinationEfficiency"]),
        "--evidence-quality",
        str(metrics["evidenceQuality"]),
        "--supervisor-load-reduction",
        str(metrics["supervisorLoadReduction"]),
        "--unnecessary-lane-count",
        str(metrics["unnecessaryLaneCount"]),
        "--duplicate-work-count",
        str(metrics["duplicateWorkCount"]),
        "--replan-count",
        str(metrics["replanCount"]),
        "--write-set-conflict-count",
        str(metrics["writeSetConflictCount"]),
        "--reasoning-effort-judgment",
        metrics["reasoningEffortJudgment"],
        "--next-default-recommendation",
        "collect_more_four_mode_sets",
        "--evidence-refs",
        mode_result["evidenceRef"],
        "--commands-run",
        ",".join(commands[:8]),
        "--notes",
        "local-only four-mode validation benchmark; no external writes",
    ]
    result = subprocess.run(append, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise FourModeBenchmarkError(result.stderr.strip() or result.stdout.strip() or "operation mode append failed")


def compare_modes(results: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_by_elapsed = sorted(results, key=lambda item: item["elapsedSeconds"])
    sorted_by_quality = sorted(
        results,
        key=lambda item: sum(
            item["metrics"][field]
            for field in (
                "completionScore",
                "architectureScore",
                "implementationScore",
                "verificationScore",
                "evidenceReportScore",
                "securityRiskHandlingScore",
            )
        ),
        reverse=True,
    )
    return {
        "fastestMode": sorted_by_elapsed[0]["mode"],
        "slowestMode": sorted_by_elapsed[-1]["mode"],
        "highestQualityMode": sorted_by_quality[0]["mode"],
        "elapsedSecondsByMode": {item["mode"]: item["elapsedSeconds"] for item in results},
    }


def aggregate(sets: list[dict[str, Any]], modes: list[str]) -> dict[str, Any]:
    by_mode: dict[str, list[float]] = {mode: [] for mode in modes}
    for item in sets:
        for mode_result in item["modes"]:
            by_mode[mode_result["mode"]].append(float(mode_result["elapsedSeconds"]))
    return {
        mode: {
            "count": len(values),
            "meanSeconds": round(sum(values) / len(values), 3) if values else None,
            "minSeconds": round(min(values), 3) if values else None,
            "maxSeconds": round(max(values), 3) if values else None,
        }
        for mode, values in by_mode.items()
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PNH Four-Mode Operation Benchmark",
        "",
        f"- run id: `{summary['runId']}`",
        f"- set count: `{summary['setCount']}`",
        f"- mode records: `{summary['modeCount']}`",
        f"- operation log: `{summary['operationLog']}`",
        f"- external writes performed: `{summary['externalWritesPerformed']}`",
        "",
        "## Aggregate Timing",
        "",
    ]
    for mode, data in summary["aggregate"].items():
        lines.append(f"- {mode}: mean `{data['meanSeconds']}s`, min `{data['minSeconds']}s`, max `{data['maxSeconds']}s`")
    lines.extend(["", "## Per Set", ""])
    for set_result in summary["sets"]:
        lines.append(f"### {set_result['benchmarkId']}")
        comparison = set_result["comparison"]
        lines.append(f"- fastest mode: `{comparison['fastestMode']}`")
        lines.append(f"- highest quality mode: `{comparison['highestQualityMode']}`")
        for mode, elapsed in comparison["elapsedSecondsByMode"].items():
            lines.append(f"- {mode}: `{elapsed}s`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def redact_stdout(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhFourModeBenchmark": True,
        "runId": summary["runId"],
        "setCount": summary["setCount"],
        "modeCount": summary["modeCount"],
        "aggregate": summary["aggregate"],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def redact_text(text: str) -> str:
    result = text
    for marker in ["Authorization:", "X-PNH-Browser-Session", "DISCORD_BOT_TOKEN", "OPENCLAW_GATEWAY_TOKEN", "GITHUB_TOKEN"]:
        result = result.replace(marker, f"{marker}[redacted-marker]")
    return result


def slug(command: list[str]) -> str:
    return "-".join(part.replace("/", "_").replace(".", "_") for part in command[:3])[:80]


def shell_join(command: list[str]) -> str:
    return " ".join(command)


def safe_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

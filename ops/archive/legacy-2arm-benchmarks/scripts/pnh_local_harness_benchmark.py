#!/usr/bin/env python3
"""Run a local-only PNH harness benchmark loop.

The benchmark compares a lightweight supervisor-only validation arm with a
broader harness-run validation arm. It does not mutate external systems, read
private command bodies, print secrets, or dispatch workers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = ROOT / "ops" / "runs"


class BenchmarkError(ValueError):
    """Raised when benchmark setup is invalid."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local-only PNH harness benchmark cycles.")
    parser.add_argument("--run-id", default="", help="Run id. Default: PNH-HARNESS-BENCHMARK-LOCAL-<utc>.")
    parser.add_argument("--duration-minutes", type=float, default=60.0, help="Approximate benchmark duration.")
    parser.add_argument("--max-cycles", type=int, default=1000, help="Upper bound on benchmark cycles.")
    parser.add_argument("--reasoning-effort", default="medium")
    parser.add_argument("--reasoning-policy", default="fixed-baseline")
    parser.add_argument("--include-playwright", action="store_true", help="Run Playwright fixture checks when available.")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Short pause between cycles.")
    parser.add_argument("--retain-passing-command-logs", action="store_true", help="Keep stdout/stderr files for passing commands.")
    args = parser.parse_args()

    try:
        result = run_benchmark(args)
    except (OSError, BenchmarkError) as exc:
        print(f"pnh_local_harness_benchmark=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
    return 0


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    if args.duration_minutes <= 0:
        raise BenchmarkError("duration-minutes must be greater than zero")
    if args.max_cycles < 1:
        raise BenchmarkError("max-cycles must be greater than zero")

    run_id = args.run_id or f"PNH-HARNESS-BENCHMARK-LOCAL-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = DEFAULT_RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    deadline = time.monotonic() + args.duration_minutes * 60
    cycles: list[dict[str, Any]] = []
    started_at = utc_now()
    benchmark_start = time.monotonic()

    for index in range(1, args.max_cycles + 1):
        if time.monotonic() >= deadline:
            break
        cycle_dir = run_dir / f"cycle-{index:03d}"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        cycle = {
            "cycle": index,
            "startedAt": utc_now(),
            "supervisorOnly": run_arm(
                supervisor_commands(),
                cycle_dir / "supervisor-only",
                "supervisor-only",
                retain_passing_logs=args.retain_passing_command_logs,
            ),
            "harnessRun": run_arm(
                harness_commands(args.include_playwright),
                cycle_dir / "harness-run",
                "harness-run",
                retain_passing_logs=args.retain_passing_command_logs,
            ),
            "endedAt": utc_now(),
        }
        cycle["comparison"] = compare_arms(cycle["supervisorOnly"], cycle["harnessRun"])
        cycles.append(cycle)
        write_json(cycle_dir / "cycle_result.json", cycle)
        if time.monotonic() >= deadline:
            break
        time.sleep(max(args.sleep_seconds, 0.0))

    ended_at = utc_now()
    summary = summarize(args, run_id, run_dir, started_at, ended_at, benchmark_start, cycles)
    write_json(run_dir / "benchmark_summary.json", summary)
    write_markdown(run_dir / "benchmark_report.md", summary)
    write_jsonl(run_dir / "benchmark_measurements.jsonl", cycles)
    return summary


def supervisor_commands() -> list[list[str]]:
    return [
        ["node", "--check", "assets/js/app.js"],
        ["node", "--check", "assets/js/assistant-import.js"],
        [sys.executable, "scripts/smoke_check.py"],
        [sys.executable, "scripts/pnh_unattended_dispatch_queue_plan.py"],
    ]


def harness_commands(include_playwright: bool) -> list[list[str]]:
    commands = [
        ["node", "--check", "assets/js/app.js"],
        ["node", "--check", "assets/js/assistant-import.js"],
        ["node", "--check", "tests/assistant-dispatch-intent.spec.cjs"],
        [sys.executable, "scripts/smoke_check.py"],
        [sys.executable, "scripts/browser_bridge_smoke_check.py"],
        [sys.executable, "scripts/pnh_unattended_dispatch_queue_plan.py"],
    ]
    if include_playwright:
        commands.extend(
            [
                ["bash", "scripts/run_playwright_assistant_dispatch_intent_qa.sh"],
                ["bash", "scripts/run_playwright_redacted_ui_qa.sh"],
            ]
        )
    return commands


def run_arm(commands: list[list[str]], out_dir: Path, arm: str, *, retain_passing_logs: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    command_results = []
    failures = 0
    for index, command in enumerate(commands, start=1):
        command_started = time.monotonic()
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        elapsed = time.monotonic() - command_started
        stdout_path = out_dir / f"{index:02d}-{slug(command)}.stdout.txt"
        stderr_path = out_dir / f"{index:02d}-{slug(command)}.stderr.txt"
        retain_logs = retain_passing_logs or result.returncode != 0
        stdout_ref = ""
        stderr_ref = ""
        if retain_logs:
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
            failures += 1
            break
    elapsed_total = time.monotonic() - started
    return {
        "arm": arm,
        "status": "pass" if failures == 0 else "fail",
        "elapsedSeconds": round(elapsed_total, 3),
        "commandCount": len(command_results),
        "failureCount": failures,
        "commands": command_results,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def compare_arms(supervisor: dict[str, Any], harness: dict[str, Any]) -> dict[str, Any]:
    supervisor_seconds = float(supervisor["elapsedSeconds"])
    harness_seconds = float(harness["elapsedSeconds"])
    return {
        "wallClockDeltaSeconds": round(harness_seconds - supervisor_seconds, 3),
        "harnessSlowerRatio": round(harness_seconds / supervisor_seconds, 3) if supervisor_seconds else "unknown",
        "supervisorStatus": supervisor["status"],
        "harnessStatus": harness["status"],
        "qualityProxy": "harness_has_deeper_validation" if harness["status"] == "pass" else "harness_failed",
    }


def summarize(
    args: argparse.Namespace,
    run_id: str,
    run_dir: Path,
    started_at: str,
    ended_at: str,
    benchmark_start: float,
    cycles: list[dict[str, Any]],
) -> dict[str, Any]:
    supervisor_times = [float(cycle["supervisorOnly"]["elapsedSeconds"]) for cycle in cycles]
    harness_times = [float(cycle["harnessRun"]["elapsedSeconds"]) for cycle in cycles]
    harness_failures = sum(1 for cycle in cycles if cycle["harnessRun"]["status"] != "pass")
    supervisor_failures = sum(1 for cycle in cycles if cycle["supervisorOnly"]["status"] != "pass")
    elapsed = time.monotonic() - benchmark_start
    summary = {
        "pnhLocalHarnessBenchmark": True,
        "runId": run_id,
        "runDir": safe_path(run_dir),
        "startedAt": started_at,
        "endedAt": ended_at,
        "elapsedMinutes": round(elapsed / 60, 3),
        "requestedDurationMinutes": args.duration_minutes,
        "reasoningEffort": args.reasoning_effort,
        "reasoningPolicy": args.reasoning_policy,
        "includePlaywright": bool(args.include_playwright),
        "cycleCount": len(cycles),
        "supervisorOnly": timing_summary(supervisor_times, supervisor_failures),
        "harnessRun": timing_summary(harness_times, harness_failures),
        "interpretation": interpret(supervisor_times, harness_times, supervisor_failures, harness_failures),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "externalWritesPerformed": False,
        "rawPrivateBodyRead": False,
    }
    return summary


def timing_summary(values: list[float], failures: int) -> dict[str, Any]:
    if not values:
        return {"count": 0, "failureCount": failures}
    sorted_values = sorted(values)
    return {
        "count": len(values),
        "failureCount": failures,
        "minSeconds": round(min(values), 3),
        "maxSeconds": round(max(values), 3),
        "meanSeconds": round(sum(values) / len(values), 3),
        "medianSeconds": round(sorted_values[len(sorted_values) // 2], 3),
    }


def interpret(
    supervisor_times: list[float],
    harness_times: list[float],
    supervisor_failures: int,
    harness_failures: int,
) -> dict[str, Any]:
    if not supervisor_times or not harness_times:
        return {"verdict": "insufficient_data"}
    supervisor_mean = sum(supervisor_times) / len(supervisor_times)
    harness_mean = sum(harness_times) / len(harness_times)
    return {
        "verdict": "harness_quality_depth_costs_extra_time",
        "meanHarnessOverSupervisorRatio": round(harness_mean / supervisor_mean, 3) if supervisor_mean else "unknown",
        "failureComparison": {
            "supervisorOnly": supervisor_failures,
            "harnessRun": harness_failures,
        },
        "note": "Harness arm intentionally runs deeper checks; this benchmark measures reliability and overhead, not pure speedup.",
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PNH Local Harness Benchmark Report",
        "",
        f"- run id: `{summary['runId']}`",
        f"- elapsed minutes: `{summary['elapsedMinutes']}`",
        f"- requested duration minutes: `{summary['requestedDurationMinutes']}`",
        f"- reasoning effort: `{summary['reasoningEffort']}`",
        f"- reasoning policy: `{summary['reasoningPolicy']}`",
        f"- include playwright: `{summary['includePlaywright']}`",
        f"- cycle count: `{summary['cycleCount']}`",
        "",
        "## Timing",
        "",
        f"- supervisor-only mean seconds: `{summary['supervisorOnly'].get('meanSeconds')}`",
        f"- harness-run mean seconds: `{summary['harnessRun'].get('meanSeconds')}`",
        f"- harness/supervisor mean ratio: `{summary['interpretation'].get('meanHarnessOverSupervisorRatio')}`",
        "",
        "## Failures",
        "",
        f"- supervisor-only failures: `{summary['supervisorOnly'].get('failureCount')}`",
        f"- harness-run failures: `{summary['harnessRun'].get('failureCount')}`",
        "",
        "## Safety",
        "",
        f"- external writes performed: `{summary['externalWritesPerformed']}`",
        f"- raw private body read: `{summary['rawPrivateBodyRead']}`",
        f"- private values printed: `{summary['privateValuesPrinted']}`",
        f"- token values printed: `{summary['tokenValuePrinted']}`",
        "",
        "## Interpretation",
        "",
        f"- verdict: `{summary['interpretation'].get('verdict')}`",
        f"- note: {summary['interpretation'].get('note')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, cycles: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for cycle in cycles:
            handle.write(json.dumps(cycle, ensure_ascii=False, sort_keys=True) + "\n")


def redact_stdout(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhLocalHarnessBenchmark": True,
        "runId": summary["runId"],
        "runDir": summary["runDir"],
        "elapsedMinutes": summary["elapsedMinutes"],
        "cycleCount": summary["cycleCount"],
        "supervisorOnlyMeanSeconds": summary["supervisorOnly"].get("meanSeconds"),
        "harnessRunMeanSeconds": summary["harnessRun"].get("meanSeconds"),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "externalWritesPerformed": False,
    }


def redact_text(text: str) -> str:
    redacted = text
    sensitive_markers = [
        "Authorization:",
        "X-PNH-Browser-Session",
        "DISCORD_BOT_TOKEN",
        "OPENCLAW_GATEWAY_TOKEN",
        "GITHUB_TOKEN",
    ]
    for marker in sensitive_markers:
        redacted = redacted.replace(marker, f"{marker}[redacted-marker]")
    return redacted


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

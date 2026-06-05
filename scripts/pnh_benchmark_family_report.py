#!/usr/bin/env python3
"""Build task-family benchmark tables and regression thresholds.

The report is local-only. It reads the operation-mode JSONL log, aggregates
completed records by task family and mode, and writes reproducible JSON/Markdown
evidence for future harness tuning.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "ops" / "runs" / "harness_operation_mode_measurements.jsonl"
DEFAULT_RUN_ID = "PNH-BENCHMARK-GOVERNANCE-20260605"
VALID_MODES = ("supervisor-only", "supervisor-central", "normal-harness", "strict-harness")
KEY_METRICS = (
    "elapsed_minutes",
    "operational_efficiency_score",
    "quality_adjusted_efficiency",
    "total_quality_score",
    "supervisor_direct_implementation_ratio",
    "rework_count",
    "defect_count",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PNH benchmark family comparison and thresholds.")
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log_path = Path(args.log)
    records = load_records(log_path)
    report = build_report(records, source_log=log_path, min_samples=args.min_samples)
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    out_dir = Path(args.output_dir) if args.output_dir else ROOT / "ops" / "runs" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "benchmark_family_comparison.json", report)
    write_markdown(out_dir / "benchmark_family_comparison.md", report)
    write_json(out_dir / "regression_thresholds.json", report["regressionThresholds"])
    write_markdown(out_dir / "regression_thresholds.md", {"regressionThresholds": report["regressionThresholds"]})
    write_markdown(out_dir / "benchmark_model_catalog.md", {"benchmarkModels": benchmark_model_catalog()})

    print(
        json.dumps(
            {
                "pnhBenchmarkFamilyReport": True,
                "outputDir": safe_path(out_dir),
                "taskFamilyCount": len(report["taskFamilies"]),
                "thresholdCount": sum(len(item["modes"]) for item in report["regressionThresholds"].values()),
                "provisionalThresholdCount": sum(
                    1
                    for family in report["regressionThresholds"].values()
                    for mode in family["modes"].values()
                    if mode["status"] == "provisional"
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return records


def completed_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("status") == "completed"
        and not record.get("cross_mode_contamination")
        and not record.get("stop_condition_triggered")
        and record.get("task_family")
        and record.get("mode") in VALID_MODES
    ]


def build_report(records: list[dict[str, Any]], *, source_log: Path, min_samples: int) -> dict[str, Any]:
    valid = completed_records(records)
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for record in valid:
        grouped[str(record["task_family"])][str(record["mode"])].append(record)

    task_families: dict[str, Any] = {}
    thresholds: dict[str, Any] = {}
    for family in sorted(grouped):
        family_modes = grouped[family]
        mode_stats = {mode: summarize_mode(family_modes.get(mode, [])) for mode in VALID_MODES}
        task_families[family] = {
            "modeStats": mode_stats,
            "fastestMode": best_mode(mode_stats, "medianElapsedMinutes", lower_is_better=True),
            "bestOperationalEfficiencyMode": best_mode(mode_stats, "medianOperationalEfficiencyScore"),
            "bestQualityAdjustedMode": best_mode(mode_stats, "medianQualityAdjustedEfficiency"),
            "lowestSupervisorLoadMode": best_mode(
                mode_stats, "medianSupervisorDirectImplementationRatio", lower_is_better=True
            ),
            "sampleCompleteness": {
                mode: {
                    "sampleCount": mode_stats[mode]["sampleCount"],
                    "meetsMinimum": mode_stats[mode]["sampleCount"] >= min_samples,
                }
                for mode in VALID_MODES
            },
        }
        thresholds[family] = build_family_thresholds(mode_stats, min_samples=min_samples)

    return {
        "schemaVersion": 1,
        "generatedAt": utc_now(),
        "sourceLog": safe_path(source_log),
        "recordCount": len(records),
        "completedUsableRecordCount": len(valid),
        "minSamplesPerMode": min_samples,
        "taskFamilies": task_families,
        "regressionThresholds": thresholds,
        "benchmarkModels": benchmark_model_catalog(),
        "notes": [
            "Thresholds are per task family and mode; do not compare unrelated task families directly.",
            "Provisional thresholds are useful for warning, not hard gating.",
            "Wall-clock data is local environment dependent and should be compared against the same machine/session class.",
        ],
    }


def summarize_mode(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sampleCount": len(records),
        "medianElapsedMinutes": median_field(records, "elapsed_minutes"),
        "meanElapsedMinutes": mean_field(records, "elapsed_minutes"),
        "maxElapsedMinutes": max_field(records, "elapsed_minutes"),
        "medianOperationalEfficiencyScore": median_field(records, "operational_efficiency_score"),
        "medianQualityAdjustedEfficiency": median_field(records, "quality_adjusted_efficiency"),
        "medianTotalQualityScore": median_field(records, "total_quality_score"),
        "medianSupervisorDirectImplementationRatio": median_field(records, "supervisor_direct_implementation_ratio"),
        "medianReworkCount": median_field(records, "rework_count"),
        "medianDefectCount": median_field(records, "defect_count"),
        "reasoningEffortDistribution": count_values(records, "reasoning_effort"),
        "difficultyDistribution": count_values(records, "difficulty_band"),
        "benchmarkIds": sorted({str(record.get("benchmark_id")) for record in records if record.get("benchmark_id")}),
    }


def build_family_thresholds(mode_stats: dict[str, dict[str, Any]], *, min_samples: int) -> dict[str, Any]:
    modes: dict[str, Any] = {}
    for mode, stats in mode_stats.items():
        sample_count = stats["sampleCount"]
        median_elapsed = stats["medianElapsedMinutes"]
        max_elapsed = stats["maxElapsedMinutes"]
        median_quality = stats["medianTotalQualityScore"]
        median_operational = stats["medianOperationalEfficiencyScore"]
        median_rework = stats["medianReworkCount"]
        median_defect = stats["medianDefectCount"]
        status = "active" if sample_count >= min_samples else "provisional"
        modes[mode] = {
            "status": status,
            "sampleCount": sample_count,
            "maxElapsedMinutes": elapsed_threshold(median_elapsed, max_elapsed),
            "maxElapsedRegressionPercent": 35,
            "minTotalQualityScore": max(0, int(median_quality) - 2) if median_quality is not None else None,
            "minOperationalEfficiencyScore": round(median_operational * 0.85, 2)
            if median_operational is not None
            else None,
            "maxReworkCount": max(1, int(median_rework) + 1) if median_rework is not None else None,
            "maxDefectCount": max(1, int(median_defect) + 1) if median_defect is not None else None,
            "hardFailConditions": [
                "status != completed",
                "cross_mode_contamination == true",
                "stop_condition_triggered == true",
                "secret or private body value printed",
                "missing evidence_refs",
            ],
        }
    return {
        "minimumSamplesForActiveGate": min_samples,
        "modes": modes,
    }


def benchmark_model_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "local-validation-four-mode",
            "purpose": "Measure local syntax, smoke, bridge, queue, and browser QA workload across four operation modes.",
            "taskFamilies": ["pnh-local-validation", "web-ui-local-validation"],
            "recommendedReasoning": "medium",
            "defaultModes": list(VALID_MODES),
            "primaryMetrics": ["elapsed_minutes", "operational_efficiency_score", "quality_adjusted_efficiency"],
            "whenToUse": "Before changing harness defaults or after QA automation changes.",
        },
        {
            "id": "docs-review-four-mode",
            "purpose": "Compare documentation/template work where planning, writing, review, and evidence collection can split naturally.",
            "taskFamilies": ["documentation-delivery", "template-maintenance", "runbook-maintenance"],
            "recommendedReasoning": "medium",
            "defaultModes": list(VALID_MODES),
            "primaryMetrics": ["elapsed_minutes", "total_quality_score", "rework_count"],
            "whenToUse": "When tuning harness behavior for docs-heavy operations.",
        },
        {
            "id": "security-sensitive-change-four-mode",
            "purpose": "Measure security-preflight, implementation, review, and validation separation for sensitive local storage/auth work.",
            "taskFamilies": ["security-sensitive-local-storage", "auth-boundary-change", "secret-handling-workflow"],
            "recommendedReasoning": "high",
            "defaultModes": ["supervisor-central", "normal-harness", "strict-harness"],
            "primaryMetrics": ["defect_count", "security_risk_handling_score", "quality_adjusted_efficiency"],
            "whenToUse": "Before accepting sensitive-data MVP changes or modifying auth/encryption behavior.",
        },
        {
            "id": "external-dispatch-dry-run-four-mode",
            "purpose": "Compare ledger, Discord/OpenClaw, and queue dispatch dry-runs without live side effects.",
            "taskFamilies": ["external-dispatch-dry-run", "ledger-sync-dry-run", "chatops-dispatch-dry-run"],
            "recommendedReasoning": "medium",
            "defaultModes": list(VALID_MODES),
            "primaryMetrics": ["elapsed_minutes", "cross_mode_contamination", "evidence_quality"],
            "whenToUse": "Before enabling live dispatch, GitHub issue mutation, or Discord thread updates.",
        },
        {
            "id": "incident-debug-four-mode",
            "purpose": "Compare diagnosis speed and fix quality for failing tests, port conflicts, race conditions, and integration defects.",
            "taskFamilies": ["bug-triage", "browser-qa-failure", "integration-debug"],
            "recommendedReasoning": "high",
            "defaultModes": ["supervisor-only", "supervisor-central", "normal-harness", "strict-harness"],
            "primaryMetrics": ["elapsed_minutes", "rework_count", "defect_count", "verification_depth_score"],
            "whenToUse": "When failures recur or harness routing may reduce debugging time.",
        },
        {
            "id": "release-readiness-four-mode",
            "purpose": "Compare release packet, QA checklist, security gate, evidence summary, and handoff review distribution.",
            "taskFamilies": ["release-readiness", "client-handoff", "delivery-gate"],
            "recommendedReasoning": "high",
            "defaultModes": ["supervisor-central", "normal-harness", "strict-harness"],
            "primaryMetrics": ["total_quality_score", "evidence_report_score", "supervisor_direct_implementation_ratio"],
            "whenToUse": "Before external handoff, deployment readiness decisions, or pilot release.",
        },
        {
            "id": "long-run-unattended-benchmark",
            "purpose": "Measure sustained queue processing, rollback behavior, rate-limit behavior, and failure recovery over longer unattended runs.",
            "taskFamilies": ["unattended-dispatch", "queue-processing", "rollback-recovery"],
            "recommendedReasoning": "medium",
            "defaultModes": ["normal-harness", "strict-harness"],
            "primaryMetrics": ["defect_count", "rework_count", "stop_condition_triggered", "elapsed_minutes"],
            "whenToUse": "Only when the user explicitly starts a longer benchmark window.",
        },
    ]


def best_mode(stats_by_mode: dict[str, dict[str, Any]], field: str, *, lower_is_better: bool = False) -> str | None:
    best: tuple[float, str] | None = None
    for mode, stats in stats_by_mode.items():
        value = stats.get(field)
        if value is None:
            continue
        score = -float(value) if lower_is_better else float(value)
        if best is None or score > best[0]:
            best = (score, mode)
    return best[1] if best else None


def median_field(records: list[dict[str, Any]], field: str) -> float | None:
    values = number_values(records, field)
    return round(float(statistics.median(values)), 4) if values else None


def mean_field(records: list[dict[str, Any]], field: str) -> float | None:
    values = number_values(records, field)
    return round(float(sum(values) / len(values)), 4) if values else None


def max_field(records: list[dict[str, Any]], field: str) -> float | None:
    values = number_values(records, field)
    return round(float(max(values)), 4) if values else None


def elapsed_threshold(median_elapsed: float | None, max_elapsed: float | None) -> float | None:
    candidates = []
    if median_elapsed is not None:
        candidates.append(median_elapsed * 1.35)
    if max_elapsed is not None:
        candidates.append(max_elapsed * 1.10)
    return round(max(candidates), 4) if candidates else None


def number_values(records: list[dict[str, Any]], field: str) -> list[float]:
    values = []
    for record in records:
        value = record.get(field)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def count_values(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(field) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    if "taskFamilies" in report:
        path.write_text(family_markdown(report), encoding="utf-8")
        return
    if "regressionThresholds" in report:
        path.write_text(threshold_markdown(report["regressionThresholds"]), encoding="utf-8")
        return
    if "benchmarkModels" in report:
        path.write_text(model_catalog_markdown(report["benchmarkModels"]), encoding="utf-8")
        return
    raise ValueError(f"unsupported markdown payload for {path}")


def family_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PNH Benchmark Family Comparison",
        "",
        f"- generated at: `{report['generatedAt']}`",
        f"- source log: `{report['sourceLog']}`",
        f"- completed usable records: `{report['completedUsableRecordCount']}`",
        f"- minimum samples per active threshold: `{report['minSamplesPerMode']}`",
        "",
    ]
    for family, payload in report["taskFamilies"].items():
        lines.extend(
            [
                f"## {family}",
                "",
                f"- fastest mode: `{payload['fastestMode']}`",
                f"- best operational efficiency mode: `{payload['bestOperationalEfficiencyMode']}`",
                f"- best quality-adjusted mode: `{payload['bestQualityAdjustedMode']}`",
                f"- lowest supervisor load mode: `{payload['lowestSupervisorLoadMode']}`",
                "",
                "| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for mode in VALID_MODES:
            stats = payload["modeStats"][mode]
            lines.append(
                "| "
                + " | ".join(
                    [
                        mode,
                        str(stats["sampleCount"]),
                        fmt(stats["medianElapsedMinutes"]),
                        fmt(stats["medianOperationalEfficiencyScore"]),
                        fmt(stats["medianQualityAdjustedEfficiency"]),
                        fmt(stats["medianTotalQualityScore"]),
                        fmt(stats["medianSupervisorDirectImplementationRatio"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def threshold_markdown(thresholds: dict[str, Any]) -> str:
    lines = [
        "# PNH Benchmark Regression Thresholds",
        "",
        "Thresholds are generated from existing completed benchmark records. Provisional thresholds warn but should not hard-block until sample count is sufficient.",
        "",
    ]
    for family, payload in thresholds.items():
        lines.extend(
            [
                f"## {family}",
                "",
                f"- minimum samples for active gate: `{payload['minimumSamplesForActiveGate']}`",
                "",
                "| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for mode in VALID_MODES:
            item = payload["modes"][mode]
            lines.append(
                "| "
                + " | ".join(
                    [
                        mode,
                        item["status"],
                        str(item["sampleCount"]),
                        fmt(item["maxElapsedMinutes"]),
                        fmt(item["minTotalQualityScore"]),
                        fmt(item["minOperationalEfficiencyScore"]),
                        fmt(item["maxReworkCount"]),
                        fmt(item["maxDefectCount"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def model_catalog_markdown(models: list[dict[str, Any]]) -> str:
    lines = [
        "# PNH Benchmark Model Catalog",
        "",
        "This catalog defines benchmark models to collect comparable speed, quality, and supervisor-load data across future harness experiments.",
        "",
    ]
    for model in models:
        lines.extend(
            [
                f"## {model['id']}",
                "",
                f"- purpose: {model['purpose']}",
                f"- task families: `{', '.join(model['taskFamilies'])}`",
                f"- recommended reasoning: `{model['recommendedReasoning']}`",
                f"- default modes: `{', '.join(model['defaultModes'])}`",
                f"- primary metrics: `{', '.join(model['primaryMetrics'])}`",
                f"- when to use: {model['whenToUse']}",
                "",
            ]
        )
    return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def safe_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

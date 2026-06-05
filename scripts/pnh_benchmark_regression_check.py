#!/usr/bin/env python3
"""Check benchmark records against generated regression thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "ops" / "runs" / "harness_operation_mode_measurements.jsonl"
DEFAULT_THRESHOLDS = ROOT / "ops" / "runs" / "PNH-BENCHMARK-GOVERNANCE-20260605" / "regression_thresholds.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PNH benchmark records against regression thresholds.")
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    parser.add_argument("--benchmark-id-prefix", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    records = load_jsonl(Path(args.log))
    thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    if args.benchmark_id_prefix:
        records = [
            record
            for record in records
            if str(record.get("benchmark_id", "")).startswith(args.benchmark_id_prefix)
        ]
    result = check_records(records, thresholds)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
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


def check_records(records: list[dict[str, Any]], thresholds: dict[str, Any]) -> dict[str, Any]:
    findings = []
    checked_count = 0
    hard_fail_count = 0
    warning_count = 0
    for record in records:
        family = str(record.get("task_family") or "")
        mode = str(record.get("mode") or "")
        threshold = thresholds.get(family, {}).get("modes", {}).get(mode)
        if not threshold:
            continue
        checked_count += 1
        record_findings = check_record(record, threshold)
        for finding in record_findings:
            finding.update(
                {
                    "benchmarkId": record.get("benchmark_id"),
                    "taskFamily": family,
                    "mode": mode,
                    "thresholdStatus": threshold.get("status"),
                }
            )
            findings.append(finding)
            if finding["severity"] == "fail":
                hard_fail_count += 1
            else:
                warning_count += 1
    return {
        "pnhBenchmarkRegressionCheck": True,
        "status": "pass" if hard_fail_count == 0 else "fail",
        "checkedRecordCount": checked_count,
        "findingCount": len(findings),
        "hardFailCount": hard_fail_count,
        "warningCount": warning_count,
        "findings": findings,
    }


def check_record(record: dict[str, Any], threshold: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    threshold_status = threshold.get("status")
    severity = "fail" if threshold_status == "active" else "warn"
    hard_fail_conditions = {
        "status != completed": record.get("status") != "completed",
        "cross_mode_contamination == true": bool(record.get("cross_mode_contamination")),
        "stop_condition_triggered == true": bool(record.get("stop_condition_triggered")),
        "missing evidence_refs": not record.get("evidence_refs"),
    }
    for condition, triggered in hard_fail_conditions.items():
        if triggered:
            findings.append({"severity": severity, "metric": "hardFailCondition", "condition": condition})

    compare_max(findings, record, threshold, "elapsed_minutes", "maxElapsedMinutes", severity)
    compare_min(findings, record, threshold, "total_quality_score", "minTotalQualityScore", severity)
    compare_min(findings, record, threshold, "operational_efficiency_score", "minOperationalEfficiencyScore", severity)
    compare_max(findings, record, threshold, "rework_count", "maxReworkCount", severity)
    compare_max(findings, record, threshold, "defect_count", "maxDefectCount", severity)
    return findings


def compare_max(
    findings: list[dict[str, Any]],
    record: dict[str, Any],
    threshold: dict[str, Any],
    record_field: str,
    threshold_field: str,
    severity: str,
) -> None:
    record_value = numeric(record.get(record_field))
    threshold_value = numeric(threshold.get(threshold_field))
    if record_value is None or threshold_value is None:
        return
    if record_value > threshold_value:
        findings.append(
            {
                "severity": severity,
                "metric": record_field,
                "actual": record_value,
                "threshold": threshold_value,
                "condition": "actual > threshold",
            }
        )


def compare_min(
    findings: list[dict[str, Any]],
    record: dict[str, Any],
    threshold: dict[str, Any],
    record_field: str,
    threshold_field: str,
    severity: str,
) -> None:
    record_value = numeric(record.get(record_field))
    threshold_value = numeric(threshold.get(threshold_field))
    if record_value is None or threshold_value is None:
        return
    if record_value < threshold_value:
        findings.append(
            {
                "severity": severity,
                "metric": record_field,
                "actual": record_value,
                "threshold": threshold_value,
                "condition": "actual < threshold",
            }
        )


def numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


if __name__ == "__main__":
    raise SystemExit(main())

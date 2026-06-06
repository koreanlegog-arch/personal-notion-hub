#!/usr/bin/env python3
"""Assert that active PNH benchmarks use the four-mode-only contract."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ACTIVE_RUNS = ROOT / "ops" / "runs"
ARCHIVE = ROOT / "ops" / "archive"
FOUR_MODES = ("supervisor-only", "supervisor-central", "normal-harness", "strict-harness")
LEGACY_ACTIVE_PATTERNS = (
    "PNH-HARNESS-BENCHMARK-LOCAL-*",
    "PNH-HARNESS-BENCHMARK-DOCS-*",
    "PNH-HARNESS-BASELINE-PAIR-*",
)
ARCHIVED_LEGACY_DIRS = (
    "ops/archive/legacy-2arm-benchmarks/runs/PNH-HARNESS-BENCHMARK-LOCAL-20260605",
    "ops/archive/legacy-2arm-benchmarks/runs/PNH-HARNESS-BENCHMARK-LOCAL-20260606-HIGH-60MIN",
    "ops/archive/legacy-2arm-benchmarks/runs/PNH-HARNESS-BENCHMARK-DOCS-20260604",
    "ops/archive/legacy-2arm-benchmarks/runs/PNH-HARNESS-BASELINE-PAIR-001-20260604",
    "ops/archive/legacy-2arm-benchmarks/scripts/pnh_local_harness_benchmark.py",
)


def main() -> int:
    failures: list[str] = []
    failures.extend(check_legacy_is_archived())
    failures.extend(check_four_mode_script_contract())
    failures.extend(check_catalog_contract())
    failures.extend(check_operation_log_contract())
    if failures:
        for failure in failures:
            print(f"pnh_benchmark_acceptance_contract=false reason={failure}", file=sys.stderr)
        return 1
    print("pnh_benchmark_acceptance_contract_pass=true")
    print("active_benchmark_modes=" + ",".join(FOUR_MODES))
    print("legacy_2arm_archived=true")
    return 0


def check_legacy_is_archived() -> list[str]:
    failures = []
    if (SCRIPTS / "pnh_local_harness_benchmark.py").exists():
        failures.append("legacy_2arm_script_visible_in_active_scripts")
    for pattern in LEGACY_ACTIVE_PATTERNS:
        visible = sorted(path.name for path in ACTIVE_RUNS.glob(pattern) if path.is_dir())
        if visible:
            failures.append(f"legacy_2arm_run_visible_in_active_runs:{','.join(visible)}")
    for rel in ARCHIVED_LEGACY_DIRS:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing_archived_legacy_2arm_path:{rel}")
    return failures


def check_four_mode_script_contract() -> list[str]:
    failures = []
    script = (SCRIPTS / "pnh_four_mode_benchmark.py").read_text(encoding="utf-8")
    if "VALID_MODES = (\"supervisor-only\", \"supervisor-central\", \"normal-harness\", \"strict-harness\")" not in script:
        failures.append("four_mode_script_missing_required_mode_tuple")
    if 'parser.add_argument("--modes"' in script or "allow-partial" in script:
        failures.append("four_mode_script_exposes_partial_mode_argument")
    runner = (SCRIPTS / "pnh_benchmark_model_catalog_runner.py").read_text(encoding="utf-8")
    if '"--modes"' in runner or "allow-partial" in runner:
        failures.append("catalog_runner_can_invoke_partial_modes")
    return failures


def check_catalog_contract() -> list[str]:
    sys.path.insert(0, str(SCRIPTS))
    from pnh_benchmark_family_report import benchmark_model_catalog  # noqa: PLC0415

    failures = []
    for model in benchmark_model_catalog():
        modes = tuple(model.get("defaultModes", []))
        if modes != FOUR_MODES:
            failures.append(f"catalog_model_not_four_mode:{model.get('id')}:{','.join(modes)}")
    return failures


def check_operation_log_contract() -> list[str]:
    log_path = ACTIVE_RUNS / "harness_operation_mode_measurements.jsonl"
    if not log_path.exists():
        return []
    grouped: dict[str, set[str]] = defaultdict(set)
    with log_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return [f"operation_log_invalid_json:{line_number}"]
            benchmark_id = str(record.get("benchmark_id") or "")
            mode = str(record.get("mode") or "")
            if benchmark_id and mode:
                grouped[benchmark_id].add(mode)
    failures = []
    for benchmark_id, modes in grouped.items():
        if modes != set(FOUR_MODES):
            failures.append(f"operation_log_non_four_mode_benchmark:{benchmark_id}:{','.join(sorted(modes))}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())

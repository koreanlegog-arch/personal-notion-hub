#!/usr/bin/env python3
"""Compatibility wrapper for the workspace benchmark catalog runner."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROOT_BENCHMARK_SCRIPT = ROOT / "scripts" / "harness_benchmark_catalog_runner.py"
PROJECT_ADAPTER = ROOT / "ops" / "benchmarks" / "projects" / "personal_notion_hub.json"


def main() -> int:
    command = [
        sys.executable,
        str(ROOT_BENCHMARK_SCRIPT),
        "--project-adapter",
        str(PROJECT_ADAPTER),
        *sys.argv[1:],
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

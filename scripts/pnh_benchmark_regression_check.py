#!/usr/bin/env python3
"""Compatibility wrapper for the workspace benchmark regression check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROOT_BENCHMARK_SCRIPT = ROOT / "scripts" / "harness_benchmark_regression_check.py"


def main() -> int:
    command = [sys.executable, str(ROOT_BENCHMARK_SCRIPT), *sys.argv[1:]]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

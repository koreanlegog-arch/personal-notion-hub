#!/usr/bin/env python3
"""Compile-only smoke check for PNH real data privacy gate script."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = subprocess.run(
        ["python3", "-m", "py_compile", str(ROOT / "scripts" / "pnh_real_data_privacy_gate.py")],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr)
    print("pnh_real_data_privacy_gate_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

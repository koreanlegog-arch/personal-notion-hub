#!/usr/bin/env python3
"""Smoke check for tailnet companion API helper scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for rel in [
        "scripts/pnh_tailnet_companion_api_start.sh",
        "scripts/pnh_tailnet_companion_api_stop.sh",
    ]:
        result = subprocess.run(["bash", "-n", str(ROOT / rel)], capture_output=True, text=True, timeout=10, check=False)
        assert_true(result.returncode == 0, result.stderr)
    status_compile = subprocess.run(
        ["python3", "-m", "py_compile", str(ROOT / "scripts" / "pnh_tailnet_companion_api_status.py")],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert_true(status_compile.returncode == 0, status_compile.stderr)
    print("pnh_tailnet_companion_api_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

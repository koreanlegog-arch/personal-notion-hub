#!/usr/bin/env python3
"""Smoke check for pnh_doc_script_drift_check.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pnh-doc-script-drift-") as temp_dir:
        out_path = Path(temp_dir) / "drift.json"
        result = subprocess.run(
            [sys.executable, "scripts/pnh_doc_script_drift_check.py", "--out", str(out_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(result.stderr or result.stdout, file=sys.stderr)
            return 2
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        if payload.get("missingScriptRefs"):
            print("unexpected_missing_script_refs", file=sys.stderr)
            return 3
        if payload.get("scriptRefCount", 0) < 20:
            print("unexpectedly_low_script_ref_count", file=sys.stderr)
            return 4
        if payload.get("privateValuesPrinted") is not False or payload.get("tokenValuePrinted") is not False:
            print("sensitive_output_flags_invalid", file=sys.stderr)
            return 5
    print("pnh_doc_script_drift_check_smoke_check=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

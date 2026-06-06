#!/usr/bin/env python3
"""Smoke check for semantic worker progress parsing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "progress-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        state = temp / "state.json"
        out = temp / "progress.json"
        state.write_text(json.dumps({"packet-1": {"privateNote": PRIVATE_MARKER}}, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_worker_progress_parse.py"),
                "--packet-id",
                "packet-1",
                "--text",
                "QA verification passed and worker_done completed.",
                "--state-file",
                str(state),
                "--out",
                str(out),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        payload = json.loads(state.read_text(encoding="utf-8"))
        assert_true(payload["packet-1"]["semanticProgress"]["status"] == "done", "semantic_status_not_saved=true")
        assert_true(payload["packet-1"]["privateNote"] == PRIVATE_MARKER, "existing_private_metadata_lost=true")

    print("pnh_worker_progress_parse_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

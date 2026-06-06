#!/usr/bin/env python3
"""Smoke check for worker progress batch import."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "progress-batch-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        state = temp / "state.json"
        input_json = temp / "progress.json"
        out = temp / "batch.json"
        state.write_text(json.dumps({"packet-a": {"privateNote": PRIVATE_MARKER}}, ensure_ascii=False), encoding="utf-8")
        input_json.write_text(
            json.dumps([{"packetId": "packet-a", "text": "Implementation done and QA passed."}], ensure_ascii=False),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_worker_progress_batch_import.py"),
                "--input-json",
                str(input_json),
                "--state-file",
                str(state),
                "--out",
                str(out),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["entriesProcessed"] == 1, "entry_count_mismatch=true")
        state_payload = json.loads(state.read_text(encoding="utf-8"))
        assert_true(state_payload["packet-a"]["semanticProgress"]["status"] == "done", "semantic_progress_missing=true")

    print("pnh_worker_progress_batch_import_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

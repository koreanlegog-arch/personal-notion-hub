#!/usr/bin/env python3
"""Smoke check for OpenClaw worker-session metadata capture."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MESSAGE = "synthetic-private-openclaw-worker-message"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        fake_bin = temp_path / "bin"
        fake_bin.mkdir()
        fake_openclaw = fake_bin / "openclaw"
        fake_openclaw.write_text(
            "#!/usr/bin/env sh\n"
            "printf '%s\\n' '{\"sessionId\":\"fake-openclaw-session-001\",\"ok\":true}'\n",
            encoding="utf-8",
        )
        fake_openclaw.chmod(fake_openclaw.stat().st_mode | stat.S_IXUSR)

        state = temp_path / "state.json"
        run_dir = temp_path / "run"
        out_env = os.environ.copy()
        out_env["PATH"] = f"{fake_bin}{os.pathsep}{out_env.get('PATH', '')}"

        dry_run = run_capture(state, run_dir, env=out_env)
        assert_true(dry_run.returncode == 0, f"capture_dry_run_failed={dry_run.stderr.strip()}")
        dry_payload = json.loads(dry_run.stdout)
        assert_true(dry_payload["externalAgentRunPerformed"] is False, "dry_run_performed_agent_run=true")
        assert_true(dry_payload["writesPerformed"] is False, "dry_run_performed_write=true")
        assert_true("openclawEnvSet" in dry_payload, "openclaw_env_status_missing=true")
        assert_true(PRIVATE_MESSAGE not in dry_run.stdout, "private_message_leaked_in_dry_run=true")

        blocked = run_capture(state, run_dir, env=out_env, apply=True, approve=False)
        assert_true(blocked.returncode == 2, "apply_without_openclaw_approval_allowed=true")
        assert_true("approve-openclaw-agent-run" in blocked.stderr, "approval_gate_message_missing=true")

        applied = run_capture(state, run_dir, env=out_env, apply=True, approve=True)
        assert_true(applied.returncode == 0, f"capture_apply_failed={applied.stderr.strip()}")
        assert_true(PRIVATE_MESSAGE not in applied.stdout, "private_message_leaked_in_apply=true")
        apply_payload = json.loads(applied.stdout)
        assert_true(apply_payload["externalAgentRunPerformed"] is True, "agent_run_not_recorded=true")
        assert_true(apply_payload["replyDelivered"] is False, "reply_delivery_not_disabled=true")
        state_payload = json.loads(state.read_text(encoding="utf-8"))
        record = state_payload["capture-openclaw-smoke-001"]
        assert_true(record["workerSessionId"] == "fake-openclaw-session-001", "worker_session_id_not_saved=true")
        assert_true(record["workerStatus"] == "done", "worker_status_not_saved=true")
        assert_true("workerEvidenceRef" in record, "worker_evidence_ref_missing=true")

    print("pnh_openclaw_worker_capture_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def run_capture(
    state: Path,
    run_dir: Path,
    *,
    env: dict[str, str],
    apply: bool = False,
    approve: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_openclaw_worker_capture.py"),
        "--packet-id",
        "capture-openclaw-smoke-001",
        "--agent",
        "qa",
        "--session-key",
        "pnh:capture-openclaw-smoke-001:qa",
        "--message",
        PRIVATE_MESSAGE,
        "--thinking",
        "low",
        "--timeout",
        "30",
        "--state-file",
        str(state),
        "--run-dir",
        str(run_dir),
    ]
    if apply:
        command.append("--apply")
    if approve:
        command.append("--approve-openclaw-agent-run")
    return subprocess.run(command, capture_output=True, text=True, timeout=15, check=False, env=env)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

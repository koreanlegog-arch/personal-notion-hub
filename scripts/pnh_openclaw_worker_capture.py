#!/usr/bin/env python3
"""Run an OpenClaw agent turn and record redacted worker metadata for PNH.

Default mode is dry-run. Apply mode requires an explicit approval flag because
it can invoke a configured model provider through OpenClaw. The script never
delivers the reply to Discord and stores only metadata in the local dispatch
state file.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_RUN_DIR = ROOT / "ops" / "runs" / "PNH-OPENCLAW-WORKER-CAPTURE-20260605"
DEFAULT_OPENCLAW_ENV = Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"
ALLOWED_THINKING = {"off", "minimal", "low", "medium", "high", "xhigh", "adaptive", "max"}


class OpenClawWorkerCaptureError(ValueError):
    """Raised when a worker capture command is unsafe or failed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture an OpenClaw worker-session result into PNH dispatch state.")
    parser.add_argument("--packet-id", required=True, help="PNH capture/packet id to update.")
    parser.add_argument("--agent", default="qa", help="OpenClaw agent id.")
    parser.add_argument("--session-key", default="", help="Explicit OpenClaw session key. Default: pnh:<packet-id>:<agent>.")
    parser.add_argument("--message", default="", help="Worker prompt. Use a non-sensitive scoped task packet.")
    parser.add_argument("--message-file", default="", help="Read worker prompt from a local file.")
    parser.add_argument("--thinking", default="low", choices=sorted(ALLOWED_THINKING), help="OpenClaw thinking level.")
    parser.add_argument("--timeout", type=int, default=180, help="OpenClaw command timeout seconds.")
    parser.add_argument("--openclaw-env", default=str(DEFAULT_OPENCLAW_ENV), help="Optional env file for gateway credentials.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR), help="Metadata evidence output directory.")
    parser.add_argument("--apply", action="store_true", help="Run OpenClaw and update local dispatch state.")
    parser.add_argument("--approve-openclaw-agent-run", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    try:
        packet_id = compact(args.packet_id, "packet id", max_len=160)
        agent = compact(args.agent, "agent", max_len=80)
        session_key = compact(args.session_key or f"pnh:{packet_id}:{agent}", "session key", max_len=220)
        message = load_message(args.message, args.message_file)
        command = build_command(agent, session_key, message, args.thinking, args.timeout)
        state_path = Path(args.state_file)
        run_dir = Path(args.run_dir)
        result: dict[str, Any] = {
            "openclawWorkerCapture": True,
            "mode": "apply" if args.apply else "dry-run",
            "packetId": packet_id,
            "agent": agent,
            "sessionKey": session_key,
            "thinking": args.thinking,
            "timeoutSeconds": args.timeout,
            "openclawEnvSet": Path(args.openclaw_env).exists(),
            "stateFile": safe_path_label(state_path),
            "runDir": safe_path_label(run_dir),
            "writesPerformed": False,
            "externalAgentRunPerformed": False,
            "replyDelivered": False,
            "privateValuesPrinted": False,
            "plannedCommand": redact_command(command),
        }
        if not args.apply:
            write_evidence(run_dir, result)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        if not args.approve_openclaw_agent_run:
            raise OpenClawWorkerCaptureError("--apply requires --approve-openclaw-agent-run")
        env = os.environ.copy()
        env.update(read_env_file(Path(args.openclaw_env)))
        completed = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout + 15, check=False, env=env)
        metadata = summarize_completed_process(completed, session_key)
        result.update(
            {
                "externalAgentRunPerformed": True,
                "workerStatus": metadata["workerStatus"],
                "workerSessionId": metadata["workerSessionId"],
                "returnCode": completed.returncode,
                "stdoutBytes": len(completed.stdout.encode("utf-8")),
                "stderrBytes": len(completed.stderr.encode("utf-8")),
            }
        )
        result["writesPerformed"] = True
        evidence_path = run_dir / "openclaw_worker_capture_metadata.json"
        result["workerEvidenceRef"] = safe_path_label(evidence_path)
        write_evidence(run_dir, result)
        update_state(state_path, packet_id, metadata, result["workerEvidenceRef"])
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if completed.returncode == 0 else 2
    except (OSError, subprocess.TimeoutExpired, OpenClawWorkerCaptureError) as exc:
        print(f"pnh_openclaw_worker_capture=false error={exc}", file=sys.stderr)
        return 2


def load_message(message: str, message_file: str) -> str:
    if message_file:
        text = Path(message_file).read_text(encoding="utf-8")
    else:
        text = message
    text = text.strip()
    if not text:
        raise OpenClawWorkerCaptureError("message or message-file is required")
    if len(text.encode("utf-8")) > 16 * 1024:
        raise OpenClawWorkerCaptureError("message is too large")
    return text


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue
        env[key] = value.strip().strip('"').strip("'")
    return env


def build_command(agent: str, session_key: str, message: str, thinking: str, timeout: int) -> list[str]:
    if timeout < 30 or timeout > 900:
        raise OpenClawWorkerCaptureError("timeout must be between 30 and 900 seconds")
    return [
        "openclaw",
        "agent",
        "--agent",
        agent,
        "--session-key",
        session_key,
        "--message",
        message,
        "--thinking",
        thinking,
        "--timeout",
        str(timeout),
        "--json",
    ]


def summarize_completed_process(completed: subprocess.CompletedProcess[str], session_key: str) -> dict[str, str]:
    payload = parse_json_object(completed.stdout)
    worker_session_id = first_text(
        payload,
        [
            ("sessionId",),
            ("session", "id"),
            ("payload", "sessionId"),
            ("payload", "session", "id"),
            ("result", "sessionId"),
        ],
    )
    if not worker_session_id:
        worker_session_id = session_key
    return {
        "workerSessionId": worker_session_id,
        "workerStatus": "done" if completed.returncode == 0 else "failed",
    }


def parse_json_object(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def first_text(payload: dict[str, Any], paths: list[tuple[str, ...]]) -> str:
    for path in paths:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if isinstance(current, str) and current.strip():
            return current.strip()
    return ""


def update_state(state_path: Path, packet_id: str, metadata: dict[str, str], evidence_ref: str) -> None:
    state = load_state(state_path)
    record = dict(state.get(packet_id, {}))
    now = utc_now()
    record.update(
        {
            "workerSessionId": metadata["workerSessionId"],
            "workerStatus": metadata["workerStatus"],
            "workerEvidenceRef": evidence_ref,
            "workerResultRecordedAt": now,
            "updatedAt": now,
        }
    )
    state[packet_id] = record
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(state_path, 0o600)
    except OSError:
        pass


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OpenClawWorkerCaptureError("dispatch state must be an object")
    return value


def write_evidence(run_dir: Path, result: dict[str, Any]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "openclaw_worker_capture_metadata.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def redact_command(command: list[str]) -> list[str]:
    redacted = list(command)
    if "--message" in redacted:
        index = redacted.index("--message") + 1
        if index < len(redacted):
            redacted[index] = "[redacted-message]"
    return redacted


def compact(value: Any, label: str, *, max_len: int) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip()
    if not text:
        raise OpenClawWorkerCaptureError(f"{label} is required")
    if len(text) > max_len:
        raise OpenClawWorkerCaptureError(f"{label} is too long")
    return text


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

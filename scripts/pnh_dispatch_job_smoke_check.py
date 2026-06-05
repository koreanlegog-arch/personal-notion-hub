#!/usr/bin/env python3
"""Smoke check for the PNH idempotent dispatch job."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_TITLE = "synthetic-dispatch-private-title"
PRIVATE_BODY = "synthetic-dispatch-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        packet = temp_root / "packet.json"
        out = temp_root / "plan.json"
        state = temp_root / "state.json"
        packet.write_text(
            json.dumps(
                {
                    "id": "capture-dispatch-smoke-001",
                    "payloadType": "pnh_mobile_command_packet",
                    "commandType": "task_request",
                    "commandStatus": "stored",
                    "dispatchState": "not_dispatched",
                    "priority": "high",
                    "sensitivity": "highly_sensitive",
                    "title": PRIVATE_TITLE,
                    "body": PRIVATE_BODY,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        dry_run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_job.py"),
                "--input-json",
                str(packet),
                "--repo",
                "example/private-ledger",
                "--discord-target",
                "channel:123",
                "--state-file",
                str(state),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(dry_run.returncode == 0, f"dispatch_dry_run_failed={dry_run.stderr.strip()}")
        plan_text = out.read_text(encoding="utf-8")
        combined = dry_run.stdout + plan_text
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")
        plan = json.loads(plan_text)
        assert_true(plan["writesPerformed"] is False, "dry_run_performed_write=true")
        assert_true(plan["privateValuesIncluded"] is False, "private_values_included=true")
        assert_true(plan["tokenValuePrinted"] is False, "token_value_printed=true")
        assert_true(plan["planned"]["discordThreadName"] == "PNH-capture-dispatch-smoke-001-dispatch", "thread_name_contract_failed=true")

        state.write_text(
            json.dumps(
                {
                    "capture-dispatch-smoke-001": {
                        "githubIssueUrl": "https://github.com/example/private-ledger/issues/1",
                        "discordThreadId": "1234567890",
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        idempotent_dry_run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_job.py"),
                "--input-json",
                str(packet),
                "--repo",
                "example/private-ledger",
                "--discord-target",
                "channel:123",
                "--state-file",
                str(state),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(idempotent_dry_run.returncode == 0, f"idempotent_dry_run_failed={idempotent_dry_run.stderr.strip()}")
        idempotent_plan = json.loads(out.read_text(encoding="utf-8"))
        assert_true(idempotent_plan["idempotency"]["existingGitHubIssue"] is True, "dry_run_did_not_read_existing_issue=true")
        assert_true(idempotent_plan["idempotency"]["existingDiscordThread"] is True, "dry_run_did_not_read_existing_thread=true")

        duplicate_detection_no_token = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_job.py"),
                "--input-json",
                str(packet),
                "--repo",
                "example/private-ledger",
                "--discord-target",
                "channel:123",
                "--state-file",
                str(temp_root / "empty-state.json"),
                "--out",
                str(out),
                "--detect-existing-github",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env={"PATH": ""},
        )
        assert_true(duplicate_detection_no_token.returncode == 0, f"duplicate_detection_dry_run_failed={duplicate_detection_no_token.stderr.strip()}")
        duplicate_plan = json.loads(out.read_text(encoding="utf-8"))
        detection = duplicate_plan["idempotency"]["githubDuplicateDetection"]
        assert_true(detection["enabled"] is True, "github_duplicate_detection_not_enabled=true")
        assert_true(detection["tokenSet"] is False, "github_duplicate_detection_token_unexpected=true")
        assert_true(detection["match"] is False, "github_duplicate_detection_false_match=true")
        assert_true("not_set" in detection["error"], "github_duplicate_detection_error_missing=true")

        blocked_apply = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_job.py"),
                "--input-json",
                str(packet),
                "--repo",
                "example/private-ledger",
                "--state-file",
                str(state),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(blocked_apply.returncode == 2, "apply_without_approval_allowed=true")
        assert_true("approve-external-write" in blocked_apply.stderr, "apply_gate_message_missing=true")

        fake_bin = temp_root / "fake-bin"
        fake_bin.mkdir()
        fake_log = temp_root / "fake-calls.log"
        fake_gh = fake_bin / "gh"
        fake_gh.write_text(
            """#!/usr/bin/env python3
import json
import os
import sys
with open(os.environ["PNH_FAKE_LOG"], "a", encoding="utf-8") as handle:
    handle.write("gh " + " ".join(sys.argv[1:]) + "\\n")
args = sys.argv[1:]
if args[:2] == ["auth", "status"]:
    raise SystemExit(0)
if args and args[0] == "api":
    endpoint = args[1] if len(args) > 1 else ""
    if endpoint.endswith("/issues") and "POST" in args:
        print(json.dumps({"number": 42, "html_url": "https://github.com/example/private-ledger/issues/42"}))
        raise SystemExit(0)
    if "/comments" in endpoint:
        print(json.dumps({"id": 99}))
        raise SystemExit(0)
    print(json.dumps([]))
    raise SystemExit(0)
raise SystemExit(1)
""",
            encoding="utf-8",
        )
        fake_openclaw = fake_bin / "openclaw"
        fake_openclaw.write_text(
            """#!/usr/bin/env python3
import json
import os
import sys
with open(os.environ["PNH_FAKE_LOG"], "a", encoding="utf-8") as handle:
    handle.write("openclaw " + " ".join(sys.argv[1:]) + "\\n")
args = sys.argv[1:]
if args[:3] == ["message", "thread", "create"]:
    print(json.dumps({"payload": {"thread": {"id": "9876543210"}}}))
    raise SystemExit(0)
if args[:2] == ["message", "send"]:
    print("synthetic discord send failure", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(1)
""",
            encoding="utf-8",
        )
        fake_gh.chmod(0o755)
        fake_openclaw.chmod(0o755)
        fake_env = os.environ.copy()
        fake_env.pop("GITHUB_TOKEN", None)
        fake_env["PATH"] = str(fake_bin) + os.pathsep + fake_env.get("PATH", "")
        fake_env["PNH_FAKE_LOG"] = str(fake_log)
        fake_openclaw_env = temp_root / "openclaw.env"
        fake_token_key = "OPENCLAW_" + "GATEWAY_TOKEN"
        fake_openclaw_env.write_text(f"{fake_token_key}=dummy-redacted-test-token\n", encoding="utf-8")
        checkpoint_state = temp_root / "checkpoint-state.json"
        first_apply = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_job.py"),
                "--input-json",
                str(packet),
                "--repo",
                "example/private-ledger",
                "--discord-target",
                "channel:123",
                "--state-file",
                str(checkpoint_state),
                "--openclaw-env",
                str(fake_openclaw_env),
                "--apply",
                "--approve-external-write",
                "--approve-discord-dispatch",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=fake_env,
        )
        assert_true(first_apply.returncode == 2, "partial_dispatch_failure_not_exercised=true")
        checkpoint = json.loads(checkpoint_state.read_text(encoding="utf-8"))
        checkpoint_record = checkpoint["capture-dispatch-smoke-001"]
        assert_true(checkpoint_record["githubIssueNumber"] == 42, "github_checkpoint_missing=true")
        assert_true(checkpoint_record["discordThreadId"] == "9876543210", "discord_checkpoint_missing=true")
        assert_true(checkpoint_record["lastDispatchCheckpoint"] == "discord_thread_created", "discord_checkpoint_label_missing=true")

        second_apply = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_job.py"),
                "--input-json",
                str(packet),
                "--repo",
                "example/private-ledger",
                "--discord-target",
                "channel:123",
                "--state-file",
                str(checkpoint_state),
                "--openclaw-env",
                str(fake_openclaw_env),
                "--apply",
                "--approve-external-write",
                "--approve-discord-dispatch",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=fake_env,
        )
        assert_true(second_apply.returncode == 0, f"checkpoint_retry_failed={second_apply.stderr.strip()}")
        fake_log_text = fake_log.read_text(encoding="utf-8")
        assert_true(fake_log_text.count("openclaw message thread create") == 1, "retry_created_duplicate_thread=true")

    print("pnh_dispatch_job_smoke_check_pass=true")
    print("writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())

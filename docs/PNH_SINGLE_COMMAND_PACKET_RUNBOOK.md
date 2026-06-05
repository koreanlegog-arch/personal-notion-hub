# PNH Single Command Packet Runbook

Status: ready for bounded PNH test and implementation runs
Date: 2026-06-05

## Purpose

This runbook converts one PNH private-inbox command packet into a complete
metadata-safe worker dispatch cycle:

```text
private inbox command packet
-> queue selection
-> GitHub Issue ledger
-> Discord/OpenClaw worker thread
-> OpenClaw worker-session capture
-> GitHub dispatch label reconciliation
-> local dispatch state refresh
-> supervisor review summary
```

The goal is to run the same operational flow without rediscovering command
order, evidence paths, label rules, or refresh sequencing each time.

## Delegation Boundary

The project `AGENTS.md` delegates bounded PNH test and implementation writes for:

- GitHub Issue creation/update
- Discord/OpenClaw thread/message creation
- local dispatch-state updates
- metadata-safe OpenClaw worker/model execution
- label reconciliation
- Git commit/push for scoped PNH work

This runbook still does not allow:

- raw private command bodies in worker prompts, logs, GitHub Issues, or Discord
- secret values in tracked files, screenshots, chat, or evidence
- daemon/scheduler activation
- unbounded worker/model execution
- real phone/contact/calendar/call/recording adapters
- public exposure beyond owner-only local/tailnet scope

## Inputs

Required:

- an encrypted private-inbox command capture with `kind` in:
  - `project_brief`
  - `task_request`
  - `daily_command`
  - `urgent_approval`
- `gh` authenticated for `koreanlegog-arch/personal-notion-hub`
- OpenClaw gateway available
- Discord/OpenClaw target channel configured
- `companion/private/pnh_dispatch_state.json` available or creatable

Optional:

- a known capture id, if a specific inbox item must be dispatched
- a custom run id, if evidence needs a named directory

## Output Evidence

Each complete packet run should leave evidence in:

```text
ops/runs/<RUN_ID>/
ops/runs/<RUN_ID>/dispatch_pilot/
ops/runs/<RUN_ID>/worker_capture/
ops/runs/<RUN_ID>/label_reconciliation/
ops/runs/PNH-DISPATCH-STATUS-REFRESH-20260605/dispatch_status_refresh.json
ops/runs/PNH-DISCORD-THREAD-STATUS-REFRESH-20260605/discord_thread_status_refresh.json
ops/runs/PNH-DISPATCH-EVIDENCE-SUMMARY-20260605/dispatch_evidence_summary.json
ops/runs/PNH-SUPERVISOR-REVIEW-SUMMARY-20260605/supervisor_review_summary.md
```

Tracked evidence must remain metadata-only.

## Safe Sequential Command Packet

Preferred wrapper command:

```bash
python3 scripts/pnh_single_command_packet.py --apply
```

Dry-run wrapper command:

```bash
python3 scripts/pnh_single_command_packet.py
```

Browser-triggered dry-run is available from the Launch UI after pairing with
the local companion. Browser-triggered apply remains locked unless the
companion runtime is intentionally started with:

```bash
PNH_BROWSER_SINGLE_PACKET_APPLY_ENABLED=1
```

and the request includes the apply confirmation phrase. This keeps mobile/UI
dry-run convenient while preventing accidental GitHub, Discord, or worker
side effects from a browser click.

The detailed manual sequence below remains the reference procedure used by the
wrapper and is useful for troubleshooting.

Set paths for a single run:

```bash
RUN_ID="PNH-COMMAND-PACKET-$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="ops/runs/${RUN_ID}"
QUEUE_PLAN="${RUN_DIR}/queue_plan.json"
PILOT_DIR="${RUN_DIR}/dispatch_pilot"
WORKER_DIR="${RUN_DIR}/worker_capture"
LABEL_DIR="${RUN_DIR}/label_reconciliation"
export RUN_ID RUN_DIR QUEUE_PLAN PILOT_DIR WORKER_DIR LABEL_DIR
mkdir -p "$RUN_DIR" "$WORKER_DIR" "$LABEL_DIR"
```

Plan the queue without external writes:

```bash
python3 scripts/pnh_unattended_dispatch_queue_plan.py --out "$QUEUE_PLAN"
python3 scripts/pnh_unattended_dispatch_readiness.py \
  --queue-plan "$QUEUE_PLAN" \
  --out "${RUN_DIR}/readiness.json"
```

Apply one bounded dispatch batch:

```bash
python3 scripts/pnh_unattended_dispatch_pilot.py \
  --queue-plan "$QUEUE_PLAN" \
  --run-dir "$PILOT_DIR" \
  --apply \
  --approve-unattended-pilot \
  --detect-existing-github
```

Extract the selected packet id from the pilot result:

```bash
PACKET_ID="$(python3 - <<'PY'
import json
import os
from pathlib import Path
pilot_result = Path(os.environ["PILOT_DIR"]) / "pilot_result.json"
payload = json.loads(pilot_result.read_text(encoding="utf-8"))
print(payload.get("selectedCaptureId", ""))
PY
)"
export PACKET_ID
test -n "$PACKET_ID"
```

Refresh external metadata in safe order:

```bash
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
python3 scripts/pnh_discord_thread_status_refresh.py --openclaw-read --approve-discord-read --apply --limit 10
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
```

Create a metadata-safe worker prompt:

```bash
python3 - <<'PY'
import json
import os
from pathlib import Path
state = json.loads(Path("companion/private/pnh_dispatch_state.json").read_text(encoding="utf-8"))
packet_id = os.environ["PACKET_ID"]
worker_dir = Path(os.environ["WORKER_DIR"])
record = state.get(packet_id, {})
prompt = f"""You are the QA worker for Personal_Notion_Hub.

Task:
Review the metadata-only PNH dispatch record for packet {packet_id} and provide a concise QA status for the supervisor.

Important boundaries:
- Do not request or expose raw private command body content.
- Treat the private command body as local-vault only.
- Use only metadata-safe facts from dispatch state.
- Do not deliver a Discord reply; this run is metadata capture only.

Metadata:
- GitHub Issue: {record.get("githubIssueNumber", "")}
- Discord thread: {record.get("discordThreadId", "")}
- current worker status: {record.get("workerStatus", "")}
- current GitHub label state: {", ".join(record.get("githubIssueLabels", []))}

Expected output:
- session status
- readiness for supervisor review after worker metadata capture
- remaining risks or next action
"""
worker_dir.mkdir(parents=True, exist_ok=True)
(worker_dir / "worker_prompt.txt").write_text(prompt, encoding="utf-8")
PY
```

Run bounded OpenClaw worker capture:

```bash
python3 scripts/pnh_openclaw_worker_capture.py \
  --packet-id "$PACKET_ID" \
  --agent qa \
  --message-file "${WORKER_DIR}/worker_prompt.txt" \
  --thinking low \
  --timeout 300 \
  --run-dir "$WORKER_DIR"

python3 scripts/pnh_openclaw_worker_capture.py \
  --packet-id "$PACKET_ID" \
  --agent qa \
  --message-file "${WORKER_DIR}/worker_prompt.txt" \
  --thinking low \
  --timeout 300 \
  --run-dir "$WORKER_DIR" \
  --apply \
  --approve-openclaw-agent-run
```

Refresh state and reconcile GitHub labels:

```bash
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
python3 scripts/pnh_discord_thread_status_refresh.py --openclaw-read --approve-discord-read --apply --limit 10
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply

python3 scripts/pnh_external_reconciliation_plan.py \
  --out "${LABEL_DIR}/external_reconciliation_plan.json"

python3 scripts/pnh_github_label_reconciliation_apply.py \
  --plan-json "${LABEL_DIR}/external_reconciliation_plan.json" \
  --out "${LABEL_DIR}/github_label_reconciliation_dry_run.json"

python3 scripts/pnh_github_label_reconciliation_apply.py \
  --plan-json "${LABEL_DIR}/external_reconciliation_plan.json" \
  --out "${LABEL_DIR}/github_label_reconciliation_apply.json" \
  --apply \
  --approve-external-write
```

Finalize state and supervisor evidence:

```bash
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
python3 scripts/pnh_external_reconciliation_plan.py \
  --out "${LABEL_DIR}/post_reconciliation_plan.json"
python3 scripts/pnh_dispatch_state_status.py --include-urls
python3 scripts/pnh_dispatch_evidence_summary.py
python3 scripts/pnh_supervisor_review_summary.py
```

## Expected Pass Criteria

For the selected packet:

- GitHub Issue is set.
- Discord thread is set.
- worker session is set.
- worker status is `done`.
- GitHub dispatch label is `dispatch:worker-done`.
- evidence completeness is `100`.
- `plannedExternalWriteCount` is `0` after final reconciliation.
- no token values or raw private bodies are printed.

## Verification Commands

Run after the packet:

```bash
python3 scripts/smoke_check.py
python3 scripts/pnh_openclaw_worker_capture_smoke_check.py
python3 scripts/pnh_external_reconciliation_plan_smoke_check.py
python3 scripts/pnh_github_label_reconciliation_apply_smoke_check.py
python3 scripts/pnh_dispatch_status_refresh_smoke_check.py
python3 scripts/pnh_discord_thread_status_refresh_smoke_check.py
python3 scripts/pnh_dispatch_evidence_summary_smoke_check.py
python3 scripts/pnh_supervisor_review_summary_smoke_check.py
python3 scripts/pnh_command_packet_status_smoke_check.py
git diff --check
```

Secret scan for run evidence:

```bash
rg -n "OPENCLAW_GATEWAY_TOKEN|DISCORD_BOT_TOKEN|GITHUB_TOKEN=|Bearer [A-Za-z0-9_\\-]+|gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9]|password\\s*[=:]|secret\\s*[=:]" \
  docs ops/runs/"${RUN_ID}" || true
```

## Failure Recovery

If dispatch apply fails before external writes:

- keep the run directory
- inspect `pilot_result.json` or command stderr
- rerun the queue plan
- do not manually edit private inbox rows

If external records are created but local state is inconsistent:

- restore from the run-local rollback snapshot when appropriate
- rerun GitHub refresh, Discord refresh, and GitHub refresh again in that order
- rerun `pnh_external_reconciliation_plan.py`

If label reconciliation remains pending:

- inspect the label plan JSON
- rerun dry-run apply first
- then rerun apply only if the action is bounded to the current PNH packet

If worker capture fails:

- do not expose raw private body to recover
- inspect metadata only: return code, stdout byte count, stderr byte count
- rerun worker capture with the same metadata-safe prompt if the failure is transient

## Wrapper Script

The guarded wrapper is:

```bash
python3 scripts/pnh_single_command_packet.py
```

Default mode is dry-run. Apply mode performs the bounded delegated workflow:

```bash
python3 scripts/pnh_single_command_packet.py --apply
```

Useful options:

```bash
python3 scripts/pnh_single_command_packet.py \
  --run-id PNH-COMMAND-PACKET-MY-RUN \
  --agent qa \
  --thinking low \
  --timeout 300
```

The wrapper enforces:

- unique run directory creation
- single-packet apply lock
- queue planning before apply
- bounded pilot apply
- sequential GitHub/Discord/GitHub refresh
- metadata-safe worker prompt generation
- OpenClaw worker capture without Discord reply delivery
- GitHub label reconciliation dry-run before apply
- final evidence summary and supervisor review summary

## Current Known Limitation

The wrapper still runs a single queue item per invocation. It is not a daemon,
scheduler, or background unattended service.

Future work can add a higher-level batch runner if repeated unattended
processing is needed.

# Current Capabilities

Date: 2026-06-05

This document summarizes what the current `Personal_Notion_Hub` can do now, what requires explicit operator action, and what remains out of scope.

## Ready To Use Now

### Personal Hub UI

- Dashboard, Projects, Tasks, Notes, Routines, Links, Settings
- Quick Capture
- Launch packet creation
- Assistant input capture
- Assistant dispatch intent selection for direct command-packet ingress
- localStorage persistence
- JSON export/import
- light/dark theme
- responsive desktop/mobile layout baseline

### Local Private Capture

- Local companion server
- one-time browser pairing
- memory-only browser session token
- private inbox status and redacted summaries
- encrypted vault mode for sensitive local captures
- `windows-dpapi-file` passphrase storage
- encrypted backup/restore/delete/rotation smoke coverage

### Phone/Remote Owner Access

- private LAN phone ingress mode
- Tailscale owner-only access runbook
- phone browser can use the companion-served PNH UI when the local companion is running and the allowed origin matches
- owner live capture readiness check for private pairing/input handoff

### Launch-To-Worker MVP

The current verified Launch flow can:

1. accept a Launch/project brief in the browser
2. send the latest Launch packet to local companion private storage
3. export a metadata-only dispatch candidate
4. create or detect a GitHub Issue ledger entry without raw private body
5. create a Discord/OpenClaw worker thread through delegated or gated apply mode
6. capture bounded OpenClaw worker-session metadata without delivering a Discord reply
7. refresh GitHub Issue state and dispatch labels into local dispatch state
8. apply delegated or approved GitHub dispatch label reconciliation
9. refresh Discord/OpenClaw thread metadata without storing message content
10. show dispatch state in the Launch UI
11. show single command packet wrapper status in the Launch UI
12. run a browser-triggered single command packet dry-run through the paired local companion
13. confirm mapping and task status into browser-local Launch, Projects, and Tasks
14. generate supervisor review summary
15. run bounded unattended dispatch pilot batches with queue limits and rollback snapshot
16. run metadata-only auto-dispatch dry-runs from the encrypted private inbox
17. skip already-dispatched capture IDs before selecting an automatic dispatch candidate
18. seed a synthetic encrypted command capture for end-to-end dispatch rehearsal
19. verify owner live capture readiness before the owner enters real private content
20. send Assistant input as a selected command type without metadata alias correction

Latest owner live command-packet dispatch:

- GitHub Issue: `#6`
- Discord thread id: `1512364450869547130`
- worker session: `pnh:assistant-capture-capture-mq0mgu4q-uvzyzm0s:qa`
- command type: `task_request`
- task status: `worker_done`
- evidence completeness: `100%`
- raw private body read: `false`

Current verified Launch record:

- GitHub Issue: `#2`
- Discord thread id: `1512295718054793419`
- worker session: `pnh:capture-5345e37040604a2fca64f317:qa`
- GitHub dispatch label: `dispatch:worker-done`
- evidence completeness: `100%`

Latest completed unattended pilot record:

- GitHub Issue: `#4`
- Discord thread id: `1512323845514596373`
- worker session: `pnh:capture-3b8522ff102b0469c683b027:qa`
- GitHub dispatch label: `dispatch:worker-done`
- task status: `worker_done`
- evidence completeness: `100%`
- next action: `summarize_worker_result_for_supervisor_review`

Latest synthetic single command packet rehearsal:

- GitHub Issue: `#5`
- Discord thread id: `1512357660807270561`
- worker session: `pnh:capture-40fc5ea5d769acebdb130781:qa`
- GitHub dispatch label: `dispatch:worker-done`
- task status: `worker_done`
- evidence completeness: `100%`
- raw private body read: `false`

Latest owner live capture readiness:

- verdict: `ready_for_owner_action`
- access mode: `tailnet`
- encrypted vault ready: `true`
- plaintext inbox rows: `0`
- queue count before owner input: `0`
- pending external reconciliation writes: `0`
- material gate: owner must pair locally and enter real private command content

Previous completed unattended pilot record:

- GitHub Issue: `#3`
- Discord thread id: `1512315698351706183`
- worker session: `pnh:capture-2a0fcdefc3f169ec30c6497f:qa`
- GitHub dispatch label: `dispatch:worker-done`
- task status: `worker_done`
- current reconciliation: no pending external writes

## Commands You Can Use

### General Checks

```bash
python3 scripts/smoke_check.py
python3 scripts/sensitive_owner_readiness_check.py
python3 scripts/keychain_readiness.py
```

### Local Companion And Private Storage

```bash
python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox --enable-encrypted-vault --vault-passphrase-provider windows-dpapi-file
python3 scripts/private_inbox_status.py
python3 scripts/private_inbox_status.py --include-recent
python3 scripts/pnh_seed_synthetic_command_capture.py
python3 scripts/pnh_owner_live_capture_readiness.py
```

### Dispatch Pipeline

```bash
python3 scripts/pnh_auto_dispatch_from_inbox.py --detect-existing-github
python3 scripts/pnh_auto_dispatch_from_inbox_smoke_check.py
python3 scripts/pnh_dispatch_state_status.py
python3 scripts/pnh_dispatch_evidence_summary.py
python3 scripts/pnh_supervisor_review_summary.py
python3 scripts/pnh_dispatch_status_refresh.py --github-read
python3 scripts/pnh_external_reconciliation_plan.py
python3 scripts/pnh_discord_thread_readiness_probe.py
python3 scripts/pnh_github_label_reconciliation_apply.py
python3 scripts/pnh_discord_thread_status_refresh.py
python3 scripts/pnh_unattended_dispatch_queue_plan.py
python3 scripts/pnh_unattended_dispatch_readiness.py
python3 scripts/pnh_single_command_packet.py
python3 scripts/pnh_command_packet_status_smoke_check.py
python3 scripts/pnh_single_command_packet_browser_run_smoke_check.py
```

For the full single packet flow from private inbox to worker-done evidence, see:

- `docs/PNH_SINGLE_COMMAND_PACKET_RUNBOOK.md`

Use `--apply` only when the script's apply mode is intentionally needed and the
project `AGENTS.md` delegation or relevant approval gate has been satisfied.

### Browser QA

```bash
bash scripts/run_playwright_redacted_ui_qa.sh
bash scripts/run_playwright_launch_status_sync_qa.sh
```

### Phone/Tailscale

See:

- `docs/TAILSCALE_REMOTE_ACCESS_RUNBOOK.md`
- `docs/PHONE_INGRESS_SECURITY.md`
- `docs/OWNER_LIVE_COMMAND_CAPTURE_RUNBOOK.md`

## Requires Explicit Approval

These actions still require explicit approval because they change security posture
or expand data risk:

- adding real phone/contact/calendar/call/recording adapters
- exposing the companion beyond owner-only local or tailnet scope
- distributing the app to another user

Bounded GitHub Issue, Discord/OpenClaw thread/message, dispatch-state, and
metadata-safe unattended dispatch and worker/model test writes are delegated in
project `AGENTS.md` and do not require a separate per-run approval.

## Not Ready Yet

- unattended mobile-to-worker automation beyond bounded pilot batches and
  metadata-safe worker captures
- unattended daemon/scheduler activation
- real contact/call/recording/calendar ingestion
- multi-user distribution
- cloud sync of private data
- production auth model
- packaged desktop/mobile app
- semantic Discord/OpenClaw worker progress parsing beyond metadata-only refresh
- unattended unbounded worker/model execution
- GitHub Projects board mutation

## Practical Current Usage

Recommended current usage:

1. Run the local companion in encrypted vault mode.
2. Open PNH from local browser or owner-only phone path.
3. Create a Launch packet.
4. Send it to the workspace private inbox.
5. Run dispatch dry-run first.
6. Apply bounded GitHub/Discord/OpenClaw dispatch steps when needed for PNH
   test/implementation evidence.
7. Refresh dispatch state.
8. Confirm Launch task status into browser-local boards.
9. Read the supervisor review summary before deciding next work.

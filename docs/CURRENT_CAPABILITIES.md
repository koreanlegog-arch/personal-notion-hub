# Current Capabilities

Date: 2026-06-06

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
21. close GitHub Issues for worker_done dispatch records after redacted evidence reaches 100%
22. archive stale incomplete dispatch-state records out of active evidence summaries
23. parse redacted worker progress snippets into metadata-only semantic progress
24. import owner-exported local contacts/calendar/call-log/recording transcript files into encrypted vault storage
25. batch-plan owner-exported private data imports without printing private values
26. read live adapter readiness from environment-backed endpoints without printing URL or token values
27. fetch fixture or approved live adapter payloads into encrypted vault storage through fail-closed apply mode
28. plan unattended retry/backoff candidates for failed or blocked dispatch records
29. batch-check all live adapter slots from one readiness command
30. run bounded scheduler ticks/loops or a user-systemd timer for local status, queue, retry, evidence, and live-adapter readiness checks
31. accept authenticated phone automation adapter POST payloads into encrypted vault storage

Latest owner live command-packet dispatch:

- GitHub Issue: `#6`
- GitHub Issue state: `closed`
- Discord thread id: `1512364450869547130`
- worker session: `pnh:assistant-capture-capture-mq0mgu4q-uvzyzm0s:qa`
- command type: `task_request`
- task status: `worker_done`
- evidence completeness: `100%`
- raw private body read: `false`

Latest dispatch state cleanup:

- archived stale incomplete record: `pnh-live-openclaw-capture-20260605`
- active dispatch records: `6`
- active evidence completeness average: `100%`
- archive path: `companion/private/pnh_dispatch_state_archive.json`

Latest semantic worker progress parse:

- packet: `launch-packet-launch-mq11rzo5-8kcrgo`
- semantic status: `done`
- semantic stage: `done`
- confidence: `75`
- message content stored: `false`

Current verified Launch record:

- GitHub Issue: `#2`
- GitHub Issue state: `closed`
- Discord thread id: `1512295718054793419`
- worker session: `pnh:capture-5345e37040604a2fca64f317:qa`
- GitHub dispatch label: `dispatch:worker-done`
- evidence completeness: `100%`

Latest completed unattended pilot record:

- GitHub Issue: `#4`
- GitHub Issue state: `closed`
- Discord thread id: `1512323845514596373`
- worker session: `pnh:capture-3b8522ff102b0469c683b027:qa`
- GitHub dispatch label: `dispatch:worker-done`
- task status: `worker_done`
- evidence completeness: `100%`
- next action: `summarize_worker_result_for_supervisor_review`

Latest synthetic single command packet rehearsal:

- GitHub Issue: `#5`
- GitHub Issue state: `closed`
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
- GitHub Issue state: `closed`
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
python3 scripts/pnh_dispatch_state_cleanup.py
python3 scripts/pnh_worker_progress_parse.py --packet-id "<packet-id>" --text "<redacted progress text>"
python3 scripts/pnh_dispatch_status_refresh.py --github-read
python3 scripts/pnh_external_reconciliation_plan.py
python3 scripts/pnh_github_worker_done_closure.py
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

### Local Private Data Adapter Import

These adapters read owner-exported local files only. They do not connect to
phone APIs, cloud accounts, OAuth, or external services.

```bash
python3 scripts/pnh_private_data_adapter_import.py --adapter contacts-csv --input ./contacts.csv
python3 scripts/pnh_private_data_adapter_import.py --adapter calendar-ics --input ./calendar.ics
python3 scripts/pnh_private_data_adapter_import.py --adapter call-log-csv --input ./calls.csv
python3 scripts/pnh_private_data_adapter_import.py --adapter recording-transcript-txt --input ./recording-transcript.txt
python3 scripts/pnh_private_data_adapter_status.py
python3 scripts/pnh_private_data_adapter_batch_plan.py --input-dir ./owner-export
```

Apply mode requires encrypted vault passphrase resolution and stores records in
the local encrypted vault without printing private values.

### Live Private Data Adapter Framework

The live adapter framework is available as a guarded MVP. It can read adapter
endpoint references from local environment variables, but it does not print URL
or token values and does not contact external services unless `--fetch` or
`--apply` is intentionally used with `--approve-live-adapter`.

Supported rough adapter slots:

- `live-calendar-ics-url`
- `live-contacts-json-url`
- `live-call-log-json-url`
- `live-recording-transcript-url`

Readiness check:

```bash
python3 scripts/pnh_live_private_data_adapter_sync.py
python3 scripts/pnh_live_private_data_adapter_batch_sync.py
```

Fixture-safe fetch smoke:

```bash
python3 scripts/pnh_live_private_data_adapter_sync_smoke_check.py
python3 scripts/pnh_live_private_data_adapter_batch_sync_smoke_check.py
```

### Bounded Scheduler MVP

Scheduler scripts are available for bounded local ticks and loops. A
user-systemd timer installer is also available for WSL/systemd environments.

```bash
python3 scripts/pnh_scheduler_tick.py
python3 scripts/pnh_scheduler_loop.py --iterations 1 --interval-seconds 1
python3 scripts/pnh_scheduler_smoke_check.py
python3 scripts/pnh_scheduler_service_status.py
```

Runtime service output is written under ignored `companion/private/scheduler/`.

### Phone Automation Adapter POST

The companion can accept authenticated phone automation JSON payloads and store
them as encrypted private captures:

```text
POST /api/private/phone-adapter-captures
```

Supported adapter names:

- `phone-contacts-json`
- `phone-calendar-json`
- `phone-call-log-json`
- `phone-recording-transcript-json`

The endpoint uses the same private bearer/session authentication as
`/api/private/mobile-captures`. Responses are metadata-only and do not echo raw
phone data.

Smoke:

```bash
python3 scripts/phone_adapter_ingress_smoke_check.py
```

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

- activating new live phone/contact/calendar/call/recording API endpoints or cloud accounts with real credentials
- exposing the companion beyond owner-only local or tailnet scope
- distributing the app to another user

Bounded GitHub Issue, Discord/OpenClaw thread/message, dispatch-state, and
metadata-safe unattended dispatch and worker/model test writes are delegated in
project `AGENTS.md` and do not require a separate per-run approval.

## Not Ready Yet

- unattended mobile-to-worker automation beyond bounded pilot batches,
  metadata-safe worker captures, and bounded local scheduler ticks
- production companion server daemon activation
- production-grade live phone/contact/call/recording/calendar API ingestion
- native phone app extraction client
- multi-user distribution
- cloud sync of private data
- production auth model
- packaged desktop/mobile app
- direct semantic Discord/OpenClaw worker progress parsing from live thread bodies
- unattended unbounded worker/model execution
- GitHub Projects board mutation

## Newly Available Rough MVPs

- `scripts/pnh_dispatch_state_cleanup.py`: archives stale incomplete dispatch
  records out of the active dispatch state.
- `scripts/pnh_worker_progress_parse.py`: parses redacted worker progress text
  into metadata-only semantic progress fields without storing message content.
- `scripts/pnh_private_data_adapter_import.py`: imports owner-exported local
  contacts CSV, call-log CSV, calendar ICS, or recording transcript text into
  encrypted vault storage. It does not connect to phone APIs or cloud accounts.
- `scripts/pnh_private_data_adapter_batch_plan.py`: plans or applies local
  owner-exported adapter batches with encrypted-vault apply gates.
- `scripts/pnh_live_private_data_adapter_sync.py` and
  `scripts/pnh_live_private_data_adapter_batch_sync.py`: check live adapter
  readiness and can fetch approved live or fixture payloads without exposing
  URL or token values.
- `scripts/pnh_unattended_retry_backoff.py`: plans bounded retry candidates for
  failed or blocked dispatch records.
- `scripts/pnh_scheduler_tick.py`, `scripts/pnh_scheduler_loop.py`, and
  `scripts/pnh_scheduler_install_user_service.sh`: run bounded local scheduler
  checks manually or through a user-systemd timer.
- `POST /api/private/phone-adapter-captures`: accepts authenticated phone
  automation adapter JSON payloads and stores them in encrypted vault mode.

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

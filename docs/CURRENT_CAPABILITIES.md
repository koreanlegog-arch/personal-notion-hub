# Current Capabilities

Date: 2026-06-05

This document summarizes what the current `Personal_Notion_Hub` can do now, what requires explicit operator action, and what remains out of scope.

## Ready To Use Now

### Personal Hub UI

- Dashboard, Projects, Tasks, Notes, Routines, Links, Settings
- Quick Capture
- Launch packet creation
- Assistant input capture
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

### Launch-To-Worker MVP

The current verified Launch flow can:

1. accept a Launch/project brief in the browser
2. send the latest Launch packet to local companion private storage
3. export a metadata-only dispatch candidate
4. create or detect a GitHub Issue ledger entry without raw private body
5. create a Discord/OpenClaw worker thread after explicit approval
6. capture OpenClaw worker-session metadata without delivering a Discord reply
7. refresh GitHub Issue state and dispatch labels into local dispatch state
8. apply approved GitHub dispatch label reconciliation
9. refresh Discord/OpenClaw thread metadata without storing message content
10. show dispatch state in the Launch UI
11. confirm mapping and task status into browser-local Launch, Projects, and Tasks
12. generate supervisor review summary

Current verified live record:

- GitHub Issue: `#2`
- Discord thread id: `1512295718054793419`
- worker session: `pnh:capture-5345e37040604a2fca64f317:qa`
- GitHub dispatch label: `dispatch:worker-done`
- evidence completeness: `100%`

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
```

### Dispatch Pipeline

```bash
python3 scripts/pnh_auto_dispatch_from_inbox.py --detect-existing-github
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
```

Use `--apply` only when the script's apply mode is intentionally needed and the relevant approval gate has been satisfied.

### Browser QA

```bash
bash scripts/run_playwright_redacted_ui_qa.sh
bash scripts/run_playwright_launch_status_sync_qa.sh
```

### Phone/Tailscale

See:

- `docs/TAILSCALE_REMOTE_ACCESS_RUNBOOK.md`
- `docs/PHONE_INGRESS_SECURITY.md`

## Requires Explicit Approval

These actions create external writes, change security posture, or expand data risk:

- creating GitHub Issues from local command packets
- updating GitHub Issue labels/state/comments
- creating Discord/OpenClaw threads or messages
- running OpenClaw worker/model calls
- enabling unattended dispatch
- adding real phone/contact/calendar/call/recording adapters
- exposing the companion beyond owner-only local or tailnet scope
- distributing the app to another user

## Not Ready Yet

- unattended mobile-to-worker automation
- unattended dispatch pilot activation
- real contact/call/recording/calendar ingestion
- multi-user distribution
- cloud sync of private data
- production auth model
- packaged desktop/mobile app
- semantic Discord/OpenClaw worker progress parsing beyond metadata-only refresh
- unattended GitHub/Discord/OpenClaw external metadata reconciliation apply
- GitHub Projects board mutation

## Practical Current Usage

Recommended current usage:

1. Run the local companion in encrypted vault mode.
2. Open PNH from local browser or owner-only phone path.
3. Create a Launch packet.
4. Send it to the workspace private inbox.
5. Run dispatch dry-run first.
6. Apply live GitHub/Discord/OpenClaw steps only when intentionally approved.
7. Refresh dispatch state.
8. Confirm Launch task status into browser-local boards.
9. Read the supervisor review summary before deciding next work.

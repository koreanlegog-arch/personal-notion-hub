# Owner Live Command Capture Runbook

Status: ready for owner action after readiness check
Date: 2026-06-05

## Purpose

This runbook describes the first real owner command capture path for Personal
Notion Hub. It is designed so real private command content stays in the local
encrypted vault and only metadata-safe dispatch facts reach GitHub, Discord,
OpenClaw, or tracked evidence.

## Boundary

Codex may prepare and verify the environment, but the human owner must perform
the pairing and enter any real private content.

Codex must not receive, print, store, or summarize:

- pairing code
- browser session token
- raw private command body
- secret values

## Readiness Check

Run:

```bash
python3 scripts/pnh_owner_live_capture_readiness.py
```

Expected:

- `verdict` is `ready_for_owner_action` or `ready_for_local_only_owner_action`
- `materialGateReached` is `true`
- `privateValuesPrinted=false`
- `secretValuePrinted=false`

## Owner Input Paths

### Local Browser

Use this when phone/tailnet is not needed.

1. Start the encrypted companion in local browser bridge mode.
2. Open the local PNH page.
3. Pair using the short-lived pairing code from the approved owner-only path.
4. Enter the owner command in Launch.
5. Send the packet to workspace private storage.

### Owner-Only Tailnet

Use this when mobile access is required and the phone is on the same tailnet.

```bash
bash scripts/start_tailnet_session.sh
```

For unattended remote use, set an owner-only Discord DM target before starting:

```bash
export PNH_OWNER_DISCORD_TARGET="user:<discord-user-id>"
bash scripts/start_tailnet_session.sh
```

The script prints the phone URL and writes a short-lived pairing handoff event
to ignored local storage. When `PNH_OWNER_DISCORD_TARGET` is set, the pairing
code is sent to the owner-only Discord DM through OpenClaw. Do not paste the
pairing code into Codex chat, docs, screenshots, Git, or shared channels.

By default, `start_tailnet_session.sh` enables bounded background dispatch for
new captures. The browser response shows whether `autoDispatch.requested=true`.
Manual dispatch commands are now fallback-only.

## After Owner Capture

After the owner submits the command, check metadata-only status:

```bash
python3 scripts/private_inbox_status.py
python3 scripts/pnh_unattended_dispatch_queue_plan.py
python3 scripts/pnh_dispatch_state_status.py
python3 scripts/pnh_dispatch_evidence_summary.py
```

Fallback manual dispatch, only if background dispatch did not run:

```bash
python3 scripts/pnh_single_command_packet.py --apply
```

## Safety Rules

- The worker prompt must use dispatch metadata only.
- Raw private command body must remain in encrypted vault storage.
- Tracked evidence should contain capture id, issue id, thread id, worker session
  id, labels, and status only.
- If `queuedCount=0`, there is no new command packet to dispatch.
- If any output prints raw private title/body, stop and treat it as a privacy
  incident.

# Evidence Log: PNH Command Packet Status Card

Date: 2026-06-05

## Goal

Expose single command packet wrapper and dispatch metadata in the PNH Launch UI without showing raw private command bodies, tokens, or URLs.

## Acceptance Criteria

- Companion provides a metadata-only command packet status endpoint.
- Browser bridge can read the endpoint only after pairing/session auth.
- Launch UI shows queue count, latest run directory, last issue, worker status, and next action.
- Existing dispatch mapping/task-status sync still works.
- Browser QA covers the status card with synthetic metadata.
- Static and backend smoke checks pass.

## Verification Plan

- `python3 scripts/pnh_command_packet_status_smoke_check.py`
- `python3 scripts/smoke_check.py`
- `python3 scripts/browser_bridge_smoke_check.py`
- `python3 -m py_compile companion/command_packet_status.py companion/server.py scripts/pnh_command_packet_status_smoke_check.py`
- `bash scripts/run_playwright_launch_status_sync_qa.sh`
- `git diff --check`

## Safety Notes

- Status helper reads only `single_command_packet_summary.json` and redacted dispatch-state fields.
- Private command body/title fixture strings are checked for absence in status smoke output.
- Browser session token remains memory-only in `assets/js/companion-bridge.js`.

## Results

- `python3 scripts/pnh_command_packet_status_smoke_check.py`: pass
- `python3 scripts/smoke_check.py`: pass
- `python3 scripts/browser_bridge_smoke_check.py`: pass
- `python3 -m py_compile companion/command_packet_status.py companion/server.py scripts/pnh_command_packet_status_smoke_check.py`: pass
- `bash scripts/run_playwright_launch_status_sync_qa.sh`: pass
- `git diff --check`: pass
- secret-pattern scan: only matched scanner patterns, help text, and synthetic fixture strings; no live secret value was identified in this slice.

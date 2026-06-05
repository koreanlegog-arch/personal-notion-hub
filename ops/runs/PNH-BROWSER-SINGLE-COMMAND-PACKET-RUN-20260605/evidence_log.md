# Evidence Log: PNH Browser Single Command Packet Run

Date: 2026-06-05

## Goal

Allow the paired PNH Launch UI to trigger the single command packet wrapper in
dry-run mode and keep apply mode separated behind a runtime gate.

## Acceptance Criteria

- Browser bridge exposes `runSingleCommandPacket`.
- Companion exposes `POST /api/private/single-command-packet/run`.
- Default browser-triggered mode is dry-run.
- Browser-triggered apply is blocked unless runtime env and confirmation phrase are set.
- UI shows `Run Dry-Run` and an explicitly locked apply control.
- Raw private bodies and secret values are not returned to browser responses or tracked evidence.
- Playwright verifies the Launch UI run state.

## Verification

- `python3 scripts/pnh_single_command_packet_browser_run_smoke_check.py`: pass
- `python3 scripts/browser_bridge_smoke_check.py`: pass
- `python3 scripts/smoke_check.py`: pass
- `python3 -m py_compile companion/single_command_packet_runner.py companion/server.py scripts/pnh_single_command_packet_browser_run_smoke_check.py`: pass
- `node --check assets/js/app.js && node --check assets/js/companion-bridge.js`: pass
- `bash scripts/run_playwright_launch_status_sync_qa.sh`: pass
- `git diff --check`: pass

## Safety

- Dry-run smoke uses a synthetic temp private inbox.
- HTTP smoke verifies the apply gate returns `403`.
- The UI apply control is disabled by default.
- The runner records stdout/stderr byte counts but returns only the redacted wrapper summary.

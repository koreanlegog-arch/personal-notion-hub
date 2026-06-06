# PNH Owner Phone Capture Session Evidence

Date: 2026-06-06

## Work Mode

- Mode: `normal-harness`
- Reason: Supervisor integrated the session runner while private-ingress, live-probe, privacy-gate, and completion-audit scripts remain specialized validators.
- Efficiency note: This reduces owner-side coordination overhead by turning several post-send checks into one bounded session command.

## Scope

- Add a first owner phone capture session runner.
- Capture baseline count, wait for the next phone automation payload, and optionally run post-capture privacy/completion checks.
- Keep private values, token values, exact owner-network URLs, and raw private bodies out of output and evidence.

## Commands

- `python3 scripts/pnh_owner_phone_capture_session_smoke_check.py`
- `python3 scripts/pnh_owner_phone_capture_session.py --baseline-count 17 --timeout-seconds 0 --skip-post-checks --out ops/runs/PNH-OWNER-PHONE-CAPTURE-SESSION-20260606/owner_phone_capture_session_status.json`
- `python3 scripts/pnh_owner_phone_capture_session.py --baseline-count 17 --timeout-seconds 30 --poll-seconds 1 --out ops/runs/PNH-OWNER-PHONE-CAPTURE-SESSION-20260606/owner_phone_capture_session.json`
- `python3 scripts/pnh_phone_automation_rehearsal.py --use-tailnet --out companion/private/scheduler/phone_automation_rehearsal_owner_session_trigger.json`

## Results

- Smoke check passed.
- Status session correctly reported no new phone capture at baseline `17`.
- Wait session detected a new phone capture and increased count from `17` to `18`.
- Post-capture privacy gate and completion audit ran.
- Session verdict: `owner_phone_capture_verified`.
- Owner next action: `ready_for_controlled_owner_operation`.
- Private values printed: `false`.
- Token values printed: `false`.
- Exact owner network URL persisted: `false`.
- Raw private body read: `false`.

## Residual Risk

- The successful trigger used synthetic owner-tailnet rehearsal data. Real
  phone-tool configuration still requires owner-side endpoint/token entry
  outside chat and committed files.

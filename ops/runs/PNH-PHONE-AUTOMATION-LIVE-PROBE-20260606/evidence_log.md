# PNH Phone Automation Live Probe Evidence

Date: 2026-06-06

## Work Mode

- Mode: `normal-harness`
- Reason: Supervisor handled integration and final verification while the work was split into private-ingress probing, automation smoke validation, documentation, and release evidence slices.
- Efficiency note: The slice is small enough to avoid strict stage-gating, but benefits from specialist private-ingress and automation validation checks rather than a single broad implementation pass.

## Scope

- Add metadata-only live probe for phone automation captures.
- Verify new phone automation input reaches local encrypted vault without reading private bodies.
- Keep token values, private values, and exact owner-network URLs out of stdout and committed evidence.

## Commands

- `python3 scripts/pnh_phone_automation_live_probe_smoke_check.py`
- `python3 scripts/pnh_phone_automation_live_probe.py`
- `python3 scripts/pnh_phone_automation_live_probe.py --baseline-count 16 --timeout-seconds 30 --poll-seconds 1 --out ops/runs/PNH-PHONE-AUTOMATION-LIVE-PROBE-20260606/live_probe_wait.json`
- `python3 scripts/pnh_phone_automation_rehearsal.py --use-tailnet --out companion/private/scheduler/phone_automation_rehearsal_live_probe_trigger.json`
- `python3 scripts/pnh_phone_automation_setup_readiness.py`
- `python3 scripts/pnh_real_data_privacy_gate.py`
- `python3 scripts/private_inbox_status.py`
- `python3 scripts/smoke_check.py`
- `git diff --check`
- `python3 scripts/pnh_unattended_automation_status.py`

## Results

- Smoke check passed.
- Status probe found the latest phone capture as encrypted-vault metadata.
- Wait probe detected a new phone capture.
- Private inbox count increased from `16` to `17`.
- Latest detected source: `phone_call_log`.
- Latest detected storage mode: `encrypted-vault`.
- Phone automation setup readiness verdict: `ready_for_owner_phone_tool_configuration`.
- Real data privacy gate verdict: `ready_for_controlled_real_phone_adapter_run`.
- Private inbox after probe trigger: `17` total, `17` encrypted-vault, `0` plaintext.
- Full static smoke check passed.
- Git whitespace check passed.
- Unattended automation status: `idle_ready`.
- Raw private body read: `false`.
- Private values printed: `false`.
- Token values printed: `false`.
- Exact owner network URL persisted: `false`.

## Residual Risk

- This probe validates the workspace ingress side. The owner phone automation
  app still needs to be configured with the generated placeholder profile and
  local token outside Codex chat.

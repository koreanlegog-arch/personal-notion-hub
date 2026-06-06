# PNH Worker Progress Backfill Evidence

Date: 2026-06-06

## Goal

Improve semantic worker progress parsing and normalize active dispatch-state
records without storing private command bodies, Discord/OpenClaw message bodies,
GitHub issue bodies, tokens, or secret values.

## Work Mode

- mode: `normal-harness`
- reason: the work needed a small implementation slice, local state cleanup,
  smoke validation, and documentation drift correction. The supervisor-agent
  performed integration while routing the work into separable parser,
  backfill, state-summary, and documentation checks.

## Efficiency Notes

- specialist fit: medium-high
  - `local-private-data-ingress` governed privacy-sensitive local state handling.
  - `automation-delivery` governed dry-run/apply scripts and smoke checks.
- supervisor load: moderate
  - integration stayed with the supervisor because the change touched shared
    dispatch metadata contracts.
- parallel value: medium
  - independent reads and smoke checks were run in parallel where safe.
- rework observed: low
  - one smoke expectation was corrected after the backfill scope intentionally
    expanded from missing-only semantic data to legacy semantic upgrades.
- evidence quality: high
  - smoke checks cover parser v2 fields, legacy backfill, private marker
    non-leakage, secret-like input rejection, dispatch-state summary, and full
    project smoke.

## Results

- active dispatch records inspected: `6`
- semantic records after backfill: `6`
- high evidence-strength records after backfill: `6`
- supervisor-action-required records: `0`
- message content stored: `false`
- private values printed: `false`

## Verification Commands

```bash
python3 scripts/pnh_worker_progress_backfill_from_state_smoke_check.py
python3 scripts/pnh_worker_progress_parse_smoke_check.py
python3 scripts/pnh_worker_progress_batch_import_smoke_check.py
python3 scripts/pnh_dispatch_state_status_smoke_check.py
python3 scripts/pnh_worker_progress_backfill_from_state.py --apply
python3 scripts/pnh_dispatch_state_status.py --limit 10
python3 scripts/smoke_check.py
git diff --check
```

## Privacy Notes

- No raw worker progress message was persisted.
- Backfill used dispatch-state metadata only.
- Local dispatch state remains under ignored `companion/private/`.

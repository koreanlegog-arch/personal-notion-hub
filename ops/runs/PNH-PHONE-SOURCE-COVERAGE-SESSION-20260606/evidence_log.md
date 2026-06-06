# PNH Phone Source Coverage Session Evidence

Date: 2026-06-06

## Work Mode

- Mode: `normal-harness`
- Reason: Supervisor integrated a source-coverage session while existing adapter rehearsal and recent-summary scripts remained specialized validators.
- Efficiency note: The session collapses four separate adapter checks into one bounded coverage workflow and keeps detailed source inspection metadata-only.

## Scope

- Verify recent coverage across phone contacts, calendar, call log, and recording sources.
- Optionally rehearse missing sources with synthetic payloads through loopback or owner-tailnet.
- Keep private values, token values, exact owner URLs, and raw private bodies out of evidence.

## Commands

- `python3 scripts/pnh_phone_source_coverage_session_smoke_check.py`
- `python3 scripts/pnh_phone_source_coverage_session.py --out ops/runs/PNH-PHONE-SOURCE-COVERAGE-SESSION-20260606/phone_source_coverage_status.json`
- `python3 scripts/pnh_phone_source_coverage_session.py --rehearse-missing --use-tailnet --out ops/runs/PNH-PHONE-SOURCE-COVERAGE-SESSION-20260606/phone_source_coverage_session.json`
- `python3 scripts/pnh_phone_capture_recent_summary.py`
- `python3 scripts/private_inbox_status.py`
- `python3 scripts/pnh_real_data_privacy_gate.py`
- `python3 scripts/pnh_assistant_mvp_completion_audit.py`
- `python3 scripts/pnh_scheduler_tick.py`
- `python3 scripts/smoke_check.py`

## Results

- Smoke check passed with all four supported phone sources in a fixture DB.
- Initial status found missing sources: `phone_contacts`, `phone_calendar`.
- Synthetic owner-tailnet coverage rehearsal sent `2` missing adapter payloads.
- Final coverage verdict: `all_phone_sources_covered`.
- Final recent phone sources:
  - `phone_contacts`: `1`
  - `phone_calendar`: `1`
  - `phone_call_log`: `5`
  - `phone_recording`: `1`
- Final phone captures: `8`.
- Final encrypted phone captures: `8`.
- Final plaintext phone captures: `0`.
- Private inbox total: `20`, encrypted-vault `20`, plaintext `0`.
- Real data privacy gate verdict: `ready_for_controlled_real_phone_adapter_run`.
- Completion audit passed `15/15`.
- Scheduler tick passed with `11` jobs and no failures.
- Full static smoke check passed.
- Private values printed: `false`.
- Token values printed: `false`.
- Exact owner network URL persisted: `false`.
- Raw private body read: `false`.

## Residual Risk

- Coverage was completed with synthetic owner-tailnet payloads. Real phone-tool
  source coverage still depends on the owner's phone automation app sending the
  same adapter shapes.

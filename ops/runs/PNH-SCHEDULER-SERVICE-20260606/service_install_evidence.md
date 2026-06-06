# PNH Scheduler Service Evidence

Date: 2026-06-06

## Scope

Installed a bounded user-systemd timer for PNH scheduler ticks.

## Installed Units

- `pnh-scheduler.timer`
- `pnh-scheduler.service`

## Runtime Output

- `companion/private/scheduler/scheduler_tick.json`
- child job output directory: `companion/private/scheduler/jobs/`

Both paths are under ignored `companion/private/`.

## Verification

- `python3 scripts/pnh_scheduler_service_plan_smoke_check.py`: passed
- `python3 scripts/pnh_scheduler_smoke_check.py`: passed
- `python3 scripts/smoke_check.py`: passed
- `bash scripts/pnh_scheduler_install_user_service.sh --apply --interval-minutes 10`: installed
- `python3 scripts/pnh_scheduler_service_status.py`: timer active, service static, runtime output exists
- `python3 -m json.tool companion/private/scheduler/scheduler_tick.json`: passed

## Safety Notes

- No secret values printed.
- No private values printed.
- Timer runs bounded status/readiness checks only.
- Live adapter job is readiness-only by default.
- No system-level service was installed.

## Rollback

```bash
bash scripts/pnh_scheduler_uninstall_user_service.sh --apply
```

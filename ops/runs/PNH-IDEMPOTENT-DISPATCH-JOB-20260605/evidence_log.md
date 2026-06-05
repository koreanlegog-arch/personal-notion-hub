# Evidence Log: PNH Idempotent Dispatch Job

Date: 2026-06-05

## Planned Validation

```bash
python3 -m py_compile scripts/pnh_dispatch_job.py scripts/pnh_dispatch_job_smoke_check.py
python3 scripts/pnh_dispatch_job_smoke_check.py
python3 scripts/github_ledger_bridge_smoke_check.py
python3 scripts/smoke_check.py
git diff --check
```

## Results

- `python3 -m py_compile scripts/pnh_dispatch_job.py scripts/pnh_dispatch_job_smoke_check.py scripts/github_ledger_bridge.py scripts/github_ledger_bridge_smoke_check.py`: passed
- `python3 scripts/pnh_dispatch_job_smoke_check.py`: passed
  - `pnh_dispatch_job_smoke_check_pass=true`
  - `writes_performed=false`
  - `private_values_printed=false`
- `python3 scripts/github_ledger_bridge_smoke_check.py`: passed
  - `github_ledger_bridge_smoke_check_pass=true`
  - `writes_performed=false`
  - `private_values_printed=false`
- `python3 scripts/smoke_check.py`: passed
  - `smoke_check_pass=true`
- Sample dispatch dry-run:
  - command: `python3 scripts/pnh_dispatch_job.py --input-json ops/runs/PNH-GITHUB-LEDGER-BRIDGE-20260605/sample_command_packet.json --repo koreanlegog-arch/personal-notion-hub --discord-target channel:1511691320136306718 --out ops/runs/PNH-IDEMPOTENT-DISPATCH-JOB-20260605/dispatch_plan.json`
  - `writesPerformed=false`
  - `tokenValuePrinted=false`
  - `privateValuesIncluded=false`
  - planned thread: `PNH-capture-sample-001-dispatch`
- Private value scan:
  - synthetic private sample values appear only in sample input or smoke fixtures
  - synthetic private sample values do not appear in `dispatch_plan.json`
- Final validation:
  - `python3 -m py_compile scripts/pnh_dispatch_job.py scripts/pnh_dispatch_job_smoke_check.py scripts/github_ledger_bridge.py scripts/github_ledger_bridge_smoke_check.py`: passed
  - `python3 scripts/pnh_dispatch_job_smoke_check.py`: passed
  - `python3 scripts/github_ledger_bridge_smoke_check.py`: passed
  - `python3 scripts/smoke_check.py`: passed
  - `git diff --check`: passed
- Secret pattern scan:
  - matches were existing synthetic fixture text, companion runtime pairing-code print location, and prior evidence command text
  - no GitHub token, Discord bot token, OpenClaw gateway token, or raw private command value was identified in this change

## Security Notes

- Dry-run only in this packet.
- Apply mode requires approval flags.
- Default GitHub/Discord payload excludes raw private command body.
- Default local dispatch state is under ignored `companion/private/`.
- Apply mode was not executed in this packet.

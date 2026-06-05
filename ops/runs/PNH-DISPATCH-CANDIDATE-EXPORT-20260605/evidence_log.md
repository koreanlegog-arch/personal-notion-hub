# Evidence Log: PNH Dispatch Candidate Export

Date: 2026-06-05

## Planned Validation

```bash
python3 -m py_compile scripts/pnh_dispatch_candidate_export.py scripts/pnh_dispatch_candidate_export_smoke_check.py
python3 scripts/pnh_dispatch_candidate_export_smoke_check.py
python3 scripts/pnh_dispatch_job_smoke_check.py
python3 scripts/smoke_check.py
git diff --check
```

## Results

- `python3 -m py_compile scripts/pnh_dispatch_candidate_export.py scripts/pnh_dispatch_candidate_export_smoke_check.py scripts/pnh_dispatch_job.py scripts/pnh_dispatch_job_smoke_check.py`: passed
- `python3 scripts/pnh_dispatch_candidate_export_smoke_check.py`: passed
  - `pnh_dispatch_candidate_export_smoke_check_pass=true`
  - `private_values_printed=false`
- `python3 scripts/pnh_dispatch_job_smoke_check.py`: passed
  - `pnh_dispatch_job_smoke_check_pass=true`
  - `writes_performed=false`
  - `private_values_printed=false`
- `python3 scripts/smoke_check.py`: passed
  - `smoke_check_pass=true`
- Actual local encrypted-vault metadata export:
  - command: `python3 scripts/pnh_dispatch_candidate_export.py --out ops/runs/PNH-DISPATCH-CANDIDATE-EXPORT-20260605/live_metadata_candidate.json`
  - `dispatchCandidateExported=true`
  - `storageMode=encrypted-vault`
  - `privateValuesPrinted=false`
- Actual exported candidate dispatch dry-run:
  - command: `python3 scripts/pnh_dispatch_job.py --input-json ops/runs/PNH-DISPATCH-CANDIDATE-EXPORT-20260605/live_metadata_candidate.json --repo koreanlegog-arch/personal-notion-hub --discord-target channel:1511691320136306718 --out ops/runs/PNH-DISPATCH-CANDIDATE-EXPORT-20260605/live_metadata_dispatch_plan.json`
  - `writesPerformed=false`
  - `tokenValuePrinted=false`
  - `privateValuesIncluded=false`
  - planned thread name uses capture id only
- Final validation:
  - `python3 -m py_compile scripts/pnh_dispatch_candidate_export.py scripts/pnh_dispatch_candidate_export_smoke_check.py scripts/pnh_dispatch_job.py scripts/pnh_dispatch_job_smoke_check.py`: passed
  - `python3 scripts/pnh_dispatch_candidate_export_smoke_check.py`: passed
  - `python3 scripts/pnh_dispatch_job_smoke_check.py`: passed
  - `python3 scripts/smoke_check.py`: passed
  - `git diff --check`: passed
- Secret/private-value scan:
  - matches were synthetic fixture literals, companion runtime pairing-code print location, existing sample input, and prior evidence command text
  - exported candidate and dispatch plan do not contain raw private body/title values
  - no GitHub token, Discord token, OpenClaw token, or raw private command value was identified in this change

## Security Notes

- Export is metadata-only.
- Raw private title/body are not printed.
- Encrypted-vault rows are preferred by default.
- Plaintext rows require `--allow-plaintext`.
- Fixture tests use `--allow-external-db` only for temporary databases outside `companion/private/`.
- No external GitHub or Discord write was performed in this packet.

# Evidence Log: PNH GitHub Ledger Bridge

Date: 2026-06-05

## Planned Validation

```bash
python3 -m py_compile scripts/github_ledger_bridge.py scripts/github_ledger_bridge_smoke_check.py
python3 scripts/github_ledger_bridge_smoke_check.py
python3 scripts/smoke_check.py
git diff --check
```

## Results

- `python3 -m py_compile scripts/github_ledger_bridge.py scripts/github_ledger_bridge_smoke_check.py`: passed
- `python3 scripts/github_ledger_bridge_smoke_check.py`: passed
  - `github_ledger_bridge_smoke_check_pass=true`
  - `writes_performed=false`
  - `private_values_printed=false`
- `python3 scripts/smoke_check.py`: passed
  - `smoke_check_pass=true`
- Synthetic dry-run:
  - command: `python3 scripts/github_ledger_bridge.py --input-json ops/runs/PNH-GITHUB-LEDGER-BRIDGE-20260605/sample_command_packet.json --repo koreanlegog-arch/personal-notion-hub --out ops/runs/PNH-GITHUB-LEDGER-BRIDGE-20260605/github_issue_dry_run.json`
  - `writesPerformed=false`
  - `tokenValuePrinted=false`
  - `privateValuesIncluded=false`
  - output title: `[PNH] project_brief command packet (capture-sample-001)`
- Private value scan for synthetic sample:
  - raw sample title/body appear only in `sample_command_packet.json`
  - raw sample title/body do not appear in `github_issue_dry_run.json`
- Final validation:
  - `python3 -m py_compile scripts/github_ledger_bridge.py scripts/github_ledger_bridge_smoke_check.py`: passed
  - `python3 scripts/github_ledger_bridge_smoke_check.py`: passed
  - `python3 scripts/smoke_check.py`: passed
  - `git diff --check`: passed
- Secret pattern scan:
  - matches were existing synthetic fixture text, companion runtime pairing-code print location, and prior evidence command text
  - no GitHub token, Discord token, OpenAI key, or new secret value was identified in this bridge change
- Live GitHub issue apply after supervisor approval:
  - approval phrase: `APPROVE_PNH_GITHUB_ISSUE_LEDGER_APPLY`
  - command used `GITHUB_TOKEN` from `gh auth token` without printing the token value
  - command included `--apply --approve-external-write --omit-labels`
  - `writesPerformed=true`
  - `tokenValuePrinted=false`
  - `privateValuesIncluded=false`
  - GitHub issue: https://github.com/koreanlegog-arch/personal-notion-hub/issues/1
- GitHub issue ledger comment:
  - URL: https://github.com/koreanlegog-arch/personal-notion-hub/issues/1#issuecomment-4627177556
  - recorded Discord thread and audit-log message IDs
  - raw private command body was not posted

## Security Notes

- No GitHub token is stored in the repository.
- Dry-run does not require a token.
- Live GitHub issue creation is blocked behind approval flags.
- Sensitive packet title/body are excluded by default.
- GitHub Projects mutation is not implemented in this phase.
- Live issue creation used `--omit-labels` to avoid introducing label-management side effects during the first rehearsal.

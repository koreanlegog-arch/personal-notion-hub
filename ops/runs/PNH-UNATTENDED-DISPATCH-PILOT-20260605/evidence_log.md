# Evidence Log: PNH Unattended Dispatch Pilot

Date: 2026-06-05

## Approval

Approved phrase received:

```text
APPROVE_PNH_UNATTENDED_DISPATCH_PILOT
```

## Scope

Run one unattended dispatch pilot batch using the approved queue limits.

## Commands Run

```bash
python3 scripts/pnh_unattended_dispatch_pilot_smoke_check.py
python3 scripts/pnh_unattended_dispatch_pilot.py --detect-existing-github
python3 scripts/pnh_unattended_dispatch_pilot.py --apply --approve-unattended-pilot --detect-existing-github
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
python3 scripts/pnh_discord_thread_status_refresh.py --openclaw-read --approve-discord-read --apply --limit 10
python3 scripts/pnh_external_reconciliation_plan.py
python3 scripts/pnh_unattended_dispatch_queue_plan.py
python3 scripts/pnh_unattended_dispatch_readiness.py
python3 scripts/pnh_dispatch_state_status.py --include-urls
python3 scripts/pnh_dispatch_evidence_summary.py
python3 scripts/pnh_supervisor_review_summary.py
```

## Result

- selected capture: `capture-2a0fcdefc3f169ec30c6497f`
- GitHub Issue: `#3`
- Discord thread: `1512315698351706183`
- local task status: `dispatched_to_worker_thread`
- evidence completeness: `67`
- missing evidence: `worker_session`
- next action: `capture_worker_session_result`

## Safety

- Private command body exported: false.
- Token values printed: false.
- Message content stored: false.
- Rollback snapshot created:
  `ops/runs/PNH-UNATTENDED-DISPATCH-PILOT-20260605/rollback/dispatch_state_before.json`

## Failure And Fix

The first apply attempt failed before external writes because `gh api` duplicate
detection was missing an explicit `--method GET`. The command path was patched,
smoke checks were rerun, and apply succeeded.

## Post-Pilot Queue

- cooldown active: true
- queued count: `0`
- additional eligible command captures are held until the next allowed batch

## Next Gate

The next material gate is OpenClaw worker/model execution for Issue `#3`.

Reason: worker execution can invoke configured model providers and produce
agent output that may later be delivered or acted on.

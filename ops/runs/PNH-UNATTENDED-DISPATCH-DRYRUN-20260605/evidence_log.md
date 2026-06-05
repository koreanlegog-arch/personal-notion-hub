# Evidence Log: PNH Unattended Dispatch Dry-Run

Date: 2026-06-05

## Scope

Run the next unattended dispatch candidate through queue planning, readiness
checks, and pilot dry-run without creating GitHub, Discord, or OpenClaw records.

## Commands Run

```bash
python3 scripts/pnh_unattended_dispatch_queue_plan.py --out ops/runs/PNH-UNATTENDED-DISPATCH-DRYRUN-20260605/queue_plan.json
python3 scripts/pnh_unattended_dispatch_readiness.py --queue-plan ops/runs/PNH-UNATTENDED-DISPATCH-DRYRUN-20260605/queue_plan.json --out ops/runs/PNH-UNATTENDED-DISPATCH-DRYRUN-20260605/readiness.json
python3 scripts/pnh_unattended_dispatch_pilot.py --queue-plan ops/runs/PNH-UNATTENDED-DISPATCH-DRYRUN-20260605/queue_plan.json --run-dir ops/runs/PNH-UNATTENDED-DISPATCH-DRYRUN-20260605/pilot
```

## Result

- captures inspected: `8`
- queued candidate count: `1`
- selected capture id: `capture-3b8522ff102b0469c683b027`
- selected command type: `project_brief`
- storage mode: `encrypted-vault`
- readiness verdict: `ready_for_approval_gated_pilot`
- external writes performed: `false`
- private values printed: `false`
- token values printed: `false`

## Next Gate

The next material gate is live unattended pilot apply because that would create
or mutate external GitHub, Discord, and OpenClaw records.

Gate reason:

- `--apply --approve-unattended-pilot` would dispatch the selected private-inbox
  command packet into external systems.
- Rollback snapshot and single-writer lock are required before apply.

## Safety Notes

- Raw private command body was not exported.
- Existing approved pilot evidence was preserved in its original run directory.
- This dry-run used a separate run directory to avoid overwriting apply evidence.

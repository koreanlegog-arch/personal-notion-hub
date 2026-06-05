# PNH Unattended Dispatch Runbook

Status: readiness packet only; live unattended dispatch is not enabled.
Date: 2026-06-05

## Purpose

Unattended dispatch should let approved owner mobile captures move from the
local encrypted private inbox into the existing GitHub/Discord/OpenClaw dispatch
pipeline without per-item manual command entry.

This runbook defines the queue, rollback, and rate-limit model required before
that mode can be piloted.

## Current Boundary

Current implementation supports a single approved pilot batch.

It can:

- inspect private-inbox metadata
- identify queue-eligible command captures
- skip already dispatched captures
- enforce per-run and per-hour planning limits
- produce rollback requirements
- assess readiness for an approval-gated pilot
- run one approved pilot batch with rollback snapshot and single-writer lock

It must not:

- create GitHub Issues without `--apply --approve-unattended-pilot`
- create Discord/OpenClaw threads without `--apply --approve-unattended-pilot`
- post GitHub comments without `--apply --approve-unattended-pilot`
- run OpenClaw worker/model calls automatically
- run as a daemon or scheduled service
- store raw private command bodies in reports

## Queue Model

Queue source:

```text
companion/private/pnh_private_inbox.sqlite
```

Eligible capture metadata:

- `kind` in `project_brief`, `task_request`, `daily_command`, `urgent_approval`
- `status` is `inbox`
- capture id is not already present in `companion/private/pnh_dispatch_state.json`
- encrypted vault storage by default
- plaintext rows are blocked unless fixture-only `--allow-plaintext` is used

Dry-run command:

```bash
python3 scripts/pnh_unattended_dispatch_queue_plan.py
```

Default pilot policy:

- `maxJobsPerRun=1`
- `maxExternalWritesPerHour=3`
- `cooldownMinutes=10`
- single-writer lock required before any future apply runner

## Rollback Model

Before any future apply runner can be enabled, it must:

1. snapshot `companion/private/pnh_dispatch_state.json`
2. write run-local candidate and dispatch plan before external apply
3. record GitHub issue labels before mutation
4. record Discord thread id only after creation succeeds

Rollback actions:

- restore the local dispatch state snapshot if local metadata becomes inconsistent
- manually close or relabel GitHub issues created by failed runs
- avoid additional Discord messages until supervisor review
- rerun `pnh_external_reconciliation_plan.py` before retry

## Rate Limit Model

The pilot must use bounded external writes:

- one queue item per run by default
- maximum three external write events per hour by default
- minimum ten-minute cooldown between unattended runs
- no retry storm; failed items require explicit review before retry
- queue planner returns zero queued items while cooldown is active

Rate limit enforcement is currently a dry-run planning contract. Future apply
mode must persist dispatch history before it can be considered safe.

## Readiness Assessment

Run:

```bash
python3 scripts/pnh_unattended_dispatch_queue_plan.py
python3 scripts/pnh_unattended_dispatch_readiness.py
```

The readiness script checks:

- queue plan exists and remains dry-run
- no pending external reconciliation writes
- Discord metadata refresh is available without message-content storage
- `gh` is available
- `openclaw` is available

## Activation Gate

Live unattended pilot activation required:

```text
APPROVE_PNH_UNATTENDED_DISPATCH_PILOT
```

Reason: activation would allow queued mobile captures to create external
GitHub/Discord/OpenClaw records without per-item operator confirmation.

## Pilot Result

First approved pilot batch:

- capture: `capture-2a0fcdefc3f169ec30c6497f`
- GitHub Issue: `#3`
- Discord thread: `1512315698351706183`
- worker session: `pnh:capture-2a0fcdefc3f169ec30c6497f:qa`
- status: `worker_done`
- GitHub dispatch label: `dispatch:worker-done`
- external reconciliation: no pending writes

## Not Yet Implemented

- daemon/service/scheduler integration
- automatic retry/backoff state machine
- semantic Discord worker-progress parsing
- real private-data adapters

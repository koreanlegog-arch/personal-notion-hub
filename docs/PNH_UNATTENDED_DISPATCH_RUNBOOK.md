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

Current implementation is dry-run/readiness only.

It can:

- inspect private-inbox metadata
- identify queue-eligible command captures
- skip already dispatched captures
- enforce per-run and per-hour planning limits
- produce rollback requirements
- assess readiness for an approval-gated pilot

It must not:

- create GitHub Issues automatically
- create Discord/OpenClaw threads automatically
- post GitHub comments automatically
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

Live unattended pilot activation requires:

```text
APPROVE_PNH_UNATTENDED_DISPATCH_PILOT
```

Reason: activation would allow queued mobile captures to create external
GitHub/Discord/OpenClaw records without per-item operator confirmation.

## Not Yet Implemented

- actual unattended apply runner
- durable dispatch history store
- daemon/service/scheduler integration
- automatic retry/backoff state machine
- semantic Discord worker-progress parsing
- real private-data adapters

# PNH Unattended Dispatch Runbook

Status: bounded pilot batches are delegated for PNH test and implementation
evidence; bounded local scheduler scripts and a user-systemd timer are
available.
Date: 2026-06-06

## Purpose

Unattended dispatch should let approved owner mobile captures move from the
local encrypted private inbox into the existing GitHub/Discord/OpenClaw dispatch
pipeline without per-item manual command entry.

This runbook defines the queue, rollback, and rate-limit model required before
that mode can be piloted.

## Current Boundary

Current implementation supports bounded pilot batches.

It can:

- inspect private-inbox metadata
- identify queue-eligible command captures
- skip already dispatched captures
- enforce per-run and per-hour planning limits
- produce rollback requirements
- assess readiness for a bounded pilot batch
- run bounded pilot batches with rollback snapshot and single-writer lock
- plan retry/backoff candidates for failed or blocked dispatch records
- run bounded local scheduler ticks/loops for status, queue, retry, evidence,
  and live-adapter readiness checks

It must not:

- run unbounded OpenClaw worker/model calls or include raw private command bodies
- install or activate a daemon or scheduled service
- store raw private command bodies in reports

## Queue Model

Queue source:

```text
companion/private/pnh_private_inbox.sqlite
```

Eligible capture metadata:

- `kind` in `project_brief`, `task_request`, `daily_command`, `urgent_approval`
- or an explicit command alias in `companion/private/pnh_command_aliases.json`
  that maps an encrypted `assistant_capture` to one of those command types
- `status` is `inbox`
- capture id is not already present in `companion/private/pnh_dispatch_state.json`
- encrypted vault storage by default
- plaintext rows are blocked unless fixture-only `--allow-plaintext` is used

Command alias flow:

```bash
python3 scripts/pnh_capture_command_alias.py \
  --capture-id "<capture-id>" \
  --command-type task_request
python3 scripts/pnh_unattended_dispatch_queue_plan.py
```

This overlay is for dispatch interpretation only. It does not change encrypted
vault metadata because changing authenticated metadata would break future
decryption.

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
- no retry storm; failed or blocked items use bounded retry/backoff planning
- queue planner returns zero queued items while cooldown is active

Rate limit enforcement is persisted in local dispatch history for pilot runs.
Retry/backoff planning writes metadata-only retry plans to local history when
apply mode is used.

Retry/backoff check:

```bash
python3 scripts/pnh_unattended_retry_backoff.py
python3 scripts/pnh_unattended_retry_backoff.py --apply
```

## Scheduler Model

The scheduler MVP is a bounded local runner. It can run status, queue, retry,
evidence, and live-adapter readiness jobs in one tick, in a capped loop, or as a
user-systemd timer.

```bash
python3 scripts/pnh_scheduler_tick.py
python3 scripts/pnh_scheduler_loop.py --iterations 1 --interval-seconds 1
python3 scripts/pnh_scheduler_service_status.py
```

Safety boundaries:

- user-systemd timer only; no system-level service
- service runtime output goes to ignored `companion/private/scheduler/`
- no unbounded loop; iterations and intervals are capped
- no raw private values in scheduler output
- no external write by default
- live adapter job is readiness-only by default and does not fetch external
  data unless a separate guarded sync command is run

Install or remove the user timer:

```bash
bash scripts/pnh_scheduler_install_user_service.sh --apply --interval-minutes 10
bash scripts/pnh_scheduler_uninstall_user_service.sh --apply
```

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

## State Refresh Ordering

Do not run GitHub status refresh and Discord thread refresh in parallel because
both update `companion/private/pnh_dispatch_state.json`.

Use this order after a dispatch or label reconciliation:

```bash
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
python3 scripts/pnh_discord_thread_status_refresh.py --openclaw-read --approve-discord-read --apply --limit 10
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
python3 scripts/pnh_external_reconciliation_plan.py
python3 scripts/pnh_dispatch_evidence_summary.py
python3 scripts/pnh_supervisor_review_summary.py
```

The final GitHub refresh preserves issue state and label fields if a prior
Discord refresh used an older state snapshot.

When `worker_done` records have 100% redacted evidence completeness, close the
linked GitHub Issues with the metadata-only closure script:

```bash
python3 scripts/pnh_github_worker_done_closure.py
python3 scripts/pnh_github_worker_done_closure.py --apply --approve-external-write
python3 scripts/pnh_dispatch_status_refresh.py --github-read --apply
python3 scripts/pnh_dispatch_evidence_summary.py
```

This closure path is limited to records that already have GitHub issue,
Discord thread, worker session, `worker_done`, and complete evidence metadata.
It does not read private command bodies.

## Activation Gate

Live unattended pilot activation is delegated for bounded PNH test and
implementation batches when the existing queue, rate-limit, rollback, redaction,
and evidence scripts are used:

```text
project AGENTS.md bounded dispatch delegation
```

Reason: the supervisor delegated this class of test/implementation write to
avoid micro-approval during PNH pipeline validation.

## Pilot Result

Owner live assistant-capture dispatch:

- capture: `assistant-capture-capture-mq0mgu4q-uvzyzm0s`
- command alias: `task_request`
- GitHub Issue: `#6`
- GitHub Issue state: `closed`
- Discord thread: `1512364450869547130`
- worker session: `pnh:assistant-capture-capture-mq0mgu4q-uvzyzm0s:qa`
- status: `worker_done`
- evidence completeness: `100%`
- raw private body read: no

Synthetic single command packet rehearsal:

- capture: `capture-40fc5ea5d769acebdb130781`
- GitHub Issue: `#5`
- GitHub Issue state: `closed`
- Discord thread: `1512357660807270561`
- worker session: `pnh:capture-40fc5ea5d769acebdb130781:qa`
- status: `worker_done`
- GitHub dispatch label: `dispatch:worker-done`
- evidence completeness: `100%`

Second pilot batch:

- capture: `capture-3b8522ff102b0469c683b027`
- GitHub Issue: `#4`
- GitHub Issue state: `closed`
- Discord thread: `1512323845514596373`
- worker session: `pnh:capture-3b8522ff102b0469c683b027:qa`
- status: `worker_done`
- GitHub dispatch label: `dispatch:worker-done`
- external reconciliation: no pending writes
- next action: `summarize_worker_result_for_supervisor_review`

First approved pilot batch:

- capture: `capture-2a0fcdefc3f169ec30c6497f`
- GitHub Issue: `#3`
- GitHub Issue state: `closed`
- Discord thread: `1512315698351706183`
- worker session: `pnh:capture-2a0fcdefc3f169ec30c6497f:qa`
- status: `worker_done`
- GitHub dispatch label: `dispatch:worker-done`
- external reconciliation: no pending writes

## Remaining Gaps

- production companion server daemon
- production scheduler alerting and escalation
- live Discord worker-progress parsing from thread bodies
- production live phone/cloud private-data adapters

## Rough MVP Additions

- `scripts/pnh_worker_progress_parse.py` can parse redacted worker progress
  snippets into metadata-only semantic progress.
- `scripts/pnh_dispatch_state_cleanup.py` can archive stale incomplete records
  from active dispatch state.
- `scripts/pnh_private_data_adapter_import.py` supports owner-exported local
  private data imports into encrypted vault storage.
- `scripts/pnh_unattended_retry_backoff.py` plans bounded retry candidates for
  failed or blocked records.
- `scripts/pnh_scheduler_tick.py`, `scripts/pnh_scheduler_loop.py`, and
  `scripts/pnh_scheduler_install_user_service.sh` run bounded local scheduler
  checks, including live-adapter readiness, manually or through a user-systemd
  timer.

# Queue / Rollback / Rate-Limit Design

Date: 2026-06-05

## Queue

The unattended queue is derived from private-inbox metadata, not message body
contents.

Eligible items:

- command kind: `project_brief`, `task_request`, `daily_command`,
  `urgent_approval`
- status: `inbox`
- not already linked in `pnh_dispatch_state.json`
- encrypted storage preferred

Skipped items:

- already dispatched
- non-command captures
- plaintext captures unless fixture-only override is used
- items beyond per-run or hourly rate limits

## Lock

Future apply mode must use:

```text
companion/private/pnh_unattended_dispatch.lock
```

Rules:

- single writer only
- state writes must be sequential
- stale lock threshold defaults to at least 15 minutes
- no parallel local state writes

## Rate Limit

Default pilot:

- `maxJobsPerRun=1`
- `maxExternalWritesPerHour=3`
- `cooldownMinutes=10`

The first pilot should prioritize correctness and auditability over throughput.

## Rollback

Before apply:

- snapshot local dispatch state
- write candidate and dispatch plan
- record pre-mutation GitHub labels
- record Discord thread id only after successful creation

After failure:

- restore local snapshot if metadata is inconsistent
- manually close/relabel failed GitHub artifacts
- pause Discord/OpenClaw writes
- rerun reconciliation planning before retry

## Stop Conditions

Stop unattended execution when:

- queue planner detects plaintext private rows
- duplicate detection fails
- GitHub/Discord/OpenClaw auth is unavailable
- rate limit is exhausted
- any external write partially succeeds
- local dispatch state JSON becomes invalid
- message content appears in evidence output

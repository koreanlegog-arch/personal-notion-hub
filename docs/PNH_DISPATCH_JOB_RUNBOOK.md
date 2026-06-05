# PNH Dispatch Job Runbook

Status: dry-run implementation ready
Date: 2026-06-05

## Purpose

The dispatch job turns a stored PNH mobile command packet into a durable GitHub Issue ledger entry and a Discord/OpenClaw routing thread without duplicating records on repeated runs.

## Current Boundary

Default behavior is dry-run only.

Live apply is allowed only when the supervisor has approved external writes and the operator intentionally passes apply flags.

## Flow

```text
PNH command packet JSON
-> privacy-preserving GitHub Issue payload
-> optional GitHub Issue creation
-> optional Discord thread creation through OpenClaw
-> local private dispatch state records external IDs
-> repeated runs skip existing issue/thread records
```

## State File

Default apply-mode state:

```text
companion/private/pnh_dispatch_state.json
```

This path is ignored by Git. It stores external IDs and timestamps, not secret values.

## Dry Run

```bash
python3 scripts/pnh_dispatch_job.py \
  --input-json ops/runs/PNH-GITHUB-LEDGER-BRIDGE-20260605/sample_command_packet.json \
  --repo koreanlegog-arch/personal-notion-hub \
  --discord-target channel:1511691320136306718
```

## Apply Requirements

Apply mode requires:

- supervisor approval for external writes
- `--apply`
- `--approve-external-write`
- `GITHUB_TOKEN` available in the runtime environment
- `--approve-discord-dispatch` if creating a Discord thread
- approved OpenClaw env file for gateway/Discord secrets

## Privacy Rules

- Raw private command body is never included by default.
- Token values are never printed.
- GitHub Issue body records metadata and local capture references only.
- Discord messages are routing summaries only.

## Remaining Work

- Extract the latest stored launch packet from browser/local companion state automatically.
- Store `githubIssueUrl` and `discordThreadId` back into PNH browser state or companion metadata.
- Add duplicate detection against existing GitHub Issues if local state is missing.
- Capture real OpenClaw worker-session result IDs after actual worker execution is enabled.

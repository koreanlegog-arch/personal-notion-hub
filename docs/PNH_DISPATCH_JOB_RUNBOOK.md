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

Inspect state without opening the private file directly:

```bash
python3 scripts/pnh_dispatch_state_status.py
```

URLs are hidden by default. Use `--include-urls` only for local operator inspection.

## Dry Run

Run the full local rehearsal:

```bash
python3 scripts/pnh_dispatch_rehearsal.py
```

The rehearsal performs candidate export, dispatch dry-run planning, and state status output. It does not create GitHub Issues or Discord/OpenClaw messages.

Export a metadata-only candidate from the local private inbox:

```bash
python3 scripts/pnh_dispatch_candidate_export.py \
  --out ops/runs/PNH-DISPATCH-CANDIDATE-EXPORT-20260605/dispatch_candidate.json
```

Then generate a dispatch plan:

```bash
python3 scripts/pnh_dispatch_job.py \
  --input-json ops/runs/PNH-DISPATCH-CANDIDATE-EXPORT-20260605/dispatch_candidate.json \
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
- Candidate export does not decrypt private bodies by default.

## Remaining Work

- Store `githubIssueUrl` and `discordThreadId` back into PNH browser state or companion metadata.
- Add duplicate detection against existing GitHub Issues if local state is missing.
- Capture real OpenClaw worker-session result IDs after actual worker execution is enabled.

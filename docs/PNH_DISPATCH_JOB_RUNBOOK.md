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
-> PNH Launch UI can read redacted mapping through the paired companion bridge
-> operator can confirm external ID metadata into browser-local Launch records
-> optional local worker-result metadata can be recorded for status display
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

Record a local worker-result rehearsal without external calls:

```bash
python3 scripts/pnh_worker_result_record.py \
  --packet-id <capture_or_packet_id> \
  --worker-session-id <worker_session_or_rehearsal_id> \
  --status done
```

Add `--apply` only when the dry-run output is correct. The script records metadata only and does not store private command bodies.

Run an OpenClaw worker turn and capture metadata without delivering a Discord reply:

```bash
python3 scripts/pnh_openclaw_worker_capture.py \
  --packet-id <capture_or_packet_id> \
  --agent qa \
  --message-file ops/runs/<run-id>/worker_prompt.txt
```

Apply mode requires both `--apply` and `--approve-openclaw-agent-run` because it can invoke the configured model provider through OpenClaw. The script stores only session/status/evidence metadata in local dispatch state.

Export a supervisor-facing evidence summary from local dispatch state:

```bash
python3 scripts/pnh_dispatch_evidence_summary.py
```

The summary derives `taskStatus`, `evidenceCompleteness`, `missingEvidence`, and `nextAction` without reading or printing private command bodies.

After refreshing dispatch state in the Launch UI, use `Confirm Task Status` to persist the synthesized task/evidence metadata into the browser-local Launch record and update the Projects/Tasks board. This stores status fields and evidence references only, not private command bodies.

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

- Add status refresh for already-linked GitHub Issues and Discord/OpenClaw threads.
- Add duplicate detection against existing GitHub Issues if local state is missing.
- Convert confirmed Launch task status into project/task board progress.

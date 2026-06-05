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

Refresh linked GitHub Issue status into local dispatch state:

```bash
python3 scripts/pnh_dispatch_status_refresh.py --github-read
```

Default mode writes a redacted dry-run output only. Add `--apply` to update the ignored local dispatch state with GitHub issue state, labels, and checked timestamp. This script performs no GitHub, Discord, or OpenClaw writes.

Plan external reconciliation without performing writes:

```bash
python3 scripts/pnh_external_reconciliation_plan.py
```

This creates a redacted plan for stale external metadata such as replacing
`dispatch:not-dispatched` with `dispatch:worker-done`. It does not update
GitHub, Discord, or OpenClaw. Any planned external write requires a separate
operator approval gate.

Apply an approved GitHub label reconciliation plan:

```bash
python3 scripts/pnh_github_label_reconciliation_apply.py \
  --apply \
  --approve-external-write
```

This mutates GitHub Issue labels through the authenticated `gh` CLI. It stores
before/after label names and does not print token values or private command
bodies.

Probe whether Discord/OpenClaw thread read-refresh can be implemented:

```bash
python3 scripts/pnh_discord_thread_readiness_probe.py
```

Default mode checks local OpenClaw CLI capability only. Live Discord reads are
blocked behind `--openclaw-read --approve-discord-read` because reading channel
content can expose private thread messages even without writing.

Refresh Discord thread metadata into local dispatch state:

```bash
python3 scripts/pnh_discord_thread_status_refresh.py \
  --openclaw-read \
  --approve-discord-read \
  --apply
```

This performs a read-only Discord/OpenClaw call and stores metadata only:
return code, observed message count, checked timestamp, and byte count. It does
not store message content.

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

Export a Markdown review summary for supervisor handoff:

```bash
python3 scripts/pnh_supervisor_review_summary.py
```

This converts redacted dispatch evidence into a review checklist and per-packet status summary. It does not include raw private command bodies, token values, or secret values.

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
  --discord-target channel:1511691320136306718 \
  --detect-existing-github
```

`--detect-existing-github` performs a read-only exact-title GitHub Issue check when a runtime token is available. In dry-run mode, missing token status is reported in the plan without creating anything. In apply mode, a failed duplicate read-check fails closed before creating a new issue.

Run the operational auto-dispatch dry-run from the local private inbox:

```bash
python3 scripts/pnh_auto_dispatch_from_inbox.py --detect-existing-github
```

This wrapper exports a metadata-only candidate from the local private inbox, generates a dispatch plan, and writes:

```text
ops/runs/PNH-AUTO-DISPATCH-FROM-INBOX-20260605/dispatch_candidate.json
ops/runs/PNH-AUTO-DISPATCH-FROM-INBOX-20260605/dispatch_plan.json
ops/runs/PNH-AUTO-DISPATCH-FROM-INBOX-20260605/auto_dispatch_summary.json
```

Default mode is dry-run and must not create GitHub Issues, Discord threads/messages, GitHub comments, or OpenClaw messages.

Plan an unattended dispatch pilot queue without enabling it:

```bash
python3 scripts/pnh_unattended_dispatch_queue_plan.py
python3 scripts/pnh_unattended_dispatch_readiness.py
```

This checks queue eligibility, rate limits, rollback requirements, and pilot
readiness. It performs no external writes. Live unattended pilot activation
requires `APPROVE_PNH_UNATTENDED_DISPATCH_PILOT`.

## Apply Requirements

Apply mode requires:

- supervisor approval for external writes
- `--apply`
- `--approve-live-dispatch`
- `--approve-external-write`
- `GITHUB_TOKEN` available in the runtime environment
- `--approve-discord-dispatch` if creating a Discord thread
- approved OpenClaw env file for gateway/Discord secrets

The live-dispatch approval gate exists because apply mode can create GitHub Issues, Discord threads/messages, GitHub comments, and OpenClaw messages. Dry-run planning, local metadata export, and smoke checks do not require that gate.

## Privacy Rules

- Raw private command body is never included by default.
- Token values are never printed.
- GitHub Issue body records metadata and local capture references only.
- Discord messages are routing summaries only.
- Candidate export does not decrypt private bodies by default.

## Remaining Work

- Implement approval-gated Discord/OpenClaw thread read-refresh using the
  detected `openclaw message read --json` capability.
- Apply GitHub Issue dispatch label reconciliation only after an external write
  approval gate.
- Promote browser-local Projects/Tasks progress to a durable local task store
  if multi-device status authority becomes necessary.

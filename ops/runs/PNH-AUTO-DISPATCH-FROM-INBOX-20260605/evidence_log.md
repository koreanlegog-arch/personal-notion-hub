# Evidence Log: PNH Auto Dispatch From Inbox

Date: 2026-06-05

## Goal

Make the local private inbox to dispatch-job bridge safe for repeated use by
preventing already dispatched or worker-completed command packets from being
selected again as automatic dispatch candidates.

## Acceptance Criteria

- Auto-dispatch dry-run exports metadata only.
- Raw private command bodies are not printed or written to tracked evidence.
- Apply mode remains guarded by explicit live-dispatch flags.
- Candidate export skips capture IDs already present in local dispatch state.
- If no new command candidate exists, the command fails closed instead of
  reusing an existing dispatched packet.

## Changes

- `scripts/pnh_dispatch_candidate_export.py`
  - Added dispatch-state awareness.
  - Added `--state-file`.
  - Added `--allow-dispatched` only for explicit override scenarios.
  - Rejects an explicit `--capture-id` when that ID is already present in dispatch state.
- `scripts/pnh_auto_dispatch_from_inbox.py`
  - Passes the selected dispatch state file into candidate export.
- `scripts/pnh_auto_dispatch_from_inbox_smoke_check.py`
  - Added a regression check that a processed capture cannot be auto-exported.

## Verification

Executed:

- `python3 -m py_compile scripts/pnh_auto_dispatch_from_inbox.py scripts/pnh_auto_dispatch_from_inbox_smoke_check.py scripts/pnh_dispatch_candidate_export.py scripts/pnh_dispatch_job.py`
  - Result: passed.
- `python3 scripts/pnh_auto_dispatch_from_inbox_smoke_check.py`
  - Result: passed.
  - Evidence: `pnh_auto_dispatch_from_inbox_smoke_check_pass=true`, `writes_performed=false`, `private_values_printed=false`.
- `python3 scripts/pnh_dispatch_candidate_export_smoke_check.py`
  - Result: passed.
- `python3 scripts/pnh_dispatch_job_smoke_check.py`
  - Result: passed.
- `python3 scripts/private_inbox_status.py`
  - Result: `totalCaptures=8`, all captures are `encrypted-vault`, private values were not printed.
- `python3 scripts/pnh_dispatch_state_status.py --include-urls`
  - Result: 4 dispatch records, 3 GitHub/Discord linked, 4 worker results, private values were not printed.
- `python3 scripts/pnh_auto_dispatch_from_inbox.py --run-dir ops/runs/PNH-AUTO-DISPATCH-FROM-INBOX-20260605 --detect-existing-github`
  - Result: expected fail-closed result: `no exportable command candidate found`.

## Finding

Before the patch, the actual encrypted inbox dry-run selected
`capture-5345e37040604a2fca64f317`, which was already in dispatch state with
worker evidence. This would have made repeated unattended runs ambiguous.

After the patch, already-dispatched capture IDs are excluded and the command
fails closed when there is no new exportable command candidate.

## Safety

- No external writes were performed.
- No real private command body was decrypted, printed, or written to tracked evidence.
- Stale pre-patch dry-run artifacts were intentionally removed from this run directory
  because they represented a now-rejected duplicate-dispatch candidate.

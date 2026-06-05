# Evidence Log: PNH Approval Gate Diet

Date: 2026-06-05

## Commands Run

```bash
find /home/koreanlego/projects -maxdepth 5 \( -iname '*archive*' -o -iname '*obsolete*' -o -iname '*prun*' -o -iname '*deprecated*' \) -print
rg -n "Approval Gates|separate approval|separately approved|until separately approved|Before routine use|Forbidden before separate approval|not ready for|Not Ready For|Approval Gates Remaining" docs ops/runs -g '*.md'
```

## Findings

- Existing instruction archive found at `/home/koreanlego/projects/ops/reports/INSTRUCTION_PRUNING_ARCHIVE_2026-06-04.md`.
- PNH has no project-local `.agents/skills` folder; active skill pruning is not needed inside this repo.
- Historical `ops/runs/*` packets contain many approval gates that were accurate before later phases closed those gates.
- Active docs needed a current policy layer to prevent old packet text from causing repeated micro-approval.

## Changes Made

- Added `docs/APPROVAL_GATE_POLICY.md`.
- Added `ops/runs/PNH-APPROVAL-GATE-DIET-20260605/approval_gate_archive.md`.
- Updated active PNH docs to reflect current implemented status.

## Validation

Commands:

```bash
rg -n "separate approval|separately approved|until separately approved|Forbidden before separate approval|Approval Gates Remaining|still required before|not yet implemented|Status: partially|Current MVP does not|write encrypted vault data|handle real private data|approved loopback bridge" docs ops/runs/PNH-APPROVAL-GATE-DIET-20260605 -g '*.md'
python3 scripts/smoke_check.py
git diff --check
find docs ops/runs/PNH-APPROVAL-GATE-DIET-20260605 -type f -name '*.md' -size 0 -print
```

Results:

- Remaining approval phrases are either active material gates, archive quotations, or historical interpretation notes.
- `smoke_check_pass=true`.
- `git diff --check` passed.
- No empty Markdown files found.

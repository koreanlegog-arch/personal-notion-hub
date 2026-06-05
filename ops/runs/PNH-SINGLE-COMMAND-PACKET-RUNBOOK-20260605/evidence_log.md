# Evidence Log: PNH Single Command Packet Runbook

Date: 2026-06-05

## Scope

Create a reusable runbook for processing one PNH private-inbox command packet
from queue selection through worker-done evidence and supervisor summary.

## Files

- `docs/PNH_SINGLE_COMMAND_PACKET_RUNBOOK.md`
- `docs/CURRENT_CAPABILITIES.md`
- `docs/PNH_DISPATCH_JOB_RUNBOOK.md`

## Evidence Basis

The runbook is based on verified packet runs:

- GitHub Issue `#3`, Discord thread `1512315698351706183`, worker session
  `pnh:capture-2a0fcdefc3f169ec30c6497f:qa`
- GitHub Issue `#4`, Discord thread `1512323845514596373`, worker session
  `pnh:capture-3b8522ff102b0469c683b027:qa`

## Safety Controls Included

- metadata-only candidate export
- bounded queue and rate-limit model
- rollback snapshot requirement
- sequential state refresh order
- metadata-safe worker prompt generation
- no raw private command body in worker prompt
- no Discord reply delivery during worker capture
- GitHub label reconciliation dry-run before apply
- final pending external write check

## Verification Planned

Runbook verification uses Markdown existence, smoke checks, secret pattern scan,
and `git diff --check`.

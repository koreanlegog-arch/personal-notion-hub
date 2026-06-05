# Task Packet: PNH Idempotent Dispatch Job

Date: 2026-06-05

## Objective

Create a repeatable dispatch job that can route a PNH command packet to GitHub Issue ledger and Discord/OpenClaw thread targets without duplicate external records.

## Scope

- Implement dry-run default dispatch job.
- Add local apply-mode state file design.
- Keep private values out of stdout, GitHub body, and Discord messages by default.
- Add smoke tests for dry-run and approval gates.
- Document runbook and residual work.

## Out Of Scope

- Running apply mode in this packet.
- Pulling real browser localStorage from a live browser.
- Auto-dispatching every PNH capture.
- Real worker execution.
- Secret storage workflow changes.

## Acceptance Criteria

- Dry-run writes a dispatch plan only.
- Apply without approval flags fails closed.
- Synthetic private title/body are not present in dry-run output.
- Local state path is ignored by Git.
- Verification commands are recorded.

## Risk Level

Medium.

Reason: implementation prepares repeatable external writes, but this packet validates only dry-run behavior.

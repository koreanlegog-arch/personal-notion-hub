# Task Packet: PNH External Reconciliation Planning

Date: 2026-06-05

## Objective

Prepare the next PNH Launch-to-worker stabilization step without performing
external writes.

## Scope

- Plan GitHub Issue label/status reconciliation from local dispatch metadata.
- Probe Discord/OpenClaw thread read-refresh capability without reading channel
  content by default.
- Keep all outputs metadata-only and redacted.
- Stop before GitHub, Discord, or OpenClaw external mutation.

## Out Of Scope

- Updating GitHub Issue labels, state, or comments.
- Posting Discord/OpenClaw messages.
- Reading Discord thread content without explicit operator approval.
- Running OpenClaw worker/model calls.
- Changing live gateway config or tokens.

## Acceptance Criteria

- Reconciliation plan identifies stale external metadata.
- Discord/OpenClaw read-refresh feasibility is classified.
- No secret or private command body is printed.
- No external writes are performed.
- The next approval gate is explicit and justified.

## Approval Gate

Required before applying planned GitHub label changes or live Discord/OpenClaw
thread reads/writes.

Reason: GitHub label updates mutate an external ledger, and Discord reads can
expose private channel content even when no message is sent.

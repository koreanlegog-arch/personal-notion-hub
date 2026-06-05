# Task Packet: PNH Unattended Dispatch Readiness

Date: 2026-06-05

## Objective

Prepare PNH for an approval-gated unattended dispatch pilot by defining queue,
rollback, and rate-limit controls without enabling automatic external dispatch.

## Scope

- Add dry-run queue planning from local private-inbox metadata.
- Add readiness assessment for an unattended dispatch pilot.
- Document queue, rollback, and rate-limit rules.
- Produce evidence that no external writes are performed by readiness tooling.

## Out Of Scope

- Enabling unattended dispatch.
- Creating GitHub Issues automatically.
- Creating Discord/OpenClaw threads automatically.
- Running OpenClaw worker/model calls automatically.
- Installing a daemon, scheduler, or service.
- Adding real phone/contact/calendar/call/recording adapters.

## Acceptance Criteria

- Queue planning identifies eligible captures without printing private values.
- Queue plan includes rate-limit and rollback requirements.
- Readiness assessment returns a clear verdict.
- Activation gate is explicit.
- Smoke checks pass.
- No external writes are performed.

## Approval Gate

Activation requires:

```text
APPROVE_PNH_UNATTENDED_DISPATCH_PILOT
```

Reason: unattended pilot mode can create external GitHub/Discord/OpenClaw
records without per-item operator confirmation.

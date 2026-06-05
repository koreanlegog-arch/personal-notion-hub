# Readiness Packet: PNH Unattended Dispatch Pilot

Date: 2026-06-05

## Verdict

Ready for approval-gated pilot.

One approved pilot batch has now been executed.

## Scope Covered

```text
private inbox metadata
-> queue dry-run plan
-> rate-limit and rollback policy
-> readiness assessment
-> activation gate
```

## Current Queue Result

- captures inspected: `8`
- queued for pilot candidate: `0` after pilot cooldown
- skipped: `8`
- external writes performed: `false`
- private values printed: `false`

## Pilot Limits

- max jobs per run: `1`
- max external writes per hour: `3`
- cooldown: `10` minutes

## Safety Controls

- dry-run only
- plaintext captures blocked by default
- already-dispatched captures skipped
- single-writer lock required before future apply runner
- rollback snapshot required before future apply runner
- no message body or private command body stored in readiness evidence

## Activation Gate

Activation requires:

```text
APPROVE_PNH_UNATTENDED_DISPATCH_PILOT
```

Reason: unattended dispatch can create GitHub Issues, Discord/OpenClaw threads,
GitHub comments, and worker/model calls without per-item operator confirmation.

## Current Non-Blocking Notes

- One encrypted `project_brief` capture was dispatched by the first pilot batch.
- One additional encrypted `project_brief` capture is eligible but skipped by
  cooldown/rate-limit controls.
- `assistant_capture` records are correctly skipped because they are not command
  dispatch kinds.

## Not Yet Enabled

- no daemon
- no scheduler
- no automatic external dispatch apply
- no automatic retry loop
- no real phone/contact/calendar/call/recording adapter

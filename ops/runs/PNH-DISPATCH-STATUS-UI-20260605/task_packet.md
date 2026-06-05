# Task Packet: PNH Dispatch Status UI

Date: 2026-06-05

## Objective

Show redacted local dispatch state in the PNH Launch screen through the paired local companion.

## Scope

- Add read-only companion endpoint for dispatch state metadata.
- Add browser bridge method for paired dispatch state reads.
- Add Launch screen `Dispatch status` panel.
- Add smoke validation.

## Out Of Scope

- External GitHub/Discord/OpenClaw writes.
- Raw private body display.
- URL display by default.
- Daemon, scheduler, or token workflow changes.

## Acceptance Criteria

- Endpoint requires existing private auth/session path.
- UI displays counts and IDs only.
- Browser bridge does not persist session tokens.
- Smoke checks pass.

## Risk Level

Low-Medium.

Reason: local read-only metadata endpoint, but exposed through the paired browser bridge.

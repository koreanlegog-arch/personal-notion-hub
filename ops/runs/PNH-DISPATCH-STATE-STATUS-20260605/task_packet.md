# Task Packet: PNH Dispatch State Status

Date: 2026-06-05

## Objective

Expose local dispatch state as a redacted status command so linked GitHub issue and Discord thread metadata can be inspected without opening private state files directly.

## Scope

- Add local-only dispatch state status script.
- Add fixture smoke validation.
- Keep URLs hidden by default.
- Do not contact GitHub, Discord, or OpenClaw.

## Out Of Scope

- Creating or updating external records.
- Writing dispatch state.
- UI integration.
- Reading raw private command bodies.

## Acceptance Criteria

- Missing state file returns an empty status successfully.
- Existing state shows counts and IDs without private notes.
- External URLs are hidden unless `--include-urls` is passed.
- Validation evidence is recorded.

## Risk Level

Low.

Reason: local metadata read-only status command.

# PNH-SENSITIVE-LOCAL-OWNER-MVP-20260605 Task Packet

## Objective

Move Personal Notion Hub from demo/private-inbox compatibility toward a local
owner mode that is safe enough to begin supervisor-controlled sensitive testing.

## Scope

- Confirm current keychain/passphrase readiness without printing secrets.
- Confirm encrypted vault lifecycle smoke checks still pass with synthetic data.
- Detect plaintext inbox rows that block routine sensitive use.
- Add an owner readiness check that summarizes blockers.
- Keep real passphrase entry and plaintext migration apply behind explicit local operator gates.

## Out Of Scope

- Requesting or recording the real vault passphrase.
- Migrating or deleting existing plaintext inbox rows automatically.
- Opening phone ingress or public network access.
- Adding phone/contact/calendar/recording adapters.
- Adding cloud sync, OAuth, Discord, GitHub, or OpenClaw live dispatch.

## Acceptance Criteria

- Readiness check reports keychain status, passphrase storage status, plaintext row count, and private-value output status.
- Readiness check does not print secret or private values.
- Existing synthetic encrypted vault, backup, delete, rotation, migration apply, and DPAPI smoke checks pass.
- Current blockers are documented before sensitive real data entry.

## Risk

Medium-high. This phase is the boundary before real sensitive local data may be
entered. The implementation must be conservative and fail closed when passphrase
storage or plaintext cleanup is incomplete.

# Task Packet: PNH Dispatch Local Rehearsal

Date: 2026-06-05

## Objective

Bundle dispatch candidate export, dispatch dry-run plan generation, and redacted state status into one local rehearsal command.

## Scope

- Add local-only rehearsal script.
- Add fixture smoke validation.
- Produce candidate, plan, and status artifacts.
- Avoid all external writes.

## Out Of Scope

- GitHub issue creation.
- Discord/OpenClaw message creation.
- Scheduler or daemon setup.
- Secret workflow changes.

## Acceptance Criteria

- Rehearsal command performs no external writes.
- Private body/title values are not printed or written to rehearsal outputs.
- Smoke check passes with temporary fixture DB.
- Real local run can produce metadata-only artifacts from the current encrypted vault.

## Risk Level

Low.

Reason: local-only dry-run orchestration.

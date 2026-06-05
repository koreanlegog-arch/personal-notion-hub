# Task Packet: PNH Discord/OpenClaw Dispatch Rehearsal

Date: 2026-06-05

## Objective

Connect the approved PNH GitHub Issue ledger entry to a Discord/OpenClaw worker-routing rehearsal.

## Scope

- Use GitHub issue #1 as the durable ledger reference.
- Create a Discord `#command-center` thread through OpenClaw.
- Post worker lifecycle rehearsal messages.
- Post an `#audit-log` mapping message.
- Comment back on the GitHub issue with the Discord thread reference.

## Out Of Scope

- Real slash command implementation.
- Real production worker execution.
- Permission overwrite changes.
- OpenClaw config mutation.
- Token rotation or secret storage changes.
- Posting raw private command body.

## Acceptance Criteria

- Discord thread exists.
- Thread contains task create, assign, review, QA, and done messages.
- Audit-log message records the issue/thread mapping.
- GitHub issue comment records the dispatch rehearsal reference.
- No token value or raw private command body is printed or committed.

## Risk Level

Medium.

Reason: this phase performs live Discord and GitHub mutations, but only with privacy-preserving rehearsal content.

## Approval Boundary

Approved by the supervisor request to continue from `APPROVE_PNH_GITHUB_ISSUE_LEDGER_APPLY` into Discord/OpenClaw dispatch rehearsal.

Not approved in this packet:

- unattended production worker execution
- automatic dispatch from every PNH capture
- broader OpenClaw gateway config changes
- exposing private packet bodies to GitHub or Discord

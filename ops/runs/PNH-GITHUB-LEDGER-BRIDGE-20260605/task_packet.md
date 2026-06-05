# Task Packet: PNH GitHub Ledger Bridge

Date: 2026-06-05

## Objective

Design and prepare a GitHub Issues ledger bridge so PNH mobile command packets can become durable task records before Discord/OpenClaw worker dispatch.

## Scope

- Document the GitHub ledger bridge architecture.
- Implement a dry-run GitHub Issue payload generator.
- Add smoke validation for no external write and no private value leakage.
- Stop before live GitHub mutation.

## Out Of Scope

- Creating real GitHub Issues.
- Mutating GitHub Projects.
- Storing or rotating GitHub tokens.
- Dispatching work to Discord/OpenClaw.
- Including raw sensitive project brief contents in GitHub.

## Acceptance Criteria

- Dry-run is the default.
- Live issue creation requires explicit apply and approval flags.
- Missing token in dry-run does not block local validation.
- Sensitive title/body are not included by default.
- GitHub Projects work remains a documented future phase.
- Validation commands are recorded.

## Risk Level

Medium.

Reason: the bridge prepares an external write path, but this phase does not execute it.

## Approval Gates

- Live GitHub issue creation requires supervisor approval.
- Any GitHub token workflow change requires supervisor approval.
- Including raw sensitive fields in GitHub requires separate supervisor approval.
- GitHub Projects mutation requires a separate design and approval gate.

## Recommended Next Gate

```text
APPROVE_PNH_GITHUB_ISSUE_LEDGER_APPLY
```

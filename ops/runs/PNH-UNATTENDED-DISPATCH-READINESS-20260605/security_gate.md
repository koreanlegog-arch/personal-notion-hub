# Security Gate: PNH Unattended Dispatch Readiness

Date: 2026-06-05

## Risk Summary

Unattended dispatch is higher risk than current owner-operated commands because
it can turn local mobile captures into external GitHub/Discord/OpenClaw records
without a person reviewing each item.

## Secret Exposure Assessment

- Token values must not be printed.
- GitHub authentication should continue to use `gh` or approved env references.
- OpenClaw should continue to use the approved local env file.
- Reports must not include raw private command bodies.

## Permission Assessment

Required future permissions:

- GitHub Issues read/write for the target repository.
- Discord/OpenClaw channel thread/message permission for the approved control
  channel.
- Local read/write for ignored private state files.

No new permission is granted by the current readiness packet.

## Data Flow Risk

Allowed data flow for readiness:

```text
private inbox metadata -> queue plan -> readiness report
```

Blocked until activation gate:

```text
private inbox metadata -> GitHub Issue
private inbox metadata -> Discord/OpenClaw thread
private inbox metadata -> worker/model run
```

## Required Mitigations

- Queue uses metadata only.
- Plaintext candidates are blocked by default.
- One job per run default.
- Three external writes per hour default.
- Rollback snapshot required before apply.
- Single-writer lock required before future apply runner.

## Approval Gates

- `APPROVE_PNH_UNATTENDED_DISPATCH_PILOT` for the first live unattended pilot.
- Separate approval remains required for daemon/service/scheduler installation.
- Separate approval remains required for real private-data adapters.

## Residual Risk

The current packet does not yet implement durable dispatch history or retry
state. Those must be added before unattended mode can run repeatedly.

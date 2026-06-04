# Release Readiness: PNH Tailnet Manual Phone QA

Date: 2026-06-05

## Verdict

Ready for repeated owner-only tailnet manual sessions.

## Evidence

- Real phone capture reached the encrypted vault.
- Private values were not printed by status commands.
- Helper scripts added for repeatable session start/stop.
- Stop helper removed temporary forwarding successfully.
- Full smoke check passed after helper scripts were added.

## Not Ready For

- Client-facing deployment.
- Public internet exposure.
- Always-on unattended remote access.

## Required Operator Note

After a manual session, stop the companion process and run:

```bash
bash scripts/stop_tailnet_session.sh
```

if the start script did not already clean up on exit.

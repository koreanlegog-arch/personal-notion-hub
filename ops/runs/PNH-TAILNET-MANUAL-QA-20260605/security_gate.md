# Security Gate: PNH Tailnet Manual Phone QA

Date: 2026-06-05

## Verdict

Ready for owner-only manual QA.

## Controls

- Tailscale-only remote path.
- Companion remains bound to `127.0.0.1`.
- Windows `portproxy` and firewall rule are temporary.
- Encrypted vault mode is required.
- Pairing code is local-terminal-only.
- Session token and capture body are not recorded.

## Residual Risk

Fallback URL uses browser HTTP over the encrypted Tailscale tunnel. This remains owner-only MVP infrastructure, not client-facing deployment.


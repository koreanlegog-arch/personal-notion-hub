# Security Gate: PNH Remote Access via Tailscale

Date: 2026-06-05

## Verdict

Ready for owner-only MVP testing with explicit constraints.

## Security Constraints

- PNH remains local-first and binds to `127.0.0.1`.
- Tailscale is the only remote network path approved for this phase.
- Encrypted vault mode is required before sensitive owner data entry.
- Pairing code and session token must never be recorded.
- Public origins, wildcard origins, and public IP origins are rejected.
- Temporary Windows firewall/portproxy rules must be removed after tests unless an active owner session is intentionally running.

## Accepted Temporary Risk

The fallback path uses `http://<tailnet-ip>:8765` in the browser because the current Tailscale account does not support TLS certificates. Traffic still traverses Tailscale's encrypted tailnet, but the browser origin is not HTTPS. This is acceptable only for owner-only MVP rehearsal, not for client-facing deployment.

## Blockers

No blocker for owner-only MVP testing.

For HTTPS Tailscale Serve, the account must support Tailscale certificates or a future equivalent configuration.

## Required Operator Actions

- Keep the phone signed in to the same tailnet.
- Use only the generated pairing code in the UI.
- Remove fallback portproxy/firewall rules after the session.
- Rotate or reset any secret if it is accidentally pasted into chat or logs.


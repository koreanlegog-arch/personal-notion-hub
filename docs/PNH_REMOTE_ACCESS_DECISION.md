# PNH Remote Access Decision

Date: 2026-06-05

## Decision

Personal Notion Hub remote access should use Tailscale as the first remote-access layer for owner-only mobile ingress.

The preferred operating path is:

1. Windows host runs Tailscale.
2. PNH companion stays local-first and binds to `127.0.0.1:8765` inside WSL.
3. Tailscale Serve exposes the local companion to the tailnet when HTTPS certificates are available.
4. If Tailscale HTTPS certificates are unavailable, use a temporary Windows `portproxy` from the Windows tailnet IPv4 to WSL loopback as a fallback.

Do not use public port forwarding, Cloudflare Tunnel, ngrok, or internet-facing exposure for sensitive owner data unless a separate security review approves that change.

## Rationale

The original private LAN route was blocked because the PC did not have a phone-reachable private LAN address. The phone and PC can still communicate through Tailscale because Tailscale creates an encrypted tailnet path independent of the home LAN topology.

Tailscale also keeps the remote-access surface small:

- No public IP exposure is required.
- Phone access can be restricted to the owner's tailnet devices.
- PNH can remain local-first with encrypted SQLite storage.
- Pairing/session tokens remain short-lived and local to the companion.

## Current Environment Finding

Tailscale was installed on the Windows host and the Windows node plus Android phone appeared in the same tailnet.

Tailscale HTTPS Serve could not be completed in this environment because `tailscale cert` returned that the account does not currently support Tailscale TLS certificates. Therefore, the working rehearsal path for now is:

`phone -> Tailscale WireGuard tunnel -> Windows tailnet IPv4:8765 -> Windows portproxy -> WSL 127.0.0.1:8765 -> PNH companion`

This fallback is not public internet exposure, but the browser URL is `http://...` rather than `https://...`. Treat it as acceptable for owner-only MVP testing through Tailscale, not as a general client-facing deployment pattern.

## Accepted Architecture

- Companion bind: `127.0.0.1:8765`
- Storage mode: encrypted vault required for sensitive data
- Browser bridge: required
- Allowed origin: exact tailnet origin only
- Tailnet HTTPS origin: `https://<windows-tailnet-dns>`
- Tailnet HTTP fallback origin: `http://<windows-tailnet-ip>:8765` or `http://<windows-tailnet-dns>:8765`
- Public origin: rejected
- Wildcard origin: rejected
- Pairing/session values: never logged or documented

## Rejected Options

### Public port forwarding

Rejected because it would expose an early owner-data workflow to the public internet and require harder auth, monitoring, rate limiting, and patch discipline.

### ngrok or similar public tunnel

Rejected for the current phase because it adds third-party exposure and account-level tunnel security before the local companion has a mature production auth layer.

### Running Tailscale in both Windows and WSL

Rejected for this phase. Tailscale's WSL guidance prefers using the Windows host client for WSL access instead of running two overlapping clients.

### Cloud-hosted PNH backend

Rejected for sensitive owner data MVP. Cloud storage can be reconsidered later with client-grade auth, encryption, backups, audit logs, and retention controls.

## Security Constraints

- Never store real tokens or pairing codes in repo files.
- Never print pairing code, session token, vault passphrase, or private capture body in reports.
- Keep firewall/portproxy changes temporary unless explicitly enabling a live owner session.
- Reset `tailscale serve` after tests unless a live session is intentionally being kept open.
- Use encrypted vault mode before accepting sensitive owner data.
- Use exact origin matching; do not use `*`, `localhost`, public IPs, or ambiguous hostnames.

## Source References

- Tailscale WSL guidance: https://tailscale.com/kb/1295/install-windows-wsl2
- Tailscale Serve documentation: https://tailscale.com/kb/1312/serve
- Tailscale Serve use cases: https://tailscale.com/kb/1247/funnel-serve-use-cases


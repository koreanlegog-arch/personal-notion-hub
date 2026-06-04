# Task Packet: PNH Remote Access via Tailscale

Date: 2026-06-05

## Objective

Enable and validate owner-only remote mobile access to PNH through Tailscale without exposing PNH to the public internet.

## Scope

- Document remote access decision.
- Document Tailscale runbook.
- Add tailnet ingress mode to the local companion.
- Support Tailscale HTTPS origin and tailnet HTTP fallback origin.
- Validate static UI, health, pairing, and encrypted capture through a tailnet path.

## Out Of Scope

- Public internet deployment.
- Cloud backend.
- Telegram/Discord ingestion.
- Persistent always-on Windows service for PNH.
- Storing or printing secrets, pairing codes, session tokens, or private capture bodies.

## Acceptance Criteria

- Companion can run in tailnet ingress mode while binding only to `127.0.0.1`.
- Exact Tailscale origin is required.
- Public and wildcard origins are rejected.
- Static UI is served in tailnet ingress mode.
- Pairing and mobile capture work through tailnet rehearsal.
- Rehearsal leaves no persistent test portproxy/firewall rule.
- Runbook documents preferred HTTPS and fallback tailnet HTTP paths.

## Validation Plan

- Run Python compile checks.
- Run tailnet ingress smoke check.
- Run browser bridge and phone ingress smoke checks.
- Run full smoke check.
- Run sensitive owner readiness check.
- Run one real tailnet fallback rehearsal with synthetic data only.

## Risk Level

Medium. This touches remote access, Windows firewall/portproxy during rehearsal, and private capture ingress. The rehearsal used temporary reversible Windows rules and synthetic data.


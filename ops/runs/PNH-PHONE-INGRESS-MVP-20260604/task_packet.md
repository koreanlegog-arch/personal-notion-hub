# PNH-PHONE-INGRESS-MVP-20260604 Task Packet

## Objective

Implement a safe MVP path for opening Personal Notion Hub from a phone browser on
the same trusted private LAN and sending explicit captures into the workspace
private inbox or encrypted vault path.

## Scope

- Add explicit `--enable-phone-ingress` companion mode.
- Keep loopback-only behavior as the default.
- Serve static PNH UI from the companion only in phone ingress mode.
- Allow private LAN origins only with exact origin matching.
- Reuse one-time pairing and memory-only browser session tokens.
- Add LAN helper, security guide, smoke check, docs, release notes, and evidence.

## Out Of Scope

- Real phone OS adapters.
- Contacts, call logs, recordings, transcripts, calendar sync, or external APIs.
- Public internet exposure.
- HTTPS/certificate provisioning.
- Automatic background sync.
- Real sensitive data entry during automated tests.

## Acceptance Criteria

- Non-loopback bind is rejected unless phone ingress is explicitly enabled.
- Phone ingress requires private inbox and browser bridge mode.
- Public, wildcard, `localhost`, and `0.0.0.0` browser origins are rejected.
- Companion serves the static UI in phone ingress mode.
- One-time pairing still gates browser writes.
- Synthetic phone-style capture reaches SQLite without title/body echo in responses.
- Existing loopback browser bridge, private inbox, companion, static smoke, and Playwright redacted QA still pass.

## Risk

Medium-high. This intentionally exposes a local companion service to a private
LAN, so it must stay opt-in, exact-origin, paired, metadata-only, and synthetic
first.

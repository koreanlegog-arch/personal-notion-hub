# PNH-ASSISTANT-WORKSPACE-INGRESS-20260604 Task Packet

## Objective

Allow a synthetic or low-risk Assistant web input to reach the workspace local
private inbox/encrypted vault path through the existing paired companion bridge.

## Scope

- Extend the companion bridge with a generic capture send function.
- Add an Assistant-specific send wrapper.
- Add Assistant UI controls for companion status, pairing, redaction, latest-input send, and per-capture send.
- Keep browser auth material memory-only.
- Verify that the bridge can store assistant-style synthetic payloads.
- Update docs, release notes, and run evidence.

## Out Of Scope

- Real phone/LAN/mobile-device connection.
- Automatic send on every Assistant input.
- External APIs, cloud sync, OAuth, Discord, Telegram, or GitHub issue creation.
- Real private data in tests or evidence.
- New dependency installation.

## Acceptance Criteria

- Assistant input remains usable in browser-only IndexedDB mode.
- A paired companion session can send the latest Assistant input to `/api/private/mobile-captures`.
- A capture card can send an individual Assistant input.
- Browser responses remain metadata-only.
- File token, pairing code, browser session token, title, and body are not echoed in smoke responses.
- Static smoke still allows `fetch` only in `assets/js/companion-bridge.js`.
- Browser bridge smoke stores both launch-style and assistant-style synthetic captures.

## Risk

Medium. This touches browser-to-local private inbox flow, but it reuses the
existing paired loopback endpoint and does not expose new external surfaces.

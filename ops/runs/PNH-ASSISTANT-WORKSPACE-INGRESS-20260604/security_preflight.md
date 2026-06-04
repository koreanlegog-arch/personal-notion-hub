# Security Preflight

## Constraints

- No automatic Assistant-to-workspace writes.
- No real private data in tests or evidence.
- Browser session token remains memory-only.
- Pairing code is local-terminal only and must not be recorded.
- Bridge requests remain restricted to `http://127.0.0.1:8765`.
- Responses must not echo Assistant title/body values.

## Controls

- Assistant send path uses the existing authenticated `/api/private/mobile-captures` endpoint.
- `assets/js/companion-bridge.js` remains the only browser JavaScript module allowed to call `fetch`.
- Assistant body previews are marked `data-sensitive` for screenshot redaction.
- UI exposes explicit `Send Latest Input` and `Send to Workspace` actions instead of background sync.

## Residual Risks

- Manual browser QA is still required to validate final visual layout.
- This does not make phone/LAN access available.
- Real sensitive data should use encrypted vault mode and redacted QA.

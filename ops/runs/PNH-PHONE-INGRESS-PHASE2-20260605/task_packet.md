# PNH-PHONE-INGRESS-PHASE2-20260605 Task Packet

## Objective

Continue from sensitive local owner readiness into actual phone ingress, where a
phone browser can reach the local companion and send captures into encrypted
vault mode.

## Scope

- Re-run LAN candidate detection.
- Re-run phone ingress reachability detection.
- Keep public IP exposure blocked.
- Proceed only if `safePhoneUrls` is non-empty.

## Out Of Scope

- Public IP exposure.
- Private tunnel/VPN setup.
- USB/ADB reverse setup.
- Windows firewall or portproxy mutation when no safe private LAN IP exists.
- Real phone/contact/calendar/recording adapters.

## Acceptance Criteria

- Phase 2 is ready only when a phone-reachable Windows private LAN IP is detected.
- `safePhoneUrls` must be non-empty before any portproxy/firewall rule is applied.
- Companion must run in encrypted vault mode for sensitive capture.
- Phone test must use synthetic or low-risk input first.

## Current Result

Blocked. No phone-reachable Windows private LAN IP is currently detected.

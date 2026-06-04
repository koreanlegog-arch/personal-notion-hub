# Release Readiness: PNH Remote Access via Tailscale

Date: 2026-06-05

## Verdict

Ready for owner-only MVP rehearsal.

Not ready for client-facing or public deployment.

## Scope Covered

- Tailnet ingress mode.
- Exact-origin browser bridge for Tailscale origins.
- Static UI served through tailnet ingress mode.
- Pairing and metadata-only encrypted capture response.
- Runbook and decision documentation.
- Temporary fallback rehearsal with cleanup.

## Validation Evidence

Passed:

- Python compile checks.
- Tailnet ingress smoke check.
- Real tailnet HTTP fallback rehearsal through Windows portproxy.

Passed final full suite:

- Browser bridge smoke check.
- Phone ingress smoke check.
- Sensitive owner readiness check.
- Full smoke check.
- Redacted browser QA.
- Playwright redacted UI QA.
- `git diff --check`.

## Security Status

Owner-only MVP acceptable with constraints. HTTPS Serve is preferred but blocked by current Tailscale account capability. Fallback tailnet HTTP is limited to Tailscale's encrypted tunnel and should not be treated as a general deployment model.

## Rollback

- Stop the companion process.
- Run `tailscale serve reset`.
- Delete Windows `portproxy` rule for port `8765`.
- Delete Windows firewall rule named `PNH Tailnet Ingress 8765`.
- Revert this commit if tailnet ingress support is no longer desired.

## Known Risks

- Fallback path uses browser HTTP origin, although traffic is inside Tailscale.
- Windows `portproxy`/firewall rules must not be left open unintentionally.
- Mobile manual QA from the actual phone is still recommended after enabling fallback for a live session.

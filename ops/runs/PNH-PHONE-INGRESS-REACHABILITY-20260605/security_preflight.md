# Security Preflight

## Security Constraints

- Do not expose Personal Notion Hub on a public Windows IP.
- Do not add Windows firewall or portproxy rules unless the target is a phone-reachable private LAN IP.
- Do not record pairing codes, session tokens, bearer tokens, or environment secret values in reports.
- Keep phone ingress opt-in and exact-origin only.
- Keep manual phone testing synthetic or low-risk until encrypted vault mode is verified on the same path.

## Blockers

- No phone-reachable private Windows LAN IP is currently detected.
- Windows loopback reaches the WSL companion, but that does not make the service reachable from the phone.
- The detected non-WSL Windows IP is public and is rejected by policy.

## Approval Gates

- Public IP exposure requires a separate security design and explicit approval.
- Private tunnel/VPN setup requires a separate integration and security review.
- USB/ADB reverse requires separate approval because it introduces a device integration path.
- Real sensitive phone input requires encrypted vault mode and a passed local reachability rehearsal.

## Incident Note

A PowerShell quoting mistake caused an environment token value to appear in local terminal output during diagnosis. The value is not recorded here. Rotate the affected Telegram bot token and avoid reusing terminal output that contains secret values.

## Release Constraint

Phone ingress remains blocked for actual phone use until `scripts/phone_ingress_reachability_check.py` reports at least one `safePhoneUrls` entry and the operator applies the corresponding private-LAN-only Windows forwarding rule.

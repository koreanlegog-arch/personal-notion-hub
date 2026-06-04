# Security Preflight

## Controls

- Disabled by default.
- Non-loopback bind requires `--enable-phone-ingress`.
- Phone ingress requires browser bridge and private inbox.
- Allowed origin must be exact HTTP loopback/private LAN host with a concrete port.
- `localhost`, `0.0.0.0`, wildcard, and public IP origins are rejected.
- One-time pairing code is still required.
- Browser session token stays in JS memory only.
- Responses remain metadata-only.
- Request bodies are not logged.

## Stop Conditions

- Untrusted Wi-Fi or public network.
- Pairing code appears in evidence.
- Allowed origin uses a public IP, hostname, wildcard, or `0.0.0.0`.
- API response echoes title/body.
- Sensitive data is entered before encrypted vault mode is enabled and verified.

## Residual Risks

- HTTP LAN traffic is not encrypted.
- Same-LAN attackers may probe the service while it is running.
- Operator must stop the companion after testing.
- Real sensitive phone ingress should use encrypted vault mode and trusted LAN only.

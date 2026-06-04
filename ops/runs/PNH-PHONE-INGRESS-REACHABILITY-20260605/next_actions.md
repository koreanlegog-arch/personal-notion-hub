# Next Actions

## Preferred Path

Use a trusted private LAN where Windows has a phone-reachable private IPv4 such
as:

- `192.168.x.x`
- `10.x.x.x`
- `172.16.x.x` through `172.31.x.x`, excluding WSL/vEthernet-only addresses

Then rerun:

```bash
python3 scripts/phone_ingress_lan_info.py
python3 scripts/phone_ingress_reachability_check.py
```

If `safePhoneUrls` is non-empty, use the script's
`adminCommandExamplesForPrivateIpsOnly` from an Administrator PowerShell.

## Blocked Current Path

Do not use:

```text
http://172.31.155.144:8765/
```

Reason: WSL internal NAT address, not phone-reachable.

Do not use the detected public Windows IP without a separate security decision.

## Alternatives

- Use a Windows/private-router network that gives the PC a private LAN IP.
- Use Android USB debugging plus `adb reverse` after separate approval.
- Use a private tunnel/VPN such as Tailscale only after separate integration and security review.
- Keep using desktop browser loopback until the network path is ready.

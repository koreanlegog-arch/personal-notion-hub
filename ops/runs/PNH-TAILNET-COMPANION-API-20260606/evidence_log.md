# Evidence Log: PNH Tailnet Companion API

Date: 2026-06-06

## Scope

Exposed the headless loopback companion service to the owner's tailnet through
temporary Windows `portproxy` forwarding.

## Path

```text
phone automation
-> Tailscale tailnet URL
-> Windows portproxy
-> WSL 127.0.0.1:8765 companion service
-> encrypted vault
```

## Verification

- `python3 scripts/pnh_tailnet_companion_api_smoke_check.py`: passed
- `bash scripts/pnh_tailnet_companion_api_start.sh --apply`: forwarding ready
- `python3 scripts/pnh_tailnet_companion_api_status.py`: tailnet running, health OK, encrypted vault enabled
- `python3 scripts/pnh_phone_adapter_send.py --base-url http://[tailnet-ip]:8765 --allow-owner-network --payload /tmp/pnh-tailnet-phone-template.json`: passed
- `python3 scripts/private_inbox_status.py --include-recent`: encrypted vault count increased, plaintext rows remained `0`

## Safety

- Exact tailnet IP is intentionally not recorded here.
- No secret values printed.
- No raw private values printed.
- This is owner-only tailnet exposure, not public internet deployment.

## Rollback

```bash
bash scripts/pnh_tailnet_companion_api_stop.sh --apply
```

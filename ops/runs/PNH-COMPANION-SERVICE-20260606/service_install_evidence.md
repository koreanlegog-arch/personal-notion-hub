# PNH Companion Service Evidence

Date: 2026-06-06

## Scope

Installed a headless loopback user-systemd service for the PNH companion API.

## Installed Unit

- `pnh-companion.service`

## Service Boundary

- host: `127.0.0.1`
- port: `8765`
- private inbox: enabled
- encrypted vault: enabled
- browser bridge: disabled
- pairing code printed: no

## Verification

- `python3 scripts/pnh_companion_service_plan_smoke_check.py`: passed
- `bash scripts/pnh_companion_install_user_service.sh --apply`: installed
- `python3 scripts/pnh_companion_service_status.py`: service active, health OK, encrypted vault enabled
- `python3 scripts/pnh_phone_adapter_send.py --base-url http://127.0.0.1:8765 --payload /tmp/pnh-phone-service-template.json`: passed
- `python3 scripts/private_inbox_status.py --include-recent`: encrypted vault count increased with metadata-only output

## Safety Notes

- No secret values printed.
- No raw private values printed.
- The service does not enable browser bridge or print pairing code.
- The service is loopback-only by default.

## Rollback

```bash
bash scripts/pnh_companion_uninstall_user_service.sh --apply
```

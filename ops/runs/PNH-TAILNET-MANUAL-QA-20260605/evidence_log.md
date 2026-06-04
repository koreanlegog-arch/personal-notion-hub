# Evidence Log: PNH Tailnet Manual Phone QA

Date: 2026-06-05

## Pre-Submission State

Command:

```bash
python3 scripts/sensitive_owner_readiness_check.py
```

Result:

- `verdict=ready_for_sensitive_local_owner_mode`
- `encryptedVaultRows=7`
- `plaintextInboxRows=0`
- `privateOrSecretValuePrinted=false`

## Manual Phone Submission

Path:

`phone browser -> Tailscale tailnet HTTP fallback -> Windows portproxy -> WSL loopback companion -> encrypted vault`

The pairing code and browser session token were not recorded.

## Post-Submission State

Commands:

```bash
python3 scripts/sensitive_owner_readiness_check.py
python3 scripts/private_inbox_status.py --limit 5
```

Result:

- `encryptedVaultRows=8`
- `privateInboxTotalCaptures=8`
- `plaintextInboxRows=0`
- latest recent capture had `encrypted=true`
- latest recent capture had `storageMode=encrypted-vault`
- latest recent capture title was redacted as `[encrypted]`
- `privateValuesPrinted=false`

## Follow-Up Automation

Added:

- `scripts/start_tailnet_session.sh`
- `scripts/stop_tailnet_session.sh`

These scripts avoid writing secrets and keep pairing code output local to the companion terminal.

## Cleanup And Script Validation

Commands:

```bash
bash -n scripts/start_tailnet_session.sh scripts/stop_tailnet_session.sh
bash scripts/stop_tailnet_session.sh
python3 scripts/smoke_check.py
python3 scripts/sensitive_owner_readiness_check.py
```

Result:

- shell syntax check passed
- `tailnet_session_forwarding_removed=true`
- `remaining_portproxy_output_present=false`
- `smoke_check_pass=true`
- `verdict=ready_for_sensitive_local_owner_mode`
- `encryptedVaultRows=8`
- `privateOrSecretValuePrinted=false`

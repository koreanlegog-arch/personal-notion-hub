# PNH Phone Automation Rehearsal Evidence

Date: 2026-06-06

## Goal

Run a synthetic phone automation request through the same companion endpoint
that an owner phone automation tool will use, and verify encrypted-vault ingress
without exposing token values, private payload values, or exact tailnet URLs.

## Work Mode

- mode: `normal-harness`
- reason: this was a focused backend automation slice. The supervisor-agent
  integrated the sender, fixture smoke, live loopback rehearsal, owner-tailnet
  rehearsal, privacy gate, and documentation updates.

## Efficiency Notes

- specialist fit: high
  - `local-private-data-ingress` matched phone adapter, token, tailnet, and
    encrypted vault safety requirements.
  - `automation-delivery` matched reusable rehearsal script, smoke check, and
    evidence recording.
- parallel value: medium
  - smoke, live rehearsal, privacy gate, and full smoke were run independently
    where safe.
- rework observed: low
  - no failed smoke after implementation.
- evidence quality: high
  - fixture smoke verifies actual POST without leaking the synthetic token.
  - loopback rehearsal verified an encrypted-vault row increment.
  - owner-tailnet rehearsal verified the owner-network path and persisted no
    exact tailnet URL.

## Results

- loopback rehearsal: success
- owner-tailnet rehearsal: success
- latest rehearsal adapter: `phone-call-log-json`
- latest base URL mode: `owner_tailnet`
- latest records accepted: `1`
- latest inbox count delta: `1`
- private values printed: `false`
- token values printed: `false`
- base URL value printed: `false`

## Verification Commands

```bash
python3 scripts/pnh_phone_automation_rehearsal_smoke_check.py
python3 scripts/pnh_phone_automation_setup_readiness.py
python3 scripts/pnh_phone_automation_rehearsal.py
python3 scripts/pnh_phone_automation_rehearsal.py --use-tailnet
python3 scripts/private_inbox_status.py --include-recent
python3 scripts/pnh_real_data_privacy_gate.py
python3 scripts/smoke_check.py
git diff --check
```

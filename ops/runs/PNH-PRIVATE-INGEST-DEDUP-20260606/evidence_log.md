# PNH Private Ingest Dedup Evidence

Date: 2026-06-06

## Work Mode

- Mode: `normal-harness`
- Reason: Supervisor integrated the storage change while dedicated private-ingress and automation smoke checks covered direct insert, adapter import, and phone endpoint behavior.
- Efficiency note: The work benefited from specialist validation because the risk was not broad architecture, but repeated private-data ingestion across multiple entry points.

## Scope

- Add opt-in private ingest fingerprint deduplication.
- Apply dedup to real-data adapter import, guarded live adapter apply, and authenticated phone automation adapter writes.
- Preserve normal manual/mobile capture behavior unless the caller opts into deduplication.
- Keep private values, token values, and exact owner-network values out of stdout and evidence.

## Commands

- `python3 scripts/pnh_private_ingest_dedup_smoke_check.py`
- `python3 scripts/private_inbox_smoke_check.py`
- `python3 scripts/pnh_private_data_adapter_import_smoke_check.py`
- `python3 scripts/pnh_live_private_data_adapter_sync_smoke_check.py`
- `python3 scripts/phone_adapter_ingress_smoke_check.py`
- `python3 scripts/pnh_phone_adapter_send_smoke_check.py`
- `python3 scripts/pnh_phone_automation_rehearsal_smoke_check.py`
- `python3 scripts/pnh_real_data_privacy_gate.py`
- `python3 scripts/private_inbox_status.py`
- `python3 scripts/smoke_check.py`
- `git diff --check`

## Results

- Direct encrypted private-store duplicate insert skipped.
- Repeated local private data adapter import skipped duplicate input.
- Repeated guarded live adapter apply skipped duplicate input.
- Repeated phone automation payload skipped duplicate input.
- Existing authenticated private inbox behavior still passed.
- Existing local private data adapter smoke still passed.
- Existing phone adapter send smoke still passed.
- Phone adapter ingress and automation rehearsal smoke passed.
- Real data privacy gate verdict: `ready_for_controlled_real_phone_adapter_run`.
- Current private inbox remains `17` encrypted-vault rows and `0` plaintext rows.
- Full static smoke check passed.
- Git whitespace check passed.
- Private values printed: `false`.
- Token values printed: `false`.
- Raw private body read: `false`.

## Residual Risk

- Fingerprint dedup is an ingestion-stability mechanism, not a cryptographic
  privacy boundary. It reduces repeat writes for identical normalized private
  records inside the local encrypted-vault workflow.

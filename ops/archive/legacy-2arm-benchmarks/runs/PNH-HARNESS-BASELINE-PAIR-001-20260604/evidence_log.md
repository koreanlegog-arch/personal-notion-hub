# Evidence Log: Harness Baseline Pair 001

## Run Metadata

- pair_id: `PNH-BASELINE-PAIR-001`
- reasoning_effort: `medium`
- reasoning_policy: `fixed-baseline`
- project: `Personal_Notion_Hub`
- date: `2026-06-04`
- evidence policy: synthetic data only; no private value, token, passphrase, session, or pairing code recorded

## Timing

| arm | start_epoch | end_epoch | wall_clock_minutes | note |
| --- | ---: | ---: | ---: | --- |
| supervisor-only | 1780561492 | 1780561571 | 1.32 | exact epoch captured before and after direct arm |
| harness-run | 1780561492 | 1780561726 | 3.90 | start approximated from worker spawn window; end captured after integration/regression |

## Supervisor-Only Evidence

Changed files:

- `scripts/encrypted_vault_metadata_audit.py`
- `scripts/encrypted_vault_metadata_audit_smoke_check.py`

Commands:

```bash
python3 -m py_compile scripts/encrypted_vault_metadata_audit.py scripts/encrypted_vault_metadata_audit_smoke_check.py
python3 scripts/encrypted_vault_metadata_audit_smoke_check.py
```

Result:

```text
encrypted_vault_metadata_audit_smoke_check_pass=true
private_values_printed=false
db_mutated=false
```

Metrics:

- rework_count: `0`
- defect_count: `0`
- verification_depth_score: `2`
- supervisor_direct_implementation_ratio: `1.0`

## Harness-Run Evidence

Changed files:

- `scripts/encrypted_backup_envelope_audit.py`
- `scripts/encrypted_backup_envelope_audit_smoke_check.py`

Worker reported commands:

```bash
python3 -m py_compile scripts/encrypted_backup_envelope_audit.py scripts/encrypted_backup_envelope_audit_smoke_check.py
python3 scripts/encrypted_backup_envelope_audit_smoke_check.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/encrypted_backup_envelope_audit_smoke_check.py
find scripts -path '*/__pycache__/*encrypted_backup_envelope_audit*' -print
```

Supervisor integration commands:

```bash
python3 -m py_compile scripts/encrypted_backup_envelope_audit.py scripts/encrypted_backup_envelope_audit_smoke_check.py scripts/encrypted_vault_metadata_audit.py scripts/encrypted_vault_metadata_audit_smoke_check.py
python3 scripts/encrypted_backup_envelope_audit_smoke_check.py
python3 scripts/encrypted_vault_metadata_audit_smoke_check.py
```

Result:

```text
encrypted_backup_envelope_audit_smoke_check_pass=true
secret_value_printed=false
plaintext_found_in_backup=false
unsupported_algorithm_detected=true
```

Sidecar evidence:

- reviewer checklist: no passphrase CLI, no `decrypt_backup_payload`, no private value output, fail-on-unsupported required.
- QA matrix: normal envelope audit, forbidden value scan, unsupported schema/kind/crypto headers, malformed envelope, regression bundle.

Metrics:

- rework_count: `0`
- defect_count: `0`
- verification_depth_score: `2`
- supervisor_direct_implementation_ratio: `0.30`

## Regression Bundle

```bash
python3 scripts/encrypted_vault_backup_restore_smoke_check.py
python3 scripts/encrypted_vault_smoke_check.py
python3 scripts/encrypted_vault_delete_smoke_check.py
python3 scripts/plaintext_migration_audit_smoke_check.py
python3 scripts/private_inbox_smoke_check.py
python3 scripts/browser_bridge_smoke_check.py
python3 scripts/companion_smoke_check.py
python3 scripts/smoke_check.py
git diff --check
```

Result: pass.

## Initial Interpretation

This single pair does not establish a policy. It suggests that harness-run reduced supervisor direct implementation ratio, but had higher wall-clock overhead for this small-medium script task. More pairs in the same band are required before changing defaults.

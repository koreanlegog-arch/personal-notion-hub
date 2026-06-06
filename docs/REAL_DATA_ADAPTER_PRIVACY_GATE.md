# Real Data Adapter Privacy Gate

## Status

Required before any real phone, calendar, contact, call, recording, Notion, or external account adapter is connected.

## Default Decision

Live external real-data adapters are disabled until all gates below are
satisfied with fixture-only evidence. The owner-exported local import adapters
are available as a rough MVP when they write only to the approved local
encrypted vault and do not contact phone APIs, cloud accounts, OAuth providers,
or external services.

Current controlled phone-adapter readiness is verified by:

```bash
python3 scripts/pnh_real_data_privacy_gate.py
```

The gate checks encrypted vault mode, zero plaintext rows, companion service
health, scheduler timer health, owner-tailnet availability, and no token/private
value output. It does not read raw private bodies.

## Gates

| Gate | Requirement |
| --- | --- |
| Scope | Adapter purpose, data source, data types, and retention are documented. |
| Consent | Data subject and legal/consent notes are recorded without private values. |
| Storage | Sensitive outputs use approved local encrypted vault only. |
| Credentials | Tokens and API keys are stored through approved secret workflow only. |
| Redaction | UI, screenshots, logs, reports, and browser QA use redacted or synthetic values. |
| External Services | Any cloud or third-party transfer requires separate approval. |
| Backup/Rollback | Backup, delete, rollback, and failure cleanup are defined. |
| QA | `ops/checklists/PRIVATE_DATA_ADAPTER_QA_CHECKLIST.md` is complete. |
| Security | `ops/templates/PRIVATE_DATA_ADAPTER_SECURITY_GATE_TEMPLATE.md` is approved. |

## Adapter Approval Packet

Use:

- `ops/templates/PRIVATE_DATA_ADAPTER_BRIEF_TEMPLATE.md`
- `ops/templates/PRIVATE_DATA_ADAPTER_SECURITY_GATE_TEMPLATE.md`
- `ops/checklists/PRIVATE_DATA_ADAPTER_QA_CHECKLIST.md`

## Stop Conditions

Stop before real-data execution if any of these occur:

- credential handling is unclear
- private values appear in logs or evidence
- storage path is outside encrypted vault boundary
- rollback plan is untested
- external service transfer is not approved
- screenshot redaction is not validated

## Verdict

Real-data adapter readiness is `Ready for local import MVP` for owner-exported
CSV/ICS/TXT/JSON files that use the approved local encrypted vault.

Controlled owner phone-adapter POST runs are `Ready for controlled owner run`
when `scripts/pnh_real_data_privacy_gate.py` returns
`ready_for_controlled_real_phone_adapter_run`.

Native phone/cloud API readiness remains `Blocked` by default until a concrete
adapter, credential source, storage scope, and live execution scope are
configured and validated.

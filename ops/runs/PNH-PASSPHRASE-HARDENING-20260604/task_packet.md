# PNH-PASSPHRASE-HARDENING-20260604 Task Packet

## Objective

Harden Personal Notion Hub encrypted vault passphrase handling before routine sensitive local testing.

## Scope

- Add no-echo prompt support for vault and backup passphrases.
- Preserve existing environment-variable passphrase mode for non-interactive local runs.
- Add keychain readiness reporting without storing or printing secrets.
- Update docs and smoke checks to reflect the implemented boundary.

## Out Of Scope

- Actual OS keychain storage/retrieval.
- Passphrase recovery or rotation.
- New dependencies or package manager changes.
- Real private data, phone adapters, cloud sync, or non-loopback access.

## Acceptance Criteria

- Prompt options are available for init, server, backup, restore, delete, and decrypted status inspection.
- Prompt confirmation rejects mismatched values where a new passphrase is being set.
- Short or missing passphrases fail closed.
- Secret values are not printed by scripts or evidence.
- Existing env-var smoke flows continue to pass.
- Documentation distinguishes implemented prompt hardening from future OS keychain work.

## Risk

Medium. This touches encrypted vault startup and lifecycle scripts, but does not change encryption format or persisted data schema.

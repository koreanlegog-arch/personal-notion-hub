# Security Gate

## Risk Summary

Sensitive owner mode is not ready yet.

Confirmed blockers:

- The local private inbox currently contains plaintext rows.
- Phone ingress is still blocked because no phone-reachable private Windows LAN IP is available.

## Secret Exposure Assessment

- No secret value was requested from the supervisor.
- Readiness and smoke commands report only capability flags, counts, and redacted metadata.
- The new readiness check reports `secretValuePrinted=false`.

## Data Flow Risk

The current local data store has a transitional plaintext inbox path. Routine
high-sensitivity input must use encrypted vault mode and should not proceed
while plaintext inbox rows remain unresolved.

## Required Mitigations

1. Create an encrypted backup before any plaintext migration apply.
2. Migrate or delete plaintext inbox rows.
3. Re-run readiness and smoke checks.
4. Use encrypted vault mode for future sensitive local capture.

## Approval Gates

- Real passphrase entry is local operator action only; do not paste it into chat.
- Plaintext migration apply requires backup and confirmation phrase.
- Deleting existing local rows requires explicit operator intent.
- Phone ingress requires a private LAN reachability pass.

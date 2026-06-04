# Private Data Adapter Brief Template

## Adapter Summary

- Adapter Name:
- Owner:
- Requested Date:
- Data Source:
- Intended Use:
- Expected Users:

## Data Scope

- Data Types:
- Example Fixture Shape:
- Real Data Required?: No / Yes with approval
- Collection Frequency:
- Retention Target:
- Deletion Requirement:

## Sensitivity And Consent

- Sensitivity Classification:
- Personal Data Included?: No / Yes
- Third-Party Data Included?: No / Yes
- Consent Requirement:
- Legal/Policy Notes:

## Storage And Security

- Storage Mode: encrypted vault / browser demo / disabled
- Encryption Requirement:
- Passphrase/Key Handling:
- OS Keychain Requirement:
- Backup Requirement:
- Redaction Requirement:

## Integration Boundary

- Local-Only?: Yes / No
- External Services:
- Network Access:
- Credentials Required:
- Logs Prohibited From Containing:

## Acceptance Criteria

- [ ] Fixture-only adapter test passes.
- [ ] No real private data appears in repository files.
- [ ] No secret or private value appears in logs/evidence.
- [ ] Encrypted vault path is verified if sensitive data is used.
- [ ] Redacted browser QA path is defined if UI displays adapter output.

## Approval Gates

- Supervisor approval required before real data use.
- Security review required before credential or token use.
- Release-readiness review required before distribution.

## Residual Risks

- Risk:
- Mitigation:
- Accepted By:

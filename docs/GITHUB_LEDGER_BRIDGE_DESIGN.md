# GitHub Ledger Bridge Design

Status: design + dry-run implementation ready
Date: 2026-06-05

## Purpose

`Personal_Notion_Hub` should turn a mobile command packet into a durable task ledger entry before Discord/OpenClaw dispatch.

The first ledger target is GitHub Issues. GitHub Projects integration remains a later phase because it requires additional project identifiers, GraphQL mutations, and broader permission review.

## Recommended Flow

```text
PNH mobile Launch input
-> local companion encrypted vault
-> local command packet metadata
-> GitHub issue draft
-> approved external issue creation
-> future Discord/OpenClaw dispatch reads the issue/task reference
```

## Scope

In scope for the current phase:

- Generate GitHub Issue payloads from a PNH command packet.
- Keep dry-run as the default behavior.
- Avoid printing or sending private packet values by default.
- Require explicit apply flags before GitHub mutation.
- Record evidence without token values.

Out of scope for the current phase:

- GitHub Projects item mutation.
- Discord/OpenClaw dispatch.
- Token creation, token storage, or credential rotation.
- Cloud sync of private packet bodies.
- Automatic issue creation from the encrypted vault without supervisor approval.

## Data Handling

Default issue payloads are privacy-preserving:

- Title uses command type and local packet reference, not the raw private title.
- Body records metadata, acceptance criteria shell, and local vault reference.
- Raw command body is not included.
- Secret values, browser session tokens, and pairing codes are never included.

Sensitive fields may only be sent to GitHub after a separate supervisor approval confirming the target repository privacy, token scope, and acceptable data exposure.

## Token And Permission Requirements

GitHub Issue creation requires a GitHub token with access to the target repository and Issues write permission. Fine-grained personal access tokens should be scoped to only the target repository and Issues read/write where possible.

The token must be provided at runtime through an environment variable such as `GITHUB_TOKEN`. It must not be committed, printed, or stored in this repository.

## Apply Gate

Dry-run is allowed inside the current approval boundary.

Live issue creation requires all of:

- Supervisor approval for external GitHub mutation.
- Target repository confirmed.
- `GITHUB_TOKEN` present in the local environment.
- `--apply` flag.
- `--approve-external-write` flag.
- No private body inclusion unless separately approved.

## Failure Handling

- Missing token in dry-run: allowed.
- Missing token in apply mode: fail closed.
- HTTP error from GitHub: print status and redacted error body only.
- Private body request without explicit sensitive-data approval: fail closed.
- Duplicate prevention is not implemented yet; use dry-run and issue title review until a dedupe strategy is approved.

## Future Projects Integration

GitHub Projects may be added later after:

- Project owner/type is confirmed.
- Project ID or number is identified.
- Field mapping is defined.
- GraphQL mutation permission is reviewed.
- Dry-run preview is implemented.

## Next Approval Gate

The next material approval gate is live GitHub issue creation.

Recommended approval phrase:

```text
APPROVE_PNH_GITHUB_ISSUE_LEDGER_APPLY
```

After that approval, the implementation may run the bridge in apply mode against the approved repository using a local environment token.

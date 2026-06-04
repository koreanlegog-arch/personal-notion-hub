# Security Preflight

## Constraints

- Do not store real secrets.
- Do not request secret values from the supervisor.
- Do not print passphrase values.
- Do not implement backend storage before explicit approval.
- Do not use `cmdkey /pass:` because the secret can be exposed through command-line arguments.
- Do not install keyring packages without dependency approval.

## Backend Boundary

Recommended next candidate is `windows-dpapi-file`, not `cmdkey` and not Linux Secret Service in this WSL session.

Reason:

- Windows PowerShell and DPAPI are available on the host side.
- Current WSL does not expose a ready Linux Secret Service backend.
- DPAPI protected files can avoid command-line secret arguments if implemented through stdin and strict output policy.

## Approval Gate

Implementation requires:

```text
APPROVE_PNH_WINDOWS_DPAPI_FILE_BACKEND
```

No actual backend storage should be added before that approval phrase.

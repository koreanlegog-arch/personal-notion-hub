# Acceptance Matrix

| Requirement | Evidence |
| --- | --- |
| Design document exists | `docs/PASSPHRASE_KEYCHAIN_BACKEND_DESIGN.md` |
| Recommended backend is explicit | `windows-dpapi-file` in design document |
| No actual backend implementation added | no new secret backend code in this run |
| Dangerous `cmdkey /pass:` path rejected | design and security preflight |
| Approval phrase documented | `APPROVE_PNH_WINDOWS_DPAPI_FILE_BACKEND` |
| Validation plan uses synthetic secrets only | design document |
| Existing smoke checks still pass | evidence log |

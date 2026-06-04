# Release Readiness

Date: 2026-06-04

## Verdict

Ready for local MVP use.

## Scope Covered

- Local companion private inbox MVP.
- Synthetic mobile capture ingress.
- Workspace-local SQLite persistence.
- Security and QA documentation.

## Acceptance Criteria Status

- Loopback-only bind: pass.
- Missing/wrong auth rejection: pass.
- Authorized synthetic capture write: pass.
- Metadata-only response: pass.
- Redacted status output: pass.
- Fixture preview no-write contract: pass.
- Private inbox ignored by Git: pass.

## Validation Evidence

Commands executed:

```bash
python3 scripts/smoke_check.py
python3 scripts/companion_smoke_check.py
python3 scripts/private_inbox_smoke_check.py
python3 -m py_compile companion/server.py companion/preview.py companion/private_store.py scripts/smoke_check.py scripts/companion_smoke_check.py scripts/private_inbox_init.py scripts/simulate_mobile_capture.py scripts/private_inbox_status.py scripts/private_inbox_smoke_check.py
python3 scripts/private_inbox_init.py
python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox
python3 scripts/simulate_mobile_capture.py --title "<redacted synthetic title>" --body "<redacted synthetic body>" --sensitivity private
curl -s http://127.0.0.1:8765/api/health
python3 scripts/private_inbox_status.py
git status --ignored --short companion/private
find companion/private -maxdepth 2 -type f -printf '%p %s\n'
chmod 0644 companion/private/auth_token && python3 scripts/private_inbox_init.py && stat -c '%a' companion/private/auth_token
python3 scripts/private_inbox_init.py --db /tmp/pnh_should_not_create.sqlite
python3 scripts/simulate_mobile_capture.py --base-url https://example.com
python3 scripts/private_inbox_status.py --db companion/private/nonexistent-status.sqlite
curl -s -H "Authorization: Bearer <redacted token>" http://127.0.0.1:8765/api/private/mobile-captures?limit=abc
curl -s -H "Authorization: Bearer <redacted token>" http://127.0.0.1:8765/api/private/summary
node --check assets/js/app.js
node --check assets/js/assistant-storage.js
node --check assets/js/assistant-import.js
node --check assets/js/assistant-rules.js
python3 -m json.tool data/seed.json
git diff --check
```

Results:

- Static smoke check: pass.
- Fixture companion smoke check: pass.
- Private inbox smoke check: pass.
- Python compile check: pass.
- JavaScript syntax checks: pass.
- Seed JSON parse: pass.
- Diff whitespace check: pass.
- Actual local private inbox init: pass.
- Actual local companion private mode: pass.
- Actual synthetic mobile capture: HTTP 201, metadata-only response.
- Actual private inbox status: `totalCaptures>=1`, redacted recent title, no body printed.
- Git ignore check: `companion/private/` is ignored.
- Synthetic title/body values are intentionally redacted in this evidence file.
- Existing auth token permission repair: pass, final mode `600`.
- External DB path override rejection: pass.
- External/non-loopback capture URL rejection: pass.
- Status command missing DB no-create behavior: pass.
- Invalid list `limit` returns client error instead of storage failure: pass.
- HTTP summary omits DB path while CLI status shows repo-relative path only: pass.
- Server-running HTTP summary and independent CLI status agreed on capture count after journal mode update.

## Security Status

Pass for local MVP boundary.

No token value was printed. API/status outputs did not print raw capture body. Private files were created only under ignored `companion/private/`.

## Documentation Status

Updated:

- `README.md`
- `companion/README.md`
- `docs/LOCAL_COMPANION_ARCHITECTURE.md`
- `docs/PRIVATE_DATA_POLICY.md`
- `docs/SECURITY_NOTES.md`
- `docs/TEST_PLAN.md`
- `docs/RELEASE_NOTES.md`

## Rollback Plan

Revert the tracked commit. Ignored local `companion/private/` may be kept for local use or manually removed by the supervisor if the stored private test data is no longer needed.

## Known Risks

- No encryption-at-rest yet.
- No browser pairing/CORS yet.
- No phone-native adapter yet.
- SQLite private inbox is local-only and tied to this workspace.

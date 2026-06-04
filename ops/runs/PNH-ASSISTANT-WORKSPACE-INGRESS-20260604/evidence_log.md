# Evidence Log

## Commands Run

This file is updated after validation.

| Command | Result |
| --- | --- |
| `python3 -m py_compile scripts/browser_bridge_smoke_check.py scripts/redacted_browser_qa_check.py scripts/smoke_check.py` | pass |
| `python3 scripts/smoke_check.py` | pass |
| `python3 scripts/redacted_browser_qa_check.py` | pass: `real_private_values_used=false` |
| `python3 scripts/browser_bridge_smoke_check.py` | pass: launch-style and assistant-style synthetic captures stored, no token/session/private response values printed |
| `python3 scripts/private_inbox_smoke_check.py` | pass: `token_value_printed=false`, `private_response_values_printed=false` |
| `python3 scripts/companion_smoke_check.py` | pass |
| `git ls-files companion/private encrypted_exports exports` | pass: no tracked private/generated artifacts listed |
| `git diff --check` | pass |
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `71.7`, band `useful`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION` |

## Evidence Notes

- Automated validation used synthetic values only.
- Assistant ingress reuses the existing paired loopback browser bridge.
- No real mobile, phone, contact, call, recording, calendar, or client data was used.

## Residual Risk

- Manual browser UI check is still recommended before using the flow interactively.

# Evidence Log

## Commands Run

This file is updated after validation.

| Command | Result |
| --- | --- |
| `npx --no-install playwright --version` | pass: Playwright CLI available |
| `npx playwright install chromium` | pass: Chromium, Chromium headless shell, and FFmpeg downloaded to local Playwright cache |
| `npx playwright install-deps chromium --dry-run` | blocked: 39 missing OS packages reported |
| `npx playwright install-deps chromium` | blocked: sudo password requires an interactive user terminal; Codex did not receive or request the password |
| `sudo -n true` | blocked: non-interactive sudo unavailable |
| supervisor-ran `npx playwright install-deps chromium` in interactive WSL terminal | pass: OS dependencies installed |
| `bash scripts/run_playwright_redacted_ui_qa.sh` | pass: 2 Playwright tests passed, redacted screenshot artifact generated under ignored `artifacts/` |
| `python3 scripts/redacted_browser_qa_check.py` | pass |
| `python3 scripts/smoke_check.py` | pass |
| `git check-ignore -v ops/runs/PNH-REDACTED-BROWSER-QA-20260604/artifacts/http-server.log ops/runs/PNH-REDACTED-BROWSER-QA-20260604/artifacts/playwright-output/.last-run.json` | pass: generated browser QA artifacts ignored |
| `git diff --check` | pass |
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `67.8`, band `partial`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION` |

## Manual QA

- Supervisor confirmed the real browser Assistant/workspace ingress flow worked.
- No secret, pairing code, token, passphrase, screenshot, or real private value was recorded.

## Residual Risk

- Repeatable Playwright screenshot validation now passes in this WSL runtime.
- Generated artifact paths are ignored by Git, but any future screenshots must still use synthetic/redacted content only.

# Security Preflight

## Constraints

- Do not use real private data in browser QA.
- Do not commit screenshots, traces, videos, or browser output artifacts.
- Do not paste pairing codes, session tokens, or passphrases into evidence.
- Do not install Playwright browsers without supervisor approval.

## Controls

- Playwright test uses a synthetic marker string only.
- Screenshot is taken only after `body.screenshot-redaction` is active.
- Test checks `data-sensitive="true"` masking styles.
- Test checks localStorage/sessionStorage for token material.
- `ops/runs/*/artifacts/` is ignored by Git.
- Runner exits with explicit blocked output when Chromium is unavailable.

## Residual Risks

- Current environment now has the required Playwright Chromium system dependencies.
- The supervisor's manual browser confirmation is backed by repeatable synthetic/redacted Playwright screenshot QA.

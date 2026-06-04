# Evidence Log

## Run

- run_id: `PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604`
- scope: mobile-like stdin/file companion ingress
- real_sensitive_data_used: no
- token_values_printed: no
- external_calls: no

## Sidecar Evidence

### Repo Explorer

- model tier: economy
- reasoning effort: low
- result used: identified the existing safe path as `simulate_mobile_capture.py -> companion/server.py -> private_store.py`.
- result used: recommended stdin/prompt script input instead of browser fetch because browser pairing/CORS was larger and gated.

### Security Preflight

- model tier: frontier
- reasoning effort: high
- result used: browser UI fetch/CORS/pairing is out of scope until separately approved.
- result used: synthetic-only payloads, no token values, no DB dumps, no screenshots with body text.
- result used: preserve loopback-only base URL and ignored `companion/private/`.

## Files Changed

- `scripts/simulate_mobile_capture.py`
- `scripts/private_inbox_smoke_check.py`
- `README.md`
- `docs/TEST_PLAN.md`
- `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/task_packet.md`
- `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/command_packet.md`
- `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/security_preflight.md`
- `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/reports/harness_score.json`
- `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/reports/harness_score.md`

## Commands Run

```bash
python3 -m py_compile companion/server.py companion/private_store.py scripts/private_inbox_smoke_check.py scripts/simulate_mobile_capture.py scripts/smoke_check.py
```

- result: pass

```bash
python3 scripts/private_inbox_smoke_check.py
```

- result: pass
- important output:
  - `private_inbox_smoke_check_pass=true`
  - `token_value_printed=false`
  - `private_response_values_printed=false`

```bash
python3 scripts/smoke_check.py
```

- result: pass
- important output:
  - `smoke_check_pass=true`

```bash
python3 scripts/simulate_mobile_capture.py --help
```

- result: pass
- important output:
  - `--body-file BODY_FILE`
  - `Read capture body from a UTF-8 file, or '-' for stdin.`

```bash
printf 'Synthetic body' | python3 scripts/simulate_mobile_capture.py --base-url http://example.com:8765 --body-file -
```

- result: expected failure with exit code `2`
- important output:
  - `mobile_capture_sent=false error=base-url must target 127.0.0.1`
- note: this validates loopback guard before token read.

```bash
git ls-files companion/private
```

- result: no tracked files printed

```bash
git check-ignore -v companion/private/auth_token companion/private/pnh_private_inbox.sqlite
```

- result: pass
- important output:
  - `.gitignore:18:companion/private/ companion/private/auth_token`
  - `.gitignore:18:companion/private/ companion/private/pnh_private_inbox.sqlite`

```bash
git diff --check
```

- result: pass

```bash
python3 scripts/harness_score_run.py --score-model efficiency --run-id PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604 --root Personal_Notion_Hub/ops/runs ... --write
```

- result: pass
- efficiency score: `60.1`
- classification: `single-agent-or-partial-harness`

## Acceptance Criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| stdin/file body input works | pass | `private_inbox_smoke_check.py` file-input validation and `--help` output |
| loopback endpoint restrictions remain enforced | pass | expected failure for `http://example.com:8765` |
| token is not printed | pass | smoke output `token_value_printed=false` |
| private response values are not printed | pass | smoke output `private_response_values_printed=false` |
| ignored private storage remains untracked | pass | `git ls-files companion/private` no output, `git check-ignore` pass |
| static smoke still passes | pass | `smoke_check_pass=true` |
| browser fetch remains out of scope | pass | no browser `fetch` added; static smoke still forbids `fetch(` |

## Efficiency Measurement Notes

Directly observed:

- sidecar findings changed scope before risky implementation.
- one bounded implementation slice was completed.
- one replan happened because security sidecar blocked browser fetch scope.
- no write-set conflict or duplicated implementation work occurred.
- evidence completeness is high for local checks.

Estimated only:

- critical-path reduction is not an A/B fact. It is estimated from avoided browser CORS/pairing work and avoided security rework.
- elapsed-time speedup is not claimed.

Measurement limit:

- To prove real speedup, the same task class must be compared against either a historical non-harness baseline with recorded duration or a controlled A/B rehearsal.

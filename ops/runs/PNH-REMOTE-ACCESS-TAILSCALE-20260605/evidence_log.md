# Evidence Log: PNH Remote Access via Tailscale

Date: 2026-06-05

## External Documentation Checked

- Tailscale WSL guidance: https://tailscale.com/kb/1295/install-windows-wsl2
- Tailscale Serve documentation: https://tailscale.com/kb/1312/serve
- Tailscale Serve use cases: https://tailscale.com/kb/1247/funnel-serve-use-cases

## Environment Evidence

- Tailscale installed on Windows host with `winget`.
- Tailscale backend status: running.
- Windows node and Android phone peer were visible in the same tailnet.
- Tailscale HTTPS certificate check failed because the account does not support Tailscale TLS certificates.
- Exact tailnet DNS, IP, email, pairing code, session token, and private values are intentionally omitted.

## Commands Run

```bash
python3 -m py_compile companion/server.py scripts/tailnet_ingress_smoke_check.py scripts/smoke_check.py
python3 scripts/tailnet_ingress_smoke_check.py
python3 scripts/browser_bridge_smoke_check.py
python3 scripts/phone_ingress_smoke_check.py
python3 scripts/sensitive_owner_readiness_check.py
python3 scripts/smoke_check.py
python3 scripts/redacted_browser_qa_check.py
bash scripts/run_playwright_redacted_ui_qa.sh
git diff --check
```

Result: passed.

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" status --json
& "C:\Program Files\Tailscale\tailscale.exe" serve status --json
& "C:\Program Files\Tailscale\tailscale.exe" version
& "C:\Program Files\Tailscale\tailscale.exe" cert <WINDOWS_TAILNET_DNS>
```

Result: Tailscale running. Serve config initially empty. HTTPS certificate check failed due account capability.

```bash
python3 <tailnet-portproxy-rehearsal-script>
```

Result:

- `tailscale_backend=running`
- `tailnet_ip_detected=true`
- `portproxy_added=true`
- `firewall_rule_added=true`
- `tailnet_http_root=true`
- `tailnet_http_health=true`
- `tailnet_http_pair=true`
- `tailnet_http_capture=true`
- `private_values_printed=false`
- `cleanup_done=true`

## Secret Pattern Scan

Command:

```bash
rg -n --hidden --glob '!companion/private/**' --glob '!.git/**' --glob '!node_modules/**' --glob '!playwright-report/**' --glob '!test-results/**' "(DISCORD_BOT_TOKEN|TELEGRAM_BOT_TOKEN|OPENAI_API_KEY|ghp_|github_pat_|BEGIN (RSA|OPENSSH|PRIVATE) KEY|TAILNET_PORTPROXY_REHEARSAL_SYNTHETIC_BODY_DO_NOT_LOG|browser_pairing_code=|X-PNH-Browser-Session:|Authorization: Bearer [A-Za-z0-9_-])" .
```

Result: no committed secret value found. Matches were known fixture/source-code false positives:

- masked private-key fixture in a smoke test
- source code that prints a short-lived local pairing code at runtime
- older evidence log command text

## Notes

The rehearsal used synthetic capture data only. A new encrypted vault row was written as evidence of end-to-end capture. The response body did not include the synthetic private body value.

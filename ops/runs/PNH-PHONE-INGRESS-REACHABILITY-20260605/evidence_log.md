# Evidence Log

## Commands Run

| Command | Result |
| --- | --- |
| `hostname -I` / `ip -4 addr show` | WSL IP is `172.31.155.144`; this is WSL internal NAT. |
| `ss -ltnp | rg ':8765'` | companion is listening in WSL on `0.0.0.0:8765`. |
| Windows `Invoke-WebRequest http://127.0.0.1:8765/api/health` | pass: `200`. |
| Windows `Invoke-WebRequest http://220.126.9.129:8765/api/health` | blocked. |
| Windows `Test-NetConnection 220.126.9.129 -Port 8765` | `TcpTestSucceeded=false`. |
| `netsh interface portproxy show v4tov4` | no rules present. |
| `python3 scripts/phone_ingress_reachability_check.py` | verdict: `blocked_no_phone_reachable_private_windows_lan_ip`. |
| `python3 scripts/phone_ingress_lan_info.py` | pass: `candidateLanIps=[]`, WSL NAT IP listed only as not phone-reachable by default. |
| `python3 scripts/smoke_check.py` | pass. |
| `git diff --check` | pass. |
| `python3 -m py_compile scripts/phone_ingress_reachability_check.py scripts/phone_ingress_smoke_check.py scripts/smoke_check.py` | pass. |
| `python3 -m py_compile scripts/phone_ingress_lan_info.py scripts/phone_ingress_reachability_check.py scripts/phone_ingress_smoke_check.py scripts/smoke_check.py` | pass after LAN helper correction. |
| `bash scripts/run_playwright_redacted_ui_qa.sh` | pass: 2 Playwright Chromium tests passed with synthetic/redacted evidence. |
| `rg ... secret patterns ...` | pass: no matching token/private-key pattern found in the Phase 0 changed files. |

## Current Revalidation Note

After the earlier live companion diagnosis, a later validation run found the
companion no longer listening on port `8765`. That changes localhost health from
`200` to blocked, but it does not change the network verdict: `safePhoneUrls`
remains empty because no phone-reachable Windows private LAN IP exists.
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `65.7`, band `partial`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION`. |

## Network Findings

- `172.31.155.144` is the WSL app IP and is not directly reachable from the phone.
- `172.31.144.1` is Windows `vEthernet (WSL)` and is internal to the host.
- `220.126.9.129` is a public Windows interface IP and is rejected by phone ingress policy.
- No phone-reachable private Windows LAN IP was detected.

## Security Incident

A PowerShell quoting mistake caused an environment token value to appear in
terminal output. The value is not recorded in this file. The relevant Telegram
bot token should be rotated.

## Conclusion

Current state is not ready for same-LAN phone access. The next safe path is to
connect the PC and phone to a trusted private LAN that gives Windows a private
phone-reachable IP, then configure portproxy/firewall to that private IP.

## Evidence Completeness

- WSL listener confirmed.
- Windows localhost forwarding confirmed.
- Windows LAN/public interface reachability checked.
- Portproxy absence confirmed.
- Public exposure rejected.
- Private LAN next action documented.
- Harness score recorded with the token-output incident counted as a security penalty.
- LAN helper corrected so WSL NAT addresses are not presented as phone-ready candidates.

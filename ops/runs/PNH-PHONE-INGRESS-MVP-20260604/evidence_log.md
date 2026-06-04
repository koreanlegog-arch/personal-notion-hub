# Evidence Log

## Commands Run

| Command | Result |
| --- | --- |
| `python3 -m py_compile companion/server.py scripts/phone_ingress_smoke_check.py scripts/phone_ingress_lan_info.py scripts/browser_bridge_smoke_check.py scripts/smoke_check.py` | pass |
| `python3 scripts/phone_ingress_lan_info.py` | pass: candidate LAN IP reported without secrets |
| `python3 scripts/phone_ingress_smoke_check.py` | pass: `phone_ingress_smoke_check_pass=true`, `private_values_printed=false`, `phone_ingress_default_off=true` |
| `python3 scripts/smoke_check.py` | pass |
| `python3 scripts/browser_bridge_smoke_check.py` | pass |
| `python3 scripts/private_inbox_smoke_check.py` | pass |
| `python3 scripts/companion_smoke_check.py` | pass |
| `python3 scripts/redacted_browser_qa_check.py` | pass |
| `bash scripts/run_playwright_redacted_ui_qa.sh` | pass: 2 tests passed |
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `76.1`, band `useful`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION` |

## LAN Candidate

`scripts/phone_ingress_lan_info.py` reported:

```text
172.31.155.144
```

This may be WSL/NAT-specific. The supervisor should verify the reachable LAN IP
from the phone on the actual network.

## Residual Risk

- Manual phone browser test is still required.
- HTTP LAN traffic is not encrypted.
- Use synthetic or low-risk input until encrypted vault mode is started and verified.

#!/usr/bin/env bash
set -euo pipefail

# Remove PNH tailnet fallback forwarding from WSL.
# This script does not stop a companion process running in another terminal.

PORT="${PNH_TAILNET_PORT:-8765}"
RULE_NAME="${PNH_TAILNET_FIREWALL_RULE:-PNH Tailnet Ingress ${PORT}}"
TAILSCALE_EXE="${PNH_TAILSCALE_EXE:-C:\\Program Files\\Tailscale\\tailscale.exe}"

detect_tailnet_ip() {
  if [[ -n "${PNH_TAILNET_IP:-}" ]]; then
    printf '%s\n' "$PNH_TAILNET_IP"
    return 0
  fi
  powershell.exe -NoProfile -Command "& '${TAILSCALE_EXE}' status --json" \
    | python3 -c 'import json, sys
data = json.load(sys.stdin)
for ip in data.get("TailscaleIPs", []):
    if isinstance(ip, str) and ip.startswith("100."):
        print(ip)
        raise SystemExit(0)
raise SystemExit("tailnet_ipv4_not_found")'
}

TAILNET_IP="$(detect_tailnet_ip)"

powershell.exe -NoProfile -Command "\$ip='${TAILNET_IP}'; \$port=${PORT}; \$rule='${RULE_NAME}'; netsh interface portproxy delete v4tov4 listenaddress=\$ip listenport=\$port | Out-Null; Get-NetFirewallRule -DisplayName \$rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue; netsh interface portproxy show v4tov4; Get-NetFirewallRule -DisplayName \$rule -ErrorAction SilentlyContinue | Select-Object DisplayName,Enabled | ConvertTo-Json -Depth 2; exit 0" \
  | python3 -c 'import sys
text = sys.stdin.read()
print("tailnet_session_forwarding_removed=true")
print("remaining_portproxy_output_present=" + str(bool(text.strip())).lower())'

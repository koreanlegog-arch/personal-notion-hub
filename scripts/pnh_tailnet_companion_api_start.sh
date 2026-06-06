#!/usr/bin/env bash
set -euo pipefail

PORT="${PNH_TAILNET_PORT:-8765}"
RULE_NAME="${PNH_TAILNET_API_FIREWALL_RULE:-PNH Tailnet Companion API 8765}"
TAILSCALE_EXE="${PNH_TAILSCALE_EXE:-C:\\Program Files\\Tailscale\\tailscale.exe}"
APPLY="false"

if [[ "${1:-}" == "--apply" ]]; then
  APPLY="true"
fi

detect_tailnet_ip() {
  if [[ -n "${PNH_TAILNET_IP:-}" ]]; then
    printf '%s\n' "$PNH_TAILNET_IP"
    return 0
  fi
  powershell.exe -NoProfile -Command "& '${TAILSCALE_EXE}' status --json" \
    | python3 -c 'import json, sys
data = json.load(sys.stdin)
if data.get("BackendState") != "Running":
    raise SystemExit("tailscale_backend_not_running")
for ip in data.get("TailscaleIPs", []):
    if isinstance(ip, str) and ip.startswith("100."):
        print(ip)
        raise SystemExit(0)
raise SystemExit("tailnet_ipv4_not_found")'
}

TAILNET_IP="$(detect_tailnet_ip)"
TAILNET_URL="http://${TAILNET_IP}:${PORT}"

echo "# PNH Tailnet Companion API"
echo "tailnet_url=${TAILNET_URL}"
echo "service_expected=http://127.0.0.1:${PORT}/api/health"
echo "apply=${APPLY}"

if [[ "${APPLY}" != "true" ]]; then
  echo "mode=dry-run"
  exit 0
fi

powershell.exe -NoProfile -Command "\$ip='${TAILNET_IP}'; \$port=${PORT}; \$rule='${RULE_NAME}'; netsh interface portproxy delete v4tov4 listenaddress=\$ip listenport=\$port | Out-Null; Get-NetFirewallRule -DisplayName \$rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue; netsh interface portproxy add v4tov4 listenaddress=\$ip listenport=\$port connectaddress=127.0.0.1 connectport=\$port; New-NetFirewallRule -DisplayName \$rule -Direction Inbound -Action Allow -Protocol TCP -LocalAddress \$ip -LocalPort \$port | Out-Null" >/dev/null

echo "tailnet_companion_api_forwarding_ready=true"

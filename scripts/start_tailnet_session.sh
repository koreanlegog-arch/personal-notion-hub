#!/usr/bin/env bash
set -euo pipefail

# Start an owner-only PNH tailnet session from WSL.
# Pairing can be handed off to an owner-only Discord DM when
# PNH_OWNER_DISCORD_TARGET=user:<discord-user-id> is set.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PNH_TAILNET_PORT:-8765}"
RULE_NAME="${PNH_TAILNET_FIREWALL_RULE:-PNH Tailnet Ingress ${PORT}}"
TAILSCALE_EXE="${PNH_TAILSCALE_EXE:-C:\\Program Files\\Tailscale\\tailscale.exe}"
OWNER_TARGET="${PNH_OWNER_DISCORD_TARGET:-}"
PAIRING_HANDOFF_FILE="${PNH_PAIRING_HANDOFF_FILE:-companion/private/pairing_handoff.json}"
CAPTURE_AUTO_DISPATCH="${PNH_CAPTURE_AUTO_DISPATCH:-1}"
OWNER_DEVICE_SESSIONS="${PNH_ENABLE_OWNER_DEVICE_SESSIONS:-1}"

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

cleanup() {
  local exit_code=$?
  powershell.exe -NoProfile -Command "\$ip='${TAILNET_IP}'; \$port=${PORT}; \$rule='${RULE_NAME}'; netsh interface portproxy delete v4tov4 listenaddress=\$ip listenport=\$port | Out-Null; Get-NetFirewallRule -DisplayName \$rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue" >/dev/null 2>&1 || true
  echo "tailnet_session_cleanup=true"
  exit "$exit_code"
}

TAILNET_IP="$(detect_tailnet_ip)"
ORIGIN="http://${TAILNET_IP}:${PORT}"

cd "$ROOT"
echo "# PNH Tailnet Session"
echo "tailnet_url=${ORIGIN}/"
echo "allowed_origin=${ORIGIN}"
echo "pairing_handoff_file=${PAIRING_HANDOFF_FILE}"
if [[ -n "$OWNER_TARGET" ]]; then
  echo "pairing_code_policy=owner_discord_dm_plus_ignored_local_file"
else
  echo "pairing_code_policy=ignored_local_file_only_set_PNH_OWNER_DISCORD_TARGET_for_remote_dm"
fi
echo "capture_auto_dispatch_enabled=${CAPTURE_AUTO_DISPATCH}"
echo "owner_device_sessions_enabled=${OWNER_DEVICE_SESSIONS}"

powershell.exe -NoProfile -Command "\$ip='${TAILNET_IP}'; \$port=${PORT}; \$rule='${RULE_NAME}'; netsh interface portproxy delete v4tov4 listenaddress=\$ip listenport=\$port | Out-Null; Get-NetFirewallRule -DisplayName \$rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue; netsh interface portproxy add v4tov4 listenaddress=\$ip listenport=\$port connectaddress=127.0.0.1 connectport=\$port; New-NetFirewallRule -DisplayName \$rule -Direction Inbound -Action Allow -Protocol TCP -LocalAddress \$ip -LocalPort \$port | Out-Null" >/dev/null
echo "tailnet_forwarding_ready=true"

trap cleanup EXIT INT TERM

SERVER_ARGS=(
  companion/server.py
  --host 127.0.0.1 \
  --port "$PORT" \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file \
  --enable-browser-bridge \
  --enable-tailnet-ingress \
  --allowed-origin "$ORIGIN" \
  --pairing-handoff-file "$PAIRING_HANDOFF_FILE"
)

if [[ -n "$OWNER_TARGET" ]]; then
  SERVER_ARGS+=(--pairing-handoff-channel discord-dm --pairing-handoff-owner-target "$OWNER_TARGET")
fi

if [[ "$CAPTURE_AUTO_DISPATCH" == "1" || "$CAPTURE_AUTO_DISPATCH" == "true" ]]; then
  SERVER_ARGS+=(--enable-capture-auto-dispatch)
fi

if [[ "$OWNER_DEVICE_SESSIONS" == "1" || "$OWNER_DEVICE_SESSIONS" == "true" ]]; then
  SERVER_ARGS+=(--enable-owner-device-sessions)
fi

python3 "${SERVER_ARGS[@]}"

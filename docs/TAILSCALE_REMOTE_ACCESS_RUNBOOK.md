# Tailscale Remote Access Runbook

Date: 2026-06-05

## Purpose

This runbook enables owner-only mobile access to Personal Notion Hub without placing PNH on the public internet.

The runbook has two paths:

1. Preferred: Tailscale Serve over HTTPS.
2. Fallback: Tailscale tailnet HTTP through temporary Windows `portproxy`.

Use the fallback only when Tailscale HTTPS certificates are unavailable.

## Prerequisites

- Tailscale is installed and signed in on Windows.
- The phone is signed in to the same tailnet.
- PNH encrypted vault mode is ready.
- Do not paste secrets, pairing codes, or session tokens into chat or docs.

## Check Tailscale State

Run in Windows PowerShell:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" status
& "C:\Program Files\Tailscale\tailscale.exe" ip -4
(& "C:\Program Files\Tailscale\tailscale.exe" status --json | ConvertFrom-Json).Self.DNSName
```

Record only redacted device facts in reports, for example:

- Windows tailnet DNS: `[windows-tailnet-dns]`
- Windows tailnet IPv4: `[windows-tailnet-ip]`
- Phone peer: `[android-tailnet-peer]`

## Preferred Path: Tailscale Serve HTTPS

Start the companion in WSL:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file \
  --enable-browser-bridge \
  --enable-tailnet-ingress \
  --allowed-origin https://<WINDOWS_TAILNET_DNS_WITHOUT_TRAILING_DOT>
```

Start Tailscale Serve in Windows PowerShell:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" serve --yes --bg http://127.0.0.1:8765
& "C:\Program Files\Tailscale\tailscale.exe" serve status
```

Open on phone:

```text
https://<WINDOWS_TAILNET_DNS_WITHOUT_TRAILING_DOT>/
```

Stop Serve when finished:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" serve reset
```

## Fallback Path: Tailnet HTTP With Temporary Windows Portproxy

Use this only when Tailscale HTTPS certificates are unavailable.

### Headless Companion API Service

Use this path for phone automation POST requests when the headless companion
service is already installed and active:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
bash scripts/pnh_tailnet_companion_api_start.sh --apply
python3 scripts/pnh_tailnet_companion_api_status.py
```

Stop forwarding:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
bash scripts/pnh_tailnet_companion_api_stop.sh --apply
```

This path does not start a second companion process and does not enable browser
pairing. It forwards the owner tailnet IP to the existing loopback companion
service.

### Recommended WSL Helper

Start a session from WSL:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
bash scripts/start_tailnet_session.sh
```

If the managed headless companion API service already uses port `8765`, start a
separate browser-pairing session on another port:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
PNH_TAILNET_PORT=8766 bash scripts/start_tailnet_session.sh
```

The script prints:

- `tailnet_url`
- `allowed_origin`
- `pairing_handoff_file`
- `pairing_code_policy`
- `capture_auto_dispatch_enabled`

For remote operation, set owner-only Discord handoff before starting:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
export PNH_OWNER_DISCORD_TARGET="user:<discord-user-id>"
PNH_TAILNET_PORT=8766 bash scripts/start_tailnet_session.sh
```

With `PNH_OWNER_DISCORD_TARGET` set, the pairing code is delivered to the owner
DM through OpenClaw and also written only to ignored local handoff storage. Do
not paste the code into Codex chat, docs, screenshots, Git, or shared channels.

`PNH_CAPTURE_AUTO_DISPATCH` defaults to `1` for this helper. New browser
captures can therefore start bounded background dispatch without a second
terminal command. Set `PNH_CAPTURE_AUTO_DISPATCH=0` only when intentionally
testing storage without dispatch.

When the companion process exits normally, the script removes the temporary Windows forwarding rule. If cleanup is needed manually, run:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
bash scripts/stop_tailnet_session.sh
```

### Manual Fallback

Start the companion in WSL:

```bash
cd /home/koreanlego/projects/Personal_Notion_Hub
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file \
  --enable-browser-bridge \
  --enable-tailnet-ingress \
  --allowed-origin http://<WINDOWS_TAILNET_IP>:8765
```

Create temporary Windows forwarding in Administrator PowerShell:

```powershell
netsh interface portproxy add v4tov4 listenaddress=<WINDOWS_TAILNET_IP> listenport=8765 connectaddress=127.0.0.1 connectport=8765
New-NetFirewallRule -DisplayName "PNH Tailnet Ingress 8765" -Direction Inbound -Action Allow -Protocol TCP -LocalAddress <WINDOWS_TAILNET_IP> -LocalPort 8765
```

Open on phone while Tailscale is connected:

```text
http://<WINDOWS_TAILNET_IP>:8765/
```

Remove temporary Windows forwarding when finished:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=<WINDOWS_TAILNET_IP> listenport=8765
Get-NetFirewallRule -DisplayName "PNH Tailnet Ingress 8765" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
```

## Pairing

The companion still creates a short-lived pairing code at startup. Preferred
remote handoff is owner-only Discord DM through `PNH_OWNER_DISCORD_TARGET`.
Local terminal/file handoff is fallback-only.

If `PNH_ENABLE_OWNER_DEVICE_SESSIONS=1` is set, the paired browser may receive a
revocable owner-device credential for reconnect. The raw credential must not be
logged, screenshotted, or copied into chat. It is stored only in the browser
localStorage and the ignored local credential hash store.

After pairing, the browser receives a short-lived session token. Do not record it.

## Validation Commands

Run from WSL:

```bash
python3 scripts/tailnet_ingress_smoke_check.py
python3 scripts/browser_bridge_smoke_check.py
python3 scripts/phone_ingress_smoke_check.py
python3 scripts/sensitive_owner_readiness_check.py
python3 scripts/smoke_check.py
```

## Disable Checklist

- Stop the companion process.
- Run `tailscale serve reset`.
- Delete temporary `portproxy` rule.
- Delete temporary firewall rule.
- Confirm no PNH portproxy remains:

```powershell
netsh interface portproxy show v4tov4
Get-NetFirewallRule -DisplayName "PNH Tailnet Ingress 8765" -ErrorAction SilentlyContinue
```

## Failure Modes

- `tailscale cert` reports TLS certificates are unsupported: use fallback path or enable HTTPS certificates in Tailscale admin settings if available.
- Phone cannot open the URL: confirm Tailscale app is connected on the phone and the Windows node is online.
- Pairing fails: restart the companion and use the newly printed code.
- Capture fails: verify the exact `--allowed-origin` matches the phone URL origin.
- Browser shows insecure HTTP warning: expected only for the fallback path; do not use fallback for client-facing deployment.

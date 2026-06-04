# Phone Ingress Security

## Status

MVP implemented for synthetic or low-risk local LAN testing.

## Objective

Allow a phone browser on the same trusted private LAN to open Personal Notion
Hub and send explicit Assistant/Launch captures into the workspace local private
inbox or encrypted vault path.

## Default Boundary

Phone ingress is disabled by default.

The companion remains loopback-only unless all are true:

- `--enable-private-inbox`
- `--enable-browser-bridge`
- `--enable-phone-ingress`
- exact `--allowed-origin`
- bind host is `0.0.0.0`, `127.0.0.1`, or a private LAN IP

## Recommended Test Mode

Use synthetic or low-risk data first:

```bash
python3 scripts/private_inbox_init.py
python3 scripts/phone_ingress_lan_info.py
python3 companion/server.py \
  --host 0.0.0.0 \
  --port 8765 \
  --enable-private-inbox \
  --enable-browser-bridge \
  --enable-phone-ingress \
  --allowed-origin http://<LAN_IP>:8765
```

Open on the phone:

```text
http://<LAN_IP>:8765/
```

Use the one-time pairing code printed in the local WSL terminal. Do not record
the code in chat, screenshots, Git, Discord, or reports.

## Sensitive Data Mode

For real sensitive data, use encrypted vault mode:

```bash
python3 companion/server.py \
  --host 0.0.0.0 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file \
  --enable-browser-bridge \
  --enable-phone-ingress \
  --allowed-origin http://<LAN_IP>:8765
```

Do not use plaintext private inbox mode for routine high-sensitivity records.

## Security Controls

- LAN exposure requires explicit `--enable-phone-ingress`.
- Browser writes still require one-time pairing and browser session token.
- Session token is held in browser memory only.
- File bearer token is never sent to the browser.
- CORS accepts only the exact configured origin.
- Wildcard, public IP, `localhost`, and `0.0.0.0` origins are rejected.
- Static UI is served by the companion in phone ingress mode so API and UI can share the same origin.
- API responses remain metadata-only.
- Logs do not include request body values.
- Generated screenshots and browser QA artifacts are ignored by Git.

## Stop Conditions

Stop and do not enter real private data if:

- phone and PC are not on a trusted private network
- pairing code appears in a screenshot, chat, log, or report
- allowed origin is not a concrete private LAN URL
- API response shows title/body text
- encrypted vault mode is unavailable for sensitive input
- redacted browser QA fails

## Validation

Automated:

```bash
python3 scripts/phone_ingress_smoke_check.py
python3 scripts/browser_bridge_smoke_check.py
python3 scripts/smoke_check.py
```

Manual:

- run companion with phone ingress flags
- open `http://<LAN_IP>:8765/` on phone
- pair using local WSL terminal code
- send synthetic Assistant input
- confirm `python3 scripts/private_inbox_status.py` count increased without printing private values

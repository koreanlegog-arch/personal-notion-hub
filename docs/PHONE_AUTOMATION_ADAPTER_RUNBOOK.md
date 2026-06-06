# Phone Automation Adapter Runbook

Date: 2026-06-06

## Purpose

This runbook defines how owner-controlled phone automation tools can send
contacts, calendar items, call notes, or recording transcripts into the PNH
encrypted private vault.

The workflow is designed for tools such as iOS Shortcuts, Android Tasker, or
other owner-controlled local/mobile automation systems.

## Endpoint

```text
POST /api/private/phone-adapter-captures
```

The endpoint requires the same bearer token or browser session authentication
as `/api/private/mobile-captures`.

## Schema Discovery

Authenticated schema endpoint:

```text
GET /api/private/phone-adapter-schema
```

Local schema command:

```bash
python3 scripts/pnh_phone_adapter_payload_template.py --schema
```

Generate owner-mobile automation profile templates:

```bash
python3 scripts/pnh_phone_automation_profile_template.py \
  --out ops/runs/PNH-PHONE-AUTOMATION-PROFILE-20260606/phone_automation_profile.json
```

The profile output uses placeholders such as
`Bearer <PNH_PRIVATE_INBOX_TOKEN>`. It must not contain real tokens.

Generate a single owner handoff packet with placeholder-only profiles,
readiness summary, live-probe sequence, and safety rules:

```bash
python3 scripts/pnh_phone_automation_handoff_packet.py
```

The handoff packet intentionally keeps the endpoint as
`http://<owner-tailnet-ip>:8765` and the auth header as
`Bearer <PNH_PRIVATE_INBOX_TOKEN>`. Replace those only inside the owner phone
automation tool, not in committed files or chat.

Check whether the current machine is ready for owner phone-tool configuration:

```bash
python3 scripts/pnh_phone_automation_setup_readiness.py
```

This command checks token-file presence and permissions, companion service
health, owner-tailnet reachability, and the real-data privacy gate. It does not
print the bearer token or persist the tailnet IP in evidence.

Run a synthetic phone automation rehearsal:

```bash
python3 scripts/pnh_phone_automation_rehearsal.py
```

For owner-tailnet rehearsal:

```bash
python3 scripts/pnh_phone_automation_rehearsal.py --use-tailnet
```

The rehearsal generates a synthetic payload, sends it through the phone adapter
endpoint, and records metadata-only evidence. It does not persist the exact
tailnet URL or print the bearer token.

Probe whether a phone automation send reached the encrypted private vault:

```bash
python3 scripts/pnh_phone_automation_live_probe.py
```

To wait for the next owner phone automation send, capture the current inbox
count first and use it as the baseline:

```bash
python3 scripts/private_inbox_status.py
python3 scripts/pnh_phone_automation_live_probe.py \
  --baseline-count <current-total-captures> \
  --timeout-seconds 120
```

The live probe reads metadata only. It does not decrypt private bodies and does
not print bearer tokens or owner-network URLs.

Run an owner capture session that waits for a new phone payload and then runs
post-capture privacy/completion checks:

```bash
python3 scripts/pnh_owner_phone_capture_session.py --timeout-seconds 300
```

For fixture-only diagnostics:

```bash
python3 scripts/pnh_owner_phone_capture_session.py --skip-post-checks
```

Summarize recent phone automation captures without reading private bodies:

```bash
python3 scripts/pnh_phone_capture_recent_summary.py
```

## Supported Adapters

- `phone-contacts-json`
- `phone-calendar-json`
- `phone-call-log-json`
- `phone-recording-transcript-json`

## Payload Shape

```json
{
  "adapter": "phone-call-log-json",
  "createdAt": "2026-06-06T00:00:00Z",
  "items": [
    {
      "title": "Synthetic private item",
      "body": "Synthetic private body for local fixture rehearsal only.",
      "sensitivity": "highly_sensitive",
      "createdAt": "2026-06-06T00:00:00Z"
    }
  ]
}
```

Accepted item aliases:

- `title`, `name`, or `summary`
- `body`, `text`, `notes`, or `description`
- `sensitivity`
- `createdAt` or `created_at`

## Local Template And Send Rehearsal

Create a synthetic template:

```bash
python3 scripts/pnh_phone_adapter_payload_template.py \
  --adapter phone-call-log-json \
  --out companion/private/scheduler/phone-call-template.json
```

Send it to a running local companion:

```bash
python3 scripts/pnh_phone_adapter_send.py \
  --base-url http://127.0.0.1:8765 \
  --payload companion/private/scheduler/phone-call-template.json
```

For owner-only LAN or tailnet URLs:

```bash
python3 scripts/pnh_phone_adapter_send.py \
  --base-url http://100.x.y.z:8765 \
  --allow-owner-network \
  --payload companion/private/scheduler/phone-call-template.json
```

## Owner-Only Tailnet API Forwarding

When the headless companion service is active on WSL loopback, expose it to the
owner tailnet with:

```bash
bash scripts/pnh_tailnet_companion_api_start.sh --apply
python3 scripts/pnh_tailnet_companion_api_status.py
```

Then send from an owner-controlled phone automation tool to:

```text
http://<windows-tailnet-ip>:8765/api/private/phone-adapter-captures
```

Remove forwarding:

```bash
bash scripts/pnh_tailnet_companion_api_stop.sh --apply
```

## Expected Response

The response is metadata-only:

```json
{
  "ok": true,
  "writesPerformed": true,
  "phoneAdapterCapture": {
    "recordsAccepted": 1,
    "recordsWritten": 1,
    "duplicatesSkipped": 0,
    "captureIds": ["capture-id"],
    "storageMode": "encrypted-vault",
    "privateValuesPrinted": false
  }
}
```

Raw phone data is not echoed.

Repeated identical normalized phone payloads are skipped by the private ingest
dedup layer. The response remains metadata-only and reports `duplicatesSkipped`.

## Safety Rules

- Do not paste bearer tokens into chat, screenshots, docs, or commits.
- Keep token files under ignored `companion/private/`.
- Use encrypted vault mode for real private data.
- Use `--allow-owner-network` only for owner-controlled LAN/tailnet endpoints.
- Do not route this endpoint through public internet without a separate
  production auth and exposure review.
- Tailnet forwarding is owner-only and uses Tailscale's encrypted tunnel, but
  the fallback browser/API URL is still `http://...`; do not treat it as a
  client-facing HTTPS deployment.

## Verification

```bash
python3 scripts/pnh_phone_adapter_send_smoke_check.py
python3 scripts/pnh_phone_automation_profile_template_smoke_check.py
python3 scripts/pnh_phone_automation_handoff_packet_smoke_check.py
python3 scripts/pnh_phone_automation_setup_readiness_smoke_check.py
python3 scripts/pnh_phone_automation_rehearsal_smoke_check.py
python3 scripts/pnh_phone_automation_live_probe_smoke_check.py
python3 scripts/pnh_owner_phone_capture_session_smoke_check.py
python3 scripts/pnh_phone_capture_recent_summary_smoke_check.py
python3 scripts/pnh_private_ingest_dedup_smoke_check.py
python3 scripts/phone_adapter_ingress_smoke_check.py
python3 scripts/pnh_tailnet_companion_api_smoke_check.py
python3 scripts/private_inbox_status.py --include-recent
```

## Current Limit

This runbook does not implement native phone extraction. It defines the secure
workspace ingress contract and local rehearsal path for owner-controlled phone
automation tools.

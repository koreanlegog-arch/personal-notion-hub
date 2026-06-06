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

## Expected Response

The response is metadata-only:

```json
{
  "ok": true,
  "writesPerformed": true,
  "phoneAdapterCapture": {
    "recordsAccepted": 1,
    "captureIds": ["capture-id"],
    "storageMode": "encrypted-vault",
    "privateValuesPrinted": false
  }
}
```

Raw phone data is not echoed.

## Safety Rules

- Do not paste bearer tokens into chat, screenshots, docs, or commits.
- Keep token files under ignored `companion/private/`.
- Use encrypted vault mode for real private data.
- Use `--allow-owner-network` only for owner-controlled LAN/tailnet endpoints.
- Do not route this endpoint through public internet without a separate
  production auth and exposure review.

## Verification

```bash
python3 scripts/pnh_phone_adapter_send_smoke_check.py
python3 scripts/phone_adapter_ingress_smoke_check.py
python3 scripts/private_inbox_status.py --include-recent
```

## Current Limit

This runbook does not implement native phone extraction. It defines the secure
workspace ingress contract and local rehearsal path for owner-controlled phone
automation tools.

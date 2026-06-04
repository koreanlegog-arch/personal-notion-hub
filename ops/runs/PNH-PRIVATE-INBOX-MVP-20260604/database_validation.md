# Database Validation

Date: 2026-06-04

## Data Objective

Persist mobile-like private captures in a workspace-local inbox so later automation can read, triage, and dispatch them.

## Storage

- Engine: Python stdlib SQLite.
- Path: `companion/private/pnh_private_inbox.sqlite`.
- Git policy: ignored, never committed.

## Schema

Tables:

- `meta`: schema metadata.
- `mobile_captures`: source, kind, title, body, payload JSON, sensitivity, status, timestamps.
- `audit_events`: append-only local event trail for capture creation.

Indexes:

- `idx_mobile_captures_status`
- `idx_mobile_captures_stored_at`

## Migration Strategy

Current schema version: `1`.

This is an initial local-only schema. Future schema changes should use additive migration first, then data backfill, then contract cleanup only after backup/restore procedures exist.

## Backup And Rollback

Rollback for this MVP:

- stop local companion
- remove ignored `companion/private/` only if the supervisor intentionally wants to discard local private test data
- revert tracked code/docs by Git commit

No automatic destructive cleanup is performed by scripts.

## Validation Evidence

Captured in `release_readiness.md`.

Observed result:

- `private_inbox_init.py` created the ignored local SQLite inbox and auth token file.
- local companion accepted one authorized synthetic mobile capture.
- `private_inbox_status.py` reported `totalCaptures=1`.
- API/status outputs did not print raw private body text.

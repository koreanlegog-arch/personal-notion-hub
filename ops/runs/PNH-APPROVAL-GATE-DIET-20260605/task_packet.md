# Task Packet: PNH Approval Gate Diet

Date: 2026-06-05

## Objective

Separate obsolete or already-closed approval gates from active material gates so the PNH workflow does not re-request approval for work that is already inside an approved phase boundary.

## Scope

- Review active PNH docs and historical run packets for approval-gate drift.
- Create a current approval gate policy.
- Update active docs to reflect implemented private inbox, encrypted vault, browser bridge, Tailscale ingress, and redacted QA status.
- Archive closed historical gates without deleting audit packets.

## Out Of Scope

- Editing every historical packet in place.
- Removing security gates for real adapters, external dispatch, public deployment, or client-facing release.
- Changing runtime behavior.

## Acceptance Criteria

- Current active policy separates closed gates from active material gates.
- Active docs no longer imply that already implemented MVP capabilities still need fresh approval.
- Historical packet references are preserved as audit evidence.
- Verification confirms docs exist and no runtime code behavior changed.


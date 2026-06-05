# Task Packet: PNH Mobile Command Packet

Date: 2026-06-05

## Objective

Turn mobile Launch intake from a generic capture into a typed command packet that can later feed a GitHub/Discord/OpenClaw dispatch flow.

## Scope

- Add command type selection to Launch intake.
- Store command type in local launch packets.
- Send companion payloads as `pnh_mobile_command_packet`.
- Preserve encrypted vault write path and metadata-only response.
- Keep external dispatch disabled.

## Out Of Scope

- GitHub issue creation.
- Discord/OpenClaw dispatch.
- New external API, token, OAuth, or cloud sync.
- Real phone/contact/calendar/call/recording adapters.

## Acceptance Criteria

- Launch packets include a command type.
- Supported command types include `project_brief`, `task_request`, `daily_command`, and `urgent_approval`.
- Companion payload includes `payloadType=pnh_mobile_command_packet`.
- Smoke test verifies a typed command packet can be stored without private value leakage.
- Existing smoke suite still passes.


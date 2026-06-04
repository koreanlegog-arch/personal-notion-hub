# PNH-PHONE-INGRESS-REACHABILITY-20260605 Task Packet

## Objective

Diagnose why the phone browser cannot reach `http://172.31.155.144:8765/` and
prepare the next safe reachability path.

## Scope

- Verify WSL companion listener state.
- Verify Windows localhost and Windows IP reachability.
- Inspect Windows portproxy and firewall status.
- Add a reachability diagnostic script.
- Keep public-IP exposure blocked by policy.

## Out Of Scope

- Opening public inbound firewall exposure.
- Allowing public IP origins.
- Installing external tunnel software.
- Requesting or storing secrets.

## Acceptance Criteria

- WSL listener status is known.
- Windows localhost reachability is known.
- Phone-reachable private LAN candidate status is known.
- Unsafe public-IP path is explicitly rejected.
- Next operator action is clear.

## Risk

Medium. Reachability work can accidentally expose the companion beyond the
trusted LAN. This run keeps public IP exposure blocked.

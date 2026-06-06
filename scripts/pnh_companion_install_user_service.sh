#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="pnh-companion.service"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
HOST="127.0.0.1"
PORT="8765"
APPLY="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY="true"
      shift
      ;;
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown_arg=$1" >&2
      exit 2
      ;;
  esac
done

echo "# PNH Companion User Service Installer"
echo "root=${ROOT}"
echo "service=${SERVICE_NAME}"
echo "host=${HOST}"
echo "port=${PORT}"
echo "apply=${APPLY}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl_available=false"
  exit 2
fi

if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "systemd_user_available=false"
  exit 2
fi

PLAN_JSON="$(python3 "${ROOT}/scripts/pnh_companion_service_plan.py" --host "${HOST}" --port "${PORT}")"
SERVICE_TEXT="$(printf '%s\n' "${PLAN_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["serviceText"], end="")')"

if [[ "${APPLY}" != "true" ]]; then
  echo "mode=dry-run"
  printf '%s\n' "${PLAN_JSON}"
  exit 0
fi

mkdir -p "${SYSTEMD_USER_DIR}"
printf '%s' "${SERVICE_TEXT}" > "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
chmod 0644 "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}" >/dev/null
systemctl --user restart "${SERVICE_NAME}"

echo "installed=true"
systemctl --user --no-pager --full status "${SERVICE_NAME}" || true

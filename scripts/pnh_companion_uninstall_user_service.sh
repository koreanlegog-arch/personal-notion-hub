#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="pnh-companion.service"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
APPLY="false"

if [[ "${1:-}" == "--apply" ]]; then
  APPLY="true"
fi

echo "# PNH Companion User Service Uninstaller"
echo "apply=${APPLY}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl_available=false"
  exit 2
fi

if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "systemd_user_available=false"
  exit 2
fi

if [[ "${APPLY}" != "true" ]]; then
  echo "mode=dry-run"
  echo "would_stop=${SERVICE_NAME}"
  echo "would_remove=${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
  exit 0
fi

systemctl --user disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
rm -f "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
systemctl --user daemon-reload
echo "uninstalled=true"

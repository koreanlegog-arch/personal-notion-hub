#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PNH_QA_PORT:-4175}"
BASE_URL="http://127.0.0.1:${PORT}"
RUN_DIR="${PNH_QA_RUN_DIR:-${ROOT}/ops/runs/PNH-ASSISTANT-DISPATCH-INTENT-QA-20260605}"
ARTIFACT_DIR="${RUN_DIR}/artifacts"

mkdir -p "${ARTIFACT_DIR}"

if ! command -v npx >/dev/null 2>&1; then
  echo "playwright_assistant_dispatch_intent_qa_skipped=true"
  echo "reason=npx_unavailable"
  exit 0
fi

if ! npx --no-install playwright --version >/dev/null 2>&1; then
  echo "playwright_assistant_dispatch_intent_qa_skipped=true"
  echo "reason=playwright_cli_unavailable_without_install"
  exit 0
fi

PLAYWRIGHT_NODE_MODULES="$(find "${HOME}/.npm/_npx" -path '*/node_modules/playwright/test.js' -printf '%h\n' 2>/dev/null | sed 's#/playwright$##' | head -n 1 || true)"
if [[ -z "${PLAYWRIGHT_NODE_MODULES}" ]]; then
  echo "playwright_assistant_dispatch_intent_qa_skipped=true"
  echo "reason=playwright_node_modules_unavailable"
  exit 0
fi

if ! find "${HOME}/.cache/ms-playwright" -path '*chrome-headless-shell' -type f -perm -u=x 2>/dev/null | grep -q .; then
  echo "playwright_assistant_dispatch_intent_qa_blocked=true"
  echo "reason=playwright_chromium_binary_unavailable"
  exit 0
fi

CHROMIUM_SHELL="$(find "${HOME}/.cache/ms-playwright" -path '*chrome-headless-shell' -type f -perm -u=x 2>/dev/null | head -n 1)"
if ldd "${CHROMIUM_SHELL}" 2>/dev/null | grep -q 'not found'; then
  echo "playwright_assistant_dispatch_intent_qa_blocked=true"
  echo "reason=playwright_system_dependencies_missing"
  echo "missing_libraries=$(ldd "${CHROMIUM_SHELL}" 2>/dev/null | awk '/not found/ {print $1}' | sort -u | paste -sd, -)"
  exit 0
fi

python3 -m http.server "${PORT}" --bind 127.0.0.1 --directory "${ROOT}" >"${ARTIFACT_DIR}/http-server.log" 2>&1 &
SERVER_PID="$!"
cleanup() {
  kill "${SERVER_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -fsS "${BASE_URL}/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

PNH_QA_BASE_URL="${BASE_URL}" \
PNH_QA_ARTIFACT_DIR="${ARTIFACT_DIR}" \
NODE_PATH="${PLAYWRIGHT_NODE_MODULES}${NODE_PATH:+:${NODE_PATH}}" \
npx --no-install playwright test "${ROOT}/tests/assistant-dispatch-intent.spec.cjs" \
  --browser=chromium \
  --workers=1 \
  --reporter=line \
  --output="${ARTIFACT_DIR}/playwright-output"

echo "playwright_assistant_dispatch_intent_qa_pass=true"
echo "base_url=${BASE_URL}"
echo "artifact_dir=${ARTIFACT_DIR}"

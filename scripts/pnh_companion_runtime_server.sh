#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

python3 companion/server.py \
  --host "${PNH_COMPANION_HOST:-127.0.0.1}" \
  --port "${PNH_COMPANION_PORT:-8765}" \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider "${PNH_VAULT_PASSPHRASE_PROVIDER:-windows-dpapi-file}" \
  --vault-passphrase-name "${PNH_VAULT_PASSPHRASE_NAME:-vault-passphrase}"

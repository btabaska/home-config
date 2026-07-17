#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="$HOME/slskd-native/.env"
APP_DIR="$HOME/slskd-native"
BIN="$HOME/bin/slskd/slskd"

if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^[A-Z_]+= ]] || continue
    [[ "$line" =~ ^# ]] && continue
    export "$line"
  done < "$ENV_FILE"
fi

export SLSKD_REMOTE_CONFIGURATION=true
export SLSKD_SLSK_LISTEN_PORT=50300
export SLSKD_HTTP_PORT=5030
export SLSKD_HTTPS_DISABLED=true
export SLSKD_HTTP_IP=${SLSKD_HTTP_IP:-127.0.0.1}
export SLSKD_USERNAME="${SLSKD_WEB_USERNAME:-slskd}"
export SLSKD_PASSWORD="${SLSKD_WEB_PASSWORD:?Set SLSKD_WEB_PASSWORD in ~/slskd-native/.env}"

exec "$BIN" --app-dir "$APP_DIR"

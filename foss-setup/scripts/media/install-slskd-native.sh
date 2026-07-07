#!/usr/bin/env bash
# Install slskd as a native binary on the Bytesized seedbox (Betty).
#
# Rootless Docker cannot expose Soulseek peer port 50300 — use this instead.
# Run from your MacBook after SSH to seedbox works:
#   scp scripts/media/install-slskd-native.sh seedbox:~/install-slskd-native.sh
#   ssh seedbox 'bash ~/install-slskd-native.sh'
#
# Credentials: edit ~/slskd-native/.env (see configs/seedbox/slskd-native.example.env)

set -euo pipefail

SLSKD_VERSION="${SLSKD_VERSION:-0.25.1}"
APP_DIR="${HOME}/slskd-native"
BIN_DIR="${HOME}/bin/slskd"
ENV_FILE="${APP_DIR}/.env"
# Locate the example env template. Honors an explicit REPO_EXAMPLE override,
# otherwise tries (1) the repo-relative path next to this script (works when run
# from a repo checkout) then (2) ~/foss-setup (works on the seedbox after scp).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${REPO_EXAMPLE:-}" ]]; then
  for candidate in \
    "${SCRIPT_DIR}/../../configs/seedbox/slskd-native.example.env" \
    "${HOME}/foss-setup/configs/seedbox/slskd-native.example.env"; do
    if [[ -f "$candidate" ]]; then
      REPO_EXAMPLE="$candidate"
      break
    fi
  done
fi
REPO_EXAMPLE="${REPO_EXAMPLE:-${HOME}/foss-setup/configs/seedbox/slskd-native.example.env}"

log() { printf '[install-slskd] %s\n' "$*"; }

mkdir -p "$APP_DIR" "$BIN_DIR" "${HOME}/files/slskd/incomplete"

if [[ ! -x "${BIN_DIR}/slskd" ]]; then
  log "Downloading slskd ${SLSKD_VERSION}..."
  tmp="$(mktemp -d)"
  curl -fsSL -o "${tmp}/slskd.zip" \
    "https://github.com/slskd/slskd/releases/download/${SLSKD_VERSION}/slskd-${SLSKD_VERSION}-linux-x64.zip"
  unzip -qo "${tmp}/slskd.zip" -d "$BIN_DIR"
  chmod +x "${BIN_DIR}/slskd"
  rm -rf "$tmp"
fi

cat > "${BIN_DIR}/start-slskd.sh" <<'SCRIPT'
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
export SLSKD_HTTP_IP="${SLSKD_HTTP_IP:-127.0.0.1}"
export SLSKD_USERNAME="${SLSKD_WEB_USERNAME:-slskd}"
export SLSKD_PASSWORD="${SLSKD_WEB_PASSWORD:?Set SLSKD_WEB_PASSWORD in ~/slskd-native/.env}"

exec "$BIN" --app-dir "$APP_DIR"
SCRIPT
chmod +x "${BIN_DIR}/start-slskd.sh"

mkdir -p "${HOME}/.config/systemd/user"
cat > "${HOME}/.config/systemd/user/slskd.service" <<UNIT
[Unit]
Description=Soulseek daemon (native)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${BIN_DIR}/start-slskd.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNIT

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$REPO_EXAMPLE" ]]; then
    cp "$REPO_EXAMPLE" "$ENV_FILE"
  else
    log "Create ${ENV_FILE} from configs/seedbox/slskd-native.example.env before starting."
    exit 1
  fi
  chmod 600 "$ENV_FILE"
  log "Created ${ENV_FILE} — edit Soulseek + web UI credentials, then re-run this script."
  exit 0
fi

chmod 600 "$ENV_FILE"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
systemctl --user daemon-reload
systemctl --user enable --now slskd.service
loginctl enable-linger "$(whoami)" 2>/dev/null || true

sleep 5
if systemctl --user is-active --quiet slskd.service; then
  log "slskd running. Web UI: ssh -L 5030:127.0.0.1:5030 seedbox → http://localhost:5030"
else
  journalctl --user -u slskd.service -n 20 --no-pager
  exit 1
fi

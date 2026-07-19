#!/usr/bin/env bash
#
# etckeeper-setup.sh — put /etc under version control with etckeeper, and commit
#                      automatically on change via a systemd .path watcher.
#
# What it does (idempotent — safe to re-run):
#   1. Detects the package manager (apt vs pacman) and installs etckeeper.
#   2. Installs our etckeeper.conf to /etc/etckeeper/etckeeper.conf.
#   3. Runs `etckeeper init` + an initial commit (no-op if already a repo).
#   4. Installs etc-watch.path AND writes its companion etckeeper-commit.service.
#   5. Enables the .path unit so /etc changes are committed automatically.
#
# Docs: https://etckeeper.branchable.com/
#
# >>> /etc HOLDS SECRETS. If you configure PUSH_REMOTE in etckeeper.conf it MUST
#     point at a PRIVATE per-host repo (e.g. Forgejo). Never push /etc publicly. <<<
#
# Skipped on Synology/DSM (no systemd, managed appliance).
#
# Usage:  sudo ./etckeeper-setup.sh
# Optional env:
#   CONF_SRC=/path/to/etckeeper.conf   # defaults to ../../configs/inventory/etckeeper.conf

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_SRC="${CONF_SRC:-${SCRIPT_DIR}/../../configs/inventory/etckeeper.conf}"
PATH_UNIT_SRC="${SCRIPT_DIR}/etc-watch.path"

readonly SYSTEMD_DIR="/etc/systemd/system"
readonly COMMIT_SERVICE="${SYSTEMD_DIR}/etckeeper-commit.service"
readonly PATH_UNIT="${SYSTEMD_DIR}/etc-watch.path"
readonly SERIALIZE_WRAPPER="/usr/local/sbin/etckeeper-serialized.sh"
readonly DAILY_DROPIN_DIR="${SYSTEMD_DIR}/etckeeper.service.d"

log()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  [[ "${EUID}" -eq 0 ]] || die "Run as root or with sudo (e.g. 'sudo $0')."
}

skip_on_synology() {
  if [[ -f /etc/synoinfo.conf || -d /etc.defaults ]] || grep -qi synology /etc/os-release 2>/dev/null; then
    warn "Synology/DSM detected — etckeeper+systemd flow not supported here. Skipping."
    exit 0
  fi
  command -v systemctl >/dev/null 2>&1 || die "systemd not found; this script needs systemd."
}

install_etckeeper() {
  if command -v etckeeper >/dev/null 2>&1; then
    log "etckeeper already installed."
    return 0
  fi
  if command -v apt-get >/dev/null 2>&1; then
    log "Installing etckeeper + git via apt."
    apt-get update -y
    apt-get install -y etckeeper git
  elif command -v pacman >/dev/null 2>&1; then
    log "Installing etckeeper + git via pacman."
    pacman -Sy --needed --noconfirm etckeeper git
  else
    die "No supported package manager (apt/pacman) found."
  fi
}

install_conf() {
  [[ -r "${CONF_SRC}" ]] || die "etckeeper.conf source not readable: ${CONF_SRC}"
  install -D -m 0644 "${CONF_SRC}" /etc/etckeeper/etckeeper.conf
  log "Installed etckeeper.conf -> /etc/etckeeper/etckeeper.conf"
  warn "Remember: set PUSH_REMOTE in /etc/etckeeper/etckeeper.conf to a PRIVATE repo before pushing /etc."
}

init_repo() {
  if [[ -d /etc/.git ]]; then
    log "/etc is already an etckeeper git repo."
  else
    log "Initializing etckeeper in /etc."
    etckeeper init
  fi
  # Commit any pending changes (idempotent: no-op when the tree is clean).
  if etckeeper unclean 2>/dev/null; then
    log "Committing current /etc state."
    etckeeper commit "etckeeper-setup.sh: initial/baseline commit" || warn "Nothing to commit."
  else
    log "/etc working tree is clean; nothing to commit."
  fi
}

install_units() {
  [[ -r "${PATH_UNIT_SRC}" ]] || die "etc-watch.path source not readable: ${PATH_UNIT_SRC}"
  install -D -m 0644 "${PATH_UNIT_SRC}" "${PATH_UNIT}"
  log "Installed ${PATH_UNIT}"

  # Serializing wrapper: concurrent etckeeper runs (etc-watch.path commit, daily
  # autocommit, apt's own DPkg hook) raced on /etc/.git/index.lock and silently
  # dropped commits (quality-gate M2, fix-39). flock covers our units; the retry
  # loop covers invocations we cannot wrap (apt's hook holds index.lock directly).
  log "Writing ${SERIALIZE_WRAPPER}"
  cat >"${SERIALIZE_WRAPPER}" <<'EOS'
#!/usr/bin/env bash
# etckeeper-serialized.sh <cmd...> — run an etckeeper action under a host-wide
# lock, retrying on git index.lock collisions (M2, fix-39).
# flock serializes our own systemd units, but apt invokes etckeeper directly via
# its DPkg hook and holds /etc/.git/index.lock outside any lock we control —
# so collisions are retried with backoff instead of dropping the commit.
# Exit 0 also covers "nothing to commit" (etckeeper exits 1). Exit 75 = still
# colliding after all retries (EX_TEMPFAIL) so the unit lands in failed state.
set -u
for i in 1 2 3 4 5; do
  out=$(/usr/bin/flock -w 120 /run/lock/etckeeper.lock "$@" 2>&1); rc=$?
  if printf "%s" "$out" | grep -q "index.lock"; then
    sleep $((i * 3)); continue
  fi
  printf "%s\n" "$out"
  [ "$rc" -le 1 ] && exit 0 || exit "$rc"
done
printf "%s\n" "$out"; exit 75
EOS
  chmod 0755 "${SERIALIZE_WRAPPER}"

  # Companion service the .path activates. Written here so the two always match.
  log "Writing companion ${COMMIT_SERVICE}"
  cat >"${COMMIT_SERVICE}" <<UNIT
# etckeeper-commit.service — commit /etc when etc-watch.path fires.
# Auto-generated by etckeeper-setup.sh. Activated by etc-watch.path.
# Serialized + retried via etckeeper-serialized.sh (M2, fix-39).
[Unit]
Description=Commit /etc changes with etckeeper
Documentation=https://etckeeper.branchable.com/

[Service]
Type=oneshot
ExecStart=${SERIALIZE_WRAPPER} /usr/bin/etckeeper commit "auto: /etc change"
# \`etckeeper commit\` exits non-zero when there's nothing to commit; that's fine.
SuccessExitStatus=0 1
UNIT

  # The distro's daily autocommit (etckeeper.timer -> etckeeper.service) is the
  # other systemd-side racer; point it at the same wrapper.
  log "Writing ${DAILY_DROPIN_DIR}/serialize.conf"
  mkdir -p "${DAILY_DROPIN_DIR}"
  cat >"${DAILY_DROPIN_DIR}/serialize.conf" <<DROPIN
# Serialize the daily autocommit against all other etckeeper invocations
# (etc-watch.path commits AND apt DPkg-hook runs) — M2, fix-39.
[Service]
ExecStart=
ExecStart=${SERIALIZE_WRAPPER} /etc/etckeeper/daily
DROPIN

  systemctl daemon-reload
  log "Enabling etc-watch.path."
  systemctl enable --now etc-watch.path
}

main() {
  require_root
  skip_on_synology
  install_etckeeper
  install_conf
  init_repo
  install_units
  log "Done. /etc is versioned and auto-commits on change."
  warn "Verify with: systemctl status etc-watch.path  &&  ( cd /etc && git log --oneline | head )"
}

main "$@"

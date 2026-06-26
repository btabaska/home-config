#!/usr/bin/env bash
#
# export-manifests.sh — snapshot everything needed to rebuild THIS host into the
#                       control repo, then regenerate the human-readable inventory.
#
# What it captures into hosts/<hostname>/ (idempotent — overwrites each run):
#   - Explicitly-installed packages (per distro):
#       Arch/CachyOS : pacman -Qqe  (+ AUR/foreign packages via pacman -Qqm)
#       Ubuntu/Debian: apt-mark showmanual
#   - flatpak applications (if flatpak present)
#   - Pinned container image tags (grep 'image:' across /opt/stacks)
#   - crontabs: `crontab -l` per user + a listing of /etc/cron.d
#   - systemd timers (system) + user timer unit listing (~/.config/systemd/user)
#   Then calls gen-inventory-md.sh to refresh configs/inventory/inventory.md.
#
# Designed for a weekly systemd timer (export-manifests.timer). Commit the
# resulting hosts/<hostname>/ files so the box is reproducible from git.
#
# Optional env:
#   REPO_ROOT=/path/to/foss-setup     # defaults to two levels up from this script
#   STACKS_DIR=/opt/stacks            # where compose stacks live
#   NTFY_URL=https://ntfy.example/inventory   # pinged on failure (optional)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
STACKS_DIR="${STACKS_DIR:-/opt/stacks}"
NTFY_URL="${NTFY_URL:-}"

HOST="$(hostname -s)"
OUT_DIR="${REPO_ROOT}/hosts/${HOST}"

log()  { printf '%s [export-manifests] %s\n' "$(date -Is)" "$*"; }
warn() { printf '%s [export-manifests][!] %s\n' "$(date -Is)" "$*" >&2; }

# Ping ntfy on any failure so a silent weekly job can't rot unnoticed.
on_error() {
  local rc=$?
  warn "FAILED (exit ${rc}) on host ${HOST}."
  if [[ -n "${NTFY_URL}" ]]; then
    curl -fsS -H "Title: export-manifests FAILED on ${HOST}" \
         -H "Priority: high" -H "Tags: warning" \
         -d "export-manifests.sh exited ${rc}. Check journalctl -u export-manifests.service." \
         "${NTFY_URL}" >/dev/null 2>&1 || true
  fi
  exit "${rc}"
}
trap on_error ERR

mkdir -p "${OUT_DIR}"
log "Writing manifests to ${OUT_DIR}"

# --- Package manifests (distro-aware) --------------------------------------------
if command -v pacman >/dev/null 2>&1; then
  log "Arch/CachyOS detected: exporting pacman package lists."
  # Explicitly-installed (everything you asked for, repo + AUR).
  pacman -Qqe > "${OUT_DIR}/pkglist.pacman-explicit.txt"
  # Foreign/AUR-only subset (not in sync DBs) — install these via your AUR helper.
  pacman -Qqm > "${OUT_DIR}/pkglist.aur.txt"
elif command -v apt-mark >/dev/null 2>&1; then
  log "Ubuntu/Debian detected: exporting apt manual-install list."
  apt-mark showmanual > "${OUT_DIR}/pkglist.apt-manual.txt"
else
  warn "No supported package manager (pacman/apt) found; skipping package manifest."
fi

# --- Flatpak ---------------------------------------------------------------------
if command -v flatpak >/dev/null 2>&1; then
  log "Exporting flatpak application list."
  flatpak list --app --columns=application,version,branch,origin > "${OUT_DIR}/flatpak.txt" 2>/dev/null || true
fi

# --- Pinned container image tags -------------------------------------------------
if [[ -d "${STACKS_DIR}" ]]; then
  log "Collecting pinned compose image tags from ${STACKS_DIR}."
  # Grep the literal pinned tags so drift from the repo is visible at a glance.
  grep -rhoE '^[[:space:]]*image:[[:space:]]*\S+' "${STACKS_DIR}" 2>/dev/null \
    | sed -E 's/^[[:space:]]*image:[[:space:]]*//' \
    | sort -u > "${OUT_DIR}/compose-images.txt" || true
else
  warn "Stacks dir ${STACKS_DIR} not found; skipping compose image tags."
fi

# --- Cron ------------------------------------------------------------------------
log "Collecting crontabs."
: > "${OUT_DIR}/crontabs.txt"
# Per-user crontabs (best-effort; needs privileges to read others').
if command -v getent >/dev/null 2>&1; then
  while IFS=: read -r user _ uid _ _ _ shell; do
    # Real login users only (skip system accounts / nologin shells).
    [[ "${uid}" -ge 1000 || "${user}" == "root" ]] || continue
    case "${shell}" in */nologin|*/false) continue;; esac
    if out="$(crontab -l -u "${user}" 2>/dev/null)"; then
      printf '### user: %s\n%s\n\n' "${user}" "${out}" >> "${OUT_DIR}/crontabs.txt"
    fi
  done < <(getent passwd)
fi
# System cron drop-ins.
ls -1 /etc/cron.d 2>/dev/null > "${OUT_DIR}/cron.d-listing.txt" || true

# --- systemd timers --------------------------------------------------------------
log "Collecting systemd timers."
systemctl list-timers --all --no-pager > "${OUT_DIR}/systemd-timers.txt" 2>/dev/null || true
# User-level units for the invoking (non-root) user, if any.
USER_HOME="$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)"
if [[ -n "${USER_HOME}" && -d "${USER_HOME}/.config/systemd/user" ]]; then
  ls -1 "${USER_HOME}/.config/systemd/user" > "${OUT_DIR}/systemd-user-units.txt" 2>/dev/null || true
fi

# --- Regenerate the readable inventory -------------------------------------------
if [[ -x "${SCRIPT_DIR}/gen-inventory-md.sh" ]]; then
  log "Regenerating inventory.md."
  "${SCRIPT_DIR}/gen-inventory-md.sh"
else
  warn "gen-inventory-md.sh not executable/found; skipping inventory.md refresh."
fi

log "Done. Review + commit ${OUT_DIR} to keep ${HOST} reproducible."

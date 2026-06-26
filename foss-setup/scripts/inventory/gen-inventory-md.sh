#!/usr/bin/env bash
#
# gen-inventory-md.sh — render a readable what/where/version/status table at
#                       configs/inventory/inventory.md from the manifests that
#                       export-manifests.sh wrote under hosts/<hostname>/.
#
# Idempotent: regenerates the whole file each run. Called by export-manifests.sh
# (and runnable standalone). Commit the result so the inventory tracks reality.
#
# Optional env:
#   REPO_ROOT=/path/to/foss-setup    # defaults to two levels up from this script
#   STACKS_DIR=/opt/stacks           # used to count running/compose services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
STACKS_DIR="${STACKS_DIR:-/opt/stacks}"

HOST="$(hostname -s)"
HOST_DIR="${REPO_ROOT}/hosts/${HOST}"
OUT="${REPO_ROOT}/configs/inventory/inventory.md"

log() { printf '%s [gen-inventory-md] %s\n' "$(date -Is)" "$*"; }

mkdir -p "$(dirname "${OUT}")"

# Helpers ------------------------------------------------------------------------
# Count non-empty, non-comment lines in a file (0 if missing).
count_lines() {
  local f="$1"
  [[ -r "${f}" ]] || { printf '0'; return; }
  grep -cvE '^\s*(#|$)' "${f}" 2>/dev/null || printf '0'
}

os_pretty() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    printf '%s' "${PRETTY_NAME:-unknown}"
  else
    printf 'unknown'
  fi
}

kernel="$(uname -r 2>/dev/null || echo unknown)"
generated_at="$(date -Is)"

# Counts from manifests (fall back gracefully if a file is absent) ---------------
pac_explicit="${HOST_DIR}/pkglist.pacman-explicit.txt"
aur_list="${HOST_DIR}/pkglist.aur.txt"
apt_manual="${HOST_DIR}/pkglist.apt-manual.txt"
flatpak_list="${HOST_DIR}/flatpak.txt"
compose_images="${HOST_DIR}/compose-images.txt"
timers_file="${HOST_DIR}/systemd-timers.txt"

if [[ -r "${apt_manual}" ]]; then
  pkg_label="apt manual"
  pkg_count="$(count_lines "${apt_manual}")"
elif [[ -r "${pac_explicit}" ]]; then
  pkg_label="pacman explicit"
  pkg_count="$(count_lines "${pac_explicit}")"
else
  pkg_label="packages"
  pkg_count="n/a"
fi
aur_count="$(count_lines "${aur_list}")"
flatpak_count=$(( $(count_lines "${flatpak_list}") ))
# flatpak.txt may have a header row; subtract 1 if present.
[[ -r "${flatpak_list}" && "${flatpak_count}" -gt 0 ]] && flatpak_count=$(( flatpak_count - 1 ))
[[ "${flatpak_count}" -lt 0 ]] && flatpak_count=0
image_count="$(count_lines "${compose_images}")"

running_containers="n/a"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  running_containers="$(docker ps -q 2>/dev/null | wc -l | tr -d ' ')"
fi

active_timers="n/a"
if command -v systemctl >/dev/null 2>&1; then
  active_timers="$(systemctl list-timers --no-legend 2>/dev/null | wc -l | tr -d ' ')"
fi

# Emit the markdown -------------------------------------------------------------
log "Writing ${OUT}"
{
  cat <<EOF
# Inventory — ${HOST}

> **Auto-generated** by \`scripts/inventory/gen-inventory-md.sh\` (invoked nightly/
> weekly by \`export-manifests.sh\` via \`export-manifests.timer\`).
> **Do not edit by hand** — your changes will be overwritten. Adjust the generator
> or the source manifests under \`hosts/${HOST}/\` instead.
>
> Generated: ${generated_at}

## Host

| what | where | version | status |
|------|-------|---------|--------|
| OS | ${HOST} | $(os_pretty) | active |
| Kernel | ${HOST} | ${kernel} | active |

## Software & services

| what | where | version | status |
|------|-------|---------|--------|
| ${pkg_label} packages | \`hosts/${HOST}/\` | ${pkg_count} pkgs | tracked |
| AUR/foreign packages | \`hosts/${HOST}/pkglist.aur.txt\` | ${aur_count} pkgs | tracked |
| Flatpak apps | \`hosts/${HOST}/flatpak.txt\` | ${flatpak_count} apps | tracked |
| Compose images (pinned) | \`${STACKS_DIR}\` | ${image_count} images | pinned |
| Running containers | docker | ${running_containers} up | $( [[ "${running_containers}" == "0" ]] && echo "idle" || echo "active" ) |
| systemd timers | \`hosts/${HOST}/systemd-timers.txt\` | ${active_timers} active | scheduled |

## Pinned container images

| image:tag | source |
|-----------|--------|
EOF

  if [[ -r "${compose_images}" ]]; then
    while IFS= read -r img; do
      [[ -n "${img}" ]] || continue
      printf '| `%s` | %s |\n' "${img}" "${STACKS_DIR}"
    done < "${compose_images}"
  else
    printf '| _no compose-images.txt yet — run export-manifests.sh_ | — |\n'
  fi

  cat <<EOF

---

_See \`hosts/${HOST}/\` for the raw manifests (package lists, crontabs, timers).
Restore procedure: \`configs/inventory/restore-runbook-template.md\`._
EOF
} > "${OUT}"

log "Done: ${OUT}"

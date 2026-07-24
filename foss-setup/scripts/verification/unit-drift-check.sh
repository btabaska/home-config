#!/usr/bin/env bash
# unit-drift-check.sh — fix-43 (L86 class): hand-copied systemd unit files must
# stay byte-identical to the repo copy on every host that runs them. The
# ansible-pull units are NOT converged by the pull flow itself (site.yml does
# not install them — see the timer's own header), so drift here is silent until
# it bites (the 2026-07-15 stale-playbook-path missed run, L6).
#
# glue-13 extended coverage to the rig's other hand-copied foss-setup host units
# (gpu-power-tune.service, the export-manifests service+timer). Nothing converges
# these either — see configs/host/rig/README.md for the full unit->source map.
# Only STATIC foss-setup mirrors are checked here: ansible-managed backup units
# (restic-backup, ntfy-notify@) are templated + self-heal daily, and fleet-mcp /
# the ollama override are owned by the separate local-ai-tooling repo.
#
# Usage: unit-drift-check.sh <repo-checkout-root>
# Prints UNIT-DRIFT-OK, or lists each mismatch and exits 1. An unreachable rig
# counts as drift (fail-loud beats silently skipping the comparison).
set -u
R="${1:?usage: unit-drift-check.sh <repo-checkout-root>}"
fail=0

check_local() { # <deployed-path> <repo-relative-path>
  cmp -s "$1" "$R/$2" || { echo "DRIFT mini:$1 != repo/$2"; fail=1; }
}
check_rig() { # <deployed-path> <repo-relative-path>
  ssh -o BatchMode=yes -o ConnectTimeout=10 rig cat "$1" 2>/dev/null \
    | cmp -s - "$R/$2" || { echo "DRIFT rig:$1 != repo/$2"; fail=1; }
}

check_local /etc/systemd/system/ansible-pull.service foss-setup/configs/ansible/ansible-pull.service
check_local /etc/systemd/system/ansible-pull.timer   foss-setup/configs/ansible/ansible-pull.timer
check_rig   /etc/systemd/system/ansible-pull.service foss-setup/configs/ansible/ansible-pull.service
check_rig   /etc/systemd/system/ansible-pull.timer   foss-setup/configs/ansible/ansible-pull.timer

# glue-13: the rig's other hand-copied foss-setup host units. Canonical source
# for each is pinned in configs/host/rig/README.md (gpu-power-tune + the timer
# live under scripts/, so they are NOT re-copied into configs/host/rig/).
check_rig   /etc/systemd/system/gpu-power-tune.service   foss-setup/scripts/gaming/gpu-power-tune.service
check_rig   /etc/systemd/system/export-manifests.service foss-setup/configs/host/rig/export-manifests.service
check_rig   /etc/systemd/system/export-manifests.timer   foss-setup/scripts/inventory/export-manifests.timer

# glue-14: the rig Immich-ML night-window units + driver script (foss-setup static
# mirror under configs/host/rig/immich-ml/). Nothing converges these — see the README.
check_rig   /usr/local/bin/immich-ml-window.sh              foss-setup/configs/host/rig/immich-ml/immich-ml-window.sh
check_rig   /etc/systemd/system/immich-ml-window@.service   foss-setup/configs/host/rig/immich-ml/immich-ml-window@.service
check_rig   /etc/systemd/system/immich-ml-window-on.timer   foss-setup/configs/host/rig/immich-ml/immich-ml-window-on.timer
check_rig   /etc/systemd/system/immich-ml-window-off.timer  foss-setup/configs/host/rig/immich-ml/immich-ml-window-off.timer

[ "$fail" -eq 0 ] && echo UNIT-DRIFT-OK || exit 1

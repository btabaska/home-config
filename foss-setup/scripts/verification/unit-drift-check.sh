#!/usr/bin/env bash
# unit-drift-check.sh — fix-43 (L86 class): hand-copied systemd unit files must
# stay byte-identical to the repo copy on every host that runs them. The
# ansible-pull units are NOT converged by the pull flow itself (site.yml does
# not install them — see the timer's own header), so drift here is silent until
# it bites (the 2026-07-15 stale-playbook-path missed run, L6).
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

[ "$fail" -eq 0 ] && echo UNIT-DRIFT-OK || exit 1

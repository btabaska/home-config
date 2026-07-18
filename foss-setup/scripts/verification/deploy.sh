#!/usr/bin/env bash
# Deploy the verification suite to mini:/opt/verification — reproducibly, from git.
#
# WHY THIS SCRIPT EXISTS (quality-gate M38/M53)
# ---------------------------------------------
# The suite is NOT self-contained under foss-setup/verification/. Four scripts it
# runs live canonically elsewhere in the repo and are copied into
# /opt/verification/bin at deploy time:
#   scripts/gaming/mc-status-ping.py             -> checks.d/rig.yaml  playit-java-public
#   scripts/gaming/mc-bedrock-ping.py            -> checks.d/rig.yaml  playit-bedrock-public
#   scripts/ai/wiki-rag-sync.py                  -> wiki-rag-sync.service ExecStart
#   scripts/media/window-maint-unpackerr-rclone.sh -> window-maint units
# The old README deploy — `rsync -a --delete foss-setup/verification/ -> /opt/
# verification/` — would DELETE all four (they are not under verification/),
# breaking two live checks and a service. This script assembles a COMPLETE
# staging tree (verification/ + those four) so `--delete` is safe, strips macOS
# ._* / __pycache__ / *.pyc junk, and REFUSES to deploy if any /opt/verification/
# bin/<x> a check or unit references is not in the tree.
#
# Usage:  scripts/verification/deploy.sh            # deploy
#         MINI=othername scripts/verification/deploy.sh
# Idempotent — safe to re-run. Requires rsync + ssh; mini has passwordless sudo.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # foss-setup/
SRC="$REPO/verification"
MINI="${MINI:-mini}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Scripts that live outside verification/ but run from /opt/verification/bin.
# Keep this list in sync with the header comment above.
EXTERNAL_BIN=(
  "scripts/gaming/mc-status-ping.py"
  "scripts/gaming/mc-bedrock-ping.py"
  "scripts/ai/wiki-rag-sync.py"
  "scripts/media/window-maint-unpackerr-rclone.sh"
)

echo "==> assembling staging tree from $SRC + ${#EXTERNAL_BIN[@]} external scripts"
rsync -a --exclude '._*' --exclude '__pycache__' --exclude '*.pyc' "$SRC"/ "$STAGE"/
for rel in "${EXTERNAL_BIN[@]}"; do
  [ -f "$REPO/$rel" ] || { echo "FATAL: external script missing from repo: $rel"; exit 1; }
  install -m 755 "$REPO/$rel" "$STAGE/bin/$(basename "$rel")"
done

echo "==> guard: every /opt/verification/bin/<x> referenced by a check or unit is present"
missing=0
refs="$(grep -rhoE '/opt/verification/bin/[A-Za-z0-9._-]+' "$SRC/checks.d" "$SRC/systemd" 2>/dev/null | sort -u || true)"
for r in $refs; do
  b="$(basename "$r")"
  if [ ! -e "$STAGE/bin/$b" ]; then echo "  MISSING: bin/$b  (referenced by $r)"; missing=1; fi
done
[ "$missing" = 0 ] || { echo "FATAL: staging tree incomplete — refusing to deploy (would break a check)"; exit 1; }
echo "    ok — $(echo "$refs" | grep -c . ) referenced bin scripts all present"

echo "==> pushing to $MINI:/tmp/verification-deploy/ (clean tree, no junk)"
rsync -a --delete "$STAGE"/ "$MINI":/tmp/verification-deploy/

echo "==> syncing into /opt/verification and (re)installing systemd units"
# NOTE: no --exclude on this --delete apply, so host-side ._*/__pycache__ junk is
# removed. The staging tree is already clean, so nothing legit is deleted.
ssh "$MINI" '
  set -e
  sudo rsync -a --delete /tmp/verification-deploy/ /opt/verification/
  sudo chown -R root:root /opt/verification
  # Normalize modes so the root-owned tree stays readable/traversable by the
  # btabaska RUNNER regardless of source-side perms. A 600 file in the repo
  # working tree (nas/rig.containers) + chown root:root silently broke the
  # coverage checks with "Permission denied" — the runner is btabaska, not root.
  sudo find /opt/verification -type d -exec chmod 755 {} +
  sudo find /opt/verification -type f -exec chmod 644 {} +
  sudo chmod 755 /opt/verification/bin/*.sh /opt/verification/bin/*.py
  sudo install -d -o btabaska -g btabaska /var/lib/verification
  for u in verification verification-quick verification-fast; do
    sudo install -m 644 /opt/verification/systemd/$u.service /etc/systemd/system/
    sudo install -m 644 /opt/verification/systemd/$u.timer   /etc/systemd/system/
  done
  # The daily dead-man ping now lives in the base verification.service
  # (${VERIFY_DAILY_PING_URL}); retire the old etckeeper-only drop-in so there
  # is ONE source of truth (M53). Harmless if it was already removed.
  sudo rm -f /etc/systemd/system/verification.service.d/healthchecks.conf
  sudo rmdir --ignore-fail-on-non-empty /etc/systemd/system/verification.service.d 2>/dev/null || true
  sudo systemctl daemon-reload
  sudo systemctl enable --now verification.timer verification-quick.timer verification-fast.timer >/dev/null
  rm -rf /tmp/verification-deploy
  echo "    deployed."
'
echo "==> done. (env: /etc/verification/env holds NTFY_TOKEN + VERIFY_*_PING_URL etc., out of git — see systemd/env.example)"

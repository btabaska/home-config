#!/usr/bin/env bash
# ==============================================================================
# rclone-manual-copy.sh — the ONE scheduled rclone transfer (manual lane only)
# ==============================================================================
# Phase 2. Runs ON THE NAS (DS920+) on a schedule (e.g. every 15 min).
#
# This is the SINGLE scheduled rclone transfer in the whole system. It exists
# ONLY for the non-*arr / manual downloads lane:
#
#   Seedbox Deluge `manual` label  ->  /home/hd34/btabaska/files/manual
#   this job copies it down to      ->  /volume1/media/manual
#
# !!! IT MUST NEVER TOUCH THE *ARR LABEL FOLDERS !!!
# *arr-managed media (tv/movies/music/books) arrives via the LIVE rclone mount +
# the *arr import step — NOT via a scheduled copy. This job is scoped strictly to
# the `manual/` subtree so the two lanes never overlap or double-import.
#
# COPY (not move/sync): copy KEEPS the file seeding on the seedbox and is
# re-run-safe (idempotent — only new/changed files transfer). --min-age 5m skips
# files still being written. --transfers 4 bounds concurrency.
#
# THROWAWAY VARIANT (non-seeding public grabs you don't care to seed): use
#   rclone move ... --min-age 5m --transfers 4
# `move` deletes the source after a successful transfer (stops seeding, frees
# seedbox space). Only use `move` for files you deliberately do NOT want to seed.
#
# DSM SETUP: Control Panel -> Task Scheduler -> Create -> Scheduled Task ->
#   User-defined script, User = root, repeat every 15 minutes,
#   Command = /volume1/scripts/media/rclone-manual-copy.sh
# On a systemd host instead, use a .service + .timer pair.
#
# Docs: https://rclone.org/commands/rclone_copy/
# ==============================================================================
set -euo pipefail

RCLONE="${RCLONE:-/usr/local/bin/rclone}"               # TODO: adjust (`which rclone`)
RCLONE_CONF="${RCLONE_CONF:-/root/.config/rclone/rclone.conf}"
SRC="${SRC:-seedbox:/home/hd34/btabaska/files/manual}"  # manual label folder ONLY
DST="${DST:-/volume1/media/manual}"
LOG="${LOG:-/var/log/rclone-manual.log}"

mkdir -p "$DST"

exec "$RCLONE" copy "$SRC" "$DST" \
  --config "$RCLONE_CONF" \
  --min-age 5m \
  --transfers 4 \
  --log-file "$LOG" \
  --log-level INFO

#!/usr/bin/env bash
#
# immich-go-import.sh — import a mirrorless-camera SD card into Immich via immich-go.
#                       Phase 2. Idempotent (immich-go dedups by checksum on the server).
#
# WHY THIS EXISTS: a camera SD card has NO auto-backup — nothing pulls photos off
# it the way a phone auto-uploads. The workflow is: copy the card off to an SSD
# first (so you have the originals), THEN import that copy into Immich. This script
# does the import step; see immich-go-import.md for the full SD → SSD → Immich flow.
#
# What it does:
#   1. Validates env (server URL, API key, card/source folder).
#   2. Runs `immich-go upload from-folder` with --manage-raw-jpeg so a RAW+JPEG
#      pair shot together is STACKED as one asset (not two duplicates).
#   3. Re-running is safe: immich-go skips assets already on the server (checksum).
#
# Docs:
#   immich-go:        https://github.com/simulot/immich-go
#   upload from-folder: https://github.com/simulot/immich-go/blob/main/docs/upload.md
#   Immich API keys:  https://docs.immich.app/features/command-line-interface (and Account Settings)
#
# Usage:
#   IMMICH_SERVER=https://photos.example.com \
#   IMMICH_API_KEY=xxxxxxxx \
#   CARD_PATH=/mnt/ssd/ingest/2026-06-26 \
#     ./immich-go-import.sh
#
#   # dry-run first to see what WOULD upload:
#   DRY_RUN=1 CARD_PATH=... ./immich-go-import.sh

set -euo pipefail

# --- Configuration via environment ----------------------------------------------
IMMICH_SERVER="${IMMICH_SERVER:-}"     # e.g. https://photos.example.com (your Caddy URL or http://NAS:2283)
IMMICH_API_KEY="${IMMICH_API_KEY:-}"   # Immich → Account Settings → API Keys
CARD_PATH="${CARD_PATH:-}"             # the COPIED-OFF card folder on the SSD (not the live card)
DRY_RUN="${DRY_RUN:-0}"                # 1 = preview only, upload nothing

log() { printf '%s [immich-go-import] %s\n' "$(date -Is)" "$*"; }
die() { printf '%s [immich-go-import] ERROR: %s\n' "$(date -Is)" "$*" >&2; exit 1; }

# --- Preconditions --------------------------------------------------------------
command -v immich-go >/dev/null 2>&1 || die "immich-go not installed — see immich-go-import.md (release binary)."
[[ -n "${IMMICH_SERVER}" ]] || die "IMMICH_SERVER is required (e.g. https://photos.example.com)."
[[ -n "${IMMICH_API_KEY}" ]] || die "IMMICH_API_KEY is required (Immich → Account Settings → API Keys)."
[[ -n "${CARD_PATH}" ]]    || die "CARD_PATH is required (the copied-off card folder on your SSD)."
[[ -d "${CARD_PATH}" ]]    || die "CARD_PATH is not a directory: ${CARD_PATH}"

# --- Build args -----------------------------------------------------------------
# --manage-raw-jpeg=StackCoverRaw : keep both files but stack them with the RAW as the
#   cover/primary. Chosen for a mirrorless/RAW-editing workflow (immich-go's own docs
#   recommend StackCoverRaw "for photographers who edit RAW"). Switch to StackCoverJPG
#   if you'd rather the more universally-viewable JPEG be the cover asset.
ARGS=(
  upload from-folder
  --server "${IMMICH_SERVER}"
  --api-key "${IMMICH_API_KEY}"
  --manage-raw-jpeg StackCoverRaw
  --manage-burst Stack
  --recursive
)
[[ "${DRY_RUN}" == "1" ]] && { ARGS+=( --dry-run ); log "DRY-RUN: nothing will be uploaded."; }

# --- Import (idempotent: server-side checksum dedup skips existing assets) -------
log "Importing ${CARD_PATH} -> ${IMMICH_SERVER}"
immich-go "${ARGS[@]}" "${CARD_PATH}"
log "Done. Re-running is safe; already-uploaded assets are skipped by checksum."

# --- Optional: continuous ingest from a staging folder --------------------------
# NOTE: immich-go has NO --watch flag; it is one-shot only (re-running is cheap and
# idempotent). There are two supported ways to get continuous ingest:
#
# 1) Re-run THIS script on a schedule (recommended — keeps the same stacking config).
#    cron example (every 15 min):
#      */15 * * * *  IMMICH_SERVER=https://photos.example.com IMMICH_API_KEY=xxxx \
#                    CARD_PATH=/mnt/ssd/ingest/staging /opt/scripts/media/immich-go-import.sh
#    or a systemd timer that runs this script (see *.timer examples in scripts/backup/).
#
# 2) Use the OFFICIAL Immich CLI (a DIFFERENT tool from immich-go) which DOES watch:
#      immich upload --watch /mnt/ssd/ingest/staging
#    Docs: https://docs.immich.app/features/command-line-interface
#    (The official CLI does not do immich-go's RAW/JPEG stacking, so prefer option 1.)

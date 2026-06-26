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
# --manage-raw-jpeg=StackCoverJPG : keep both files but stack them, JPEG as cover.
ARGS=(
  upload from-folder
  --server "${IMMICH_SERVER}"
  --api-key "${IMMICH_API_KEY}"
  --manage-raw-jpeg StackCoverJPG
  --manage-burst Stack
  --recursive
)
[[ "${DRY_RUN}" == "1" ]] && { ARGS+=( --dry-run ); log "DRY-RUN: nothing will be uploaded."; }

# --- Import (idempotent: server-side checksum dedup skips existing assets) -------
log "Importing ${CARD_PATH} -> ${IMMICH_SERVER}"
immich-go "${ARGS[@]}" "${CARD_PATH}"
log "Done. Re-running is safe; already-uploaded assets are skipped by checksum."

# --- Optional: WATCH a staging folder (continuous ingest) -----------------------
# Instead of a one-shot import you can have immich-go watch a staging dir and
# upload new files as they land (e.g. a card-copy script drops files there):
#   immich-go upload from-folder --server "$IMMICH_SERVER" --api-key "$IMMICH_API_KEY" \
#     --manage-raw-jpeg StackCoverJPG --watch /mnt/ssd/ingest/staging

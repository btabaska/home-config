#!/usr/bin/env bash
#
# restic-backup.sh — Tier 1 off-site backup of a Linux host (Ubuntu / CachyOS)
#                    to Backblaze B2 via restic.
#
# What it does (idempotent — safe to re-run, designed for cron/systemd timer):
#   1. Loads B2 creds + repo settings from an env file (NOT hardcoded).
#   2. Initializes the restic repo on first run (no-op if it already exists).
#   3. Backs up the configured paths with sensible excludes.
#   4. Applies a forget+prune retention policy.
#   5. Runs a lightweight integrity check.
#
# Docs:
#   restic + B2:      https://www.backblaze.com/docs/cloud-storage-integrate-restic-with-backblaze-b2
#   restic manual:    https://restic.readthedocs.io/en/stable/
#   retention/forget: https://restic.readthedocs.io/en/stable/060_forget.html
#
# Setup (once per host):
#   sudo install -d -m 0700 /etc/restic
#   sudo cp restic-backup.env.example /etc/restic/b2.env   # then edit, chmod 600
#   openssl rand -base64 48 | sudo tee /etc/restic/password >/dev/null && sudo chmod 600 /etc/restic/password
#   # >>> Save that password in your password manager AND print it. No password = no restore. <<<
#
# Run:  sudo ENV_FILE=/etc/restic/b2.env ./restic-backup.sh
# Cron: 30 2 * * *  root  ENV_FILE=/etc/restic/b2.env /opt/scripts/restic-backup.sh >> /var/log/restic-backup.log 2>&1

set -euo pipefail

# --- Configuration via environment (override before calling) ---------------------
# Path to the env file that exports B2 + restic variables (see restic-backup.env.example).
ENV_FILE="${ENV_FILE:-/etc/restic/b2.env}"

# Space-separated list of paths to back up. Override BACKUP_PATHS in the env file or here.
# Defaults cover typical Tier 1 data on a Linux workstation/server.
DEFAULT_BACKUP_PATHS="/home /etc /opt /var/lib/docker/volumes /srv"

# Retention policy (snapshots to keep). Override in the env file if desired.
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
KEEP_MONTHLY="${KEEP_MONTHLY:-12}"
KEEP_YEARLY="${KEEP_YEARLY:-3}"

# --- Load secrets / settings -----------------------------------------------------
if [[ ! -r "${ENV_FILE}" ]]; then
  echo "ERROR: env file not readable: ${ENV_FILE}" >&2
  echo "       Create it from restic-backup.env.example (chmod 600)." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${ENV_FILE}"

# Allow BACKUP_PATHS to come from the env file; fall back to defaults.
BACKUP_PATHS="${BACKUP_PATHS:-${DEFAULT_BACKUP_PATHS}}"

# Sanity-check required restic variables (sourced from the env file).
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY must be set in ${ENV_FILE}}"
: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE must be set in ${ENV_FILE}}"
# B2 S3-compatible creds (AWS_* names) OR native B2_* — the env file sets whichever you use.

command -v restic >/dev/null 2>&1 || { echo "ERROR: restic not installed." >&2; exit 1; }

HOSTNAME_TAG="$(hostname -s)"
log() { printf '%s [restic-backup] %s\n' "$(date -Is)" "$*"; }

# --- 1. Initialize repo if missing (idempotent) ----------------------------------
# `restic cat config` succeeds only if the repo already exists & is reachable.
if restic cat config >/dev/null 2>&1; then
  log "Repository already initialized."
else
  log "Repository not found — initializing: ${RESTIC_REPOSITORY}"
  restic init
fi

# --- 2. Back up ------------------------------------------------------------------
log "Starting backup of: ${BACKUP_PATHS}"
# shellcheck disable=SC2086  # intentional word-splitting of the path list
restic backup ${BACKUP_PATHS} \
  --tag automated \
  --tag "host:${HOSTNAME_TAG}" \
  --one-file-system \
  --exclude-caches \
  --exclude '*.tmp' \
  --exclude '*.log' \
  --exclude '**/.cache' \
  --exclude '**/node_modules' \
  --exclude '**/.local/share/Trash' \
  --exclude '/home/*/.cache' \
  --exclude '/var/lib/docker/volumes/*/_data/**/*.sock'
log "Backup complete."

# --- 3. Retention: forget + prune ------------------------------------------------
log "Applying retention (d=${KEEP_DAILY} w=${KEEP_WEEKLY} m=${KEEP_MONTHLY} y=${KEEP_YEARLY})."
restic forget \
  --tag automated \
  --host "${HOSTNAME_TAG}" \
  --keep-daily   "${KEEP_DAILY}" \
  --keep-weekly  "${KEEP_WEEKLY}" \
  --keep-monthly "${KEEP_MONTHLY}" \
  --keep-yearly  "${KEEP_YEARLY}" \
  --prune
log "Retention applied."

# --- 4. Lightweight integrity check ---------------------------------------------
# Structural check only (fast). For a deep check, run `restic check --read-data-subset=10%`
# from a trusted machine on a schedule (it downloads data and costs B2 egress).
log "Running structural integrity check."
restic check
log "All done."

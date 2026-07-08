#!/usr/bin/env bash
#
# restic-backup.sh — Tier 1 off-site backup of a Linux host (Ubuntu / CachyOS)
#                    to Backblaze B2 via restic.
#
# What it does (idempotent — safe to re-run, designed for cron/systemd timer):
#   1. Loads B2 creds + repo settings from an env file (NOT hardcoded).
#   2. Initializes the restic repo on first run (no-op if it already exists).
#   3. Runs an optional PRE_BACKUP_SCRIPT hook (e.g. consistent DB dumps on mini).
#   4. Backs up the configured paths with sensible excludes
#      (+ per-host RESTIC_EXCLUDE_FILE, e.g. /etc/restic/excludes.txt).
#   5. Applies a forget retention policy daily; --prune once a week
#      (PRUNE_WEEKDAY, default Sunday) to keep B2 API churn low.
#   6. Runs a lightweight integrity check.
#
# Docs:
#   restic + B2:      https://www.backblaze.com/docs/cloud-storage-integrate-restic-with-backblaze-b2
#   restic manual:    https://restic.readthedocs.io/en/stable/
#   retention/forget: https://restic.readthedocs.io/en/stable/060_forget.html
#
# Setup (once per host):
#   sudo install -d -m 0700 /etc/restic
#   sudo cp restic-backup.env.example /etc/restic/env   # then edit, chmod 600
#   Password: either RESTIC_PASSWORD directly in the env file (0600 root — how
#   mini/rig are deployed) or RESTIC_PASSWORD_FILE pointing at /etc/restic/password.
#   # >>> Save that password in your password manager AND print it. No password = no restore. <<<
#
# Run:  sudo ENV_FILE=/etc/restic/env ./restic-backup.sh
# Prod: restic-backup.timer → restic-backup.service (OnFailure → ntfy-notify@)

set -euo pipefail

# --- Configuration via environment (override before calling) ---------------------
# Path to the env file with B2 + restic variables (see restic-backup.env.example).
# Plain KEY=VALUE lines are fine (set -a below exports them); `export KEY=...` too.
ENV_FILE="${ENV_FILE:-/etc/restic/env}"

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
# set -a: export everything the env file defines, whether or not it says `export`.
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# Allow BACKUP_PATHS to come from the env file; fall back to defaults.
BACKUP_PATHS="${BACKUP_PATHS:-${DEFAULT_BACKUP_PATHS}}"

# Sanity-check required restic variables (sourced from the env file).
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY must be set in ${ENV_FILE}}"
if [[ -z "${RESTIC_PASSWORD:-}" && -z "${RESTIC_PASSWORD_FILE:-}" ]]; then
  echo "ERROR: set RESTIC_PASSWORD or RESTIC_PASSWORD_FILE in ${ENV_FILE}" >&2
  exit 1
fi
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

# --- 2. Optional pre-backup hook (consistent DB dumps, etc.) ---------------------
# Set PRE_BACKUP_SCRIPT in the env file (mini: /opt/scripts/pre-backup-db-dumps.sh).
# A failing hook ABORTS the backup: better no snapshot than one with torn DB state.
if [[ -n "${PRE_BACKUP_SCRIPT:-}" ]]; then
  log "Running pre-backup hook: ${PRE_BACKUP_SCRIPT}"
  "${PRE_BACKUP_SCRIPT}"
  log "Pre-backup hook done."
fi

# --- 3. Back up ------------------------------------------------------------------
# Host-specific excludes (one pattern per line) via RESTIC_EXCLUDE_FILE, deployed
# from scripts/backup/excludes-<host>.txt to /etc/restic/excludes.txt.
EXCLUDE_FILE_ARGS=()
if [[ -n "${RESTIC_EXCLUDE_FILE:-}" ]]; then
  [[ -r "${RESTIC_EXCLUDE_FILE}" ]] || { echo "ERROR: RESTIC_EXCLUDE_FILE not readable: ${RESTIC_EXCLUDE_FILE}" >&2; exit 1; }
  EXCLUDE_FILE_ARGS=(--exclude-file "${RESTIC_EXCLUDE_FILE}")
fi

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
  --exclude '/var/lib/docker/volumes/*/_data/**/*.sock' \
  "${EXCLUDE_FILE_ARGS[@]}"
log "Backup complete."

# --- 4. Retention: forget daily, prune weekly ------------------------------------
# forget is cheap metadata work — do it every run. prune rewrites pack files and
# costs B2 API calls/egress — do it once a week (PRUNE_WEEKDAY: 1=Mon..7=Sun).
PRUNE_WEEKDAY="${PRUNE_WEEKDAY:-7}"
FORGET_ARGS=(
  --tag automated
  --host "${HOSTNAME_TAG}"
  --keep-daily   "${KEEP_DAILY}"
  --keep-weekly  "${KEEP_WEEKLY}"
  --keep-monthly "${KEEP_MONTHLY}"
)
# --keep-yearly 0 is rejected by restic; omit the flag to keep no yearly snapshots.
[[ "${KEEP_YEARLY}" -gt 0 ]] && FORGET_ARGS+=(--keep-yearly "${KEEP_YEARLY}")
if [[ "$(date +%u)" == "${PRUNE_WEEKDAY}" || "${FORCE_PRUNE:-0}" == "1" ]]; then
  FORGET_ARGS+=(--prune)
fi
log "Applying retention (d=${KEEP_DAILY} w=${KEEP_WEEKLY} m=${KEEP_MONTHLY} y=${KEEP_YEARLY}; prune day ${PRUNE_WEEKDAY})."
restic forget "${FORGET_ARGS[@]}"
log "Retention applied."

# --- 5. Lightweight integrity check ---------------------------------------------
# Structural check only (fast). For a deep check, run `restic check --read-data-subset=10%`
# from a trusted machine on a schedule (it downloads data and costs B2 egress).
log "Running structural integrity check."
restic check
log "All done."

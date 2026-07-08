#!/usr/bin/env bash
#
# restore-test.sh — prove a backup is RESTORABLE, not just that it ran.
#                   "A backup you have never restored is not a backup." Run monthly.
#
# Supports two backends:
#   restic    — restores the latest snapshot into a temp dir and verifies files exist.
#   borgmatic — extracts the latest archive into a temp dir and verifies files exist.
#
# Nothing is overwritten in place: everything is restored into a fresh mktemp dir,
# checked, then cleaned up. Read-only with respect to your live system and the repos.
#
# Docs:
#   restic restore:  https://restic.readthedocs.io/en/stable/050_restore.html
#   borg extract:    https://borgbackup.readthedocs.io/en/stable/usage/extract.html
#   borgmatic:       https://torsion.org/borgmatic/docs/how-to/extract-a-backup/
#
# Usage:
#   ENV_FILE=/etc/restic/env ./restore-test.sh restic
#   ./restore-test.sh borgmatic [/etc/borgmatic/config.yaml]

set -euo pipefail

BACKEND="${1:-}"
log()  { printf '%s [restore-test] %s\n' "$(date -Is)" "$*"; }
die()  { printf '%s [restore-test] ERROR: %s\n' "$(date -Is)" "$*" >&2; exit 1; }

[[ -n "${BACKEND}" ]] || die "usage: $0 <restic|borgmatic> [borgmatic-config]"

# Temp restore target, always cleaned up on exit (success or failure).
RESTORE_DIR="$(mktemp -d -t restore-test.XXXXXX)"
cleanup() { rm -rf "${RESTORE_DIR}"; }
trap cleanup EXIT

# Fail the test if fewer than this many files were restored (catches empty/partial restores).
MIN_FILES="${MIN_FILES:-1}"

verify_nonempty() {
  local dir="$1"
  local count
  count="$(find "${dir}" -type f 2>/dev/null | wc -l | tr -d ' ')"
  log "Restored ${count} file(s) into ${dir}"
  [[ "${count}" -ge "${MIN_FILES}" ]] || die "restore produced ${count} files (< ${MIN_FILES}); restore FAILED"
  log "Sample of restored files:"
  find "${dir}" -type f 2>/dev/null | head -n 5 || true
}

case "${BACKEND}" in
  restic)
    command -v restic >/dev/null 2>&1 || die "restic not installed"
    ENV_FILE="${ENV_FILE:-/etc/restic/env}"
    [[ -r "${ENV_FILE}" ]] || die "env file not readable: ${ENV_FILE}"
    # set -a: export everything the env file defines (plain KEY=VALUE files work).
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
    : "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY must be set in ${ENV_FILE}}"
    [[ -n "${RESTIC_PASSWORD:-}" || -n "${RESTIC_PASSWORD_FILE:-}" ]] \
      || die "set RESTIC_PASSWORD or RESTIC_PASSWORD_FILE in ${ENV_FILE}"

    log "Confirming repository is reachable..."
    restic cat config >/dev/null || die "cannot read repo config — check creds/endpoint"

    log "Restoring latest snapshot to ${RESTORE_DIR} ..."
    # 'latest' alone is the newest snapshot across ALL hosts; scope it to THIS host so
    # the comment holds. Non-destructive: restores into the mktemp RESTORE_DIR only.
    restic restore latest --host "$(hostname -s)" --target "${RESTORE_DIR}"
    verify_nonempty "${RESTORE_DIR}"
    log "restic restore test PASSED."
    ;;

  borgmatic)
    command -v borgmatic >/dev/null 2>&1 || die "borgmatic not installed"
    CONFIG="${2:-/etc/borgmatic/config.yaml}"
    [[ -r "${CONFIG}" ]] || die "borgmatic config not readable: ${CONFIG}"

    log "Finding the latest archive..."
    # `borgmatic rlist`/`list` prints archives; take the last (most recent) name.
    LATEST="$(borgmatic --config "${CONFIG}" list --last 1 2>/dev/null \
                | awk 'NF{name=$1} END{print name}')"
    [[ -n "${LATEST}" ]] || die "no archives found — has a backup run yet?"
    log "Latest archive: ${LATEST}"

    log "Extracting ${LATEST} to ${RESTORE_DIR} ..."
    borgmatic --config "${CONFIG}" extract \
      --archive "${LATEST}" \
      --destination "${RESTORE_DIR}"
    verify_nonempty "${RESTORE_DIR}"
    log "borgmatic restore test PASSED."
    ;;

  *)
    die "unknown backend '${BACKEND}' (expected: restic | borgmatic)"
    ;;
esac

log "Restore verification complete. Temp data cleaned up."

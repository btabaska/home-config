#!/usr/bin/env bash
#
# pre-backup-db-dumps.sh — consistent database dumps on mini, run by
# restic-backup.sh (PRE_BACKUP_SCRIPT) immediately before the restic snapshot.
#
# WHY: file-copying a live Postgres/MariaDB data dir is not a safe backup — the
# raw DB dirs (paperless-ngx/pgdata, wallabag/db, miniflux/db, healthchecks/db,
# forgejo/data/db) are EXCLUDED from restic (see excludes-mini.txt) and these
# dumps are backed up instead. Restore = create DB, `gunzip -c x.sql.gz | psql`
# (or mysql for wallabag).
#
# Dumps land in /opt/stacks/backups/db/ with FIXED filenames — restic snapshots
# provide the history, so no timestamped clutter and no local rotation needed.
#
# Container names/creds come from each stack's compose.yaml (all on this host):
#   paperless_db    postgres  -U paperless    db paperless
#   wallabag_db     mariadb   creds from the container's own MYSQL_* env
#   miniflux_db     postgres  -U miniflux     db miniflux
#   healthchecks_db postgres  -U healthchecks db healthchecks
#   forgejo_db      postgres  -U forgejo      db forgejo   (repos are on-disk
#                   under /opt/stacks/forgejo/data/forgejo and backed up as files)
#
# vaultwarden is NOT dumped here: its image ships no sqlite3 CLI, so a
# `.backup` via docker exec isn't trivial. Restic snapshots the live
# /opt/stacks/vaultwarden/data/db.sqlite3 instead (small, WAL-journaled) —
# acceptable for v1, FLAGGED: add a proper sqlite dump if the vault grows.
#
# Any failed or empty dump exits non-zero, which ABORTS the restic backup.

set -euo pipefail

OUT_DIR="${DB_DUMP_DIR:-/opt/stacks/backups/db}"
install -d -m 0700 "${OUT_DIR}"

log() { printf '%s [pre-backup-db-dumps] %s\n' "$(date -Is)" "$*"; }

# Write via a tmp file + atomic rename so a crashed dump never replaces a good one,
# and require a plausible minimum size to catch silently-empty dumps.
finish() { # finish <tmpfile> <dest> <min_bytes>
  local tmp="$1" dest="$2" min="$3" size
  size=$(stat -c%s "${tmp}")
  if [[ "${size}" -lt "${min}" ]]; then
    log "ERROR: $(basename "${dest}") is only ${size} bytes (< ${min}) — dump failed?"
    rm -f "${tmp}"
    return 1
  fi
  mv "${tmp}" "${dest}"
  log "OK: $(basename "${dest}") (${size} bytes)"
}

dump_pg() { # dump_pg <container> <user> <db> <outname>
  local container="$1" user="$2" db="$3" out="${OUT_DIR}/$4"
  log "pg_dump ${db} from ${container} ..."
  docker exec "${container}" pg_dump -U "${user}" -d "${db}" --clean --if-exists \
    | gzip > "${out}.tmp"
  finish "${out}.tmp" "${out}" 512
}

dump_mariadb() { # dump_mariadb <container> <db> <outname> — creds from container env
  local container="$1" db="$2" out="${OUT_DIR}/$3"
  log "mariadb-dump ${db} from ${container} ..."
  docker exec "${container}" sh -c \
    'exec mariadb-dump --single-transaction --quick -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "$0"' "${db}" \
    | gzip > "${out}.tmp"
  finish "${out}.tmp" "${out}" 512
}

dump_sqlite() { # dump_sqlite <db-path-on-host> <outname> — consistent online snapshot
  local db="$1" out="${OUT_DIR}/$2"
  log "sqlite backup ${db} ..."
  python3 - "$db" "${out}.tmp" <<'SQPY'
import sqlite3, sys, gzip
src = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
dst = sqlite3.connect(":memory:")
src.backup(dst)
data = "\n".join(dst.iterdump()).encode()
with gzip.open(sys.argv[2], "wb") as f: f.write(data)
SQPY
  finish "${out}.tmp" "${out}" 512
}

dump_pg      paperless_db    paperless    paperless    paperless.sql.gz
dump_mariadb wallabag_db     wallabag     wallabag.sql.gz
dump_pg      miniflux_db     miniflux     miniflux     miniflux.sql.gz
dump_pg      healthchecks_db healthchecks healthchecks healthchecks.sql.gz
dump_pg      forgejo_db      forgejo      forgejo      forgejo.sql.gz
dump_sqlite  /opt/stacks/mealie/data/mealie.db          mealie.sqlite.sql.gz
dump_sqlite  /opt/stacks/vaultwarden/data/db.sqlite3    vaultwarden.sqlite.sql.gz

log "All DB dumps complete in ${OUT_DIR}."

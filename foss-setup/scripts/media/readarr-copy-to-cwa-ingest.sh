#!/usr/bin/env bash
# Readarr Connect custom script — copy imported books to CWA ingest (Option A).
# Readarr keeps files in /readarr-library; CWA ingests copies from /cwa-book-ingest.
# Triggers: Connect → On Import, On Upgrade (not On Grab — paths do not exist yet).
# Env: readarr_addedbookpaths (| separated), readarr_eventtype (Test on dry-run).
#
# 2026-07-13 BUGFIX (apostrophe drop): the old whitespace trim
#   BOOK_PATH="$(echo "$BOOK_PATH" | xargs)"
# used xargs, which does shell-quote processing and CORRUPTS any path containing
# an apostrophe/quote — the NAS busybox xargs strips it ("Kushiel's Chosen" ->
# "Kushiels Chosen"), so the -f test failed and the book was silently dropped;
# every apostrophe title (all the Kushiel's/Naamah's books) never reached CWA
# while "Miranda and Caliban" (no apostrophe) did. Fixed with a pure-bash trim.
# Added a normalized-basename fallback search so ANY residual path-mangling still
# resolves the real file instead of dropping the book.

set -euo pipefail

LOGFILE="/config/logs/readarr-copy-to-cwa-ingest.log"
DEST_DIR="/cwa-book-ingest"
SRC_ROOT="/readarr-library"

mkdir -p "$(dirname "$LOGFILE")"
log() { echo "$(date -Iseconds) $*" >>"$LOGFILE"; }

if [[ "${readarr_eventtype:-}" == "Test" ]]; then
    log "INFO - Test event; exiting."
    exit 0
fi

BOOK_PATHS="${readarr_addedbookpaths:-}"
if [[ -z "$BOOK_PATHS" ]]; then
    log "ERROR - readarr_addedbookpaths empty (manual imports may not populate this)."
    exit 1
fi

# Safe whitespace trim — pure bash, NO xargs (xargs mangles quotes/apostrophes).
trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

# Normalize a path to a comparable key for the fallback search: basename, drop
# extension, lowercase, keep only alphanumerics.
norm() { local b="${1##*/}"; b="${b%.*}"; printf '%s' "$b" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]'; }

IFS='|' read -ra BOOK_ARRAY <<<"$BOOK_PATHS"

for RAW in "${BOOK_ARRAY[@]}"; do
    BOOK_PATH="$(trim "$RAW")"
    [[ -z "$BOOK_PATH" ]] && continue

    # Fallback if the exact path doesn't resolve: find the real book file whose
    # normalized basename matches (guards against any future path-mangling).
    if [[ ! -f "$BOOK_PATH" ]]; then
        want="$(norm "$BOOK_PATH")"
        found=""
        while IFS= read -r -d '' f; do
            if [[ "$(norm "$f")" == "$want" ]]; then found="$f"; break; fi
        done < <(find "$SRC_ROOT" -type f \
            \( -iname '*.epub' -o -iname '*.mobi' -o -iname '*.azw3' -o -iname '*.pdf' -o -iname '*.cbz' \) \
            -print0 2>/dev/null)
        if [[ -n "$found" ]]; then
            log "WARN - exact path missing ('$BOOK_PATH'); resolved by name match -> '$found'"
            BOOK_PATH="$found"
        else
            log "ERROR - Not a file and no name match: '$BOOK_PATH'"
            continue
        fi
    fi

    DEST_BOOK="$DEST_DIR/$(basename "$BOOK_PATH")"
    if cp -v "$BOOK_PATH" "$DEST_BOOK" >>"$LOGFILE" 2>&1; then
        log "SUCCESS - Copied '$BOOK_PATH' -> '$DEST_BOOK'"
    else
        log "ERROR - Failed to copy '$BOOK_PATH'"
    fi
done

exit 0

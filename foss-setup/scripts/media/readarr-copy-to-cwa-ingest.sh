#!/usr/bin/env bash
# Readarr Connect custom script — copy imported books to CWA ingest (Option A).
# Readarr keeps files in /readarr-library; CWA ingests copies from /cwa-book-ingest.
# Triggers: Connect → On Import, On Upgrade (not On Grab — paths do not exist yet).
# Env: readarr_addedbookpaths (| separated), readarr_eventtype (Test on dry-run).

set -euo pipefail

LOGFILE="/config/logs/readarr-copy-to-cwa-ingest.log"
DEST_DIR="/cwa-book-ingest"

mkdir -p "$(dirname "$LOGFILE")"

if [[ "${readarr_eventtype:-}" == "Test" ]]; then
    echo "$(date -Iseconds) INFO - Test event; exiting." >>"$LOGFILE"
    exit 0
fi

BOOK_PATHS="${readarr_addedbookpaths:-}"
if [[ -z "$BOOK_PATHS" ]]; then
    echo "$(date -Iseconds) ERROR - readarr_addedbookpaths empty (manual imports may not populate this)." >>"$LOGFILE"
    exit 1
fi

IFS='|' read -ra BOOK_ARRAY <<<"$BOOK_PATHS"

for BOOK_PATH in "${BOOK_ARRAY[@]}"; do
    BOOK_PATH="$(echo "$BOOK_PATH" | xargs)"
    [[ -z "$BOOK_PATH" ]] && continue

    if [[ ! -f "$BOOK_PATH" ]]; then
        echo "$(date -Iseconds) ERROR - Not a file: $BOOK_PATH" >>"$LOGFILE"
        continue
    fi

    DEST_BOOK="$DEST_DIR/$(basename "$BOOK_PATH")"
    if cp -v "$BOOK_PATH" "$DEST_BOOK" >>"$LOGFILE" 2>&1; then
        echo "$(date -Iseconds) SUCCESS - Copied '$BOOK_PATH' → '$DEST_BOOK'" >>"$LOGFILE"
    else
        echo "$(date -Iseconds) ERROR - Failed to copy '$BOOK_PATH'" >>"$LOGFILE"
    fi
done

exit 0

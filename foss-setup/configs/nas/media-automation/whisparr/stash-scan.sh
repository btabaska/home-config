#!/bin/bash
# Whisparr Connect (Custom Script): on import, trigger a Stash scan of the
# Whisparr sub-library so new scenes index automatically (seed-13).
# Stash sees the whisparr root folder at /data/whisparr; library path is /data/.
STASH_URL="http://192.168.10.4:9999/graphql"
QUERY='{"query":"mutation{metadataScan(input:{paths:[\"/data/whisparr\"]})}"}'
# Whisparr sets whisparr_eventtype=Test when validating; still exit 0.
if command -v curl >/dev/null 2>&1; then
  curl -s -m 20 -X POST "$STASH_URL" -H 'Content-Type: application/json' -d "$QUERY" >/dev/null 2>&1
elif command -v wget >/dev/null 2>&1; then
  wget -q -O /dev/null --header='Content-Type: application/json' --post-data="$QUERY" "$STASH_URL" 2>/dev/null
fi
exit 0

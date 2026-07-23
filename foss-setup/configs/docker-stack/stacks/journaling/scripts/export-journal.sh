#!/usr/bin/env bash
# export-journal.sh (journal-06) — portable JSON EXPORT of every Memos entry (and its
# reflection comments, which are themselves memos) via the Memos 0.29 ConnectRPC API,
# paginating nextPageToken. This is the human-portable / migrate-to-another-Memos export;
# the automatic BACKUP is restic (the whole stack dir — memos sqlite + uploads, n8n
# workflows + encryption key — is in the nightly Backblaze B2 snapshot; see README
# "Backup & export"). LAN-only, uses the same never-expiring PAT as n8n.
#
# Run on the mini (or anywhere that can reach Memos + has the PAT):
#   cd /opt/stacks/journaling && ./scripts/export-journal.sh [OUTFILE]
# Default OUTFILE: ./journal-export-YYYY-MM-DD.json (gitignored).
set -euo pipefail
cd "$(dirname "$0")/.."

# Load MEMOS_API_TOKEN (and optional MEMOS_URL) from the stack .env unless already set.
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${MEMOS_API_TOKEN:?set MEMOS_API_TOKEN (stack .env has it)}"
MEMOS_URL="${MEMOS_URL:-http://localhost:5230}"
OUT="${1:-journal-export-$(date +%F).json}"

python3 - "$MEMOS_URL" "$MEMOS_API_TOKEN" "$OUT" <<'PY'
import json, sys, urllib.request
base, tok, out = sys.argv[1], sys.argv[2], sys.argv[3]
hdrs = {"Authorization": "Bearer " + tok}


def get(path):
    with urllib.request.urlopen(urllib.request.Request(base + path, headers=hdrs), timeout=30) as r:
        return json.load(r)


# 1) all top-level entries (paginate). The list API returns entries only — the AI
#    reflection comments are separate memos NOT in this list, so fetch them per entry.
memos, token = [], ""
while True:
    d = get("/api/v1/memos?pageSize=200" + (f"&pageToken={token}" if token else ""))
    memos += d.get("memos", [])
    token = d.get("nextPageToken") or ""
    if not token:
        break

# 2) attach each entry's reflection comments so the export is self-contained.
n_comments = 0
for m in memos:
    try:
        cm = get(f"/api/v1/{m['name']}/comments").get("memos", [])
    except Exception:
        cm = []
    m["_comments"] = cm
    n_comments += len(cm)

with open(out, "w") as f:
    json.dump({"exported_entries": len(memos), "exported_comments": n_comments, "memos": memos},
              f, indent=2, ensure_ascii=False)
print(f"exported {len(memos)} entries (+{n_comments} reflection comments) -> {out}")
PY

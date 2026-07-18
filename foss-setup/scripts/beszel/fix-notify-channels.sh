#!/usr/bin/env bash
# fix-29 / L28 — keep Beszel's alert channels coherent.
#
# Beszel user_settings listed an email destination while the hub has NO SMTP_*
# env configured, so every email alert send fails silently — a dead notification
# path that reads as "I'll get emailed" but delivers nothing. The working channel
# is the ntfy webhook (and beszel-down is independently caught by the
# alert-beszel-none-down verification check). This script removes email
# destinations whenever SMTP is not configured, and leaves them untouched if it
# is — so re-enabling email later (add SMTP_* to the beszel env) just works.
#
# Idempotent. Run on the mini (where the beszel container + PocketBase live):
#   BESZEL_ADMIN_USER=… BESZEL_ADMIN_PASSWORD=… bash fix-notify-channels.sh
# (creds: vault beszel.admin_user / beszel.admin_password — never hard-coded here)
set -euo pipefail

BESZEL_URL="${BESZEL_URL:-http://localhost:8090}"
CONTAINER="${BESZEL_CONTAINER:-beszel}"
: "${BESZEL_ADMIN_USER:?set BESZEL_ADMIN_USER (vault beszel.admin_user)}"
: "${BESZEL_ADMIN_PASSWORD:?set BESZEL_ADMIN_PASSWORD (vault beszel.admin_password)}"

# Is SMTP actually configured on the hub? If so, email is a live path — leave it.
if docker inspect "$CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' \
     | grep -qiE '^SMTP_'; then
  SMTP_CONFIGURED=1
else
  SMTP_CONFIGURED=0
fi
echo "smtp_configured=${SMTP_CONFIGURED}"

TOK=$(curl -s -m 8 -X POST "${BESZEL_URL}/api/collections/_superusers/auth-with-password" \
  -H 'Content-Type: application/json' \
  -d "{\"identity\":\"${BESZEL_ADMIN_USER}\",\"password\":\"${BESZEL_ADMIN_PASSWORD}\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
[ -z "$TOK" ] && { echo "AUTH_FAILED" >&2; exit 1; }

# Walk every user_settings record; strip email dests when SMTP is absent,
# preserving webhooks and every other setting field. (Records are passed via env,
# not stdin — a `<<'PY'` heredoc already owns python's stdin.)
RECORDS=$(curl -s -m 8 -H "Authorization: $TOK" \
  "${BESZEL_URL}/api/collections/user_settings/records")
RECORDS="$RECORDS" SMTP_CONFIGURED="$SMTP_CONFIGURED" BESZEL_URL="$BESZEL_URL" TOK="$TOK" python3 <<'PY'
import json, os, urllib.request

smtp = os.environ["SMTP_CONFIGURED"] == "1"
base = os.environ["BESZEL_URL"]
tok = os.environ["TOK"]
items = json.loads(os.environ["RECORDS"]).get("items", [])
changed = 0
for r in items:
    s = r.get("settings", {}) or {}
    emails = s.get("emails") or []
    if emails and not smtp:
        s["emails"] = []
        body = json.dumps({"settings": s}).encode()
        req = urllib.request.Request(
            f"{base}/api/collections/user_settings/records/{r['id']}",
            data=body, method="PATCH",
            headers={"Authorization": tok, "Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=8).read()
        changed += 1
        print(f"stripped dead email dest from record {r['id']} "
              f"(webhooks kept: {bool(s.get('webhooks'))})")
    else:
        print(f"record {r['id']} ok (emails={emails}, smtp={smtp})")
print(f"records_changed={changed}")
PY

# Checks — reading

`foss-setup/verification/checks.d/reading.yaml` — 8 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `cwa-kobo-sync-consumer`

CWA Kobo sync answers valid JSON for both device users (M35 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^KOBO_SYNC_OK$`

```bash
ok=1; for u in "$CWA_KOBO_SYNC_URL_ADMIN" "$CWA_KOBO_SYNC_URL_KOBO2"; do code=$(curl -s -o /tmp/cwa-kobo-probe.json -m 30 -w '%{http_code}' "$u"); if [ "$code" != "200" ] || ! python3 -c 'import json;json.load(open("/tmp/cwa-kobo-probe.json"))' 2>/dev/null; then ok=0; echo "KOBO_SYNC_FAIL code=$code"; fi; done; rm -f /tmp/cwa-kobo-probe.json; [ "$ok" = 1 ] && echo KOBO_SYNC_OK
```

## `cwa-kobo-proxy-intent`

CWA store passthrough matches documented intent (ENABLED, fix-38/M35)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^proxy=1 sync=1$`

```bash
sqlite3 "file:/volume1/docker/calibre-web-automated/config/app.db?mode=ro" "select 'proxy='||config_kobo_proxy||' sync='||config_kobo_sync from settings;"
```

## `cwa-image-digest-pinned`

CWA runs the digest-pinned fork image, compose pin present (I68)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^PIN_OK$`

```bash
img=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker inspect calibre-web-automated --format '{{.Config.Image}}'" 2>/dev/null); pin=$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "grep -oE 'image: *[^ ]+' /volume1/docker/calibre-web-automated/docker-compose.yml" 2>/dev/null | awk '{print $2}'); if [ -n "$img" ] && [ "$img" = "$pin" ] && printf '%s' "$img" | grep -qE '@sha256:[0-9a-f]{64}$'; then echo PIN_OK; else echo "PIN_BAD running=$img compose=$pin"; fi
```

## `cwa-ghcr-tag-digest-drift`

ghcr v4.0.7 tag still points at the vetted digest (I68 tamper tripwire)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^TAG_UNCHANGED$`

```bash
pin=$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "grep -oE 'image: *[^ ]+' /volume1/docker/calibre-web-automated/docker-compose.yml" 2>/dev/null | grep -oE 'sha256:[0-9a-f]{64}'); tok=$(curl -s -m 20 "https://ghcr.io/token?scope=repository:new-usemame/calibre-web-nextgen:pull" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("token",""))'); remote=$(curl -sI -m 20 -H "Authorization: Bearer $tok" -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json" "https://ghcr.io/v2/new-usemame/calibre-web-nextgen/manifests/v4.0.7" | tr -d '\r' | awk 'tolower($1)=="docker-content-digest:"{print $2}'); if [ -z "$pin" ] || [ -z "$remote" ]; then echo "TAG_CHECK_ERROR pin=$pin remote=$remote"; elif [ "$pin" = "$remote" ]; then echo TAG_UNCHANGED; else echo "TAG_REPOINTED pin=$pin remote=$remote"; fi
```

## `cwa-upstream-cve-catchup`

upstream crocodilestick CWA still stalled pre-CVE-fix (fail = migrate back)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^UPSTREAM_STALLED`

```bash
curl -s -m 20 https://api.github.com/repos/crocodilestick/calibre-web-automated/releases/latest | python3 -c '
import sys, json
tag = (json.load(sys.stdin).get("tag_name") or "").lstrip("vV")
try:
    newer = tuple(int(x) for x in tag.split(".")[:3]) > (4, 0, 6)
except ValueError:
    print("UPSTREAM_CHECK_ERROR tag=%r" % tag); sys.exit(0)
print("UPSTREAM_CAUGHT_UP %s - migrate off the fork" % tag if newer else "UPSTREAM_STALLED %s" % tag)'
```

## `cwa-library-author-split`

CWA library has no split author identities (L47 class)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^AUTHOR_SPLITS=NONE$`

```bash
python3 -c '
import sqlite3, collections
db = sqlite3.connect("file:/volume1/books/metadata.db?mode=ro", uri=True)
norm = collections.defaultdict(list)
for (n,) in db.execute("select name from authors"):
    norm["".join(sorted(c for c in n.lower() if c.isalnum()))].append(n)
splits = [" / ".join(v) for v in norm.values() if len(v) > 1]
print("AUTHOR_SPLITS=" + ("; ".join(splits) if splits else "NONE"))'
```

## `cwa-library-dup-titles`

CWA library has no duplicate title per author (L47 class)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^DUP_TITLES=NONE$`

```bash
python3 -c '
import sqlite3, collections, re
db = sqlite3.connect("file:/volume1/books/metadata.db?mode=ro", uri=True)
q = "select a.name, b.title from books b join books_authors_link l on l.book=b.id join authors a on a.id=l.author"
norm = collections.defaultdict(list)
for author, title in db.execute(q):
    key = (author, re.sub(r"[^a-z0-9]", "", title.lower().split(":")[0]))
    norm[key].append(title)
dups = ["%s: %s" % (a, " / ".join(t)) for (a, _), t in norm.items() if len(t) > 1]
print("DUP_TITLES=" + ("; ".join(dups) if dups else "NONE"))'
```

## `cwa-library-covers`

every CWA library book has a cover (L47)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^nocover=0$`

```bash
sqlite3 "file:/volume1/books/metadata.db?mode=ro" "select 'nocover='||count(*) from books where has_cover=0;"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

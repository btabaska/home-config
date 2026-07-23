# Checks — reading

`foss-setup/verification/checks.d/reading.yaml` — 23 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `bookshelf-foreign-records`

Bookshelf has no actionable foreign-language book records (fix-46 B1)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-46` · **enabled:** True
- **expects:** `^FOREIGN_RECORDS=NONE$`

```bash
python3 -c '
import json, os, re, urllib.request
req = urllib.request.Request("http://192.168.10.4:8790/api/v1/book", headers={"X-Api-Key": os.environ["BOOKSHELF_API_KEY"]})
books = json.load(urllib.request.urlopen(req, timeout=30))
pat = re.compile("^(L[\\x27\\u2019]|La |Le |Les |El |Los )|\\bTome ?\\d|, T\\d\\b|Urzeala|Fest\\u00edn", re.I)
live = [b for b in books if b.get("monitored") or (b.get("statistics") or {}).get("bookFileCount", 0) > 0]
bad = ["%s:%s" % (b["id"], b["title"]) for b in live if pat.search(b["title"])]
print("FOREIGN_RECORDS=" + ("; ".join(bad) if bad else "NONE"))'
```

## `bookshelf-foreign-grab-history`

no foreign-language grabs in Bookshelf history since fix-46 guard (B2 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-46` · **enabled:** True
- **expects:** `^FOREIGN_GRABS=NONE$`

```bash
python3 -c '
import json, os, re, urllib.request
url = "http://192.168.10.4:8790/api/v1/history?pageSize=200&sortKey=date&sortDirection=descending"
req = urllib.request.Request(url, headers={"X-Api-Key": os.environ["BOOKSHELF_API_KEY"]})
recs = json.load(urllib.request.urlopen(req, timeout=30)).get("records", [])
pat = re.compile("\\[(FRE|FRA|SPA|ESP|ROM|GER|ITA|POR)\\]|FRENCH|SPANISH|VOSTFR|\\bVF\\b|\\bTome ?\\d", re.I)
bad = sorted({r.get("sourceTitle") or "" for r in recs if r.get("eventType") == "grabbed" and (r.get("date") or "") >= "2026-07-20" and pat.search(r.get("sourceTitle") or "")})
print("FOREIGN_GRABS=" + ("; ".join(bad) if bad else "NONE"))'
```

## `books-language-guard`

Bookshelf language+derivative blocklist + libreseerr edition pinning in place (fix-46 B2/B3)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-46` · **enabled:** True
- **expects:** `^LANG_GUARD_OK$`

```bash
rp=$(curl -sm 20 -H "X-Api-Key: $BOOKSHELF_API_KEY" http://192.168.10.4:8790/api/v1/releaseprofile | python3 -c '
import json, sys
ps = json.load(sys.stdin)
en = [p for p in ps if p.get("enabled")]
terms = " ".join(t.lower() for p in en for t in p.get("ignored") or [])
ok = "french" in terms and "companion" in terms and "coloring book" in terms
print("RP_OK" if ok else "RP_MISSING")');
pin=$(grep -c '"anyEditionOk": False' /opt/stacks/libreseerr/readarr.py 2>/dev/null);
if [ "$rp" = RP_OK ] && [ "$pin" = 1 ]; then echo LANG_GUARD_OK;
else echo "LANG_GUARD_BAD rp=$rp pin=$pin"; fi
```

## `books-pipeline-lost-imports`

every Bookshelf book with a file is present in Calibre (fix-47 B4)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-47` · **enabled:** True
- **expects:** `^LOST_BOOKS=NONE$`

```bash
python3 -c '
import json, os, re, subprocess, urllib.request
STOP = {"a", "an", "and", "the", "or", "of"}
def full(s): return frozenset(w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP)
req = urllib.request.Request("http://192.168.10.4:8790/api/v1/book", headers={"X-Api-Key": os.environ["BOOKSHELF_API_KEY"]})
books = json.load(urllib.request.urlopen(req, timeout=30))
with_files = {b["title"]: full(b["title"]) for b in books if (b.get("statistics") or {}).get("bookFileCount", 0) > 0}
out = subprocess.run(["ssh", "nas", "sqlite3 \x27file:/volume1/books/metadata.db?mode=ro\x27 \x27select title from books;\x27"], capture_output=True, text=True, timeout=60)
cal = [full(t) for t in out.stdout.splitlines() if t.strip()]
lost = [t for t, n in with_files.items() if n and not any(n <= c or c <= n for c in cal)]
print("LOST_BOOKS=" + ("; ".join(sorted(lost)) if lost else "NONE"))'
```

## `bookshelf-import-deadends`

no silent Bookshelf import dead-ends in the last 48h (fix-47 B6)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-47` · **enabled:** True
- **expects:** `^IMPORT_DEADENDS=NONE$`

```bash
python3 -c '
import datetime, json, os, urllib.request
def get(path):
    req = urllib.request.Request("http://192.168.10.4:8790/api/v1/" + path, headers={"X-Api-Key": os.environ["BOOKSHELF_API_KEY"]})
    return json.load(urllib.request.urlopen(req, timeout=30))
cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
recs = get("history?pageSize=200&sortKey=date&sortDirection=descending").get("records", [])
incomplete = {r["bookId"]: r.get("sourceTitle") or "?" for r in recs if r.get("eventType") == "bookImportIncomplete" and (r.get("date") or "") >= cutoff}
dead = []
if incomplete:
    queue_ids = {i.get("bookId") for i in (get("queue?pageSize=100").get("records") or [])}
    for bid, src in incomplete.items():
        b = get("book/%d" % bid)
        if (b.get("statistics") or {}).get("bookFileCount", 0) == 0 and bid not in queue_ids:
            dead.append("%s (book %d)" % (src[:60], bid))
print("IMPORT_DEADENDS=" + ("; ".join(sorted(dead)) if dead else "NONE"))'
```

## `books-format-guard`

EPUB-Preferred profile intact + all ebook authors on it (fix-47 B7)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-47` · **enabled:** True
- **expects:** `^FORMAT_GUARD=OK$`

```bash
python3 -c '
import json, os, urllib.request
def get(path):
    req = urllib.request.Request("http://192.168.10.4:8790/api/v1/" + path, headers={"X-Api-Key": os.environ["BOOKSHELF_API_KEY"]})
    return json.load(urllib.request.urlopen(req, timeout=30))
bad = []
profs = {p["id"]: p for p in get("qualityprofile")}
ep = next((p for p in profs.values() if p["name"] == "EPUB Preferred"), None)
if not ep:
    bad.append("EPUB-Preferred profile missing")
else:
    if not ep.get("upgradeAllowed"): bad.append("upgradeAllowed off")
    if ep.get("cutoff") != 3: bad.append("cutoff not EPUB")
    for it in ep["items"]:
        q = it.get("quality") or {}
        if q.get("id") == 1 and it.get("allowed"): bad.append("PDF allowed")
        if q.get("id") == 3 and not it.get("allowed"): bad.append("EPUB not allowed")
spoken = {p["id"] for p in profs.values() if p["name"] == "Spoken"}
for a in get("author"):
    if a["qualityProfileId"] in spoken: continue
    if not ep or a["qualityProfileId"] != ep["id"]:
        bad.append("author %s on profile %d" % (a["authorName"], a["qualityProfileId"]))
print("FORMAT_GUARD=" + ("; ".join(bad) if bad else "OK"))'
```

## `cwa-ingest-automerge-guard`

CWA ingest automerge=overwrite + duplicate detection on (media-08 guard)

- **host:** `nas` · **severity:** `warn` · **guards task:** `media-08` · **enabled:** True
- **expects:** `^automerge=overwrite dupdetect=1 scan=1 freq=after_import$`

```bash
sqlite3 -cmd ".timeout 30000" "file:/volume1/docker/calibre-web-automated/config/cwa.db?mode=ro" "select 'automerge='||auto_ingest_automerge||' dupdetect='||duplicate_detection_enabled||' scan='||duplicate_scan_enabled||' freq='||duplicate_scan_frequency from cwa_settings;"
```

## `cwa-library-covers`

every CWA library book has a cover (L47)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-38` · **enabled:** True
- **expects:** `^nocover=0$`

```bash
sqlite3 "file:/volume1/books/metadata.db?mode=ro" "select 'nocover='||count(*) from books where has_cover=0;"
```

## `libreseerr-request-stuck`

libreseerr: no non-terminal request without activity >48h (fix-48 B10/B12)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-48` · **enabled:** True
- **expects:** `^STUCK_REQUESTS=NONE$`

```bash
python3 -c '
import json, datetime
reqs = json.load(open("/opt/stacks/libreseerr/data/requests.json"))
now = datetime.datetime.utcnow()
act = lambda r: datetime.datetime.fromisoformat(r.get("last_search_at") or r.get("created_at"))
stuck = ["%s(%s %.0fh)" % (r.get("title"), r.get("status"), (now - act(r)).total_seconds() / 3600) for r in reqs if r.get("status") in ("pending", "processing", "retrying", "downloading") and (now - act(r)).total_seconds() > 48 * 3600]
print("STUCK_REQUESTS=" + ("; ".join(stuck) if stuck else "NONE"))'
```

## `libreseerr-request-path-guards`

libreseerr: no resurfaced failure classes, request-path guards in place (fix-48 B8/B9/B11)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-48` · **enabled:** True
- **expects:** `^REQUEST_PATH_OK$`

```bash
sig=$(python3 -c '
import json, re
reqs = json.load(open("/opt/stacks/libreseerr/data/requests.json"))
pat = re.compile("read timeout=15|A book with this ID was not found|AddSkyhookData|Could not find author")
bad = [str(r.get("title")) for r in reqs if r.get("status") == "error" and (r.get("created_at") or "") >= "2026-07-21" and pat.search(str(r.get("error")))]
print(";".join(bad) if bad else "NONE")');
guard=OK;
grep -q "PermanentRequestError" /opt/stacks/libreseerr/app.py || guard=NO_PATCH_APP;
grep -q "adopt_library_book" /opt/stacks/libreseerr/readarr.py || guard=NO_PATCH_READARR;
grep -q "class BookshelfClient(ReadarrClient)" /opt/stacks/libreseerr/bookshelf.py || guard=NO_PATCH_BOOKSHELF;
docker inspect libreseerr --format '{{json .Config.Cmd}}' | grep -q -- --timeout || guard=NO_GUNICORN_TIMEOUT;
[ -n "$(docker exec libreseerr printenv NTFY_TOKEN 2>/dev/null)" ] || guard=NO_NTFY_TOKEN;
if [ "$sig" = NONE ] && [ "$guard" = OK ]; then echo REQUEST_PATH_OK;
else echo "REQUEST_PATH_BAD sig=$sig guard=$guard"; fi
```

## `hardcover-token-valid`

hardcover API token authenticates and is >17d from Jan-1 expiry (bmig-06)

- **host:** `mini` · **severity:** `warn` · **guards task:** `bmig-06` · **enabled:** True
- **expects:** `^HC_TOKEN_OK `

```bash
python3 -c '
import base64, json, os, time, urllib.error, urllib.request
tok = (os.environ.get("HARDCOVER_API_TOKEN") or "").strip()
if not tok:
    print("HC_TOKEN_ERROR missing HARDCOVER_API_TOKEN"); raise SystemExit
if not tok.lower().startswith("bearer "):
    tok = "Bearer " + tok
try:
    pay = tok.split(" ", 1)[1].split(".")[1]
    exp = json.loads(base64.urlsafe_b64decode(pay + "=" * (-len(pay) % 4)))["exp"]
    days = (exp - time.time()) / 86400
except Exception as e:
    print("HC_TOKEN_ERROR cannot decode JWT exp: %r" % e); raise SystemExit
body = json.dumps({"query": "query { me { username } }"}).encode()
user, code = "", 0
for attempt in (1, 2):
    try:
        req = urllib.request.Request("https://api.hardcover.app/v1/graphql", data=body,
            headers={"Authorization": tok, "Content-Type": "application/json"})
        resp = json.load(urllib.request.urlopen(req, timeout=25))
        me = (resp.get("data") or {}).get("me")
        if isinstance(me, list): me = (me or [{}])[0]
        user = (me or {}).get("username")
        code = 200 if user else 0
        if user or "errors" in resp: break
    except urllib.error.HTTPError as e:
        code = e.code
        if e.code == 429 and attempt == 1: time.sleep(20); continue
        break
    except Exception:
        break
if not user:
    print("HC_TOKEN_INVALID http=%s days_left=%.0f" % (code, days))
elif days < 17:
    print("HC_TOKEN_EXPIRING days_left=%.1f user=%s - renew at hardcover.app before Jan 1" % (days, user))
else:
    print("HC_TOKEN_OK days_left=%.0f user=%s" % (days, user))'
```

## `request-author-parity`

libreseerr: every bound request author-matches the request (C1/C4 tripwire)

- **host:** `mini` · **severity:** `warn` · **guards task:** `bmig-06` · **enabled:** True
- **expects:** `^AUTHOR_PARITY_OK`

```bash
python3 /opt/verification/bin/books-author-parity.py
```

## `metadata-search-canary`

Bookshelf lookup: canonical Pride & Prejudice present + rank (C2 canary)

- **host:** `mini` · **severity:** `warn` · **guards task:** `bmig-06` · **enabled:** True
- **expects:** `^CANARY_OK `

```bash
python3 -c '
import json, os, re, urllib.parse, urllib.request
norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("&", " and "))
url = "http://192.168.10.4:8790/api/v1/book/lookup?term=" + urllib.parse.quote("Pride and Prejudice Jane Austen")
req = urllib.request.Request(url, headers={"X-Api-Key": os.environ["BOOKSHELF_API_KEY"]})
results = json.load(urllib.request.urlopen(req, timeout=45))
rank = next((i for i, r in enumerate(results) if norm(r.get("title")) == "prideandprejudice" and "austen" in norm(r.get("authorTitle") or str(r.get("author", {}).get("authorName", "")))), None)
if rank is None:
    print("CANARY_MISS results=%d: %s" % (len(results), " | ".join((r.get("title") or "?")[:30] for r in results[:5])))
else:
    print("CANARY_OK rank=%d results=%d" % (rank, len(results)))'
```

## `shelfmark-mam-path-ready`

Shelfmark up + seedbox mount rshared (MAM→CWA-ingest path intact)

- **host:** `nas` · **severity:** `warn` · **guards task:** `bmig-06` · **enabled:** True
- **expects:** `^SHELFMARK_OK`

```bash
h=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 http://127.0.0.1:8084/api/health); p=$(grep seedbox-files /proc/self/mountinfo 2>/dev/null | grep -oE "shared:[0-9]+" | head -1); if [ "$h" = "200" ] && [ -n "$p" ]; then echo "SHELFMARK_OK health=$h prop=$p"; else echo "SHELFMARK_BAD health=$h prop=$p"; fi
```

## `audiobookshelf-libraries-consumer`

Audiobookshelf: API key authorizes + Audiobooks/Podcasts libraries return real item counts (read-16 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `read-16` · **enabled:** True
- **expects:** `^ABS_OK books=[1-9]`

```bash
python3 -c '
import json, os, urllib.request
base = "http://192.168.10.4:13378"
hdr = {"Authorization": "Bearer " + os.environ["AUDIOBOOKSHELF_API_KEY"]}
get = lambda p: json.load(urllib.request.urlopen(urllib.request.Request(base + p, headers=hdr), timeout=25))
by = {l["mediaType"]: l["id"] for l in get("/api/libraries")["libraries"]}
total = lambda mt: get("/api/libraries/" + by[mt] + "/items?limit=0").get("total", 0) if mt in by else -1
b, p = total("book"), total("podcast")
print("ABS_OK books=%d podcasts=%d" % (b, p) if (b >= 1 and p >= 0) else "ABS_FAIL books=%d podcasts=%d types=%s" % (b, p, sorted(by)))'
```

## `komga-libraries-consumer`

Komga: admin creds authorize + Comics/Manga libraries exist, a series is indexed, a page streams, OPDS responds (read-17 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `read-17` · **enabled:** True
- **expects:** `^KOMGA_OK`

```bash
python3 /opt/verification/bin/komga-serves.py
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

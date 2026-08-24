# Checks — nas-services

`foss-setup/verification/checks.d/nas-services.yaml` — 25 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `nas-ssh`

NAS reachable over SSH from mini

- **host:** `nas` · **severity:** `crit` · **guards task:** `nas-01` · **enabled:** True
- **expects:** `^nas-ssh-ok$`

```bash
echo nas-ssh-ok
```

## `nas-flaresolverr`

flaresolverr Cloudflare solver healthy (Prowlarr/arr search dependency)

- **host:** `nas` · **severity:** `warn` · **guards task:** `nas-01` · **enabled:** True
- **expects:** `"ok"`

```bash
curl -sm 8 http://localhost:8191/health
```

## `nas-rreading-glasses-hc`

rreading-glasses-hc hardcover metadata provider serving on :8789 (bookshelf)

- **host:** `nas` · **severity:** `warn` · **guards task:** `bmig-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8789/
```

## `nas-immich`

immich API ping on nas:2283

- **host:** `mini` · **severity:** `crit` · **guards task:** `nas-09` · **enabled:** True
- **expects:** `pong`

```bash
curl -s -m 8 http://nas:2283/api/server/ping
```

## `nas-plex`

plex answers on nas:32400 (401 unauthenticated = up)

- **host:** `mini` · **severity:** `crit` · **guards task:** `media-01` · **enabled:** True
- **expects:** `^401$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:32400/
```

## `nas-cwa`

calibre-web-automated answers on nas:8083

- **host:** `mini` · **severity:** `warn` · **guards task:** `ebook-04` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:8083/
```

## `nas-sonarr`

sonarr answers on nas:8989

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-02` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:8989/
```

## `nas-radarr`

radarr answers on nas:7878

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-02` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:7878/
```

## `nas-lidarr`

lidarr answers on nas:8686

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-03` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:8686/
```

## `nas-prowlarr`

prowlarr answers on nas:9696

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-02` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:9696/
```

## `nas-bookshelf`

bookshelf answers on nas:8790

- **host:** `mini` · **severity:** `warn` · **guards task:** `bmig-02` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:8790/
```

## `stash-serving`

stash answers its GraphQL version query with auth (:9999, real consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `nas-01` · **enabled:** True
- **expects:** `^stash=ok `

```bash
code=$(curl -s -m 8 -o /tmp/stash-ver.$$ -w '%{http_code}' -X POST http://nas:9999/graphql -H 'Content-Type: application/json' -H "ApiKey: $STASH_API_KEY" -d '{"query":"{version{version}}"}'); body=$(cat /tmp/stash-ver.$$ 2>/dev/null); rm -f /tmp/stash-ver.$$; printf '%s' "$body" | grep -q '"version":"v[0-9]' && echo "stash=ok http=$code" || echo "stash=FAIL http=$code body=${body:0:60}"
```

## `nas-beets`

beets youtube-tagging web UI serving on :8337

- **host:** `mini` · **severity:** `warn` · **guards task:** `nas-30` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:8337/
```

## `nas-beets-ingest-fresh`

beets youtube-ingest tagging ran recently (import.log < 30h)

- **host:** `nas` · **severity:** `warn` · **guards task:** `nas-30` · **enabled:** True
- **expects:** `^ingest=fresh$`

```bash
find /volume1/docker/beets/import.log -mmin -1800 2>/dev/null | grep -q . && echo ingest=fresh || echo ingest=STALE
```

## `nas-whisparr`

whisparr answers its /ping (adult automation :6969, seed-13)

- **host:** `mini` · **severity:** `warn` · **guards task:** `seed-13` · **enabled:** True
- **expects:** `"status":\s*"OK"`

```bash
curl -s -m 8 http://nas:6969/ping
```

## `whisparr-stash-scan-authed`

whisparr->stash Connect scan sends the Stash ApiKey (fix-88, no more silent 401)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-88` · **enabled:** True
- **expects:** `^SCAN_AUTH_WIRED$`

```bash
grep -q 'ApiKey' /volume1/docker/whisparr/config/stash-scan.sh && echo SCAN_AUTH_WIRED || echo SCAN_AUTH_MISSING
```

## `nas-immich-backup-freshness`

immich library has assets and a file landed in the last 7 days (phone backup flowing)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-35` · **enabled:** True
- **expects:** `^backup=fresh$`

```bash
t=$(curl -sm 10 -H "x-api-key: $IMMICH_API_KEY" "$IMMICH_URL/api/server/statistics" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["photos"]+d["videos"])' 2>/dev/null || echo api_err); since=$(date -u -d "-7 days" +%Y-%m-%dT%H:%M:%SZ); n=$(curl -sm 15 -H "x-api-key: $IMMICH_API_KEY" -H 'Content-Type: application/json' "$IMMICH_URL/api/search/metadata" -d "{\"createdAfter\":\"$since\",\"size\":1}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["assets"]["total"])' 2>/dev/null || echo err); { [ "$t" != api_err ] && [ "$t" -gt 0 ] && [ "$n" != err ] && [ "$n" -gt 0 ] && echo backup=fresh; } || echo "backup=STALE assets=$t fresh_7d=$n"
```

## `nas-immich-mobile-paired`

immich has at least one mobile (iOS/Android) session paired

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-35` · **enabled:** False
- **expects:** `^paired=yes$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker exec immich_postgres psql -U postgres -d immich -tAc \"SELECT count(*) FROM session WHERE \\\"deviceOS\\\" ILIKE '%ios%' OR \\\"deviceOS\\\" ILIKE '%android%'\"" 2>/dev/null); [ -n "$n" ] && [ "$n" -gt 0 ] && echo paired=yes || echo "paired=NO mobile_sessions=${n:-query_failed}"
```

## `immich-user-zero-assets`

every Immich user has >0 assets (per-user backup flowing, SM36)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-60` · **enabled:** True
- **expects:** `^per_user=ok$`

```bash
curl -sm 12 -H "x-api-key: $IMMICH_API_KEY" "$IMMICH_URL/api/server/statistics" | python3 -c 'import sys,json;d=json.load(sys.stdin);z=[u["userName"] for u in d["usageByUser"] if (u["photos"]+u["videos"])==0];print("per_user=ok" if not z else "per_user=ZERO:"+",".join(z))'
```

## `nas-immich-corrupt-mov-quarantined`

corrupt IMG_3674 asset keeps its preview row (crash-loop quarantined, SM1)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-60` · **enabled:** True
- **expects:** `^quarantined=yes$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker exec immich_postgres psql -U postgres -d immich -tAc \"SELECT count(*) FROM asset_file WHERE \\\"assetId\\\"='8a5d0a66-9ee4-47d3-a058-c80eea7d53ba' AND type='preview'\"" 2>/dev/null); [ "$n" = 1 ] && echo quarantined=yes || echo "quarantined=NO cnt=${n:-err}"
```

## `nas-immich-ffmpeg-nocrash`

no Immich ffmpeg core dump at /volume1 root (transcode crash-loop class, SM1/fix-87)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-60` · **enabled:** True
- **expects:** `^0$`

```bash
ls /volume1/ 2>/dev/null | grep -c '@ffmpeg.*core\.gz' || true
```

## `nas-immich-no-future-dates`

no Immich asset dated >1y in the future (timeline-hijack class, SL5)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-60` · **enabled:** True
- **expects:** `^dates=ok$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker exec immich_postgres psql -U postgres -d immich -tAc \"SELECT count(*) FROM asset WHERE \\\"fileCreatedAt\\\" > now() + interval '1 year' AND \\\"deletedAt\\\" IS NULL\"" 2>/dev/null); [ -n "$n" ] && [ "$n" = 0 ] && echo dates=ok || echo "dates=FUTURE n=${n:-err}"
```

## `nas-immich-dump-rotation`

Immich pg-dump dir stays bounded by keep-N rotation (<=10 files, SL29)

- **host:** `nas` · **severity:** `warn` · **guards task:** `fix-60` · **enabled:** True
- **expects:** `^rotation=ok`

```bash
n=$(ls /volume1/docker/immich/backups 2>/dev/null | grep -c 'immich-.*\.sql\.gz'); [ "$n" -le 10 ] && echo "rotation=ok n=$n" || echo "rotation=BLOAT n=$n"
```

## `nas-beszel-volume-split`

NAS beszel-agent still mounts all 3 volume extra-filesystems (home-07)

- **host:** `nas` · **severity:** `warn` · **guards task:** `home-07` · **enabled:** True
- **expects:** `^3$`

```bash
grep -c 'extra-filesystems/volume[123]:ro' /volume1/docker/beszel-agent/compose.yaml
```

## `nas-jellyfin-serves`

Jellyfin serves populated Movies+TV libraries AND streams a title (media-05)

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-05` · **enabled:** True
- **expects:** `^JELLYFIN_OK`

```bash
python3 /opt/verification/bin/jellyfin-serves.py --key "$JELLYFIN_API_KEY"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

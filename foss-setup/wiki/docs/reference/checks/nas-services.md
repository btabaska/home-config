# Checks — nas-services

`foss-setup/verification/checks.d/nas-services.yaml` — 17 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

## `nas-rreading-glasses`

rreading-glasses metadata provider serving on :8788 (readarr/libreseerr)

- **host:** `nas` · **severity:** `warn` · **guards task:** `nas-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8788/
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

## `nas-readarr`

readarr answers on nas:8787

- **host:** `mini` · **severity:** `warn` · **guards task:** `ebook-02` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://nas:8787/
```

## `stash-serving`

stash answers its GraphQL version query (:9999)

- **host:** `mini` · **severity:** `warn` · **guards task:** `nas-01` · **enabled:** True
- **expects:** `"version":"v[0-9]`

```bash
curl -s -m 8 -X POST http://nas:9999/graphql -H 'Content-Type: application/json' -d '{"query":"{version{version}}"}'
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

## `nas-immich-backup-freshness`

immich library has assets and a file landed in the last 7 days (phone backup flowing)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-35` · **enabled:** True
- **expects:** `^backup=fresh$`

```bash
t=$(curl -sm 10 -H "x-api-key: $IMMICH_API_KEY" "$IMMICH_URL/api/server/statistics" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["photos"]+d["videos"])' 2>/dev/null || echo api_err); f=$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "find /volume1/photo/upload /volume1/photo/library -type f -not -name .immich -mtime -7 2>/dev/null | head -1" 2>/dev/null); [ "$t" != api_err ] && [ "$t" -gt 0 ] && [ -n "$f" ] && echo backup=fresh || echo "backup=STALE assets=$t fresh_file=${f:-none}"
```

## `nas-immich-mobile-paired`

immich has at least one mobile (iOS/Android) session paired

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-35` · **enabled:** True
- **expects:** `^paired=yes$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker exec immich_postgres psql -U postgres -d immich -tAc \"SELECT count(*) FROM session WHERE \\\"deviceOS\\\" ILIKE '%ios%' OR \\\"deviceOS\\\" ILIKE '%android%'\"" 2>/dev/null); [ -n "$n" ] && [ "$n" -gt 0 ] && echo paired=yes || echo "paired=NO mobile_sessions=${n:-query_failed}"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

# Checks — nas-services

`foss-setup/verification/checks.d/nas-services.yaml` — 15 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

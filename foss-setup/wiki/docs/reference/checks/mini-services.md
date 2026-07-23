# Checks — mini-services

`foss-setup/verification/checks.d/mini-services.yaml` — 27 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `mini-caddy-running`

caddy reverse proxy container running

- **host:** `mini` · **severity:** `crit` · **guards task:** `docker-02` · **enabled:** True
- **expects:** `^running$`

```bash
docker inspect -f '{{.State.Status}}' caddy
```

## `mini-caddy-live-config-current`

caddy running config matches on-disk Caddyfile (no edited-but-never-reloaded vhosts)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-32` · **enabled:** True
- **expects:** `^caddy_config=current$`

```bash
{ docker exec caddy caddy adapt --config /etc/caddy/Caddyfile 2>/dev/null; echo __SPLIT__; docker exec caddy wget -qO- http://localhost:2019/config/; } | python3 -c "import sys,json; raw=sys.stdin.read().split(\"__SPLIT__\"); hosts=lambda c: {h for s in c.get(\"apps\",{}).get(\"http\",{}).get(\"servers\",{}).values() for r in s.get(\"routes\",[]) for m in r.get(\"match\",[]) for h in m.get(\"host\",[])}; disk=hosts(json.loads(raw[0])); live=hosts(json.loads(raw[1])); print(\"caddy_config=current\" if disk==live else \"caddy_config=DRIFT missing_live:%s extra_live:%s\" % (sorted(disk-live), sorted(live-disk)))"
```

## `mini-adguard-running`

adguardhome container running

- **host:** `mini` · **severity:** `crit` · **guards task:** `dns-01` · **enabled:** True
- **expects:** `^running$`

```bash
docker inspect -f '{{.State.Status}}' adguardhome
```

## `mini-paperless`

paperless-ngx answers on :8000

- **host:** `mini` · **severity:** `crit` · **guards task:** `docker-05` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8000/
```

## `mini-forgejo`

forgejo answers on :3030

- **host:** `mini` · **severity:** `crit` · **guards task:** `docker-09` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:3030/
```

## `mini-ntfy`

ntfy answers on :8080

- **host:** `mini` · **severity:** `crit` · **guards task:** `docker-10` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8080/
```

## `mini-homepage`

homepage dashboard answers on :3010

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-06` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:3010/
```

## `mini-healthchecks`

healthchecks answers on :8001

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-07` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8001/
```

## `mini-uptime-kuma`

uptime-kuma answers on :3001

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-08` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:3001/
```

## `mini-wallabag`

wallabag answers on :8085

- **host:** `mini` · **severity:** `warn` · **guards task:** `read-07` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8085/
```

## `mini-miniflux`

miniflux answers on :8082

- **host:** `mini` · **severity:** `warn` · **guards task:** `read-14` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8082/
```

## `mini-miniflux-feeds-fresh`

miniflux scheduler polled a feed within 3h

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-33` · **enabled:** True
- **expects:** `^t$`

```bash
docker exec miniflux_db psql -U miniflux -d miniflux -tA -c "SELECT max(checked_at) > now() - interval '3 hours' FROM feeds"
```

## `mini-miniflux-articles-flowing`

miniflux ingested at least one article in 48h

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-33` · **enabled:** True
- **expects:** `^t$`

```bash
docker exec miniflux_db psql -U miniflux -d miniflux -tA -c "SELECT count(*) > 0 FROM entries WHERE created_at > now() - interval '48 hours'"
```

## `mini-miniflux-no-bootstrap-admin`

miniflux has no leftover bootstrap 'admin' user

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-33` · **enabled:** True
- **expects:** `^0$`

```bash
docker exec miniflux_db psql -U miniflux -d miniflux -tA -c "SELECT count(*) FROM users WHERE username='admin'"
```

## `mini-container-dns`

docker embedded DNS resolves external names from a container

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-33` · **enabled:** True
- **expects:** `^OK$`

```bash
docker exec miniflux_db nslookup miniflux.app 127.0.0.11 >/dev/null 2>&1 && echo OK
```

## `mini-mealie`

mealie answers on :9000

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-11` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:9000/
```

## `mini-navidrome`

navidrome answers on :4533

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-03` · **enabled:** True
- **expects:** `^302$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:4533/
```

## `mini-seerr`

jellyseerr/overseerr answers on :5055

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-02` · **enabled:** True
- **expects:** `^307$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:5055/
```

## `mini-tautulli`

tautulli answers on :8181

- **host:** `mini` · **severity:** `warn` · **guards task:** `media-02` · **enabled:** True
- **expects:** `^303$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8181/
```

## `mini-beszel`

beszel monitoring answers on :8090

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-13` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8090/
```

## `mini-dockge`

dockge answers on :5001

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:5001/
```

## `romm-serving`

RomM answers its heartbeat with a version (functional, not just container-up)

- **host:** `mini` · **severity:** `warn` · **guards task:** `retro-02` · **enabled:** True
- **expects:** `^romm=ok:`

```bash
curl -sf --max-time 10 http://localhost:8998/api/heartbeat 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('SYSTEM') or {}; v=s.get('VERSION') or ''; print('romm=ok:'+v if v else 'romm=BAD')" 2>/dev/null || echo romm=BAD
```

## `romm-retroachievements`

RomM reports RetroAchievements enabled (RA_API_ENABLED true in heartbeat)

- **host:** `mini` · **severity:** `warn` · **guards task:** `retro-02` · **enabled:** True
- **expects:** `^ra=on$`

```bash
curl -sf --max-time 10 http://localhost:8998/api/heartbeat 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); m=d.get('METADATA_SOURCES') or {}; print('ra=on' if m.get('RA_API_ENABLED') else 'ra=OFF')" 2>/dev/null || echo ra=OFF
```

## `metube-serving`

metube backend + yt-dlp loaded (:8081/version, not just the SPA)

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-02` · **enabled:** True
- **expects:** `"yt-dlp": "[0-9]`

```bash
curl -s -m 8 http://localhost:8081/version | grep -o '"yt-dlp": "[0-9.]*"' || echo METUBE_BAD
```

## `bgutil-pot-serving`

bgutil POT provider serving (:4416/ping — YouTube token dep for pinchflat)

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-02` · **enabled:** True
- **expects:** `"version":"[0-9]`

```bash
docker exec caddy wget -qO- --timeout=8 http://bgutil-pot:4416/ping | grep -o '"version":"[0-9.]*"' || echo BGUTIL_BAD
```

## `mini-wiki-rag-fresh`

wiki->OWUI RAG sync ran clean in the last 26h (homelab-wiki fresh)

- **host:** `mini` · **severity:** `warn` · **guards task:** `ai-01` · **enabled:** True
- **expects:** `RAG_FRESH`

```bash
st=$(systemctl show wiki-rag-sync.service -p ExecMainStatus --value); age=$(( $(date +%s) - $(stat -c %Y /var/lib/verification/wiki-rag-state.json 2>/dev/null || echo 0) )); echo "exit=$st age_h=$(( age / 3600 ))"; [ "$st" = "0" ] && [ "$age" -lt 93600 ] && echo RAG_FRESH || echo RAG_STALE
```

## `mini-root-fs-writable`

mini root filesystem is READ-WRITE (real write probe — silent RO/ENOSPC tripwire)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-20` · **enabled:** True
- **expects:** `write=OK root=rw`

```bash
p="/home/btabaska/.verify-rw-probe"; if ( : > "$p" ) 2>/dev/null; then rm -f "$p"; w=OK; else w=FAIL; fi; echo "write=$w root=$(findmnt -no OPTIONS / | cut -d, -f1)"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

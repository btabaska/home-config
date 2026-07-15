# Checks — mini-services

`foss-setup/verification/checks.d/mini-services.yaml` — 20 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `mini-caddy-running`

caddy reverse proxy container running

- **host:** `mini` · **severity:** `crit` · **guards task:** `docker-02` · **enabled:** True
- **expects:** `^running$`

```bash
docker inspect -f '{{.State.Status}}' caddy
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

## `mini-vaultwarden`

vaultwarden web vault answers at https://vault.tabaska.us

- **host:** `mini` · **severity:** `crit` · **guards task:** `docker-14` · **enabled:** True
- **expects:** `^200$`

```bash
curl -sk -o /dev/null -m 8 -w '%{http_code}' --resolve vault.tabaska.us:443:127.0.0.1 https://vault.tabaska.us/
```

## `romm-serving`

RomM answers its heartbeat with a version (functional, not just container-up)

- **host:** `mini` · **severity:** `warn` · **guards task:** `retro-02` · **enabled:** True
- **expects:** `^romm=ok:`

```bash
curl -sf --max-time 10 http://localhost:8998/api/heartbeat 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('SYSTEM') or {}; v=s.get('VERSION') or ''; print('romm=ok:'+v if v else 'romm=BAD')" 2>/dev/null || echo romm=BAD
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

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

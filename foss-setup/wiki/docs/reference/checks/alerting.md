# Checks — alerting

`foss-setup/verification/checks.d/alerting.yaml` — 11 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `alert-ntfy-healthy`

ntfy serving and healthy via vhost

- **host:** `url` · **severity:** `crit` · **guards task:** `docker-09` · **enabled:** True
- **expects:** `"healthy"\s*:\s*true`

```bash
curl -sk -m 8 https://ntfy.tabaska.us/v1/health
```

## `alert-ntfy-upstream-relay`

ntfy iOS upstream relay configured (NTFY_UPSTREAM_BASE_URL)

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-09` · **enabled:** True
- **expects:** `ntfy\.sh`

```bash
docker exec ntfy sh -c 'printenv NTFY_UPSTREAM_BASE_URL' | grep -x 'https://ntfy.sh'
```

## `alert-diun-mini-up`

Diun (mini) container healthy

- **host:** `mini` · **severity:** `warn` · **guards task:** `docker-12` · **enabled:** True
- **expects:** `^healthy$`

```bash
docker inspect -f '{{.State.Health.Status}}' diun
```

## `alert-diun-nas-up`

Diun (NAS) container running

- **host:** `nas` · **severity:** `warn` · **guards task:** `docker-12` · **enabled:** True
- **expects:** `^running$`

```bash
sudo -n /usr/local/bin/docker inspect -f '{{.State.Status}}' diun
```

## `alert-healthchecks-checks-defined`

Healthchecks has its dead-man checks (>=6) and ntfy channel

- **host:** `mini` · **severity:** `warn` · **guards task:** `sec-03` · **enabled:** True
- **expects:** `checks=([6-9]|[1-9][0-9]+) ntfy=[1-9]`

```bash
docker exec healthchecks python3 /opt/healthchecks/manage.py shell -c "from hc.api.models import Check, Channel; print('checks='+str(Check.objects.count()), 'ntfy='+str(Channel.objects.filter(kind='ntfy').count()))"
```

## `alert-healthchecks-none-down`

no Healthchecks check is in 'down' state

- **host:** `mini` · **severity:** `crit` · **guards task:** `sec-03` · **enabled:** True
- **expects:** `^down=0$`

```bash
docker exec healthchecks python3 /opt/healthchecks/manage.py shell -c "from hc.api.models import Check; print('down='+str(sum(1 for c in Check.objects.all() if c.get_status()=='down')))"
```

## `alert-dsm-immich-task-scheduled`

DSM crontab still carries the immich dump task (DSM wipes raw cron lines)

- **host:** `nas` · **severity:** `crit` · **guards task:** `nas-08` · **enabled:** True
- **expects:** `^1$`

```bash
grep -c 'synoschedtask --run id=9' /etc/crontab
```

## `alert-dsm-health-task-allday`

DSM docker-health task runs all day (last-work-hour regression guard)

- **host:** `nas` · **severity:** `warn` · **guards task:** `nas-08` · **enabled:** True
- **expects:** `^1$`

```bash
grep 'synoschedtask --run id=5' /etc/crontab | grep -c '0,1,2'
```

## `media-youtube-mounts-rw`

YouTube pipeline mounts writable (pinchflat + metube + audio)

- **host:** `mini` · **severity:** `warn` · **guards task:** `read-14` · **enabled:** True
- **expects:** `^RW_OK$`

```bash
touch /mnt/nas-youtube/.verif-probe /mnt/nas-music-rw/YouTube/.verif-probe && rm /mnt/nas-youtube/.verif-probe /mnt/nas-music-rw/YouTube/.verif-probe && echo RW_OK
```

## `alert-kuma-none-down`

no Uptime Kuma monitor is down (47 fleet monitors seeded 2026-07-09)

- **host:** `mini` · **severity:** `warn` · **guards task:** `sec-03` · **enabled:** True
- **expects:** `^down=0$`

```bash
docker exec uptime-kuma mariadb --socket=/app/data/run/mariadb.sock kuma -N -e "SELECT CONCAT('down=', COUNT(*)) FROM monitor m JOIN heartbeat h ON h.id=(SELECT MAX(id) FROM heartbeat WHERE monitor_id=m.id) WHERE m.active=1 AND h.status=0;"
```

## `alert-beszel-none-down`

Beszel hub shows no system down (mini/nas/rig agents, seeded 2026-07-09)

- **host:** `mini` · **severity:** `warn` · **guards task:** `sec-03` · **enabled:** True
- **expects:** `^down=0$`

```bash
TOK=$(curl -s -m 8 -X POST http://localhost:8090/api/collections/_superusers/auth-with-password -H 'Content-Type: application/json' -d "{\"identity\":\"$BESZEL_ADMIN_USER\",\"password\":\"$BESZEL_ADMIN_PASSWORD\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])') && curl -s -m 8 -H "Authorization: $TOK" 'http://localhost:8090/api/collections/systems/records?filter=(status%3D%22down%22)' | python3 -c 'import json,sys; print("down="+str(json.load(sys.stdin)["totalItems"]))'
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

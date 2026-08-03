# Checks — alerting

`foss-setup/verification/checks.d/alerting.yaml` — 15 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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
docker exec healthchecks python3 /opt/healthchecks/manage.py shell -v 0 -c "from hc.api.models import Check, Channel; print('checks='+str(Check.objects.count()), 'ntfy='+str(Channel.objects.filter(kind='ntfy').count()))"
```

## `alert-healthchecks-none-down`

no Healthchecks dead-man is in 'down' state

- **host:** `mini` · **severity:** `crit` · **guards task:** `sec-03` · **enabled:** True
- **expects:** `^down_checks=NONE$`

```bash
docker exec healthchecks python3 /opt/healthchecks/manage.py shell -v 0 -c "from hc.api.models import Check; d=[c.name for c in Check.objects.all() if c.get_status()=='down']; print('down_checks='+(','.join(sorted(d)) if d else 'NONE'))"
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

## `alert-offmini-deadman-armed`

off-mini dead-man (rig watcher) is armed and fresh (SH19)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-63` · **enabled:** True
- **expects:** `armed age=[0-9]+s FRESH`

```bash
systemctl is-active --quiet mini-deadman.timer && hb=$(cat /var/lib/mini-deadman/heartbeat 2>/dev/null || echo 0) && age=$(( $(date +%s) - hb )) && echo "armed age=${age}s $([ "$age" -lt 1200 ] && echo FRESH || echo STALE)"
```

## `alert-wol-selfheal-fast-tier`

rig WoL self-heal wired into the fast tier (SM54)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-63` · **enabled:** True
- **expects:** `^WOL_FAST_TIER_OK$`

```bash
systemctl cat verification-fast.service 2>/dev/null | grep -q 'rig-wol-selfheal.sh' && test -x /opt/verification/bin/rig-wol-selfheal.sh && echo WOL_FAST_TIER_OK
```

## `alert-kuma-statuspage-nonempty`

Uptime Kuma 'fleet' status page is published and non-empty (SL23)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-63` · **enabled:** True
- **expects:** `groups=[1-9][0-9]* monitors=[1-9][0-9]*`

```bash
curl -s -m 8 http://localhost:3001/api/status-page/fleet | python3 -c 'import json,sys; d=json.load(sys.stdin); g=d.get("publicGroupList",[]) or []; m=sum(len(x.get("monitorList",[]) or []) for x in g); print(f"groups={len(g)} monitors={m}")'
```

## `alert-delivery-drill-fresh`

synthetic alert-delivery drill sent within the last 8 days (SM39)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-63` · **enabled:** True
- **expects:** `drill_age_days=[0-9]+ FRESH`

```bash
f=/var/lib/verification/alert-drill-last; test -f "$f" && s=$(sed -n 's/^sent_at=//p' "$f") && age=$(( ( $(date +%s) - $(date -d "$s" +%s) ) / 86400 )) && echo "drill_age_days=${age} $([ "$age" -le 8 ] && echo FRESH || echo STALE)"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

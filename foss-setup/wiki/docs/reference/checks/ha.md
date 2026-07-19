# Checks — ha

`foss-setup/verification/checks.d/ha.yaml` — 10 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `ha-http`

Home Assistant UI answers on :8123

- **host:** `mini` · **severity:** `crit` · **guards task:** `ha-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://192.168.10.50:8123/
```

## `ha-proxy-e2e`

ha.tabaska.us serves the HA frontend THROUGH caddy (proxy accepted, not 400)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-32` · **enabled:** True
- **expects:** `^<title>Home Assistant</title>$`

```bash
curl -sk -m 10 --resolve ha.tabaska.us:443:127.0.0.1 https://ha.tabaska.us/ | grep -o "<title>Home Assistant</title>" || echo HA_PROXY_BROKEN
```

## `ha-api-auth`

HA REST API authenticates (long-lived token valid)

- **host:** `mini` · **severity:** `warn` · **guards task:** `ha-32` · **enabled:** True
- **expects:** `^1$`

```bash
curl -s -m 8 -H "Authorization: Bearer $HA_TOKEN" http://192.168.10.50:8123/api/config | grep -c '"version"'
```

## `ha-hue-lights`

Hue integration healthy (>=50 light entities registered)

- **host:** `mini` · **severity:** `warn` · **guards task:** `ha-05` · **enabled:** True
- **expects:** `^([5-9][0-9]|[1-9][0-9]{2,})$`

```bash
curl -s -m 8 -H "Authorization: Bearer $HA_TOKEN" http://192.168.10.50:8123/api/states | grep -o '"entity_id":"light\.' | wc -l | tr -d ' '
```

## `ha-lights-available`

HA lights available (not a whole room dark; >12 unavailable = alert)

- **host:** `mini` · **severity:** `warn` · **guards task:** `ha-05` · **enabled:** True
- **expects:** `^lights_avail=ok$`

```bash
curl -s -m 12 -H "Authorization: Bearer $HA_TOKEN" http://192.168.10.50:8123/api/states | python3 -c "import sys,json; d=json.load(sys.stdin); n=sum(1 for e in d if e['entity_id'].startswith('light.') and e['state'] in ('unavailable','unknown')); print('lights_avail=ok' if n<=12 else 'lights_avail=DARK:%d'%n)"
```

## `ha-updates-pending`

HA updates not left pending >=21 days (core/OS/add-ons)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-36` · **enabled:** True
- **expects:** `^updates=ok$`

```bash
curl -s -m 12 -H "Authorization: Bearer $HA_TOKEN" http://192.168.10.50:8123/api/states | python3 -c "import sys,json,datetime; d=json.load(sys.stdin); now=datetime.datetime.now(datetime.timezone.utc); old=[e['entity_id'] for e in d if e['entity_id'].startswith('update.') and e['state']=='on' and (now-datetime.datetime.fromisoformat(e['last_changed'])).days>=21]; print('updates=ok' if not old else 'updates=STALE:'+','.join(old))"
```

## `ha-availability-drift`

HA entity availability matches accepted baseline (no silent integration death)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-36` · **enabled:** True
- **expects:** `^avail=ok$`

```bash
curl -s -m 12 -H "Authorization: Bearer $HA_TOKEN" http://192.168.10.50:8123/api/states | python3 -c "import sys,json,datetime; d=json.load(sys.stdin); now=datetime.datetime.now(datetime.timezone.utc); unav=[e for e in d if e['state']=='unavailable']; bt=[e for e in unav if e['entity_id'].startswith('sensor.btiphone_')]; lights=[e for e in unav if e['entity_id'].startswith('light.')]; other=[e['entity_id'] for e in unav if not e['entity_id'].startswith(('sensor.btiphone_','light.'))]; dark=[e['entity_id'] for e in lights if (now-datetime.datetime.fromisoformat(e['last_changed'])).days>=30]; msg=([('DRIFT:'+','.join(other))] if other else [])+([('BTIPHONE:%d'%len(bt))] if len(bt)>11 else [])+([('DARK30:'+','.join(dark))] if dark else []); print('avail=ok' if not msg else 'avail='+';'.join(msg))"
```

## `ha-iphone-presence`

iPhone companion presence pipeline alive (tracker + battery report real values)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-36` · **enabled:** True
- **expects:** `^presence=ok$`

```bash
curl -s -m 12 -H "Authorization: Bearer $HA_TOKEN" http://192.168.10.50:8123/api/states | python3 -c "import sys,json; d={e['entity_id']:e['state'] for e in json.load(sys.stdin)}; dt=d.get('device_tracker.brandon_iphone','missing'); bl=d.get('sensor.btiphone_battery_level','missing'); ok=dt not in ('missing','unavailable','unknown') and bl.replace('.','',1).isdigit(); print('presence=ok' if ok else 'presence=DEAD:dt=%s,batt=%s'%(dt,bl))"
```

## `ha-backup-offsite-fresh`

HA has an off-eMMC (NAS) backup < 48h old (dead-man)

- **host:** `mini` · **severity:** `crit` · **guards task:** `ha-11` · **enabled:** True
- **expects:** `^backup=fresh$`

```bash
c=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' bash -c 'find /volume1/backups -maxdepth 1 -name \"*.tar\" -mmin -2880 2>/dev/null | wc -l'" 2>/dev/null); c=$(echo "$c" | tr -d ' '); [ "${c:-0}" -ge 1 ] && echo backup=fresh || echo backup=STALE
```

## `ha-assist-rig-llm-reachable`

HA Assist LLM backend (rig Ollama) reachable + serves the configured model

- **host:** `mini` · **severity:** `warn` · **guards task:** `ha-12` · **enabled:** True
- **expects:** `^assist_llm=ok$`

```bash
curl -sm 15 http://192.168.10.12:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); ms=[m.get('name') for m in d.get('models',[])]; print('assist_llm=ok' if 'llama3.2:3b' in ms else 'assist_llm=MISSING')" 2>/dev/null || echo assist_llm=UNREACHABLE
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

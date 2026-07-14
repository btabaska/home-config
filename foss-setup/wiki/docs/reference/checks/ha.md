# Checks — ha

`foss-setup/verification/checks.d/ha.yaml` — 5 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `ha-http`

Home Assistant UI answers on :8123

- **host:** `mini` · **severity:** `crit` · **guards task:** `ha-01` · **enabled:** True
- **expects:** `^200$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' http://192.168.10.50:8123/
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

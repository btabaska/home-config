# Checks — monitoring-coverage

`foss-setup/verification/checks.d/monitoring-coverage.yaml` — 7 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `homepage-dead-tiles`

homepage has no tile pointing at a nonexistent container (M17 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-29` · **enabled:** True
- **expects:** `^DEAD_TILES=NONE$`

```bash
python3 /opt/verification/bin/homepage-tiles-resolve.py
```

## `homepage-widget-errors`

homepage renders 0 dead-tile DNS errors in the last 2h (M17 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-29` · **enabled:** True
- **expects:** `^errors=0$`

```bash
echo "errors=$(docker logs homepage --since 2h 2>&1 | grep -icE 'EAI_AGAIN|getaddrinfo')"
```

## `homepage-calendar-ics-fetch`

homepage container fetches the Proton Calendar .ics (home-08 Calendar consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `home-08` · **enabled:** True
- **expects:** `^BEGIN:VCALENDAR$`

```bash
docker exec homepage sh -c 'wget -qO- "$HOMEPAGE_VAR_PROTON_CAL_ICS" 2>/dev/null | head -c 15'
```

## `kuma-all-monitors-notified`

every active Uptime-Kuma monitor is linked to an alert channel (M21)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-29` · **enabled:** True
- **expects:** `^unlinked=0$`

```bash
docker exec uptime-kuma mariadb --socket=/app/data/run/mariadb.sock kuma -N -e "SELECT CONCAT('unlinked=', COUNT(*)) FROM monitor m LEFT JOIN monitor_notification mn ON mn.monitor_id=m.id WHERE m.active=1 AND mn.id IS NULL;"
```

## `unpackerr-poll-advancing`

unpackerr reaches every Starr app and its poll loop is advancing (L94)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-29` · **enabled:** True
- **expects:** `^UNPACKERR_OK`

```bash
python3 /opt/verification/bin/unpackerr-poll-advancing.py
```

## `beszel-notify-coherent`

beszel has no dead email path + keeps a live webhook channel (L28)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-29` · **enabled:** True
- **expects:** `^BESZEL_COHERENT_OK`

```bash
python3 /opt/verification/bin/beszel-notify-coherent.py
```

## `rig-litellm-consumer-e2e`

litellm returns a real completion to a virtual-key client (M57 consumer end)

- **host:** `rig` · **severity:** `warn` · **guards task:** `fix-29` · **enabled:** True
- **expects:** `^LITELLM_CONSUMER_OK`

```bash
set -a && . ~/.config/fleet-mcp/env && set +a && curl -s -m 90 http://localhost:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_VERIFY_KEY" -H 'Content-Type: application/json' -d '{"model":"utility","messages":[{"role":"user","content":"Reply with the single word PONG and nothing else."}],"max_tokens":16}' | python3 -c 'import sys,json; d=json.load(sys.stdin); c=(d.get("choices") or [{}])[0].get("message",{}).get("content") if isinstance(d,dict) else None; print("LITELLM_CONSUMER_OK "+repr((c or "").strip()) if (c and c.strip()) else "LITELLM_CONSUMER_FAIL "+json.dumps(d)[:180])'
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

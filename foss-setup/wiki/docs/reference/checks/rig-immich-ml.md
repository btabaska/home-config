# Checks — rig-immich-ml

`foss-setup/verification/checks.d/rig-immich-ml.yaml` — 4 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `immich-smart-search-consumer`

immich smart search returns results end-to-end (text-encode + vector search, any ML backend)

- **host:** `mini` · **severity:** `crit` · **guards task:** `nas-32` · **enabled:** True
- **expects:** `^SEARCH_OK$`

```bash
resp=$(curl -s -m 30 -X POST https://immich.tabaska.us/api/search/smart -H "x-api-key: $IMMICH_API_KEY" -H 'Content-Type: application/json' -d '{"query":"a photo of people outdoors"}' 2>/dev/null); printf '%s' "$resp" | grep -q '"id":' && echo SEARCH_OK || echo SEARCH_FAIL
```

## `rig-immich-ml-window`

rig immich-ml honors the night-only GPU window (up+encoding 01-07 EDT, off by day)

- **host:** `mini` · **severity:** `warn` · **guards task:** `nas-32` · **enabled:** True
- **expects:** `^(NIGHT_ENCODE_OK|DAY_OFF_OK)$`

```bash
H=$(TZ=America/New_York date +%H); ping=$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "curl -s -m 8 http://192.168.10.12:3003/ping" 2>/dev/null); if [ "$H" -ge 1 ] && [ "$H" -lt 7 ]; then enc=$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "curl -s -m 30 -X POST http://192.168.10.12:3003/predict -F 'entries={\"clip\":{\"textual\":{\"modelName\":\"ViT-B-16-SigLIP2__webli\"}}}' -F 'text=verification canary'" 2>/dev/null); printf '%s' "$enc" | grep -q '"clip":"\[' && echo NIGHT_ENCODE_OK || echo NIGHT_BROKEN; else printf '%s' "$ping" | grep -q pong && echo DAY_UNEXPECTED_UP || echo DAY_OFF_OK; fi
```

## `rig-immich-ml-configured`

immich server config still routes ML at the rig (URL not reverted to NAS-only)

- **host:** `mini` · **severity:** `warn` · **guards task:** `nas-32` · **enabled:** True
- **expects:** `^present$`

```bash
printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker exec immich_postgres psql -U postgres -d immich -tAc \"SELECT value FROM system_metadata WHERE key='system-config'\"" 2>/dev/null | grep -q 'http://192.168.10.12:3003' && echo present || echo MISSING
```

## `rig-immich-ml-version-match`

rig immich-ml -cuda image matches NAS immich-server version (no ML/server skew)

- **host:** `mini` · **severity:** `warn` · **guards task:** `nas-32` · **enabled:** True
- **expects:** `^match=v`

```bash
nas=$(curl -sm 8 http://nas:2283/api/server/version | sed -n 's/.*"major":\([0-9]*\),"minor":\([0-9]*\),"patch":\([0-9]*\).*/v\1.\2.\3/p'); rig=$(ssh -o BatchMode=yes -o ConnectTimeout=10 rig "docker inspect -f '{{.Config.Image}}' immich_machine_learning" 2>/dev/null | sed 's/.*://; s/-cuda$//'); [ -n "$nas" ] && [ "$nas" = "$rig" ] && echo "match=$nas" || echo "SKEW nas=${nas:-?} rig=${rig:-?}"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

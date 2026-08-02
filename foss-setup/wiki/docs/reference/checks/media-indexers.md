# Checks — media-indexers

`foss-setup/verification/checks.d/media-indexers.yaml` — 4 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `bitmagnet-dht-ingesting`

bitmagnet: DHT crawler ingested new torrents in the last 30min (rate > 0)

- **host:** `mini` · **severity:** `warn` · **guards task:** `seed-12` · **enabled:** True
- **expects:** `^ingesting=yes recent30m=[1-9][0-9]*$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker exec bitmagnet-postgres psql -U postgres -d bitmagnet -tAc \"SELECT count(*) FROM torrents WHERE created_at > now() - interval '30 minutes'\"" 2>/dev/null | tr -d '[:space:]'); { [ -n "$n" ] && [ "$n" -gt 0 ] && echo "ingesting=yes recent30m=$n"; } || echo "ingesting=NO recent30m=${n:-query_failed}"
```

## `bitmagnet-torznab-via-prowlarr`

bitmagnet: registered in Prowlarr + Torznab endpoint alive for manual search (consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-50` · **enabled:** True
- **expects:** `^BITMAGNET_PROWLARR_(OK|SLOW)`

```bash
python3 /opt/verification/bin/bitmagnet-torznab-probe.py
```

## `bitmagnet-demoted-interactive-only`

bitmagnet: RSS + automatic-search DISABLED in radarr & sonarr — no auto-grab path (fix-50 regression)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-50` · **enabled:** True
- **expects:** `^DEMOTED_OK`

```bash
python3 /opt/verification/bin/arr-grab-indexer-share.py demoted
```

## `arr-grab-source-not-storming`

arr grabs: no auto-grab-enabled indexer is monopolising the grab stream (fix-50 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-50` · **enabled:** True
- **expects:** `^SHARE_OK`

```bash
python3 /opt/verification/bin/arr-grab-indexer-share.py share
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

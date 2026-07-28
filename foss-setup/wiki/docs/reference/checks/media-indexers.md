# Checks — media-indexers

`foss-setup/verification/checks.d/media-indexers.yaml` — 2 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `bitmagnet-dht-ingesting`

bitmagnet: DHT crawler ingested new torrents in the last 30min (rate > 0)

- **host:** `mini` · **severity:** `warn` · **guards task:** `seed-12` · **enabled:** True
- **expects:** `^ingesting=yes recent30m=[1-9][0-9]*$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' /usr/local/bin/docker exec bitmagnet-postgres psql -U postgres -d bitmagnet -tAc \"SELECT count(*) FROM torrents WHERE created_at > now() - interval '30 minutes'\"" 2>/dev/null | tr -d '[:space:]'); { [ -n "$n" ] && [ "$n" -gt 0 ] && echo "ingesting=yes recent30m=$n"; } || echo "ingesting=NO recent30m=${n:-query_failed}"
```

## `bitmagnet-torznab-via-prowlarr`

bitmagnet: registered in Prowlarr + Torznab search returns real hits (consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `seed-12` · **enabled:** True
- **expects:** `^BITMAGNET_PROWLARR_OK indexer=[0-9]+ hits=[1-9][0-9]*$`

```bash
K=$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "grep -oE '<ApiKey>[a-f0-9]+</ApiKey>' /volume1/docker/prowlarr/config/config.xml" 2>/dev/null | sed 's/<[^>]*>//g'); [ -n "$K" ] || { echo 'no_prowlarr_key'; exit 0; }; ID=$(curl -s -H "X-Api-Key: $K" http://192.168.10.4:9696/api/v1/indexer | python3 -c "import sys,json;print(next((i['id'] for i in json.load(sys.stdin) if i['name']=='Bitmagnet (DHT)'),''))"); [ -n "$ID" ] || { echo 'BITMAGNET_NOT_REGISTERED'; exit 0; }; N=$(curl -s -H "X-Api-Key: $K" "http://192.168.10.4:9696/api/v1/search?query=1080p&indexerIds=$ID&limit=5" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null); { [ -n "$N" ] && [ "$N" -gt 0 ] && echo "BITMAGNET_PROWLARR_OK indexer=$ID hits=$N"; } || echo "BITMAGNET_PROWLARR_FAIL hits=${N:-err}"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

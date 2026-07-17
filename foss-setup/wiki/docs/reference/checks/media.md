# Checks — media

`foss-setup/verification/checks.d/media.yaml` — 16 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `music-library-dupes`

music library has no duplicate album folders (year/case/unicode collisions)

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^DUPES_OK`

```bash
python3 /opt/verification/bin/music-dupes.py /mnt/nas/music
```

## `sonarr-queue-stuck`

sonarr: import queue not clogged (<=5 items stuck in warning state)

- **host:** `url` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^stuck=[0-5]$`

```bash
curl -sm 20 -H "X-Api-Key: $SONARR_API_KEY" "http://192.168.10.4:8989/api/v3/queue?pageSize=200" | python3 -c "import json,sys; d=json.load(sys.stdin); print('stuck=%d' % sum(1 for r in d.get('records',[]) if r.get('trackedDownloadStatus')=='warning'))"
```

## `sonarr-indexer-redundancy`

sonarr has >=3 search-enabled indexers (no IPT-only single point of failure)

- **host:** `url` · **severity:** `warn` · **guards task:** `seed-11` · **enabled:** True
- **expects:** `^searchable=(?:[3-9]|[1-9][0-9]+)$`

```bash
curl -sm 20 -H "X-Api-Key: $SONARR_API_KEY" "http://192.168.10.4:8989/api/v3/indexer" | python3 -c "import json,sys; d=json.load(sys.stdin); print('searchable=%d' % sum(1 for i in d if i.get('enableAutomaticSearch')))"
```

## `radarr-queue-stuck`

radarr: import queue not clogged (<=5 items stuck in warning state)

- **host:** `url` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^stuck=[0-5]$`

```bash
curl -sm 20 -H "X-Api-Key: $RADARR_API_KEY" "http://192.168.10.4:7878/api/v3/queue?pageSize=200" | python3 -c "import json,sys; d=json.load(sys.stdin); print('stuck=%d' % sum(1 for r in d.get('records',[]) if r.get('trackedDownloadStatus')=='warning'))"
```

## `sonarr-pipeline-health`

sonarr: no download-client/root-folder/remote-path/import health issues

- **host:** `url` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^pipeline=ok$`

```bash
curl -sm 20 -H "X-Api-Key: $SONARR_API_KEY" "http://192.168.10.4:8989/api/v3/health" | python3 -c "import json,sys,re; h=json.load(sys.stdin); bad=sorted({i['source'] for i in h if re.match(r'(DownloadClient|RootFolder|RemotePathMapping|ImportMechanism)', i.get('source',''))}); print('pipeline=' + (','.join(bad) if bad else 'ok'))"
```

## `radarr-pipeline-health`

radarr: no download-client/root-folder/remote-path/import health issues

- **host:** `url` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^pipeline=ok$`

```bash
curl -sm 20 -H "X-Api-Key: $RADARR_API_KEY" "http://192.168.10.4:7878/api/v3/health" | python3 -c "import json,sys,re; h=json.load(sys.stdin); bad=sorted({i['source'] for i in h if re.match(r'(DownloadClient|RootFolder|RemotePathMapping|ImportMechanism)', i.get('source',''))}); print('pipeline=' + (','.join(bad) if bad else 'ok'))"
```

## `seedbox-mount-listable`

nas: rclone seedbox mount lists content within 15s (imports depend on it)

- **host:** `mini` · **severity:** `crit` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^mount=ok$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' timeout 15 ls /volume1/mounts/seedbox-files/tv 2>/dev/null | head -1" 2>/dev/null); [ -n "$n" ] && echo mount=ok || echo mount=DEAD
```

## `pinchflat-plex-visible`

pinchflat: archived YouTube videos are visible in Plex (disk vs library)

- **host:** `mini` · **severity:** `crit` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^COVERAGE_OK`

```bash
PLEX_URL="$PLEX_URL" PLEX_TOKEN="$PLEX_TOKEN" python3 /opt/verification/bin/plex-flat-library-coverage.py --disk /mnt/nas-youtube/pinchflat --section 4 --min-ratio 0.8
```

## `plex-youtube-readable`

nas: Plex service user can traverse the youtube share (ACL invariant)

- **host:** `mini` · **severity:** `crit` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^plexacl=ok$`

```bash
r=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' sudo -u PlexMediaServer test -x /volume1/youtube && echo yes" 2>/dev/null); [ "$r" = "yes" ] && echo plexacl=ok || echo plexacl=BAD
```

## `readarr-cwa-copy-drops`

readarr->cwa copy script dropped no books (no path-resolution errors)

- **host:** `mini` · **severity:** `crit` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^drops=0$`

```bash
c=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' grep -cE 'ERROR - (Not a file|.*no name match)' /volume1/docker/readarr/config/logs/readarr-copy-to-cwa-ingest.log 2>/dev/null" 2>/dev/null); [ "${c:-0}" = "0" ] && echo drops=0 || echo drops=$c
```

## `cwa-ingest-not-stuck`

cwa: book-ingest folder is being consumed (nothing stuck >20m)

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^ingest=ok$`

```bash
n=$(printf '%s\n' "$NAS_SUDO_PASSWORD" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' find /volume1/docker/calibre-web-automated/ingest -type f -mmin +20 2>/dev/null | wc -l" 2>/dev/null); n=$(echo "$n" | tr -d ' '); [ "${n:-1}" = "0" ] && echo ingest=ok || echo ingest=STUCK:$n
```

## `radarr-movies-in-plex`

radarr: imported movies are actually served in Plex (tmdb-id coverage)

- **host:** `mini` · **severity:** `crit` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^COVERAGE_OK`

```bash
python3 /opt/verification/bin/arr-plex-journey.py --kind radarr --arr-url http://192.168.10.4:7878 --arr-key "$RADARR_API_KEY" --plex-url "$PLEX_URL" --plex-token "$PLEX_TOKEN" --section 1 --min-ratio 0.85
```

## `sonarr-tv-in-plex`

sonarr: imported series are actually served in Plex (tvdb-id coverage)

- **host:** `mini` · **severity:** `crit` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^COVERAGE_OK`

```bash
python3 /opt/verification/bin/arr-plex-journey.py --kind sonarr --arr-url http://192.168.10.4:8989 --arr-key "$SONARR_API_KEY" --plex-url "$PLEX_URL" --plex-token "$PLEX_TOKEN" --section 2 --min-ratio 0.85
```

## `musicseerr-phantom-requests`

musicseerr: no request stuck 'downloading' while unmonitored in Lidarr

- **host:** `mini` · **severity:** `warn` · **guards task:** `verify-06` · **enabled:** True
- **expects:** `^PHANTOM_OK`

```bash
LIDARR_URL="$LIDARR_URL" LIDARR_API_KEY="$LIDARR_API_KEY" python3 /opt/verification/bin/musicseerr-phantom-requests.py
```

## `arr-grabbed-not-imported`

*arr: no silent grabbed-never-imported downloads >48h (H3/H5 class)

- **host:** `mini` · **severity:** `crit` · **guards task:** `fix-25` · **enabled:** True
- **expects:** `^GRABS_OK`

```bash
python3 /opt/verification/bin/arr-grab-audit.py grabs
```

## `arr-orphan-monitor-flags`

*arr: no monitored+fileless media hidden from wanted by unmonitored parent (H6/H14 class)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-25` · **enabled:** True
- **expects:** `^FLAGS_OK`

```bash
python3 /opt/verification/bin/arr-grab-audit.py monitor-flags
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

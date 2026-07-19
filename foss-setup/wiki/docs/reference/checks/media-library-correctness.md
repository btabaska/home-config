# Checks — media-library-correctness

`foss-setup/verification/checks.d/media-library-correctness.yaml` — 6 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `plex-unmatched-items`

plex: 0 movies/shows with no external-id match (M32 — mangled/invisible)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-28` · **enabled:** True
- **expects:** `^UNMATCHED_OK`

```bash
python3 /opt/verification/bin/plex-unmatched-items.py
```

## `arr-plex-parity`

arr->plex: every movie/series with files is present in Plex (M33)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-28` · **enabled:** True
- **expects:** `^PARITY_OK`

```bash
python3 /opt/verification/bin/arr-plex-parity.py
```

## `lidarr-incomplete-albums`

lidarr: 0 monitored albums served partial-on-disk (M34)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-28` · **enabled:** True
- **expects:** `^ALBUMS_OK`

```bash
python3 /opt/verification/bin/lidarr-incomplete-albums.py
```

## `navidrome-recycle-rows`

navidrome: 0 library rows under #recycle (deleted-content leak)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-28` · **enabled:** True
- **expects:** `^RECYCLE_OK`

```bash
python3 /opt/verification/bin/navidrome-recycle-rows.py
```

## `arr-unmapped-folders-growth`

radarr/sonarr: unmapped root folders at accepted baseline (39/13)

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^UNMAPPED_OK`

```bash
python3 -c "import json,os,urllib.request; g=lambda url,key: json.load(urllib.request.urlopen(urllib.request.Request(url,headers={'X-Api-Key':key}),timeout=20)); u=lambda d: sum(len(r.get('unmappedFolders') or []) for r in d); r=u(g('http://192.168.10.4:7878/api/v3/rootfolder',os.environ['RADARR_API_KEY'])); s=u(g('http://192.168.10.4:8989/api/v3/rootfolder',os.environ['SONARR_API_KEY'])); print(('UNMAPPED_OK' if r<=39 and s<=13 else 'UNMAPPED_GREW')+' radarr=%d sonarr=%d'%(r,s))"
```

## `sonarr-unmanaged-profile`

sonarr: no monitored series on the unmanaged 'Any' profile

- **host:** `mini` · **severity:** `warn` · **guards task:** `fix-45` · **enabled:** True
- **expects:** `^PROFILE_OK`

```bash
python3 -c "import json,os,urllib.request; req=urllib.request.Request('http://192.168.10.4:8989/api/v3/series',headers={'X-Api-Key':os.environ['SONARR_API_KEY']}); d=json.load(urllib.request.urlopen(req,timeout=20)); bad=[s['title'] for s in d if s.get('monitored') and s.get('qualityProfileId')==1]; print('PROFILE_OK n=0' if not bad else 'PROFILE_BAD '+','.join(bad[:5]))"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

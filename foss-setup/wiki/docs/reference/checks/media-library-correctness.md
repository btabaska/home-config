# Checks — media-library-correctness

`foss-setup/verification/checks.d/media-library-correctness.yaml` — 4 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

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

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)

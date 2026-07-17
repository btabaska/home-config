# Runbook — Plex / Navidrome library correctness (unmatched, partial, #recycle)

**Task:** `fix-28` · **Findings:** M32, M33, M34 (+ Navidrome/#recycle hygiene) · **Hosts:** nas (Sonarr/Radarr/Lidarr → Plex), mini (Navidrome)

## The failure class

Everything is green — Plex is up, Radarr/Sonarr/Lidarr are up, the files are on disk —
yet the item is **wrong at the consumer end**:

- **M32** — a movie is in Plex but carries **no external-id match** (`guid=local://`, no
  `<Guid>`). It plays, but shows a mangled title/no artwork and is invisible to guid-based
  checks and seerr availability sync. Cause: junk filenames the Plex Movie agent can't parse
  (multi-movie "pack" folders, brace-years `{1997}`, mangled names like `Star Trek10 … Nemesis`).
- **M33** — an *arr series has files and is 100% monitored, but is **absent or mismatched in
  Plex**: *Over the Garden Wall* imported as `Part01…Part10` (no `SxxExx`) so the Plex TV
  scanner never built the show; a wrong Sonarr series (tvdb 73817 "The Scooby-Doo Show") was
  mapped over lower-quality `[cedar]` `.avi` rips of *Where Are You!* that Plex already had as a
  BluRay set (duplicated); *Delicious in Dungeon* played but the show fell to a `local://` match.
- **M34** — a monitored album is served **silently incomplete** (17/18 tracks) because the
  source download was missing a track. Lidarr is green (album has files, auto-searching), so
  nothing pages, but Plex/Navidrome serve the incomplete album.
- **Hygiene** — the NAS music mount exposes Synology's `#recycle` bin; Navidrome indexed
  user-deleted tracks from it as live, searchable library rows.

Liveness monitoring missed **all** of these — the boxes were up and the files were "present."
The existing `arr-plex-journey.py` also missed M32/M33 because it passes on a coverage
**ratio**: a handful of unmatched items stayed under the threshold.

## Fixing each class

### M32 — a Plex movie/show with no external id (`local://`)

Plex "Fix Match" pins the correct metadata (a manual match is **locked** — Plex won't
auto-rematch it). Via the API (token in vault `plex.token`):

```
# find candidates (Movie agent):
GET  /library/metadata/{ratingKey}/matches?manual=1&title=<clean title>&year=<year>
# apply the chosen plex://movie|show guid:
PUT  /library/metadata/{ratingKey}/match?guid=<plex://…>&name=<name>
PUT  /library/metadata/{ratingKey}/refresh          # populate tmdb/imdb/year/art
```

If the server-agent search can't find the title (it happened for *The Happytime Murders* —
the file said "Happy Time", canonical is one word "Happytime"), search Plex Discover for the
real guid:

```
GET https://discover.provider.plex.tv/library/search?query=<t>&searchTypes=movies&searchProviders=discover&includeMetadata=1
```

Always **verify after applying**: re-GET the item and confirm `guid` is now `plex://…` and a
`tmdb://` child appeared. Do **not** delete these — each of the fix-28 nine was the *sole copy*
of that film; deletion would lose it.

### M33 — an *arr series with files missing/wrong in Plex

- **Absent because of naming** (Over the Garden Wall, `PartNN`): let Sonarr rename to `SxxExx`
  so the Plex TV scanner can build the show, then scan:
  ```
  GET  /api/v3/rename?seriesId=<id>            # preview episodeFileIds
  POST /api/v3/command {"name":"RenameFiles","seriesId":<id>,"files":[ids]}
  GET  {plex}/library/sections/2/refresh       # incremental TV scan (GET, not PUT)
  ```
- **Wrong Sonarr series over duplicate files** (Scooby `[cedar]` avi): if the episodes already
  exist in Plex from a better copy, **verify the good copy is present & playable first**, then
  retire the redundant series+files: `DELETE /api/v3/series/<id>?deleteFiles=true`. Sonarr's
  recycle bin is unset, so this hard-deletes — the safety net is the confirmed replacement,
  never the delete itself.
- **Plex `local://` match** (Delicious in Dungeon): same Fix-Match flow as M32 but on the show
  ratingKey with a `plex://show/…` guid.

> **Always resolve the *arr series id by `tvdbId`, never trust a remembered id** — a stale id
> here means renaming/deleting the wrong show. `GET /api/v3/series` then filter by `tvdbId`.

### M34 — an album served partial

The album is already monitored, so it auto-searches. Trigger one manual search and **watch the
queue** — do not blindly let a full-album grab replace a good rip with a worse one:

```
POST /api/v1/command {"name":"AlbumSearch","albumIds":[<id>]}
GET  /api/v1/queue?pageSize=200          # inspect quality before it imports
```

Accept the grab only if it's an equal-or-better quality that *completes* the album (a lossless
WEB release replacing an incomplete lossless rip is fine); cancel a downgrade. If nothing clean
surfaces, leave it monitored and document — do not force-replace for a single missing track.

### Navidrome indexing `#recycle`

The 0.62 "new scanner" does **not** honor `ND_IGNOREDPATTERNS`. The working guard is an empty
`.ndignore` marker in the offending folder:

```
touch "/volume1/music/#recycle/.ndignore"     # skip the whole folder
# purge already-indexed rows (ignore != missing, so a rescan won't remove them):
docker exec navidrome sh -c 'sqlite3 /data/navidrome.db "delete from media_file where path like \"#recycle%\""'
docker exec navidrome navidrome scan --full    # confirm rows stay gone
```

## Monitoring — the checks that now catch this class

`verification/checks.d/media-library-correctness.yaml` (host `mini`, route → ntfy `verification`):

| check | asserts | script |
|-------|---------|--------|
| `plex-unmatched-items` | 0 items in Movies+TV with no external id (M32) | `plex-unmatched-items.py` |
| `arr-plex-parity` | every Radarr/Sonarr item with files is present in Plex (M33) | `arr-plex-parity.py` |
| `lidarr-incomplete-albums` | 0 monitored albums served partial-on-disk (M34) | `lidarr-incomplete-albums.py` |
| `navidrome-recycle-rows` | 0 Navidrome rows under `#recycle` | `navidrome-recycle-rows.py` |

`arr-plex-parity` is the strict, zero-tolerance per-item complement to `arr-plex-journey`'s
ratio check. It treats "present under a different external id" (dual TMDB/TVDB records,
imdb-only matches, festival-vs-release year drift ±2) as **covered** — the defect it flags is a
title **absent** from Plex entirely. Fresh imports (<24 h) are excluded for scan lag.

Run them ad-hoc on `mini`:

```
set -a; source /etc/verification/env; set +a
python3 /opt/verification/bin/arr-plex-parity.py       # PARITY_OK …
python3 /opt/verification/bin/plex-unmatched-items.py  # UNMATCHED_OK …
python3 /opt/verification/bin/lidarr-incomplete-albums.py
python3 /opt/verification/bin/navidrome-recycle-rows.py
```

## When a check fires

- `PARITY_BAD movie:'X'(year)` / `show:'X'` → the title isn't in Plex. Check the *arr file is on
  disk and named sanely; for TV confirm `SxxExx` naming (rename via Sonarr); then scan Plex. If
  it's genuinely a different-id-but-present case, the ±2/title logic should already cover it —
  if not, widen deliberately, don't allowlist silently.
- `UNMATCHED_BAD` → Fix-Match the listed item(s) (M32 flow above).
- `ALBUMS_BAD 'Artist - Album'(n/total)` → manual `AlbumSearch`, supervise the grab.
- `RECYCLE_BAD` → the `.ndignore` marker was removed or a new junk dir appeared; re-add it and
  purge rows.

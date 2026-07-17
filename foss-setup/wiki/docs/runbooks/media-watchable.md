# Runbook — "green but not watchable" (sample / ISO / un-extracted RAR imports)

**Task:** `fix-27` · **Findings:** H11, H12, H13, H30, M27, M31, M60 · **Host:** nas (Sonarr/Radarr/unpackerr) → Plex

## The failure class

Sonarr/Radarr report `hasFile=True` (item is green, nothing in wanted/missing) while the
file they actually track is **not a watchable video**:

- a scene **`Sample/*.avi`** (5–30 MB) — the real episode/movie sat un-extracted in a
  `.rar` set right next to it;
- a **`.iso`** disc image — Plex cannot index ISOs, so the title is invisible;
- an **un-extracted `.rar`** as the only copy of a wanted movie;
- a **mis-mapped file** — e.g. Radarr's *All About My Mother* pointed at the *Mamma Mia! 2008* file;
- a **stuck partial** (`~uTorrentPartFile*.dat`) tracked as the episode.

Because the *arr is green, nothing re-grabs it automatically, and container-liveness
monitoring never noticed — the whole class was invisible until the 2026-07-16 audit swept
every `episodeFile`/`movieFile` against the on-disk reality and Plex.

## Root cause

1. The **2026-06-28 bulk library-scan import** walked the pre-existing on-disk library and
   accepted whatever video it found in each release folder — the small `Sample/` file (real
   content was an un-extracted scene RAR) or a fuzzy-matched wrong file. Custom-format
   rejection (recyclarr's `Extras`/`BR-DISK` = −10000) applies to **grabs**, not to a bare
   disk scan, so samples/ISOs walked straight in.
2. **unpackerr is queue-driven** — it polls each *arr's download *queue* and extracts there.
   RARs that already sit **inside the library roots** (`/volume3/tv`, `/volume2/movies`) are
   never in a queue, so unpackerr can never reach them (M60: 606 `.rar/.r00` sets, 252 dirs
   with no playable video).
3. **whisparr had no unpackerr block** (M27) — a rar'd adult grab would have stalled the same way.

## Remediation pattern (how fix-27 resolved it, and how to fix a recurrence)

Per item, in order of preference:

1. **Real file already alongside the sample** → delete the sample record, `ManualImport` the
   real file. (Radarr/Sonarr `DELETE …/{movie,episode}file/{id}` deletes the record *and* the
   physical sample file.)
2. **Real content is an un-extracted RAR alongside** → `unrar x -o+` in the release dir, then
   delete sample + `ManualImport` the extracted video to its episode range (multi-episode scene
   files like `S03E07-10` map to all four episodeIds).
3. **No recoverable real** (pure sample, ISO-in-RAR, subs-only, corrupt archive, stuck `.dat`)
   → delete the record so the item flips to **honest missing** (`hasFile=False`, monitored),
   which lets the normal pipeline re-grab it. **Never** delete a shared real file — H13's file
   was *Mamma Mia's*; it was reassigned (added Mamma Mia to Radarr, `ManualImport` moved the
   file to it) so AAMM became honest-missing without destroying the movie.

> **ManualImport gotcha:** the POST `files[]` entry MUST include `languages` (e.g.
> `[{"id":1,"name":"English"}]`) — Sonarr's `EpisodeFiles.Languages` column is NOT NULL and the
> import throws a SQLite constraint error (approved but not imported) without it.

Extraction is NAS-local disk I/O only (both library volumes had 8 TB free); the library RARs are
**not** the seeding copies (those live on the seedbox), so extracting in place is seed-safe.

## Prevention

- **Grab-time (already in place):** recyclarr's `HD Bluray + WEB` (Radarr) / `WEB-1080p`
  (Sonarr) profiles score `BR-DISK` and `Extras` at −10000, so sample/ISO *releases* are
  rejected. This does not cover a manual bulk disk-scan.
- **Detective (the real guard):** the `media-arr-file-quality` check below is a hard tripwire —
  it makes the silent class loud. **Do not run a bare "import existing library" scan** without
  re-running the check afterward.

## The checks (`verification/checks.d/media-watchable.yaml`)

| id | what it proves | host |
|----|----------------|------|
| `media-arr-file-quality` | no `hasFile` item points at a sample/iso/rar/partial/stub (class) | mini → arr APIs |
| `media-gossip-girl-in-plex` | the H11 flagship actually resolves in Plex with its episode count (regression, consumer end) | mini → Plex |
| `media-extraction-backlog` | library isn't accumulating un-extractable rar-only dirs (M60) | nas |
| `unpackerr-whisparr-block` | the M27 whisparr block survives unpackerr redeploys | nas |

Script: `/opt/verification/bin/arr-file-quality.py` (repo:
`foss-setup/verification/bin/arr-file-quality.py`). Deliberately flags only *unambiguous*
signals (whole-word `sample`, `/Sample/` dir, `.iso/.rar/.zip`, partial extensions, <3 MB stub)
— legit short-form content and episode titles containing a word like "Trailer" do not trip it.

## Known residual (honestly missing, not falsely green)

Corrupt/un-recoverable sources left honestly missing for the normal pipeline to re-grab:
*The Matrix Resurrections* (2160p, CRC-failed RAR), *Animaniacs S03E01-06* (CRC-failed RAR),
*Castle in the Sky* / *The Addams Family* (RAR contains only an ISO), *The Intouchables*
(only a subs RAR on disk).

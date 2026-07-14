# Runbook — Acceptance testing (end-to-end user journeys)

The layer above [Verification](verification.md). Verification proves a service
is **alive** (container up, port 200, upstream reachable). Acceptance testing
proves the **user actually gets what they asked for** — that a requested album
became playable, a scanned document became searchable, an archived video became
watchable. Same runner, same `checks.d/*.yaml` schema, same hourly cadence — a
different *question*.

!!! success "Status: LIVE (seeded from 3 incidents)"
    Acceptance checks live in `checks.d/media.yaml` and run on the mini via the
    existing verification runner. This doc formalizes the pattern that emerged
    from the Pinchflat→Plex, Libreseerr→CWA, and MusicSeerr incidents into a
    reusable framework + a journey catalog so we can see, at a glance, which
    user journeys are guarded and which are still only liveness-checked.

## Why this exists — the quality gap

The tracker reported **"green / 100%"** while real features were broken in live
use:

- **Pinchflat → Plex** — 1363 videos archived to disk, container healthy, Plex
  showing **0 items** (missing `user:PlexMediaServer` ACL on the share).
- **Libreseerr → CWA** — books grabbed + imported in Readarr, healthy the whole
  time, but **never reached the reading library** (a copy script stripped
  apostrophes from paths with `xargs`).
- **MusicSeerr requests** — albums stuck **"Downloading 0%" for 2 days**; page
  and API both healthy, but Lidarr left them `monitored:False` so nothing ever
  grabbed.

Every one was invisible to liveness/health monitoring, because the boxes were
all **up**. The failure was in the *seam between* boxes, or in the *outcome the
user sees*. That is the class acceptance testing exists to catch.

> **The principle:** probe the *user-journey outcome*, not the boxes around it.
> "Did a requested album / book / video / document actually become
> watchable / readable / searchable?" — not "is the container up?"

## Two check shapes

Every acceptance check is one of two shapes. Pick the one that fits the journey.

### 1. Outcome / coverage

Compare **producer output** (things that exist upstream — files on disk,
requests made) to **consumer visibility** (things the user can actually reach —
items served in Plex / CWA / Navidrome). A shortfall means content exists but is
invisible.

- Best when producer and consumer counts are **directly comparable** — a *flat*
  1:1 library where one media file == one served item (personal-media / YouTube
  archives). Reusable primitive: `verification/bin/plex-flat-library-coverage.py`.
- **Do NOT** use a raw count ratio where item count ≠ file count — a Plex TV
  show is one item but many episode files, a movie is one item but may be split.
  For those, use a handoff-integrity check instead.

Example: `pinchflat-plex-visible` — `disk_media_files` vs `plex_library_size`
for the flat YouTube library, must be ≥ 80%.

### 2. Handoff integrity

Probe the **fragile seam between two services** directly — the specific way a
known handoff breaks — instead of counting the whole population. Best when the
two sides aren't count-comparable, or when one specific transfer step is the
proven point of failure.

Examples:

- `readarr-cwa-copy-drops` — the copy script logged zero path-resolution drops
  (the apostrophe bug's exact signature).
- `cwa-ingest-not-stuck` — nothing sitting unconsumed in the ingest folder > 20m.
- `musicseerr-phantom-requests` — no request is `downloading` in MusicSeerr
  while its Lidarr album is unmonitored + fileless (the phantom signature).

## Conventions (non-negotiable)

**Read real state, not app dashboards.** Checks read the filesystem, the app's
own sqlite DB (via the container's `python3` — `sqlite3` CLI is absent in some
app containers), or a downstream API — never a status page that reports its own
health. A dashboard saying "healthy" is exactly what failed us.

**Fail loudly on a down mount — never a vacuous pass.** `0 files on disk + 0 in
Plex` must **FAIL**, not silently pass. Coverage primitives check the mount is
listable first and emit `MOUNT_DOWN` rather than a misleading `COVERAGE_OK`. A
check that goes green when its data source disappears is worse than no check.

**Severity.**

- `crit` — user-visible data is **invisible or lost** (archived media not in
  Plex; a requested book that never reached CWA; the shared import mount dead).
  Pages high-priority.
- `warn` — **degraded or transient-tolerant** (ingest folder briefly backed up;
  a request still settling; a duplicate folder). Real, but not a data-loss
  emergency.

**False-positive discipline.** A legitimately-unavailable item must not page.
`musicseerr-phantom-requests` ignores albums that are monitored-but-have-no-
release (genuinely waiting on Soulseek/RSS) and only fires on the *unmonitored*
phantom. Thresholds tolerate transient in-flight work (e.g. `sonarr-queue-stuck`
allows ≤ 5 items in `warning` state — active grabbing is fine, a pile-up is not).

**Negative test before "done" — mandatory.** A check is not finished until you
have *forced the underlying outcome broken and watched the check FAIL*, then
restored it and watched it PASS. A check that has only ever been observed
passing is unproven — it may be structurally incapable of failing (wrong path,
swallowed error, over-broad regex). See [Verification](verification.md) for the
exact single-check run + negative-test recipe.

**Right-sized for a home fleet.** Extend the existing hourly runner and the
`checks.d/*.yaml` schema. Do **not** build a heavyweight CI, a synthetic-user
harness, or a separate scheduler. The whole value is that these ride the
verification infrastructure that already pages via ntfy.

## Journey catalog

Every user-facing pipeline: its producer, its consumer, the fragile seam(s), and
what covers it. ✅ = an acceptance check guards the outcome; ⚠️ = partial (seam
guarded but not the end outcome, or vice-versa); ❌ = liveness-only, outcome
unguarded.

| Journey | Producer → Consumer | Fragile seams | Coverage |
|---|---|---|---|
| **YouTube** | Pinchflat / MeTube → Plex (§4) | share ACL for `PlexMediaServer`; scan/visibility | ✅ `pinchflat-plex-visible` (coverage) + `plex-youtube-readable` (ACL invariant) |
| **Book** | Libreseerr → Readarr → CWA | Readarr→ingest copy (path drops); CWA ingest consumption | ✅ `readarr-cwa-copy-drops` + `cwa-ingest-not-stuck` |
| **Album** | MusicSeerr → Lidarr → Navidrome | request→Lidarr monitor state (phantom); import→library | ⚠️ `musicseerr-phantom-requests` (request seam) + `music-library-dupes`; **gap:** no Lidarr-imported→visible-in-Navidrome outcome check |
| **Movie / TV** | Seerr → Radarr/Sonarr → Plex (§1/§2) | grab→import queue clog; **import→visible/playable in Plex** | ✅ `radarr-movies-in-plex` + `sonarr-tv-in-plex` (2026-07-14, #6: external-id `tmdb`/`tvdb` coverage of arr-items-with-files vs Plex — immune to item≠file count; crit @ 0.85 = gross-seam guard) + `sonarr-queue-stuck` / `radarr-queue-stuck` / `*-pipeline-health` / `seedbox-mount-listable` (upstream seams). **Known data-quality gap (not a seam break):** ~12/197 movies unwatchable — 7 sample-file imports, 2 `.iso` disc images, 1 wrong-file map, 2 Plex-mismatch — tracked for remediation, kept above the 0.85 line so it doesn't page. |
| **Photos** | phone / upload → Immich | upload→library indexing; thumbnail/ML backlog | ❌ liveness-only (`nas-immich`); no outcome check |
| **Documents** | scan / upload → Paperless | consume folder → OCR → searchable index | ❌ liveness-only (`mini-paperless`); no ingest-consumed / OCR-complete check |
| **Smart-home** | HA automations → lights / HomePod HomeKit | HA→hub bridge; automation actually fires the device | ⚠️ `ha-hue-lights` (state readable); **gap:** HomePod↔HA HomeKit hub (queue #06) + automation-fired-outcome |

**Reusable primitives** (`verification/bin/`): `plex-flat-library-coverage.py`
(flat coverage), `arr-plex-journey.py` (Radarr/Sonarr→Plex external-id coverage,
tmdb/tvdb), `musicseerr-phantom-requests.py` (phantom-request signature),
`music-dupes.py` (library collisions). New journeys should add a primitive when
the logic is non-trivial and reuse these when the shape matches.

## Anti-pattern watch: producer flood → consumer storm

The seams aren't only *drops* — a successful producer fix can **overload** the
consumer. On 2026-07-13 the Pinchflat ACL fix made 1363 YouTube items visible to
Plex all at once; Plex's `none`-agent metadata analysis on section 4 saturated
its worker thread pool and it returned **HTTP 503 to every client** — a
user-facing outage caused by *too much* successful hand-off, not a drop. A
liveness check ("container up") stayed green; the acceptance check
(`pinchflat-plex-visible`) correctly went `PLEX_UNREACHABLE`. Lesson for the
catalog: a coverage/outcome check that talks to the consumer's API *also*
catches consumer saturation, because a saturated consumer can't answer. A
candidate future check is **"Plex front-end responsive (not 503 / overloaded)"**
— a reliability guard that would name this failure directly rather than as a
side effect. (Tracked; deferred until Plex is serving so it can be
negative-tested against the PASS side.)

## Adding an acceptance check

1. **Diagnose the real journey.** Walk it end to end. Where does the user-visible
   outcome actually live (which DB row, which file path, which API count)? What
   is the *specific* seam that broke or could break?
2. **Choose the shape** — coverage (comparable counts) or handoff-integrity
   (a fragile seam).
3. **Write the check** reading real state, printing exactly one deterministic
   token line, exiting nonzero on failure and on data-source-down. Follow the
   schema in [Verification](verification.md).
4. **Run it live** — it must PASS against the healthy system.
5. **Negative-test it** — force the outcome broken, confirm it FAILS, restore,
   confirm it PASSES. Not done until this holds.
6. **Deploy** to the mini (`/opt/verification/`), **commit** to `origin`, and
   `./foss-setup/scripts/docs/publish-deploy.sh` to forgejo.
7. **Record** — update `docs/quality-hardening-state.md` and memory.

## The "done" bar (task #10)

A tracker item that touches a user-facing pipeline is **not "done" on liveness**.
"Done" requires an end-to-end acceptance pass — the actual outcome observed, or a
negative-tested acceptance check guarding it. Treat every existing green/"done"
on the *seerr / *arr / media / photos / documents pipelines as *liveness only*
until re-verified against this bar.

**Audit run 2026-07-14 (once Plex recovered):** the full media journey suite is
**13/13 green after remediation**. Two real user-facing defects surfaced that
liveness never showed:
- **Movie pipeline data quality** — 12/197 movies were `hasFile=True` in Radarr
  but not watchable in Plex: **7 sample-file imports** (Radarr grabbed the 6–24 MB
  `sample.*` instead of the movie), **2 `.iso` disc images** (Plex won't play raw
  ISOs), **1 wrong-file map** (All About My Mother ← a Mamma Mia file), 2 Plex
  agent-mismatch. Seam is healthy (0.94 ≥ 0.85); this is a **remediation backlog**,
  not a monitoring gap — see `quality-hardening-state.md`.
- **MusicSeerr phantom recurred** — a "3OH!3" album sat request-`downloading`
  while unmonitored+fileless in Lidarr (same class as #3); `musicseerr-phantom-requests`
  caught it live. **Fixed** (Lidarr monitor + AlbumSearch on album 6037).
Everything else (Pinchflat→Plex now 1364/1364, Book→CWA, mounts, pipeline health)
verified green.

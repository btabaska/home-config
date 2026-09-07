# Shelfmark (NAS) — book search / download / ingest frontend

Deployed 2026-07-21 at `nas:/volume1/docker/shelfmark/`, exposed via Caddy at
`shelfmark.tabaska.us`. Replaces the libreseerr + Bookshelf + rreading-glasses chain
with a single search→download→ingest hub, using **direct Hardcover/OpenLibrary metadata**
(no Goodreads-shaped proxy → sidesteps the rreading-glasses wrong-edition bug).

## Flow
Search (Hardcover/OpenLibrary) → pick a release from **Prowlarr (MAM etc.)** or Anna's
Archive DDL → torrent handed to the **seedbox Deluge** (`category=shelfmark`, keep-seeding
for MAM ratio) → on completion Shelfmark **copies** the file into the CWA ingest folder
(`/books`, seed-preserving) → CWA converts + syncs to Kobo. Nothing in this path touches
rreading-glasses/Bookshelf/libreseerr.

## Non-obvious setup
- **Metadata provider (Hardcover, restored 2026-09-07):** `METADATA_PROVIDER=hardcover`
  in `shelfmark.env`. History: 2026-09-06 the deployed JWT's **Hardcover account went
  inactive upstream** → every search 401'd ("No results found" even for "The cat in the
  hat"), so we ran OpenLibrary (keyless) as a stopgap. A fresh `hc_pat_`
  personal-access-token (account `RobitFarmer`, active) then landed in the vault
  (`books.hardcover_api_token`) → back on Hardcover for richer edition metadata.
  Free-plan limits: 60 req/min, burst 10, 5,000/day. `OPENLIBRARY_ENABLED=true` stays
  on: to fall back, set `METADATA_PROVIDER=openlibrary` and recreate.
- **Metadata cache off (2026-09-06):** `METADATA_CACHE_ENABLED=false`.
  Shelfmark's `@cacheable` decorator stores any non-`None` result, and a
  transient OpenLibrary egress timeout (slow cold start / 429) returns `[]` —
  so the *empty* result was cached for 300s, turning a rare timeout into a
  5-minute "No results found" for that query. With caching off, every search
  hits OpenLibrary live and a bad result self-clears on the next request.
  (Trade-off: slightly more OpenLibrary egress — acceptable at this query rate.)
- **Secrets** in `shelfmark.env` (chmod 600, gitignored; see `shelfmark.env.example`).
- **Settings persisted in `/config`** (not env), set once via the settings API:
  `USE_DOH=false`, `AA_MIRROR_URLS=[annas-archive.gs, .li]`,
  `USING_EXTERNAL_BYPASSER=true` + `EXT_BYPASSER_URL=http://192.168.10.4:8191` (flaresolverr).
- **Seedbox mount propagation (critical):** the container bind-mounts the seedbox rclone
  mount `:rslave` at the *same path Deluge reports* (`/home/hd34/btabaska/files`) so it can
  read completed torrents. The rclone mount comes up **private** at boot, so it must be made
  `rshared`. `boot-rshared.sh` does this (wait-for-mount → `mount --make-rshared` → restart
  shelfmark) and is run at boot by **DSM Task Scheduler boot-up task `15.task`**
  (`/usr/syno/etc/synoschedule.d/root/15.task`, cloned from the fix-21 `13.task` template).
  This is purely additive — it never disturbs the *arr containers that bind `/seedbox` private.
  Guarded live by verification check `shelfmark-mam-path-ready`.

## Recreate the DSM boot task (if lost)
Copy an existing `type=bootup` `.task` (e.g. `13.task`), set a free `id=`, point `cmd=`
(base64) and `app args` script at `/bin/sh /volume1/docker/shelfmark/boot-rshared.sh`.

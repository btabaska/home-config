# 2. Open-source replacements, by Apple/iOS task

For each: the pick, the runners-up, and what's new. **Bold = recommended.**

## Photos (iCloud Photos / Apple Photos)

- **Immich** — a mature, stable project. Self-hosted, iOS/Android apps with automatic background backup, face/object recognition, "Free Up Space," non-destructive editing, and (3.0 line, still preview) automation workflows and real-time transcoding. Standout iCloud Photos replacement, ready for primary use (still: keep backups — see Backup). **Live version: v2.7.5** on the NAS (the 3.0 RC discussed in the plan is general context, not the deployed build).
- *Runner-up:* **PhotoPrism** (more "archive/browse"); **Synology Photos** (turnkey, ecosystem lock-in).
- *Host on:* the NAS. Point its library at existing storage; use the VectorChord Postgres image it ships with.
- *Mirrorless camera — works well.* Immich stores/displays RAW (ARW/CR3/NEF/RAF/DNG) and reads EXIF. **No auto-backup for a camera** (the mobile app only backs up the phone's roll), so import from the SD card via the **immich-go** CLI (`upload from-folder`, `--manage-raw-jpeg` to stack RAW+JPEG) or **pbak** (SD → SSD → Immich with EXIF sorting + SHA-256 dedup). For plug-and-forget, copy the card into a watched NAS staging folder and run immich-go on a schedule.

## Music — library + streaming (Apple Music / iTunes library)

- **Navidrome** — self-hosted music server (Subsonic API). Mobile clients: **Symfonium** (Android), **play:Sub** / **Amperfy** (iOS); desktop: **Feishin** or **Supersonic**. **Live on the mini.**
- *Getting music in:* CD rips drop straight in; automated acquisition (the "music half") uses **Lidarr** and feeds this same library — see *Media acquisition* below.

## iPod Classic

**Decision: keep Apple firmware + libgpod tools.** Sync from Linux with **Rhythmbox** (simplest, built-in iPod support); **gtkpod** or **Clementine** as alternatives. Keeps the device stock (car/USB compatibility intact).

- Plug the iPod into the CachyOS rig and **Rhythmbox auto-detects it like iTunes did** — click sync or drag tracks. **Podcasts ride along on the same iPod:** point gPodder to download episodes into a folder that's part of Rhythmbox's library, so a single plug-in-and-sync pushes new music *and* new podcasts.
- *Gotcha:* libgpod writes Apple's iPod DB; occasionally a sync needs a re-init. Keep the music master library on the NAS (Navidrome's library) so the iPod is a reproducible copy.
- *If you ever drop the DB hassle:* **Rockbox** turns the iPod into a plain drag-and-drop USB drive (FLAC/Opus, custom EQ) via a modern bootloader — but loses Apple's car/USB integration.

## Podcasts (Apple Podcasts)

- **gPodder** — maintained desktop podcatcher (RSS / YouTube / SoundCloud), batch-download, auto-cleanup. On the Apple-firmware + Rhythmbox path: point gPodder at a folder inside Rhythmbox's library so a single sync writes episodes alongside music.
- *Optional sync server:* **oPodSync**, **goPodder**, or **Sintoniza** if you also listen on a phone. Skip if the iPod is the only device.

## YouTube & web video — download / archive

- **Pinchflat (recommended)** — "Sonarr for YouTube": **one self-contained Docker container** where you add channels/playlists as *sources*; it pulls new uploads, names to a template, writes NFO/poster metadata for Plex/Jellyfin/Kodi. Supports **SponsorBlock** and can expose a channel as a **podcast RSS feed**. Built on **yt-dlp**, low resource. **Live on the mini**, output to a Plex "YouTube" library (section 4).
- *Heavier archive with search:* **Tube Archivist** (app + Redis + Elasticsearch) — only if in-app browse/search matters more than a lean stack.
- *Ad-hoc grabs:* **MeTube** (tiny web UI over yt-dlp), or run **yt-dlp** straight from the CachyOS terminal.

## News / RSS (Apple News, algorithmic feeds)

- **Miniflux (recommended)** — minimalist single Go binary, PostgreSQL backend (required — no SQLite/MySQL), distraction-free, strips tracking pixels, full-text fetch, speaks Fever + Google Reader APIs (NetNewsWire, Reeder, NewsFlash, Readrops sync to it). **Live on the mini** (`miniflux` + `miniflux_db`).
- **FreshRSS** — PHP, more features + extensions, single container with SQLite. Pick for extensions/customization.
- *Tie-ins:* pair with **Wallabag** (self-hosted read-it-later, replaces Pocket — **live on the mini**); both feed **KOReader's** news/RSS and Wallabag plugins on the eReader.

## Reading / eReader (Kindle + iBooks)

- **Calibre** (desktop) — library master + conversion engine.
- **Calibre-Web-Automated (CWA)** — the actively-developed fork. Auto-ingest folder, EPUB-fixer, metadata/cover enforcement, OPDS server, native Kobo sync, built-in KOReader progress sync. **Image decision (June 2026):** deploy the community fork **`ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7`** — upstream `crocodilestick/calibre-web-automated` stops at v4.0.6 and never published v4.0.7; the NextGen fork is a drop-in with **CVE-2026-7713** (Kobo auth-token IDOR) fixed. **Live on the NAS at exactly this image.** Keep CWA LAN/VPN-only; do not expose `:8083` publicly.
- **KOReader** — open reader (Kobo, jailbroken Kindle, PocketBook, Boox, reMarkable, Android). OPDS + Calibre wireless plugin.
- **Syncthing** — peer-to-peer sync of books and progress files. No cloud.

Device notes: **Kobo** = smoothest (native CWA sync + optional KOReader). **Kindle** = jailbreak + KOReader (Amazon removed USB transfer Feb 2025 and ended Kindle Store access for pre-2012 devices May 20 2026). **Buying new?** Kobo / PocketBook / Boox are friendliest.

## Notes (Apple Notes — already on Obsidian)

**Decision: paid Obsidian Sync.** Official, E2E-encrypted, zero setup. Notes remain plain local Markdown — you own the data and it's captured by Backup. (Free alternatives — LiveSync + CouchDB, or plain Syncthing — exist but there's no reason to complicate this.)

## Office (Pages/Numbers/Keynote, MS Office)

- **LibreOffice (26.2)** — mature desktop-first FOSS suite (26.2 is current mid-2026, after 25.8 EOL'd June 2026). The obvious baseline for solo/offline work on CachyOS.
- *Better MS fidelity:* **OnlyOffice Desktop** (OOXML-native; the old 20-connection community limit on the server edition was removed in Docs 9.4, May 2026).
- *Browser-based collaboration:* **Collabora Online** with Nextcloud.

**Recommendation:** LibreOffice desktop. Don't self-host an office server unless you want in-browser collaboration.

## Video / media server (Plex — staying)

**Decision: keep Plex** (grandfathered lifetime pass). The library stays on the NAS and Plex serves it; the existing Lifetime Pass is unaffected by the price change (new-purchase lifetime tripled to **$749.99 on July 1, 2026**, up from $249.99). The 2025 remote-streaming paywall applies to **video** only; remote music/photo streaming stays free. (Jellyfin remains the FOSS fallback — standable-up alongside Plex in ~30 min at the same folders — but no action needed now.)

## Media acquisition — private, off-site

**Decision: a managed seedbox runs the P2P off-site; finished media syncs to the NAS for Plex.** This retires the home VPN routing entirely.

> ### ⭐ ARCHITECTURE UPDATE (2026) — the authoritative model
> The earlier plan put the whole *arr suite + qBittorrent **on the seedbox**. The current split is different and **settled** (configs: `configs/nas/media-automation/` + `scripts/media/rclone-seedbox-*.sh`). **This model is confirmed live 2026-07-14.**
>
> **Seedbox = Deluge + slskd.** The seedbox **"Betty"** (Bytesized AppBox, no root, shared IP `185.162.184.38`, home `/home/hd34/btabaska`) runs **Deluge** (torrents) and **slskd** (Soulseek, **native binary** — not rootless Docker). No *arr apps, Soularr, beets, qBittorrent, or sync agents on Betty. Deluge sorts completed torrents into label folders under `files/`: `tv`, `movies`, `music`, `books`, `manual`. slskd writes to `files/slskd/`.
>
> **Home stack + mount.** The **full *arr stack runs on the NAS (DS920+)** in Container Manager — `sonarr`, `radarr`, `prowlarr`, `lidarr`, `readarr`, `rreading-glasses` (+ its Postgres), `soularr`, `unpackerr`, `flaresolverr` — co-located with the library split across three Basic volumes: **TV** on `/volume3/tv`, **Movies** on `/volume2/movies`, **Music + Books + Tier 1 + Docker** on `/volume1/`. *(All of these containers verified running on the NAS 2026-07-14.)* Optional **beets** (tag-only) runs on the NAS against `/volume1/music` after Lidarr import — **note: `beets` is running live on the NAS**, though `nas-30` was marked "retired" in the tracker (redundant with Lidarr's layout ownership); live state wins, beets is present. The home apps reach Deluge over its **API** and read completed downloads through a persistent **rclone SFTP mount** of the seedbox `files/` folder: `seedbox:/home/hd34/btabaska/files → /volume1/mounts/seedbox-files`, bound into every download-touching container at **`/seedbox` with `:rslave`**. Each *arr's **Remote Path Mapping** `/home/hd34/btabaska/files/ → /seedbox/` resolves the path Deluge reports to the mount. A **watchdog** remounts if the mount goes empty/stale — *a dropped mount silently stalls every import*. Import is a cross-filesystem **copy** (not a hardlink), and **"Remove Completed" stays OFF** in every *arr so the seedbox keeps seeding. There is **exactly one scheduled rclone job** — the **manual lane** (`files/manual → /volume1/manual`, `copy`, re-run-safe). *arr media arrives only via the live mount + import.
>
> - **Music = MusicSeerr (Mac mini) → Lidarr + Soulseek (split) + optional beets.** **MusicSeerr** forwards album requests to Lidarr on the NAS (Seerr has no Lidarr support). Torrent music via Deluge (label `lidarr` → `/seedbox/music/`). Soulseek via **slskd on Betty** + **Soularr on NAS** (imports from `/seedbox/slskd/`). Finished files reach the NAS via the same rclone mount. **beets** is tag-only on `/music` — Lidarr owns layout.
> - **Books = Readarr + self-hosted rreading-glasses → CWA.** Readarr's metadata provider points at the **local** rreading-glasses (not a public instance); Readarr imports into the **CWA ingest** folder and CWA owns the final Calibre library. Book automation is **inherently less reliable than video** (no organized scene, messy metadata, Readarr is retired upstream) — **expect occasional manual metadata fixes**.

### RAM-phased rollout checklist (NAS now at 20 GB — the "4 GB first" gating is satisfied)

- `id <user>` on the NAS → set identical `PUID`/`PGID` (+ `TZ`, DB password).
- Install rclone on DSM; create `rclone.conf`; run the mount; confirm `/volume1/mounts/seedbox-files` lists the seedbox tree (*nothing imports without this*).
- Task Scheduler: boot-up task = mount; every-5-min task = watchdog.
- **Phase A (core):** `prowlarr flaresolverr sonarr radarr` — indexers, Deluge client, remote path mapping, roots `/tv`, `/movies`.
- **Phase B (extend):** `lidarr` + `readarr rreading-glasses rreading-glasses-db` — music + books.
- **Phase C (polish):** `unpackerr` — fill API keys.
- **Phase D (Soulseek):** `slskd` on Betty (`seed-09`) → `soularr` on NAS (`nas-29`).
- **Phase E (optional):** `beets` tag layer on NAS (`nas-30`).
- **MusicSeerr:** deploy on Mac mini (`docker-16`) → wire to Lidarr (`seed-06`) → E2E (`seed-10`).
- Task Scheduler: every-15-min task = the single manual-lane `rclone copy`.
- Run the self-check in the stack README.

### Physical-device last hop (iPod + Kobo)

The library on `/volume3/tv`, `/volume2/movies`, and `/volume1/music` is **kept current automatically**, but the **final hop to a handheld is physical/triggered**, not push: the **iPod** (Rhythmbox/libgpod) syncs from `/volume1/music` **when you physically plug it in**; the **Kobo** (KOReader OPDS) pulls from the CWA/Calibre library on `/volume1/books` **when it wakes on WiFi**. So "is it up to date?" has two answers — the library, continuously; the device, as of its last plug-in / wake. Don't change the `/volume1/music` naming without checking **both** Plex and the iPod sync.

> *Superseded design:* the original seedbox-hosted pipeline (qBittorrent + the full *arr suite + a sync agent all on the seedbox) is in Appendix A.

## Media companion layer (polish around Plex + the *arrs)

Most run as one small container each.

- **Tautulli (recommended)** — Plex analytics: play history, who's watching/transcoding, per-user stats, notifications, transcode-abuse spotting. *Host: Mac mini* — **live**.
- **Recyclarr** — syncs **TRaSH Guides** custom formats/quality profiles/scoring into Sonarr/Radarr on a cron. *Host: with the *arrs* (now the NAS).
- **Unpackerr** — auto-extracts RAR'd releases *arr otherwise silently fails to import. **Live on the NAS.**
- **Kometa** (formerly Plex Meta Manager) — collections, overlay badges, posters, playlists. *Host: Mac mini* — **live**.
- ~~**Tdarr** / **FileFlows**~~ — **REMOVED from the plan (2026-07-08, `media-04`, won't do):** re-encoding conflicts with the TRaSH quality automation, and storage isn't scarce.
- ~~**Maintainerr**~~ — **REMOVED from the plan (2026-07-08, `media-03`, won't do):** no auto-deletion wanted.
- *Niche / by taste:* **Komga** or **Kavita** (comics/manga); **beets** + **MusicBrainz Picard** for clean music tags.
- *Book automation:* **Readarr was archived June 2025** — no maintained "monitor an author, auto-grab" *arr. CWA still organizes/serves ebooks; for acquisition automation, **Bindery** or **LazyLibrarian** are the community picks.

## Files, Contacts, Calendar (iCloud Drive / Contacts / Calendar)

- **One hub — Nextcloud.** Files (WebDAV) + Contacts (CardDAV) + Calendar (CalDAV). Closest single-app iCloud replacement; heavier.
- **Discrete tools (lighter).** **Syncthing** for files + **Baikal** or **Radicale** for CalDAV/CardDAV.
- **Lean on Proton (least effort).** **Proton Drive / Calendar / Pass** — already paid for, zero hosting.

**Recommendation:** Proton for calendar/contacts/drive + Syncthing for truly-local folders. Nextcloud only if you want the unified hub.

## Documents — the paperless filing cabinet

- **Paperless-ngx** — OCRs every page, auto-tags/classifies, full-text search. The document half of leaving Apple that nothing else here covers. Feed from a watched "consume" folder. Five containers: webserver + Postgres + Redis + **Gotenberg** + **Tika**. *Host on the NAS* — its data is **Tier 1**. **Status: planned, not yet deployed** (no Paperless containers on the NAS as of 2026-07-14).

## Passwords (Bitwarden — keep what you have)

**Decision: stay on Bitwarden.** Open-source, audited (Cure53), zero-knowledge, great iOS/browser autofill, TOTP, self-hostable later. It holds the **backup encryption keys, the HA backup key, and the SOPS/age key** (with a printed off-machine copy).

- *Optional self-host:* **Vaultwarden** (~256 MB RAM) if owning the vault outright is the goal. Back it up as Tier 1.

## Recipes

- **Mealie** — self-hosted recipe manager: URL import, meal-plan, shopping lists, clean PWA. Lighter than **Tandoor**. *Host on the Mac mini* — **live**.

## Browser & the rest

- **Browser (Safari → ):** on CachyOS, **Firefox**, **LibreWolf** (hardened), or **Zen**. Set **Kagi** as default search.
- Keep **Kagi** and **ProtonMail / VPN / Drive / Calendar / Pass**. Proton VPN = private egress; Tailscale (set-and-forget) = reaching your own services — you want both.

---
[← index](index.md)

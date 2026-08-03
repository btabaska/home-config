# Roadmap — reading

32 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `fix-38` | Reading/CWA: reconcile Kobo store-passthrough state + note fork-image supply-chain risk | ✅ done | 1-3 hrs |
| `fix-46` | Books: eliminate the French/wrong-edition class (rreading-glasses foreign records, no language guard, Libreseerr anyEditionOk) | ✅ done | 1-3 hrs |
| `fix-47` | Books: import completion + file-to-record correctness (cross-wired pack import, 2 lost books, 36 stranded files, silent match dead-ends) | ✅ done | 1-3 hrs |
| `fix-48` | Libreseerr request-path robustness (OL-id 400s, 15s timeouts, reconciler dead-ends, unicode authors, no retry) | ✅ done | 1-3 hrs |
| `fix-57` | Books request layer broken-quiet: last successful request 07-20, 12/30 libreseerr requests errored, one grabbed book lost pre-import for 13 days | ✅ done | 1-3 hrs |
| `fix-58` | Manga chain silently severed at BOTH ends: Komga scheduler scans a deleted library-id (279 new chapters invisible 6 days) and Suwayomi's bind raced the CIFS mount into an empty view | ✅ done | 1-3 hrs |
| `nas-09` | Deploy Calibre-Web-Automated on Container Manager (pinned, hardened) | ✅ done | 30 min |
| `read-01` | Install Calibre desktop (library master + conversion) on CachyOS | ✅ done | 20 min |
| `read-02` | Set up Syncthing as a systemd user service on CachyOS | ✅ done | 20 min |
| `read-03` | Wire the Calibre library into CWA auto-ingest on the NAS | ✅ done | 20 min |
| `read-04` | Install KOReader on the Kobo | ✅ done | 30 min |
| `read-05` | Connect KOReader to Calibre/CWA over WiFi (OPDS + wireless send) | ⬜ open | 20 min |
| `read-06` | Enable CWA built-in KOReader progress sync (KOSync) on the Kobo | ⬜ open | 20 min |
| `read-08` | Wire the KOReader Wallabag plugin on the Kobo | ⬜ open | 20 min |
| `read-09` | Add RSS/news to KOReader (Miniflux tie-in) | ⬜ open | 20 min |
| `read-10` | Install the iPod sync toolchain on CachyOS (Rhythmbox + libgpod) | ✅ done | 15 min |
| `read-11` | Sync the iPod Classic from CachyOS via Rhythmbox/libgpod | ✅ done | 45 min |
| `read-12` | Install + configure gPodder for podcasts on CachyOS (funnel into Rhythmbox) | 🗑️ retired | 20 min |
| `read-13` | Enable official Obsidian Sync (E2E encrypted) on CachyOS | ✅ done | 20 min |
| `read-14` | Deploy Pinchflat — archive YouTube channels into Plex (and as podcast RSS) | ✅ done | 30 min |
| `read-15` | CWA: KOReader sync checksum table missing (book_format_checksums) | ✅ done | 15-30 min |
| `read-16` | Deploy Audiobookshelf (audiobooks + podcasts) on the NAS + Homepage widget | ✅ done | 1.5 hr |
| `read-17` | Deploy Komga (comics + manga reader) on the NAS + Homepage widget | ✅ done | 1.5 hr |
| `read-18` | Deploy Suwayomi (manga server) on the rig, feeding Komga | ✅ done | 1.5 hr |
| `read-19` | Sync Audiobookshelf audiobooks + podcasts to the iPod Classic (alongside music) | ✅ done | 3 hr |
| `read-20` | Provision the ComicVine API key for Mylar3 into the vault | ✅ done | 15 min |
| `read-21` | Deploy the Mylar3 container on the NAS (base install + first-run config) | ✅ done | 45 min |
| `read-22` | Enable Mylar3 GetComics (DDL) acquisition + prove one comic end-to-end into Komga | ✅ done | 1 hr |
| `read-23` | Wire Mylar3's fallback acquisition: Prowlarr app-sync + seedbox Deluge (best-effort) | ✅ done | 1 hr |
| `read-24` | Add a consumer-end monitoring check + coverage for Mylar3 | ✅ done | 30 min |
| `read-25` | Document Mylar3: service catalog + wiki page + Homepage tile | ✅ done | 45 min |
| `read-26` | Deploy BookLogr (personal reading tracker / library) on the mini + Homepage tile | ✅ done | 1 hr |

[← Roadmap overview](index.md)

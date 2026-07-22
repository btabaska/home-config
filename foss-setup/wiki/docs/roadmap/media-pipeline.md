# Roadmap — media-pipeline

37 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `betty-01` | Seedbox = Deluge only: install Deluge + create label folders | ✅ done | 20 min |
| `docker-03` | Deploy Seerr media request portal (home, Mac mini) | ✅ done | 20 min |
| `docker-16` | Deploy MusicSeerr on Mac mini (album request portal) | ✅ done | 20-30 min |
| `fix-25` | Fix the silent "grabbed → never imported" class (download-client import + reaper label coverage) | ✅ done | 1-3 hrs |
| `fix-26` | Reconcile stuck request-layer states (seerr/libreseerr/musicseerr dangling & unmonitored) | ✅ done | 1-3 hrs |
| `fix-27` | Remediate "green but not watchable": sample-file imports + unextracted RARs | ✅ done | 1-3 hrs |
| `media-05` | Deploy Jellyfin as a fully-local media server (plex.tv-independent parallel to Plex) | ⬜ open | 1-2 hrs |
| `media-06` | Resolve the rig ~/Music mirror conflict (05:00 ALAC transcode vs 05:30 rsync --delete-after) | ✅ done | 30 min |
| `media-07` | MusicSeerr can still create unmonitored-artist requests (upstream monitor_artist=0 default) — tripwire-covered, close the generator | ⬜ open | 30-45 min |
| `media-08` | CWA duplicate ingest on Readarr re-import — connect script has no dedupe, add a books-dup tripwire | ✅ done | 30-60 min |
| `media-09` | fix-27 residual: re-grab 5 un-extractable titles + reclaim ~200GB of redundant library RARs | ⬜ open | 1-2 hrs |
| `media-10` | Seedbox: retire drained readarr label pair from deluge-reaper | ⬜ open | 10 min |
| `media-11` | Lidarr: 'Camera' album monitored under unmonitored artist (orphan flag) | ⬜ open | 10-20 min |
| `media-12` | Deploy Bazarr (subtitles) on the NAS + Homepage widget | ⬜ open | 1.5 hr |
| `nas-10` | Deploy Plex Media Server on the NAS (libraries + Quick Sync) | ✅ done | 45-60 min |
| `nas-20` | rclone SFTP mount of the seedbox files (persistent + self-healing) | ✅ done | 45 min |
| `nas-21` | Deploy the NAS media-automation *arr stack (phased, pinned) | ✅ done | 1-2 hrs |
| `nas-22` | Wire remote Deluge + Remote Path Mappings + root folders (all *arrs) | ✅ done | 45 min |
| `nas-23` | Music pipeline — Lidarr only (no beets/slskd/Soularr) | ✅ done | 30 min |
| `nas-24` | Books pipeline — Readarr + self-hosted rreading-glasses -> CWA | ✅ done | 45 min |
| `nas-25` | Unpackerr — extract archived releases for the *arrs | ✅ done | 20 min |
| `nas-26` | Manual lane — the ONE scheduled rclone copy job | ✅ done | 15 min |
| `nas-27` | Media-automation self-check (report violations, don't silently fix) | ✅ done | 15 min |
| `nas-28` | Apply TRaSH quality profiles + naming via Recyclarr (Ubuntu → NAS *arrs) | ✅ done | 30-45 min |
| `nas-29` | Deploy Soularr on NAS (Lidarr ↔ remote slskd bridge) | ✅ done | 30-45 min |
| `nas-30` | beets YouTube-audio tagging layer on NAS (tags non-Lidarr music) | ✅ done | 20-30 min |
| `seed-01` | Provision seedbox "Betty" — Bytesized Stream +3 (Deluge + slskd later) | ✅ done | 1 hr + provisioning |
| `seed-03` | Put the seedbox on Tailscale (userspace networking) | ✅ done | 20-30 min |
| `seed-05` | Connect Seerr to NAS Sonarr/Radarr (movies/TV — not music) | ✅ done | 20-30 min |
| `seed-06` | Connect MusicSeerr to NAS Lidarr + Plex/Navidrome | ✅ done | 20-30 min |
| `seed-07` | End-to-end pipeline verification (Seerr → Deluge → NAS import → Plex) | ✅ done | 30 min |
| `seed-08` | Decommission the old home torrent stack (qBittorrent/Gluetun + dual-LAN + 5Mbps cap) | ✅ done | 45-60 min |
| `seed-09` | Deploy slskd on Betty (Soulseek P2P off-site) | ✅ done | 45-60 min |
| `seed-10` | End-to-end music verification (MusicSeerr → Betty → NAS → Plex/Navidrome) | ✅ done | 30-45 min |
| `seed-11` | Indexer redundancy layer in Prowlarr (TV/anime over IPT+MAM) | ✅ done | ~30-45 min |
| `seed-12` | Deploy Bitmagnet self-hosted DHT crawler on NAS (rate-limit-proof indexer hedge) | 🗑️ retired | ~1 hr + runbook |
| `seed-13` | Whisparr adult-acquisition pipeline (sukebei/XXXClub -> Stash) on NAS | ✅ done | ~an afternoon + runbook |

[← Roadmap overview](index.md)

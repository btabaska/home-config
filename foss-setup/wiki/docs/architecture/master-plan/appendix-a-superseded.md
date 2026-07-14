# Appendix A — superseded designs (kept for history)

> Moved here 2026-07-07 from Section 2 (*Media acquisition* — see `replacements.md`). The sections below describe the **original seedbox-hosted pipeline** (qBittorrent + the full *arr suite + a sync agent on the seedbox) and are kept for history only. Where they conflict with the ⭐ ARCHITECTURE UPDATE box in Section 2, **that box wins** — the live model is **Deluge + slskd on Betty, full *arr on the NAS** (validated 2026-07-14).

Why this answers "never visible to my ISP" *and* the network crashes: the old setup torrented on the NAS behind a home VPN, and thousands of simultaneous peer connections (DHT/uTP) exhausted the connection-state (conntrack) table until you rebooted — the classic torrent-kills-the-network failure. (VPN encapsulation adds MTU/fragmentation headaches on top — though a full tunnel can *reduce* the router's tracked-connection count by collapsing peers into one flow.) The 5 Mbps cap was a band-aid. A seedbox eliminates the root cause: **the P2P happens on a rented server, so your home network only ever does one tidy encrypted download from a datacenter.** Your ISP never sees a swarm — just a normal transfer.

## The pipeline (original: request → auto-appears in Plex)

1. **Seerr** (movie/TV requests) and **MusicSeerr** (album requests) — both run at home on the Mac mini; household members request from phone or Apple TV. (Use **Seerr** `ghcr.io/seerr-team/seerr` for Radarr/Sonarr — **no Lidarr support**. Use **MusicSeerr** `ghcr.io/habirabbu/musicseerr` for Lidarr album requests.)
2. **Sonarr / Radarr / Lidarr** *(the original plan put these on the seedbox — the current model runs them on the NAS)* — receive requests, search via **Prowlarr** indexers, hand off torrent grabs. *(Sonarr = TV, Radarr = movies, Lidarr = music.)*
3. **qBittorrent** downloads *(current model: Deluge)*, then Sonarr/Radarr rename/organize; **Bazarr** grabs subtitles.
4. **Sync agent** (Syncthing or rclone, on the seedbox) pushes finished files into the NAS library *(current model: an rclone SFTP mount + import, not a push agent)*.
5. **Plex** (home) imports them; Seerr sees they're available and notifies the requester.

## How the home and seedbox talked

Original: put the seedbox on **Tailscale** so Seerr (home) reaches Sonarr/Radarr (seedbox) and the sync runs privately, over SFTP/Syncthing. *(Current model: the *arrs are at home on the NAS and reach Deluge on Betty over its API + an rclone mount.)*

## Music — the original two twists

**Lidarr** handles albums; **MusicSeerr** (not Seerr) is the request portal for music. Torrent trackers are thin for music, so the standard add is **Soulseek** via **slskd on Betty** + **Soularr on the NAS** — Soularr reads Lidarr's "wanted" list, finds albums on Soulseek, downloads to `files/slskd/`, and triggers Lidarr import. Because Soulseek is P2P, **slskd stays on Betty**. *(This half survived into the live model unchanged.)*

## Provider — decided: Bytesized

**Bytesized "Stream +3"** (*New Appbox* tier) — **3000 GB HDD, a 6-10 TB/month upload cap (verify the exact SKU at checkout), €16/mo (~$18)**, on a 10 Gbit network in Europe with a one-click panel. Won on ease-of-setup and one-click catalog breadth. *(Runners-up: Seedboxes.cc, DediSeedbox for uncapped upload; Whatbox for SSH freedom — see `configs/seedbox/provider-comparison.md`.)*

- **The upload cap:** capped at 6-10 TB/month (verify at checkout), well above normal private-tracker seeding. qBittorrent/Deluge share-ratio + seeding-time limits keep you under it. The cap is **upload only** — downloads are unmetered.
- **The 3000 GB storage:** the seedbox is a *working + seeding buffer*, not the library — finished files sync to the NAS and Plex serves from there. The sync **copies** completed media home (never the seeding source), and torrents age out (ratio/seed-time rules) so the box self-prunes.

## Decommission the old setup

Remove qBittorrent/Gluetun from the NAS, undo the dual-LAN policy routing, drop the 5 Mbps throttle. The second NAS LAN port is freed (use it for link aggregation/failover, or leave it). If you ever torrent at home again, the fix for the crashes is capping qBittorrent's global max connections (~200) and per-torrent peers — but with the seedbox you won't need to.

---
[← index](index.md)

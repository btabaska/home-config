# 0. The host decision that drives everything: everything runs 24/7 (settled 2026-07-08)

This was originally framed as "24/7 vs. on-demand," and it's still the difference between a ~$160/year power bill and a ~$700+/year one — but it's now **settled: every host, including the rig, runs 24/7** (decision 2026-07-08: ~130 W rig idle ≈ $23/mo, accepted as the price of availability; an idle-power-tuning task is open). Wake-on-LAN is retained as **recovery tooling** (power outage, accidental shutdown), not a workflow — an unreachable rig is an incident, not expected sleep.

**Always-on tier (the quiet workhorses):**

- **DS920+ NAS** — storage, plus the home for most lightweight always-on services. Its Celeron J4125 has Intel Quick Sync, so it can even handle Jellyfin transcoding for a stream or two. It shipped with 4 GB; the heavy-offload plan needs ~20 GB. **✅ Done — the RAM upgrade is complete: the NAS reports 20 GB live** (`MemTotal: 20328580 kB`, validated 2026-07-14) via a single Crucial `CT16G4SFD8266` 16 GB dual-rank SO-DIMM (4 GB + 16 GB = 20 GB DSM recognizes; unofficial, beyond Intel's spec, proven reliable). The offload plan is active and the limp-mode guidance is retired.
- **Mac mini (Late 2014, Macmini7,1) → Ubuntu Server** — the Docker host for anything you don't want on the NAS's locked-down DSM. True idle ~6-10 W; ~10-15 W running the container stack. It's a **dual-core i5-4278U with 8 GB of RAM soldered to the board — non-upgradeable, ever** — so treat it as a fixed *light* host: the web/management stack only (see capacity note).

**Heavy 24/7 tier (powerful; the idle bill is a deliberate trade):**

- **CachyOS rig (3090 Ti / 12700K, 64 GB RAM)** — the *local-LLM, game-streaming, and heavy-game-server box*, now running **24/7** (decision 2026-07-08: ~130 W idle ≈ $23/mo, accepted for availability). Gemma/Qwen/DeepSeek inference, Sunshine sessions, and beefy game servers are available anytime with no wake step; the open idle-power-tuning task (`game-09`) keeps the idle number honest. WoL stays configured purely as recovery.

## What runs where

Below is the plan's intended assignment, annotated with **live 2026-07-14 reality** where it differs. Retired/removed items are struck and explained.

| Service | Host | Why / status |
|---|---|---|
| File storage, Immich, Plex, Calibre-Web-Automated, backups | DS920+ | Always on, low power, Quick Sync transcode. **Live** (Immich v2.7.5, CWA NextGen v4.0.7). |
| Heavy/always-on offload: Paperless-ngx, Frigate *(~~Dependency-Track~~, ~~Tdarr~~ removed)* | DS920+ | Co-located with the data/media they touch. **Status:** Paperless-ngx is **planned (not yet deployed)**; Frigate is **deferred** (Protect judged sufficient); **Dependency-Track is fully retired**; Tdarr was removed 2026-07-08. |
| Docker stack: Seerr, **MusicSeerr**, Miniflux, Navidrome, Pinchflat, Wallabag, Mealie, Tautulli/Kometa (~~Maintainerr~~ removed), Homepage, Caddy, AdGuard+Unbound, monitoring (Beszel/Uptime-Kuma/ntfy), Forgejo *(~~LiteLLM~~ never deployed)* | Mac mini (Ubuntu) | Flexible Docker host, ~12 W, no DSM constraints. **Live** on mini: caddy, homepage, kometa, mealie, miniflux(+db), musicseerr, navidrome, ntfy, pinchflat, romm(+db), tautulli, wallabag(+db+redis), beszel(+agent). **LiteLLM was never deployed** (phantom). |
| qBittorrent → **Deluge** + Sonarr/Radarr/Prowlarr/Bazarr + sync agent | Managed seedbox — **Bytesized** (off-site) | Keeps all P2P off the home network. **Corrected model:** the seedbox ("Betty") runs **only Deluge + slskd**; the full *arr suite runs **on the NAS** — see [Media acquisition](replacements.md). |
| Home Assistant | **HA Green (purchased)** | Isolated, always-on, low power. **Live** — v2026.6.4, RUNNING. |
| One light game server | Mac mini (Ubuntu) | The 8 GB box has room for *one small* server alongside the stack. Heavier servers run on the rig. |
| Local LLM (Ollama), Open WebUI, Sunshine streaming, heavy game servers, gaming | CachyOS rig | Runs 24/7; WoL kept as recovery tooling only. Heavy game servers run via **AMP on the rig**. |
| Routing, firewall, VLANs, WiFi | Dream Wall | Already always-on. |

> If you'd rather consolidate, the Mac mini's services could also live on the NAS via Container Manager. But keeping a separate Docker host means a NAS firmware update or a runaway photo-index job never takes the containers down with it. Worth the extra ~$20/year.

## Capacity note — both always-on boxes are RAM-constrained

The Mac mini is a **Late-2014 Macmini7,1 (dual-core i5-4278U) with 8 GB soldered — it cannot be upgraded, ever.** Treat it as a fixed *light* host: the Docker web/management stack fits ~8 GB with little to spare, so **no heavy game servers, no real local LLM model, and no HA VM live here** — those belong on the rig (24/7) or the HA Green.

**Original offload rationale (kept for history, now partly moot):** the heavy hitters — two Java apps (Dependency-Track's apiserver wanted ~4 GB+, plus Paperless's Tika), Frigate's live object detection, and the database pile — would thrash an 8 GB box, so they were slated to move to the NAS next to the data. **What actually happened:**

- The NAS RAM upgrade to **20 GB is done** (validated live), so the offload plan is active and the limp-mode guidance is retired.
- **Dependency-Track (and the whole SBOM feature) was retired** — it never became a permanent NAS resident and is gone.
- **Tdarr was removed** from the plan entirely (2026-07-08).
- **Frigate is deferred** (UniFi Protect's built-in detection is enough for now).
- **Paperless-ngx** remains the intended NAS offload but is **not yet deployed**.

The enduring point stands: don't put heavy Java + live video + many DBs on the small Mac mini.

---
[← index](index.md)

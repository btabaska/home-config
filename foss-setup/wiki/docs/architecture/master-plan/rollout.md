# Suggested rollout (phased)

Do a phase before starting the next; each leaves you better off. **Status notes reflect live reality 2026-07-14** — most of Phases 1-3 and much of 4-5 are already done.

## Phase 1 — Foundation (network, access, safety net)

1. **Back up your UniFi config**, then build the segmentation: Default(mgmt) / Trusted / IoT / Cameras / Work / Guest, the firewall rules, mDNS reflector on + IGMP snooping off. (One-way door — back up first.) **✅ Done** (segmentation live, operator-confirmed).
2. **Install Tailscale** on the NAS, Mac mini, rig, laptop, and phone. Turn on **Tailscale SSH** (`tailscale up --ssh`) with `tag:admin`→`tag:server` ACLs, drop in the `~/.ssh/config` aliases + ed25519 key as break-glass (enable SSH on DSM, the HA SSH add-on). **✅ Done** (aliases work; `net-14` closed). Note HA is not a tailnet node — driven via REST.
3. **Lock in backups:** Synology Hyper Backup + Snapshot Replication, plus a Restic/Kopia job for irreplaceable data → B2. Test one restore. Follow `reference/nas/volume-schema.md` when reorganizing shares. **✅ Done** (encrypted NAS→B2 task live; restic dead-men FRESH).

## Phase 2 — De-cloud the essentials

3a. **Prerequisite — prep the Mac mini Docker host.** Install Docker and **create the shared proxy network once: `docker network create edge`**. Every web stack joins `edge` as `external`; Caddy later reaches each service by container name across it. **✅ Done.**

4. **Home Assistant** (HA Green): add Hue (local), Midea (local via `midea_ac_lan`), Nest (SDM API). Move smart devices onto IoT. Build the backbone: Zigbee coordinator + Zigbee2MQTT + Mosquitto, HA Companion app + presence, UniFi Protect integration, HomeKit Bridge, scheduled HA backups to the NAS (key in Proton Pass), Node-RED if needed. **✅ Live:** HA Green v2026.6.4, Hue (14 entities), HomeKit Bridge, encrypted daily NAS backups. **⚠️ Corrected:** point local voice **directly at the rig's Ollama** (`conversation.rig_ollama_assist`) — the LiteLLM/mini-fallback path is retired. Zigbee sensor rollout is deferred (hardware, staged).

5. **Seedbox pipeline:** sign up for the **Bytesized** seedbox, run the acquisition stack, put the seedbox on Tailscale, sync to the NAS library, then decommission the old NAS dual-LAN/Gluetun setup. **✅ Live — corrected architecture:** the seedbox ("Betty") runs **Deluge + slskd only**; the **full *arr suite runs on the NAS**, reading completed downloads via an rclone SFTP mount. See Section 2 (`replacements.md`).
   - **Music:** **Lidarr** on the NAS; torrents via Deluge, Soulseek via slskd (Betty) + Soularr (NAS) → Navidrome. **✅ E2E validated** (`seed-10`).

6. **Immich** with phone auto-backup; import the mirrorless SD card via immich-go / pbak. **✅ Live** (v2.7.5).

## Phase 3 — The analogue media stack

7. **Calibre + Calibre-Web-Automated + KOReader (Kobo) + Syncthing** for reading. **✅ Live** (Calibre `read-01`; CWA NextGen v4.0.7; KOReader-on-Kobo `read-04`).
8. **iPod via Rhythmbox/libgpod** + **gPodder** (one plug-in syncs music + podcasts); add **Pinchflat** to archive YouTube channels into Plex. **✅ Live** (iPod sync `read-11`; Pinchflat on the mini → Plex YouTube library).
9. **Miniflux** (+ optional Wallabag) for RSS, wired into KOReader. **✅ Live** (both on the mini).
10. **Turn on Obsidian Sync** (paid, official). **✅ Done** (`read-13`).
11. **Paperless-ngx** for documents + **Mealie** for recipes. Keep **Proton Pass**. **Mealie ✅ live**; **Paperless-ngx planned, not yet deployed**; Vaultwarden retired 2026-07-22 (foss-01) — passwords consolidated on Proton Pass.

## Phase 4 — Glue & polish

12. Stand up the management layer: **Homepage** + **Dockhand/Dockge** + **Beszel** + **Uptime Kuma** + **ntfy** + **Caddy**, add **AdGuard Home** for DNS filtering (then Unbound/DoT + a second resolver). **✅ Live** (Homepage, Caddy, Beszel, ntfy on the mini; AdGuard on mini + NAS; fail-open three-tier DNS).
13. **Wire LAN app hosting:** add the `*.home.lan` wildcard DNS record in AdGuard, let **Caddy** route by hostname, ship vibecoded apps as small Compose stacks behind Caddy (option A). **✅ Live (option A).** **⚠️ Corrected:** Coolify (option B) was **dropped** — non-starter on the 8 GB mini.
14. **Media companion layer:** **Tautulli** + **Kometa** on the mini. **✅ Live.** *(~~Maintainerr~~ + ~~Tdarr~~ removed 2026-07-08.)* **Frigate deferred** (Protect judged sufficient).
15. **Harden it:** MFA/2FA everywhere, Docker log rotation, immutable backups (B2 Object Lock), a Healthchecks.io dead-man's-switch, CrowdSec/forward-auth on the seedbox + public ports. **Partial:** Healthchecks live; B2 Object Lock scoped to `sec-03`; credential rotations deferred (`#18`).
16. Push all compose files + configs to **Git**. **✅ Done** (dual remotes: GitHub `btabaska/home-config` + Forgejo `home/homelab`).
17. **Inventory/SBOM layer:** self-host **Forgejo**, turn on **etckeeper** + **chezmoi** + the nightly manifest job, commit the **`ansible/`** playbooks, ~~stand up Dependency-Track v5~~, encrypt secrets with **SOPS + age**, write + drill restore runbooks. **⚠️ Corrected:** **Dependency-Track / SBOM is fully retired** (see Section 8, `inventory-sbom.md`). Forgejo + etckeeper + chezmoi + Ansible are the surviving pieces; the rebuild-drill capstone is deferred.

## Phase 5 — Play

18. **Game servers:** light games on the Mac mini, heavy games on the rig (24/7), friends in via Tailscale. **⚠️ Corrected & live:** heavy servers run via **AMP on the rig** (Minecraft Java+Bedrock, Palworld), exposed via **playit premium** (not LinuxGSM, not Tailscale). See `reference/gaming/server-guide.md`.
19. **Sunshine** on the rig + **Moonlight** clients; set up the headless display (dummy HDMI or the Apollo-Linux/`sunshine_virt_display` virtual display); confirm Tailscale "direct" for remote. Add a launcher (Heroic/Lutris + RomM) and Ludusavi + Syncthing save-sync. **✅ Live:** in-home (`game-06`) + remote-direct (`game-07`) streaming; RomM live (4.9.2). Launcher bundle deferred; save-sync folds into the Syncthing hub task.
20. **Tune the rig (`game-09` — idle-power tuning):** GPU idle/undervolt + power-limit tuning to shave the ~130 W idle, keep WoL as recovery, set the **GPU contention policy** (Ollama `keep_alive=0`) so streaming/servers/AI share the one card. Optionally add ComfyUI / Continue / Open WebUI RAG. **Open** (`game-09`).

---
[← index](index.md)

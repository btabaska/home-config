# The stack at a glance

The whole build in one table, mapping each Apple/iOS task to its FOSS replacement and host. **Retired/removed/corrected items are annotated.**

| Apple/iOS task | FOSS replacement | Runs on |
|---|---|---|
| iCloud Photos | **Immich** (v2.7.5 live) | NAS |
| Camera (RAW) photo import | **immich-go** / **pbak** | desktop → NAS |
| Apple Music (own files) | **Navidrome** (+ Symfonium/Amperfy) | Mac mini |
| iPod sync | **Rhythmbox / libgpod** (Apple firmware) | device |
| Apple Podcasts | **gPodder** (+ optional sync server) | desktop |
| Apple News / RSS | **Miniflux** (or FreshRSS) + Wallabag | Mac mini |
| Kindle/iBooks | **Calibre + CWA (NextGen v4.0.7) + KOReader (Kobo) + Syncthing** | NAS + device |
| Apple Notes | **Obsidian + Obsidian Sync** (paid, official) | desktop |
| iWork / MS Office | **LibreOffice** (or OnlyOffice/Collabora) | CachyOS |
| Plex / TV | **Plex** (keeping; Jellyfin = FOSS fallback) | NAS |
| Plex stats & monitoring | **Tautulli** | Mac mini |
| Library polish (collections/overlays) | **Kometa** | Mac mini |
| Quality profiles / extraction | **Recyclarr** + **Unpackerr** | NAS (with the *arrs) |
| Library pruning | ~~Maintainerr~~ — removed 2026-07-08 (no auto-deletion) | — |
| Pre-transcode automation | ~~Tdarr / FileFlows~~ — removed 2026-07-08 (conflicts with TRaSH; storage not scarce) | — |
| YouTube / web video archive | **Pinchflat** (Tube Archivist / MeTube alt) | Mac mini |
| Private media acquisition | **Managed seedbox** (Deluge + slskd) + **Seerr** + **MusicSeerr** | off-site (Betty) + Mac mini + NAS |
| Automated music acquisition | **MusicSeerr** + **Lidarr** + **Soularr** + **slskd** (Betty) + **beets** | Mac mini + NAS + seedbox |
| Documents (scan/OCR/search) | **Paperless-ngx** *(planned, not yet deployed)* | NAS |
| Recipes & meal planning | **Mealie** | Mac mini |
| Passwords | **Bitwarden** (Vaultwarden if self-hosting) | cloud / optional self-host |
| iCloud Drive/Contacts/Calendar | **Proton** or **Nextcloud** or **Syncthing + Baikal** | cloud/NAS |
| Safari | **Firefox / LibreWolf / Zen** + Kagi | CachyOS |
| Siri / smart home (Hue, Nest, Midea) | **Home Assistant** + local voice (Whisper/Piper + **rig Ollama**) | HA Green |
| Local sensors | **Zigbee2MQTT + Mosquitto** (+ USB coordinator) *(deferred)* | HA |
| Cameras / NVR AI | **UniFi Protect → HA** (Frigate deferred) | Dream Wall / HA |
| Apple Home compatibility | **HA HomeKit Bridge** (live) | HA |
| Local AI assistant | **rig Ollama, direct** *(LiteLLM gateway/fallback retired — AI-SPOF accepted)* | CachyOS rig |
| Image gen / coding AI | **ComfyUI** / **Continue** / **Aider** | CachyOS rig |
| GeForce Now / game streaming | **Sunshine + Moonlight** (+ virtual display) | rig (host) + clients |
| Game launcher / retro | **Heroic / Lutris** + **RomM** (RomM live 4.9.2; launcher deferred) | rig / Mac mini |
| Save-game sync | **Ludusavi + Syncthing** *(folds into Syncthing hub)* | rig + clients |
| Hosting game servers | **AMP on the rig** (heavy) / one light on Mac mini *(LinuxGSM superseded)* | rig / Mac mini |
| Exposing game servers to friends | **playit premium** *(Tailscale-expose superseded)* | rig |
| Remote access | **Tailscale** | all |
| SSH / fleet maintenance | **Tailscale SSH** + **~/.ssh/config** + **Ansible** | all hosts |
| Network segmentation | **UniFi VLANs + Zone-Based Firewall** | Dream Wall |
| Ad/tracker DNS | **AdGuard Home** (+ Unbound/DoT; fail-open three-tier) | Mac mini + NAS |
| Auth / MFA for exposed apps | **CrowdSec** + forward-auth (Pocket-ID/Authelia) | seedbox / Mac mini |
| Backup monitoring | **Healthchecks.io** (dead-man's-switch) | Mac mini |
| Container mgmt | **Dockhand** / Dockge / Komodo | Mac mini |
| Self-hosted app deployment | **Caddy-fronted Compose stacks** *(Coolify/Dokploy dropped)* | Mac mini |
| Dashboard / service launcher | **Homepage** (Homarr if multi-user) | Mac mini |
| Monitoring | **Beszel** + Uptime Kuma + ntfy | Mac mini |
| Backup | **Restic/Kopia** + Borg + Synology native | NAS + hosts |
| SBOM / vuln inventory dashboard | ~~OWASP Dependency-Track v5 (+ Syft/Grype)~~ — **RETIRED** | — |
| Config/dotfile/state-in-Git | **etckeeper** (/etc) + **chezmoi** (~) + **Forgejo** control repo | all hosts |
| Fleet provisioning / convergence | **Ansible** (`ansible-pull` + roles, SOPS-integrated) | control repo → rig + Mac mini (+ seedbox user-space) |
| Secrets at rest | **SOPS + age** (chezmoi age for dotfiles) | control repo |
| Local LLM | **Ollama** + Open WebUI | CachyOS rig (24/7) |

Already in the stack and worth keeping: **Kagi** (search), **ProtonMail/VPN/Drive/Calendar/Pass**, and **Plex** (lifetime pass — staying; Jellyfin is the FOSS fallback only if Plex ever paywalls something you depend on).

---
[← index](index.md)

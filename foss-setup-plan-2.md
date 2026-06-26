# Going Analogue: A FOSS Computing Setup

A reference build for moving off the Apple/iOS ecosystem onto your own hardware, with as much current open-source tooling as possible. Scoped to what you already run (CachyOS rig, DS920+, Mac mini/Ubuntu, Dream Wall, Hue, Nest, Midea, Plex, Kagi, Proton) and what you're moving toward (iPod Classic, eReader, Immich, Obsidian, Home Assistant, self-hosted RSS, game servers, game streaming).

The FOSS world genuinely moved in the last year. The shifts relevant to you: Immich shipped a stable 2.x line and 3.0 is now in release-candidate (no longer "don't trust it with your only copy", though 3.0's headline workflow/transcoding features are still labeled preview); Plex hiked its lifetime price ($119.99 -> $249.99 in 2025, and **tripling again to $749.99 on July 1, 2026**) and paywalled remote *video* streaming, pushing the hobby toward Jellyfin; Calibre-Web forked into a far better automated version; Rockbox on the iPod Classic got a modern bootloader; a new wave of single-binary homelab tools (Dockhand, Komodo, Beszel) replaced the older sprawl; UniFi moved to a zone-based firewall; and Sunshine + Moonlight matured into a genuinely excellent self-hosted GeForce-Now replacement.

---

## 0. The host decision that drives everything: 24/7 vs. on-demand

Before any app choice, settle this. It's the difference between a ~$160/year power bill and a ~$700+/year one, and it's *also* what makes the whole thing "set and forget."

**Always-on tier (the quiet workhorses):**
- **DS920+ NAS** — storage, plus the home for most lightweight always-on services. Its Celeron J4125 has Intel Quick Sync, so it can even handle Jellyfin transcoding for a stream or two.
- **Mac mini 2015 -> Ubuntu Server** — your Docker host for anything you don't want on the NAS's locked-down DSM. True idle is ~6-10W; figure ~10-15W running the container stack and a couple of light game servers, which live here.

**On-demand tier (powerful but expensive to idle):**
- **CachyOS rig (3090 Ti / 12700K)** — your *local-LLM, game-streaming, and heavy-game-server box*, not a 24/7 server. Wake it for Gemma/Qwen/DeepSeek inference, a Sunshine streaming session, or a beefy game server; let it sleep otherwise. Running it 24/7 just to host services would dwarf every other cost on this page.

### What runs where

| Service | Host | Why |
|---|---|---|
| File storage, Immich, Plex, Calibre-Web-Automated, backups | DS920+ | Always on, low power, Quick Sync transcode |
| Docker stack: Jellyseerr/Seerr (request portal), Miniflux, Navidrome, reverse proxy, monitoring, Pi-hole | Mac mini (Ubuntu) | Flexible Docker host, ~12W, no DSM constraints |
| qBittorrent + Sonarr/Radarr/Prowlarr/Bazarr + sync agent | Managed seedbox (off-site) | Keeps all P2P off your home network; ISP never sees a swarm (see Media acquisition) |
| Home Assistant | HA Green or HAOS VM on Ubuntu | Isolated, always-on, low power (see Smart Home) |
| Light game servers (Minecraft, Valheim, Terraria, Factorio) | Mac mini (Ubuntu) | Always-on so friends can hop on anytime |
| Local LLM (Ollama), Open WebUI, Sunshine streaming, heavy game servers, gaming | CachyOS rig | On-demand only; Wake-on-LAN + auto-suspend |
| Routing, firewall, VLANs, WiFi | Dream Wall | Already always-on |

> If you'd rather consolidate, the Mac mini's services could also live on the NAS via Container Manager. But keeping a separate Docker host means a NAS firmware update or a runaway photo-index job never takes your containers down with it. Worth the extra ~$20/year.

---

## 1. The home network: segmenting the UniFi Dream Wall

The Dream Wall is your all-in-one core (router + firewall + a 17-port GbE switch with 12 PoE ports + 2x 10G SFP+, split one LAN / one WAN + WiFi 6 + the Network controller), so everything hangs off it. Goal: isolate the risky stuff (IoT, guests, work laptop) for security and privacy, without over-engineering — which kills both your sanity and, via mDNS headaches, your smart home.

### The honest answer on "how many networks"
Resist the urge to build a VLAN per use case. Experienced UniFi operators are blunt about this: IoT is just another internal VLAN, and over-zoning multiplies the policy surface for no benefit. And a separate gaming/streaming VLAN actively *hurts* — Moonlight discovers the Sunshine host via mDNS on the same subnet, so different VLANs force a router hop and break auto-discovery. More SSIDs also eat WiFi airtime. So: **~4-5 networks, and gaming/streaming stays on your trusted network with QoS, not its own VLAN.**

### The layout

```
Fiber  ->  ISP ONT (bridge mode)  ->  UniFi Dream Wall  ->  [downstream UniFi switches / APs]  ->  devices
                                          (router + firewall + switch + WiFi6 + controller)
```

UniFi's Zone-Based Firewall ships with six built-in zones — **Internal, External, Gateway, VPN, Hotspot, DMZ**. By default all your LANs land in *Internal* and the WAN is *External*. For real segmentation you **create custom zones** (e.g., Trusted, IoT, Cameras, Work) and assign each network to one. The table below uses those custom zone names:

| Network (VLAN) | Firewall zone | What's on it |
|---|---|---|
| Default (mgmt) | Internal | UniFi gear only — gateway, switches, APs. Don't put clients here. |
| Trusted | Trusted | PCs, NAS, Mac mini, phones, consoles, **Sunshine host + Moonlight clients** |
| IoT | Untrusted | Hue bridge, Nest, Midea AC/dehumidifier, smart TVs / streaming sticks |
| Cameras (optional) | Untrusted | Any IP cameras — most locked down, no internet |
| Work | own / Trusted | Nava work laptop — internet only, no access to other VLANs |
| Guest | Hotspot | Visitors — isolated, client isolation on |

Home Assistant lives on **Trusted**, not IoT — and never dual-home it across two NICs (that's a security hole). It reaches IoT devices because Trusted -> IoT is allowed.

### Firewall rules that actually isolate (UniFi Network 9.x = Zone-Based Firewall)
**Back up your config first — migrating to the Zone-Based Firewall is a one-way door**, and it can sever VPNs, mDNS, and inter-VLAN flows if you rush it.

The model: **allow Trusted -> Untrusted (return traffic is automatic — these firewalls are stateful, so you do not need an "allow established/related" rule); block Untrusted -> Trusted; add narrow pinholes for the few flows that must cross.** Concretely for the IoT VLAN:
- Allow IoT -> internet, and allow IoT -> gateway for DNS (53) and DHCP (67/68). **Never blanket-block the gateway** or devices can't get an IP or resolve names.
- Block IoT -> RFC1918 (10/8, 172.16/12, 192.168/16) so it can't reach any of your other subnets.
- Block IoT -> gateway admin (HTTP/HTTPS/SSH) so a compromised device can't touch your router console.
- **Order matters:** specific allows must sit above the broad block, and UniFi custom policies outrank built-ins — use Reorder. Rules are **directional** (blocking A->B still allows B->A unless you also block that).
- **Work VLAN:** internet-only; block -> all other VLANs.
- **Guest:** use UniFi's built-in Guest network type (auto-isolation) + enable Client Device Isolation.

### Don't break casting and your smart home (mDNS)
Home Assistant, Chromecast, AirPlay, Matter, and Sonos all rely on mDNS/multicast, which doesn't cross VLANs by default. To keep discovery working between Trusted and IoT:
- Settings -> Networks -> **Multicast Settings: enable mDNS / IoT Auto Discovery** for those networks.
- **Turn IGMP Snooping OFF** — UniFi's implementation is aggressive and drops the discovery packets Apple TVs / HomePods / Matter devices depend on.
- **Matter caveat:** Matter uses link-local IPv6 multicast and is genuinely hard to isolate on a separate VLAN from HA. Your current devices (Hue via Zigbee bridge, Nest and Midea over WiFi/IP) are fine on the IoT VLAN. If you later add Matter devices and they misbehave across VLANs, put those specific devices on HA's VLAN.

### Security & privacy extras
- **Enable IDS/IPS** (Threat Management) on the Dream Wall — it has the CPU for it. It can cap throughput at multi-gig line rates, but for typical use it's worth the protection.
- **Network-wide DNS filtering:** run **Pi-hole** or **AdGuard Home** (HA add-on or a container) and point your VLANs' DHCP DNS at it — blocks ads/trackers at the network level, a real privacy win and a nice complement to IoT isolation.
- Once Hue is fully local in HA, you can block the Hue bridge from the internet. (Nest needs Google's cloud; Midea can be made fully local with an ESPHome dongle — see Smart Home.)
- Use WPA3 where devices support it; map one SSID each to Trusted, IoT, Guest, and Work.

### Speed
Performance comes from physics and tuning, not segmentation:
- **Wire what you can** — the rig, NAS, Mac mini, and any Moonlight client near the TV. Ethernet beats WiFi for both throughput and latency.
- WiFi 6 on the Dream Wall (6E/7 if you add newer APs); pick clean DFS channels, sensible channel widths, and keep the SSID count low (each SSID consumes airtime).
- For local Moonlight/Sunshine, same-VLAN + wired = effectively zero added latency. Only reach for QoS / Smart Queues if you actually see contention; on fiber you usually won't.

---

## 2. Open-source replacements, by Apple/iOS task

For each: the pick, the runners-up, and what's new. Bold = recommended.

### Photos (iCloud Photos / Apple Photos)
- **Immich** — now a mature, stable project. Self-hosted, iOS/Android apps with automatic background backup, face/object recognition, "Free Up Space" to offload phone storage after backup, non-destructive editing, and (3.0 line, currently preview) automation workflows and real-time transcoding. Standout iCloud Photos replacement, ready for primary use (still: keep backups, see Section 6).
- *Runner-up:* **PhotoPrism** (more "archive/browse"); **Synology Photos** (turnkey, less polished, ecosystem lock-in).
- *Host on:* the NAS. Point its library at your existing storage; use the VectorChord Postgres image it ships with.

### Music — library + streaming (Apple Music / iTunes library)
- **Navidrome** — self-hosted music server (Subsonic API). Stream your own collection without a subscription. Mobile clients: **Symfonium** (Android, excellent), **play:Sub** / **Amperfy** (iOS); desktop: **Feishin** or **Supersonic**.
- Separate from getting music onto the iPod (next).

### iPod Classic
**Decision: keep Apple firmware + libgpod tools.** Sync from Linux with **Rhythmbox** (simplest, built-in iPod support), with **gtkpod** (power-user, aging) or **Clementine** as alternatives. This keeps the device stock — car/USB-controller compatibility intact — and you manage the library the familiar way. Set a static library workflow and it's reliable.
- *Gotcha:* libgpod-based sync writes Apple's iPod database; occasionally a sync needs a re-init if the DB gets confused. Keep your music master library on the NAS (Navidrome's library) so the iPod is always a reproducible copy.
- *If you ever want to drop the database hassle entirely:* **Rockbox** turns the iPod into a plain drag-and-drop USB drive (FLAC/Opus, custom EQ) via a modern bootloader (installed using the freemyipod project's tooling) — but it loses Apple's car/USB-control integration, so it's only worth it if that compatibility stops mattering.

### Podcasts (Apple Podcasts)
- **gPodder** — maintained desktop podcatcher (RSS / YouTube / SoundCloud), batch-download, auto-cleanup (development is ongoing, though the last stable release was Dec 2024). With a Rockbox'd iPod: gPodder downloads into a folder, you copy/sync that folder to the device.
- *Optional sync server* (if you also listen on a phone and want play-position synced): self-host **oPodSync**, **goPodder**, or **Sintoniza**. Skip if the iPod is your only podcast device.

### News / RSS (Apple News, algorithmic feeds)
- **Miniflux (recommended)** — minimalist, single static Go binary (tiny footprint, typically low tens of MB RAM), PostgreSQL backend (Postgres is required — no SQLite/MySQL), deliberately distraction-free, strips tracking pixels, full-text fetch, and speaks the Fever + Google Reader APIs so native apps (NetNewsWire, Reeder, NewsFlash, Readrops) sync to it. The spartan UI is a feature for "going analogue"; lowest-maintenance once running.
- **FreshRSS** — PHP, more features and an extension ecosystem (YouTube-channel-to-RSS, podcast feeds, scraping bridges), runs as a single container with SQLite (no separate DB), larger community. Pick this if you want extensions/customization.
- *Tie-ins:* pair with **Wallabag** (self-hosted read-it-later, replaces Pocket); both Miniflux/FreshRSS and Wallabag feed into **KOReader's news/RSS and Wallabag plugins**, so you can read feeds and saved articles on the eReader.

### Reading / eReader (Kindle + iBooks)
- **Calibre** (desktop) — library master and conversion engine.
- **Calibre-Web-Automated (CWA)** — the actively-developed fork. Auto-ingest folder, an EPUB-fixer that cleans files so Send-to-Kindle stops rejecting them, metadata/cover enforcement written into the files, OPDS server, native Kobo sync, and **built-in zero-config KOReader progress sync**. One Docker container on the NAS.
- **KOReader** — open reader for the device. Runs on Kobo, jailbroken Kindle, PocketBook, Boox, reMarkable, Android. Stores progress in accessible files; OPDS + Calibre wireless plugin.
- **Syncthing** — peer-to-peer sync of books and progress files. No cloud.

Device notes: **Kobo** = smoothest (native CWA sync + optional KOReader). **Kindle** = jailbreak + KOReader (worth it — Amazon removed "Download & transfer via USB" in Feb 2025, and ended Kindle Store support for pre-2013 devices on May 20, 2026; those devices can't buy/download new books and are effectively bricked only if reset or deregistered). **Buying new?** Kobo / PocketBook / Boox are friendliest.

### Notes (Apple Notes — already on Obsidian)
**Decision: paid Obsidian Sync.** Official, end-to-end encrypted, zero setup, nothing to self-host or maintain — the right call given the set-and-forget priority. Your notes remain plain local Markdown, so you still own the data and it's still captured by Section 6's backup. (If you ever want to drop the subscription, self-hosted LiveSync + CouchDB or plain Syncthing are free alternatives — but there's no reason to complicate this now.)

### Office (Pages/Numbers/Keynote, MS Office)
- **LibreOffice (26.2)** — mature desktop-first FOSS suite (year.month versioning; 26.2 is the current line as of mid-2026, after 25.8 reached end-of-life in June 2026). For solo, offline, local work on CachyOS, the obvious baseline.
- *Better MS fidelity:* **OnlyOffice Desktop** (OOXML-native). (Open-core; the old 20-concurrent-connection community limit on the server edition was removed in Docs 9.4, May 2026; had a 2026 falling-out with Nextcloud after Nextcloud/IONOS/Proton forked it into "Euro-Office.")
- *Browser-based collaboration:* **Collabora Online** (LibreOffice-based, lighter to self-host) with Nextcloud.

**Recommendation:** LibreOffice desktop. Don't self-host an office server unless you want in-browser collaboration.

### Video / media server (Plex — staying)
**Decision: keep Plex** (grandfathered lifetime pass). Nothing changes here — your library stays on the NAS and Plex serves it, and your existing Lifetime Pass is unaffected by the upcoming price change (the new-purchase lifetime price triples to **$749.99 on July 1, 2026**, up from $249.99 — so your grandfathered pass is now worth even more). Note the 2025 remote-streaming paywall applies to **video** only; remote music/photo streaming stays free. (Jellyfin remains the FOSS fallback if Plex ever paywalls something you depend on; you can stand it up alongside Plex in ~30 min pointed at the same folders, no re-organizing. But no action needed now.)

### Media acquisition — private, off-site (replaces the dual-LAN VPN/Gluetun setup)
**Decision: a managed seedbox runs the whole download stack off-site; finished media syncs to the NAS for Plex.** This retires the home VPN routing entirely.

Why this is the answer to "never visible to my ISP" *and* the network crashes: the old setup torrented on the NAS behind a home VPN, and thousands of simultaneous peer connections (DHT/uTP especially) exhausted the connection-state (conntrack) table until you rebooted — the classic torrent-kills-the-network failure. (VPN encapsulation adds its own MTU/fragmentation headaches on top, a separate reliability drag — though note a full tunnel can actually *reduce* the router's tracked-connection count by collapsing all peers into one encrypted flow.) The 5 Mbps cap was a band-aid. A seedbox eliminates the root cause: **the P2P happens on a rented server, so your home network only ever does one tidy encrypted download from a datacenter.** Your ISP never sees a swarm (or even an always-on VPN tunnel) — just a normal-looking transfer — which is the purest form of "invisible to my ISP."

**The pipeline (fully automated: request -> auto-appears in Plex):**
1. **Jellyseerr/Seerr** (request portal) — runs at home on the Mac mini; household members request a title from their phone or Apple TV. (Use **Seerr**, the 2026 unified successor of Overseerr + Jellyseerr — image `ghcr.io/seerr-team/seerr`. Overseerr's development had stalled since ~2023 and its repo was finally archived (read-only) on Feb 15, 2026 with an in-app migration notice pointing to Seerr. Jellyseerr is the fork most seedbox app stores still ship and is fine too — it's literally the codebase that became Seerr. All support Plex.)
2. **Sonarr / Radarr** (on the seedbox) — receive the request, search via **Prowlarr** indexers, hand off to **qBittorrent** (on the seedbox).
3. **qBittorrent** downloads at full seedbox speed, then Sonarr/Radarr rename/organize; **Bazarr** grabs subtitles.
4. **Sync agent** (Syncthing or rclone, on the seedbox) pushes the finished, named files into the NAS library folders.
5. **Plex** (home) imports them; Seerr sees they're available and notifies the requester.

**How the home and seedbox talk:** put the seedbox on your **Tailscale** tailnet, so Seerr (home) reaches Sonarr/Radarr (seedbox) and the sync runs privately, with nothing exposed to the internet. Use SFTP/Syncthing (encrypted) for the file transfer — never plain FTP.

**Provider pick (managed, ~$15-30/mo, set-and-forget):** prioritize **unlimited upload bandwidth** (not an upload cap) if you use private trackers and need to seed for ratio, a **privacy-friendly jurisdiction** (Netherlands is common) with minimal logging, and a one-click app catalog that includes qBittorrent + the *arr suite + rclone/Syncthing. Strong options: **Whatbox** (excellent privacy reputation, generous storage, SSH access), **Seedboxes.cc** or **DediSeedbox** (unlimited bandwidth, good for seeding), **Bytesized** (slickest UI, easy Plex/Resilio). Avoid upload-capped tiers (e.g., Ultra.cc's entry plans) if you seed private trackers, since seeding stops once you hit the cap.

**Decommission the old setup:** remove qBittorrent/Gluetun from the NAS, undo the dual-LAN policy routing, and drop the 5 Mbps throttle. The second NAS LAN port is freed up (use it for link aggregation/failover, or leave it). If you ever torrent at home again, the fix for the crashes is simply capping qBittorrent's global max connections (~200) and per-torrent peers — but with the seedbox you won't need to.

### Files, Contacts, Calendar (iCloud Drive / Contacts / Calendar)
The gap people forget when leaving Apple. Three approaches:
- **One hub — Nextcloud.** Files (sync clients + WebDAV), Contacts (CardDAV), Calendar (CalDAV), optional Office/photos. Closest single-app iCloud replacement; heavier to run.
- **Discrete tools (lighter).** **Syncthing** for files + **Baikal** or **Radicale** as a tiny CalDAV/CardDAV server.
- **Lean on Proton (least effort).** You already pay for it — **Proton Drive**, **Proton Calendar**, **Proton Pass** cover much of this with zero hosting.

**Recommendation:** for minimal moving parts, use Proton for calendar/contacts/drive and Syncthing for the folders you want truly local. Stand up Nextcloud only if you want the single unified hub.

### Browser & the rest you already have
- **Browser (Safari -> ):** on CachyOS, **Firefox**, **LibreWolf** (hardened), or **Zen** (Firefox-based, polished). Set **Kagi** as default search.
- Keep **Kagi** (search) and **ProtonMail / VPN / Drive / Calendar / Pass**. Note: Proton VPN is for private egress; Tailscale (Section 7) is a *different* tool for reaching your own services — you'll want both.

---

## 3. Smart home: Home Assistant

Home Assistant (HA) is the hub, and a privacy win in itself: it pulls cloud-tethered devices into local control where possible, so your lights and climate keep working even when Google's or Midea's servers don't.

### How to run it (set-and-forget)
Two good options:
1. **HA Green (~$199) — zero-fuss.** Dedicated, plug-and-play, ~1.7-3W, isolated, auto-updates, full add-on ("Apps") support. (Launched at ~$99; the price rose through 2026 on component costs.) Best if you want it to sit in the rack and never think about it.
2. **HA OS in a VM on the Ubuntu box — consolidate.** Run HAOS as a KVM/libvirt VM (or via Proxmox). No new hardware, still full Supervisor + add-ons.

Avoid HA in plain Docker (you lose the add-on store + Supervisor) unless you specifically want that, and **never run HA on an SD card** — constant DB writes kill them. Back up to the NAS and **save the backup encryption key in your password manager** (you can't restore without it).

Given your set-and-forget priority: HA Green = lowest friction; HAOS VM = no new hardware.

### Your devices
- **Hue -> native, local.** HA's Hue integration talks to your Hue Bridge over the LAN — no cloud, rock solid, instant. Keep the bridge.
- **Nest -> works, but the fiddly one.** "Works with Nest" is gone; HA uses Google's Smart Device Management (SDM) API, which needs a Google Cloud project, the Device Access Console (one-time $5 fee), and OAuth. It works (thermostat control + sensors) but routes through Google's cloud (not local) and is the most involved of your three. Matter support for Nest *thermostats* has improved (the 4th-gen Nest Learning Thermostat ships with native Matter), but Matter thermostat control in HA can still be feature-limited/quirky, so SDM remains the most complete path today. If local control becomes a priority, a Matter or Zigbee thermostat is the cleaner long-term swap — but that's hardware, not now.
- **Midea AC + dehumidifier -> local, with a one-time handshake.** Use the **`midea_ac_lan`** HACS integration (actively maintained; also handles dehumidifiers) or **`midea-air-appliances-lan`**. They control units over the LAN; V3-protocol devices need a single connection to Midea's cloud to fetch a token/key, then run fully local. **Back up the per-device `.json` config files** — Midea has been closing its cloud token APIs, which can block *adding new* devices later (already-added devices keep working).
  - **Fully cloud-free option (recommended for privacy):** replace the OEM WiFi dongle with an **ESPHome-flashable dongle** (e.g., SLWF-01Pro, ~$13) — severs the unit from Midea's cloud and gives local ESPHome/MQTT control. Great fit since you're hands-on; with that done you can block those devices from the internet on the IoT VLAN.
  - Caveat: some Midea units built 2021+ use the Tuya platform — those use a LocalTuya integration, not the Midea ones. Check your model.

### Tie-ins worth doing
- **Local voice (replaces Siri/Alexa):** HA's Assist pipeline + the Whisper/Piper add-ons gives local speech, and you can point its conversation agent at **Ollama on your rig** for a fully local LLM assistant (rig is on-demand, so best for non-urgent queries — or keep a small always-on model).
- **Energy dashboard:** with a smart plug or whole-home monitor, HA tracks per-device power — directly useful for the 24/7 power question in Section 5.
- HA on Trusted reaches the Hue bridge and Midea units on IoT via the Trusted->IoT allow rule; no extra config beyond the mDNS settings in Section 1.

---

## 4. Game servers and game streaming

Two different things: **hosting servers** so friends can join, and **streaming your rig's games** to your own screens.

### Hosting servers for friends
Pick by how much you want to manage:
- **LinuxGSM** — command-line manager with install scripts for 100+ games. Lightest, no web UI, ideal if you're terminal-comfortable (you are) and want one or two servers.
- **Pelican Panel** — the modern, container-native game-server panel (community fork by former Pterodactyl contributors). Panel + "Wings" agent; game definitions ("eggs") are JSON, shared via Git and imported through the admin UI; huge game list. Best if you want to be the friend-group's "spin up any game" host with a clean web UI.
- **Pterodactyl** — the established panel Pelican forks from; still excellent, slightly heavier setup. **Crafty Controller** — simpler, Minecraft-focused.

**Where to run them:** light co-op (Minecraft, Valheim, Terraria, Factorio, Project Zomboid, Core Keeper) runs fine on the **Mac mini** — keep those always-on so friends can hop on anytime. Heavier servers (Palworld, ARK, modded packs) want the **CachyOS rig** — run on-demand, bring it up for game night (Wake-on-LAN).

**Exposing them safely (the important part):**
- **Friends-only co-op -> Tailscale.** Invite friends to your tailnet (or share just the server node). No ports open to the internet, encrypted, works great for co-op. The set-and-forget, secure default.
- **Public / many players -> careful port-forward or a tunnel.** Forward only the specific game ports on the Dream Wall to the server host, keep that host patched, and consider **Playit.gg** (a game-server tunnel) to avoid exposing your IP. Don't put the server on IoT; keep it on Trusted (or a dedicated server VLAN if you get serious) with only the needed ports allowed.

### Streaming your rig to your own screens (Sunshine + Moonlight)
Replaces NVIDIA's discontinued GameStream and beats GeForce Now / Xbox Cloud for self-hosters — your 3090 Ti's NVENC encoder does 4K/120 with HDR, free.
- **Host:** install **Sunshine** on the CachyOS rig (NVENC). Start on boot; set a username/password on its web UI (anyone who can reach it can add clients).
- **Clients:** **Moonlight** on laptops, Steam Deck, Apple TV, phone, or TV.
- **In-home:** keep host and clients on the **same (Trusted) VLAN** so Moonlight auto-discovers the host via mDNS and there's no inter-VLAN hop. Wire the host and the client near your TV. This is exactly why a "streaming VLAN" is the wrong move — it breaks discovery and adds latency.
- **Remote -> Tailscale.** Add the host in Moonlight by its Tailscale IP (100.x.x.x) — auto-discovery doesn't work over Tailscale's Layer 3. **Critical tuning:** make sure Tailscale gets a *direct* connection, not a DERP relay — relays are throughput-limited (often only tens of Mbps, and as low as single digits under load) and ruin the stream. Run `tailscale status` and confirm "direct"; if relayed, forward **UDP 41641** on the Dream Wall to the host so hole-punching succeeds (Tailscale's newer self-hosted Peer Relays are another fallback if direct fails). Then you're limited only by encoder + bandwidth (tens to hundreds of Mbps).
- **Wake-on-LAN ties it together:** with WoL + auto-login, you can wake the rig, stream a session, and let it sleep — the powerful box earns its keep on-demand instead of idling.
- *Handhelds:* for Android handhelds, the **Apollo** (Sunshine fork) + **Artemis** (Moonlight fork) pair adds touchscreen/on-screen-keyboard niceties; otherwise stock Sunshine + Moonlight is more stable.

---

## 5. Electricity cost of running hardware 24/7

**Your rate:** RG&E all-in residential runs about **$0.20/kWh** in 2026 (supply + delivery; per-kWh delivery alone is ~8.5c and supply floats seasonally). Rule of thumb:

> **1 watt running 24/7 ~ $1.75/year.** Every 100W you leave on ~ $175/year.

| Device | Typical draw | ~Annual cost @ $0.20/kWh |
|---|---|---|
| DS920+ + 4 large drives | ~35-45W (less if drives hibernate) | **~$60-80** |
| Mac mini 2015 (Ubuntu) | ~10-15W under load (idle ~6-10W) | **~$18-26** |
| HA Green (if used) | ~2-3W | ~$4-5 |
| Dream Wall router | ~30-40W | **~$55-70** |
| Fiber ONT/modem | ~5-10W | ~$10-15 |
| **Always-on subtotal** | **~80-115W** | **~$145-200/year** |
| CachyOS rig — *idling* | ~90-120W (3090 Ti idles ~20-30W alone, but on Linux can get stuck at ~100W+) | ~$160-210 *if left on* |
| CachyOS rig — *under LLM / streaming / heavy-server load* | 400-600W+ | ~$700-1,000+ *if sustained 24/7* |

**Takeaways:**
1. **The rig is the entire story.** Always-on gear is cheap (~$150/year). Idling the 3090 Ti adds as much again; sustained load 24/7 is multiples more. Keep it on-demand and its real cost is whatever your actual usage hours are (a few hours/day might be ~$40-80/year). This is exactly why Sunshine streaming, local LLM, and heavy game servers all live on the *on-demand* rig.
2. **Wake-on-LAN + auto-suspend** on the rig: enable WoL in BIOS, suspend after idle, wake from phone/laptop (or via Sunshine) on demand.
3. **NAS drive hibernation:** enable HDD hibernation in DSM so drives spin down when idle.
4. **GPU idle fix on Linux:** the 3090 Ti can get stuck in a high-power state at idle (~100-115W doing nothing) instead of its normal ~20-30W. Check `nvidia-smi` at idle; persistence mode (`-pm 1`, keeps the driver loaded and the fix stuck), a power limit (`nvidia-smi -pl`), and a modest undervolt (locked clocks + offset, via a systemd service so it survives reboot) keep idle and load down.
5. **Measure it.** You already have **Emporia Energy** on your breaker/circuits — use its per-circuit data to replace these estimates with your real draw (and feed it into HA's Energy dashboard).

---

## 6. Backup, beyond the NAS

RAID is not a backup — it survives a dead drive, not a deletion, ransomware hit, fire, or theft. Target: **3-2-1 — three copies, two media types, one off-site.**

### Tier your data first (the key move)
Don't back up 40TB to the cloud (~$278/month at B2's current ~$6.95/TB). Split it:
- **Tier 1 — irreplaceable (cloud + local).** Immich photos, documents, Obsidian vault, **HA config**, **game-server worlds/saves**, all your compose files/configs. Realistically 1-2TB. **This goes off-site to the cloud** (~$7-14/month at B2 — trivial insurance).
- **Tier 2 — replaceable media (local redundancy only).** Ripped movies/shows/music you could re-acquire. NAS RAID + one cold copy; **don't pay to cloud-store it.** For off-site of this tier, a **rotated external HDD** at your office or a relative's house is the cheap option.

### Tools
- **Synology native (turnkey, start here):** **Hyper Backup** (to B2 / Synology C2 / another Synology / external), **Snapshot Replication** (Btrfs point-in-time — great vs. accidental deletion/ransomware), **Active Backup for Business** (pull backups of your computers, including the Ubuntu box, onto the NAS).
- **Ubuntu/CachyOS -> cloud:** **Restic** (single Go binary, native B2/S3, simple password encryption, biggest community) or **Kopia** (similar + built-in web UI/scheduler).
- **SSH/local targets:** **BorgBackup + Borgmatic** (best compression, fastest restores, YAML scheduling, DB-dump hooks, healthcheck pings) with a cheap SSH storage box.

### Off-site targets (current pricing)
| Target | ~Price | Protocol | Best for |
|---|---|---|---|
| **Backblaze B2** | ~$6.95/TB/month, free-ish egress (free up to 3x stored/mo) | S3 API | Hot cloud copy of Tier 1; native Restic/Kopia |
| **Hetzner Storage Box** | ~$4/TB (tiered) | SSH/SFTP/Borg | Cheapest Borg/rsync target (EU) |
| **rsync.net** | pricier, Borg/restic plans | SSH/SFTP/Borg | Reliable SSH target, US options |
| **Rotated external HDD** | one-time drive cost | physical | Off-site copy of bulky Tier 2 |

> Synology NAS units don't qualify for Backblaze's flat $99/year personal plan (that's for direct-attached drives on a PC/Mac). For the NAS use **B2** (per-TB) or **Synology C2**.

### Don't forget
- **Test a restore** at least once. An untested backup is a hope.
- **Store encryption keys/passphrases off the machine** (password manager + a printed copy).
- **Back up Docker volumes and the CouchDB volume** (if you use LiveSync), and HA's backup archive, not just visible files.

---

## 7. "Set it and forget it" configuration

Goal: rebuildable, self-updating-but-not-recklessly, quiet until something needs you.

### Container management (pick one)
- **Dockge** — lightweight, Compose-focused, dead simple, single-host. Great if your stack lives on the one Ubuntu box.
- **Dockhand** — the 2025/26 breakout. One container that absorbs logs, resource monitoring (history), update tracking with *safe pulls* + rollback, notifications (Apprise: ntfy/Telegram/Discord/email), visual Compose editing + Git sync, and Grype/Trivy vulnerability scanning. Replaces a pile of sidecar tools.
- **Komodo** — Rust, Git-driven (point at a repo, it builds/deploys), multi-server. Best if you manage NAS + Ubuntu + rig as a fleet. Heavier (needs a DB).

**Recommendation:** **Dockhand** for consolidation, or **Dockge** for the simplest. Both beat Portainer now (whose full SSO/RBAC are Business-Edition features — free for up to 3 nodes, paid beyond that).

### Updates — do this deliberately
**Avoid blind auto-updates.** Watchtower's "always pull latest" model is how a set-and-forget box silently breaks at 3am, and the original project was archived (read-only) in Dec 2025 (a community fork, `nicholas-fedor/watchtower`, continues it). Instead: **pin versions** (`immich:v3.0.0`, not `:latest`); use **notify-only** awareness (Dockhand's tracking, or **Diun**); update on *your* schedule with safe-pull + rollback; read release notes for the breaking-change projects (Immich majors especially).

### Monitoring & uptime
- **Beszel** — ultra-light (hub + tiny single-binary Go agents, ~6-23MB RAM each), at-a-glance CPU/RAM/disk/network across all boxes. (Dockhand covers much of this too.)
- **Uptime Kuma** — pings services, alerts on downtime. Point it at Immich, Jellyfin, CWA, HA, Miniflux.
- **ntfy** — self-hosted push to your phone for backups, downtime, update alerts. The notification backbone.

### Remote access
- **Tailscale** — mesh VPN, near-zero config, generous free tier. Install on the NAS, Ubuntu box, rig, laptop, and phone; reach Jellyfin/Immich/CWA/Obsidian/HA remotely with no port-forwarding and nothing exposed. Also your path for **remote Moonlight** and **inviting friends to game servers**.
- *Full control:* self-host **Headscale** or use **Netbird**. Tailscale's hosted control plane is the pragmatic set-and-forget pick.

### Reverse proxy + HTTPS (for services you expose locally)
- **Caddy** — automatic HTTPS with a tiny config. The set-and-forget choice.
- *GUI alternative:* **Nginx Proxy Manager**.

### Config-as-code (makes "rebuild in an hour" true)
- Put **all compose files + configs in Git** — self-hosted **Gitea/Forgejo**, or a private GitHub repo. Disk dies or you migrate hosts -> `git clone` + `docker compose up` and you're back. This habit turns a homelab from fragile to disposable-and-rebuildable.

### Power resilience
- **UPS** on the NAS + Ubuntu box + Dream Wall. DSM reads most consumer UPSes over USB and does a graceful shutdown on battery — important on fiber where brief outages can corrupt a DB mid-write. The Ubuntu box can listen to the NAS's UPS status over the network (NUT).

---

## Suggested rollout (phased)

Do a phase before starting the next; each leaves you better off.

**Phase 1 — Foundation (network, access, safety net)**
1. **Back up your UniFi config**, then build the segmentation: Default(mgmt) / Trusted / IoT / Guest / Work, the firewall rules, mDNS reflector on + IGMP snooping off. (One-way door on the new firewall — back up first. **Start here.**)
2. **Install Tailscale** on the NAS, Mac mini, rig, laptop, and phone.
3. **Lock in backups:** Synology Hyper Backup + Snapshot Replication, plus a Restic/Kopia job for your irreplaceable data -> B2. Test one restore.

**Phase 2 — De-cloud the essentials**
4. **Home Assistant** (HA Green or HAOS VM): add Hue (local), Midea (local via `midea_ac_lan` or an ESPHome dongle), Nest (SDM API). Move smart devices onto the IoT VLAN.
5. **Seedbox pipeline:** sign up for a managed seedbox, install qBittorrent + Sonarr/Radarr/Prowlarr/Bazarr + a sync agent on it, run **Seerr/Jellyseerr** at home, put the seedbox on Tailscale, and point the sync at your NAS library. Then **decommission the NAS dual-LAN/Gluetun setup** and drop the 5 Mbps cap.
6. **Immich** with phone auto-backup; start leaving iCloud Photos.

**Phase 3 — The analogue media stack**
7. **Calibre + Calibre-Web-Automated + KOReader (Kobo) + Syncthing** for reading.
8. **iPod via Rhythmbox/libgpod** + **gPodder** for music/podcasts.
9. **Miniflux** (+ optional Wallabag) for RSS, wired into KOReader's news plugin.
10. **Turn on Obsidian Sync** (paid, official — nothing to host).

**Phase 4 — Glue & polish**
11. Stand up the management layer: **Dockhand** (or Dockge) + **Beszel** + **Uptime Kuma** + **ntfy** + **Caddy**, and add **Pi-hole / AdGuard** for network DNS filtering.
12. Push all compose files + configs to **Git** so the whole thing is rebuildable.

**Phase 5 — Play**
13. **Game servers:** LinuxGSM or Pelican — light games always-on on the Mac mini, heavy games on-demand on the rig, friends in via Tailscale.
14. **Sunshine** on the rig + **Moonlight** clients; confirm Tailscale shows "direct" for remote streaming.
15. **Tune the rig:** Wake-on-LAN, auto-suspend, GPU idle/undervolt — so streaming and heavy servers are on-demand and cheap.

---

## The stack at a glance

| Apple/iOS task | FOSS replacement | Runs on |
|---|---|---|
| iCloud Photos | **Immich** | NAS |
| Apple Music (own files) | **Navidrome** (+ Symfonium/Amperfy) | Ubuntu/NAS |
| iPod sync | **Rhythmbox / libgpod** (Apple firmware) | device |
| Apple Podcasts | **gPodder** (+ optional sync server) | desktop |
| Apple News / RSS | **Miniflux** (or FreshRSS) + Wallabag | Ubuntu |
| Kindle/iBooks | **Calibre + CWA + KOReader (Kobo) + Syncthing** | NAS + device |
| Apple Notes | **Obsidian + Obsidian Sync** (paid, official) | desktop |
| iWork / MS Office | **LibreOffice** (or OnlyOffice/Collabora) | CachyOS |
| Plex / TV | **Plex** (keeping; Jellyfin = FOSS fallback) | NAS |
| Private media acquisition | **Managed seedbox** (qBit + *arr) + **Seerr** | off-site + Mac mini |
| iCloud Drive/Contacts/Calendar | **Proton** or **Nextcloud** or **Syncthing + Baikal** | cloud/NAS |
| Safari | **Firefox / LibreWolf / Zen** + Kagi | CachyOS |
| Siri / smart home (Hue, Nest, Midea) | **Home Assistant** + local voice (Whisper/Piper + Ollama) | HA Green / VM |
| GeForce Now / game streaming | **Sunshine + Moonlight** | rig (host) + clients |
| Hosting game servers | **Pelican** / LinuxGSM | Mac mini / rig |
| Remote access | **Tailscale** | all |
| Network segmentation | **UniFi VLANs + Zone-Based Firewall** | Dream Wall |
| Ad/tracker DNS | **Pi-hole / AdGuard Home** | Ubuntu / HA |
| Container mgmt | **Dockhand** / Dockge / Komodo | Ubuntu |
| Monitoring | **Beszel** + Uptime Kuma + ntfy | Ubuntu |
| Backup | **Restic/Kopia** + Borg + Synology native | NAS + hosts |
| Local LLM | **Ollama** + Open WebUI | CachyOS rig (on-demand) |

Already in your stack and worth keeping: **Kagi** (search), **ProtonMail/VPN/Drive/Calendar/Pass**, and **Plex** (lifetime pass — staying put; Jellyfin is the FOSS fallback only if Plex ever paywalls something you depend on).

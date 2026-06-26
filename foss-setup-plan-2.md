# Going Analogue: A FOSS Computing Setup

A reference build for moving off the Apple/iOS ecosystem onto your own hardware, with as much current open-source tooling as possible. Scoped to what you already run (CachyOS rig, DS920+, Mac mini/Ubuntu, Dream Wall, Hue, Nest, Midea, Plex, Kagi, Proton) and what you're moving toward (iPod Classic, eReader, Immich, Obsidian, Home Assistant, self-hosted RSS, game servers, game streaming).

The FOSS world genuinely moved in the last year. The shifts relevant to you: Immich shipped a stable 2.x line and 3.0 is now in release-candidate (no longer "don't trust it with your only copy", though 3.0's headline workflow/transcoding features are still labeled preview); Plex hiked its lifetime price ($119.99 -> $249.99 in 2025, and **tripling again to $749.99 on July 1, 2026**) and paywalled remote *video* streaming, pushing the hobby toward Jellyfin; Calibre-Web forked into a far better automated version; Rockbox on the iPod Classic got a modern bootloader; a new wave of single-binary homelab tools (Dockhand, Komodo, Beszel) replaced the older sprawl; UniFi moved to a zone-based firewall; and Sunshine + Moonlight matured into a genuinely excellent self-hosted GeForce-Now replacement.

---

## 0. The host decision that drives everything: 24/7 vs. on-demand

Before any app choice, settle this. It's the difference between a ~$160/year power bill and a ~$700+/year one, and it's *also* what makes the whole thing "set and forget."

**Always-on tier (the quiet workhorses):**
- **DS920+ NAS** — storage, plus the home for most lightweight always-on services. Its Celeron J4125 has Intel Quick Sync, so it can even handle Jellyfin transcoding for a stream or two. **It ships with 4GB; the heavy-offload plan below needs a RAM upgrade to ~20GB first — a Crucial `CT16G4SFD8266` 16GB stick (~$40-110 depending on seller — verify it's brand-new and dual-rank/2Rx8; decided, future purchase, see capacity note). Until then keep the NAS to Immich + Plex + CWA.**
- **Mac mini (Late 2014, Macmini7,1) -> Ubuntu Server** — your Docker host for anything you don't want on the NAS's locked-down DSM. True idle is ~6-10W; figure ~10-15W running the container stack. It's a **dual-core i5-4278U with 8GB of RAM soldered to the board — non-upgradeable, ever** — so treat it as a fixed *light* host: the web/management stack only (see capacity note).

**On-demand tier (powerful but expensive to idle):**
- **CachyOS rig (3090 Ti / 12700K, 64 GB RAM)** — your *local-LLM, game-streaming, and heavy-game-server box*, not a 24/7 server. Wake it for Gemma/Qwen/DeepSeek inference, a Sunshine streaming session, or a beefy game server; let it sleep otherwise. Running it 24/7 just to host services would dwarf every other cost on this page.

### What runs where

| Service | Host | Why |
|---|---|---|
| File storage, Immich, Plex, Calibre-Web-Automated, backups | DS920+ | Always on, low power, Quick Sync transcode |
| **Heavy/always-on offload: Paperless-ngx, Dependency-Track, Frigate, Tdarr (server)** | DS920+ | Co-located with the data/media they touch; keeps RAM-hungry Java + live video detection off the small Mac mini (see capacity note below) |
| Docker stack: Seerr (request portal), Miniflux, Navidrome, Pinchflat, Wallabag, Mealie, Tautulli/Kometa/Maintainerr, Homepage, Caddy, AdGuard+Unbound, monitoring (Beszel/Uptime-Kuma/ntfy), LiteLLM (small model), Forgejo | Mac mini (Ubuntu) | Flexible Docker host, ~12W, no DSM constraints — the *light* always-on services |
| qBittorrent + Sonarr/Radarr/Prowlarr/Bazarr + sync agent | Managed seedbox — **Bytesized "Stream +3"** (3000 GB, off-site) | Keeps all P2P off your home network; ISP never sees a swarm (see Media acquisition) |
| Home Assistant | **HA Green (purchased)** | Isolated, always-on, low power (see Smart Home) |
| One light game server (e.g. a single Minecraft or Terraria) | Mac mini (Ubuntu) | Always-on for friends — but the 8GB box only has room for *one small* server alongside the stack; all other/heavier servers run on the rig on-demand (see capacity note) |
| Local LLM (Ollama), Open WebUI, Sunshine streaming, heavy game servers, gaming | CachyOS rig | On-demand only; Wake-on-LAN + auto-suspend |
| Routing, firewall, VLANs, WiFi | Dream Wall | Already always-on |

> If you'd rather consolidate, the Mac mini's services could also live on the NAS via Container Manager. But keeping a separate Docker host means a NAS firmware update or a runaway photo-index job never takes your containers down with it. Worth the extra ~$20/year.

> **Capacity note — both always-on boxes are RAM-constrained; size for it (and the NAS needs a RAM upgrade first).** The Mac mini is a **Late-2014 Macmini7,1 (dual-core i5-4278U) with 8GB of RAM soldered to the board — it cannot be upgraded, ever.** Treat it as a fixed *light* host: the Docker web/management stack fits ~8GB with little to spare, so **no heavy game servers, no real local LLM model (a tiny ≤1B at most), and no HA VM live here** — those belong on the on-demand rig or an HA Green. The heavy hitters from Sections 2/8 — two Java apps (**Dependency-Track**'s apiserver wants ~4GB+ — official 2-4.5GB min — plus Paperless's **Tika**), **Frigate**'s live object detection, **Tdarr**, and the database pile (5× Postgres + Wallabag's MariaDB + two Redis) — would thrash or OOM an 8GB box, **so they move to the NAS** next to the data they touch: Frigate on the NAS Quick Sync iGPU (or keep it on the Mac mini *if* you add a ~$60 Coral), Tdarr server only with transcodes on the rig node, and Dependency-Track where there's RAM headroom.
>
> **But that headroom doesn't exist yet — it requires a NAS RAM upgrade.** The DS920+ ships with **4GB**, and at 4GB it already swaps under just Immich (with ML) + Plex; it cannot also take the offloads. Intel officially caps the J4125 at 8GB, but the DS920+ is the well-documented exception that runs **20GB** with a single 16GB dual-rank SO-DIMM in practice (it works, but it's beyond Intel's spec and Synology's support). **Decided (future purchase):** Crucial **`CT16G4SFD8266`** — 16GB DDR4-2666 PC4-21300, dual-rank 2Rx8, CL19, **~$40-110 depending on seller** (verify it's brand-new and dual-rank 2Rx8; the exact stick locked in, buying it later). It yields 4GB + 16GB = **20GB that DSM recognizes and uses** (unofficial → voids Synology support, but proven reliable). **Until that stick is installed, limp by:** run only **Immich (ML concurrency capped + indexing scheduled off-peak) + Plex + Calibre-Web-Automated** on the NAS, and **defer Paperless / Dependency-Track / Frigate / Tdarr** — stand them up on the rig on-demand, or hold them — rather than landing the offloads on a 4GB NAS. **Measure** with Section 5's Emporia + HA Energy and `free -m`/DSM resource monitor. The point isn't a fixed assignment — it's *don't put both Java apps + live video + six DBs on the small Mac mini, and don't land them on the NAS until it's at 20GB.*

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
| Trusted | Trusted | PCs, NAS, Mac mini, phones, consoles, **Home Assistant (HA Green)**, **Sunshine host + Moonlight clients** |
| IoT | IoT (untrusted) | Hue bridge, Nest, Midea AC/dehumidifier, smart TVs / streaming sticks |
| Cameras (optional) | Cameras (untrusted) | Any IP cameras — most locked down, no internet |
| Work | Work | Nava work laptop — internet only, no access to other VLANs (its own isolated zone) |
| Guest | Hotspot | Visitors — isolated, client isolation on |

Home Assistant lives on **Trusted**, not IoT. **Prefer keeping HA single-homed** and putting any Matter devices on HA's own VLAN; dual-homing HA across two NICs does work, but it widens HA's exposure (a foothold there now straddles both segments), so single-homed is the cleaner default. It reaches IoT devices because Trusted -> IoT is allowed.

### Firewall rules that actually isolate (UniFi Network 9.x = Zone-Based Firewall)
**Back up your config first — migrating to the Zone-Based Firewall is a one-way door**, and it can sever VPNs, mDNS, and inter-VLAN flows if you rush it.

The model: **allow Trusted -> Untrusted (return traffic is automatic — these firewalls are stateful, so you do not need an "allow established/related" rule); block Untrusted -> Trusted; add narrow pinholes for the few flows that must cross.** Concretely for the IoT VLAN:
- Allow IoT -> internet, and allow IoT -> gateway for DNS 53, DHCP 67, NTP 123. **Never blanket-block the gateway** or devices can't get an IP, resolve names, or sync time.
- Block IoT -> RFC1918 (10/8, 172.16/12, 192.168/16) so it can't reach any of your other subnets. (This is the legacy-rule equivalent of the zone-based "block IoT -> all internal zones" rule the config files use — same outcome, expressed in the old per-subnet paradigm.)
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
- **Encrypt the DNS that leaves your house.** Filtering alone still forwards plaintext queries your ISP can read. Either point Pi-hole/AdGuard at **Unbound** as a local **recursive resolver with DNSSEC** (no upstream sees your queries at all), or at minimum enable **DoT/DoH** to Quad9/Cloudflare. Then **stop clients bypassing it:** a firewall rule that redirects (NAT) outbound port 53 to your resolver and **blocks known DoH endpoints** keeps every device on the filtered, encrypted path. Run a **second resolver** (e.g. AdGuard on the NAS) as the DHCP secondary so one box dying doesn't take DNS down.
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
- *Your mirrorless camera — yes, this works well.* Immich stores and displays RAW formats (ARW/CR3/NEF/RAF/DNG) and reads the EXIF, so camera shots land on the right date/place alongside your phone photos and get faces/objects indexed like everything else. The one difference from the phone: there's **no auto-backup for a camera** — the mobile app only backs up the phone's own roll. So you import from the SD card. Easiest paths: the **immich-go** CLI (`upload from-folder`, with `--manage-raw-jpeg` to stack RAW+JPEG pairs into one asset) pointed at the card after you copy it off, or **pbak** — a photographer's wrapper around immich-go that does the whole **SD -> SSD -> Immich** flow with EXIF date-sorting, SHA-256 dedup, integrity checks, and optional Lightroom-album sync. For a true plug-and-forget habit, copy the card into a watched staging folder on the NAS and run immich-go (or `immich upload --watch`) on a schedule so new shots ingest themselves.

### Music — library + streaming (Apple Music / iTunes library)
- **Navidrome** — self-hosted music server (Subsonic API). Stream your own collection without a subscription. Mobile clients: **Symfonium** (Android, excellent), **play:Sub** / **Amperfy** (iOS); desktop: **Feishin** or **Supersonic**.
- *Getting music in:* rips of your own CDs drop straight into the library; for **automated acquisition** (the "music half" of the download stack) see Media acquisition below — **Lidarr** is the music *arr, and it feeds this same Navidrome library.
- Separate from getting music onto the iPod (next).

### iPod Classic
**Decision: keep Apple firmware + libgpod tools.** Sync from Linux with **Rhythmbox** (simplest, built-in iPod support), with **gtkpod** (power-user, aging) or **Clementine** as alternatives. This keeps the device stock — car/USB-controller compatibility intact — and you manage the library the familiar way. Set a static library workflow and it's reliable.
- *The plug-in experience (what you asked):* yes. Plug the iPod into the CachyOS rig and **Rhythmbox auto-detects it like iTunes did** — click sync (or drag tracks) and it writes to the device, car/USB controls intact. **Podcasts ride along on the same iPod:** the cleanest set-and-forget path is to have gPodder (next) download episodes into a folder that's part of Rhythmbox's library, so a single plug-in-and-sync pushes both new music *and* new podcast episodes onto the device in one operation. (gPodder can also sync straight to an iPod over libgpod, but funneling everything through Rhythmbox keeps a single tool writing Apple's database, which is more reliable.)
- *Gotcha:* libgpod-based sync writes Apple's iPod database; occasionally a sync needs a re-init if the DB gets confused. Keep your music master library on the NAS (Navidrome's library) so the iPod is always a reproducible copy.
- *If you ever want to drop the database hassle entirely:* **Rockbox** turns the iPod into a plain drag-and-drop USB drive (FLAC/Opus, custom EQ) via a modern bootloader (installed using the freemyipod project's tooling) — but it loses Apple's car/USB-control integration, so it's only worth it if that compatibility stops mattering.

### Podcasts (Apple Podcasts)
- **gPodder** — maintained desktop podcatcher (RSS / YouTube / SoundCloud), batch-download, auto-cleanup (development is ongoing, though the last stable release was Dec 2024). On the chosen Apple-firmware + Rhythmbox path (see iPod Classic above): point gPodder at a download folder that's part of Rhythmbox's library, so a single plug-in-and-sync writes new podcast episodes to the iPod alongside your music.
- *Optional sync server* (if you also listen on a phone and want play-position synced): self-host **oPodSync**, **goPodder**, or **Sintoniza**. Skip if the iPod is your only podcast device.

### YouTube & web video — download / archive
Keep the creators you care about locally (and offline-able), instead of relying on the algorithm.
- **Pinchflat (recommended)** — "Sonarr for YouTube": **one self-contained Docker container** (no Redis/Elasticsearch sidecars) where you add channels/playlists as *sources* and it periodically pulls new uploads, names them to a template, and writes NFO/poster metadata for **Plex/Jellyfin/Kodi**. Supports **SponsorBlock**, and can expose a channel as a **podcast RSS feed** — which means a downloaded channel can flow into gPodder and onto the iPod just like a podcast. Built on **yt-dlp**, low resource use, set-and-forget. Host on the NAS or Mac mini and point its output at a Plex library (a dedicated "YouTube" library, or mixed into TV).
- *Heavier archive with search:* **Tube Archivist** — a full web UI to browse/search your archive (including transcripts and comments) with an in-app player, but it needs three containers (app + Redis + Elasticsearch). Pick it only if in-app browsing/search matters more than a lean stack.
- *Ad-hoc grabs:* **MeTube** — a tiny web UI over yt-dlp for one-off downloads (paste a URL, get a file; also handles many non-YouTube sites). Or just run **yt-dlp** straight from the CachyOS terminal — everything above is yt-dlp underneath.

### News / RSS (Apple News, algorithmic feeds)
- **Miniflux (recommended)** — minimalist, single static Go binary (tiny footprint, typically low tens of MB RAM), PostgreSQL backend (Postgres is required — no SQLite/MySQL), deliberately distraction-free, strips tracking pixels, full-text fetch, and speaks the Fever + Google Reader APIs so native apps (NetNewsWire, Reeder, NewsFlash, Readrops) sync to it. The spartan UI is a feature for "going analogue"; lowest-maintenance once running.
- **FreshRSS** — PHP, more features and an extension ecosystem (YouTube-channel-to-RSS, podcast feeds, scraping bridges), runs as a single container with SQLite (no separate DB), larger community. Pick this if you want extensions/customization.
- *Tie-ins:* pair with **Wallabag** (self-hosted read-it-later, replaces Pocket); both Miniflux/FreshRSS and Wallabag feed into **KOReader's news/RSS and Wallabag plugins**, so you can read feeds and saved articles on the eReader.

### Reading / eReader (Kindle + iBooks)
- **Calibre** (desktop) — library master and conversion engine.
- **Calibre-Web-Automated (CWA)** — the actively-developed fork. Auto-ingest folder, an EPUB-fixer that cleans files so Send-to-Kindle stops rejecting them, metadata/cover enforcement written into the files, OPDS server, native Kobo sync, and **built-in zero-config KOReader progress sync**. One Docker container on the NAS.
- **KOReader** — open reader for the device. Runs on Kobo, jailbroken Kindle, PocketBook, Boox, reMarkable, Android. Stores progress in accessible files; OPDS + Calibre wireless plugin.
- **Syncthing** — peer-to-peer sync of books and progress files. No cloud.

Device notes: **Kobo** = smoothest (native CWA sync + optional KOReader). **Kindle** = jailbreak + KOReader (worth it — Amazon removed "Download & transfer via USB" in Feb 2025, and, per Amazon, ended Kindle Store access for devices released in 2012 or earlier on May 20, 2026; those devices can't buy/borrow/download new books and become unrecoverable only if reset or deregistered). **Buying new?** Kobo / PocketBook / Boox are friendliest.

### Notes (Apple Notes — already on Obsidian)
**Decision: paid Obsidian Sync.** Official, end-to-end encrypted, zero setup, nothing to self-host or maintain — the right call given the set-and-forget priority. Your notes remain plain local Markdown, so you still own the data and it's still captured by Section 6's backup. (If you ever want to drop the subscription, self-hosted LiveSync + CouchDB or plain Syncthing are free alternatives — but there's no reason to complicate this now.)

### Office (Pages/Numbers/Keynote, MS Office)
- **LibreOffice (26.2)** — mature desktop-first FOSS suite (year.month versioning; 26.2 is the current line as of mid-2026, after 25.8 reached end-of-life in June 2026). For solo, offline, local work on CachyOS, the obvious baseline.
- *Better MS fidelity:* **OnlyOffice Desktop** (OOXML-native). (Open-core; the old 20-concurrent-connection community limit on the server edition was removed in Docs 9.4, May 2026; had a 2026 falling-out with Nextcloud after Nextcloud/IONOS forked it into "Euro-Office.")
- *Browser-based collaboration:* **Collabora Online** (LibreOffice-based, lighter to self-host) with Nextcloud.

**Recommendation:** LibreOffice desktop. Don't self-host an office server unless you want in-browser collaboration.

### Video / media server (Plex — staying)
**Decision: keep Plex** (grandfathered lifetime pass). Nothing changes here — your library stays on the NAS and Plex serves it, and your existing Lifetime Pass is unaffected by the upcoming price change (the new-purchase lifetime price triples to **$749.99 on July 1, 2026**, up from $249.99 — so your grandfathered pass is now worth even more). Note the 2025 remote-streaming paywall applies to **video** only; remote music/photo streaming stays free. (Jellyfin remains the FOSS fallback if Plex ever paywalls something you depend on; you can stand it up alongside Plex in ~30 min pointed at the same folders, no re-organizing. But no action needed now.)

### Media acquisition — private, off-site (replaces the dual-LAN VPN/Gluetun setup)
**Decision: a managed seedbox runs the whole download stack off-site; finished media syncs to the NAS for Plex.** This retires the home VPN routing entirely.

Why this is the answer to "never visible to my ISP" *and* the network crashes: the old setup torrented on the NAS behind a home VPN, and thousands of simultaneous peer connections (DHT/uTP especially) exhausted the connection-state (conntrack) table until you rebooted — the classic torrent-kills-the-network failure. (VPN encapsulation adds its own MTU/fragmentation headaches on top, a separate reliability drag — though note a full tunnel can actually *reduce* the router's tracked-connection count by collapsing all peers into one encrypted flow.) The 5 Mbps cap was a band-aid. A seedbox eliminates the root cause: **the P2P happens on a rented server, so your home network only ever does one tidy encrypted download from a datacenter.** Your ISP never sees a swarm (or even an always-on VPN tunnel) — just a normal-looking transfer — which is the purest form of "invisible to my ISP."

**The pipeline (fully automated: request -> auto-appears in Plex):**
1. **Jellyseerr/Seerr** (request portal) — runs at home on the Mac mini; household members request a title from their phone or Apple TV. (Use **Seerr**, the 2026 unified successor of Overseerr + Jellyseerr — image `ghcr.io/seerr-team/seerr`. Overseerr's development had stalled since ~2023 and its repo was finally archived (read-only) on Feb 15, 2026 with an in-app migration notice pointing to Seerr. Jellyseerr is the fork most seedbox app stores still ship and is fine too — it's literally the codebase that became Seerr. All support Plex.)
2. **Sonarr / Radarr / Lidarr** (on the seedbox) — receive the request, search via **Prowlarr** indexers, hand off to **qBittorrent** (on the seedbox). *(Sonarr = TV, Radarr = movies, **Lidarr = music** — same model, same seedbox.)*
3. **qBittorrent** downloads at full seedbox speed, then Sonarr/Radarr rename/organize; **Bazarr** grabs subtitles.
4. **Sync agent** (Syncthing or rclone, on the seedbox) pushes the finished, named files into the NAS library folders.
5. **Plex** (home) imports them; Seerr sees they're available and notifies the requester.

**How the home and seedbox talk:** put the seedbox on your **Tailscale** tailnet, so Seerr (home) reaches Sonarr/Radarr (seedbox) and the sync runs privately, with nothing exposed to the internet. Use SFTP/Syncthing (encrypted) for the file transfer — never plain FTP.

**Yes, it includes music — with one twist.** **Lidarr** slots into the exact same pipeline for albums, and **Navidrome** then serves whatever it grabs (alongside your CD rips). The twist: torrent trackers are thin for music compared to TV/movies, so the community-standard addition is **Soulseek** via **slskd** (a self-hosted Soulseek daemon) glued to Lidarr by **Soularr** — Soularr reads Lidarr's "wanted" list, finds the albums on Soulseek, downloads them, and tells Lidarr to import, fully hands-off (it even keeps a deny-list so failed imports don't pile up). Because Soulseek is also P2P, **run slskd + Soularr on the seedbox**, not at home — the same logic that keeps every swarm off your network. Net result: requested albums land in Navidrome's library (and become the reproducible master that syncs to the iPod) the same way movies land in Plex. *(Podcasts and YouTube channels are handled separately — gPodder and Pinchflat via RSS — not the \*arr stack.)*

**Provider — decided: [Bytesized "Stream +3"](https://bytesized-hosting.com)** (their *New Appbox* tier) — **3000 GB HDD storage, a 6-10 TB/month upload cap (verify the exact Stream +3 SKU at checkout), €16/mo (~$18)**, on a 10 Gbit network in Europe (LUX/FR/NL) with the slickest one-click panel (qBittorrent + the full *arr suite + Seerr/Bazarr/Tautulli + rclone/Syncthing, 67+ apps). It won on ease-of-setup and the breadth of the one-click catalog. *(Runners-up were Seedboxes.cc and DediSeedbox for genuinely uncapped upload, and Whatbox for SSH freedom/reputation — see `configs/seedbox/provider-comparison.md`.)*
- **The upload cap, addressed:** earlier drafts said "prioritize *unlimited* upload," and Stream +3 is *capped* — at **6-10 TB/month depending on the exact SKU (verify at checkout)**, still a generous ceiling, well above what normal private-tracker seeding burns, so it's a non-issue for typical use. If you ever seed *very* hard for ratio and approach the cap in a month, qBittorrent's per-torrent share-ratio / seeding-time limits keep you under it; only a ratio-grinder would need to move up a tier or to an uncapped provider. The cap is **upload only** — downloads are unmetered.
- **The 3000 GB storage, addressed:** the seedbox is a *working + seeding buffer*, not your library — finished files sync to the NAS (below) and Plex serves from there. To stay inside 3 TB, the sync agent **copies** completed media home (never the seeding source), and you let qBittorrent age torrents out (ratio/seed-time rules + auto-delete on completion of seeding goals) so the box self-prunes. 3 TB is plenty of active-seeding headroom for a household; if you hoard a huge seeding set for ratio you can add Bytesized's 6¢/10 GB add-on storage rather than jumping plans.

**Decommission the old setup:** remove qBittorrent/Gluetun from the NAS, undo the dual-LAN policy routing, and drop the 5 Mbps throttle. The second NAS LAN port is freed up (use it for link aggregation/failover, or leave it). If you ever torrent at home again, the fix for the crashes is simply capping qBittorrent's global max connections (~200) and per-torrent peers — but with the seedbox you won't need to.

### Media companion layer (the polish around Plex + the *arrs)
The acquisition stack above gets files onto the NAS; this layer makes the library *good*, *observable*, and *self-tidying*. Most run as one small container each.
- **Tautulli (recommended)** — Plex's missing analytics: play history, who's watching/transcoding right now, per-user stats, "recently added" and watch notifications, and transcode-abuse spotting. The de-facto Plex companion. *Host: Mac mini.*
- **Recyclarr** — syncs **TRaSH Guides** custom formats / quality profiles / scoring into Sonarr/Radarr on a cron, so the *arrs grab *good* releases instead of mislabeled or bloated ones. A tiny CLI, perfectly set-and-forget. *Host: the seedbox (next to the *arrs).*
- **Unpackerr** — auto-extracts RAR'd releases that Sonarr/Radarr otherwise silently fail to import. Optional on a private-tracker stack (RAR'd releases are uncommon there), more useful with Usenet or public trackers. *Host: the seedbox.*
- **Kometa** (formerly Plex Meta Manager) — builds collections, resolution/HDR overlay badges, posters, and curated playlists, turning a folder dump into a "produced"-looking Plex. *Host: Mac mini.*
- **Tdarr** *(or **FileFlows**)* — pre-transcodes the library to a direct-play-friendly codec set so the NAS's J4125 Quick Sync isn't asked to live-transcode multiple 4K/HDR streams it can't sustain. Run the heavy transcodes on the **CachyOS rig** (NVENC) on-demand and let the NAS just serve. *Server on the **NAS** (light, and next to the media library it scans); the heavy transcode **node** runs on the rig.*
- **Maintainerr** — rule-based library pruning (e.g. "unwatched 90 days + not in a collection -> delete with a grace period"), cleaning across Plex + the *arrs + Seerr. The "anti-Seerr" that keeps Tier-2 storage from growing unbounded — directly serves the tiering goal in Section 6. *Host: Mac mini.*
- *Niche / by taste:* **Komga** or **Kavita** (comics/manga; Kavita also does ebooks) if that's a library you want; **beets** + **MusicBrainz Picard** for clean music tags once Lidarr is feeding Navidrome. (**YouTube archiving is already covered by Pinchflat above.**)
- *Note — book automation:* **Readarr was retired (archived) in June 2025**, so there's no maintained "monitor an author, auto-grab new releases" *arr. CWA still covers organizing/serving ebooks; if you want *acquisition* automation later, **Bindery** or **LazyLibrarian** are the current community picks.

### Files, Contacts, Calendar (iCloud Drive / Contacts / Calendar)
The gap people forget when leaving Apple. Three approaches:
- **One hub — Nextcloud.** Files (sync clients + WebDAV), Contacts (CardDAV), Calendar (CalDAV), optional Office/photos. Closest single-app iCloud replacement; heavier to run.
- **Discrete tools (lighter).** **Syncthing** for files + **Baikal** or **Radicale** as a tiny CalDAV/CardDAV server.
- **Lean on Proton (least effort).** You already pay for it — **Proton Drive**, **Proton Calendar**, **Proton Pass** cover much of this with zero hosting.

**Recommendation:** for minimal moving parts, use Proton for calendar/contacts/drive and Syncthing for the folders you want truly local. Stand up Nextcloud only if you want the single unified hub.

### Documents — the paperless filing cabinet (the iCloud thing everyone forgets)
- **Paperless-ngx** — scan or drop in bills, statements, manuals, warranties, and tax docs; it **OCRs** every page, auto-tags and classifies, and makes the whole pile **full-text searchable**. This is the document half of leaving Apple that nothing else here covers (Immich = photos, Obsidian = notes). Feed it from a watched "consume" folder (drag a PDF in, or point a scanner/phone-scan app at it). Five containers: webserver + Postgres + Redis + **Gotenberg** (Chromium) + **Tika** (Java). *Host on the **NAS** — its data is **Tier 1** (irreplaceable, rides the Section 6 cloud backup) and lives on the NAS anyway, and this keeps the Tika/Gotenberg weight off the small Mac mini (see Section 0's capacity note).*

### Passwords (Bitwarden — keep what you have)
**Decision: stay on Bitwarden.** It's open-source, audited (Cure53), zero-knowledge, has great iOS/browser autofill, stores TOTP, and — unlike Proton Pass — can be **self-hosted** later if you want. No reason to switch to Proton Pass (its edges — encrypted metadata, hide-my-email aliases — are minor and migration is one-way friction for little gain). Bitwarden is where the **backup encryption keys, the HA backup key, and the SOPS/age key** all live (with a printed copy off-machine), per Sections 3/6/8.
- *Optional self-host:* **Vaultwarden** (lightweight Bitwarden-compatible server, ~256 MB RAM) if you'd rather own the vault outright. Lateral move — only do it if self-hosting the vault is itself the goal; back it up as Tier 1.

### Recipes (no Apple equivalent, but a household staple)
- **Mealie** — self-hosted recipe manager: import a recipe from any URL, meal-plan, and generate shopping lists, with a clean mobile-friendly PWA. Lighter and more modern than the alternative **Tandoor** (which is more powerful at meal-planning but heavier). Nothing else in this build is a recipe app, so there's no collision. *Host on the Mac mini.*

### Browser & the rest you already have
- **Browser (Safari -> ):** on CachyOS, **Firefox**, **LibreWolf** (hardened), or **Zen** (Firefox-based, polished). Set **Kagi** as default search.
- Keep **Kagi** (search) and **ProtonMail / VPN / Drive / Calendar / Pass**. Note: Proton VPN is for private egress; Tailscale (Section 7) is a *different* tool for reaching your own services — you'll want both.

---

## 3. Smart home: Home Assistant

Home Assistant (HA) is the hub, and a privacy win in itself: it pulls cloud-tethered devices into local control where possible, so your lights and climate keep working even when Google's or Midea's servers don't.

### How to run it (set-and-forget)
**Decision: HA Green — purchased.** The dedicated appliance was the right call for the set-and-forget priority: plug-and-play, ~2-3W, isolated, auto-updates, full add-on ("Apps") support — it sits in the rack and you never think about it. (For the record, the alternative was **HAOS in a KVM/libvirt VM on the Ubuntu box** — no new hardware, same full Supervisor + add-ons — but the Green wins on isolation and zero-fuss, and it keeps an always-on smart-home hub off the small 8GB Mac mini.)

Whichever you run, **never run HA on an SD card** (constant DB writes kill them — the Green uses eMMC, so you're fine) and avoid HA in plain Docker (you lose the add-on store + Supervisor). Back up to the NAS and **save the backup encryption key in your password manager** (you can't restore without it).

### Your devices
- **Hue -> native, local.** HA's Hue integration talks to your Hue Bridge over the LAN — no cloud, rock solid, instant. Keep the bridge.
- **Nest -> works, but the fiddly one.** "Works with Nest" is gone; HA uses Google's Smart Device Management (SDM) API, which needs a Google Cloud project, the Device Access Console (one-time $5 fee), and OAuth. It works (thermostat control + sensors) but routes through Google's cloud (not local) and is the most involved of your three. Matter support for Nest *thermostats* has improved (the 4th-gen Nest Learning Thermostat ships with native Matter), but Matter thermostat control in HA can still be feature-limited/quirky, so SDM remains the most complete path today. If local control becomes a priority, a Matter or Zigbee thermostat is the cleaner long-term swap — but that's hardware, not now.
- **Midea AC + dehumidifier -> local, with a one-time handshake.** Use the **`midea_ac_lan`** HACS integration (actively maintained; also handles dehumidifiers) or **`midea-air-appliances-lan`**. They control units over the LAN; V3-protocol devices need a single connection to Midea's cloud to fetch a token/key, then run fully local. **Back up the per-device `.json` config files** — Midea has been closing its cloud token APIs, which can block *adding new* devices later (already-added devices keep working).
  - **Fully cloud-free option (recommended for privacy):** replace the OEM WiFi dongle with an **ESPHome-flashable dongle** (e.g., SLWF-01Pro, ~$13) — severs the unit from Midea's cloud and gives local ESPHome/MQTT control. Great fit since you're hands-on; with that done you can block those devices from the internet on the IoT VLAN.
  - Caveat: some Midea units built 2021+ use the Tuya platform — those use a LocalTuya integration, not the Midea ones. Check your model.

### Cameras — bring your UniFi feeds into HA (and optionally Frigate)
You already have UniFi Protect cameras and view them on the Dream Wall. Two upgrades, in order of effort:
- **HA native UniFi Protect integration (do this — easy win).** Fully local, no subscription; it pulls your cameras' live streams **and** UniFi's own motion/smart-detection events into HA as entities (needs a Protect **API key** as of HA 2025.8, and RTSP enabled per camera: *Protect -> Devices -> Settings -> Share Livestream*). The payoff is **automation**: "person detected at the door after dark -> hall light on + phone notification," camera tiles on HA dashboards, and recordings stay on the UniFi NVR. Nothing leaves your network.
- **Frigate (optional — only if you want better AI).** Frigate ingests the same RTSP streams and adds *local* object detection UniFi doesn't: **custom detection zones, package/animal/face detection**, and far better notification snapshots/clips. It needs compute — a **Coral TPU (~$60)** or an **Intel Quick Sync iGPU (OpenVINO)** — and YAML config. *Host on the **NAS**, using its Quick Sync iGPU for detection (no extra hardware) and writing clips straight to NAS storage; alternatively keep it on the Mac mini **with a Coral** so detection runs on the TPU instead of pegging that box's CPU (see Section 0's capacity note — don't run iGPU-less detection on the Mac mini).* Worth it only if UniFi's built-in person/vehicle detection isn't enough for the automations you want; otherwise the native integration alone is plenty. *(If you ever want those cameras in Apple Home / HomeKit Secure Video, **Scrypted** is the bridge.)* Keep cameras on the locked-down **Cameras VLAN** (Section 1); HA on Trusted reaches them via the allow rule.

### Local sensors — the Zigbee backbone (what makes it actually "smart")
Hue/Nest/Midea are all WiFi/cloud-ish appliances. The cheap **local** sensors that drive real automations (motion, door/window contact, temperature/humidity, water-leak, buttons) speak **Zigbee** — so add a radio and a broker:
- **Coordinator:** one USB Zigbee stick — **Sonoff Zigbee 3.0 Dongle Plus-E** (~$20) or the official **Home Assistant Connect ZBT-2**. Plug it into the HA host (use a short USB-2 extension to dodge USB-3 interference).
- **Zigbee2MQTT (recommended) or ZHA.** ZHA is the zero-extra-service built-in path; **Zigbee2MQTT** supports more devices and exposes everything over MQTT (handy once you add ESPHome/Midea-dongle devices). Either runs as an HA add-on.
- **Mosquitto** — the MQTT broker. Required for Zigbee2MQTT *and* for the ESPHome Midea dongle, so stand it up once as the shared message bus (HA add-on).
- **Mesh tip:** every mains-powered Zigbee device (smart plug) is also a router — aim for 5-7 spread around the house, pair devices close to the coordinator then move them, and **avoid Aqara-branded hubs** if you want to mix brands. See the **Cheap local sensor shopping list** section for grounded picks + prices.
- *(Z-Wave is the optional second radio if you adopt Z-Wave-only devices; Zigbee covers everything in the shopping list.)*

### Presence detection — automations that follow you
- **HA Companion app** (iOS/Android) gives free **device-tracker presence** (home/away) plus actionable notifications — install it on every phone. This drives the "arriving/leaving" automations.
- For **room-level** presence (lights that follow you between rooms), add **mmWave** occupancy sensors or **Bermuda** (BLE trilateration using ESPHome Bluetooth-proxy nodes — often a few cheap ESP32s). This is the layer that makes the whole system feel intelligent rather than scheduled.

### Keep your iPhones working — HomeKit / Matter bridge
You're de-Appling the *backend*, but the household keeps iPhones. **HA's HomeKit Bridge** (built-in integration) exposes HA entities to **Apple Home**, so everyone keeps Siri and the Home app — shared access, familiar UI — while HA does the real work underneath. (`home-assistant-matter-hub` is the Matter-based alternative.) Expose a curated set of entities, not everything.

### Tie-ins worth doing
- **Local voice (replaces Siri/Alexa):** HA's Assist pipeline + the Whisper/Piper add-ons gives local speech, and you can point its conversation agent at **Ollama on your rig** for a fully local LLM assistant.
  - **The on-demand-rig problem + fix (LiteLLM fallback):** the rig sleeps, so a conversation agent pointed straight at it goes dead whenever it's suspended. Put **LiteLLM** (a tiny OpenAI-compatible gateway) in front instead: HA (and Open WebUI, scripts, etc.) all target one stable URL, and LiteLLM **routes to the rig's big model when it's awake and automatically falls back** — on timeout/5xx — to a **small always-on model** (a ≤1B model via Ollama/llama.cpp on the Mac mini, CPU-only is fine) or a cloud API. Net result: "turn off the lights" and quick questions are instant and always work; heavy reasoning uses the rig when it's up. (Optionally have HA send a Wake-on-LAN packet to spin the rig up for a genuinely heavy query.)
- **Node-RED — visual automations:** install the HA **Node-RED add-on** once HA automations outgrow the built-in editor (complex occupancy/time/state-machine logic, presence flows). Optional but the standard escalation path; flows live in `/config` and are captured by the HA backup.
- **HA backups — concrete method:** Settings -> System -> **Backups** -> schedule full backups (e.g. daily, keep 7) to the **NAS** via the **Samba/NFS backup location** (or the Google Drive Backup add-on), and **save the backup encryption key in Bitwarden** — you cannot restore without it. Also separately back up the Midea `.json` token files (above). See Section 8 for putting `/config` YAML under Git too.
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

**Where to run them:** the 8GB Mac mini is already carrying the always-on web stack, so it hosts **at most one light always-on server** — e.g. a single **Minecraft (Paper)** or **Terraria** world — so friends can hop on anytime without OOM-ing the box. **Everything else runs on-demand on the CachyOS rig:** the other co-op titles (Valheim, Factorio, Project Zomboid, Core Keeper) *and* the heavier servers (Palworld, ARK, modded packs) — bring the rig up for game night (Wake-on-LAN) and let it sleep otherwise. (This matches Section 0's capacity note — don't stack multiple game servers on the small Mac mini.)

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

#### The headless-display gotcha (and the fix you already have)
Sunshine can only capture an **active** display at the client's resolution/refresh — with no monitor attached (or the monitor asleep), there's nothing to encode, which is the single most common headless-streaming failure. Three options, easiest first:
- **Dummy HDMI plug (you own one) — simplest, most reliable.** Plug it in; the GPU sees a "monitor" and Sunshine captures it. Set the desktop to the plug at your target resolution. Zero software.
- **Software virtual display on CachyOS (no dongle).** Your instinct is right that a Sunshine fork handles this on Linux. Stock **Apollo's** built-in virtual display is Windows-only, but two Linux solutions are CachyOS-tested: **`MrOz59/Apollo-Linux`** (an Apollo fork that adds **EVDI**-based virtual displays — `evdi-dkms`, auto-matches the client's resolution/HDR, works on NVIDIA), and **`frostplexx/sunshine_virt_display`** (a systemd daemon that creates an EDID-override virtual display on connect). Either gives a true headless, resolution-matching session — handy since the rig wakes on demand with no monitor on.
- **Audio:** with no real display there's often no audio sink either — add a **PipeWire virtual sink** (or use the dummy plug's audio device) so Sunshine has something to capture.

#### Save-game sync (Steam Cloud for everything)
You back up game-*server* worlds (Section 6), but single-player PC saves on the rig aren't synced to your Steam Deck/laptop. **Ludusavi** (knows save locations for 19k+ Steam/GOG/Epic/Heroic titles) pointed at a **Syncthing** folder is the de-facto self-hosted save-sync — back up before a session, restore on the other device, no cloud.

#### One GPU, three jobs — a contention policy
The 3090 Ti hosts Sunshine streaming, heavy game servers, **and** Ollama inference. A model resident in VRAM steals from a game (and vice-versa), so set an explicit rule: run Ollama with **`keep_alive=0`** (unload the model the moment a request finishes) or simply **don't run inference during a stream/game session**. The LiteLLM fallback (Section 3) makes this painless — small queries hit the always-on Mac mini model, so the rig's GPU is free for the game.

#### Make the streamed library usable — a launcher
Sunshine streams whatever's running, but adding apps one-by-one is tedious. Add a **launcher** so the couch/stream experience covers more than Steam: **Heroic** (GOG/Epic/Amazon) or **Lutris** on CachyOS, surfaced through Sunshine (or Steam Big Picture). *Retro:* **RomM** is the rising "Plex for ROMs" — metadata scraping, a web UI with in-browser EmulatorJS play, and Playnite/RetroArch/Deck integration; run it on the Mac mini and stream/play from anywhere.

### Local AI beyond chat (the rig's other on-demand job)
Ollama + Open WebUI already give you local chat. Cheap extensions, all on the on-demand rig behind the same LiteLLM endpoint:
- **Image generation — ComfyUI** (or Stable Diffusion / A1111): the near-default local image stack, a natural NVENC-rig workload.
- **Coding assistant — Continue (VS Code/JetBrains) or Aider (CLI)** pointed at your local endpoint: the most common "second use" of a homelab LLM, free.
- **Chat with your own docs — Open WebUI RAG:** Open WebUI ships document upload + RAG + an embeddings model; point it at your **Obsidian vault** / Paperless docs so "ask my notes" works locally.

---

## 5. Electricity cost of running hardware 24/7

**Your rate:** RG&E all-in residential runs about **$0.20/kWh** in 2026 (supply + delivery; per-kWh delivery alone is ~8.5c and supply floats seasonally). Rule of thumb:

> **1 watt running 24/7 ~ $1.75/year.** Every 100W you leave on ~ $175/year.

| Device | Typical draw | ~Annual cost @ $0.20/kWh |
|---|---|---|
| DS920+ + 4 large drives | ~35-45W (less if drives hibernate) | **~$60-80** |
| Mac mini (Late 2014, i5-4278U, 8GB) (Ubuntu) | ~10-15W under load (idle ~6-10W) | **~$18-26** |
| HA Green (purchased) | ~2-3W | ~$4-5 |
| Dream Wall router | ~30-40W | **~$55-70** |
| Fiber ONT/modem | ~5-10W | ~$10-15 |
| **Always-on subtotal** | **~82-113W** | **~$150-200/year** |
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

> **NAS storage layout that implements this tiering:** the drive/pool/shared-folder/network-drive schema that puts Tier 1 and Tier 2 onto the right shares (with matching snapshot/backup policies) lives in [nas-storage-schema.md](nas-storage-schema.md). It converts the DS920+'s three independent Basic volumes into one redundant SHR-1 Btrfs pool — read it before the rebuild (it's destructive).

### Tier your data first (the key move)
Don't back up 40TB to the cloud (~$278/month at B2's current ~$6.95/TB). Split it:
- **Tier 1 — irreplaceable (cloud + local).** Immich photos, documents, Obsidian vault, **HA config**, **game-server worlds/saves**, the **CachyOS home directory** (dotfiles, app configs, local projects — see below), all your compose files/configs. Realistically 1-2TB. **This goes off-site to the cloud** (~$7-14/month at B2 — trivial insurance).
- **Tier 2 — replaceable media (local redundancy only).** Ripped movies/shows/music you could re-acquire. NAS RAID + one cold copy; **don't pay to cloud-store it.** For off-site of this tier, a **rotated external HDD** at your office or a relative's house is the cheap option.

### Tools
- **Synology native (turnkey, start here):** **Hyper Backup** (to B2 / Synology C2 / another Synology / external), **Snapshot Replication** (Btrfs point-in-time — great vs. accidental deletion/ransomware), **Active Backup for Business** (pull backups of your computers, including the Ubuntu box, onto the NAS).
- **Ubuntu/CachyOS -> cloud:** **Restic** (single Go binary, native B2/S3, simple password encryption, biggest community) or **Kopia** (similar + built-in web UI/scheduler).
- **SSH/local targets:** **BorgBackup + Borgmatic** (best compression, fastest restores, YAML scheduling, DB-dump hooks, healthcheck pings) with a cheap SSH storage box.

### Backing up the CachyOS rig (your daily-driver home directory)
The rig is on-demand, not a server — but `/home/you` still holds what a reinstall can't recreate: dotfiles and app configs (`~/.config`), shell/theme setup, SSH/GPG keys, browser profiles, local game saves (`~/.local/share`, Steam/Proton `compatdata`), and any documents/projects not already in Git or Proton. Back it up even though it sleeps a lot:
- **What:** target `~` and exclude the firehoses — `~/.cache`, Steam's re-downloadable game files, build/`node_modules` dirs, VM images. A short exclude list turns "hundreds of GB" into the few GB that actually matter.
- **How (set-and-forget):** a **Restic** (or Kopia) job from CachyOS straight to **Backblaze B2** — encrypted, deduplicated, on a `systemd` timer that fires while the rig is awake (run it from a Sunshine/login session or a wake hook so a sleeping box doesn't miss every window). This is the same Tier-1 tool already in the table; you're just adding the rig's home as a source.
- **Also keep a local copy:** point a second Restic repo — or **Synology Active Backup for Business**, which has a Linux agent — at the **NAS**, so the rig backs up over LAN when it's up (fast restores), and the NAS then sweeps that off-site with the rest of Tier 1. Two copies, one off-site, no thinking required.
- **Dotfiles bonus:** keep the actual dotfiles in the same **Git** repo as your compose files (or a `chezmoi` / bare-repo setup). Then a rig rebuild is `git clone` + restore `~` from Restic, and you're back to your exact environment in minutes — the same "rebuildable" property Section 7 gives the servers.

### Off-site targets (current pricing)
**Decision: Backblaze B2 is the off-site cloud copy** — bucket(s) created at [secure.backblaze.com/b2_buckets.htm](https://secure.backblaze.com/b2_buckets.htm). It's the hot Tier-1 target for both the NAS (Hyper Backup over the S3 API) and the Linux hosts (native Restic/Kopia), with **Object Lock** enabled for the immutable copy below. Hetzner/rsync.net stay listed only as the optional *second* off-site target for bulky Tier 2 if you ever want one.

| Target | ~Price | Protocol | Best for |
|---|---|---|---|
| **Backblaze B2 — chosen** | ~$6.95/TB/month, free-ish egress (free up to 3x stored/mo) | S3 API | Hot cloud copy of Tier 1; native Restic/Kopia |
| **Hetzner Storage Box** | ~$2-3.20/TB (tiered) | SSH/SFTP/Borg | Cheapest Borg/rsync target (EU) |
| **rsync.net** | pricier, Borg/restic plans | SSH/SFTP/Borg | Reliable SSH target, US options |
| **Rotated external HDD** | one-time drive cost | physical | Off-site copy of bulky Tier 2 |

> Synology NAS units don't qualify for Backblaze's flat $99/year personal plan (that's for direct-attached drives on a PC/Mac). For the NAS use **B2** (per-TB) or **Synology C2**.

### Immutable / ransomware-proof copy (3-2-1-1-0)
RAID and even off-site copies don't help if stolen credentials can *delete or re-encrypt* every backup. Add one **immutable** copy so a compromised host can't wipe its own history:
- **Backblaze B2 Object Lock** on the Restic/Kopia bucket — set a retention window so even your own keys can't delete objects until it expires.
- **Local retention runs normally; the immutable tier is B2.** Borg/restic do their usual **GFS pruning on the client** so the local and SSH repos don't grow unbounded — that's fine, because the **ransomware-proof copy is the Backblaze B2 bucket with Object Lock** (above): even stolen client keys can't delete or re-encrypt those objects until the retention window expires. *(Optional future hardening: also expose the SSH/Borg target as **server-side append-only** via an SSH forced command, so the off-site SSH copy is add-only too — but with B2 Object Lock already providing the immutable tier this is belt-and-suspenders, not required.)*
- **Synology immutable snapshots** (DSM 7.2+) on the NAS shares — a locked, read-only point-in-time even an admin can't remove early.
This is the "1" and the "0 errors" in **3-2-1-1-0**: three copies, two media, one off-site, **one immutable**, zero restore errors (verified).

### Database dumps (so a "backup" isn't a corrupt file)
File-copying a *live* database directory can capture a half-written, unrestorable DB. Dump first, then back up the dump:
- **Postgres** (Immich's VectorChord, Miniflux, Paperless, Dependency-Track): a nightly `pg_dump`/`pg_dumpall` to a `backups/` folder that the file-level job then ships off. **Borgmatic** has built-in DB-dump hooks (+ Healthcheck pings) — use them.
- **SQLite** (Uptime Kuma, etc.): use the SQLite `.backup` command (or stop-copy-start), not a raw file copy of a hot DB.

### Don't forget
- **Test a restore** at least once. An untested backup is a hope.
- **Store encryption keys/passphrases off the machine** (Bitwarden + a printed copy).
- **Back up Docker volumes and the CouchDB volume** (if you use LiveSync), and HA's backup archive, not just visible files.
- **Monitor that backups actually ran** — a dead-man's-switch (self-hosted **Healthchecks.io**, pinged by each job and alerting via ntfy when a ping *doesn't* arrive) catches the silent "the timer's been off for a month" failure that uptime checks never see.

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

### Dashboard & service launcher (one screen for everything)
Two needs, one tool: **your** observability, and a **friendly front door for your wife**. **Homepage** (the 2026 standard — YAML-configured, tiny footprint, version-controlled right next to your compose files) covers both.
- **For you (observability):** Homepage has 100+ live **service widgets** — it pulls real status/stats from Plex, Immich, Sonarr/Radarr/Lidarr/Prowlarr/Bazarr, qBittorrent, Pi-hole/AdGuard, Home Assistant, Uptime Kuma, and **Beszel**, plus container health via Docker label auto-discovery. One page answers "is everything up, what's downloading, how full are the disks." It complements rather than replaces Beszel/Uptime Kuma — those do deep metrics and alerting; Homepage is the at-a-glance roll-up that links into each.
- **For your wife (bookmarks / sharing):** Homepage's **bookmarks and service tiles** are just big labeled links with icons. Make a clean "Home" group — Plex, Immich, Calibre-Web, the request portal (Seerr) — with friendly names, tuck the nerdy widgets onto a separate tab, and give her **one memorable URL**. She clicks "Movies," it opens Plex. No app sprawl, no asking you for links.
- **Getting it to her devices:** put the dashboard behind **Caddy** (HTTPS) and reach it over **Tailscale** (install the app once on her phone/laptop); a friendly local name like `home.yourdomain` makes it feel like one place. For true zero-install on her end, expose just the dashboard via a Tailscale Funnel / Cloudflare Tunnel with auth in front.
- *If she ever needs her own login or you want per-person boards:* **Homarr** is the alternative — drag-and-drop UI with built-in user accounts/permissions. It's heavier (state in a DB, less Git-friendly), so only reach for it if multi-user access actually matters; otherwise Homepage's single shared page is the lower-maintenance pick.

### Remote access
- **Tailscale** — mesh VPN, near-zero config, generous free tier. Install on the NAS, Ubuntu box, rig, laptop, and phone; reach Jellyfin/Immich/CWA/Obsidian/HA remotely with no port-forwarding and nothing exposed. Also your path for **remote Moonlight** and **inviting friends to game servers**.
- *Full control:* self-host **Headscale** or use **Netbird**. Tailscale's hosted control plane is the pragmatic set-and-forget pick.

### SSH & maintenance access
With ~25 services across 4-5 boxes plus a seedbox, you'll be SSHing between machines constantly — so make it frictionless and secure once, not ad-hoc forever. You already install Tailscale everywhere (above), so lean on it for the access layer instead of hand-distributing keys.
- **Tailscale SSH as the primary path.** Run `tailscale up --ssh` on every node and you get **key-less, ACL-gated SSH over the tailnet** — no `authorized_keys` to copy around, no port 22 exposed anywhere, and it works identically in-home and remote. Auth is the tailnet identity (with optional **re-check** to force periodic re-auth), so a lost laptop is revoked centrally by de-authing the node, not by rotating keys on five hosts.
  - **Lock it down with ACLs + tags.** Tag your admin devices (laptop, phone) `tag:admin` and your hosts `tag:server`, then an ACL `ssh` rule lets only `tag:admin` SSH `tag:server` (as a chosen Unix user). This is far tighter than open SSH, and you can enable **session recording** to a recorder node if you want an audit trail of maintenance sessions.
- **Classic SSH key + `~/.ssh/config` as the break-glass fallback.** Tailscale SSH depends on the control plane being reachable; keep a normal path for when it isn't. One **ed25519** keypair, distributed to each host's `authorized_keys`, plus a `~/.ssh/config` with friendly aliases over MagicDNS names / Tailscale IPs:

```sshconfig
Host nas mini rig ha seedbox
  User admin
  AddKeysToAgent yes
  IdentityFile ~/.ssh/id_ed25519
  ForwardAgent no
Host nas
  HostName nas.tailnet-name.ts.net
Host mini
  HostName mini.tailnet-name.ts.net
Host rig
  HostName rig.tailnet-name.ts.net
```

So maintenance is just `ssh nas` / `ssh mini` / `ssh rig`. Keep `ForwardAgent no` by default (only enable per-command when you actually need to hop). The keypair and this config are tracked by **chezmoi** (Section 8), so a rebuilt box gets your whole SSH setup back with `chezmoi init --apply` — and the keys ride the Section 6 Tier-1 backup.
- **Per-host quirks (the things that bite):**
  - **Synology DSM** — SSH is **off by default**. Enable it (Control Panel -> Terminal & SNMP -> *Enable SSH service*), then make it key-based and put it behind the **DSM 2FA** you already enforce (Section 7 hardening). Don't SSH as the default `admin`/`root` — use a dedicated admin user. DSM resets `sshd_config` on updates, so treat deep SSH customization as non-persistent (document it in `hosts/ds920/restore.md`).
  - **HAOS (Home Assistant)** — there's no normal user shell. Use the official **SSH & Web Terminal add-on** (key auth, drop your public key in its config) for day-to-day, or the **`root@<ha-ip>:22222`** debug port for low-level access. This is the same box whose `/config` already lives in Git (Section 8).
  - **On-demand rig** — it's asleep most of the time, so **wake then SSH**: send a Wake-on-LAN packet (`wol`/`etherwake <mac>`) and `ssh rig` once it's up. This reuses the exact WoL setup from Sections 4-5; pair it with the "fire jobs only while awake" timer trick (Section 6) so the rig's own backup/SBOM jobs and your manual SSH share one wake path rather than fighting auto-suspend.
  - **Seedbox** — already keys-only and hardened (see Security hardening below). Just add it to the same `~/.ssh/config` and your tailnet so it's reachable like any other node, with nothing extra exposed.
- **Fleet maintenance — run one command across every box.** At 4-5 hosts, "SSH in and update each one" gets old fast. Stand up a tiny **Ansible** setup (agentless — it just uses the SSH/Tailscale path above) with an inventory of your hosts and a few small playbooks: apply security patches, reboot in a controlled order, and audit for package/version drift against the manifests from Section 8. Run it from the Mac mini or your laptop. This is the **manual** fleet lever; it complements (doesn't replace) the automatic **`unattended-upgrades`** security patching in *Security hardening* below — unattended-upgrades keeps each box current on its own, Ansible is for the times you want to push a deliberate change everywhere at once. The playbooks live in the Section 8 control repo, so they're version-controlled and rebuildable like everything else. (For the occasional one-off, a plain `for h in nas mini rig; do ssh $h '<cmd>'; done` is fine — reach for Ansible once you're repeating yourself.) **Section 9 builds this out fully** — inventory, roles, the `ansible-pull` set-and-forget convergence loop, SOPS-integrated secrets, and turning the Section 8 restore runbooks into one executable playbook.

### Reverse proxy + HTTPS (for services you expose locally)
- **Caddy** — automatic HTTPS with a tiny config. The set-and-forget choice.
- *GUI alternative:* **Nginx Proxy Manager**.
- **Decision — Caddy owns 80/443 on the Mac mini.** Caddy is the single reverse proxy for the whole hand-managed stack: it reaches each service by container name over a shared `edge` Docker network (`reverse_proxy seerr:5055`), so it *must* be co-located with those containers. That rules out a second proxy also binding 80/443 on the same box. **Coolify (next) ships its own bundled proxy that wants 80/443 too** — so do *not* let Coolify's proxy take those ports here. Two ways to keep the peace, in order of simplicity:
  - **(A, recommended) Skip Coolify's proxy; let Caddy front everything.** Ship each vibecoded app as a small Compose stack in `/opt/stacks` (managed by Dockge) and add a one-line Caddy vhost (or a `*.app.{$DOMAIN}` wildcard). It's the same pattern every other service already uses — no second proxy, no port fight, and you skip Coolify's ~600-800 MB + its Postgres/Redis on an already-busy box.
  - **(B) Keep Coolify's git-push workflow, behind Caddy.** Run Coolify but move its bundled proxy to alternate ports (e.g. 8000/8443) and have Caddy wildcard-proxy `*.app.{$DOMAIN}` → Coolify's proxy. One host, no conflict, but two proxies to reason about.
  - Either way: **don't run two proxies both bound to 80/443 on one host**, and don't split Caddy onto the NAS — its container-name routing only works where the containers live (the Mac mini).

### Self-hosting your own apps (vibecode -> live on the LAN)
The goal: you build a little app (a script, a dashboard, a vibecoded web tool) and want it reachable by name on every device in the house with as little ceremony as possible. The set-and-forget answer is a tiny self-hosted PaaS — your own Heroku/Vercel — on the always-on Mac mini.
- **Coolify** — point it at a Git repo (your self-hosted **Forgejo** control repo from Section 8, or GitHub) and it auto-detects the stack (Node/Bun/Python/PHP/static) via **Nixpacks**, builds, deploys, assigns a hostname, and wires up TLS — **push to the repo and it redeploys** via webhook. It also takes a raw **Dockerfile** or **Docker Compose** if you'd rather, and ships 280+ one-click templates. *Footprint:* idles ~600-800MB RAM plus its own Postgres/Redis. **Port note:** Coolify's bundled proxy wants 80/443, which Caddy already owns on the Mac mini — so run Coolify under the "behind Caddy on alternate ports" pattern from *Reverse proxy + HTTPS* above (option B), not with its proxy on the default ports. Given the Mac mini is already carrying the full always-on stack (see Section 0's host table and the capacity note in Section 5), **option (A) — skip Coolify and ship vibecoded apps as plain Compose stacks behind Caddy — is the lighter, lower-friction default**; reach for Coolify only if you specifically want the git-push-to-deploy loop.
- **LAN visibility (the one bit that makes it "just work"):** add a **single wildcard record** in **Pi-hole/AdGuard** — `address=/home.lan/<mac-mini-IP>` — so *every* `*.home.lan` name resolves to the Mac mini. **Caddy** (the single proxy) then routes each app by its hostname. After that, shipping a new app is just "add a one-line Caddy vhost (or use the wildcard) and pick a name" and it's live at `http://myapp.home.lan` for the whole network — no per-app DNS edits, no port juggling. (Under option B above, Caddy hands `*.app.home.lan` to Coolify's alternate-port proxy, which does the per-app routing.)
- **HTTPS:** plain HTTP on `name.home.lan` is the zero-effort LAN default. If you want green-padlock local names, give **Caddy** the **DNS-01 challenge** with a real domain (the `home.yourdomain` you already use for the dashboard — see the `cloudflare_tls` snippet in the Caddyfile) to get a trusted wildcard cert without exposing anything.
- **Remote:** reach your apps off-LAN the same way as everything else — over **Tailscale** (Section's Remote access), no ports opened.
- **Tie-ins:** drop each new app onto **Homepage** (it shows up on your dashboard and, if household-facing, your wife's bookmarks), and because it lives in Git it inherits the Section 8 "rebuild in an hour" property for free.
- *Lighter alternative:* **Dokploy** — same git-push-to-deploy model with a cleaner, more minimal UI and slightly lower idle RAM; smaller community/template library. Pick it if Coolify's dense dashboard feels like too much.

### Security hardening (do these once)
- **MFA / 2FA everywhere — the highest-value, lowest-effort upgrade.** Turn on TOTP (your authenticator app) for every account that supports it, and a hardware key where it matters:
  - **Crown jewels (hardware key / passkey):** Bitwarden, Proton, the **Synology DSM** admin account, your email, and the Tailscale/GitHub/Forgejo accounts that gate everything else. DSM: Control Panel -> User -> Advanced -> enforce 2-step verification; supports WebAuthn/passkeys.
  - **App-level TOTP:** **Immich** (Account -> security), **Plex** (Account -> 2FA), **Seerr/Jellyseerr**, **Home Assistant** (Profile -> Multi-factor), the **seedbox** panel, **Forgejo**, **Paperless-ngx**, **Vaultwarden** (if used).
  - **Reverse-proxy MFA for the rest:** apps without native 2FA can sit behind a forward-auth layer (below) that enforces it centrally.
- **Exposed-service hardening (only what's actually reachable).** Your Tailscale-first design means the home stack isn't exposed — so this targets the **seedbox** and any **public game-server port-forwards** (Section 4): run **CrowdSec** (modern, shared-threat-intel fail2ban) or **fail2ban** on those, keep them patched, and SSH **keys-only**. For anything you *do* publish via Caddy, add a lightweight forward-auth gate — **Pocket-ID** or **tinyauth** (simple), or **Authelia/Authentik** (full SSO + enforced 2FA) — rather than exposing an app's bare login.
- **Docker log rotation (silent disk-fill killer).** Docker's default `json-file` driver grows logs unbounded — a classic "set-and-forget box dies months later." Set global caps once in `/etc/docker/daemon.json` (`log-driver: json-file`, `log-opts: max-size=10m, max-file=3`) and restart the daemon.
- **OS security patches.** You deliberately avoid blind *container* auto-updates, but the *OS* should still get security fixes: enable **`unattended-upgrades`** (Ubuntu) for security-only patches; on CachyOS, update on your own cadence.

### Config-as-code (makes "rebuild in an hour" true)
- Put **all compose files + configs in Git** — self-hosted **Gitea/Forgejo**, or a private GitHub repo. Disk dies or you migrate hosts -> `git clone` + `docker compose up` and you're back. This habit turns a homelab from fragile to disposable-and-rebuildable. (Secrets are encrypted in-repo with **SOPS + age** — see Section 8.)

### Power resilience
- **UPS** on the NAS + Ubuntu box + Dream Wall. DSM reads most consumer UPSes over USB and does a graceful shutdown on battery — important on fiber where brief outages can corrupt a DB mid-write. The Ubuntu box can listen to the NAS's UPS status over the network (NUT).

---

## 8. Inventory, SBOMs & rebuildable state (know what's running; restore it in an hour)

By the end of this build you'll be running ~25 services across 4-5 boxes (NAS, Mac mini, rig, HA, Dream Wall) plus an off-site seedbox. Section 6 (Restic/Borg/Hyper Backup) saves your **data**; Section 7's config-as-code saves your **compose files**. This section closes the last two gaps:
1. **A live inventory + SBOM** — one place that answers "what's installed, on which host, what version, and is any of it now vulnerable?" at a glance.
2. **Complete state-in-Git** — `/etc`, dotfiles, cron/timers, app configs, and device exports, so a dead or wiped box is a `git clone` + restore away, not a weekend of remembering how you set it up.

### Why "SBOM" is the right frame for a homelab
An **SBOM (Software Bill of Materials)** is a machine-readable list of every component and version inside a piece of software. For a homelab the payoff isn't compliance paperwork — it's two things you actually want: a single queryable answer to *"what version of X am I running, and where?"*, and an automatic *"the moment a CVE is published for something you run, you're told."*

The 2026 supply-chain reality makes this concrete. The **TeamPCP campaign (March 2026)** poisoned the Trivy scanner (`trivy-action` tags rewritten, malicious Docker images pushed), and that cascaded into the popular `litellm` PyPI package via stolen CI credentials — tracked as **CVE-2026-33634 (CVSS 9.4), added to CISA's Known Exploited Vulnerabilities catalog**. The lesson for a set-and-forget box: **pin versions, verify signatures/digests, and keep an inventory** so that when the next one lands you can answer "was I exposed, and where?" in seconds instead of days.

### The centerpiece: a continuously-monitored SBOM dashboard (OWASP Dependency-Track)
- **Dependency-Track v5 (codename "Hyades")** — the open-source platform (20,000+ orgs) that ingests **CycloneDX** SBOMs and **continuously re-analyzes your entire inventory** against multiple vulnerability sources (NVD, OSS Index, GitHub advisories) with **EPSS** prioritization — not just at scan time, but every time new intel lands. It tracks **OS packages, containers, firmware, and services** across every version of every "project," which maps perfectly onto "every host and every stack in my house."
  - *Version note:* v5 is GA and is the most extensive redesign since inception (horizontal scaling, active/active HA, durable processing that resumes after a crash). v4 is **maintenance-only and reaches end-of-life December 2026**, and v5 doesn't upgrade in place — so start on **v5**. It ships as separate API-server + frontend containers (Docker Hub / GHCR) and needs **PostgreSQL**.
  - *Model:* make each host and each stack a DT **project**; nightly SBOM uploads keep it live. Then "is anything I run vulnerable?" is one dashboard, and "show me everywhere `libfoo 1.2.3` is installed" is one search.
  - *Host on:* the **NAS** (always-on, with RAM headroom — the Java API server wants **~4GB+** on its own (official minimum 2-4.5GB, recommended 8-16GB), which is exactly the weight Section 0's capacity note keeps off the small Mac mini). **This requires the DS920+ RAM upgrade first** (4GB → 20GB via the Crucial `CT16G4SFD8266`, ~$40-110, decided/future purchase — see Section 0's capacity note); on the stock 4GB NAS, run Dependency-Track on the rig on-demand instead, since it won't fit alongside Immich/Plex. (The nightly Syft job still PUTs SBOMs to it over the LAN/Tailscale regardless of host.)

### Generating the SBOMs — Syft + Grype (and a deliberate note on Trivy)
- **Syft (Anchore)** — the generator. Produces CycloneDX (and SPDX) SBOMs from **container images *and* whole filesystems/directories**, with the deepest cataloger coverage of any tool (it even pulls components out of compiled Go/Rust binaries and nested Java jars). **Grype (Anchore)** scans the results. The pattern is **Syft-then-scan**, with the SBOM as a signable, archivable artifact.
- **Why standardize generation on Syft here, even though Dockhand already bundles image scanning:** Section 7's Dockhand gives you Grype/Trivy scanning of container images, and that's still useful for the container layer. But for the *whole-fleet* SBOM pipeline feeding Dependency-Track, use single-purpose **Syft** — it decouples generation from scanning (so the SBOM can be signed and consumed by DT independently), and given the March-2026 `trivy-action` compromise, fewer moving parts in the credential-bearing nightly job is the set-and-forget call. **Pin the tool versions and verify checksums/signatures regardless of which scanner you use** — that discipline is the actual takeaway from CVE-2026-33634.
- **The nightly per-host job** (systemd timer):
  - `syft dir:/ -o cyclonedx-json` for the host filesystem (catches pacman/apt/flatpak system packages *and* language packages) → one CycloneDX file.
  - `syft <image> -o cyclonedx-json` for each running container image.
  - Upload each to Dependency-Track via its REST API (`dtrack-cli` or `curl`) under that host's/stack's project.
  - Also export the plain human manifests that make a bare-metal rebuild trivial and double as an offline inventory: `pacman -Qqe` (+ a separate AUR list) on CachyOS, `apt-mark showmanual` on Ubuntu, `flatpak list`, and your pinned compose image tags. Commit these to the control repo (below).

### The control repo: state-in-Git, structured for restore
A single **private** repo — self-hosted **Forgejo/Gitea**, or a private GitHub repo (Section 7) — that is the source of truth, structured so each host has an obvious restore path:

```
homelab/
  hosts/
    cachyos/    # pacman + AUR lists, /etc snapshot ref, restore.md
    macmini/    # apt manual list, /etc ref, restore.md
    ds920/      # DSM config export, package list, restore.md
    ha/         # HA /config (YAML, automations, dashboards)
  stacks/       # every docker-compose.yml + .env.example, per service
  network/      # UniFi .unf exports
  ansible/      # inventory + fleet-maintenance playbooks (patch, reboot, audit) — see Section 7 SSH & maintenance access
  inventory.md  # auto-generated nightly: what / where / version / status
  secrets/      # SOPS + age encrypted
```

### Backing up the configs, scripts, cron jobs & dotfiles (per host)
- **`/etc` -> etckeeper.** Puts `/etc` in Git, **auto-commits on every apt/pacman operation**, and preserves the file **metadata** Git normally drops (the permissions that matter for `/etc/shadow`). Add a small **`systemd.path` unit watching `/etc`** so manual edits get committed in near-real-time too, and set **`PUSH_REMOTE`** to push to the control repo over SSH. **Warning: `/etc` contains real secrets (`/etc/shadow`, keys, tokens) — this remote MUST be private and ideally encrypted (see below).** Works on both CachyOS (pacman hooks) and Ubuntu (apt hooks).
- **Dotfiles (`~`) -> chezmoi.** The tool floated in Section 6, with its real role here: track `~/.config`, shell/theme setup, editor config, etc., with **templating + built-in `age` encryption** for secrets and the `~/.zshrc.local` machine-specific override pattern. A rig rebuild becomes `chezmoi init --apply <repo>`. (Keep the actual files next to your compose files in the same control repo, per Section 6.)
- **Cron + systemd timers.** etckeeper already captures `/etc/cron.d`, `/etc/cron.*`, and `/etc/systemd/system`. What it *misses* is **per-user crontabs** and **user units** — so the nightly job also exports `crontab -l` (per user), `systemctl list-timers`, and `~/.config/systemd/user/` into `hosts/<box>/`.
- **Home Assistant.** Its own full backups go to the NAS (Section 3) — but also put `/config` (YAML, automations, dashboards, blueprints) under Git via the community **Git pull/push add-on** or a tiny commit job, so the *declarative* state lives alongside everything else. (And the **backup encryption key** goes in your password manager — you can't restore HA without it.)
- **UniFi Dream Wall.** Auto-backup is on by default; pull the **`.unf`** export into `network/` on a schedule. (Section 1 already insists you back up before the one-way Zone-Based Firewall migration — this just keeps doing it.)
- **DS920+ / DSM.** DSM is locked down — don't fight it with etckeeper. Use **Control Panel -> Update & Restore -> Configuration Backup** on a schedule (it captures settings, users, shared-folder config, and the Task Scheduler) into `hosts/ds920/`, plus Hyper Backup's own config export, plus the installed-package list. Document, don't automate the un-automatable.
- **Docker volumes / databases.** Section 6 owns the **data** (Restic/Borg, with DB-aware dump hooks — including Dependency-Track's own Postgres). The control repo owns the **recipe**. Together: `git clone` + `docker compose up` + restore the volume = the service is back.

### Secrets, the right way
`/etc` and dotfiles inevitably contain secrets, so a private remote alone isn't enough. Two-layer rule:
1. The control-repo remote is **private** (self-hosted Forgejo on the NAS/Mac mini, or private GitHub).
2. Encrypt the sensitive bits **at rest** with **SOPS + age** (or git-crypt) so even a leaked repo is inert; chezmoi has native `age` encryption for the dotfile half.

Keep the **age/SOPS key in your password manager + a printed copy** — the same discipline Section 6 demands for the Restic and HA keys. (A backup you can't decrypt after the fire is not a backup.)

### The "at a glance" dashboard (tie it together)
- **Dependency-Track** *is* the software-inventory dashboard: what's installed, what version, what's vulnerable, on which host — continuously updated.
- **Homepage** (Section 7) gets a **custom-API widget** hitting DT's REST/metrics for a headline (projects tracked, total + critical vulnerabilities) plus tiles linking into DT, **Beszel**, and **Uptime Kuma**. One screen now covers **health** (Beszel/Uptime Kuma), **risk** (Dependency-Track), and the friendly **front door** for your wife.
- **`inventory.md`**, auto-generated nightly from the plain manifests, makes the repo itself a readable "what / where / version / status" table — useful precisely when the dashboards are down because a box is down.
- **Alerts via ntfy** (Section 7): Dependency-Track notifies on newly-discovered vulnerabilities; the nightly job pings ntfy on failure. **Diun** (Section 7) already covers "a new image is available."

### Restore runbook (the thing that makes it real)
Each `hosts/<box>/restore.md` is a short, *tested* checklist. Generic shape:
1. Reinstall the OS (CachyOS / Ubuntu) -> install `git`, `restic`, `chezmoi`.
2. `git clone` the control repo. Restore `/etc` files **selectively** from etckeeper history — **don't blanket-checkout an old tree into a live `/etc`** (it operates on the running system); restore the files you need, then re-run `etckeeper init` so metadata handling is refreshed.
3. Reinstall packages from the manifest (`pacman -S --needed - < pkglist`; `xargs -a aptlist apt install`).
4. `chezmoi init --apply` for dotfiles; reinstate cron/user timers.
5. `docker compose up -d` per stack; restore volumes/DBs from Restic.
6. Re-join Tailscale; confirm green in Homepage / Beszel / Dependency-Track.

**Drill it quarterly in a throwaway VM** — Section 6's "test a restore," extended from a single file to a whole host. An untested runbook is fiction.

### Where it all runs (power-aware, per Sections 0 & 5)
- **Mac mini (always-on, ~12W):** Forgejo (control-repo remote) and the nightly orchestration. (The light always-on web stack also lives here — see Section 0.)
- **Each host:** Syft/Grype + etckeeper + the manifest/cron exporters, fired by systemd timers. On the **on-demand rig**, gate the timer to "while awake" with the same wake-hook trick as the Restic job in Section 6, so a sleeping box doesn't just miss every window.
- **NAS:** DSM Configuration Backup + holds the Restic repo and HA backup archives; also hosts **Dependency-Track** (API + frontend + Postgres) and the other offloaded heavy services (Paperless, Frigate, Tdarr server) per Section 0's capacity note.

---

## 9. Fleet automation with Ansible (make the runbooks executable)

Sections 7 and 8 get you *rebuildable* — config-as-code, manifests, chezmoi, etckeeper, and a per-host `restore.md`. But almost all of that is **descriptive** (it records state) or **hand-run** (you follow the runbook). Ansible is the layer that turns it **executable and self-converging**: one idempotent definition of every host you fully own, applied the same way to all of them, on a schedule, with drift you can see before you fix. It's what makes "set it and forget it" and "replicable across my devices" literally true instead of aspirational.

The discipline that matters: an Ansible run is **idempotent** — run it once or a hundred times, the result is the same, and a `--check --diff` dry run *shows* you exactly what would change before anything does. That's the same "no blind auto-updates" philosophy as Section 7, applied to host config.

### Where Ansible fits (and where it deliberately doesn't)
This is the most important decision — Ansible overlaps several tools already in the plan, so give each a clean lane:

| Layer | Owner | Ansible's role |
|---|---|---|
| **OS / host state** (packages, Docker engine, `daemon.json`, `edge` network, unattended-upgrades, NUT client, sysctl, SSH hardening, systemd timers) | **Ansible** | Sets and enforces it, fleet-wide |
| **`/etc` change audit** | **etckeeper** (Section 8) | Ansible *sets* canonical `/etc` files; etckeeper *records* that they changed (incl. metadata) |
| **User dotfiles (`~`)** | **chezmoi** (Section 8) | Ansible *installs and invokes* chezmoi (`chezmoi init --apply`); it does not duplicate per-user `~` templating |
| **Container runtime/lifecycle** | **Komodo / Dockge** (Section 7) | See the split below — Ansible does host prep + first bring-up; the chosen tool owns the day-to-day loop |
| **Secrets at rest** | **SOPS + age** (Section 8) | Ansible *consumes* them via `community.sops` — no second secret system |

The honest line on what Ansible should **not** manage:
- **DS920+ / DSM** — DSM owns its own config DB and **resets `sshd_config` and system files on updates** (Section 7 already flags this). Ansible-managing the NAS OS fights the appliance and loses. Keep **DSM Configuration Backup + Hyper Backup** (Section 8) as its restore path; at most point a nightly **Syft** run at it.
- **HAOS (Home Assistant)** — no general-purpose shell/Python to drive, so Ansible can't converge it. Keep HA's **own backups + the Git `/config` add-on** (Sections 3/8).
- **Dream Wall / UniFi** — no Ansible control surface worth trusting, and the Zone-Based Firewall migration (Section 1) is one-way GUI work. Keep the **`.unf` export** (Section 8). (You *can* poke the controller API with the `uri` module for the odd toggle, but don't automate the un-automatable.)
- **Managed seedbox** — usually jailed/no root, so manage only the **user-space** you control (compose stacks, *arr/Recyclarr configs), not its OS.

**So Ansible's real fleet is the boxes you own at the OS level: the CachyOS rig + the Mac mini (+ the seedbox's user-space).** That's exactly where the per-host runbooks were most tedious — and where a playbook pays off most. The NAS, HA, and UniFi keep their native backup/restore. Set this expectation up front and you avoid the classic mistake of trying to Ansible-manage an appliance.

### The container split (resolve the overlap with Section 7)
You picked a container manager in Section 7 (**Komodo** for fleet-style Git-driven deploys, or **Dockge** for the simple single-host case). Don't have two tools racing to `docker compose up`:
- **If you run Komodo** (Git-driven, multi-server): let **Komodo own the compose deploy loop**. Ansible only lays the foundation beneath it — Docker engine, `daemon.json` log rotation, the `edge` network, and the SOPS-templated `.env` files Komodo then uses.
- **If you stay on Dockge** (manual UI, single host): Ansible can also **push the compose stacks** (`community.docker.docker_compose_v2`) and template `.env` from SOPS, since Dockge won't.
Either way Ansible owns the host *underneath* the containers; only one tool owns the containers themselves.

### The control node and where it all lives
Ansible lives **inside the same Forgejo control repo** from Section 8 — so a `git clone` of `homelab/` gives you both the state *and* the engine that applies it. Run it from the **always-on Mac mini** (and your laptop as the human-driven control node). Layout slots into the existing repo:

```
homelab/
  ansible/
    ansible.cfg
    requirements.yml        # pinned collections (community.docker, community.general,
                            #   community.sops, ansible.posix) + roles
    inventory.ini           # the fleet, by ssh-config alias (net-14)
    group_vars/
      all.yml               # fleet-wide defaults
      on_demand.yml         # rig: wake-gating, "while awake" behavior
    site.yml                # the whole fleet (both the push and ansible-pull entrypoint)
    playbooks/
      patch.yml             # rolling OS security updates
      reboot.yml            # controlled, ordered reboots
      audit.yml             # package/version drift vs. the Section 8 manifests
    roles/
      base/ docker/ tailscale/ backup/ sbom/ state/
  ...                       # (hosts/, stacks/, network/, secrets/ from Section 8)
```

**Inventory is the "replicable across my devices" backbone** — group by OS family *and* power tier so a role applies to the right machines automatically:

```ini
# inventory.ini — ssh-config aliases (net-14), grouped by OS family + power tier
[debian]
macmini  ansible_host=mini
seedbox  ansible_host=seedbox

[arch]
cachyos  ansible_host=rig

[fleet:children]      # site.yml targets `hosts: fleet`
debian
arch

[always_on]           # converge on a clock
macmini
seedbox

[on_demand]           # the rig — wake-gated (group_vars/on_demand.yml)
cachyos

[docker_hosts]        # gets the docker role; seedbox excluded (managed/jailed)
macmini
```

It reuses the **`~/.ssh/config` aliases** from Section 7 (each `ansible_host` is an alias whose `HostName`, user, and key resolve over **Tailscale MagicDNS + key-less Tailscale SSH**) — no new access layer, nothing exposed, and a de-authed laptop loses Ansible access centrally. The `fleet` group is what `site.yml` converges; `docker_hosts` is what gates the `docker` role.

### Push vs. pull — the actual set-and-forget decision
Use **both**, for different jobs:
- **`ansible-pull` on a systemd timer per host = the set-and-forget default.** Each box periodically clones the control repo and **converges itself**. No central scheduler to babysit, it keeps working even if the Mac mini is down, and it's the natural way to correct drift. On the **on-demand rig**, gate the timer to "while awake" with the **exact wake-hook trick from Sections 6/7** so a sleeping box doesn't just miss every window — the rig's Restic job, SBOM job, and Ansible convergence all share one wake path.
- **Push (`ansible-playbook` from the Mac mini/laptop) = orchestration that needs ordering.** Rolling OS patches with `serial: 1`, reboot, and a health gate before the next host; coordinated multi-host stack redeploys. Things `ansible-pull` (which only knows about its own host) can't sequence.

The safe-by-default move that mirrors Section 7's "no blind updates": run pull in **`--check` (report-only) mode for *config* changes** — it pings **ntfy** when it detects drift but waits for your deliberate push to apply — while letting it **auto-apply only OS security patches** (the same scope as `unattended-upgrades`). You get self-healing where it's safe and a heads-up where it isn't.

### Secrets — reuse SOPS + age, don't add ansible-vault
The `community.sops` collection (2.4.0) reads your existing SOPS+age files directly via `age_keyfile`, so the **age key already in Bitwarden + printed** (Section 8) is the *only* secret store. No `ansible-vault` to manage in parallel:

```yaml
# group_vars/all.yml
sops_age_keyfile: /home/admin/.config/sops/age/keys.txt

# in a role, template a stack's .env from a SOPS-encrypted file:
- name: Render Seerr .env from SOPS
  ansible.builtin.copy:
    dest: /opt/stacks/seerr/.env
    content: "{{ lookup('community.sops.sops', 'secrets/seerr.env.sops', age_keyfile=sops_age_keyfile) }}"
    mode: '0600'
```

(For `ansible-pull`, the age key lives on each host already — it's the same key chezmoi/SOPS need there per Section 8.)

### The roles to build (each maps to something already in the plan)
Small, single-purpose roles so the fleet is just a stack of them. Every one replaces a chunk of hand-run `restore.md`:
- **`base`** — admin user + the ed25519 key (Section 7), timezone/locale, `unattended-upgrades` for security-only patches (Section 7), sysctl (incl. the conntrack tuning if you ever fall back to home torrenting, Section 2), and **package convergence from the manifests** (`community.general.pacman` / `ansible.builtin.apt` fed by the `pacman -Qqe` / `apt-mark showmanual` lists Section 8 already exports). The manifest stops being a *record* and becomes the *enforcer*.
- **`docker`** — engine + compose plugin, the **`daemon.json` log-rotation caps** (Section 7's silent-disk-fill fix), and `docker network create edge` (the Phase 2 prep step, now idempotent and never forgotten).
- **`tailscale`** — install + `tailscale up --ssh` with the `tag:server` ACL tags (Section 7).
- **`backup`** — Restic install + the systemd timer, with rig wake-gating (Section 6).
- **`sbom`** — Syft/Grype install + the nightly timer + DT upload (Section 8), **pinned to a version and checksum-verified** — that's the literal lesson of CVE-2026-33634 (Section 8), now codified instead of remembered.
- **`monitoring`** *(planned — not yet in `site.yml`)* — would install the Beszel agent and friends (Section 7); for now Beszel agents are deployed by hand.
- **`state`** — installs and bootstraps **etckeeper and chezmoi themselves** (`chezmoi init --apply <repo>`), so even your state-tracking tools are reproducibly present on a fresh box.

### This is what finally makes `restore.md` real
Section 8's restore runbook is a checklist a human follows — which means it rots silently until the day you need it. With Ansible, **`hosts/<box>/restore.md` becomes (or just wraps) `site.yml`**: reinstall the OS, install `git`/`ansible`, `git clone` the control repo, `ansible-pull` (or `ansible-playbook site.yml --limit <box>`), restore data from Restic — done. The **quarterly throwaway-VM drill** (Section 8) now runs the *actual* playbook against a fresh VM, so the runbook **can't drift from reality** — if it breaks, the drill fails and tells you, instead of you discovering it mid-disaster.

Keep it honest with cheap CI in Forgejo Actions: run **`ansible-lint`** and **`ansible-playbook --check --diff`** on every push to the control repo, so a bad change is caught before it ever reaches a host. (Molecule for per-role testing exists if you want it, but it's heavier than this two-box fleet needs — `--check` in CI is the right-sized discipline here.)

### Bottom line
Ansible doesn't replace anything in Sections 7-8 — it **operationalizes** them. chezmoi still owns `~`, etckeeper still audits `/etc`, Dockhand/Dockge still run containers, SOPS+age still holds secrets, and the NAS/HA/UniFi keep their native backups. Ansible is the idempotent engine that installs and wires all of it the same way on the rig and the Mac mini, on a timer, with drift you can preview — turning "I have a runbook" into "the fleet maintains itself, and a wiped box rejoins it in one command."

---

## Suggested rollout (phased)

Do a phase before starting the next; each leaves you better off.

**Phase 1 — Foundation (network, access, safety net)**
1. **Back up your UniFi config**, then build the segmentation: Default(mgmt) / Trusted / IoT / Guest / Work, the firewall rules, mDNS reflector on + IGMP snooping off. (One-way door on the new firewall — back up first. **Start here.**)
2. **Install Tailscale** on the NAS, Mac mini, rig, laptop, and phone. Turn on **Tailscale SSH** (`tailscale up --ssh`) with `tag:admin`->`tag:server` ACLs, and drop in your `~/.ssh/config` aliases + ed25519 key as the break-glass fallback (enable SSH on DSM, the HA SSH add-on) — so admin access to every box exists from day one. (See Section 7's *SSH & maintenance access*.)
3. **Lock in backups:** Synology Hyper Backup + Snapshot Replication, plus a Restic/Kopia job for your irreplaceable data -> B2. Test one restore. **If you're also re-pooling the NAS into SHR-1, follow [nas-storage-schema.md](nas-storage-schema.md)** — its migration runbook depends on this safety net (Tailscale + B2 + a verified Tier 1 offload) being in place first, and the re-pool is destructive.

**Phase 2 — De-cloud the essentials**

> **Prep the Mac mini Docker host first.** Before the first stack here (LiteLLM, Seerr) comes up, install Docker and **create the shared proxy network once: `docker network create edge`**. Every web stack joins `edge` as an `external` network — `docker compose up` fails if it doesn't exist yet — and Caddy (Phase 4) later reaches each service by container name across it. (See `foss-setup/configs/docker-stack/README.md` → *One-time host prep*.)

4. **Home Assistant** (HA Green — purchased): add Hue (local), Midea (local via `midea_ac_lan` or an ESPHome dongle), Nest (SDM API). Move smart devices onto the IoT VLAN. Then build the local backbone: **Zigbee coordinator + Zigbee2MQTT + Mosquitto** for cheap local sensors (see shopping list), the **HA Companion app** + presence, the **UniFi Protect integration** for your cameras, the **HomeKit Bridge** so iPhones keep Siri/Home, scheduled **HA backups to the NAS** (key in Bitwarden), and **Node-RED** if automations get complex. Point local voice at **LiteLLM** (small always-on model on the Mac mini, falling back to the rig's Ollama).
5. **Seedbox pipeline:** sign up for the **Bytesized "Stream +3"** seedbox (3000 GB, 6-10 TB/mo upload cap, €16), install qBittorrent + Sonarr/Radarr/**Lidarr**/Prowlarr/Bazarr + **Recyclarr** (TRaSH profiles) + **Unpackerr** + a sync agent on it, run **Seerr/Jellyseerr** at home, put the seedbox on Tailscale, and point the sync at your NAS library (set qBittorrent ratio/seed-time limits so the 3 TB box self-prunes and stays under the upload cap). Then **decommission the NAS dual-LAN/Gluetun setup** and drop the 5 Mbps cap.
   - **Music, specifically:** yes, automated acquisition includes it — **Lidarr** drops into this same seedbox pipeline. The one twist: torrent trackers are weak for music, so the standard add is **slskd (Soulseek) + Soularr** for hands-off album fetching — **run both on the seedbox** too, since Soulseek is also P2P. Results land in your NAS library and serve through **Navidrome**.
6. **Immich** with phone auto-backup; import your mirrorless camera's SD card via **immich-go** / **pbak**. Start leaving iCloud Photos.

**Phase 3 — The analogue media stack**
7. **Calibre + Calibre-Web-Automated + KOReader (Kobo) + Syncthing** for reading.
8. **iPod via Rhythmbox/libgpod** + **gPodder** for music/podcasts (one plug-in syncs both); add **Pinchflat** if you want YouTube channels archived into Plex / as podcast feeds.
9. **Miniflux** (+ optional Wallabag) for RSS, wired into KOReader's news plugin.
10. **Turn on Obsidian Sync** (paid, official — nothing to host).
11. **Paperless-ngx** for documents (OCR filing cabinet) and **Mealie** for recipes — the two "forgotten iCloud" household apps. Keep **Bitwarden** as the password manager (Vaultwarden if you later want to self-host the vault).

**Phase 4 — Glue & polish**
12. Stand up the management layer: **Homepage** (dashboard/observability + the household front door for your wife) + **Dockhand** (or Dockge) + **Beszel** + **Uptime Kuma** + **ntfy** + **Caddy**, and add **Pi-hole / AdGuard** for network DNS filtering (then **Unbound/DoT** for encrypted upstream + a second resolver).
13. **Wire LAN app hosting:** add the `*.home.lan` wildcard DNS record (`address=/home.lan/<mac-mini-IP>`) in Pi-hole/AdGuard so any name resolves to the Mac mini, and let **Caddy** route by hostname. Ship vibecoded apps as small Compose stacks behind Caddy (option A). *Only if you want git-push-to-deploy:* stand up **Coolify** with its proxy on alternate ports behind Caddy (option B) — never let it grab 80/443, which Caddy owns. See Section 7's *Reverse proxy + HTTPS*.
14. **Media companion layer:** **Tautulli** (Plex stats), **Kometa** (collections/overlays), **Maintainerr** (auto-pruning) on the Mac mini, and **Tdarr** (server on the **NAS**, transcode node on the rig). Add **Frigate** (on the **NAS** iGPU, or Mac mini + Coral) if you want better camera AI than UniFi's built-in detection. (Paperless/Tdarr/Frigate/Dependency-Track ride the NAS per Section 0's capacity note.)
15. **Harden it:** turn on **MFA/2FA** everywhere (hardware key on Bitwarden/Proton/DSM), set **Docker log rotation**, add **immutable backups** (B2 Object Lock for the off-site immutable copy; optional server-side append-only Borg as future hardening) and a **Healthchecks.io** dead-man's-switch, and put **CrowdSec/forward-auth** on the seedbox + any public ports.
16. Push all compose files + configs to **Git** so the whole thing is rebuildable.
17. **Stand up the inventory/SBOM layer (Section 8):** self-host the control repo (**Forgejo**), turn on **etckeeper** + **chezmoi** (which carries your `~/.ssh/config` + key) + the nightly **Syft** manifest/SBOM job on each host, commit the **`ansible/`** fleet-maintenance playbooks (patch/reboot/audit) to the control repo, stand up **Dependency-Track v5** on the **NAS** (RAM headroom; see Section 0), encrypt secrets with **SOPS + age**, and write + drill the per-host **restore runbooks**. Now you can see what's installed everywhere, get told the moment any of it goes vulnerable, run maintenance across the fleet in one command, and rebuild a wiped box in an hour.

**Phase 5 — Play**
18. **Game servers:** LinuxGSM or Pelican — light games always-on on the Mac mini, heavy games on-demand on the rig, friends in via Tailscale. See [game-servers-guide.md](game-servers-guide.md) for per-title feasibility and host assignment.
19. **Sunshine** on the rig + **Moonlight** clients; set up the **headless display** (dummy HDMI plug or the Apollo-Linux/`sunshine_virt_display` virtual display) and confirm Tailscale shows "direct" for remote streaming. Add a **launcher** (Heroic/Lutris, + RomM for retro) and **Ludusavi + Syncthing** save-sync.
20. **Tune the rig:** Wake-on-LAN, auto-suspend, GPU idle/undervolt, and set the **GPU contention policy** (Ollama `keep_alive=0`) so streaming, servers, and AI share the one card. Optionally add **ComfyUI / Continue / Open WebUI RAG** behind LiteLLM.

---

## Cheap local sensor shopping list

Grounded picks for the Zigbee backbone in Section 3 — all pair cleanly with **Zigbee2MQTT/ZHA**, need **no vendor hub**, and run fully local. Street prices as of mid-2026 (USD); links go to the manufacturers. Buy the **Sonoff SNZB-P** line for the best price/reliability; **Aqara** is the premium alternative; **Third Reality** is good for plugs and the siren leak sensor.

### Start here — the coordinator (buy one)
| Item | Why | ~Price | Link |
|---|---|---|---|
| **Sonoff Zigbee 3.0 USB Dongle Plus-E** | Most-recommended 2026 coordinator (CC2652P); ZHA + Z2M. Use a short USB-2 extension. | ~$20 | [itead.cc](https://itead.cc/product/sonoff-zigbee-3-0-usb-dongle-plus/) |
| **Home Assistant Connect ZBT-2** | Official HA coordinator; zero-fuss if you want first-party. | ~$25 | [home-assistant.io](https://www.home-assistant.io/connectzbt1/) |

### Sensors (mix and match)
| Sensor | Type | ~Price | Battery | Link |
|---|---|---|---|---|
| **Sonoff SNZB-03P** | Motion (PIR, light sensor, ~5s re-trigger) | ~$11-13 | CR2477 | [sonoff.tech](https://sonoff.tech/product/gateway-and-sensors/snzb-03p/) |
| **Aqara Motion Sensor P1** | Motion, premium (adjustable sensitivity) | ~$20-25 | CR2450 | [aqara.com](https://www.aqara.com/en/product/motion-sensor-p1/) |
| **Sonoff SNZB-04P** | Door/window contact (tamper) | ~$13-15 | CR2477 | [sonoff.tech](https://sonoff.tech/product/gateway-and-sensors/snzb-04p/) |
| **Aqara Door & Window Sensor** | Contact, premium | ~$10-15 | CR1632 | [aqara.com](https://www.aqara.com/en/product/door-and-window-sensor/) |
| **Sonoff SNZB-02D** | Temp/humidity with LCD | ~$10-13 | CR2477 | [sonoff.tech](https://sonoff.tech/product/gateway-and-sensors/snzb-02d/) |
| **Third Reality 3RTHS24BZ** | Temp/humidity with e-ink screen | ~$15-18 | AAA | [3reality.com](https://3reality.com/product/temperature-and-humidity-sensor-lite/) |
| **Sonoff SNZB-05P** | Water-leak (detects 0.5mm film) | ~$10-16 | CR2477 | [sonoff.tech](https://sonoff.tech/product/gateway-and-sensors/snzb-05p/) |
| **Third Reality Water Leak Sensor** | Water-leak with **120dB siren** (alerts even if HA is down) | ~$15-20 | AAA | [3reality.com](https://3reality.com/product/water-leak-sensor/) |
| **Aqara Wireless Mini Switch** | Button (single/double/long press scenes) | ~$18 | CR2032 | [aqara.com](https://www.aqara.com/en/product/wireless-mini-switch/) |
| **Sonoff SNZB-06P** *(stretch)* | mmWave presence (occupancy, not just motion) | ~$25 | USB-C | [sonoff.tech](https://sonoff.tech/product/gateway-and-sensors/snzb-06p/) |
| **Third Reality Zigbee Smart Plug** | Smart plug **+ energy reporting + Zigbee router** | ~$13 | mains | [3reality.com](https://3reality.com/product/smart-plug/) |

> **Mesh tip:** every mains-powered device (smart plug) is also a Zigbee **router** — spread **5-7** around the house for a stable mesh. Pair devices *near* the coordinator first, then move them. **Avoid Aqara-branded hubs** if you mix brands (they often restrict pairing to Aqara). A solid starter kit: 1 coordinator + 2 smart plugs (routers) + 2 motion + 3 contact + 2 leak + 1 temp/humidity ≈ **$150-180**.

---

## The stack at a glance

| Apple/iOS task | FOSS replacement | Runs on |
|---|---|---|
| iCloud Photos | **Immich** | NAS |
| Camera (RAW) photo import | **immich-go** / **pbak** | desktop -> NAS |
| Apple Music (own files) | **Navidrome** (+ Symfonium/Amperfy) | Ubuntu/NAS |
| iPod sync | **Rhythmbox / libgpod** (Apple firmware) | device |
| Apple Podcasts | **gPodder** (+ optional sync server) | desktop |
| Apple News / RSS | **Miniflux** (or FreshRSS) + Wallabag | Ubuntu |
| Kindle/iBooks | **Calibre + CWA + KOReader (Kobo) + Syncthing** | NAS + device |
| Apple Notes | **Obsidian + Obsidian Sync** (paid, official) | desktop |
| iWork / MS Office | **LibreOffice** (or OnlyOffice/Collabora) | CachyOS |
| Plex / TV | **Plex** (keeping; Jellyfin = FOSS fallback) | NAS |
| Plex stats & monitoring | **Tautulli** | Mac mini |
| Library polish (collections/overlays) | **Kometa** | Mac mini |
| Quality profiles / extraction | **Recyclarr** + **Unpackerr** | seedbox |
| Library pruning | **Maintainerr** | Mac mini |
| Pre-transcode automation | **Tdarr** (node on rig) / FileFlows | NAS + rig |
| YouTube / web video archive | **Pinchflat** (Tube Archivist / MeTube alt) | NAS / Ubuntu |
| Private media acquisition | **Managed seedbox** (qBit + *arr) + **Seerr** | off-site + Mac mini |
| Automated music acquisition | **Lidarr** + **slskd** + **Soularr** | off-site (seedbox) |
| Documents (scan/OCR/search) | **Paperless-ngx** | NAS |
| Recipes & meal planning | **Mealie** | Mac mini |
| Passwords | **Bitwarden** (Vaultwarden if self-hosting) | cloud / optional self-host |
| iCloud Drive/Contacts/Calendar | **Proton** or **Nextcloud** or **Syncthing + Baikal** | cloud/NAS |
| Safari | **Firefox / LibreWolf / Zen** + Kagi | CachyOS |
| Siri / smart home (Hue, Nest, Midea) | **Home Assistant** + local voice (Whisper/Piper + Ollama) | HA Green (purchased) |
| Local sensors | **Zigbee2MQTT + Mosquitto** (+ USB coordinator) | HA |
| Cameras / NVR AI | **UniFi Protect -> HA** (+ optional **Frigate**) | Dream Wall / HA (Frigate on NAS iGPU or Mac mini+Coral) |
| Apple Home compatibility | **HA HomeKit Bridge** | HA |
| Local AI gateway / fallback | **LiteLLM** (+ small always-on model) | Mac mini + rig |
| Image gen / coding AI | **ComfyUI** / **Continue** / **Aider** | CachyOS rig |
| GeForce Now / game streaming | **Sunshine + Moonlight** (+ virtual display) | rig (host) + clients |
| Game launcher / retro | **Heroic / Lutris** + **RomM** | rig / Mac mini |
| Save-game sync | **Ludusavi + Syncthing** | rig + clients |
| Hosting game servers | **Pelican** / LinuxGSM | Mac mini / rig |
| Remote access | **Tailscale** | all |
| SSH / fleet maintenance | **Tailscale SSH** + **~/.ssh/config** + **Ansible** | all hosts |
| Network segmentation | **UniFi VLANs + Zone-Based Firewall** | Dream Wall |
| Ad/tracker DNS | **Pi-hole / AdGuard Home** (+ Unbound/DoT) | Ubuntu / HA |
| Auth / MFA for exposed apps | **CrowdSec** + forward-auth (Pocket-ID/Authelia) | seedbox / Ubuntu |
| Backup monitoring | **Healthchecks.io** (dead-man's-switch) | Mac mini |
| Container mgmt | **Dockhand** / Dockge / Komodo | Ubuntu |
| Self-hosted app deployment | **Caddy-fronted Compose stacks** (optional **Coolify**/Dokploy behind Caddy) | Mac mini (Ubuntu) |
| Dashboard / service launcher | **Homepage** (Homarr if multi-user) | Ubuntu |
| Monitoring | **Beszel** + Uptime Kuma + ntfy | Ubuntu |
| Backup | **Restic/Kopia** + Borg + Synology native | NAS + hosts |
| SBOM / vuln inventory dashboard | **OWASP Dependency-Track v5** (+ **Syft**/Grype) | NAS |
| Config/dotfile/state-in-Git | **etckeeper** (/etc) + **chezmoi** (~) + **Forgejo** control repo | all hosts |
| Fleet provisioning / convergence | **Ansible** (`ansible-pull` + roles, SOPS-integrated) | control repo -> rig + Mac mini (+ seedbox user-space) |
| Secrets at rest | **SOPS + age** (chezmoi age for dotfiles) | control repo |
| Local LLM | **Ollama** + Open WebUI | CachyOS rig (on-demand) |

Already in your stack and worth keeping: **Kagi** (search), **ProtonMail/VPN/Drive/Calendar/Pass**, and **Plex** (lifetime pass — staying put; Jellyfin is the FOSS fallback only if Plex ever paywalls something you depend on).

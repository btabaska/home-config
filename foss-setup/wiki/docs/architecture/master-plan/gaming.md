# 4. Game servers and game streaming

Two different things: **hosting servers** so friends can join, and **streaming your rig's games** to your own screens.

## Hosting servers for friends

Pick by how much you want to manage:

- **LinuxGSM** — command-line manager with install scripts for 100+ games. Lightest, no web UI.
- **Pelican Panel** — modern, container-native game-server panel (community fork by former Pterodactyl contributors). Panel + "Wings" agent; game definitions ("eggs") are JSON.
- **Pterodactyl** — the established panel Pelican forks from. **Crafty Controller** — simpler, Minecraft-focused.
- **AMP (AMPACHE/CubeCoders)** — a licensed panel; **this is what actually runs the heavy servers live** (see below).

> **Design decision — don't run a dedicated general-purpose panel (Pelican/Pterodactyl) at this scale** (from the 2026-07-08 `game-hosting-design` doc, still current). A game panel's main value is *provisioning servers on demand* — which duplicates what Compose already gives you for a handful of servers, while adding a database, a daemon, and its own auth surface for little gain. Pelican was also still pre-1.0 at the time. So the plan chose plain **pinned-image Compose per game** (the same one-service-per-box pattern as the rest of the fleet), managed with the tooling already in place, and to **revisit a panel only at 5+ servers or if friends should self-provision**. (`AMP` ended up as the Minecraft host anyway for its Java-server ergonomics — but as a single-instance runner, not a fleet provisioning panel.) *Live-state caveat: the rig's game stacks live as separate per-service dirs (`/opt/stacks/{amp,palworld,playit}`), not one `/opt/stacks/games/` project, and the rig is **not** enrolled in the mini's Dockge — so on the rig they're managed directly, not through a panel.*

**Where to run them:** the 8 GB Mac mini already carries the always-on web stack, so it hosts **at most one light always-on server** (a single Minecraft (Paper) or Terraria). **Everything else runs on the CachyOS rig (24/7).**

> **⚠️ Corrected — how servers actually run and are exposed (validated live):**
>
> - **Heavy servers run via AMP on the rig, not LinuxGSM on the mini.** `game-01` (LinuxGSM) is **superseded**. AMP hosts **Minecraft (Java + Bedrock via a cross-play setup)** and **Palworld** 24/7 on the rig, protocol-ping verified (`game-02`/`game-03` closed). Palworld runs with `COMMUNITY=false` to avoid a home-IP leak.
> - **Friends connect via playit premium, not Tailscale.** `game-04` (Tailscale-expose) is **superseded**. Exposure uses **playit premium** (dedicated IP + NS-delegated domains), giving friends a plain address without inviting them to the tailnet or opening router ports to a home IP.

**Exposing them safely (the general principle the plan stated):**

- **Friends-only co-op → Tailscale** *(plan's original default; superseded by playit for these servers)*. Invite friends to the tailnet or share just the server node. No ports open, encrypted.
- **Public / many players → careful port-forward or a tunnel.** Forward only the specific game ports, keep the host patched, and consider a game-server tunnel (**Playit.gg** — the chosen path) to avoid exposing your IP. Keep servers on Trusted (or a dedicated server VLAN if you get serious), not IoT.

## Streaming your rig to your own screens (Sunshine + Moonlight)

Replaces NVIDIA's discontinued GameStream and beats GeForce Now / Xbox Cloud for self-hosters — the 3090 Ti's NVENC does 4K/120 with HDR, free.

- **Host:** install **Sunshine** on the rig (NVENC). Start on boot; set a username/password on its web UI.
- **Clients:** **Moonlight** on laptops, Steam Deck, Apple TV, phone, or TV.
- **In-home:** keep host and clients on the **same (Trusted) VLAN** so Moonlight auto-discovers via mDNS with no inter-VLAN hop. Wire host + the client near the TV. This is exactly why a "streaming VLAN" is wrong — it breaks discovery and adds latency. **Live:** in-home streaming works (`game-06` done).
- **Remote → Tailscale.** Add the host in Moonlight by its Tailscale IP (100.x.x.x) — auto-discovery doesn't work over Tailscale L3. **Critical tuning:** ensure a *direct* connection, not a DERP relay (relays are throughput-limited). Run `tailscale status`, confirm "direct"; if relayed, forward **UDP 41641** on the Dream Wall to the host so hole-punching succeeds. **Live:** remote direct streaming confirmed (`game-07` done).
- **Always ready:** the rig runs 24/7, so a Moonlight session connects immediately — no wake step. WoL stays in BIOS as recovery only.
- *Handhelds:* the **Apollo** (Sunshine fork) + **Artemis** (Moonlight fork) pair adds touchscreen/keyboard niceties on Android; otherwise stock is more stable.

### The headless-display gotcha (and the fix you already have)

Sunshine can only capture an **active** display at the client's resolution — with no monitor (or one asleep) there's nothing to encode, the most common headless failure. Three options, easiest first:

- **Dummy HDMI plug (you own one) — simplest, most reliable.** The GPU sees a "monitor"; Sunshine captures it. Zero software.
- **Software virtual display on CachyOS (no dongle).** **`MrOz59/Apollo-Linux`** (Apollo fork adding **EVDI**-based virtual displays — `evdi-dkms`, auto-matches client resolution/HDR, works on NVIDIA) or **`frostplexx/sunshine_virt_display`** (systemd daemon, EDID-override virtual display on connect). Either gives a true headless, resolution-matching session — handy since the always-on rig runs headless.
- **Audio:** with no real display there's often no audio sink — add a **PipeWire virtual sink** (or the dummy plug's audio device) so Sunshine has something to capture.

### Save-game sync (Steam Cloud for everything)

Server worlds are backed up (Backup), but single-player PC saves on the rig aren't synced to the Deck/laptop. **Ludusavi** (save locations for 19k+ titles) pointed at a **Syncthing** folder is the de-facto self-hosted save-sync. **Status:** `game-12` was un-deferred and folds into the tracked **Syncthing hub** task.

### One GPU, three jobs — a contention policy

The 3090 Ti hosts Sunshine streaming, heavy game servers, **and** Ollama inference. A model resident in VRAM steals from a game (and vice-versa), so set an explicit rule: run Ollama with **`keep_alive=0`** (unload the model when a request finishes) or **don't run inference during a stream/game session**. *(Note: the plan says "the LiteLLM fallback makes this painless" — LiteLLM is retired, so the discipline is just the `keep_alive=0` policy plus not inferring during a session; there is no always-on mini fallback model.)*

### Make the streamed library usable — a launcher

Add a **launcher** so the couch experience covers more than Steam: **Heroic** (GOG/Epic/Amazon) or **Lutris** on CachyOS, surfaced through Sunshine or Steam Big Picture. *Retro:* **RomM** ("Plex for ROMs" — metadata scraping, web UI with in-browser EmulatorJS, Playnite/RetroArch/Deck integration) — **live on the mini** (pinned `4.9.2`). **Status:** the launcher (`game-14`) is **deferred** as a bundle, though RomM itself is already running.

## Local AI beyond chat (the rig's other job)

Ollama + Open WebUI give local chat. Cheap extensions, all on the always-on rig:

- **Image generation — ComfyUI** (or Stable Diffusion / A1111).
- **Coding assistant — Continue (VS Code/JetBrains) or Aider (CLI)** pointed at the local endpoint.
- **Chat with your own docs — Open WebUI RAG:** point it at the Obsidian vault / Paperless docs.

*(The local-AI build has since been expanded into its own first-class initiative — see the `architecture/local-ai-build` page. It targets llama.cpp/Ollama GGUF, keeps model choice > size, and validates GPU-coexistence with gaming.)*

---
[← index](index.md)

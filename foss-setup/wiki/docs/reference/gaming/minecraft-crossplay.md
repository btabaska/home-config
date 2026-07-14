# Minecraft crossplay finish

> Source-of-truth reference for the live Java + Bedrock crossplay Minecraft server (Paper + Geyser/Floodgate on the rig), including how to connect, public playit.gg routing, and the hard-won AMP/Java operational notes.

_Source: `foss-setup/configs/gaming/minecraft-crossplay-finish.md` · migrated + validated 2026-07-14._

The server is **up and verified** (live re-checked 2026-07-14): Paper **26.1.2** on Temurin **25** (`Temurin-25.0.3+9-LTS`), Geyser **2.10.1** on UDP 19132, Floodgate **2.2.5** enabled. Java TCP 25565 is open on the rig and a real Bedrock RakNet pong was verified from the mini. Kuma monitor "Rig Minecraft Java" (Uptime Kuma on the mini) watches 25565.

## How to connect

LAN:

- **Java**: `192.168.10.12:25565` · **Bedrock**: `192.168.10.12` port `19132`

Public (playit.gg **premium** tunnels on dedicated IP `69.9.181.17` + **external domains** NS-delegated to playit-dns; agent on the rig at `/opt/stacks/playit`):

| Game | Address | Notes |
|------|---------|-------|
| **Java** | `minecraft.tabaska.us` (no port) | playit-dns serves A=`69.9.181.17` + SRV `_minecraft._tcp` → `:1105` (verified with a real status ping). LAN path: AdGuard exact rewrite → `192.168.10.12` direct, plus a filter rule blocking that SRV name on both resolvers so home clients fall back to A:25565 (otherwise the public SRV's `:1105` would point them at a dead rig port). `filter-unthawed.nyc.mcjoin.link` also still works. |
| **Palworld** | `palworld.tabaska.us:1105` | LAN rewrite points at `69.9.181.17` (NOT the rig) so the same address+port works everywhere; LAN-direct would need `:8211` and a different address — not worth the confusion. |
| **Bedrock** | `bedrock.tabaska.us` port `1111` | = `69.9.181.17:1111`; NS-delegated like the others. Bedrock ignores SRV so the port must still be typed. `fun-diamonds.nyc.at.playit.plus:1111` also still works. LAN rewrite → `69.9.181.17` (same everywhere-address reasoning as Palworld). |

- **Cloudflare**: 6 NS records (`minecraft` / `palworld` / `bedrock.tabaska.us` → `ns1`/`ns2.playit-dns.com`). playit-dns answers everything under those three names — manage them in the playit dashboard, not Cloudflare.
- **Agent secret**: vault `playit_gg.secret_key`. Premium allows 16 TCP + 16 UDP tunnels on the same agent (agent API key is read-only; tunnel creation is dashboard-only). OLD free addresses (`analysis-conditioning.gl.joinmc.link`, `stop-spain.gl.at.ply.gg`) are **DEAD** — tunnels were recreated for paid routing.
- **Switch / consoles**: BedrockConnect runs on the mini (`bedrock-connect` container, LIVE + healthy); its "Remote/playit" list entry points at the new Bedrock address.

!!! warning "Gotcha (2026-07-09) — UDP tunnel claim"
    Right after recreating tunnels the agent flapped `tunnel_count` 2↔3 and the Bedrock UDP tunnel didn't route (timeouts) even once "loaded". Fix: restart the playit container **AFTER** the dashboard shows all tunnels assigned — the UDP claim only establishes cleanly on a fresh connect. Verify with a RakNet ping, not the dashboard status.

!!! note "Sleep mode is OFF (`Limits.SleepMode=False`)"
    AMP's empty-server sleep (5 min) stopped the app, and its wake listener only speaks Java protocol on 25565 — Bedrock/Geyser was dark while asleep and Bedrock joins could never wake it. The rig is 24/7 so the server just stays up. Gotcha: when asleep, AMP answers Java status pings itself ("Powered by AMP" MOTD) — a Java ping is NOT proof the actual server is running.

## Architecture / operational notes (hard-won, don't relearn)

- **Instance**: internal name **MinecraftCross01** (friendly "MinecraftCross"), ADS-managed, in the `amp` container on the rig (`/opt/stacks/amp`). Instance data lives at `/config/.ampdata/instances/MinecraftCross01/`. Both Main (panel) and MinecraftCross01 have the ampinstmgr **start-on-boot flag** set — a rig reboot brings everything back (this was the cause of the 2026-07-09 "white screen": Main had no boot flag). Live check 2026-07-14: both Main and MinecraftCross01 show Up.
- **CLI works as the `abc` user**: `docker exec -u abc amp ampinstmgr …`. The old "CLI is blocked (BusyBox su)" finding only applies to root exec. `CreateInstance` accepts the licence key as an argument — the "first instance must be born in the UI" claim is obsolete. (AMP Instance Manager is v2.6.0.6.)
- `ampinstmgr` refuses `SetStartBoot` / `RebindInstance` / `CreateInstance` while ADS runs → stop Main briefly for those.
- **Licence is machine-id-bound**: the container hostname is pinned in compose (`hostname: c5f46f35aee3`). If it ever changes: `docker exec -u abc amp ampinstmgr reactivate MinecraftCross01 <licence-key>` (vault `cubecoders_amp.license_key`).
- **Java**: the Alpine image ships none. `openjdk21` via `INSTALL_PACKAGES` env (persists through recreates); **Minecraft 26.x needs Java 25** = Temurin musl JRE persisted at `/config/java/jdk-25.0.3+9-jre`, fronted by `/config/java/java25-paperfix.sh` which strips the `--log-strip-color` flag (the AMP Minecraft module passes it; Paper 26.x removed it). The instance setting `Java.JavaVersion` points at the wrapper (`Java.JavaVersion=/config/java/java25-paperfix.sh`, confirmed live).
- **Version pin**: `Minecraft.SpecificPaperVersion=26.1.2` (confirmed live). Geyser latest (2.10.1) does NOT support MC 26.2 yet (reflection crash on enable) — check Geyser compatibility before bumping Paper. AMP's own manifest offered only 26.2-rc-2 as "stable"; real Paper versions come from `https://fill.papermc.io/v3/projects/paper` (api v2 is sunset).
- **Plugins** installed as jars in `/config/.ampdata/instances/MinecraftCross01/Minecraft/plugins/` (`Geyser-Spigot.jar`, `floodgate-spigot.jar`) from `https://download.geysermc.org/v2/projects/{geyser|floodgate}/versions/latest/builds/latest/downloads/spigot`.
- **Instance auth is ADS-delegated** (`ResetLogin` refuses). API access: login at `/API/Core/Login` on `amp.tabaska.us` with panel creds, then proxy calls via `/API/ADSModule/Servers/{instanceId}/API/…` — do a proxied `Core/Login` first to get an instance `SESSIONID`.
- `.mc-admin-password` on the rig is unused (instance auth = panel creds).

## Still open

- **Whitelist**: user decided OFF (2026-07-09) — mitigation is AMP hourly backups (retention 28) + sticky baseline + rig restic nightly. Flip on only if a stranger ever joins.
- Geyser auth-mode tuning for Floodgate-linked accounts, if ever wanted.
- An AMP Minecraft-module update will eventually make the java25 wrapper unnecessary — retest with the plain Temurin path after the module updates past the version that still passes `--log-strip-color`. _(The source cited "module 2.8"; the exact installed module version was not cheaply verifiable during migration.)_

BedrockConnect: DONE, live on the mini. Friendly DNS: DONE — `minecraft` / `palworld` / `bedrock.tabaska.us` via playit-dns delegation.

---
[← Gaming reference](index.md)

# Minecraft crossplay (Java + Bedrock) — LIVE 2026-07-09

The server is **up and verified**: Paper 26.1.2 on Temurin 25, Geyser on UDP
19132, Floodgate enabled. Java TCP 25565 and a real Bedrock RakNet pong were
both verified from the mini. Kuma monitor "Rig Minecraft Java" watches 25565.

## How to connect
LAN:
- **Java**: `192.168.10.12:25565` · **Bedrock**: `192.168.10.12` port `19132`

Public (playit.gg tunnels via agent on the rig, /opt/stacks/playit — home IP
never exposed, no Dream Wall port-forwards; both verified 2026-07-09):
- **Java**: `analysis-conditioning.gl.joinmc.link:14450` (joinmc.link has SRV —
  most clients can omit the port)
- **Bedrock**: `stop-spain.gl.at.ply.gg` port `58804`
- Agent secret: vault `playit_gg.secret_key`. Account allows 4 TCP + 4 UDP
  tunnels — add Palworld etc. as more tunnels on the SAME agent (dashboard;
  the agent key is read-only via API, creation is dashboard/account-auth only).
- **Switch / consoles**: still need BedrockConnect (can't type an address) —
  decision open (self-host on mini). See todo-guide.

**Sleep mode is OFF** (`Limits.SleepMode=False`): AMP's empty-server sleep
(5 min) stopped the app and its wake listener only speaks Java protocol on
25565 — Bedrock/Geyser was dark while asleep and Bedrock joins could never
wake it. Rig is 24/7 so the server just stays up. Gotcha: when asleep, AMP
answers Java status pings itself ("Powered by AMP" MOTD) — a Java ping is NOT
proof the actual server is running.

## Architecture / operational notes (hard-won, don't relearn)
- Instance: internal name **MinecraftCross01** (friendly "MinecraftCross"),
  ADS-managed, in the `amp` container on the rig (`/opt/stacks/amp`).
  Both Main (panel) and MinecraftCross01 have the ampinstmgr **start-on-boot
  flag** set — a rig reboot brings everything back (this was the cause of the
  2026-07-09 "white screen": Main had no boot flag).
- **CLI works as the `abc` user**: `docker exec -u abc amp ampinstmgr …`.
  The old "CLI is blocked (BusyBox su)" finding only applies to root exec.
  CreateInstance accepts the licence key as an argument — the "first instance
  must be born in the UI" claim is obsolete.
- `ampinstmgr` refuses SetStartBoot / RebindInstance / CreateInstance while
  ADS runs → stop Main briefly for those.
- **Licence is machine-id-bound**: container hostname is now pinned in compose.
  If it ever changes: `docker exec -u abc amp ampinstmgr reactivate
  MinecraftCross01 <licence-key>` (vault cubecoders_amp.license_key).
- **Java**: Alpine image ships none. openjdk21 via INSTALL_PACKAGES env
  (persists through recreates); **Minecraft 26.x needs Java 25** = Temurin
  musl JRE persisted at `/config/java/jdk-25.0.3+9-jre`, fronted by
  `/config/java/java25-paperfix.sh` which strips the `--log-strip-color`
  flag (AMP module 2.8 passes it; Paper 26.x removed it). The instance
  setting `Java.JavaVersion` points at the wrapper.
- **Version pin**: `Minecraft.SpecificPaperVersion=26.1.2`. Geyser latest
  (2.10.1) does NOT support MC 26.2 yet (reflection crash on enable) — check
  Geyser compatibility before bumping Paper. AMP's own manifest offered only
  26.2-rc-2 as "stable"; real Paper versions come from
  `https://fill.papermc.io/v3/projects/paper` (api v2 is sunset).
- **Plugins** installed as jars in `…/MinecraftCross01/Minecraft/plugins/`
  (Geyser-Spigot.jar, floodgate-spigot.jar) from
  `https://download.geysermc.org/v2/projects/{geyser|floodgate}/versions/latest/builds/latest/downloads/spigot`.
- **Instance auth is ADS-delegated** (ResetLogin refuses). API access: login
  at `/API/Core/Login` on amp.tabaska.us with panel creds, then proxy calls
  via `/API/ADSModule/Servers/{instanceId}/API/…` — do a proxied Core/Login
  first to get an instance SESSIONID.
- `.mc-admin-password` on the rig is unused (instance auth = panel creds).

## Still open
- Switch 2: BedrockConnect self-host (user decision) + Geyser auth-mode tuning
  for Floodgate-linked accounts if wanted.
- `mc.tabaska.us` friendly DNS (user decision).
- Whitelist: off by default — decide before handing the address to friends.
- AMP module update will eventually make the java25 wrapper unnecessary —
  retest with plain Temurin path after AMP updates past module 2.8.

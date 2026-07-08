# Minecraft crossplay (Java + Switch 2 Bedrock) — finish steps

AMP is deployed and healthy at https://amp.tabaska.us. Everything around the
server is prepared (firewall ports open, panel licensed). The first instance must
be created through AMP's **web UI**, because this minimal AMP container can't
create instances via the CLI (BusyBox `su` incompatibility) and the API needs the
deployment licence set in the UI first. Once the instance exists, I can take back
over to install/configure Geyser + Floodgate and test — or you can follow it all
here. Total UI time: ~5 minutes.

## Already done for you
- AMP panel live, licensed (Advanced Lifetime), real cert, on the dashboard.
- Rig firewall open: **25565/tcp** (Java) and **19132/udp** (Bedrock/Geyser) from LAN + tailnet.
- Instance admin password pre-generated at `rig:/opt/stacks/amp/.mc-admin-password`.

## Step 1 — set the deployment licence key (one-time, unblocks instance creation)
AMP → **Configuration → Instance Deployment → Deployment Defaults → Licence Key** →
paste your AMP licence (vault `cubecoders_amp.license_key`) → Save. This is the
only reason the automated create failed; AMP needs it to license child instances.

## Step 2 — create the Minecraft instance
AMP home → **Create Instance** → Application: **Minecraft Java Edition** →
Name `MinecraftCross` → Port 25565 → Create. When it's made, **Manage** it and in
its Configuration set the server type to **Paper** (Geyser/Floodgate are Spigot
plugins and need Paper/Spigot, not Vanilla), then **Update/Install** and **Start**.

## Step 3 — crossplay: Geyser + Floodgate
In the instance's **Plugins** (or File Manager → `plugins/`):
- **Geyser-Spigot** — lets Bedrock clients (Switch, phones, consoles) join your Java world.
- **Floodgate** — lets those Bedrock players in *without* a paid Java account (linked or `.`-prefixed usernames).

AMP's Minecraft module has a plugin browser (installs from Modrinth/Spiget) — search
"Geyser" and "Floodgate", install both, restart. Geyser defaults to Bedrock UDP
**19132** (already open). Defaults work; no config needed for LAN play. Tell me once
they're installed and I'll verify the handshake and tune `config.yml` (auth mode,
MOTD, port) + wire the player-count monitor into ntfy/Uptime Kuma.

## Step 4 — connect the Switch 2
Bedrock on consoles can't type a custom server IP in the UI, so two paths:
- **On your LAN (simplest):** the Switch's Minecraft "Friends/LAN" or a featured-server
  entry via a DNS redirect. The reliable console method is **BedrockConnect**: set the
  Switch's DNS (System Settings → Internet → your network → DNS → Manual) to a
  BedrockConnect resolver, open Minecraft → Play → Servers (featured), and it shows a
  "connect to server" tile where you enter the rig's IP `192.168.10.12` port `19132`.
  You can self-host BedrockConnect (tiny container) so no third-party DNS is involved —
  say the word and I'll stand it up on the mini.
- **PC/phone Bedrock clients** can enter `192.168.10.12:19132` directly (no BedrockConnect needed).

## Notes
- Java players connect to `192.168.10.12:25565` (or a `mc.tabaska.us` A record if you want a friendly name — I can add it in Cloudflare).
- Whitelist/allowlist: decide if you want the server whitelisted; I can enable it and add your accounts.
- Friends off-LAN: Tailscale share (PC) or a playit.gg tunnel for the Bedrock UDP port (consoles) — the game-hosting design doc covers this.

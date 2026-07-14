# LinuxGSM quickstart

> How to stand up and run a single light co-op game server with LinuxGSM on the Mac mini (Ubuntu).
_Source: `foss-setup/scripts/gaming/linuxgsm-quickstart.md` · migrated + validated 2026-07-14._

LinuxGSM is a CLI tool for deploying/managing 100+ Linux dedicated game servers.
It is the lightest option and a great fit for a terminal-comfortable operator.

**One LinuxGSM instance = one game server**, run under its **own dedicated user**.

!!! warning "Status & capacity — read before deploying"
    The Mac mini has **8 GB soldered RAM** and is already the busy always-on
    web/management hub (Caddy, primary DNS, Forgejo, ~38 containers, BedrockConnect).
    Its capacity rule is **at most ONE light always-on game server** — not a fleet.
    The original task to install multiple LinuxGSM co-op servers on the mini
    (`game-01`) was **retired**; today the mini's single game slot runs only
    BedrockConnect (a Bedrock redirect helper), so the light-server slot is still
    open but **no LinuxGSM server is deployed yet**. Check `free -m` before you add
    one. Heavy/modded servers (Palworld, ARK) do **not** belong here — those run on
    the CachyOS rig.

**Authoritative docs**

- Getting Started: <https://docs.linuxgsm.com/getting-started>
- Install command (standard vs auto-install): <https://docs.linuxgsm.com/commands/install>
- Basic usage (start/stop/console/monitor): <https://docs.linuxgsm.com/other/basic-usage>
- Per-game install pages & deps: <https://linuxgsm.com/servers>
- Source: <https://github.com/GameServerManagers/LinuxGSM>

---

## 1. Create a dedicated user (security best practice)

Each server gets its own user named after the gameserver script. Example for a
Valheim server (`vhserver`):

```bash
sudo adduser vhserver          # set a strong password
sudo su - vhserver             # become that user
```

> Find the exact gameserver script name for your game on its
> [linuxgsm.com](https://linuxgsm.com/servers) page (e.g. `mcserver`,
> `vhserver`, `tsserver`, `fctrserver`, `pzserver`, `corekeeperserver`).

## 2. Download LinuxGSM + the game installer (as that user)

```bash
curl -Lo linuxgsm.sh https://linuxgsm.sh && chmod +x linuxgsm.sh && bash linuxgsm.sh vhserver
```

This creates the `vhserver` management script in the home directory.

## 3. Install the server

```bash
./vhserver install        # interactive; follow on-screen prompts
# or, for unattended deploys:
./vhserver auto-install    # ai — skips prompts
```

The installer creates directories, installs/advises on **dependencies** (needs
`sudo` or root to auto-install them), downloads the server files, and applies any
fixes. If you hit dependency errors, see the install doc above.

## 4. Configure

Edit the instance config (LinuxGSM splits config into `_default.cfg` /
`_common.cfg` and your editable `<gameserver>.cfg`). Set server name, password,
world, ports, max players, etc. Example path:

```
~/lgsm/config-lgsm/vhserver/vhserver.cfg
```

See: <https://docs.linuxgsm.com/configuration> (and per-game start parameters).

## 5. Start / manage

```bash
./vhserver start
./vhserver stop
./vhserver restart
./vhserver details      # shows ports, connect info, query status
./vhserver console      # attach to the live server console (tmux)
./vhserver monitor      # used by cron to auto-restart if it crashes
./vhserver update       # update game server files
./vhserver backup
```

## 6. Keep it always-on

LinuxGSM is designed so `monitor` (via a cron entry) restarts a crashed server.
Add to the gameserver user's crontab, e.g.:

```bash
*/5 * * * * /home/vhserver/vhserver monitor > /dev/null 2>&1
@reboot     /home/vhserver/vhserver start > /dev/null 2>&1
```

---

## 7. Exposing to friends (do NOT blindly port-forward)

- **Friends-only co-op (recommended):** the Mac mini is already on **Tailscale**
  (tailnet node `macmini`, `100.97.245.80`). **Share the node** with each friend's
  Tailscale account (or invite them to your tailnet). They connect to the server
  via its Tailscale `100.x` IP — **no open ports**.
  Share: <https://tailscale.com/docs/features/sharing>
- **Public / many players:** port-forward only the **specific game UDP/TCP port(s)**
  on the UniFi **Dream Wall** to the Mac mini, OR use a **Playit.gg** tunnel. Keep
  the Mac mini on the **Trusted** VLAN — never on IoT.

## 8. Verify

- `./vhserver details` shows the server **running** with the right ports.
- A friend can connect via the Tailscale IP (or forwarded port).
- After a reboot the `@reboot` cron starts it; after a kill, `monitor` restarts it.

---

### Heavy servers note (Palworld / ARK / modded)

These run **on the CachyOS rig**, which is 24/7 as of 2026-07 (WoL /
`wake-rig.sh` is recovery tooling only). On the rig, heavy titles currently run
under **AMP** (Minecraft) and a purpose-built container (Palworld), fronted by a
Playit.gg tunnel — not LinuxGSM. You *can* run heavy servers with LinuxGSM the
same way as above, or use a container-native **managed panel** (e.g. Pelican
Panel + Wings, eggs in Git/GitOps) if you prefer a web UI — note that no such
panel is deployed today.

---
[← Guides](index.md)

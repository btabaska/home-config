# rig — Ludusavi save-game backup → Syncthing mesh (game-12)

"Self-hosted Steam Cloud." [Ludusavi](https://github.com/mtkennerly/ludusavi) scans the
rig's installed games (its bundled manifest knows thousands of save locations), copies each
game's saves into a backup dir, and that dir is a dedicated **Syncthing** folder on the
existing no-cloud `foss-03` mesh — so every backup replicates off-host to the NAS hub and
the mini node automatically. Back up on the rig, and the saves are safe on two other hosts.

> **Documentation-only, not ansible-managed.** These are `--user` systemd units + a user
> config that live only on the rig. `site.yml` never converges them; a live edit that skips
> this dir (or vice-versa) is silent drift. Land every change in both.

## Layout

| Live path on rig | Repo mirror | What |
|---|---|---|
| `~/.local/bin/ludusavi` | *(binary, not mirrored)* | Ludusavi **v0.31.0** prebuilt Linux binary |
| `~/.config/ludusavi/config.yaml` | `config.yaml` | backup path pinned to `~/game-saves` |
| `~/.config/systemd/user/ludusavi-backup.service` | `ludusavi-backup.service` | oneshot `ludusavi backup --force` |
| `~/.config/systemd/user/ludusavi-backup.timer` | `ludusavi-backup.timer` | every 2h + 10min after boot |
| `~/game-saves/` | *(save data, synced)* | Ludusavi backup target = Syncthing folder `game-saves` |

## Install (reproduce)

```sh
# 1. Binary (prebuilt release — no AUR build; paru is available if you prefer the AUR pkg)
cd /tmp
curl -sL -o ludusavi.tar.gz \
  https://github.com/mtkennerly/ludusavi/releases/download/v0.31.0/ludusavi-v0.31.0-linux.tar.gz
tar xzf ludusavi.tar.gz && install -Dm755 ludusavi ~/.local/bin/ludusavi && rm ludusavi*

# 2. Config: backup + restore path -> ~/game-saves (config.yaml auto-generated on first run)
mkdir -p ~/game-saves
sed -i 's#/home/btabaska/ludusavi-backup#/home/btabaska/game-saves#g' ~/.config/ludusavi/config.yaml

# 3. Units (copy the two files from this dir), then:
systemctl --user daemon-reload
systemctl --user enable --now ludusavi-backup.timer   # linger already on for the syncthing --user svc
```

Manual backup / restore:

```sh
ludusavi backup --preview      # dry-run: show what would be captured
ludusavi backup --force        # write a backup into ~/game-saves
ludusavi restore --force       # restore the newest backup onto this machine
ludusavi restore "Game Name"   # restore one game (e.g. after syncing from another host)
```

## Syncthing folder wiring (`game-saves`)

A **dedicated** mesh folder (kept separate from the general `Sync` folder so churny save
data + its versions don't mix with everything else). Wired live via each host's Syncthing
REST API (`PUT /rest/config/folders/game-saves`), matching the `foss-03` hub topology — the
rig peers only with the NAS hub, the mini peers only with the NAS hub, and the hub relays:

| Host | Folder path | Shared with | Versioning |
|---|---|---|---|
| rig (`cachyos`) | `/home/btabaska/game-saves` | nas-hub | none (source) |
| NAS hub | `/volume1/docker/syncthing/game-saves` | rig, mini | **staggered, 30d** (`maxAge=2592000`) |
| mini node | `/opt/stacks/syncthing/home/game-saves` | nas-hub | none |

Same no-cloud posture as the rest of the mesh: global-discovery + relays stay **off**. Old
save versions live on the NAS hub under `game-saves/.stversions/` for 30 days.

## Monitoring

`verification/checks.d/game-saves.yaml` (consumer-end, not liveness):

- **`game-saves-mesh-synced`** (host `nas`) — asks the always-on hub whether the `game-saves`
  folder is fully in sync **and** the rig peer is 100% complete, i.e. the hub actually holds
  every save the rig backed up. "Folder added" is not acceptance; "saves landed off-host" is.
- **`ludusavi-backup-timer-alive`** (host `rig`) — the `--user` timer is active and the last
  run succeeded, so fresh saves keep flowing (a dead timer would freeze the mesh at the last
  known saves while everything still looked green).

Not a container → **not** in `verification/coverage/rig.containers`; covered by the checks
above (same pattern as the rig's other host units, e.g. `nas-music-mirror`).

## Verified (2026-07-28, game-12)

`ludusavi backup --force` captured 4 real installed games (Loop Hero, Nuclear Throne, Selaco,
Slay the Spire 2 — 23 files, 812 KiB) into `~/game-saves`. All 23 files replicated to the NAS
hub **and** the mini node; a Slay the Spire 2 `progress.save` had an **identical SHA256** on
all three hosts. End-to-end self-hosted Steam Cloud proven, not just "installed."

# rig — ES-DE emulation frontend + RetroArch (retro-05)

Canonical, **documentation-only** record of the rig's emulation frontend. Nothing
re-applies it (the rig's `site.yml` converges only base/docker/tailscale/backup/
state — no host-app tasks), so a live edit that skips the repo (or vice-versa) is
silent drift. Land every change in both. Reproducible installer: [`setup.sh`](setup.sh).

## What this is

[ES-DE](https://es-de.org) (EmulationStation Desktop Edition) `3.4.1` + native
**RetroArch** `1.22.x` on the rig (CachyOS `192.168.10.12`), giving the couch/big-
picture browse-and-launch front-end that RomM's Playnite plugin provides on Windows.
On Linux the pair is **RomM web UI (library manager) + ES-DE (launcher)** — and the
key point is they share the **same** ROM files, not a copy:

```
NAS `games` SMB share ── CIFS ──> rig /mnt/share/Games/romm/roms/<slug>/  <── RomM (mini) reads the same
                                        │
                                        └─ symlinked ──> ~/ROMs/<es-de-system>/  <── ES-DE reads
```

RomM (mini `/opt/stacks/romm`, `romm.tabaska.us`) is the metadata/library manager;
ES-DE is a pure launcher over the identical on-disk tree. No second sync, no drift
between the two views of the library.

## ROM directory bridge (ES-DE system name → RomM slug)

ES-DE wants `~/ROMs/<system>/`; RomM stores `roms/<platform-slug>/`. A tree of
per-system **symlinks** into the NAS mount bridges them (created by `setup.sh`).
Only GameCube's name differs (`gc` ↔ `ngc`); the rest are identical:

| ES-DE system | RomM slug | Default emulator (RetroArch core) | ROMs |
|---|---|---|---|
| `gb`   | `gb`   | Gambatte (`gambatte_libretro`)            | 622   |
| `gba`  | `gba`  | mGBA (`mgba_libretro`)                    | 2808  |
| `n64`  | `n64`  | Mupen64Plus-Next (`mupen64plus_next_libretro`) | 299 |
| `nes`  | `nes`  | Mesen (`mesen_libretro`)                  | 3537  |
| `snes` | `snes` | Snes9x (`snes9x_libretro`)                | 786   |
| `gc`   | `ngc`  | Dolphin (`dolphin_libretro`)              | 101   |
| `wii`  | `wii`  | Dolphin (`dolphin_libretro`)              | 177   |

ES-DE's bundled `es_systems.xml` already **defaults** each of these systems to the
core above (verified 2026-07-28), so there is no custom `es_systems.xml` — the stock
launch command is `retroarch -L <core> <ROM>`. Cores install to `/usr/lib/libretro/`.

Symlinks keep ES-DE read-only against the NAS: gamelists, scraped media and config
live locally under `~/ES-DE/`; the share is never written.

### Wii U — deferred

ES-DE's `wiiu` system needs the **Cemu** standalone (AUR) and `.wua`/`.wux`/`.rpx`
ROMs. The 34 files in RomM's `wiiu` slug are `.zip`, which don't match ES-DE's Wii U
extensions, so ES-DE skips the system (loads **7** of 8). Wiring Wii U = install
`cemu` + point the `wiiu` command at it + supply Cemu-format ROMs. Low priority (34
titles).

## Config locations

| What | Path (on the rig, user `btabaska`) |
|---|---|
| ES-DE settings | `~/ES-DE/settings/es_settings.xml` (`ROMDirectory` empty = default `~/ROMs`) |
| Gamelists / scraped media | `~/ES-DE/gamelists/`, `~/ES-DE/downloaded_media/` |
| Bundled themes | `/usr/share/es-de/themes/{linear,modern,slate}-es-de` |
| Stock system defs | `/usr/share/es-de/resources/systems/linux/es_systems.xml` |
| RetroArch cores | `/usr/lib/libretro/*_libretro.so` |
| RetroArch config/saves/states | `~/.config/retroarch/` |
| NAS ROM source | `/mnt/share/Games/romm/roms/<slug>/` (CIFS automount, see `../nas-mounts/`) |

## Verified (retro-05, 2026-07-28)

* **ES-DE enumerates the RomM library** — a first run logged
  `loaded 7 systems … Total game count: 8328` in `~/ES-DE/logs/es_log.txt`,
  i.e. it read the real NAS library through the symlink tree.
* **RetroArch launches a game from that library** — the exact command ES-DE issues,
  `retroarch -L /usr/lib/libretro/mesen_libretro.so ~/ROMs/nes/<title>.nes`, loaded
  the content off the NAS symlink (`[Content] Loading content file …`,
  `SET_PIXEL_FORMAT`, entered the run loop) into the live Plasma Wayland session.

## Monitoring

Consumer-end check **`rig-esde-romm-library`** (`verification/checks.d/retro-emulation.yaml`,
runs on the rig from the mini): asserts es-de is installed, the NAS ROM library is
reachable through `~/ROMs`, the enumerated ROM count is ≳ the known library size, and
all six backing libretro cores are present. ES-DE is a host app, not a container, so
it is **not** in `verification/coverage/rig.containers` (that manifest reconciles
`docker ps`); like `music-mirror`/`ipod-abs-sync` it is covered by this dedicated
check instead.

## Applying (manual — ansible does NOT manage this)

```sh
# on the rig, as btabaska
bash setup.sh          # installs packages + builds the ~/ROMs symlink tree
es-de                  # launch from the graphical (Plasma/Wayland) session
```

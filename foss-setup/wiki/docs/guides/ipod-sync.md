# iPod sync (CachyOS)

> Runbook for syncing an iPod Classic from CachyOS using Apple's stock firmware + libgpod, driven by Rhythmbox (gtkpod as the power-user fallback).
_Source: `foss-setup/scripts/media/ipod-sync-cachyos.md` · migrated + validated 2026-07-14._

**Phase 3.** Sync an iPod Classic from CachyOS (Arch) using **Apple's stock firmware** + **libgpod** tooling, driven by **Rhythmbox** (simplest), with **gtkpod** as the power-user fallback.

**Why stock firmware (decision):** keeping Apple firmware preserves car-stereo / USB-controller integration. Rockbox (drag-and-drop FLAC/Opus) is the *fallback* only if that compatibility stops mattering — see the end.

**Master copy:** the music library master lives on the **NAS** (`/volume1/music`); Navidrome on the mini reads it read-only via `/mnt/nas/music`. The iPod is always a reproducible copy — if its iTunesDB ever gets confused, wipe and re-sync from the master rather than panicking.

Refs:

- ArchWiki iPod: <https://wiki.archlinux.org/title/IPod>
- libgpod: <https://github.com/gtkpod/libgpod>
- Rhythmbox: <https://wiki.gnome.org/Apps/Rhythmbox>

---

## 0. Install the tools

```bash
./install-ipod-tools-cachyos.sh                  # rhythmbox + libgpod
# optional extras:
WITH_GTKPOD=1 ./install-ipod-tools-cachyos.sh    # gtkpod GUI
WITH_HFSPROGS=1 ./install-ipod-tools-cachyos.sh  # only if the iPod is HFS+
```

The installer (`foss-setup/scripts/media/install-ipod-tools-cachyos.sh`) is idempotent (`pacman -S --needed`; AUR steps skip if already present). It installs `rhythmbox` + `libgpod` from the repos; `hfsprogs` comes from the AUR (`paru`/`yay` or manual `makepkg`).

---

## 1. Identify + mount the iPod

1. Plug in the iPod. Find the device + filesystem:

   ```bash
   lsblk -f          # note the partition (e.g. /dev/sdX2) and FSTYPE
   ```

   - **`vfat`** = FAT32 (iPod last initialized on Windows) → easiest on Linux.
   - **`hfsplus`** = HFS+ (initialized on a Mac) → needs `hfsprogs` (AUR) and a `force,rw` mount option.
2. Most desktop environments auto-mount it under `/run/media/$USER/...`. For a stable mount point, add to `/etc/fstab` (ArchWiki example):

   ```fstab
   # FAT32 iPod
   UUID=XXXX-XXXX  /mnt/ipod  vfat      user,noauto,owner            0 0
   # OR HFS+ iPod (needs hfsprogs)
   UUID=XXXX-XXXX  /mnt/ipod  hfsplus   user,noauto,owner,force,rw   0 0
   ```

   ```bash
   sudo mkdir -p /mnt/ipod && mount /mnt/ipod
   ```

> Note: the iPod **Classic** is a USB mass-storage device. Do **not** install `usbmuxd`/`ifuse` — those are for iOS / iPod Touch and are irrelevant (and can confuse detection).

---

## 2. First-time sync prep (the re-init gotcha)

libgpod writes Apple's `iTunesDB`. Two one-time things can be required on a **fresh iPod that has never been used with iTunes**, or after a restore:

### 2a. The database must exist

libgpod can write the DB on supported Classic models, but a never-initialized iPod sometimes needs a first DB created by iTunes once. If Rhythmbox/gtkpod can't read/write the DB:

- Easiest path on Linux: let **gtkpod** initialize it (`gtkpod` → it offers to create the iPod directory structure), **or**
- Initialize once in iTunes/Finder on any Mac/Windows machine (add one song), then return to Linux. (ArchWiki + libgpod README both note this for some models.)

### 2b. FirewireGuid (so libgpod finds the device)

On iPod Classic / Nano 3rd-gen+, libgpod needs the FireWire GUID written into a SysInfo file:

```bash
# 16-char serial, no colons/hyphens:
lsusb -v 2>/dev/null | grep -i Serial
# create/edit on the mounted iPod:
#   /mnt/ipod/iPod_Control/Device/SysInfo
# add this line (keep the leading 0x):
#   FirewireGuid: 0x00A1234567891231
```

Then unplug + replug the iPod. (ArchWiki "iPod Classic/Nano (3rd generation)".)

### 2c. SysInfoExtended (recommended, fixes "writes vanish on disconnect")

Generate the extended info so libgpod hashes the DB correctly (without this, some models silently revert all changes when you unplug):

```bash
ipod-read-sysinfo-extended <device-node> /mnt/ipod
# e.g.: ipod-read-sysinfo-extended /dev/sdX2 /mnt/ipod
```

This writes `iPod_Control/Device/SysInfoExtended`.

> If a model still reverts on disconnect (notably some Nano 6th gen), the `libhashab` AUR package supplies the checksum hashing libgpod needs. The Classic generally does **not** need it.

---

## 3. Sync with Rhythmbox (simplest)

1. Launch Rhythmbox; ensure the **iPod plugin** is enabled (`Preferences → Plugins → Portable Players / iPod`).
2. The mounted iPod appears in the left sidebar as a device.
3. Add music to Rhythmbox's library (point it at a **local copy** of the NAS music, or mount the NAS share). Then drag tracks/playlists onto the iPod device, or use the device's sync settings.
4. **Eject from Rhythmbox** (or `umount /mnt/ipod`) before unplugging so the iTunesDB is flushed. Never yank a mounted iPod mid-write.

Workflow tip: keep a **static, curated copy** of the NAS library locally and sync that to the iPod. A stable source set makes the iPod a clean, reproducible mirror and avoids surprise DB churn.

---

## 4. gtkpod (power user / DB repair)

Use gtkpod when you need finer control or to repair a confused DB:

- Import existing DB, edit ID3 tags, add/remove tracks + cover art, manage playlists, then **Save Changes** (this calls `itdb_write`).
- gtkpod is the tool to reach for if Rhythmbox refuses the device.

Clementine/Strawberry are alternative GUIs that also use libgpod if you prefer them.

---

## 5. When the database gets confused (recovery)

Because the master is on the NAS, recovery is cheap:

1. Back up the current DB first (in case you want to inspect it):

   ```bash
   cp /mnt/ipod/iPod_Control/iTunes/iTunesDB ~/iTunesDB.bak
   ```

2. Reset the on-iPod database and re-create it (gtkpod can re-init), then re-sync from your local master copy.
3. If the filesystem itself is suspect, check it **unmounted**:

   ```bash
   sudo umount /mnt/ipod
   sudo fsck.vfat -n /dev/sdX2      # FAT32, read-only check first
   sudo fsck.vfat -a /dev/sdX2      # repair
   # (HFS+: fsck.hfsplus from hfsprogs)
   ```

4. Worst case: re-format FAT32 and re-initialize (FAT32 avoids HFS+ hassle on Linux entirely), then re-sync from the NAS master.

---

## 6. Verify

- [ ] iPod mounts and appears in Rhythmbox's sidebar.
- [ ] Added tracks survive an **eject + unplug + replug** (proves the DB wrote — if they vanish, redo step 2c SysInfoExtended).
- [ ] Tracks play on the iPod and show correct metadata + cover art.
- [ ] Car/USB-controller still navigates the library (the reason we kept Apple firmware).

---

## Audiobooks & podcasts (Audiobookshelf → iPod, automated)

> Everything above syncs **music** by hand through Rhythmbox. This section covers the **automated** pipeline that lands Audiobookshelf (ABS) audiobooks and podcasts into the iPod's own **Audiobooks** and **Podcasts** menus — with firmware resume-position memory — alongside that music. Music stays owned by Rhythmbox; this pipeline never touches it.

### How it's wired

The flow parallels the music mirror (NAS `music` → rig `~/Music` ALAC → Rhythmbox → iPod):

```
NAS SMB shares                 rig staging              iPod menus
/volume1/audiobooks  ─(RO CIFS)→ ~/Audiobooks/*.m4b ─┐
/volume1/podcasts    ─(RO CIFS)→ ~/Podcasts/<show>/ ─┴→ libgpod → Audiobooks / Podcasts
```

- **NAS side.** `/volume1/audiobooks` and `/volume1/podcasts` are read-only Synology SMB shares. ABS's hourly auto-download only pulls **future** podcast episodes; back-catalog is fetched on demand (see below).
- **Rig mounts.** Two read-only CIFS automounts, cloned from the music mount: `/mnt/nas-audiobooks-ro` and `/mnt/nas-podcasts-ro`.
- **Rig tools** live in `~/bin` (mirrored to the repo at `foss-setup/configs/host/rig/ipod-abs-sync/`):
  - `abs-ipod-stage.py` — mirrors the RO mounts into `~/Audiobooks/` and `~/Podcasts/`. Incremental, prunes orphans, and **aborts before pruning** if the source mounts look empty (NAS-blip safety). Writes `~/.ipod-abs-manifest.json`.
  - `libgpod_abs.py` — vendored + extended libgpod ctypes bindings that add audiobook/podcast media types (Rhythmbox can't set these — see rationale).
  - `abs-ipod-push.py` — the **only** step that writes to the iPod's iTunesDB. Idempotent (skips tracks already on the device by mediatype + album + title).
  - `abs-ipod-sync` — one-command wrapper (stage, then push).
  - `abs-ipod-verify.py` — monitoring helper (`IPOD_SYNC_OK` / `IPOD_ABSENT`).

### Daily staging (automatic)

A systemd timer stages the content every morning so a sync is fast when you plug in:

```bash
systemctl status abs-ipod-stage.timer       # fires daily at 05:30
journalctl -u abs-ipod-stage.service -n 40   # last staging run
sudo systemctl start abs-ipod-stage.service  # stage now, on demand
```

Staging turns each audiobook's chapter MP3s into **one** chaptered AAC `.m4b` in `~/Audiobooks/` (ffmpeg concat) — a single Audiobooks entry with chapters inside. Podcast episodes are copied verbatim into `~/Podcasts/<show>/`.

### One-command sync (plug in → run → eject)

Normal use:

```bash
# 1. plug in the iPod (the desktop auto-mounts it)
abs-ipod-sync           # stages, then pushes to the iPod
abs-ipod-sync --eject   # ...or push and unmount in one shot when it finishes
```

Useful flags on `abs-ipod-push.py`:

```bash
abs-ipod-push.py --list      # show what's already on the iPod, by mediatype
abs-ipod-push.py --dry-run   # print what would be written, write nothing
abs-ipod-push.py --mount /run/media/$USER/<label>   # explicit mount point
abs-ipod-push.py --eject     # flush the iTunesDB + unmount when done
```

> **Never run `abs-ipod-sync` concurrently with a Rhythmbox music sync.** Both write the same iTunesDB. Do one, eject, then the other.

### Why libgpod mediatype, not Rhythmbox

Placement on the iPod is driven **purely by libgpod's `mediatype` field** — not genre, folder, or filename. Rhythmbox can copy files but **cannot tag mediatype**, so anything it pushes lands under Music. `libgpod_abs.py` sets:

- **Audiobooks** → `mediatype = AUDIOBOOK`, added to the Master Playlist → shows under **Music ▸ Audiobooks**. `.m4b` (AAC) is the reliable container: the firmware always remembers position and skips the file when shuffling.
- **Podcasts** → `mediatype = PODCAST`, added to the **Podcasts playlist only** and **kept out of the Master Playlist** → shows under **Podcasts** only. Episodes stay MP3 (episodic content tolerates it). The module lazily creates the Podcasts playlist if the iPod never had one, and `reconcile_podcasts()` self-heals membership.

### Podcast back-catalog

ABS's hourly auto-download only fetches **future** episodes. To pull older episodes so they stage to the iPod, call the ABS API against the show:

```bash
curl -X POST "$ABS_URL/api/podcasts/<podcast-id>/download-episodes" \
     -H "Authorization: Bearer $ABS_TOKEN" -H 'Content-Type: application/json' \
     -d '<episode-array-from /api/podcasts/feed>'
```

Once downloaded, they appear on the RO mount and the next staging run picks them up.

> **Patreon-shared-feed caveat.** The 6 "Chapo Trap House" ABS podcasts all point at one combined Patreon RSS feed (a setup quirk), so backfilling them would multiply-download the same episodes. Only the distinct single-creator feeds (MinnMax, Kit & Krysta) were backfilled.

### Verify on the iPod

- [ ] **Audiobooks menu** lists each book as one entry; opening it shows chapters.
- [ ] Pausing an audiobook, playing something else, then reopening **resumes at the same spot**.
- [ ] Shuffling music does **not** pull audiobook/podcast tracks into the mix.
- [ ] **Podcasts menu** lists each show and its episodes — and those episodes do **not** also show under Music.
- [ ] Content survives an **eject + unplug + replug** (proves the iTunesDB wrote).
- [ ] `abs-ipod-push.py --list` matches what the menus show.

### Recovery

The NAS is the master; the iPod is a reproducible copy. If the iTunesDB gets confused, **wipe and re-sync** — restage (`abs-ipod-stage.service`) and re-push rather than hand-repairing the DB.

---

## Fallback: Rockbox (only if car/USB control stops mattering)

If you ever decide Apple-firmware integration no longer matters, Rockbox turns the iPod into a plain drag-and-drop USB drive (native FLAC/Opus, custom EQ), removing the iTunesDB entirely. Modern install uses the freemyipod bootloader. This **loses** Apple's car/USB-control integration, so it's strictly the fallback. Docs: <https://www.rockbox.org/wiki/IpodClassic>

---
[← Guides](index.md)

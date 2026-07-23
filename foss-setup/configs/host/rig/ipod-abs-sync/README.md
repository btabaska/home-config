# iPod ABS sync (rig) — Audiobookshelf audiobooks + podcasts → iPod Classic

Syncs Audiobookshelf **audiobooks** and **podcasts** from the NAS onto the physical
**iPod Classic** on the CachyOS "rig", landing them in the iPod's native **Audiobooks**
and **Podcasts** menus (with firmware resume-position memory), alongside the existing
Rhythmbox music sync. It parallels the music flow (NAS `music` share → rig `~/Music`
ALAC mirror → Rhythmbox → iPod): NAS read-only SMB shares → rig read-only CIFS mounts
→ a nightly staging step → a manual libgpod push when the iPod is plugged in.

Placement on the iPod is driven purely by libgpod's `mediatype` field, which Rhythmbox
**cannot** set — hence the vendored bindings here.

## Files in this dir

| File | Role |
|------|------|
| `abs-ipod-stage.py` | Mirrors the RO CIFS mounts into staging. Concatenates each audiobook's chapter MP3s into one chaptered AAC `.m4b` in `~/Audiobooks/` (ffmpeg); copies podcast episodes verbatim into `~/Podcasts/<show>/`. Incremental, prunes orphans, **aborts before pruning if the source mounts look empty** (NAS-blip safety). Writes `~/.ipod-abs-manifest.json`. |
| `libgpod_abs.py` | Vendored + extended libgpod ctypes bindings (based on gpodder's `libgpod_ctypes.py`, GPLv3). Adds `ITDB_MEDIATYPE_AUDIOBOOK`, an audiobook add-path (→ Music ▸ Audiobooks, in the Master Playlist), a podcast add-path (→ Podcasts playlist **only**, kept out of the Master Playlist), lazy Podcasts-playlist creation, `reconcile_podcasts()` self-heal, and full-DB enumeration for idempotency. |
| `abs-ipod-push.py` | The **only** step that writes to the iPod's iTunesDB. Reads the manifest + staged files and writes them with correct mediatypes. Idempotent (skips by mediatype + album + title). Flags: `--list`, `--dry-run`, `--eject`, `--mount`. |
| `abs-ipod-verify.py` | Monitoring helper (`host: rig` check `ipod-abs-stage-fresh`) — prints `IPOD_SYNC_OK` / `IPOD_MOUNTED_UNSYNCED` / `IPOD_ABSENT` (all pass) or a `STAGE_*` fail. |
| `abs-ipod-sync` | One-command wrapper: runs stage, then push. |
| `abs-ipod-stage.service` | systemd unit that runs `abs-ipod-stage.py` (dead-man Healthchecks ping on success). |
| `abs-ipod-stage.timer` | Daily timer for the staging service (05:30). |
| `README.md` | This file. |

## Operating model

- **Nightly staging (automatic):** `abs-ipod-stage.timer` fires daily at 05:30 →
  `abs-ipod-stage.service` refreshes `~/Audiobooks/*.m4b` and `~/Podcasts/<show>/`
  from the RO mounts, then pings Healthchecks (`abs-ipod-stage-rig`). No iPod required.
- **Push (manual):** writing to the iPod happens only when it's plugged in and you run
  the push. Music stays owned by Rhythmbox — **never run this concurrently with a
  Rhythmbox sync** (both write the same iTunesDB).
- **Podcast back-catalog:** ABS auto-download only fetches *future* episodes; pull older
  ones on demand via `POST /api/podcasts/:id/download-episodes`, then let the next
  staging run pick them up. The 6 "Chapo Trap House" ABS podcasts share one combined
  Patreon RSS feed, so only the distinct single-creator feeds (MinnMax, Kit & Krysta)
  were backfilled.
- **Recovery:** the NAS library is the master; the iPod is a reproducible copy. If the
  iTunesDB gets confused, wipe and re-sync.

## Run a sync

```bash
# plug in the iPod (desktop auto-mounts it), then:
abs-ipod-sync                 # stage + push
abs-ipod-push.py --eject      # flush the DB + unmount before unplugging
#   ...or in one shot:  abs-ipod-sync --eject

# handy:
abs-ipod-push.py --list       # what's already on the device, by mediatype
abs-ipod-push.py --dry-run    # preview, write nothing
```

## Anti-drift / deploy

Live copies of the tools live in **`~/bin`** on the rig; the systemd units live in
**`/etc/systemd/system/`**. This dir is the repo mirror — edit both, commit here.

Re-deploy from the repo:

```bash
# tools
scp foss-setup/configs/host/rig/ipod-abs-sync/{abs-ipod-stage.py,libgpod_abs.py,abs-ipod-push.py,abs-ipod-verify.py,abs-ipod-sync} rig:~/bin/
ssh rig 'chmod +x ~/bin/abs-ipod-*'

# systemd units
scp foss-setup/configs/host/rig/ipod-abs-sync/abs-ipod-stage.{service,timer} rig:/tmp/
printf '%s\n' "$RIG_SUDO_PW" | ssh rig 'sudo -S sh -c "install -m644 /tmp/abs-ipod-stage.{service,timer} /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now abs-ipod-stage.timer"'
```

### Parts of this feature that live *outside* this dir

Documented here so they aren't lost — they have no repo home of their own.

**1. NAS SMB shares.** `/volume1/audiobooks` and `/volume1/podcasts` are read-only
Synology SMB shares (they feed the rig's CIFS mounts). They didn't exist before this
feature — DSM (7.2.2) refuses to share an already-populated folder (`synoshare --add`
→ `0xE700`, `SYNO.Core.Share create` → `3312`), so the tiny content was moved aside,
the shares created, content restored, and ABS restarted. To recreate a share on the NAS
(sudo needs the vault password piped — see repo `CLAUDE.md`):

```bash
# folder must NOT already exist when the share is created, so move content aside first
synoshare --add audiobooks "ABS audiobooks (rig iPod sync, RO)" /volume1/audiobooks "" "" "" 1 0
synoshare --setuser audiobooks RO + btabaska      # grant the rig's SMB user read
# (repeat for podcasts; then restore content, chown -R 1026:100, restart ABS)
```

**2. Rig fstab CIFS mounts.** Two read-only automounts in `/etc/fstab` on the rig,
cloned verbatim (options + all) from the existing `music` mount — only the share name
and mountpoint differ:

```fstab
//192.168.10.4/audiobooks  /mnt/nas-audiobooks-ro  cifs  credentials=/etc/samba/cred-nas,ro,uid=1000,gid=1000,iocharset=utf8,vers=3.0,x-systemd.automount,x-systemd.idle-timeout=120,_netdev,nofail  0 0
//192.168.10.4/podcasts    /mnt/nas-podcasts-ro    cifs  credentials=/etc/samba/cred-nas,ro,uid=1000,gid=1000,iocharset=utf8,vers=3.0,x-systemd.automount,x-systemd.idle-timeout=120,_netdev,nofail  0 0
```

After editing fstab: `sudo mkdir -p /mnt/nas-{audiobooks,podcasts}-ro && sudo systemctl
daemon-reload`, then `sudo systemctl start mnt-nas-audiobooks-ro.automount
mnt-nas-podcasts-ro.automount` (or reboot). The `x-systemd.automount` option means the
shares mount on first access, so a NAS reboot never hangs the rig. If an automount
latches into a failed state after share creation, `systemctl reset-failed` +
`systemctl restart <unit>.automount`.

**3. Healthchecks + monitoring.** Staging pings Healthchecks check `abs-ipod-stage-rig`
(daily, 6h grace) via the ExecStartPost in the `.service`. The consumer-end verification
check `ipod-abs-stage-fresh` (`host: rig`, tier daily) runs `abs-ipod-verify.py`.

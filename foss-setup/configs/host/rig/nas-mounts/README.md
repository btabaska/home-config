# rig — NAS CIFS mounts + Docker ordering drop-in (glue-11)

Anti-drift record of the rig's **host-level** NAS storage config. Before glue-11 these
lived only in the rig's live `/etc/fstab` and `/etc/systemd/system/docker.service.d/`,
mentioned only in passing in a couple of service dirs (`suwayomi/`, `ipod-abs-sync/`) —
never captured as one place. read-18 added the `manga` rw mount + the Docker drop-in and
surfaced the gap.

## What's here

| File | Live target on the rig | Purpose |
|------|------------------------|---------|
| `fstab.snippet` | lines appended to `/etc/fstab` | the 5 NAS CIFS mounts |
| `10-remote-fs.conf` | `/etc/systemd/system/docker.service.d/10-remote-fs.conf` | order Docker `After=remote-fs.target` so the mounts are up before containers start |

## The mounts

All target the NAS SMB shares on `192.168.10.4`. Consumers:

- `//192.168.10.4/music → /mnt/nas-music-ro` (ro, automount) — [music-mirror](../music-mirror/) FLAC→ALAC transcode
- `//192.168.10.4/audiobooks → /mnt/nas-audiobooks-ro` (ro, automount) — [ipod-abs-sync](../ipod-abs-sync/)
- `//192.168.10.4/podcasts → /mnt/nas-podcasts-ro` (ro, automount) — [ipod-abs-sync](../ipod-abs-sync/)
- `//192.168.10.4/games → /mnt/share/Games` (rw, automount) — game servers (AMP/Palworld)
- `//192.168.10.4/manga → /mnt/nas-manga` (**rw, PERSISTENT — not autofs**) — [suwayomi](../suwayomi/) writes CBZ here → Komga's Manga library (read-18)

**Why `manga` is persistent, not autofs:** it's bind-mounted continuously into the
Suwayomi container. A persistent CIFS mount reconnects in place across NAS reboots (same
mountpoint, no re-mount) so the container's bind stays valid; an autofs re-mount would not
propagate into the running container (rprivate). The `10-remote-fs.conf` drop-in closes the
boot race (Docker previously ordered only `After=network-online.target`).

## Credentials (secrets — NOT in the repo)

Two root-only cred files, referenced by the mount lines:

- `/etc/samba/cred-nas` (root:root 0600) — music, audiobooks, podcasts, manga
- `/etc/nas_creds` (root:root 0600) — games

Each is `username=btabaska` + the NAS SMB password + `domain=WORKGROUP`. Recreate with:

```sh
printf 'username=btabaska\npassword=<nas-smb-pw>\ndomain=WORKGROUP\n' | sudo tee /etc/samba/cred-nas
sudo chmod 600 /etc/samba/cred-nas
```

## Applying (manual — ansible does NOT manage this)

No ansible-pull role touches the rig fstab or systemd mounts (`site.yml` = base/docker/
tailscale/backup/state; no `ansible.posix.mount`), so this dir is **documentation only** —
there is no reverse-drift risk, but changes are applied by hand:

```sh
# fstab: append/reconcile the lines from fstab.snippet, then
sudo systemctl daemon-reload && sudo mount -a
# docker ordering drop-in:
sudo install -Dm644 10-remote-fs.conf /etc/systemd/system/docker.service.d/10-remote-fs.conf
sudo systemctl daemon-reload
```

Keep this dir in sync when the rig's NAS mounts change.

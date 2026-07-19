# Seedbox "betty" (Bytesized AppBox) — live config mirror

Shared host, **no root, no docker**. Home dir `/home/hd34/btabaska`. Everything runs as
the user via two mechanisms:

| service | run mechanism | boot persistence |
|---------|---------------|------------------|
| deluged + deluge-web | `~/.startup/deluge` (provider runs `~/.startup/*` at boot) | provider |
| slskd | systemd **user** unit `slskd.service` → `~/bin/slskd/start-slskd.sh` (sources `~/slskd-native/.env`) | `loginctl` linger=yes |
| tailscaled + `tailscale up` | systemd user units `tailscaled.service` / `tailscale-up.service` | linger=yes |
| ~~qbittorrent-nox~~ | **retired 2026-07-17 (fix-21 / L9)** — launcher `~/.startup/qbittorrent` deleted; config left at `~/.config/qBittorrent` | — |

## fix-21 lockdown (2026-07-17) — nothing binds the public IP any more

Audit findings H2/L9/M25: Deluge RPC 3254, deluge-web 5945 (plain HTTP), qBittorrent
13091 and slskd 5030/5031 were all bound `0.0.0.0` on the public IP `185.162.184.38`;
the arrs and soularr crossed the WAN in cleartext. Now:

- **Deluge** `~/.config/deluge/core.conf`: `"allow_remote":false` → RPC binds `127.0.0.1:3254`.
  `~/.config/deluge/web.conf`: `"interface":"127.0.0.1"` → web binds `127.0.0.1:5945`.
  (Edit those files only while the daemons are STOPPED — they rewrite config on shutdown.
  BT peer traffic is untouched: `random_port:true` → currently `185.162.184.38:51867` TCP+UDP.)
- **slskd**: binds `127.0.0.1:5030` (`SLSKD_HTTP_IP` in `.env` + `web.ip_address` in
  `slskd.yml`); HTTPS 5031 disabled (`web.https.disabled: true` — the
  `SLSKD_HTTPS_DISABLED` env var in start-slskd.sh is NOT a real slskd knob).
  Soulseek P2P listener 50300 stays public (peers need it).
- **Tailnet reach-through**: tailscaled runs `--tun=userspace-networking`, which forwards
  inbound tailnet connections to loopback — so NAS/mini/laptop reach the loopback-bound
  services at `100.119.134.94:<port>` (seedbox.tailb31641.ts.net) while the public IP
  exposes only sshd + BT/Soulseek peer ports. Consumers repointed: sonarr/radarr/lidarr/
  readarr Deluge client + soularr `host_url` → `100.119.134.94`.
- **NAS side**: the Synology Tailscale package needed TUN mode for outbound tailnet TCP
  (`sudo tailscale configure synology` + package restart). DSM task id 13 re-asserts it
  daily (mirror: `configs/nas/tailscale/13.task`).
- `tailscale up --ssh` means port 22 **on the tailnet IP** is Tailscale SSH (ACL-gated;
  currently only the laptop is allowed). mini's runner ssh-es via the public
  `betty.bysh.me` sshd with the normal key instead.

Verification: `verification/checks.d/seedbox.yaml` (public-port sweep, loopback-bind
assert, sonarr→Deluge e2e test, slskd LoggedIn e2e, service manifest). Runbook:
`wiki/docs/runbooks/seedbox-exposure.md`.

## Disk hygiene (2026-07-19, quality-gate M8/L8/L93/L10)

- **deluged now logs** (L10): `~/.startup/deluge` launches deluged with
  `-l ~/.config/deluge/deluged.log -L warning` (previously no `--logfile` → 0-byte log,
  daemon errors went nowhere). Mirrored in `startup/deluge`. Restart verified lossless:
  378 torrents before and after.
- **`~/media/extracted` is transient** (M8): filebot/post-extract copies land there; the
  arrs import by *copy*, so once imported the NAS owns the file and the seedbox copy is
  junk (139G of it on 2026-07-19). A daily cron reaps files >7 days old and prunes empty
  subdirs (top dir kept) — see crontab below.
- **L93 cleanup**: removed extracted `.mkv` files sitting next to their still-seeding rars
  in 11 `~/files/tv` release dirs (~10.4G; rars untouched), and removed 11 dead torrents
  WITH data via deluge-console (10× Animaniacs.2020 — series not in Sonarr, never imports —
  plus the Andor S01E00 "A Disney Day Special Look" special). Deluge 389 → 378 torrents.
- **L8**: deleted the retired on-seedbox arr install leftovers in `~/tmp`
  (`{sonarr,radarr,prowlarr}_{update,backup}`, clr-debug-pipe/dotnet-diagnostic sockets, ~1.7G).

## Crontab (live `crontab -l`, this is the manifest)

```cron
0 5 * * * ~/venvs/deluge/bin/python ~/scripts/deluge-reaper.py --live >/dev/null 2>>~/logs/deluge-reaper.err
30 5 * * * find /home/hd34/btabaska/media/extracted -type f -mtime +7 -delete; find /home/hd34/btabaska/media/extracted -mindepth 1 -type d -empty -delete
```

## Files here

- `systemd-user/*.service` → live `~/.config/systemd/user/` (enable with
  `systemctl --user enable <unit>`; needs `XDG_RUNTIME_DIR=/run/user/$(id -u)` and
  `DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus` over plain ssh)
- `bin/start-slskd.sh` → live `~/bin/slskd/start-slskd.sh`
- `startup/deluge` → live `~/.startup/deluge`
- `slskd-native/slskd.yml` → live `~/slskd-native/slskd.yml` (no secrets; creds in `.env`)
- `slskd-native/.env.example` → live `~/slskd-native/.env` (values in vault `soulseek.*`)
- `deluge-reaper.py` — queue hygiene cron (connects to `127.0.0.1:3254`, unaffected).
  Since fix-25 (2026-07-17, quality-gate L42) it reaps **all** *arr label pairs
  (`sonarr`/`radarr`/`lidarr`/`readarr`/`tv-whisparr` + `*-imported`, legacy `tv-sonarr`),
  not just sonarr — safe because `deluge-preimport-stuck.py` alarms >48h-stuck
  pre-import torrents long before the 14-day reap age.
- `deluge-preimport-stuck.py` → live `~/scripts/` — verification probe (fix-25): fails if a
  100%-complete torrent sits in a PRE-import label >48h (import path broken / Post-Import
  Category regressed). Wired as `deluge-preimport-stuck` in `verification/checks.d/seedbox.yaml`.
- `deluge-relabel-imported.py` — maintenance tool (fix-25), run **from a LAN workstation**
  (not the seedbox: it needs the NAS arr APIs + `ssh seedbox`): verifies each pre-import
  torrent against the owning arr's import history (`history?downloadId=`) and relabels
  confirmed-imported ones to `<label>-imported`. Used 2026-07-17 to clear the 273-torrent
  backlog (272 relabeled, 1 legitimately in-flight left alone). Dry-run by default.

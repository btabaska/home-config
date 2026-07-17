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

## Files here

- `systemd-user/*.service` → live `~/.config/systemd/user/` (enable with
  `systemctl --user enable <unit>`; needs `XDG_RUNTIME_DIR=/run/user/$(id -u)` and
  `DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus` over plain ssh)
- `bin/start-slskd.sh` → live `~/bin/slskd/start-slskd.sh`
- `startup/deluge` → live `~/.startup/deluge`
- `slskd-native/slskd.yml` → live `~/slskd-native/slskd.yml` (no secrets; creds in `.env`)
- `slskd-native/.env.example` → live `~/slskd-native/.env` (values in vault `soulseek.*`)
- `deluge-reaper.py` — queue hygiene cron (connects to `127.0.0.1:3254`, unaffected)

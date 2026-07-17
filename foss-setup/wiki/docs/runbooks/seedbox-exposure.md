# Runbook — seedbox exposure / tailnet path (fix-21)

**Checks:** `seedbox-public-lockdown`, `seedbox-loopback-binds`, `seedbox-arr-deluge-e2e`,
`seedbox-slskd-e2e`, `seedbox-services-manifest` (`verification/checks.d/seedbox.yaml`).

## Design (2026-07-17 lockdown, quality-gate H2/L9/M25)

Deluge RPC (3254), deluge-web (5945) and slskd (5030) bind **127.0.0.1** on betty.
Consumers (sonarr/radarr/lidarr/readarr/whisparr Deluge client + Remote Path Mapping,
soularr `host_url`) use the tailnet address **100.119.134.94** — userspace tailscaled on
betty forwards inbound tailnet connections to loopback. The NAS reaches the tailnet only
because its Tailscale package is in **TUN mode** (`tailscale configure synology`; DSM
task 13 re-asserts daily). qBittorrent is retired. Public IP exposes only sshd,
Deluge peer port (currently 51867, `random_port`), and Soulseek peer port 50300.

## seedbox-public-lockdown FAILS (STILL_OPEN:…)

A service rebound a public interface. On betty:

```
ss -tlnp | grep -E ':(3254|5945|13091|5030|5031)'
```

- Deluge: STOP daemons first (`/sbin/start-stop-daemon -K --pidfile ~/.config/deluge/.deluge-web.pid`,
  same with `.deluged.pid`; they rewrite conf on exit), then re-assert
  `"allow_remote":false` in `core.conf` (compact JSON — no space after `:`) and
  `"interface": "127.0.0.1"` in `web.conf`; restart with `~/.startup/deluge`.
- slskd: `SLSKD_HTTP_IP=127.0.0.1` in `~/slskd-native/.env` AND `web.ip_address: 127.0.0.1`
  + `web.https.disabled: true` in `~/slskd-native/slskd.yml`; then
  `systemctl --user restart slskd` (export `XDG_RUNTIME_DIR=/run/user/$(id -u)` and
  `DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus` first over plain ssh).
- qBittorrent open again = someone recreated `~/.startup/qbittorrent` — remove it,
  `pkill -x qbittorrent-nox`.

## seedbox-arr-deluge-e2e / seedbox-slskd-e2e FAIL (tailnet path dead)

Every grab strands while this is down — treat as pipeline outage, not cosmetics.
Walk the chain:

1. **betty up?** `ssh seedbox` (public sshd, `betty.bysh.me`).
2. **tailscaled on betty:** `systemctl --user is-active tailscaled tailscale-up slskd`
   (env exports above). Restarting tailscaled drops YOUR ssh if you're on the tailnet.
3. **NAS TUN mode:** `ssh nas 'ip -o addr show tailscale0'` — missing interface =
   userspace mode again (package updated?). Re-run
   `sudo /var/packages/Tailscale/target/bin/tailscale configure synology` then
   `sudo /usr/syno/bin/synosystemctl restart pkgctl-Tailscale.service`
   (**your `ssh nas` session dies** — it rides the tailnet; reconnect after ~15 s).
4. **slskd LoggedIn but check fails:** API key rotated? mini `/etc/verification/env`
   `SLSKD_API_KEY` must match betty `~/slskd-native/.env` (vault `soulseek.slskd_api_key`).
5. Consumer-side sanity: Sonarr → Settings → Download Clients → Test; soularr
   `docker logs soularr` (needs sudo on NAS).

## seedbox-services-manifest FAILS

Compare against `verification/coverage/seedbox.services`. `down:` = start it
(deluge via `~/.startup/deluge`; slskd/tailscaled via `systemctl --user start …`;
syncthing via `~/.startup/syncthing`). `retired-but-running:qbittorrent-nox` = kill it
and delete whatever launcher resurrected it. Deploying/retiring a seedbox service =
update the manifest file + this runbook + `configs/host/seedbox/README.md`.

## Gotchas that already bit

- Deluge conf edits while daemons run are silently overwritten on daemon shutdown.
- `pkill -f 'slskd --app-dir'` cleanly exits the systemd unit (`Restart=on-failure`
  does NOT bring it back) — use `systemctl --user restart slskd`.
- slskd env creds live in `.env`, loaded ONLY via `start-slskd.sh` — starting the
  binary by hand yields "username and/or password invalid" + no API keys (soularr 401s).
- `SLSKD_HTTPS_DISABLED` in start-slskd.sh is not a real slskd option; the yml
  `web.https.disabled` is what kills the 5031 listener.
- Port 22 on betty's **tailnet** IP is Tailscale SSH (ACL-gated, laptop-only);
  mini's runner must ssh `betty.bysh.me`.

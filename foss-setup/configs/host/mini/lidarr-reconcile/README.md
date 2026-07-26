# lidarr-reconcile — close the musicseerr unmonitored-artist generator (media-07)

Follow-through on **fix-25**. musicseerr (`ghcr.io/habirabbu/musicseerr:v1.4.2`)
adds a Lidarr artist with `monitored=false` for a single-album request, leaving
the requested album invisible to wanted/missing (Lidarr gates on the parent
artist). There is **no config knob** for this in musicseerr and the image has no
bind-mounted code to patch, so the generator is closed downstream instead.

`lidarr-artist-monitor-reconcile.py` sweeps Lidarr every 15 min and enforces the
invariant **"if any album is monitored, its artist must be monitored"** — it
flips `artist.monitored=true` for any artist that owns a monitored + zero-byte
album (the exact `arr-orphan-monitor-flags` tripwire condition). It does not
touch album flags and does not trigger searches, so no surprise grabs; it only
makes an already-requested album retryable. Idempotent; exits non-zero only on a
real API/config error.

## Provenance / deploy (NOT ansible-managed)

Like `tv-cleanup`, `net-selfheal`, and `static-ip`, these are **host** units on
the mini, deployed by hand (the ansible roles are base/docker/tailscale/backup/
state only). This directory is the canonical source; keep it and the live host
in sync.

| repo file | live path | owner / mode |
|-----------|-----------|--------------|
| `lidarr-artist-monitor-reconcile.py`      | `/usr/local/sbin/lidarr-artist-monitor-reconcile.py` | `root:root 0755` |
| `lidarr-artist-monitor-reconcile.service` | `/etc/systemd/system/lidarr-artist-monitor-reconcile.service` | `root:root 0644` |
| `lidarr-artist-monitor-reconcile.timer`   | `/etc/systemd/system/lidarr-artist-monitor-reconcile.timer`   | `root:root 0644` |
| `lidarr-artist-monitor-reconcile.env.example` → filled | `/etc/default/lidarr-artist-monitor-reconcile` | `root:btabaska 0640` |

```sh
sudo install -m0755 lidarr-artist-monitor-reconcile.py /usr/local/sbin/
sudo install -m0644 lidarr-artist-monitor-reconcile.{service,timer} /etc/systemd/system/
# fill LIDARR_API_KEY from vault arr_api_keys.lidarr, then:
sudo install -m0640 -o root -g btabaska /etc/default/lidarr-artist-monitor-reconcile
sudo systemctl daemon-reload
sudo systemctl enable --now lidarr-artist-monitor-reconcile.timer
```

## Monitoring

- `arr-orphan-monitor-flags` (checks.d/media.yaml, warn) — the **outcome** probe:
  orphans stay at 0 because this reconciler clears them.
- `lidarr-reconcile-timer-healthy` (checks.d/media.yaml) — catches a silently
  stopped reconciler independently of the hourly tripwire.
- `OnFailure=ntfy-notify@%n.service` — alerts on a hard reconciler failure.

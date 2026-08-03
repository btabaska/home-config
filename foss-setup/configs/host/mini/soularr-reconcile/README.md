# soularr-reconcile — prune soularr's failed-import dead-letter (fix-56)

Closes the **fix-40 regression** (fleet-sweep SM29). soularr
(`ghcr.io/mrusse/soularr:1.2.2`) records every failed import in a persistent
denylist at `nas:/volume1/docker/soularr/failed_imports.json` and skips those
albums forever ("Skipping failed import album"). The upstream code
(`/app/soularr.py`, `add_to_failed_import_denylist`) **only ever appends — it has
no path that removes an entry**, so the file grows without bound and collects:

- **ghosts** — albums that later completed via another path (torrent/manual/
  re-request) but whose stale entry lingers (the Eminem 5030 case fix-40 cleared
  by hand; on 2026-08-02: Paradise 10/10, Hybrid Theory 15/15, Underclass Hero
  16/16), and
- **abandoned** — albums the operator has since unmonitored.

fix-40 cleared the file once and added the `nas-soularr-failed-imports-fresh`
tripwire but no prevention, so the backlog re-accumulated (9 entries) and Camera
+ Heat Waves aged past the 3-day staleness threshold, cycling indefinitely.

`soularr-denylist-reconcile.py` runs on the **mini** every 6h and prunes ONLY
entries the live Lidarr proves safe to drop — the album is **complete**
(`trackFileCount >= totalTrackCount`), **unmonitored**, or **deleted** (404). A
monitored + still-incomplete album is left in place: soularr should not retry a
known-bad import, and that genuinely-stuck case is what
`nas-soularr-failed-imports-fresh` surfaces for a human. The prune is applied
NAS-side in one python invocation that deletes only the named keys from the
current file (so a concurrent soularr append is not clobbered) and atomically
`os.replace()`s it. Idempotent; exits non-zero only on a real API/ssh/config
error.

The denylist + soularr live on the NAS, but the reconciler runs on the mini
(same pattern as `lidarr-reconcile`): the mini has passwordless `ssh nas` as
`btabaska` and the Lidarr key. It never uses NAS sudo.

## Provenance / deploy (NOT ansible-managed)

Like `tv-cleanup`, `net-selfheal`, `static-ip`, `lidarr-reconcile`, and
`arr-queue-reconcile`, these are **host** units on the mini deployed by hand (the
ansible roles are base/docker/tailscale/backup/state only). This directory is the
canonical source; keep it and the live host in sync.

| repo file | live path | owner / mode |
|-----------|-----------|--------------|
| `soularr-denylist-reconcile.py`      | `/usr/local/sbin/soularr-denylist-reconcile.py` | `root:root 0755` |
| `soularr-denylist-reconcile.service` | `/etc/systemd/system/soularr-denylist-reconcile.service` | `root:root 0644` |
| `soularr-denylist-reconcile.timer`   | `/etc/systemd/system/soularr-denylist-reconcile.timer`   | `root:root 0644` |
| `soularr-denylist-reconcile.env.example` → filled | `/etc/default/soularr-denylist-reconcile` | `root:btabaska 0640` |

```sh
sudo install -m0755 soularr-denylist-reconcile.py /usr/local/sbin/
sudo install -m0644 soularr-denylist-reconcile.{service,timer} /etc/systemd/system/
# fill LIDARR_API_KEY from vault arr_api_keys.lidarr, then:
sudo install -m0640 -o root -g btabaska soularr-denylist-reconcile.env /etc/default/soularr-denylist-reconcile
sudo systemctl daemon-reload
sudo systemctl enable --now soularr-denylist-reconcile.timer
```

## Monitoring

- `soularr-denylist-no-ghosts` (checks.d/soularr-backlog.yaml, warn) — the
  **outcome/class** probe: 0 denylist entries are complete-or-unmonitored,
  because this reconciler keeps it clean (catches ghost re-accumulation well
  before the 3-day staleness tripwire).
- `soularr-reconcile-timer-healthy` (checks.d/soularr-backlog.yaml) — catches a
  silently stopped reconciler.
- `nas-soularr-failed-imports-fresh` (checks.d/nas-host.yaml, fix-40) — the
  original staleness backstop; now stays green because the file no longer rots.
- `OnFailure=ntfy-notify@%n.service` — alerts on a hard reconciler failure.

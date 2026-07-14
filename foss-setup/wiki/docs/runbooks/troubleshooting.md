# Troubleshooting index

> Start here when something is broken. This is the hub: the incident runbooks, the
> per-service "Troubleshooting" sections, and the known incident **classes** — each with
> the symptom, the real root cause, and where to fix it.

_Compiled 2026-07-14 from live incidents. When a new incident class is learned, add a row here and (if service-specific) a `troubleshoot` entry in `configs/docker-stack/service-enrichment.yaml`._

## Incident runbooks (step-by-step)

| Runbook | When |
|---|---|
| [DNS outage](dns-outage.md) | No name resolution; some/all devices "no internet" |
| [Backup & restore](backup-restore.md) | Verify a backup, or restore data / a database |
| [Rebuild a host](rebuild-a-host.md) | A host is lost and must be rebuilt from scratch |
| [Recover the rig (WoL)](wake-the-rig.md) | The rig is off/asleep and won't wake |
| [Update images](update-images.md) | Diun flagged a new image; pull & roll it out |
| [Add a service](add-a-service.md) | Stand up a new stack the repeatable way |
| [Verification](verification.md) · [Acceptance testing](acceptance-testing.md) | Read / re-run the health checks |

Every service page also has its own **Troubleshooting** section (symptom → fix), generated
from the enrichment catalog — browse them from the [services overview](../services/index.md).

## Known incident classes

### DNS & network

| Symptom | Root cause | Fix / where |
|---|---|---|
| `mini` alive but totally off-network, only a hard reboot helps | Was 24 h DHCP-lease expiry (not a freeze). **Resolved** — mini is now static-IP + `net-selfheal` watchdog | [mini network resilience](../reference/hosts/mini-network-resilience.md) |
| Whole-house "WiFi connected, no internet" | A client stuck on a single dead resolver — fail-open DHCP nameserver chain (`.2 → .4 → .1`) not yet on every VLAN (dns-03) | [DNS outage](dns-outage.md), [AdGuard](../services/adguard.md) |
| `502` through Caddy for a service | Caddy can't reach the upstream container — an **incident**, not expected (all hosts are 24/7) | [Caddy](../services/caddy.md) |

### Media & \*arr

| Symptom | Root cause | Fix / where |
|---|---|---|
| Movie/episode shows `hasFile=True` but Plex plays nothing (6–24 MB file) | \*arr imported a release's junk `sample.*` as the movie | [media-automation](../services/media-automation.md) |
| Sonarr search returns ~0 grabs / UI freezes | SQLite-lock freeze class; IPT-only indexer returns nothing; unpackerr silent-hang | [media-automation](../services/media-automation.md) |
| \*arr queue fills with "already imported" items that never leave | Download client has no **Post-Import Category** → imported torrents stay in the tracked label | [Deluge queue hygiene](../reference/seedbox/deluge-queue-hygiene.md) |

### Plex

| Symptom | Root cause | Fix / where |
|---|---|---|
| Plex library shows **0 items** after a CIFS-side write | DSM shares written over CIFS lack the `PlexMediaServer` ACL ACE | `synoacltool` add + inheritance; see [Plex on the NAS](../reference/nas/plex.md) |
| Plex returns `503` to **all** clients while a process is "running" | Bulk ingest floods none-agent metadata analysis → worker pool saturated; drains glacially | [pinchflat](../services/pinchflat.md) |

### Music

| Symptom | Root cause | Fix / where |
|---|---|---|
| New music never appears in Navidrome ("Periodic scan is DISABLED") | 0.62 ignores legacy `ND_SCANSCHEDULE`; use `ND_SCANNER_SCHEDULE` | [navidrome](../services/navidrome.md) |
| MusicSeerr request stuck "Downloading 0%" (phantom) | Album stayed `monitored=False` in Lidarr | [musicseerr](../services/musicseerr.md) |
| Rig `~/Music` ALAC files disappear overnight | Two timers fight: 05:00 transcode then 05:30 `rsync --delete-after` | [rig timers](../reference/hosts/rig-timers.md) |

### Ebooks & reading

| Symptom | Root cause | Fix / where |
|---|---|---|
| Book requests 400 / stuck | Blind `readarr_books[0]` picked a junk rreading-glasses edition (phantom-author 404) | [libreseerr](../services/libreseerr.md) |
| CWA ingest not picking up new books | `NETWORK_SHARE_MODE` CIFS watcher unreliable → runs `false` live; redeploy reverts it | [calibre-web-automated](../services/calibre-web-automated.md) |

### Hardware & backup/DR

| Symptom | Root cause | Fix / where |
|---|---|---|
| Rig froze / NVMe errors | Marginal PCIe link on the OS drive (SN570 @ `74:00.0`); APST/ASPM kernel fix applied, AER monitor watching | [rig PCIe AER monitor](../reference/hosts/rig-pcie-aer-monitor.md) |
| "Is my off-site backup real?" | DR is live but **not** reproducible-from-ansible; rig `/opt` (game worlds) not covered by restic | [Backup & restore](backup-restore.md), [NAS backup architecture](../reference/nas/backup-architecture.md) |

### Gaming

| Symptom | Root cause | Fix / where |
|---|---|---|
| Friends can't reach a game server after adding a tunnel | A new playit UDP-claim needs an **agent restart** to take effect | [playit](../services/playit.md) |
| AMP won't start / server won't wake | Licence is hostname-pinned; empty-server sleep-mode is a trap (disabled — rig is 24/7) | [amp](../services/amp.md) |
| Home IP visible to strangers | Palworld community browser leaks it → `COMMUNITY=false` | [palworld](../services/palworld.md) |

!!! warning "Monitoring ≠ correctness"
    The sweep/tracker can report **green** while an end-to-end feature is broken (e.g.
    Pinchflat→Plex, Libreseerr→CWA, MusicSeerr `/requests`). Health checks test *liveness*,
    not end-to-end *correctness* — when in doubt, verify the actual user-facing path.

---

See also: [Maintenance calendar](../operations/maintenance-calendar.md) · [Verification checks](../reference/checks/index.md)

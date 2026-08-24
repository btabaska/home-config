# Fleet hygiene — junk classes, reapers, and the accepted-state register

Outcome of **fix-45** (quality-gate 2026-07-16, the low-severity batch: M8 +
~60 L-findings across every host, resolved 2026-07-19). The theme: junk and
drift that accumulates *silently* — extracted-media leftovers nobody reaps,
core dumps nobody reads, recycle bins nobody empties, config referencing
things that no longer exist. Each cleanup below got either an automated reaper
or a verification check so the class cannot regrow unnoticed.

Sibling pages: [host-hygiene](host-hygiene.md) (fix-39, mini dead-services),
[nas-host-hygiene](nas-host-hygiene.md) (fix-40, NAS host drift),
[monitoring-coverage](monitoring-coverage.md) (fix-29, liveness vs reality).

## Reapers & schedules added

| what | where | schedule |
|---|---|---|
| extracted-leftover reaper (`find -mtime +7 -delete`) | seedbox crontab | daily 05:30 |
| recycle-bin retention, music+youtube shares (>30d) | DSM task 14 → `/volume1/scripts/nas/empty-recycle-30d.sh` | monthly 1st 05:00 |
| journald retention (`SystemMaxUse=1G`, `MaxRetentionSec=3month`) | rig `/etc/systemd/journald.conf.d/50-retention.conf` | — |
| host-manifest export (pkg/cron/timer/image lists → `hosts/cachyos/`) | rig `export-manifests.timer` | weekly Mon 04:00 |

The recycle-bin script re-creates both Navidrome `.ndignore` guards after
emptying (share-root `/volume1/music/.ndignore` + the in-bin marker), so an
emptying pass can never strip the scanner guard again.

## Checks added (all `task_id: fix-45`, ntfy topic `verification`)

| check | file | fires when |
|---|---|---|
| `seedbox-extracted-reaped` | seedbox.yaml | extracted files >7d survive (reaper rot / M8 regrowth) |
| `seedbox-tmp-arr-junk` | seedbox.yaml | `*arr` `_update`/`_backup` dirs reappear in `~/tmp` |
| `nas-core-dumps` | nas-host.yaml | any `core.gz` at `/volume1` root — **a process crashed; read the dump name/date before deleting** |
| `nas-docker-macos-junk` | nas-host.yaml | `.DS_Store`/`._*` synced into `/volume1/docker` |
| `arr-unmapped-folders-growth` | media-library-correctness.yaml | unmapped root folders exceed the accepted baseline (radarr 39 / sonarr 13) |
| `sonarr-unmanaged-profile` | media-library-correctness.yaml | a monitored series lands on the unmanaged `Any` profile (bypasses TRaSH scoring) |
| `mini-container-dns-egress` | dns.yaml | containers on mini can't resolve external names (the silent 14h docker-DNS outage class) |
| `verification-tree-macos-junk` | verification-self.yaml | AppleDouble junk ships into `/opt/verification` again |

## Accepted-state register (deliberate, not drift)

Documented here so future audits don't re-flag them:

- **Radarr 39 unmapped folders** — multi-movie packs (Star Wars saga, Indiana
  Jones 1-4, Matrix/Hobbit/BTTF/MIB trilogies, Star Trek 13-pack, Muppets
  9-pack, …) plus only-available-edition relics (4× Jackass DVDRips). Plex
  serves them; Radarr can't model packs. Junk (dupes/DVDScr/strays) was
  deleted 2026-07-19.
- **Sonarr 13 unmapped folders** — legacy series kept Plex-only (One Piece,
  Black Sails, BATMAN TAS, Justice League, Roseanne, …) + `#recycle`.
  Euphoria + I Love LA were adopted INTO Sonarr instead (21 episodes imported).
- **Hue: 8 of 73 lights unavailable** — bulbs cut at wall switches (kitchen
  x4, basement x2, bathroom vanity, attic lamp). Physical, not integration.
- **HA: Matter server loaded with 0 devices** — kept for future use.
  **Roomba dropped** — pairing needs fresh BLID/password + physical access;
  its discovery flow will keep reappearing and can be ignored/dismissed.
- **Plex credits detection fails on ~1/3 of items** ("incomplete marker
  attributes") — upstream scanner behavior, queue still advances; accepted.
- **Pinchflat: 31 pending items are members-only/unavailable** — impossible
  without channel-membership cookies; retries cap at attempt 20 and discard.
- **Lidarr: The Marshall Mathers LP at 17/18 tracks** — the missing track is a
  skit absent from available releases; album stays monitored in case a future
  release fills it (wanted/missing reads 0 today).
- **AdGuard-NAS upstreams to Quad9 DoH, not an Unbound** — deliberate: a
  mini-hosted Unbound upstream would make both resolvers die with the mini.
  Trade-off (secondary queries leave the LAN) documented in the unbound
  compose header.
- **Apollo mDNS re-registration churn (~every 20s)** — ceased after the
  2026-07-16 Apollo restart (today's 9h journal window: zero avahi lines;
  `_nvstream._tcp` still advertised). If it returns, suspect veth/interface
  churn driving avahi re-registrations; it is cosmetic log noise, not a
  discovery outage.

## Watch items (evidence logged, no action yet)

- **Apollo LAN-block — RESOLVED 2026-07-19 (operator decision: re-allow).**
  The 2026-07-16 UFW lockdown had omitted the Apollo/Moonlight ports; LAN
  streaming + the caddy vhost were dead 3 days while tailnet paths (which
  bypass UFW) stayed green. Re-allowed LAN-scoped: 47984,47989,47990,48010/tcp
  + 47998:48002/udp — verified direct 307 and apollo.tabaska.us 307 (was 502).
  Rule inventory now lives in the [rig host page](../hosts/rig.md).

- **mini→HA bad-token curls** — ad-hoc curls from mini (agent sessions not
  loading `/etc/verification/env`) trip HA's `http.ban` warning and regenerate
  the "Login attempt failed" notification. The deployed `ha-api-auth` check
  authenticates fine. If the notification reappears, look for a session/script
  curling HA without the env token — not a deployed-config bug.
- **/volume1 interim growth** (~790 GiB observed mid-cleanup 2026-07-19) and
  **seedbox +760G ROM-collection torrents** (added 18:39–19:11 the same day) —
  operator activity, not junk; noted for capacity awareness.
- **deluged.log flood — RESOLVED (fix-69 / SM18, 2026-08-03).** The libtorrent
  `outstanding_request_limit_reached` performance WARNING (~1.1/sec from heavy
  seeding) had grown the log to 36MB, ~99% that one line. Two fixes: launcher log
  level `-L warning` → `-L error` (`~/.startup/deluge`, source-quiet on next deluged
  restart) + a daily `logrotate` (`copytruncate`, keep 5 gz, `size 20M`) at
  `~/.config/logrotate/deluged.conf` (crontab 04:20). Guard:
  `seedbox-deluged-log-bounded` (<50M). Mirror: `configs/host/seedbox/logrotate/`.

- **seedbox dead rootless-docker artifacts — REMOVED (fix-69 / SL44, 2026-08-03).**
  A rootless-docker experiment (gracefully shut down 2026-07-08) left `~/docker`,
  `~/.docker`, `~/.dockerd-rootless.log` behind; all removed (`dockerd` not running,
  boot launcher already disabled). The `~/apps/syncthing` tree left over from the
  same era was already gone with the fix-52 syncthing retirement.
- **wiki-rag-sync file leak (L39 root cause)** — `scripts/ai/wiki-rag-sync.py`
  removes replaced files from the knowledge collection but never calls
  `DELETE /api/v1/files/{id}`, so every changed wiki page leaks a file row +
  chroma collection + upload on the rig. The 2026-07-19 cleanup zeroed the
  backlog; expect slow regrowth until the sync script is patched (follow-up).

## Sonarr unmanaged-profile drift + IPT grab-share false-positive (fix-94, 2026-08-23)

**Sonarr profiles**: 10 monitored series (old cartoons/anime — Teen Titans Go!,
Animaniacs, Zoids, Cardcaptor Sakura, …) had drifted onto the `Any` quality profile
(id 1), which accepts junk/cam releases (the fix-27 sample-file risk). The fleet
standard is `WEB-1080p` (id 7 — 158 of 168 series). Re-pinned all 10 to WEB-1080p via
the Sonarr series-editor API (`PUT /api/v3/series/editor {seriesIds, qualityProfileId:7}`);
`sonarr-unmanaged-profile` now `PROFILE_OK n=0`. When adding a series, confirm it lands
on a managed profile, not `Any`.

**IPT grab-share**: `arr-grab-source-not-storming` (fix-50) chronically false-fired at
IPTorrents 60-71% share. IPTorrents is the fleet's DELIBERATE primary paid tracker (the
whole WEB-1080p library is sourced from it), so it is EXPECTED to dominate the grab
stream — that is not the fix-50 junk-storm (which was Bitmagnet, a runaway DHT indexer
re-grabbing owned titles). Recalibrated `arr-grab-indexer-share.py`: a PRIMARY indexer
(`PRIMARY_INDEXERS = {IPTorrents}`) is only flagged at near-total ≥95% share (every
other indexer dead); the 60% dominance rule still applies to NON-primary indexers.
Observation (not yet failing): IPT runs ~430 searches/day ≈ 72% of its 600/24h cap —
if it ever exhausts, add indexers or reduce arr search frequency.

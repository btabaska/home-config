# Seedbox (Betty) — Deluge queue hygiene

> How Deluge runs on the Bytesized seedbox "betty", the RPC access pattern for scripts, the *arr queue-clog fix (Post-Import Category), and the age-based `deluge-reaper.py` cleanup.

_Source: `foss-setup/configs/host/seedbox/README.md` · migrated + validated 2026-07-14_

Deluge runs on the seedbox (`betty.bysh.me`, **no root**). Sonarr/Radarr/Lidarr on the NAS import from it over a mount (cross-machine → imports are **copies**, so the NAS library and the seedbox torrent data are independent copies). Deleting seedbox torrent data is therefore safe for the library.

## Deluge RPC access (for scripts)

- Daemon: `127.0.0.1:3254`, `allow_remote: true`. Label plugin enabled.
- Auth: local `btabaska` creds in `~/.config/deluge/auth` (scripts parse the `btabaska:<pass>:<lvl>` line; **never print the value**).
- Driver: the venv python `~/venvs/deluge/bin/python` has the `deluge` lib.
- `deluge-console` exists (`~/.local/bin/deluge-console`) but the Label plugin's console command is **NOT registered** — use the RPC (`client.label.*`) instead. `deluge-console` also defaults to the stale port `58846`, so it fails to connect without an explicit host/port.
- RPC API surface: `client.connect("127.0.0.1", 3254, user, pw)`, then `client.label.get_labels()` / `client.label.add()` / `client.label.set_torrent()`, `client.core.get_torrents_status({}, [fields])`, `client.core.remove_torrent(hash, remove_data)`.

!!! note "Validated against live betty (2026-07-14)"
    Reached over the working `ssh seedbox` alias (the older memory note claimed this alias was broken and required the tailscale IP — it now works directly). Deluge `core.conf` confirms `"daemon_port":3254`, `"allow_remote":true`, and `"enabled_plugins":["Bytesized","Label","ltConfig","AutoAdd"]`. `deluge-console` with no args tried `127.0.0.1:58846` and got `Connection refused` — confirming the port gotcha and the "use RPC on :3254" rule.

### Deluge daemon facts (from live `core.conf`)

| Setting | Value |
| --- | --- |
| `daemon_port` | `3254` |
| `allow_remote` | `true` |
| `download_location` | `/home/hd34/btabaska/files/` |
| `config_location` | `/home/hd34/btabaska/.config/deluge` |
| `listen_interface` / `outgoing_interface` | `185.162.184.38` |
| `enabled_plugins` | `Bytesized`, `Label`, `ltConfig`, `AutoAdd` |
| `remove_seed_at_ratio` / `stop_seed_at_ratio` | `false` (seeding is not auto-stopped) |
| `copy_torrent_file` | `true` |

## The "57-item Sonarr queue" fix (2026-07-09)

**Root cause:** Sonarr's Deluge client had **no Post-Import Category** and `removeCompletedDownloads=False`, so imported torrents stayed in the `sonarr` label, got re-scanned, pinned with "already imported" *warnings*, and never left the queue.

**Fix (keeps seeding, clears queue):**

1. Deluge label `sonarr-imported` created.
2. Sonarr → Settings → Download Clients → Deluge → **`tvImportedCategory = sonarr-imported`**. On successful import Sonarr re-labels the torrent out of the tracked `sonarr` label → it leaves the queue while Deluge keeps seeding. `removeCompletedDownloads` stays `False`.
3. Existing stuck torrents were relabeled `sonarr` → `sonarr-imported` once (via RPC `client.label.set_torrent`).

!!! note "Validated against live betty (2026-07-14)"
    RPC `client.label.get_labels()` returns all nine labels: `lidarr`, `lidarr-imported`, `manual`, `radarr`, `radarr-imported`, `readarr`, `sonarr`, `sonarr-imported`, `tv-sonarr`. Live torrent counts by label: `sonarr`=262, `sonarr-imported`=79, `radarr`=6, `radarr-imported`=10, `lidarr`=5, `lidarr-imported`=5, `readarr`=7. The `*-imported` labels are populated as designed, confirming the Post-Import Category re-labeling is working.

## Applied to all five *arr (2026-07-09; readarr + whisparr 2026-07-17, fix-25 M23)

- Sonarr: `tvImportedCategory = sonarr-imported`
- Radarr (API v3): `movieImportedCategory = radarr-imported`
- Lidarr (API v1): `musicImportedCategory = lidarr-imported`
- Readarr (API v1): `musicImportedCategory = readarr-imported` — **gotcha:** Readarr's Deluge client inherits Lidarr's field names, so the category fields are `musicCategory`/`musicImportedCategory`, not `book*`.
- Whisparr (API v3): `tvImportedCategory = tv-whisparr-imported` (tracked category is `tv-whisparr`)
- Deluge labels `radarr-imported`/`lidarr-imported` created 2026-07-09; `readarr-imported`/`tv-whisparr-imported` created 2026-07-17.
- All five keep `removeCompletedDownloads=False` (seeding preserved).
- The reaper's `LABELS` set covers all five label pairs since fix-25 (below).

## fix-25 (2026-07-17): the silent "grabbed → never imported" class

The 2026-07-16 quality gate found completed torrents piling up in pre-import labels (L42: 273 of 375, because only sonarr had reaper coverage and readarr/whisparr lacked the Post-Import Category), plus grabs silently vanishing or falling out of arr tracking with no error anywhere (H3/H5). Resolution:

1. **Backlog**: `deluge-relabel-imported.py` (in `configs/host/seedbox/`, run from a LAN workstation — the seedbox can't reach the arr APIs) verified each pre-import torrent against the owning arr's history (`/history?downloadId=<hash>` must show an import event) and relabeled confirmed ones to `<label>-imported`: **272 of 273 relabeled**, 1 legitimately in-flight torrent left alone. Unverified torrents are never relabeled — they trip the stuck alarm instead.
2. **Alarm**: `deluge-preimport-stuck.py` (deployed to `~/scripts/`, check id `deluge-preimport-stuck` in `verification/checks.d/seedbox.yaml`) fails when any 100%-complete torrent sits in a pre-import label >48h — guarding the widened reaper: nothing can age toward the 14-day reap unnoticed.
3. **Consumer-end sweep**: `arr-grab-audit.py` on the mini (`verification/checks.d/media.yaml`) probes all five arrs for 'grabbed' history events >48h old with no follow-up event, absent from the queue, and media still fileless (`arr-grabbed-not-imported`, crit) and for monitored+fileless media hidden from wanted/missing by an unmonitored author/artist — the H6/H14 no-retry root cause (`arr-orphan-monitor-flags`, warn). The libreseerr `readarr.py` add-flow was patched the same day to keep authors monitored (`_ensure_author_monitored`, stack `configs/docker-stack/stacks/libreseerr/`).

## `deluge-reaper.py`

Age-based cleanup so the seedbox doesn't fill up. Removes torrents (**+data**) in every *arr label pair (fix-25 widened it from sonarr-only) whose age (`time_added`) ≥ 14 days **and** whose progress is ≥ 99.9%. NAS library copies are untouched. The `manual` label is deliberately excluded. 14 days comfortably satisfies private-tracker seeding requirements (books come from MyAnonamouse). **Default is DRY-RUN**; pass `--live` to actually remove. Logs to `~/logs/deluge-reaper.log`.

Key constants in the script:

```python
DRY = "--live" not in sys.argv
MAX_AGE = 14*86400
ARR_LABELS = {"sonarr", "tv-sonarr", "radarr", "lidarr", "readarr", "tv-whisparr"}
LABELS = ARR_LABELS | {l + "-imported" for l in ARR_LABELS if l != "tv-sonarr"}
LOG = os.path.expanduser("~/logs/deluge-reaper.log")
```

Selection logic: connect to `127.0.0.1:3254` with the parsed `btabaska` auth, pull `client.core.get_torrents_status({}, ["name","label","time_added","progress","state","total_size","ratio"])`, and mark a torrent eligible when `label in LABELS` **and** `progress >= 99.9` **and** `age >= MAX_AGE`. In `--live` mode each eligible torrent is removed with `client.core.remove_torrent(hash, True)` (the `True` second arg removes the data too). Every run logs a summary line (`DRY-RUN`/`LIVE`, count, total GB) plus one `WOULD REMOVE`/`REMOVED` line per torrent (age, ratio, size, truncated name).

### Deploy

```
scp foss-setup/configs/host/seedbox/deluge-reaper.py seedbox:~/scripts/deluge-reaper.py
```

### Cron (installed on betty, 05:00 CEST daily)

```
0 5 * * * ~/venvs/deluge/bin/python ~/scripts/deluge-reaper.py --live >/dev/null 2>>~/logs/deluge-reaper.err
```

### Dry-run anytime

```
ssh seedbox '~/venvs/deluge/bin/python ~/scripts/deluge-reaper.py'
```

!!! note "Validated against live betty (2026-07-14)"
    `~/scripts/deluge-reaper.py` is deployed and the crontab entry matches the documented line exactly (running in `--live` mode at 05:00). The last five `~/logs/deluge-reaper.log` entries (2026-07-10 → 2026-07-14) each read `LIVE: 0 eligible (age>=14d, labels=['sonarr', 'sonarr-imported']), 0.0 GB` — the reaper runs cleanly every day and nothing has yet crossed the 14-day age threshold. `~/logs/deluge-reaper.err` is present and empty (0 bytes).

!!! note "Validated after the fix-25 widening (2026-07-17)"
    The widened reaper's dry-run reports all eleven labels and `0 eligible` (that morning's cron had already reaped the first ≥14d item, a 37.4 GB Simpsons pack). Post-relabel label counts: `sonarr-imported`=341, `radarr-imported`=17, `lidarr-imported`=10, `readarr-imported`=7, `radarr`=3 (in-flight recovery grabs) — no residue in any other pre-import label. The `deluge-preimport-stuck` check runs green (`PREIMPORT_OK`).

---

[← Seedbox & music reference](index.md)

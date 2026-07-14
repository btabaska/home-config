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

## Applied to all three *arr (2026-07-09)

- Sonarr: `tvImportedCategory = sonarr-imported`
- Radarr (API v3): `movieImportedCategory = radarr-imported`
- Lidarr (API v1): `musicImportedCategory = lidarr-imported`
- Deluge labels `radarr-imported` / `lidarr-imported` created.
- All three keep `removeCompletedDownloads=False` (seeding preserved).
- The reaper's `LABELS` set could be widened to include `radarr*`/`lidarr*` labels later if those need disk reclamation too.

## `deluge-reaper.py`

Age-based cleanup so the seedbox doesn't fill up. Removes torrents (**+data**) in labels `sonarr`/`sonarr-imported` whose age (`time_added`) ≥ 14 days **and** whose progress is ≥ 99.9%. NAS library copies are untouched. **Default is DRY-RUN**; pass `--live` to actually remove. Logs to `~/logs/deluge-reaper.log`.

Key constants in the script:

```python
DRY = "--live" not in sys.argv
MAX_AGE = 14*86400
LABELS = {"sonarr", "sonarr-imported"}
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

---

[← Seedbox & music reference](index.md)

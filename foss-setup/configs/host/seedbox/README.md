# Seedbox (Bytesized "betty") — Deluge queue hygiene

Deluge runs on the seedbox (`betty.bysh.me`, no root). Sonarr/Radarr/Lidarr on the
NAS import from it over a mount (cross-machine → imports are **copies**, so the NAS
library and the seedbox torrent data are independent copies).

## Deluge RPC access (for scripts)
- Daemon: `127.0.0.1:3254`, `allow_remote: true`. Label plugin enabled.
- Auth: local `btabaska` creds in `~/.config/deluge/auth` (scripts parse it; never print the value).
- Driver: the venv python `~/venvs/deluge/bin/python` has the `deluge` lib.
- `deluge-console` exists (`~/.local/bin/deluge-console`) but the Label plugin's console
  command is NOT registered — use the RPC (`client.label.*`) instead.

## The "57-item Sonarr queue" fix (2026-07-09)
Root cause: Sonarr's Deluge client had **no Post-Import Category** and
`removeCompletedDownloads=False`, so imported torrents stayed in the `sonarr` label,
got re-scanned, pinned with "already imported" *warnings*, and never left the queue.

Fix (keeps seeding, clears queue):
1. Deluge label `sonarr-imported` created.
2. Sonarr → Settings → Download Clients → Deluge → **tvImportedCategory = `sonarr-imported`**.
   On successful import Sonarr re-labels the torrent out of the tracked `sonarr` label →
   it leaves the queue while Deluge keeps seeding. `removeCompletedDownloads` stays False.
3. Existing stuck torrents were relabeled `sonarr` → `sonarr-imported` once.

## deluge-reaper.py
Age-based cleanup so the seedbox doesn't fill up. Removes torrents (+data) in labels
`sonarr`/`sonarr-imported` whose age (`time_added`) ≥ 14 days. NAS library copies are
untouched. **Default is DRY-RUN**; pass `--live` to actually remove. Logs to
`~/logs/deluge-reaper.log`.

Deploy:
```
scp foss-setup/configs/host/seedbox/deluge-reaper.py seedbox:~/scripts/deluge-reaper.py
```
Cron (installed on betty, 05:00 CEST daily):
```
0 5 * * * ~/venvs/deluge/bin/python ~/scripts/deluge-reaper.py --live >/dev/null 2>>~/logs/deluge-reaper.err
```
Dry-run anytime: `ssh seedbox '~/venvs/deluge/bin/python ~/scripts/deluge-reaper.py'`

## Not yet done
- Radarr (`radarr` label, 4 torrents) and Lidarr (`lidarr`, 5) have the SAME latent gap
  — no Post-Import Category set. Apply the same `*ImportedCategory` fix if their queues clog.

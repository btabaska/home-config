# Seedbox (Betty) — Deluge queue hygiene

> How Deluge runs on the Bytesized seedbox "betty", the RPC access pattern for scripts, the *arr queue-clog fix (Post-Import Category), and the age-based `deluge-reaper.py` cleanup.

_Source: `foss-setup/configs/host/seedbox/README.md` · migrated + validated 2026-07-14_

Deluge runs on the seedbox (`betty.bysh.me`, **no root**). Sonarr/Radarr/Lidarr on the NAS import from it over a mount (cross-machine → imports are **copies**, so the NAS library and the seedbox torrent data are independent copies). Deleting seedbox torrent data is therefore safe for the library.

## Deluge RPC access (for scripts)

- Daemon: `127.0.0.1:3254`, `allow_remote: false` (fix-21 loopback lockdown — the RPC daemon binds `127.0.0.1` only, so **on-box scripts** connect over localhost; remote consumers reach it over the tailnet, see below). Label plugin enabled.
- Auth: local `btabaska` creds in `~/.config/deluge/auth` (scripts parse the `btabaska:<pass>:<lvl>` line; **never print the value**).
- Driver: the venv python `~/venvs/deluge/bin/python` has the `deluge` lib.
- `deluge-console` exists (`~/.local/bin/deluge-console`) but the Label plugin's console command is **NOT registered** — use the RPC (`client.label.*`) instead. `deluge-console` also defaults to the stale port `58846`, so it fails to connect without an explicit host/port.
- RPC API surface: `client.connect("127.0.0.1", 3254, user, pw)`, then `client.label.get_labels()` / `client.label.add()` / `client.label.set_torrent()`, `client.core.get_torrents_status({}, [fields])`, `client.core.remove_torrent(hash, remove_data)`. Scripts run **on betty** (via `ssh seedbox`) and always use `127.0.0.1` — remote RPC is disabled (`allow_remote: false`).
- Remote consumers (the NAS *arr download-clients) do **not** use `:3254`; they reach the seedbox-managed Deluge over the **tailnet** at the seedbox tailscale node `100.119.134.94` (fix-21 repointed them there off the public interface).

!!! note "Validated against live betty (2026-07-14)"
    Reached over the working `ssh seedbox` alias (the older memory note claimed this alias was broken and required the tailscale IP — it now works directly). Deluge `core.conf` confirms `"daemon_port":3254`, `"allow_remote":true` (**flipped to `false` by fix-21 on 2026-07-17 — see the next note**), and `"enabled_plugins":["Bytesized","Label","ltConfig","AutoAdd"]`. `deluge-console` with no args tried `127.0.0.1:58846` and got `Connection refused` — confirming the port gotcha and the "use RPC on :3254" rule.

!!! note "Updated after the fix-21 tailnet lockdown (re-verified 2026-07-26)"
    Live `core.conf` now reads `"allow_remote":false`, and `ss -tlnp` on betty shows `deluged` listening on **`127.0.0.1:3254`** only (loopback) — remote RPC is off. On-box scripts (`deluge-reaper.py`, the seedbox half of `deluge-relabel-imported.py`) are unaffected because they connect over `127.0.0.1`. The NAS *arr download-clients were repointed to the seedbox's **tailnet** address `100.119.134.94` (its tailscale node, `tailscale status`), off the public interface.

### Deluge daemon facts (from live `core.conf`)

| Setting | Value |
| --- | --- |
| `daemon_port` | `3254` |
| `allow_remote` | `false` (fix-21 loopback lockdown; was `true` pre-2026-07-17) |
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

### media-07 (2026-07-26): closing the Lidarr artist generator

fix-25 patched libreseerr's author half but the **musicseerr** artist half stayed open: musicseerr `v1.4.2` is an upstream image with no bind-mounted code and no monitor-artist config knob, so it can still add a Lidarr artist with `monitored=false` for a single-album request, leaving that album invisible to wanted/missing (`arr-orphan-monitor-flags` fired again 2026-07-26 with 5 such albums — Charli xcx ×4, Glass Animals "Heat Waves").

The generator is closed **downstream**, source-agnostic: a 15-min mini timer (`configs/host/mini/lidarr-reconcile/`, `lidarr-artist-monitor-reconcile.py`) enforces the invariant *"if any album is monitored, its artist must be monitored"* — it flips `artist.monitored=true` for any artist owning a monitored + zero-byte album (the exact tripwire condition). It never touches album flags and never triggers a search (Lidarr does no automatic missing search here), so it only makes an already-requested album retryable; no surprise grabs. Idempotent. `arr-orphan-monitor-flags` is the outcome probe (stays green because orphans are cleared within 15 min); `lidarr-reconcile-timer-healthy` catches the reconciler silently stopping; `OnFailure=ntfy` alerts on a hard failure. These mini host units are **not** ansible-managed — deploy per the dir's `README.md`.

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

## fix-54 (2026-08-02): quota EDQUOT dropped payloads + the 3–4 day import stall

The 2026-08-02 fleet sweep found Sonarr looping **"Import failed, path does not exist"** every few minutes for 3–4 days on two grabs that Deluge still reported *"Seeding 100%"* — but whose on-disk payload was **gone**. Root cause is **not** the reaper (log-proven: it only reaps ≥14d torrents and removes the whole torrent; these were 4d old and still present). It is the **user quota**.

**The binding constraint is the quota, not the 17 TB disk.** `quota -s` for `btabaska`: soft `2862G` / hard `2909G`, sitting at 88–94% full. At that fill `deluged.log` fills with `[Errno 122] Disk quota exceeded`, which causes two silent failures:

1. **Payload dropped under a live "Seeding" torrent** (SH2/SH9) — data can't be written/kept, but Deluge keeps claiming Seeding from stale state (no recheck), so the arr polls `/seedbox/tv/<name>` forever. All wedged episodes were already satisfied in the library from an alternate release → the wedges were **redundant duplicate grabs**; cleared (removed + blocklisted), no re-grab needed.
2. **`label.conf` write fails under EDQUOT** → Deluge can't persist a Post-Import Category relabel → completed torrents stay in a pre-import label (`sonarr`) → `deluge-preimport-stuck` churn (SM28). Also strands lost-label grabs at `~/files/` root (SM26 `move_completed` wedge, e.g. HotD S02E07 100%-but-Downloading).

**Guards added (fix-54):**

- **`deluge-payload-audit.py`** (`~/scripts/`, check `deluge-payload-present`) — probes Deluge's Seeding claim against disk truth for the **import-pipeline population** (pre-import labels; empty-label for the wedge). Fails on any pre-import torrent Seeding 100% with a missing payload, or a 100%-but-Downloading `move_completed` wedge. Catches the class at the source before the arr loops. `-imported` torrents are out of scope (they routinely lose their seedbox copy to reaping — a seeding-ratio concern, not an import break).
- **`seedbox-quota-headroom`** (inline `quota -s` awk) — the **root-cause tripwire**. Fails when usage crosses the soft limit *or* headroom-to-hard drops under 100 G, i.e. **before** EDQUOT forces the next payload drop. Durable reclaim of the structural over-commit is `media-09` (~200 G un-extracted RARs) + `media-10` (retire readarr labels).
- **`arr-queue-reconcile`** (mini systemd timer, every 4h; `configs/host/mini/arr-queue-reconcile/`) — the **self-clean generator-closer**. Removes Sonarr/Radarr queue records stuck `warning` >72h that are either already **satisfied** (redundant dup → remove+blocklist, no re-grab) or a terminal **dead-end** (`No files found` / `path does not exist` / `Not an upgrade` → remove+blocklist and let the arr re-search). Still-fileless **wrong-series/movie maps** ("matched … by ID") are deliberately **left for a human**. Guarded by `arr-queue-reconcile-timer-healthy`; `arr-queue-stale-records` is the age-based backstop (anything `warning` >96h = the closer died or a wrong-map needs attention).

!!! note "Validated (2026-08-02)"
    After clearing the wedges, `sonarr-queue-stuck` dropped 16→5 and `radarr-queue-stuck` 9→0; `media-arr-file-quality` is `WATCHABLE_OK bad=0` (Leverage S05 samples + a John Wick sample purged, real files re-adopted). Audit-safe run: `deluge-payload-present` = `PAYLOAD_OK checked=78`, `seedbox-quota-headroom` = `QUOTA_OK headroom_to_hard=189G`, `arr-queue-reconcile-timer-healthy` = `RECONCILE_TIMER_OK`, `arr-queue-stale-records` = `STALEQ_OK`. ~24 GB freed on the seedbox by removing the confirmed-redundant wedged/stale torrents (Better.Off.Ted, A.Knight S01E03, HotD S02E07/S03E05/S03E06, Jackass, Passengers). Residual (out of scope, → fix-55/56): ~196 already-`-imported` torrents seed with no on-disk copy (quota cleanup), a ratio concern only.

---

[← Seedbox & music reference](index.md)

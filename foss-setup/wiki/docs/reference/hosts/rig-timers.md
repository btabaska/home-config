# rig — background timers (music mirror + AI-stack watchdog)

> The three systemd timers running on the rig (192.168.10.12): two that keep `~/Music` mirrored from the NAS master library, and one dead-man watchdog for the container→host Ollama hop.

_Source: `foss-setup/configs/host/rig/music-mirror/music-mirror.service`, `foss-setup/configs/host/rig/music-mirror/music-mirror.timer`, `foss-setup/configs/host/rig/music-mirror/nas-music-mirror.service`, `foss-setup/configs/host/rig/music-mirror/nas-music-mirror.timer`, `foss-setup/configs/host/rig/ai-stack-watchdog/ai-stack-watchdog.service`, `foss-setup/configs/host/rig/ai-stack-watchdog/ai-stack-watchdog.timer` · migrated + validated 2026-07-14_

## Overview

The rig runs two `oneshot`-service + `.timer` pairs, all installed under `/etc/systemd/system/` and enabled:

| Timer | Schedule (OnCalendar) | Service it triggers | What it does |
|---|---|---|---|
| `nas-music-mirror.timer` | `*-*-* 05:00:00` (host TZ) | `nas-music-mirror.service` | **Sole** `~/Music` mirror — transcode FLAC→ALAC (.m4a), copy mp3/aac verbatim, prune orphans; pings the `music-mirror-rig` dead-man |
| `ai-stack-watchdog.timer` | `*:0/10` (every 10 min) | `ai-stack-watchdog.service` | Dead-man ping for the open-webui→host Ollama hop |

!!! success "media-06 resolved (2026-07-14): one authoritative ~/Music mirror"
    There used to be a **second** pair, `music-mirror.timer`/`.service` (05:30) that did `rsync -rt --delete-after /mnt/nas-music-ro/ ~/Music/` — a *verbatim* mirror. It copied FLAC onto the rig and, worse, its `--delete-after` removed the `.m4a` files the 05:00 ALAC job had just made (they don't exist on the NAS source), so the two fought nightly. Per the owner's decision (**ALAC on the rig, FLAC on the NAS, no duplicates**), the rsync pair was **retired** (unit files removed) and the leftover `~/Music/*.flac` deleted. `nas-music-mirror.service` is now the single source and inherited the `music-mirror-rig` healthchecks dead-man via `ExecStartPost`. Guarded by the `rig-music-no-flac` verification check.

---

## 1. nas-music-mirror — FLAC→ALAC iPod mirror (05:00)

Keeps `~/Music` on the rig as an **iPod-Classic-playable** mirror of the NAS master library. The iPod Classic can't play FLAC/hi-res, so FLAC is transcoded to ALAC; already-native formats are copied verbatim.

### Timer — `nas-music-mirror.timer`

```ini
[Unit]
Description=Keep ~/Music mirrored from the NAS (daily) for iPod sync

[Timer]
OnCalendar=*-*-* 05:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

- Fires daily at **05:00** (host local time — no explicit TZ, so uses the rig's timezone, EDT).
- `Persistent=true` — catches up a missed run after downtime.
- `RandomizedDelaySec=300` — jitters the start up to 5 min.

### Service — `nas-music-mirror.service`

```ini
[Unit]
Description=Mirror NAS music library -> ~/Music as iPod-playable ALAC/MP3
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=btabaska
Nice=10
IOSchedulingClass=idle
ExecStart=/home/btabaska/bin/nas-music-to-alac-mirror.sh
```

- `Type=oneshot`, runs as user `btabaska`, `Nice=10` + `IOSchedulingClass=idle` so it never starves foreground work.
- ExecStart runs the deployed script at `/home/btabaska/bin/nas-music-to-alac-mirror.sh` (source: `foss-setup/configs/host/rig/music-mirror/nas-music-to-alac-mirror.sh`).

### What the script does

Source: NAS `/volume1/music` mounted read-only at `/mnt/nas-music-ro` → destination `~/Music`. Key env defaults: `SRC=/mnt/nas-music-ro`, `DST=$HOME/Music`, `LOG=$HOME/nas-alac-mirror.log`, `LOCK=$HOME/.nas-alac-mirror.lock`.

Behaviour:

- **Single-instance lock** via `flock -n` on `~/.nas-alac-mirror.lock` — a second start exits cleanly.
- **Automount trigger + safety gate**: `ls "$SRC"` triggers the automount, then counts FLAC files (`find ... -iname '*.flac' | head -400 | wc -l`). If **fewer than 20 FLACs** are seen, it ABORTS (`exit 1`) before pruning — a NAS blip must never wipe the mirror.
- **Mirror pass** over `*.flac *.mp3 *.m4a *.aac` (excluding `#recycle` and `@eaDir`):
  - FLAC → ALAC `.m4a`: skips if target is newer (`-nt`). Otherwise `ffprobe` reads the sample rate; if >48000, downsamples with `-ar 48000`. Transcodes with `ffmpeg -c:a alac -sample_fmt s16p` (16-bit, ≤48 kHz), copies embedded cover art (`-map 0:v? -c:v copy -disposition:v:0 attached_pic`), `-map_metadata 0 -movflags +faststart`. Writes to a `.converting.m4a` temp, verifies the codec is `alac` via ffprobe, then `mv -f` into place.
  - MP3/AAC/M4A → copied verbatim (`cp -p`), skipping when the source is not newer than the target.
- **Orphan prune (pass 2)**: for every `.m4a/.mp3/.aac` in `~/Music`, if no corresponding NAS source exists (checks `.flac/.m4a/.aac/.mp3` variants of the relative path), it is `rm -f`'d; then empty dirs are deleted.
- Logs a summary line: `converted=N copied=N skipped=N failed=N pruned=N`.

!!! note "Validated against live rig (2026-07-14)"
    `/mnt/nas-music-ro` is an `autofs` (systemd automount) mount, confirming the script's `ls "$SRC"` automount-trigger pattern. `~/Music` is populated (contains real artist dirs: `All Time Low`, `Beyoncé`, `Billie Eilish`, `blink-182`, `Bowling for Soup`, ...). Installed `ExecStart` = `/home/btabaska/bin/nas-music-to-alac-mirror.sh` as in the source.

---

## 2. music-mirror — verbatim rsync mirror (RETIRED 2026-07-14, media-06)

**Retired.** This pair (`music-mirror.timer` 05:30 + `music-mirror.service`) ran a
verbatim `rsync -rt --delete-after /mnt/nas-music-ro/ ~/Music/`. It copied FLAC onto
the rig and its `--delete-after` wiped the `.m4a` files the 05:00 ALAC job produced
(they don't exist on the NAS source), so the two mirrors fought nightly. Per the
owner's decision — **ALAC on the rig, FLAC on the NAS, no duplicates** — the unit
files were removed, the leftover `~/Music/*.flac` deleted, and `nas-music-mirror.service`
(§1) is now the sole mirror; it inherited the `music-mirror-rig` healthchecks dead-man
(`ExecStartPost` pinging `https://health.tabaska.us/ping/c7b523e2-…`). Guarded by the
`rig-music-no-flac` verification check. See the success banner at the top of this page.

---

## 3. ai-stack-watchdog — container→host Ollama dead-man (every 10 min)

A dead-man ping for the **container→host Ollama hop** on the rig. Why it exists (2026-07-09): a UFW hardening pass scoped port 11434 to LAN+tailnet and silently dropped docker-subnet traffic, so open-webui/litellm couldn't reach host-native Ollama ("no models available") while every external port probe stayed green. This probe runs from INSIDE the open-webui container — the only vantage point that sees that hop — and reports to healthchecks (mini:8001, check `ai-stack-rig` → ntfy phone alert). It does **no inference** (zero GPU cost, immune to model-queue latency).

### Timer — `ai-stack-watchdog.timer`

```ini
[Unit]
Description=AI stack watchdog every 10 minutes

[Timer]
OnCalendar=*:0/10
RandomizedDelaySec=30
Persistent=true

[Install]
WantedBy=timers.target
```

- `OnCalendar=*:0/10` — fires at minute 0, 10, 20, 30, 40, 50 of every hour.
- `RandomizedDelaySec=30` (≤30 s jitter), `Persistent=true`.

### Service — `ai-stack-watchdog.service`

```ini
[Unit]
Description=AI stack watchdog: container->host ollama hop -> healthchecks dead-man
After=docker.service ollama.service
Wants=docker.service

[Service]
Type=oneshot
EnvironmentFile=/etc/ai-stack-watchdog.env
ExecStart=/usr/local/bin/ai-stack-watchdog.sh
```

- `Type=oneshot`, ordered `After=docker.service ollama.service`, `Wants=docker.service`.
- `EnvironmentFile=/etc/ai-stack-watchdog.env` supplies `PING_URL` (file is `root:root 600`; vault key `healthchecks.ai_stack_rig_ping_url`).
- ExecStart = `/usr/local/bin/ai-stack-watchdog.sh` (source: `foss-setup/configs/host/rig/ai-stack-watchdog/ai-stack-watchdog.sh`).

### What the script does

`set -u`; requires `PING_URL` (fails loudly if the EnvironmentFile didn't set it).

The `probe()` function execs inside the container:

```bash
docker exec open-webui python3 -c "
import urllib.request
urllib.request.urlopen('http://host.docker.internal:11434/api/version', timeout=8)
"
```

Logic:

- If the probe succeeds → `curl` the healthchecks `PING_URL` (success ping).
- If it fails → `sleep 15` (ride out a container restart / ollama bounce) and re-probe. On second success, ping success.
- If it still fails → ping `"$PING_URL/fail"` with a `--data-raw` body: `container->host ollama probe failed (open-webui -> host.docker.internal:11434); check rig UFW 172.16.0.0/12 allow on 11434, ollama.service, docker`.

!!! note "Validated against live rig (2026-07-14)"
    `ollama.service` is `active` + `enabled`; `/etc/ai-stack-watchdog.env` EXISTS; the `open-webui` container is running (`docker ps`), so the `docker exec open-webui ...` probe path is live. Installed `ExecStart` = `/usr/local/bin/ai-stack-watchdog.sh` as in the source. Last run `Result=success`.

---

## Operations quick reference

```bash
# status of all three timers + next-fire
ssh rig "systemctl status music-mirror.timer nas-music-mirror.timer ai-stack-watchdog.timer --no-pager"
ssh rig "systemctl list-timers --no-pager | grep -E 'music|ai-stack'"

# run a job on demand (the .service, not the .timer)
ssh rig "systemctl start nas-music-mirror.service"   # ALAC transcode mirror (the sole ~/Music mirror)
ssh rig "systemctl start ai-stack-watchdog.service"  # ollama hop probe

# logs
ssh rig "journalctl -u nas-music-mirror.service -n 50 --no-pager"
ssh rig "tail -n 50 ~/nas-alac-mirror.log"           # ALAC script's own log
```

Related live state (2026-07-14): NAS music master lives at `/volume1/music`, mounted read-only on the rig at `/mnt/nas-music-ro` (autofs); host-native Ollama listens on `11434`; open-webui reaches it via `host.docker.internal:11434`; healthchecks front-end is `health.tabaska.us` (checks `music-mirror-rig`, `ai-stack-rig`).

---

[← Host internals reference](index.md)

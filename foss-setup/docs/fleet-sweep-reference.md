# Fleet-sweep reference — access, chains, logs, drift, output formats

> Companion to the **`/fleet-sweep`** command (`.claude/commands/fleet-sweep.md`). This is the
> fleet-specific playbook a sweep session loads instead of re-deriving it: working access recipes,
> the end-to-end chain matrix, log surfaces, the failure-pattern taxonomy (what has actually broken
> here before), drift axes, known-normal states, and the exact output formats the fix queue needs.
> All commands were verified live **2026-08-02**. Counts (containers, checks, vhosts) drift —
> re-verify against live before citing them as findings; the *recipes* are the durable part.

---

## 1. Host access recipes (read-only)

Vault = `foss-setup/.handoff-secrets.yaml` (gitignored, chmod 600, exists ONLY on the operator
Mac). Read values with `python3` + `yaml` into a shell variable and pipe them — **never echo, never
paste into chat/commits/docs**; refer to secrets by key path.

**mini** (Ubuntu Mac mini `192.168.10.2` — passwordless sudo + docker group, no vault needed):

```sh
ssh -o ConnectTimeout=10 mini 'docker ps -a --format "{{.Names}}\t{{.State}}\t{{.Status}}"; systemctl --failed --no-legend; df -h /; uptime'
ssh mini 'docker inspect --format "{{.Name}} restarts={{.RestartCount}}" $(docker ps -aq) | grep -v "restarts=0"'
```

Hazard: `{{.State.Health.Status}}` aborts the whole template for containers *without* a healthcheck
(nil Health) — lines silently vanish. Use the `(healthy)`/`(unhealthy)` suffix in `{{.Status}}`.

**nas** (Synology DS920+ `192.168.10.4` — no docker socket for the ssh user, no passwordless sudo,
SFTP/scp disabled, full docker path required):

```sh
PW=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['sudo']['nas_password'])")
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker ps -a --format "{{.Names}}\t{{.Status}}" 2>/dev/null'
# compound commands (command substitution needs root on both sides) — wrap in sh -c:
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c '"'"'/usr/local/bin/docker inspect --format "{{.Name}} restarts={{.RestartCount}}" $(/usr/local/bin/docker ps -aq)'"'"' 2>/dev/null'
```

`2>/dev/null` hides the sudo prompt; `df -h /volume1 /volume2 /volume3` needs no sudo. Beware the
cached-cred fall-through hazard (memory `sudo-stdin-append-hazard`): if sudo doesn't consume the
stdin password it lands in the next command's stdin. Move files with `ssh nas 'cat > path'`, never
scp. Never add raw cron lines (DSM rewrites `/etc/crontab`) — `.task` files in
`/usr/syno/etc/synoschedule.d/root/` only.

**rig** (CachyOS `192.168.10.12` — docker + journalctl work WITHOUT sudo; sudo password at vault
`sudo.rig_password`, not needed for read ops):

```sh
ssh rig 'docker ps -a --format "{{.Names}}\t{{.Status}}"; systemctl --failed --no-legend; systemctl list-timers --no-pager --no-legend; df -h /; nvidia-smi --query-gpu=memory.used,memory.total --format=csv'
```

**seedbox** (Bytesized "betty" — no root, no systemctl; everything is user processes; tailnet
`100.119.134.94`):

```sh
ssh -o ConnectTimeout=15 seedbox 'uptime; ps -u $(whoami) -o pid,etime,comm | grep -Ei "deluge|slskd|tailscale|syncthing"; df -h "$HOME" | tail -1'
```

Shared host: 29 users, load 40–57 is normal and NOT ours.

**ha** (Home Assistant Green `192.168.10.50:8123` — LAN-only, NOT on tailnet, SSH refused;
REST/WS only, token at vault `hosts.ha.api_token`):

```sh
TOK=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['hosts']['ha']['api_token'])")
curl -s -m 10 -H "Authorization: Bearer $TOK" http://192.168.10.50:8123/api/config
curl -s -m 15 -H "Authorization: Bearer $TOK" http://192.168.10.50:8123/api/states   # array of {entity_id,state,attributes,...}
```

**Self-sourced credentials** (no vault entry): Seerr key = mini
`/opt/stacks/seerr/config/settings.json` `main.apiKey`; Prowlarr key = NAS
`/volume1/docker/prowlarr/config/config.xml`; Syncthing hub key = NAS
`/volume1/docker/syncthing/config/config.xml`; RomM DB = container's own `MARIADB_ROOT_PASSWORD`.
arr API keys also live in each app's `config.xml` (600 root — sudo) and in mini
`/etc/verification/env`.

**Fixed identifiers**: rig tailnet `cachyos.tailb31641.ts.net`; playit public IP `69.9.181.17`
(Java 1105, Bedrock 1111); Plex machineIdentifier `70ffcfbb5dc9389e315070cf3a8af99c5fb340b4`; Plex
sections 1=Movies 2=TV 4=YouTube; n8n bug form `/form/8f2c1a4b-6d3e-4a90-b1c2-a1b2c3d4e5f6`.

---

## 2. Harvesting the verification framework

The runner already probes 300+ conditions — harvest it before any fan-out.

- Checks: repo `foss-setup/verification/checks.d/*.yaml` (35 files ≈ 302 checks), deployed to mini
  `/opt/verification/checks.d/`. Schema per check: `id`, `name`, `host`
  (mini|nas|rig|seedbox|url|local), `cmd`, `expect` (regex on **stdout only**) or `expect_exit`,
  `severity` (crit|warn|info), `task_id`, `runbook`, `enabled`; optional `tier` (fast|daily),
  `timeout`.
- **Audit-safe full run** (touches no scheduled state, pages nobody, never WoLs — ~8 min, 296
  enabled checks):

  ```sh
  ssh mini 'mkdir -p /tmp/verify-audit && VERIFICATION_STATE_DIR=/tmp/verify-audit /opt/verification/bin/run-checks.sh --no-notify --json'
  ```

  Run backgrounded or with a 600000 ms timeout. NEVER run an unfiltered sweep without
  `VERIFICATION_STATE_DIR` — it overwrites `/var/lib/verification/{results.json,…}` and pages ntfy.
  Never run as root. `--host <file-stem>` runs one domain (resurrects `enabled:false` unless
  `--respect-enabled`); there is no per-check-id selector.
- **State/history** on mini `/var/lib/verification/`: `results.json` (last daily sweep;
  `checks[].{id,status,output,…}`), `last-summary.md`, `reopen-suggestions.json` (authoritative
  failure→task_id bridge), `acks.json` (deliberately suppressed failures — exclude from findings),
  `triage-YYYY-MM-DD.md` (per-day failure history since 2026-07-08 — fastest historical index;
  LLM verdicts capped at 15/run and often malformed, don't assume coverage).
- **Healthchecks dead-man state** (the stale-last-success oracle), key at vault
  `healthchecks.api_key`:

  ```sh
  HK=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['healthchecks']['api_key'])")
  curl -s -H "X-Api-Key: $HK" https://health.tabaska.us/api/v3/checks/   # flag status != up, or last_ping > period+grace
  ```

- **Hazards**: never shell-source mini `/etc/verification/env` (a Hardcover JWT spans physical
  lines; sourcing echoes the token — sec-12); verification units exiting 1 means *checks* failed,
  not the runner (read results.json, not unit state); `expect` never sees stderr; deploy checks
  only via `scripts/verification/deploy.sh` or `ssh sudo tee` (scp to root-owned tree fails
  silently), then confirm ids appear in a run.

---

## 3. Service-chain matrix (end-to-end)

For each chain: hops → existing check coverage → the consumer-end probe. "Consumer" means the thing
a user actually touches — mandate 1. Chains marked **⚠ gap** have no e2e check on the named leg.

**movies-tv** (mini+nas+seedbox): seerr :5055 → Sonarr :8989 / Radarr :7878 → Prowlarr :9696
(+flaresolverr, bitmagnet) → Deluge on seedbox (loopback binds, via tailnet 100.119.134.94) → NAS
rclone SFTP mount `/volume1/mounts/seedbox-files` (shared SPOF) → unpackerr → import (/tv=/volume3,
/movies=/volume2) → Plex :32400 + Jellyfin :8096. Dense check coverage (seedbox-arr-deluge-e2e,
arr-grabbed-not-imported, arr-plex-parity, media-arr-file-quality, seerr-request-rot, …). Probe:
arr `/api/v3/queue` warning count; downloadclient `/test` POST; `arr-plex-journey.py` COVERAGE_OK.

**music** (mini+nas+seedbox+rig): musicseerr :8688 → Lidarr :8686 → Prowlarr/Deluge AND soularr →
slskd (seedbox :5030) → /volume1/music → Navidrome (mini, RO CIFS) + Plex + rig ALAC mirror.
Checks: musicseerr-phantom-requests, seedbox-slskd-e2e, navidrome-library-present, … Probe:
`musicseerr-phantom-requests.py`; navidrome.db `media_file.missing=1` count (missing=greyed-out).

**books** (mini+nas+seedbox): libreseerr :8789 → Bookshelf (NAS :8790) → rreading-glasses-hc →
Prowlarr → Deluge ('bookshelf' category) → readarr-copy-to-cwa-ingest.sh → CWA ingest → Calibre
metadata.db → Kobo sync tokened URLs + KOSync. Densest coverage in the fleet
(cwa-kobo-sync-consumer, books-pipeline-lost-imports, hardcover-token-valid, …). Probe: curl the
`CWA_KOBO_SYNC_URL_*` (vault `cwa.kobo_api_endpoint_*`) expecting 200 + parseable JSON.

**shelfmark** (nas+seedbox): Shelfmark :8084 → MAM/Deluge → seedbox mount (must be
mount-propagation **rshared** — a NAS reboot resets it to private and silently breaks copies) →
CWA ingest. Check: shelfmark-mam-path-ready.

**audiobooks+iPod** (nas+rig): ABS :13378 → apps/widget; read-19 leg: NAS RO SMB → rig CIFS →
abs-ipod-stage.timer 05:30 → manual libgpod push. Checks: audiobookshelf-libraries-consumer,
ipod-abs-stage-fresh (MOUNTED_UNSYNCED passes by design).

**manga + comics** (rig+nas+mini): Suwayomi (rig :4567) → persistent CIFS `/mnt/nas-manga` →
`/volume1/manga` → Komga :25600 (JVM ~2 min cold start); Mylar3 :8090 → GetComics DDL/Deluge →
`/volume1/comics` → Komga. Checks: suwayomi-feeds-komga, mylar3-feeds-komga,
komga-libraries-consumer (real page-stream + OPDS).

**photos** (nas+rig+mini): upload → Immich :2283 → ML on rig :3003 **night-window 01–07 EDT only**
(day = NAS iGPU fallback; "rig ML down by day" is NORMAL) → smart search. Checks:
immich-smart-search-consumer (crit), rig-immich-ml-window, nas-immich-backup-freshness. Probe:
POST `/api/search/smart` via the public vhost with vault `immich.verify_api_key`.

**youtube** (mini+nas): Pinchflat :8945 + MeTube :8081 + bgutil-pot :4416 (plugin zip must
version-match server; POT can't beat LOGIN_REQUIRED) → `/mnt/nas-youtube` (new DSM shares lack the
PlexMediaServer ACE) → Plex section 4; audio → beets → Navidrome. Checks: pinchflat-plex-visible
(crit), plex-youtube-readable, pinchflat-pot-provider, nas-beets-ingest-fresh.

**subtitles** (nas): Sonarr/Radarr → Bazarr :6767 → Podnapisi (sole provider, rate-limited —
provider search deliberately unprobed) → subs beside media. Check: bazarr-synced-from-arrs
(both SignalR feeds LIVE).

**kometa** (mini→nas): scheduled batch → Plex collections. `kometa-run-clean` parses meta.log
(kometa always exits 0; env beats CLI). **⚠ gap**: no Plex-side collection outcome assertion.

**journaling** (mini+rig): Memos :5230 webhook → n8n `/webhook/journal` (loop-guarded) →
faster-whisper :8010 (`/health`, not `/v1/models`) → rig `dolphin-venice-24b` (best-effort, OOMs
while Immich ML resident) → memos comment. Checks: journaling-loop-e2e
(E2E_OK|SKIP_COACH_UNAVAILABLE), journaling-whisper-transcribes (tier daily).

**ai-llm-serving** (rig+mini+ha): clients (OWUI, Lumiverse, Marinara, Continue.dev, HA Assist) →
llm.tabaska.us / rig :4000 LiteLLM (**DB-backed virtual keys — the hop that 503s while master-key
liveness stays green**) → llama-swap :9292 (one big model at a time) → GGUF models; ollama :11434 =
compat shim (llama3.2:3b, KEEP_ALIVE=0). Checks: rig-litellm-vkey-e2e, rig-ai-e2e,
rig-ai-gpu-yield, rig-llm-scoped-keys-public. Probe with a VIRTUAL key on model `utility`/`fast`
(vault `ai_stack.litellm_verify_key`) — reasoning models return empty on small max_tokens.

**ai-image-gen** (rig+mini): frontends → comfyui.tabaska.us → gpu-arbiter :8189 (recreate-not-
restart caveat) → ComfyUI :8188 (3 model stacks via /object_info). Marinara's real auth gate is
mini Caddy basic_auth (its own auth is void behind userland-proxy). **⚠ deliberate gap**: no
recurring real image generation.

**ai-ops-agent** (rig): OWUI → mcpo :8000 → fleet-mcp :8765. Check: rig-ops-agent-e2e (real tool
call through the LLM).

**wiki-RAG** (mini→rig): wiki site → wiki-rag-sync.timer 05:10 → OWUI knowledge collection.
Check: mini-wiki-rag-fresh (producer only). **⚠ gap**: retrieval end unprobed.

**monitoring-alerting** (fleet): checks runner → ntfy `verification` topic → Healthchecks
dead-mans / Uptime Kuma (47 monitors) / Beszel / Diun → Homepage tiles (truth =
`curl -H 'Host: home.tabaska.us' http://localhost:3010/api/services`, never the HTML shell).
**⚠ gap**: no synthetic "alert reached a device" test.

**bug-intake** (mini+rig): Homepage tile → n8n form → Forgejo issue (home/household-bugs) → ntfy
`bugs` + Discord; triage: bug-triage-evidence → rig LLM → issue comment. Checks: bug-intake-e2e
(crit), bug-triage-e2e (SKIP_MODEL_UNAVAILABLE-aware).

**git-control-plane** (mini+rig): ~/GitHub/Home → publish-deploy.sh pushes origin(GitHub) +
forgejo(mini:2222) → nightly ansible-pull mini+rig; /opt/stacks own repo (secrets inside — NEVER
`git add -A`); dotfiles chezmoi; rig local-ai-tooling dual-remoted. Checks: git-stacks-clean,
stack-mirror-drift, wiki-drift, unit-file-drift, ai-tooling-clean-pushed,
ansible-site-converged-mini.

**backups** (fleet): restic mini/rig → B2 (immutability PROVEN by attempted delete →
b2-restic-immutable); NAS Hyper Backup → B2; immich pg dump (DSM task 9); HA → NAS
(ha-backup-offsite-fresh crit); AMP zips; ludusavi → Syncthing. **⚠ gap**: no restore drill on any
leg.

**syncthing-mesh** (nas hub + mini + rig): direct LAN only — relays/global discovery disabled;
transport must be tcp/quic, `relay` = cloud leak. Checks: syncthing-hub-mesh-direct,
game-saves-mesh-synced.

**edge+dns** (mini+nas+seedbox): public zone must hold NO host A-records; only WAN 32400 (Plex) may
answer — probed FROM the seedbox (true off-net vantage); AdGuard (mini primary → Unbound; NAS
secondary → Quad9 DoH) rewrites `*.tabaska.us` → 192.168.10.2 → Caddy (62 vhost blocks). Checks:
edge-wan-port-posture (crit), edge-public-dns-no-rfc1918, mini-caddy-live-config-current
(on-disk vs :2019 running config — catches edited-but-never-reloaded), dns-*, mini-container-dns.
Vhost probe pattern: `curl -sk --resolve <h>.tabaska.us:443:127.0.0.1 https://<h>.tabaska.us/<real-endpoint>`
asserting an app-specific body, never a bare 200.

**home-assistant** (ha+mini+rig): direct :8123 + ha.tabaska.us via Caddy (trusted_proxies); Hue on
IoT VLAN 192.168.20.100; Assist → rig ollama shim. Checks: ha-proxy-e2e, ha-lights-available,
ha-availability-drift (accepted baseline: btiphone ≤11, wall-switched lights), ha-backup-offsite-
fresh. **⚠ gap**: no full `/api/conversation/process` e2e.

**game-servers** (rig+mini): AMP MinecraftCross01 → playit → 69.9.181.17 (real protocol pings
mc-status-ping.py / mc-bedrock-ping.py); Palworld REST :8212 metrics; Terraria wire-protocol
handshake on mini. **⚠ gaps**: BedrockConnect console path, Apollo game-streaming — zero checks.

**retro** (seedbox→nas→mini→rig): ROM sets → NAS Games share → RomM :8998 → rig ES-DE symlinks +
libretro cores. Checks: romm-content-ingest (fails loudly on dead CIFS), rig-esde-romm-library.

**adult** (nas+seedbox): Whisparr :6969 → Deluge → unpackerr → Stash :9999. **⚠ gap**: no Stash
import-outcome/library-growth probe (GraphQL scene count vs Whisparr hasFile).

**disk-smart** (mini+rig→nas): scrutiny collectors POST → hub NAS :8080. Check:
sys-disk-smart-health (≥7 disks all device_status==0).

**reading-web** (mini): BookLogr SPA cross-origin → API (BL_API_ENDPOINT baked at container start);
Miniflux 49 feeds. Checks: booklogr-serves-consumer, mini-miniflux-feeds-fresh/articles-flowing
(crit). Liveness-only apps: **paperless, wallabag, mealie, tautulli** (⚠ no flow-through probes).

**remote-ai-coding** (mac→rig): VSCodium/Continue.dev → LiteLLM `fast` with
`ai_stack.litellm_opencode_key`. **⚠ gap**: nothing exercises this key/path.

Retired/never-deployed — do NOT probe as live services: tdarr, maintainerr, dependency-track,
readarr (→Bookshelf), qbittorrent (seedbox), rreading-glasses goodreads-mode, meme-review
(decommissioned 2026-07-28, data retained), frigate (staged, never ran).

---

## 4. Log surfaces

| Host | Surface | Recipe |
|------|---------|--------|
| mini | docker logs | `ssh mini 'docker logs <name> --since 24h 2>&1 \| grep -iE "error\|fail\|fatal\|critical" \| tail -20'` |
| mini | journal errors + flood count | `ssh mini 'sudo journalctl -p err --since -24h --no-pager \| tail -50'`; storms: `sudo journalctl -p err -S -7days --no-pager \| awk '{$1=$2=$3=""; print}' \| sort \| uniq -c \| sort -rn \| head` |
| mini | Caddy (stdout JSON only, no file logs) | `docker logs caddy --since 24h 2>&1 \| grep '"level":"error"'`; per-vhost 4xx/5xx by `"host":"<vhost>"` + `"status":(4\|5)..` |
| mini | runner state/history | §2 — `last-summary.md`, `results.json`, `triage-*.md`, `reopen-suggestions.json`, `acks.json` |
| mini | units/timers | `systemctl --failed`; `systemctl list-timers --all`; `journalctl -u <unit> --since -48h` |
| mini | Healthchecks API | §2 dead-man harvest |
| nas | docker logs | sudo -S pipe + full path: `sudo -S /usr/local/bin/docker logs <name> --since 24h` |
| nas | DSM /var/log | `sudo -S tail -50 /var/log/messages` (now stamps EDT; pre-fix lines are US/Pacific); disk.log, apparmor.log; `/var/log/synolog` is binary, skip |
| nas | arr error-log APIs | sonarr/radarr/lidarr/whisparr `/api/v3/log?level=error`; prowlarr/bookshelf `/api/v1/log`; keys in each `config.xml` (sudo) |
| rig | journal (no sudo needed) | `journalctl -p err --since -24h`; kernel/fs: `journalctl -k \| grep -iE "btrfs\|nvme\|error"`; per-unit: ansible-pull, ai-stack-watchdog, pcie-aer-monitor, playit-udp-guard, immich-ml-window@, restic-backup, abs-ipod-stage |
| rig | docker logs | llama-swap (`exited prematurely` = model OOM), litellm (`Proxy:ERROR` — filter benign `No api key passed in` noise), comfyui, gpu-arbiter, palworld, amp, suwayomi |
| rig | AMP instance logs | `tail -50 "$(ls -t /opt/stacks/amp/config/.ampdata/instances/MinecraftCross01/AMP_Logs/*.log \| head -1)"` |
| seedbox | deluged.log (~29 MB unrotated, warning level since fix-45) | `ssh seedbox 'tail -c 200000 ~/.config/deluge/deluged.log \| grep -iE "error\|fail\|alert" \| tail -20'` — tail -c windows only |
| ha | core log | `curl -H "Authorization: Bearer $TOK" http://192.168.10.50:8123/api/hassio/core/logs` (plaintext + tracebacks). `/api/error_log` is 404 — do not use |
| ha | logbook | `GET /api/logbook/<ISO8601>` for entity-level flap evidence |

---

## 5. Failure-pattern taxonomy (this fleet's priors)

Grep for these first — every one has bitten this fleet:

1. **RO-filesystem cascade** (C1–C3/fix-20): btrfs `corrupt leaf` → RO remount → journald stops
   persisting (the log GAP is evidence), DBs segfault. `journalctl -k | grep -iE "BTRFS
   (critical|error)|corrupt leaf|forced readonly"`; `findmnt -no OPTIONS / /home | grep -c '^ro,'`.
2. **Green-but-broken liveness masking**: `docker ps` healthy while consumer path dead — LiteLLM
   master-key 200 while every virtual key 503s (`no_db_connection`). Probe the consumer, cross-check
   `docker ps` vs `docker inspect`.
3. **DB segfault exit 139** after a write-path fault: `docker inspect -f '{{.State.ExitCode}}'`;
   `journalctl | grep -iE 'systemd-coredump|segfault'`.
4. **Grabbed-but-never-imported** (arr stall): arr error log `Import failed, path does not exist`;
   deluge torrents 100% + label parked >48 h; `deluge-preimport-stuck`.
5. **Request-layer phantoms**: request PROCESSING >48 h with zero arr history; artist/author added
   `monitor:none` so failed searches never retry.
6. **Silent scheduled-job failure**: cron executing a directory (exit 126, no output); one-shot
   timer failed once, never retried; `systemctl list-timers --all | grep n/a`.
7. **Retry-storm flood on a dead path**: journal uniq-count >1000 of an identical error line
   (upsmon logged 106 834 × 'Connection refused') = nobody is reading this log.
8. **Sample/junk import marked green**: hasFile=True but file is `Sample/*.avi` <200 MB; real
   content in unextracted `.rar/.r00` beside it.
9. **Config-edited-but-never-reloaded**: Caddyfile vhost on disk, TLS handshake fails on that SNI
   (`mini-caddy-live-config-current` codifies it); same class: env baked into image at build.
10. **Proxy-path 4xx while direct port green**: ha.tabaska.us 400 for 11 days (trusted_proxies)
    while :8123 liveness passed. Probe THROUGH the proxy.
11. **Upstream-auth rot under exit-code 0**: kometa 401s daily inside meta.log; stale
    endpoint/model pins in env files. Parse run logs, never trust exit 0.
12. **Stale last-success / dead-man in grace**: Healthchecks `last_ping` older than period+grace
    exactly while the host is dying; marker must be written by the JOB, not the checker.
13. **Silently frozen poller / zero-throughput green**: miniflux up but 0 articles for 6 days;
    Immich green around zero assets. Check newest-item timestamp and `count(*)` on the primary
    object table of every "green" service.
14. **Green-but-write-dead storage**: reads 200, writes fail — `grep -iE 'readonly
    database|not writable|unable to open database'`. Pure-GET healthchecks are blind to it.
15. **Docker json-log corruption**: NUL byte makes `docker logs --since` abort mid-stream — the
    scan itself silently truncates; retry with `--tail 500`.
16. **gunicorn WORKER TIMEOUT** = uncatchable 500 (libreseerr); pair with Caddy 500s by timestamp.
17. **Restart loops / VRAM contention**: `RestartCount>3`, `Restarting` status; rig llama-swap
    `exited prematurely` is only a finding OUTSIDE the day-window contention explanation.

---

## 6. Drift axes (repo vs live)

Diff every axis; a fix that changed one side only is a finding (anti-drift is the repo's core rule).

1. **mini /opt/stacks vs `configs/docker-stack/stacks/`**: `git -C /opt/stacks status --porcelain`
   (0), `git -C /opt/stacks log origin/main..HEAD` (empty — the ORPHANED-commit hazard: both trees
   porcelain-clean yet divergent), `stack-mirror-check.sh mirrors` (STACK-MIRRORS-OK). Name traps:
   repo `syncthing-node/` = live `syncthing/`; `adguard-nas/` deploys to the NAS; live-only
   `/opt/stacks/{backups,wiki}` expected.
2. **NAS /volume1/docker vs `configs/nas/`** — NO automated check; manual per-app diff; filename
   variance compose.yaml vs docker-compose.yml.
3. **rig/mini host units vs `configs/host/{rig,mini}/`** — DOC-ONLY (ansible converges zero units);
   canonical map = `configs/host/rig/README.md` table; `unit-drift-check.sh` covers a subset;
   external local-ai-tooling units guarded by ai-tooling-clean-pushed + env-example-parity.
4. **Coverage manifests vs live containers**: `docker ps --format '{{.Names}}' | grep -v -- -run- |
   LC_ALL=C sort | diff verification/coverage/<host>.containers -` (rig also excludes
   `^immich_machine_learning$` — but the container must still be LISTED per the tripwire); also
   diff repo copy vs deployed `/opt/verification/coverage/` (they lag independently).
5. **checks.d repo vs deployed** + confirm ids actually load in a run.
6. **service-catalog.yaml vs live** (~71 entries): probe each url (502 = incident — all hosts are
   24/7, `on_demand` is legacy); invert: live containers/vhosts with no catalog row (symptom: wiki
   page with wrong URL + Uncategorized).
7. **wiki generated pages vs sources** (same-commit rule): re-run all 5 generators, any diff =
   drift; never hand-edit generated pages; gen-wiki-services skips configs/host/rig (rig services
   have no page — linking one breaks `--strict`).
8. **tracker vs reality**: checkmarks explicitly untrustworthy; a done-marked task whose check
   fails is the tell; `tracker-count-check.py` + `tracker-integrity.py` for internal coherence.
9. **Homepage tiles vs live**: `homepage-tiles-resolve.py` (dead-tile guard misses href-only
   external tiles); config truth via `:3010/api/services`.
10. **vault vs .env.example parity**: `vault-lint.py` (publish gate); live .env keys ⊆ repo
    .env.example per stack (a live-only key silently vanishes on rebuild).
11. **Caddy vhosts vs live services**: repo-vs-live Caddyfile diff; probe all vhosts expecting
    200/302/401 never 502; cross-set vhosts Δ catalog Δ tiles Δ manifests (a service can be dead in
    one plane, alive in another).
12. **DNS**: both resolvers must return 192.168.10.2 for `*.tabaska.us`; public zone NXDOMAIN for
    every service name; AdGuard config is LIVE-ONLY (`/opt/stacks/adguard/conf/AdGuardHome.yaml`
    untracked — a rebuild loses it silently).
13. **Image manifests** (`hosts/{macmini,cachyos}/compose-images.txt`): name-set mismatches only
    (`stack-mirror-check.sh manifest`); **etckeeper** (`etckeeper unclean` exits 1 when clean) and
    **chezmoi** (`chezmoi diff | grep -c '^@@'` == 0; never blanket-apply on the Mac).

---

## 7. Contradiction sources (doc planes that can disagree)

Precedence when planes conflict: **live > generated wiki > catalog/enrichment > README prose**.
Verify live before citing any of them.

- catalog vs enrichment: URL+category come ONLY from the catalog; enrichment-only services render
  wrong-URL/Uncategorized pages.
- `foss-setup/README.md` still narrates the plan era (lists ~10 mini stacks; 35 exist) and claims
  the wiki is the source of truth, contradicting mandate 3 (live is).
- wiki index says the repo lives at `~/Documents/Home`; actual checkout is `~/GitHub/Home` — grep
  docs for the stale path class.
- `configs/host/rig/README.md` calls local-ai-tooling "external/GitHub-only" — SUPERSEDED (ai-02..07:
  dual-remoted with its own tripwires).
- Quality-gate docs are point-in-time snapshots — findings get fixed without the doc changing;
  cross-check progress.json + the regression check before citing one as current.
- Caddyfile comments vs catalog vs tiles vs manifests: a retired service can linger in any one
  plane (meme-review, frigate, tdarr are the current known intentional gaps).
- Auto-memory files can supersede repo docs and vice versa — when they conflict, verify live.
- `on_demand` catalog fields + any "rig sleeps / WoL to wake" prose are legacy: all hosts 24/7
  since 2026-07-08; WoL is recovery-only.

---

## 8. Topology + SPOF (architecture-review baseline)

Edge: internet → only WAN pinhole TCP 32400 → NAS Plex; everything else via Tailscale or LAN; both
AdGuards rewrite `*.tabaska.us` → mini → Caddy (wildcard LE cert via Cloudflare DNS-01). Config
planes: GitHub origin ↔ Forgejo `home/homelab` (deploy remote, ansible-pull mini+rig) ↔ Forgejo
`home/docker-stacks` (/opt/stacks live) ↔ external `local-ai-tooling` (rig AI stack). Ansible
converges ONLY base/docker/tailscale/backup/state on mini+rig; NAS/HA/gateway are appliances;
everything in `configs/host/` is doc-only.

Single points of failure to weigh in every architecture finding:

- **mini is the mega-SPOF**: Caddy TLS for all vhosts + primary DNS + Forgejo deploy remote + the
  ENTIRE alerting plane (runner, Kuma, ntfy, Healthchecks) — mini down means no https anywhere and
  no alert can say so.
- Caddy container: one bad Caddyfile push 502s all ~62 vhosts.
- NAS shares: mini (Navidrome) and rig (manga/ROMs/music/ipod) hard-depend via CIFS.
- rig 3090 Ti: one GPU shared by Immich ML + LLMs (time-window managed, not capacity); rig down =
  AI stack + game servers + Suwayomi down.
- seedbox: only P2P path AND only off-net vantage for the WAN sweep.
- Cloudflare (cert renewal + public zone), Tailscale (only remote access), ntfy (all alert
  delivery), the vault file (exists only on the Mac), ha (unreachable remotely if mini is down).

---

## 9. Known-normal states — do NOT file these as findings

- rig `immich_machine_learning` Exited by day; llama-swap "exited prematurely" during day-window
  VRAM contention; "rig ML down by day / VRAM pinned at night" (glue-14).
- HA: scene entities `unknown` until first activation; ~8 Hue bulbs chronically unavailable
  (wall-switched); btiphone_* sensors ≤11 stale (accepted baseline, ha-availability-drift).
- verification-*.service exit 1 = checks failed, not the runner; SuccessExitStatus=1 and
  verify-cycle's unconditional exit 0 are deliberate (dead-man self-blinding fix).
- litellm `No api key passed in` Proxy:ERROR noise; Plex 401 = up; 302/303/307 login redirects =
  healthy; seedbox host load 40–57 (shared host, not ours).
- `results-<x>.json` side files can be stale ad-hoc leftovers — check `timestamp` first.
- Disabled checks (`enabled: false`) and everything in `acks.json` are deliberate.
- Deliberate probe exclusions: recurring real image-gen, big-model completions in loops, subtitle
  provider searches, indexer-availability health (rate-limit flap).
- Weekly image-manifest pin lag; `mode`-bit chezmoi flap (content hunks only count).

---

## 10. Output formats — the fix queue

A sweep's findings must land exactly like the 2026-07-16 audit's did, so `/resolve-finding` and the
tracker consume them unchanged. Four artifacts + close-out:

**(a) Findings doc `foss-setup/docs/fleet-sweep-YYYY-MM-DD.md`** — H1 title; method blockquote
(lane counts, "Nothing was modified on any host", pointer to the JSON twin, and — new this time —
the lane roster itself so the method is reproducible); totals line
(`**Totals: N findings — a critical / b high / c medium / d low / e info** (k candidates refuted
during verification)`); then five severity sections in fixed order CRITICAL/HIGH/MEDIUM/LOW/INFO.
Per finding: `### <ID>. <title>` (+ `` `known-issue` `` tag when applicable), metadata line
`**Host:** X · **Component:** Y · **Auditor:** <lane>`, detail paragraph (live-observed facts,
timestamps, "NOT fixed per read-only mandate"), then
`<details><summary>Evidence</summary>` + fenced code block of literal commands + outputs +
`</details>`. Evidence must be copy-paste runnable — resolvers start from those exact commands.
INFO entries may omit the details block in the MD.

**Finding IDs**: per-severity ordinals with a sweep letter prefix so raw ids stay unique across
docs (tasks.json `findings` arrays are a flat namespace; taken: C/H/M/L/I by 2026-07-16, B by the
books scan). First fleet-sweep uses **S** → `SC1…, SH1…, SM1…, SL1…, SI1…`; each later sweep picks
the next free letter (grep prior docs + tasks.json findings arrays to confirm).

**(b) JSON twin `…-YYYY-MM-DD.json`** — bare array, **severity-sorted contiguous blocks in order
critical→high→medium→low→info; position within a block IS the id — never reorder after the MD is
written**. Fields per finding: `severity`, `host`, `component`, `title`, `detail`, `evidence`
(newline-joined literal commands+outputs, no fences), `auditor` (lane name, e.g. `host:mini`,
`svc:ai-stack`, `flow:books`, `repo:live-drift`, `gap:<mission>`), `confidence` (high|medium),
`known_issue` (bool); optional `verification:"confirmed"` + `verify_note` on skeptic-passed items.

**(c) Worklist `…-YYYY-MM-DD-worklist.md`** — same shape as `quality-gate-worklist.md`: intro
blockquote (generated-from line, "Each item = one fix-NN task = one Claude Code session. Drive with
/resolve-finding fix-NN.", info-findings-get-no-task note); coverage line; summary table
`| id | sev | host | wave | title | # |` (sev emoji 🔴🟠🟡⚪ = max of the cluster); wave sections
(0 = active incident, 1 = security/exposure, 2 = broken user-facing pipelines, 3 = service/infra
repair, 4 = hygiene/drift batches); per item: `### \`fix-NN\` <emoji> <title>`, metadata line
(`*host:* … · *track:* … · *severity:* …` + ` · ⚠️ disruptive → 4–7AM window + approval` when
gated), summary paragraph, `**Resolves N findings:** \`SH1\` <title truncated to 60 chars>, …`.
**Clustering principle**: group by shared ROOT CAUSE / failure class across hosts and severities —
an incident bundles its whole downstream cascade; duplicates from different lanes merge; low-sev
hygiene batches into catch-alls. Info findings get no task unless action-relevant to a cluster.
Number fix-NN sequentially in wave order (lowest open = next for auto-pick).

**(d) tasks.json entries** — append to the top-level array (2-space indent), one per work item.
Next free id = max existing fix-NN + 1 (fix-48 as of 2026-08-02 → start at fix-49). Field recipe
(mirrors fix-20..48; no script validates, so self-review against an existing entry):

```json
{
 "id": "fix-NN",
 "title": "<worklist item title>",
 "host": "<dominant host | fleet | device>",
 "type": "sync",
 "depends_on": [],
 "estimate": "1-3 hrs",
 "required": true,            // true for critical/high clusters, false for medium/low
 "track": "<domain track — audit-fixes|security|media-pipeline|verification|ops|…>",
 "run": <next unused run number — 5=quality-gate and 6=books are taken; check current max>,
 "mode": "ai",                // ai-vault if a vault handoff is needed
 "gate": "",                  // or "disruptive — 4-7AM window + operator approval"
 "summary": "<2-5 sentences: symptoms + remediation direction>",
 "steps": ["Follow the /resolve-finding definition of done: (1) reproduce & root-cause live, (2) plan+approval gate for anything disruptive/destructive, (3) resolve, (4) codify the fix in the repo (anti-drift), (5) harden against recurrence, (6) add an END-TO-END regression check + a class-level check wired into verification/checks.d + coverage manifest + a monitor, (7) document in the wiki via the generation path, (8) mark the finding(s) resolved in progress.json, regenerate, one commit/PR. Findings with evidence live in docs/fleet-sweep-YYYY-MM-DD.md (NOT the 2026-07-16 quality-gate doc)."],
 "findings": ["SC1", "SH4", "SM12"],
 "verify": "Every listed finding re-probed and confirmed resolved end-to-end (consumer-level, not liveness); a regression + class check is live and green; wiki updated; progress.json updated. Source: docs/fleet-sweep-YYYY-MM-DD.md.",
 "source": "fleet sweep YYYY-MM-DD (docs/fleet-sweep-YYYY-MM-DD.md)"
}
```

**(e) Close-out (same session, ONE commit)**:
1. Edit `.claude/commands/resolve-finding.md` — register the new doc + fix range in Step A (the
   wave-range list) and Step B item 3 (the source→doc mapping). The `source` label alone is not
   enough; resolve-finding hard-codes its mappings.
2. Update the repo-root `CLAUDE.md` "Current priority" paragraph to name the new sweep docs and
   queue range alongside (or replacing, if the old queue is drained) the 2026-07-16 pointers.
3. `progress.json`: append a one-line record of the sweep to `_meta.note`, bump `_meta.updated` —
   **json.dump(indent=1)** or you churn ~490 lines.
4. Regenerate: `python3 foss-setup/scripts/docs/gen-todo.py` +
   `python3 foss-setup/scripts/docs/gen-roadmap-pages.py` (a new `track` value auto-creates a
   roadmap page — same-commit rule, or the wiki-drift check goes red).
5. `git pull` first (concurrent sessions happen), one commit scoped to the sweep, then
   `./foss-setup/scripts/docs/publish-deploy.sh` (vault-lint gate; pushes origin + forgejo).
   Confirm `git status` is clean of stray/iCloud-conflict files.

**Dedup rules before filing**: a finding already covered by an OPEN task (fix-NN or any tracker id)
is cited with `known_issue: true` + the task id in its detail — no new task. A finding that
re-breaks a DONE task (see `reopen-suggestions.json`) becomes a work item explicitly framed as a
regression of that task. Everything in `acks.json` is excluded. The 42 `known_issue` findings of
2026-07-16 show the pattern.

# Quality-gate audit — full fleet pass (2026-07-15/16)

> Read-only audit before further rollout. Method: 26 parallel auditor agents (host health x5,
> service deep-dives x9, end-to-end flows x8, repo/tracker/drift x4), skeptic verification of
> low-confidence findings, completeness critic + 6 gap-filler agents. ~2.8M tokens, 1300+ probes.
> **Nothing was modified on any host.** Full machine-readable findings: `quality-gate-2026-07-16.json`.

**Totals: 303 findings — 3 critical / 30 high / 62 medium / 95 low / 113 info** (1 candidate refuted during verification).


---

## CRITICAL — active incident (3)

> **Resolution (2026-07-16, task `fix-20`):** C1/C2/C3 and the downstream cascade
> (H22/H23/H25/H26/H27/I104/I105/M54/M56) were worked as one item. Root cause: a
> marginal PCIe link on the OS NVMe (WD SN570 2TB, serial 210318800752 @ 0000:74:00.0)
> corrupted a metadata write in flight → stale btrfs leaf → forced read-only. Recovery:
> salvage-while-readable → offline `btrfs check --repair` from USB → NVMe reseat.
> Prevention: `rig-root-fs-writable` + `mini-root-fs-writable` write-probe checks and
> `rig-litellm-vkey-e2e` (DB-auth path). Full procedure:
> [`wiki/docs/runbooks/rig-btrfs-readonly-recovery.md`](../../wiki/docs/runbooks/rig-btrfs-readonly-recovery.md).

### C1. Rig root filesystem is mounted READ-ONLY right now; journald, restic backups and ansible-pull all silently broken since ~22:49 EDT 2026-07-15

**Host:** rig · **Component:** root filesystem (btrfs on OS NVMe /dev/nvme2n1p2) · **Auditor:** repo:live-drift


The entire OS btrfs (subvols /, /home, /srv, /root, /var/cache, /var/log, /var/tmp) is ro. Consequences observed live: (1) journald stopped persisting at 22:49:15 EDT Jul 15 — system.journal reported corrupted, rotation fails with 'Read-only file system', so ~13h of logs are lost and the original fault event is unrecoverable (dmesg ring has wrapped); (2) restic-backup.service FAILED exit 1 at 01:38:34 (backup outage on the rig); (3) ansible-pull.service FAILED exit 5 at 04:21:36 — reproduced the cause read-only: ansible errors 'Errno 30 Read-only file system: /home/btabaska/.ansible/tmp/...'; rig convergence checkout stuck at b0d8c83 (3 commits behind main 3b87b1f). btrfs device stats are all 0 and SMART PASSED; pcie-aer-monitor.timer is active and its last service run exited clean, so the trigger is unconfirmed — but this is the same marginal SN570 OS drive class from the known PCIe issue. Docker AI-stack containers still show Up/healthy and ai-stack-rig still pings healthchecks — liveness-only monitoring masking a write-dead host. Healthchecks had NOT alerted yet at audit time (restic-backup-rig status=grace, ansible-pull-rig still up within its 12h grace). NOT fixed/rebooted per read-only mandate.


<details><summary>Evidence</summary>

```
$ ssh rig 'grep -E " / | /home " /proc/mounts'
/dev/nvme2n1p2 / btrfs ro,noatime,compress=zstd:3,...,subvol=/@ 0 0
/dev/nvme2n1p2 /home btrfs ro,...,subvol=/@home 0 0
$ sudo dmesg | tail
systemd-journald[496]: Failed to rotate .../system.journal: Read-only file system (Dropped 2255 similar message(s))
systemd-journald[496]: /var/log/journal/.../system.journal: Journal file corrupted, rotating.
$ journalctl --list-boots  ->  LAST ENTRY Wed 2026-07-15 22:49:17 EDT (nothing since)
$ systemctl status restic-backup: Active: failed (exit-code) since Thu 2026-07-16 01:38:34 EDT; ExecStart=/opt/scripts/restic-backup.sh (code=exited, status=1)
$ systemctl status ansible-pull: failed since 04:21:36 EDT (status=5)
$ /home/btabaska/.local/bin/ansible-pull --version
ERROR: Unhandled exception ... [Errno 30] Read-only file system: '/home/btabaska/.ansible/tmp/ansible-local-...'
$ curl healthchecks /api/v3/checks: restic-backup-rig | grace | last_ping 2026-07-15T05:40:59Z; ansible-pull-rig | up | last_ping 2026-07-15T13:55:00Z; ai-stack-rig | up | 2026-07-16T11:30Z
```

</details>

### C2. Rig root filesystem hit BTRFS metadata corruption and is mounted read-only — cascade of live failures

**Host:** rig · **Component:** filesystem / nvme2n1p2 (btrfs root) · **Auditor:** repo:verification-suite


At 2026-07-15 22:49 EDT the rig's root btrfs (nvme2n1p2 = PCI 0000:74:00.0, WDS200T3X0C — the exact drive flagged as marginal PCIe link in known issue 3) logged 'BTRFS critical: corrupt leaf ... invalid tree level' and / and /home are now mounted ro. Cascade, all evidenced: (a) palworld REST :8212 dead 6 min later (container now 'unhealthy'); (b) docker logs unreadable ('read-only file system'); (c) ansible-pull.service failed 04:21 EDT exit 5; (d) rig restic B2 backup did not ping after the 01:38 EDT run; (e) open-webui returns HTTP 500 → mini's wiki-rag-sync.service failed 05:14 UTC. The verification framework detected every symptom (fast tier paged 02:55 UTC; docker-fleet tier paged 04:40 + 05:42 UTC) but no one has acted for ~9-12h. This is an escalation beyond the known 'marginal link' issue: actual metadata corruption on the OS drive, with the reseat/replace item still open. Read-only audit — nothing was touched.


<details><summary>Evidence</summary>

```
ssh rig 'journalctl -k --since -30h | grep -i btrfs' →
Jul 15 22:49:15 cachyos kernel: BTRFS critical (device nvme2n1p2): corrupt leaf: block=1618217680896 slot=85 extent bytenr=1618206097408 len=16384 invalid tree level, have 177620385792 expect [0, 7]
ssh rig 'findmnt -no TARGET,SOURCE,OPTIONS /' → / /dev/nvme2n1p2[/@] btrfs ro,noatime,...
ssh rig 'touch /home/btabaska/.rw-probe-audit' → touch: cannot touch ...: Read-only file system
ls -l /dev/disk/by-path | grep nvme2 → pci-0000:74:00.0-nvme-1 -> ../../nvme2n1; model=WDS200T3X0C-00SJG0
ssh rig 'docker logs palworld --tail 15' → Error response from daemon: open /var/lib/docker/containers/4a1e...-json.log: read-only file system
```

</details>

### C3. Root btrfs remounted read-only after BTRFS 'corrupt leaf' on the known marginal NVMe (74:00.0) `known-issue`

**Host:** rig · **Component:** root filesystem (btrfs on nvme2n1p2) · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


Confirmed the active incident: rig / is mounted ro. Kernel journal shows BTRFS critical corrupt-leaf metadata corruption on nvme2n1p2 at Jul 15 22:49:15 EDT (Jul 16 02:49 UTC). nvme2 is the device at PCIe 0000:74:00.0 — the same slot as the known marginal-PCIe-link OS drive (model reads WDS200T3X0C 2TB, not SN570 as memory says; the address matches the known-flaky link). The garbage tree-level value (177620385792 vs expected 0-7) is consistent with in-flight bit corruption from a marginal link. Every container overlay and docker volume on this FS is now read-only; docker daemon cannot persist state or write container json logs. This extends known issue #3 from 'marginal link, monitored' to 'actual metadata corruption + forced RO remount'.


<details><summary>Evidence</summary>

```
ssh rig 'findmnt -no OPTIONS /' -> ro,noatime,compress=zstd:3,ssd,...,subvol=/@
sudo journalctl -k --since -26h | grep -iE 'read-only|btrfs.*error' ->
Jul 15 22:49:15 cachyos kernel: BTRFS critical (device nvme2n1p2): corrupt leaf: block=1618217680896 slot=85 extent bytenr=1618206097408 len=16384 invalid tree level, have 177620385792 expect [0, 7]
readlink -f /sys/class/nvme/nvme2/device -> /sys/devices/pci0000:00/0000:00:1d.4/0000:74:00.0
cat /sys/class/nvme/nvme2/model -> WDS200T3X0C-00SJG0
docker exec <llama-swap|litellm|open-webui|mcpo> touch /tmp/_p -> 'Read-only file system' for all four
```

</details>


---

## HIGH (30)

### H1. UPS monitoring dead for 7+ days: upsmon cannot reach ups@192.168.10.4:3493, ~120k errors flooding journal, no shutdown protection

**Host:** mini · **Component:** nut-monitor (upsmon) / NUT server on NAS · **Auditor:** host:mini


mini's nut-monitor is configured to MONITOR ups@192.168.10.4 but the NAS NUT server port 3493 refuses connections. upsmon has been retrying every 5 seconds continuously since at least Jul 08 (start of the 7-day journal window) through right now — 106,834 'Connection refused' + 11,197 'Network is unreachable' + 2,904 more err entries. Consequences: (1) mini has zero UPS-triggered clean-shutdown protection on power loss; (2) journal bloat (archived+active journals = 3.9G). Either the Synology 'Enable network UPS server' setting is off/lost or the permitted-client list no longer includes mini's (new static) IP 192.168.10.2 — plausible fallout from the 2026-07-10 static-IP change. Not in the known-issues list.


<details><summary>Evidence</summary>

```
ssh mini 'journalctl -p err -S -7days | ... uniq -c | sort -rn' -> '106834 upsmon[777]: UPS [ups@192.168.10.4]: connect failed: Connection failure: Connection refused' + '11197 ... Network is unreachable'. Live now: 'Jul 15 16:19:36 macmini upsmon[777]: UPS [ups@192.168.10.4]: connect failed: Connection refused' (every 5s). Port probe from mini: 'timeout 3 bash -c "echo > /dev/tcp/192.168.10.4/3493"' -> 'connect: Connection refused' -> NUT-PORT-CLOSED. 'journalctl --disk-usage' -> 3.9G.
```

</details>

### H2. Deluge RPC (3254), deluge-web (5945, plain HTTP) and qBittorrent WebUI (13091) are bound to 0.0.0.0/public IP and reachable from the open internet

> **RESOLVED 2026-07-17 (fix-21).** Deluge RPC/web bind 127.0.0.1 (`allow_remote:false`, web `interface:127.0.0.1`); qBittorrent retired; all five admin ports probe closed from the WAN. Consumers (arr Deluge clients + Remote Path Mappings, Caddy vhost) repointed to the tailnet `100.119.134.94` (userspace tailscaled forwards inbound tailnet→loopback). Guarded by `verification/checks.d/seedbox.yaml` (`seedbox-public-lockdown`, `seedbox-loopback-binds`, `seedbox-arr-deluge-e2e` — all green). Runbook: `wiki/docs/runbooks/seedbox-exposure.md`.

**Host:** seedbox (betty.bysh.me / 185.162.184.38) · **Component:** Deluge daemon RPC + deluge-web + qBittorrent WebUI · **Auditor:** host:seedbox


deluge core.conf has allow_remote:true with daemon_port 3254 listening on 0.0.0.0; web.conf interface is 0.0.0.0:5945; qBittorrent WebUI\Address=* on port 13091. All three answered from the operator's MacBook over the PUBLIC internet (betty.bysh.me resolves to public 185.162.184.38, not the tailnet). deluge-web serves the login page over plain HTTP (WebUI HTTPS disabled), so its session password crosses the WAN in cleartext; the RPC surface is protected only by the 10-char auth-file password (btabaska:LanUjzvLxZ). qBittorrent-nox is idle (0 torrents) yet still exposes a WebUI. This is a wide unauthenticated-reachable attack surface on a shared host; a guessed/leaked WebUI or RPC password grants full torrent + arbitrary-download-path control.


<details><summary>Evidence</summary>

```
$ host betty.bysh.me -> 185.162.184.38
$ nc -z betty.bysh.me 3254 -> PORT 3254: OPEN; 5945 -> OPEN; 13091 -> OPEN
$ curl -I http://betty.bysh.me:5945/ -> HTTP/1.1 200 OK / Server: TwistedWeb / <title>Deluge WebUI 2.2.0</title>
$ curl -I http://betty.bysh.me:13091/ -> HTTP/1.1 200 OK (qBittorrent)
core.conf: "allow_remote":true,"daemon_port":3254 ; ss: LISTEN 0.0.0.0:3254 deluged, 0.0.0.0:5945 deluge-web; web.conf "interface":"0.0.0.0"; qBittorrent.conf WebUI\HTTPS\Enabled=false, WebUI\Address=*
```

</details>

### H3. 3 movie requests stuck PROCESSING 10 days: Radarr grabs vanished from Deluge without importing

**Host:** mini + nas + seedbox · **Component:** seerr -> radarr -> deluge pipeline · **Auditor:** svc:request-layer


Seerr requests 13 (tmdb 556901 Teen Titans Go! vs Teen Titans), 14 (tmdb 16237 Teen Titans: Trouble in Tokyo), 17 (tmdb 13168 Smiley Face) approved 2026-07-05 and grabbed by Radarr at 02:05-02:07 that night to Deluge, but all three torrent hashes are absent from Deluge on the seedbox, Radarr queue is empty, hasFile=False, sizeOnDisk=0. The deluge-reaper is ruled out (sonarr labels only, '0 eligible' every run since 07-10). Movies are monitored and in Radarr's missing list (so a manual search can recover them) but nothing has retried in 10 days; seerr shows PROCESSING forever. Silent failure class: grab handed to download client, then lost with no error surfaced anywhere.


<details><summary>Evidence</summary>

```
curl -H 'X-Api-Key: ...' http://192.168.10.4:7878/api/v3/history/movie?movieId=315|314|20 ->
315 | Smiley Face 2007 1080p BluRay x264-VETO | 9878067A... | Deluge (grabbed 2026-07-05T02:07)
314 | Teen Titans Trouble In Tokyo 2006 1080p... | 4BA9E271... | Deluge
20  | Teen Titans Go Vs Teen Titans 2019 1080p... | DA628DB0... | Deluge
radarr /api/v3/movie: all three monitored=True hasFile=False sizeOnDisk=0; /api/v3/queue totalRecords: 0
ssh seedbox '~/venvs/deluge/bin/python -' < deluge_check2.py ->
9878067a0ac8 NOT IN DELUGE / 4ba9e2718dc6 NOT IN DELUGE / da628db094e7 NOT IN DELUGE
ssh seedbox tail ~/logs/deluge-reaper.log -> '2026-07-15 05:00:11 LIVE: 0 eligible (labels=[sonarr, sonarr-imported])'
```

</details>

### H4. Seerr request 12 (New Teen Titans) points at a Sonarr series that no longer exists (404); stuck PROCESSING since 07-05

**Host:** mini + nas · **Component:** seerr -> sonarr link · **Auditor:** svc:request-layer


Seerr request 12 (tv tmdb 283746 / tvdb 433627, 'New Teen Titans') is APPROVED with media status PROCESSING and mediaInfo.externalServiceId=258, but Sonarr has no series with tvdbId 433627 (162 series total) and GET /api/v3/series/258 returns 404 — the series was deleted from Sonarr after the request. Seerr's availability-sync does not detect the dangling link, so the request can never complete or fail; it will sit in PROCESSING indefinitely. Needs manual decline/re-request or media entry deletion in seerr.


<details><summary>Evidence</summary>

```
curl -H 'X-Api-Key: <seerr>' http://192.168.10.2:5055/api/v1/tv/283746 ->
name: New Teen Titans | mediaInfo status: 3 (PROCESSING) | serviceId: 0 | externalServiceId: 258
curl -H 'X-Api-Key: <sonarr>' 'http://192.168.10.4:8989/api/v3/series?tvdbId=433627' -> []  (NOT IN SONARR, 162 series listed)
curl -o /dev/null -w '%{http_code}' http://192.168.10.4:8989/api/v3/series/258 -> 404
seerr /api/v1/request: id 12 tv req=APPROVED media=PROCESSING added=2026-07-05
```

</details>

### H5. Book 'Naamah's Curse' fully downloaded on seedbox (100%, seeding, label=readarr) but never imported; Readarr no longer tracks it

**Host:** mini + nas + seedbox · **Component:** libreseerr -> readarr -> deluge pipeline · **Auditor:** svc:request-layer


Libreseerr request 1783906537581 (Naamah's Curse, Jacqueline Carey, readarr_book_id 293) was grabbed 2026-07-13T01:37 from MyAnonamouse to Deluge (hash C242EDA0...). The torrent is complete and seeding on the seedbox with label 'readarr' (never relabeled to imported), yet Readarr's queue is empty, the book has 0 files, and there is no import event in history — the completed download fell out of Readarr's tracking without importing and without any error surfaced. Libreseerr shows the request as 'processing' indefinitely. Same silent grabbed-never-imported class as the Radarr finding, but here the payload actually exists on the seedbox.


<details><summary>Evidence</summary>

```
curl readarr /api/v1/history?bookId=293 -> [('grabbed','2026-07-13T01:37')] sourceTitle="Naamah's Curse by Jacqueline Carey [ENG / EPUB]" indexer=MyAnonamouse downloadClient=Deluge hash=C242EDA01BA0...
curl readarr /api/v1/book/293 -> monitored=True files=0 sizeOnDisk=0; /api/v1/queue total: 0
ssh seedbox deluge RPC -> c242eda01ba0 | Kushiel's Legacy 08 - Naamah's Curse - Jacqueline Carey.epub | Seeding | progress= 100.0 | label= readarr
libreseerr GET /api/requests -> id 1783906537581 status=processing created 2026-07-13T01:35
```

</details>

### H6. Libreseerr adds authors unmonitored (addOptions monitor:none) — failed book searches are never retried; 3 books stuck 'processing' with zero Readarr history

**Host:** mini + nas · **Component:** libreseerr readarr.py add flow / readarr monitoring · **Auditor:** svc:request-layer


Books 284 (Kushiel's Scion), 280 (The Rotten Romans), 261 (Kushiel's Justice) are monitored=True in Readarr but their authors are monitored=False because the bind-mounted /opt/stacks/libreseerr/readarr.py adds authors with monitored-author options 'none' (lines ~156-159: monitorNewItems:none, addOptions.monitor:none). Readarr's wanted/missing excludes books whose author is unmonitored — confirmed all 4 stuck books absent from the 130-item wanted list — so after the one-shot search at request time (0 grabs, zero history events for all three) they will NEVER be auto-searched again. Requests remain 'processing' in libreseerr forever. This is a residual stuck-book mechanism beyond the known edition-selection patch (KI-10): the patch fixed junk-edition 400s, but a no-result first search is now permanent.


<details><summary>Evidence</summary>

```
curl readarr /api/v1/book/{284,280,261} -> monitored=True authorMonitored=False files=0
curl readarr /api/v1/history?bookId={284,280,261} -> events: 0 [] (never grabbed/searched successfully)
curl readarr /api/v1/wanted/missing?pageSize=200 -> total 130; 293/284/280/261 in wanted: False
ssh mini grep readarr.py -> 156: "monitored": True / 157: "monitorNewItems": "none" / 159: "monitor": "none"
libreseerr /api/requests -> 5 requests status=processing since 2026-07-13
```

</details>

### H7. Miniflux silently frozen: all 52 feeds excluded from polling since 2026-07-09, zero articles fetched for 6+ days

**Host:** mini · **Component:** miniflux · **Auditor:** svc:docs-life

> **Resolution (2026-07-16, task `fix-33`):** error counters reset on all 49 feeds (3 had been
> deleted since the audit), refresh-all forced via API — 49/49 polled, 105 articles ingested
> within minutes. Root-cause guard: `POLLING_PARSING_ERROR_LIMIT=0` in the stack (feeds are
> never auto-excluded again). New checks: `mini-miniflux-feeds-fresh` (scheduler stall),
> `mini-miniflux-articles-flowing` (consumer-end ingest), `mini-container-dns` (the docker
> embedded-DNS root cause, class-level). Runbook on the wiki miniflux service page.


A transient docker-DNS outage (2026-07-08 21:18 -> 2026-07-09 11:18 UTC) made every feed fetch fail 3 times. All 52 feeds now sit at parsing_error_count=3, which equals Miniflux's default POLLING_PARSING_ERROR_LIMIT, so the hourly scheduler permanently excludes every feed (jobs_count=0 every batch). No feed has been checked since 2026-07-09 11:18 UTC. The web UI (https://rss.tabaska.us 200) and container healthcheck are green, so nothing alerts — classic liveness-vs-correctness gap. Recovery needs a manual refresh-all or error-count reset (not performed, read-only pass). Container DNS verified working again today.


<details><summary>Evidence</summary>

```
ssh mini docker exec miniflux_db psql -U miniflux -d miniflux:
 SELECT count(*) FROM feeds; -> 52
 SELECT count(*) FROM feeds WHERE parsing_error_count >= 3; -> 52
 SELECT min(checked_at), max(checked_at) FROM feeds; -> 2026-07-09 01:18:52+00 | 2026-07-09 11:18:52+00
 parsing_error_msg: 'Miniflux is not able to reach this website due to a network error...'
docker logs -t miniflux (hourly, ongoing):
 2026-07-15T15:29:50 level=INFO msg="Created a batch of feeds" batch_size=100 rows_count=0 skipped_feeds_count=0 jobs_count=0
last fetch error: 2026-07-09T11:18:52 ... dial tcp: lookup www.gunnerkrigg.com on 127.0.0.11:53: server misbehaving
```

</details>

### H8. llamaswap.tabaska.us vhost added to Caddyfile but caddy never reloaded — route dead (TLS handshake fails)

**Host:** mini · **Component:** caddy · **Auditor:** svc:infra-mini


The llamaswap vhost (llama-swap UI, ai-01 stack shipped 2026-07-15) was added to /opt/stacks/caddy/caddy/Caddyfile at 2026-07-15 11:00 UTC, but the caddy container has been running since 2026-07-09 and was never reloaded. The running config (admin API) does not contain llamaswap.tabaska.us, so caddy has no cert/route for it and clients get a TLS 'internal error' alert. The upstream itself is healthy (rig:9292 /health returns OK), so a `caddy reload` would fix it. This is the ONLY vhost missing from the running config; all 43 others are live.


<details><summary>Evidence</summary>

```
$ stat Caddyfile -> 2026-07-15 11:00:31 UTC; docker inspect caddy StartedAt=2026-07-09T20:29:59Z
$ docker exec caddy wget -qO- localhost:2019/config/ | python3 ... -> 'llamaswap in running config: False' (all other Caddyfile hosts present)
$ curl -skv --resolve llamaswap.tabaska.us:443:192.168.10.2 https://llamaswap.tabaska.us/ -> SSL routines:ST_CONNECT:tlsv1 alert internal error (HTTP code 000)
$ curl http://192.168.10.12:9292/health -> OK (upstream fine)
```

</details>

### H9. ha.tabaska.us returns 400 Bad Request — HA rejects the proxy (trusted_proxies not honoring mini), route unusable

**Host:** mini · **Component:** caddy / home-assistant · **Auditor:** svc:infra-mini


The ha.tabaska.us vhost proxies to 192.168.10.50:8123. HA answers every proxied request with '400: Bad Request' while direct access to http://192.168.10.50:8123 returns 200. This is the exact failure mode the Caddyfile comment warns about ('HA will answer 400 ... until http.use_x_forwarded_for + trusted_proxies include the mini' — supposedly configured in run-5, but it is not working now). The public/LAN HTTPS entry point for Home Assistant is effectively dead. Not in the known-issues list (HA known issues cover backups/HACS/stale SSH alias only).


<details><summary>Evidence</summary>

```
$ curl -sk --resolve ha.tabaska.us:443:192.168.10.2 https://ha.tabaska.us/ -> '400: Bad Request'
$ curl -s -o /dev/null -w '%{http_code}' http://192.168.10.50:8123/ -> 200
```

</details>

### H10. AMP scheduled Minecraft backups silently failing since 2026-07-10 22:00 (backup count limit reached, ReplacePolicy=DoNothing)

**Host:** rig · **Component:** AMP / MinecraftCross01 backups · **Auditor:** svc:gaming


The MinecraftCross01 instance runs an hourly scheduled backup, but LocalFileBackupPlugin is configured with Limits.MaxBackupCount=28 and Limits.ReplacePolicy=DoNothing. The Backups dir holds exactly 28 zips (~458MB each, 12G total), newest dated Jul 10 22:00. Since then every hourly attempt logs 'Backup not taken: Backup count limit reached.' — ~115 consecutive silent failures over 5 days with no rotation and no alerting. Local point-in-time restore points for the Minecraft world are frozen at Jul 10; only the nightly rig restic snapshot of the instance dir (which does run, see separate finding) captures newer world state, at 1/day granularity instead of the intended hourly. Fix (not applied, read-only pass): set ReplacePolicy to delete-oldest or raise/prune MaxBackupCount. Path: /opt/stacks/amp/config/.ampdata/instances/MinecraftCross01/Backups/


<details><summary>Evidence</summary>

```
ssh rig 'grep -aiE backup .../MinecraftCross01/AMP_Logs/AMPLOG_2026-07-15\ 10-51-23.log'
[11:00:00] [System Activity/31] : Creating Backup: Scheduled Backup
[11:00:00] [System Warning/31]  : Backup not taken: Backup count limit reached.
[12:00:00] ... [15:00:00] same warning every hour (also present in 07-11..07-15 logs)

ssh rig 'ls -lt .../MinecraftCross01/Backups/ | head -3; ls ... | wc -l'
-rw-r--r-- 458419474 Jul 10 22:00 20260711-020000-e7becf45....zip  (newest; 28 zips + Backups.json = 29)

grep LocalFileBackupPlugin.kvp:
Limits.MaxBackupCount=28
Limits.ReplacePolicy=DoNothing
Limits.MaxTotalSizeMB=20280
```

</details>

### H11. Gossip Girl: all 120 'imported' episode files are Sample/*.avi junk; real content is 43GB of unextracted RARs; show absent from Plex

**Host:** nas · **Component:** sonarr + plex (TV library) · **Auditor:** flow:movies-tv


Sonarr reports hasFile=True for 120 Gossip Girl episodes (6 seasons) but every episodeFile points at a Sample/*.avi (9-22MB). The actual episodes are unextracted scene RAR sets (.rar/.r00-.r23, Dec 2023 vintage, 43GB at /volume3/tv/Gossip.Girl) that were never unpacked. Plex title search returns 0 hits for the entire show. Sonarr shows green (nothing in wanted/missing) so nothing will ever fix this automatically. Folder ACL is fine (PlexMediaServer ACE present, identical to working shows). This is the TV-side analog of known issue 13 (which only covered Radarr).


<details><summary>Evidence</summary>

```
curl sonarr /api/v3/episodefile?seriesId=<GossipGirl> -> 120 files, e.g.:
/tv/Gossip.Girl/Gossip.Girl.S05.DVDRip/Gossip.Girl.S05E01.DVDRip.XviD-REWARD/Sample/gossip.girl.s05e01...sample.avi size 22196224
ssh nas ls 'Gossip.Girl.S01E01.DVDRip.XviD-ORPHEUS/' -> gossip.girl.s01e01...rar + .r00-.r23 (15MB parts), Sample/ dir; du -sh /volume3/tv/Gossip.Girl -> 43G
Plex /library/sections/2/all?title=Gossip Girl -> 0 hits; sonarr series stats: epFiles:120 sizeGB:1.2
```

</details>

### H12. 6 movies live with sample-file imports (6-129MB) as their movieFile — hasFile=True, none watchable in Plex `known-issue`

**Host:** nas · **Component:** radarr (movie library integrity) · **Auditor:** flow:movies-tv


Current live state of known issue 13: American Hustle (23.7MB sample.avi), American Reunion (12.9MB), Intruders (10.8MB), Rampage (129MB Sample.mkv), Take Me to the River (6.3MB Sample.mp4), xXx: Return of Xander Cage (14.7MB sample.avi). All monitored=True, all dateAdded 2026-06-28 (bulk library scan, not new pipeline imports — no sample imports in the last 15 pipeline imports, which are all 5-22GB). None of these 6 titles resolve in Plex by tmdb guid.


<details><summary>Evidence</summary>

```
radarr /api/v3/movie cross-checked vs Plex section 1 includeGuids:
American Hustle | monitored: True | dateAdded: 2026-06-28T17:36:18Z | size_MB: 23.7 | ...sample.avi
American Reunion | 12.9MB sample.avi; Intruders | 10.8MB sample.avi; Rampage | 129.3MB Sample.mkv
Take Me to the River | 6.3MB Sample.mp4; xXx: Return of Xander Cage | 14.7MB sample.avi
All 6 tmdbIds absent from Plex Movies guid set (396 tmdb guids)
```

</details>

### H13. Radarr movie 'All About My Mother' is mapped to the Mamma Mia! 2008 file — movie not actually in library

**Host:** nas · **Component:** radarr (metadata mapping) · **Auditor:** flow:movies-tv


Radarr tmdb 99 (All About My Mother, 1999) has hasFile=True but its movieFile path is /movies/Mama Mia! 2008 10bit hevc-d3g/Mama Mia! 2008 BluRay 10Bit 1080p DD5.1 H265-d3g.mkv (2.1GB), a completely different movie (mis-identified during the 2026-06-28 bulk scan). Plex correctly lists Mamma Mia! 2008 and has NO All About My Mother. Anyone trusting Radarr (or a request layer syncing from it) believes this movie is available when it does not exist anywhere in the library.


<details><summary>Evidence</summary>

```
radarr /api/v3/movie tmdb 99: path: /movies/Mama Mia! 2008 10bit hevc-d3g/Mama Mia! 2008 BluRay 10Bit 1080p DD5.1 H265-d3g.mkv | dateAdded: 2026-06-28T17:45:01Z
Plex section 1 title search 'All About My Mother' -> 0 hits; 'Mamma Mia' -> Mamma Mia! 2008 + Here We Go Again 2018 (same file path as radarr's)
```

</details>

### H14. Phantom 'downloading' request: 3OH!3 - 3OH!3 stuck since 2026-07-13, artist unmonitored in Lidarr, zero grabs, will never auto-search `known-issue`

**Host:** mini + nas · **Component:** musicseerr -> lidarr · **Auditor:** flow:music


MusicSeerr request_history has exactly 1 non-imported request: 3OH!3 self-titled (mbid 4215d04a-8022-3c62-a616-be9fb4a5e9bd, lidarr_album_id 6037), status=downloading since 2026-07-13T20:17:16Z (2 days). Lidarr: album exists and album.monitored=True, but artist.monitored=False, 0/11 tracks on disk, 0 history events for the album (never grabbed), download queue totalRecords=0, and it is ABSENT from wanted/missing (Lidarr excludes albums whose artist is unmonitored) so automatic search will never pick it up. MusicSeerr queue.db has 0 pending_jobs and 0 dead_letters, so MusicSeerr is not retrying either — the request is permanently stuck showing 'downloading'. Variant of known issue 12 (there the album itself was monitored=False; here the artist-level monitor flag is the blocker, same phantom symptom). Fix (not applied, log-only): monitor artist 3OH!3 in Lidarr + trigger AlbumSearch for album 6037.


<details><summary>Evidence</summary>

```
sqlite3 library.db "select ... from request_history where status not in ('completed','available')" -> 4215d04a...|3OH!3|3OH!3|2026-07-13T20:17:16|...|downloading|6037 (all 13 others 'imported'). curl /api/v1/album/6037 -> monitored: True | artist.monitored: False | stats: trackFileCount 0/11, sizeOnDisk 0. curl /api/v1/queue -> queue total: 0. curl /api/v1/history?albumId=6037 -> history records: 0. curl /api/v1/wanted/missing -> total 1 (only Eminem 5030; 6037 absent).
```

</details>

### H15. Naamah's Curse grab imported into duplicate misspelled book record 'Namaah's Kiss' — request falsely stuck AND a second request falsely completed

**Host:** nas · **Component:** readarr / rreading-glasses metadata · **Auditor:** flow:books


rreading-glasses metadata contains a junk duplicate record 'Namaah's Kiss' (readarr book id 262, misspelled) alongside the real 'Naamah's Curse' (id 293). The 2026-07-13 'Naamah's Curse' grab was matched to book 262: readarr deleted book 262's prior file and imported the Curse epub as 'Jacqueline Carey - Namaah's Kiss.epub'. Net live state: book 293 (Naamah's Curse) has 0 files so the libreseerr request is stuck 'processing 0%' forever even though CWA actually HAS Naamah's Curse (58) (the connect script copied the file and CWA identified it correctly from embedded metadata); meanwhile the earlier 'Naamah's Kiss' request shows completed 100% because book 262 has a file — but that file is Curse content and NO Naamah's Kiss exists anywhere in the CWA library (Jacqueline Carey dir: Dart, Avatar, Chosen, Blessing, Curse, Miranda only). User-facing: a book reported complete is not actually available. Same junk-edition root-cause family as the libreseerr app.py patch (known issue 10) but this is a new, readarr-side manifestation.


<details><summary>Evidence</summary>

```
curl http://192.168.10.4:8787/api/v1/history?bookId=293 -> only '2026-07-13T01:37:37Z grabbed Naamah's Curse'; bookId=262 history -> '01:37:46Z bookFileImported Kushiel's Legacy 08 - Naamah's Curse' + '01:37:45Z bookFileDeleted .../Namaah's Kiss/...'; /api/v1/book: '262 | Namaah's Kiss | mon: True | files: 1' vs '293 | Naamah's Curse | mon: True | files: 0'; ssh nas ls: /volume1/docker/readarr/library/Jacqueline Carey/Namaah's Kiss/Jacqueline Carey - Namaah's Kiss.epub 651115 B; /volume1/books/Jacqueline Carey/Naamah's Curse (58)/Naamah's Curse - Jacqueline Carey.epub 649061 B; no 'Naamah's Kiss' dir in /volume1/books
```

</details>

### H16. 4 book requests stuck 'processing 0%' >48h with zero readarr download activity and no retry or error surfaced

**Host:** mini · **Component:** libreseerr -> readarr request flow · **Auditor:** flow:books


libreseerr requests created 2026-07-13 00:30-01:35 for Kushiel's Justice (readarr id 261), Kushiel's Scion (284), The Rotten Romans (280) and Naamah's Curse (293) are still status=processing, progress=0, error=null on 2026-07-15. Readarr has NO history at all for 261/280/284 (never grabbed anything — searches on IPTorrents/MyAnonamouse/Zenith returned nothing), queue is empty (totalRecords 0), and nothing retries the search, so these will sit forever with no error shown to the user. 293 is the mis-import case (separate finding). Also found readarr book 263 'Kushiel's Mercy' monitored with 0 files, empty history, and no libreseerr request tracking it at all (orphan monitored book). Adjacent to known issue 11's 'searches return ~0 grabs' pattern but that is logged for sonarr; the readarr-side silent stall is unlogged.


<details><summary>Evidence</summary>

```
curl http://192.168.10.2:8789/api/requests -> 5x status 'processing', progress 0, created 2026-07-13, error null; for id in 261 263 280 284: curl http://192.168.10.4:8787/api/v1/history?bookId=$id -> '(none)'; /api/v1/queue -> totalRecords: 0; /api/v1/book -> ids 261,263,280,284 all 'mon: True | files: 0'; /api/v1/indexer -> IPTorrents, MyAnonamouse, Zenith all enabled
```

</details>

### H17. Immich contains ZERO assets — no phone backup has ever flowed since the Jul 2 deployment; server and backup jobs are green around an empty library

**Host:** nas · **Component:** Immich (photos flow / mobile backup) · **Auditor:** flow:youtube-photos


Immich v2.7.5 is up and healthy (LAN and public ping both 'pong', web 200 in 9ms), but its entire media store is empty: UPLOAD_LOCATION=/volume1/photo (per .env.example; real .env is root-only) and every data dir — upload/, library/, thumbs/, encoded-video/, profile/ — contains only the 13-byte .immich marker (dir mtimes 2026-07-02 18:30 = deploy time). No per-user upload directories exist, meaning no mobile client has ever uploaded a single asset. Corroborated by DB dump sizes: 8 nightly pg_dumpall files vary by <300 bytes across a week (16,658,579-16,658,872 B) — a completely static database (the ~16MB is Immich's built-in geodata, not user data). Classic monitoring-vs-reality gap (cf. known issue 15): ping/version/healthchecks/dump jobs all green while the flow's actual purpose (phone photo backup) is not happening at all. Either the mobile app was never set up/logged in, or uploads are failing before reaching the server; server-side there is zero trace of any attempt.


<details><summary>Evidence</summary>

```
curl http://192.168.10.4:2283/api/server/ping -> {"res":"pong"}; /api/server/version -> {"major":2,"minor":7,"patch":5}; https://immich.tabaska.us/api/server/ping -> pong
ssh nas 'ls -la /volume1/photo/upload /volume1/photo/library ...' -> each dir: only '.immich' (13 bytes, Jul 11 01:33); dirs dated Jul 2 18:30
ls -lat /volume1/docker/immich/backups -> immich-2026-07-08..15.sql.gz all 16,658,5xx-16,658,8xx bytes (delta <300B over 8 days)
```

</details>

### H18. llamaswap vhost added to Caddyfile on disk but caddy never reloaded — TLS handshake fails, route dead

**Host:** mini · **Component:** caddy / llamaswap.tabaska.us · **Auditor:** flow:dns-proxy


The ai-01 buildout (2026-07-15) added the llamaswap.{$DOMAIN} block to /opt/stacks/caddy/caddy/Caddyfile (file mtime 2026-07-15 11:00 UTC), but the caddy container has been running since 2026-07-09 and its live admin-API config contains 43 vhosts — every on-disk site EXCEPT llamaswap.tabaska.us. No cert was ever requested (zero llamaswap entries in caddy logs), so clients get a TLS 'internal error' alert. The upstream itself is fine (rig 192.168.10.12:9292 answers 302), so a config reload is the only missing step. Not fixed per read-only mandate.


<details><summary>Evidence</summary>

```
curl -sk --resolve llamaswap.tabaska.us:443:192.168.10.2 https://llamaswap.tabaska.us/ -> CURL_ERR(35) 'tlsv1 alert internal error'
ssh mini 'stat -c %y /opt/stacks/caddy/caddy/Caddyfile' -> 2026-07-15 11:00:31
ssh mini 'docker inspect caddy --format {{.State.StartedAt}}' -> 2026-07-09T20:29:59Z
ssh mini 'docker exec caddy wget -qO- http://localhost:2019/config/ | grep -o "llamaswap"' -> (no match; 43 other tabaska.us vhosts present)
curl -s -o /dev/null -w %{http_code} http://192.168.10.12:9292/ -> 302 (upstream alive)
```

</details>

### H19. ha.tabaska.us returns 400 Bad Request from HA — trusted_proxies never configured, proxy route broken

**Host:** mini · **Component:** caddy / ha.tabaska.us -> Home Assistant · **Auditor:** flow:dns-proxy


Caddy forwards to 192.168.10.50:8123 but HA rejects every proxied request with '400: Bad Request' (response Server header 'Python/3.14 aiohttp' proves it reaches HA and HA refuses the X-Forwarded-For because the mini's Docker/caddy source IP is not in http.trusted_proxies). HA direct on :8123 is healthy (200, API running). The Caddyfile comment says this would be 'configured in run-5' — it either never happened or regressed, so the published HTTPS entry point for Home Assistant is dead while direct HTTP works.


<details><summary>Evidence</summary>

```
curl -sk --resolve ha.tabaska.us:443:192.168.10.2 -i https://ha.tabaska.us/ -> HTTP/2 400, server: Python/3.14 aiohttp/3.13.5, via: 1.1 Caddy, body '400: Bad Request'
curl -s -o /dev/null -w %{http_code} http://192.168.10.50:8123/ -> 200
curl -H 'Authorization: Bearer <ha token>' http://192.168.10.50:8123/api/ -> {"message":"API running."}
```

</details>

### H20. bucket-restic has fileLock enabled but NO default retention and NO per-file retention — documented 'GOVERNANCE 30d' immutability is not in effect

**Host:** backblaze-b2 · **Component:** bucket-restic Object Lock · **Auditor:** flow:backups


Memory/known-issue record for sec-03 claims bucket-restic has 'Object Lock GOVERNANCE 30d = ransomware-immutable'. Live API shows isFileLockEnabled=true but defaultRetention mode/period = null, and every sampled file version (mini/config, mini/data packs) has fileRetention mode=null retainUntilTimestamp=null. So nothing in the bucket is actually lock-protected. The real protection is only (a) the append-only key on mini/rig (delete attempts 401 — proven by mini's 07-15 nightly log) plus (b) lifecycle daysFromHidingToDeleting=30. The master key (deleteFiles + bypassGovernance) sits in plaintext in foss-setup/.handoff-secrets.yaml on the laptop, so a laptop compromise = instant hard-delete of all restic history; GOVERNANCE default retention would have prevented that for 30d. Fix (operator, not applied): set default bucket retention GOVERNANCE 30d via b2_update_bucket / S3 put-object-lock-configuration.


<details><summary>Evidence</summary>

```
curl -H "Authorization: $TOKEN" 'https://api005.backblazeb2.com/b2api/v3/b2_list_buckets?accountId=6e27a54eeeae'
bucket-restic | type: allPrivate
  fileLock: {"value": {"defaultRetention": {"mode": null, "period": null}, "isFileLockEnabled": true}}
  lifecycle: [{"daysFromHidingToDeleting": 30, "fileNamePrefix": ""}]
b2_list_file_versions bucket-restic (6 newest + 3 mini/data packs):
mini/config | upload | retention: {"value": {"mode": null, "retainUntilTimestamp": null}}
mini/data/00/0021514c... | retention: {"value": {"mode": null, "retainUntilTimestamp": null}}
(all sampled files identical: no retention, no legal hold)
```

</details>

### H21. ha.tabaska.us returns 400 for every request — HA has no trusted_proxies/use_x_forwarded_for; recurring http.forwarded errors through today

**Host:** ha (192.168.10.50) + mini/caddy · **Component:** HA http integration / caddy reverse proxy (ha.tabaska.us) · **Auditor:** flow:ha-deep


The caddy container on mini proxies ha.tabaska.us -> 192.168.10.50:8123, but HA's http integration is not configured for reverse proxies, so every proxied request is rejected 400. HA's own log shows 6 occurrences of the forwarded-header rejection from 192.168.10.2 (mini) between 2026-07-07 and 2026-07-15 (today). The Caddyfile even carries a note that this would 400 'until configured in run-5' — that HA-side config never landed. Direct access at http://192.168.10.50:8123 works fine, so this is a broken public/proxied path, not a full outage. Fix (not applied, read-only pass): add http: use_x_forwarded_for + trusted_proxies (mini docker networks / 192.168.10.2) to HA configuration.yaml.


<details><summary>Evidence</summary>

```
curl -sk -o /dev/null -w 'http=%{http_code}\n' https://ha.tabaska.us/ -> http=400 (body '400: Bad Request'); dig +short ha.tabaska.us -> 192.168.10.2
WS system_log/list: [ERROR] x6 homeassistant.components.http.forwarded first=2026-07-07T20:00:57 last=2026-07-15T17:21:57 'A request from a reverse proxy was received from 192.168.10.2, but your HTTP integration is not set-up for reverse proxies'
ssh mini 'sed -n 338,346p /opt/stacks/caddy/caddy/Caddyfile' -> '# NOTE: HA will answer 400 "Bad Request" through this proxy until its `http.use_x_forwarded_for` + `trusted_proxies` include the mini's Docker networks — configured in run-5.' ha.{$DOMAIN} { reverse_proxy {$HA_IP}:8123 }
```

</details>

### H22. Palworld server down (REST dead even from localhost, container unhealthy) since 2026-07-15 22:55 EDT — user-facing, unresolved ~9h+

**Host:** rig · **Component:** palworld game server · **Auditor:** repo:verification-suite


palworld-rest-liveness has failed every fast-tier (10-min) and url-tier (hourly) run since Jul 16 02:55 UTC (= 22:55 EDT Jul 15, 6 minutes after the rig btrfs went read-only). The REST API answers 000 from the tailnet AND from localhost on the rig; docker health flipped to 'unhealthy'. ntfy transition pages fired (02:55 fast tier, 03:41 url tier) so it was alerted, but the outage persists. Root cause is the read-only filesystem (previous finding); the game server likely cannot write saves either — players may be losing progress even if the UDP path is partially alive. No fix attempted per read-only mandate.


<details><summary>Evidence</summary>

```
journalctl -u verification-fast.service: 'Jul 16 02:45:10 ... 0 failed' → 'Jul 16 02:55:29 ... 1 failed'; ntfy: sent (Verification [None tier]: 1 NEW failure(s))
results-tier-fast.json (11:25 UTC): FAIL palworld-rest-liveness sev=warn, output empty
curl -sm 8 -u admin:*** http://cachyos.tailb31641.ts.net:8212/v1/api/metrics → metrics_http=000
ssh rig 'curl -sm 5 ... http://localhost:8212/v1/api/info' → local_8212=000
ssh rig docker inspect palworld → net=palworld_default health=unhealthy
```

</details>

### H23. Rig restic backups failing — last success 2026-07-15 05:40 UTC, healthchecks dead-man in grace, exactly while the OS disk is corrupting

**Host:** rig · **Component:** restic B2 backups · **Auditor:** repo:verification-suite


The daily sweep flagged restic-snapshot-fresh-rig STALE (age 36h) on Jul 15 14:16 UTC. Healthchecks 'restic-backup-rig' last pinged Jul 15 05:40 UTC and is in 'grace' (will flip down after 6h grace + will page). The Jul 16 01:38 EDT timer run left no successful ping — restic cannot write cache/locks on the now read-only filesystem. Net effect: the machine whose disk is actively corrupting is the one whose /etc + /home backups have stopped. Distinct from known issue 5 (the /opt coverage gap): this is total backup failure, not scope.


<details><summary>Evidence</summary>

```
results.json (2026-07-15T14:16:25Z): FAIL restic-snapshot-fresh-rig sev=warn | out: STALE age_hours=36 (marker)
Healthchecks API (GET /api/v3/checks/): restic-backup-rig status=grace last_ping=2026-07-15T05:40:59+00:00 period=86400 grace=21600
ssh rig 'systemctl list-timers | grep restic' → restic-backup.timer last ran Thu 2026-07-16 01:38:31 EDT (no subsequent HC ping)
```

</details>

### H24. LLM triage layer silently dead: /etc/verification/env pins qwen3-coder:30b on ollama :11434, which was trimmed 2026-07-15 — every triage completion 404s

**Host:** mini · **Component:** verification / llm-triage (verify-03/04) · **Auditor:** repo:verification-suite


llm-triage.sh (repo + deployed, updated Jul 15) now defaults to llama-swap :9292 / qwen3.6-35b-a3b, but it sources /etc/verification/env first and env still sets LLM_BASE_URL=http://cachyos.tailb31641.ts.net:11434/v1 and LLM_MODEL=qwen3-coder:30b. The ollama shim only holds nomic-embed-text, tag:fast, llama3.2:3b, so chat completions return HTTP 404. The llm_up() gate only GETs /models, which the shim answers 200 — so the WoL/incident path never trips and the failure is silent: triage-2026-07-15.md contains only 'triage failed — model did not return valid JSON / HTTP Error 404' escalate:true stubs for both failed checks. verify-03/04 has produced zero useful verdicts since the ai-01 model trim. Repo README ('Default: ollama ... qwen3-coder:30b') and systemd/env.example still document the dead endpoint, so a rebuild would re-create the bug.


<details><summary>Evidence</summary>

```
ssh mini grep /etc/verification/env → LLM_BASE_URL=http://cachyos.tailb31641.ts.net:11434/v1; LLM_MODEL=qwen3-coder:30b
curl :11434/api/tags → ollama_models= ['nomic-embed-text:latest', 'tag:fast', 'llama3.2:3b']  (no qwen3-coder:30b)
/var/lib/verification/triage-2026-07-15.md: "likely_cause": "LLM request failed (attempt 2): HTTP Error 404: Not Found" (both checks)
repo bin/llm-triage.sh: LLM_BASE_URL="${LLM_BASE_URL:-http://cachyos.tailb31641.ts.net:9292/v1}" — env override wins
```

</details>

### H25. litellm-db segfaulted (exit 139) 52 min after RO remount; docker ps still falsely reports it 'Up (healthy)'

**Host:** rig · **Component:** litellm-db (postgres container) · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


Postgres backing LiteLLM crashed with exit code 139 (SIGSEGV) at 2026-07-16T03:41:37Z, ~52 minutes after the RO remount — almost certainly a failed WAL/data write on the RO FS. Because the docker daemon cannot persist container state to the RO disk, 'docker ps' still lists litellm-db as 'Up 25 hours (healthy) running' while 'docker inspect' shows exited/unhealthy — any monitoring that reads docker ps/health is blind to this. Its logs are unreadable ('docker logs litellm-db' fails opening the json.log on the RO FS), so postgres data-integrity state cannot be assessed until the FS is recovered; a SIGSEGV mid-write raises DB corruption risk on next start.


<details><summary>Evidence</summary>

```
ssh rig 'docker ps -a --filter name=litellm-db --format ...' -> litellm-db | Up 25 hours (healthy) | running
docker inspect litellm-db -> State=exited Running=false ExitCode=139 OOM=false FinishedAt=2026-07-16T03:41:37.105263944Z Health=unhealthy
docker exec litellm-db ... -> Error response from daemon: container 727a1240... is not running
docker logs litellm-db -> Error response from daemon: open /var/lib/docker/containers/727a.../727a...-json.log: read-only file system
```

</details>

### H26. LiteLLM effectively DOWN for all virtual-key clients: 503 no_db_connection on every keyed request

**Host:** rig · **Component:** litellm (LiteLLM proxy :4000 / llm.tabaska.us) · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


With litellm-db dead, LiteLLM cannot validate virtual API keys. A completion request with the valid ops-agent key (ai_stack.litellm_ops_agent_key) returns 503 'authentication database is temporarily unreachable' (type no_db_connection). readiness=503, liveliness=200. This breaks every LiteLLM consumer on virtual keys: opencode key, open-webui key (OWUI chats via LiteLLM), ops-agent key, and the LiteLLM /ui admin. Meanwhile master-key/liveliness probes from mini keep returning 200 (constant GET /v1/models 200 from 192.168.10.2 in the litellm log), so dashboards show it up. llm.tabaska.us still serves 200 through mini caddy (reverse_proxy {$RIG_IP}:4000) — the front door is open but the service behind it rejects all normal clients.


<details><summary>Evidence</summary>

```
ssh rig "curl http://127.0.0.1:4000/v1/chat/completions -H 'Authorization: Bearer sk-TGU31a...' -d '{\"model\":\"fast\",\"max_tokens\":10,...}'" ->
{"error":{"message":"Service Unavailable, the authentication database is temporarily unreachable. Please retry shortly.","type":"no_db_connection","param":"None","code":"503"}}
curl http://127.0.0.1:4000/health/readiness -> 503 ; /health/liveliness -> 200
curl https://llm.tabaska.us -> 200 (caddy on mini: llm.{$DOMAIN} -> reverse_proxy {$RIG_IP}:4000)
```

</details>

### H27. rig restic backup missed its nightly run under the RO incident (healthchecks: down)

**Host:** rig · **Component:** restic nightly backup · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


restic-backup-rig on healthchecks is 'down', last successful ping 2026-07-15T05:40:59Z, i.e. the ~05:40 Jul 16 run never reported. Consistent with the RO root: restic cannot write its local cache/lock state, and the source filesystem it backs up (/etc + /home) is the corrupted RO btrfs. Net effect: the rig currently has a corrupting OS disk AND a stalled backup cadence at the same time — the last good restic snapshot predates the corruption event, which is actually the safe one to restore from; nothing after Jul 15 05:40 UTC is captured.


<details><summary>Evidence</summary>

```
curl http://192.168.10.2:8001/api/v3/checks/ -H 'X-Api-Key: civ8...' ->
restic-backup-rig | down | last_ping: 2026-07-15T05:40:59+00:00
(RO remount at Jul 15 22:49 EDT / Jul 16 02:49 UTC per kernel journal; nightly run window ~05:40 UTC missed)
```

</details>

### H28. Root cause of zero assets: Immich mobile app was never paired — only session ever created is a Safari/macOS web session; no upload has ever occurred

**Host:** nas · **Component:** immich · **Auditor:** gap:NAS Immich — root-cause the ZERO-assets finding via the readable Postgres dump (not just filesystem emptiness)


The 2026-07-16 02:30 nightly pg_dumpall proves the server is healthy but has never ingested a single asset since the Jul-2 deploy. Concretely: public.asset = 0 rows, asset_audit = 0 (so nothing was ever uploaded-then-deleted), library = 0 (no external library), smart_search/asset_exif/asset_file all 0, and both user rows show quotaUsageInBytes=0. Two users exist: brandon.tabaska@protonmail.com (admin, created 2026-07-03 01:33Z, onboarded) and kaelyn92@icloud.com (created 2026-07-14). Exactly ONE session exists in the entire history: deviceType=Safari deviceOS=macOS created 2026-07-03, last used 2026-07-15 00:16Z — no iOS/Android app session was EVER registered, appVersion is NULL. One API key ('API Key', permissions {all}, created 2026-07-03 23:33Z, likely for HA/monitoring) has produced no writes. Server itself is alive and running jobs (facial-recognition lastRun 2026-07-16 04:00Z; /api/server/ping = pong on both https://immich.tabaska.us and 192.168.10.4:2283, v2.7.5). Conclusion: no phone backup ever flowed because the Immich iOS app was never installed/paired — server-side setup stopped at web onboarding. This correlates with the HA Btiphone companion-app pattern (most btiphone_* sensors 'unavailable' since 2026-07-07, last battery update 2026-07-13): phone-side integrations are generally degraded/unmaintained, but for Immich this is not a regression — pairing simply never happened. All 11 nightly dumps since Jul 2 are byte-similar (~16,658,7xx bytes), confirming the DB has been static content-wise the whole time.


<details><summary>Evidence</summary>

```
ssh nas 'cat /volume1/docker/immich/backups/immich-2026-07-16.sql.gz' > scratch; gunzip; python row-count of COPY blocks:
  0 public.asset | 0 public.asset_audit | 0 public.library | 2 public."user" | 1 public.session | 1 public.api_key
COPY public.session row: 84fa31d1... 2026-07-03 01:34:01+00  2026-07-15 00:16:31+00  936853a2-...  Safari  macOS  ... appVersion=\N
COPY public."user": brandon.tabaska@protonmail.com ... quotaUsageInBytes=0 ; kaelyn92@icloud.com ... quotaUsageInBytes=0
curl https://immich.tabaska.us/api/server/ping -> {"res":"pong"} ; /api/server/version -> {"major":2,"minor":7,"patch":5}
ha_states.json (this pass): sensor.btiphone_last_update_trigger=unavailable since 2026-07-07T23:13Z; sensor.btiphone_battery_level last 2026-07-13T16:29Z
```

</details>

### H29. Root cause of dead UPS chain: DSM UPS support is disabled AND no UPS is physically attached to the NAS — upsd never runs, so 3493 refuses connections from mini

**Host:** nas · **Component:** NUT/UPS server (DSM UPS support) · **Auditor:** gap:NAS-side NUT/UPS server — root-cause the dead UPS-monitoring chain (HIGH finding only diagnosed from mini)


The NUT server on the NAS is not merely misconfigured — it does not exist at runtime. Three independent confirmations: (1) no listener on 3493 and no upsd process (earlier 'upsd' grep hits were self-matches on 'upstream'/'startups' strings); (2) no UPS hardware present: /dev/ups* absent, /sys/class/power_supply/ does not exist at all, and the USB bus carries only Synology's internal boot device (f400:f400) plus two root hubs — no APC/CyberPower/other UPS vendor device; (3) DSM API SYNO.Core.ExternalDevice.UPS get returns enable=false ('Enable UPS support' is OFF), ACL_enable=false with ACL_list=[] ('Enable network UPS server' is OFF and the permitted-DiskStation list is empty — 192.168.10.2 is NOT in it), usb_ups_connect=false, empty model/manufacture, status='usb_ups_status_unknown'. Residual mode='SLAVE' with empty net_server_ip suggests the DSM UPS page was never (or is no longer) meaningfully configured. Net effect: mini's upsmon (MONITOR ups@192.168.10.4 ... slave) polls a service that will never start; the fleet has zero power-loss shutdown protection via this chain, and the NAS itself has no UPS attached. Fix requires operator action: physically attach the UPS to the NAS via USB, then in DSM enable UPS support + network UPS server and add 192.168.10.2 to permitted DiskStations (or retire the mini upsmon config if UPS monitoring is abandoned). SYNO.Core.Hardware.UPS API does not exist on this DSM, so SYNO.Core.ExternalDevice.UPS is authoritative.


<details><summary>Evidence</summary>

```
$ ssh nas 'ss -ltn 2>/dev/null | grep 3493 || netstat -ltn 2>/dev/null | grep 3493 || echo NO_LISTENER'
NO_LISTENER
$ ssh nas 'for p in /proc/[0-9]*/cmdline; do c=$(tr "\0" " " < $p); case "$c" in *ups*) echo "$p: $c";; esac; done'
(only the probe shell, rreading-glasses '--upstream=www.goodreads.com', and sshd 'startups' matched — no upsd)
$ ssh nas 'for d in /sys/bus/usb/devices/*/; do ... idVendor:idProduct product; done'
/sys/bus/usb/devices/1-4/ f400:f400 Synology DiskStation
/sys/bus/usb/devices/usb1/ 1d6b:0002 xHCI Host Controller
/sys/bus/usb/devices/usb2/ 1d6b:0003 xHCI Host Controller
$ curl 'http://192.168.10.4:5000/webapi/entry.cgi?api=SYNO.Core.ExternalDevice.UPS&version=1&method=get&_sid=...'
{"data":{"ACL_enable":false,"ACL_list":[],"charge":0,"enable":false,"manufacture":"","mode":"SLAVE","model":"","net_server_ip":"","status":"usb_ups_status_unknown","usb_ups_connect":false},"success":true}
(session logged out after: {"success":true})
```

</details>

### H30. Gossip Girl signature quantified: 177 items tracked green but only a sample on disk (154 Sonarr episodes across 8 series + 23 Radarr movies) — and one NEW occurrence yesterday (2026-07-15) `known-issue`

**Host:** nas · **Component:** sonarr+radarr (sample-file imports) · **Auditor:** gap:NAS unpackerr — live wedge state and archive-extraction backlog never quantified (only 1 case evidenced)


Swept every episodeFile (162 series) and every movieFile (318 movies). Sonarr episodeFiles whose tracked path is a Sample file: 154 total — Gossip Girl 120 (all six DVDRip seasons, 0.5-22MB sample.avi each), Animaniacs (1993) 24, The Way of the Househusband 3, Leverage 3, Yuri!!! on Ice 1 (S01E03 = 28MB /Sample/ mkv while Sonarr reports the series 12/12 complete), Rapunzel's Tangled Adventure 1, Hollywood (2020) 1, Call the Midwife 1. Radarr: 23 movies where hasFile=True but the movieFile is a 1-37MB sample/trailer/junk file (e.g. Cabaret 4.5MB Sample.mp4, The Cabin in the Woods -> RARBG.com.mp4 1.0MB, Jennifer's Body -> a trailer .mov, Hobbit BotFA 5.8MB sample.avi). Not purely historical: EverAfter's movieFile flipped to 'Ever After...NPW-Sample.avi' (24.0MB) with dateAdded 2026-07-15T20:02:25Z — i.e. Radarr registered a sample as the movie yesterday. In every one of these the real content sits (or sat) in a never-extracted rar set alongside, so the arr and any liveness monitoring show green while the title is unwatchable in Plex. This is the same class as known issue 13 but far broader than the single evidenced case, and it affects Sonarr as much as Radarr.


<details><summary>Evidence</summary>

```
python sweep of sonarr /api/v3/episodefile per series + radarr /api/v3/movie:
'sample'-path episodeFiles per series: 120 Gossip Girl / 24 Animaniacs / 3 Househusband / 3 Leverage / 1 Yuri on Ice / 1 Tangled / 1 Hollywood(2020) / 1 Call the Midwife = 154.
example: Yuri!!! on Ice | /tv/Yuri On Ice/Yuri.On.ICE.S01E03.../Sample/aniurl-yoi.s01e03.1080p.web-sample.mkv | 28.4MB (series stats: 12/12 episodeFileCount).
radarr: 23 suspicious movieFiles (<100MB or sample), e.g. Cabaret .../Sample.mp4 4.5MB; The Cabin in the Woods .../RARBG.com.mp4 1.0MB.
EverAfter | Ever After A Cinderella Story 1998 BRRip XvidHD 720p-NPW-Sample.avi | 24.0 MB | added: 2026-07-15T20:02:25Z (hasFile=True).
```

</details>


---

## MEDIUM (62)

### M1. Dead Pterodactyl panel from Jun 2025 still runs a full LEMP+redis stack on the host: every-minute root cron, zombie nginx listening on no ports, daily telemetry errors

**Host:** mini · **Component:** host OS: pterodactyl leftovers (nginx, php8.3-fpm, mariadb, redis-server, root cron) · **Auditor:** host:mini


/var/www/pterodactyl (files dated Jun 18 2025) survives on the host even though game hosting moved to AMP on rig. Root cron fires 'php /var/www/pterodactyl/artisan schedule:run' EVERY MINUTE (output to /dev/null); the panel's queue worker pteroq.service is disabled; laravel writes an identical 13KB error log daily at ~00:01 (cURL error 35 TLS failure phoning https://telemetry.pterodactyl.io). Host nginx is active but has zero sites-enabled and does not listen on any port (80/443 are owned by docker-proxy/caddy) — a pure zombie. php8.3-fpm, mariadb (127.0.0.1:3306) and redis-server (127.0.0.1:6379) are all active serving nothing else obvious. Dead path + wasted RAM on an 8GB box already using 1.9Gi swap; listeners are localhost-only so no network exposure.


<details><summary>Evidence</summary>

```
grep CRON /var/log/syslog | tail -> '(root) CMD (php /var/www/pterodactyl/artisan schedule:run >> /dev/null 2>&1)' once per minute. 'systemctl list-unit-files | grep ptero' -> 'pteroq.service disabled'. 'systemctl is-active nginx php8.3-fpm mariadb redis-server' -> all active; 'ls /etc/nginx/sites-enabled/' -> empty; sudo ss -tlnp :80/:443 -> docker-proxy only. head of /var/www/pterodactyl/storage/logs/laravel-2026-07-14.log -> 'production.ERROR: cURL error 35 ... for https://telemetry.pterodactyl.io'; logs 13014 bytes daily.
```

</details>

### M2. etckeeper commits intermittently fail on /etc/.git/index.lock races — 26 failures Jul 07-15 including 3 today

**Host:** mini · **Component:** etckeeper-commit.service · **Auditor:** host:mini


etckeeper-commit.service ('Commit /etc changes with etckeeper', /etc/systemd/system/etckeeper-commit.service) fails with exit 128 'Unable to create /etc/.git/index.lock: File exists' when two invocations race — e.g. today at 13:56:29 two 'Starting Commit /etc changes...' fired back-to-back right after the ansible-pull/export-manifests run. 26 failed starts in the last 14 days (23x etckeeper-commit + 3x etckeeper.service Autocommit), incl. Jul 15 06:43:24 (x2), 11:39:54, 13:56:29. No stale lock exists now (checked with sudo), so each failure is a transient race, but each one silently drops that /etc change commit — /etc version history has gaps whenever ansible-pull, the daily etckeeper.timer, and triggered commits overlap.


<details><summary>Evidence</summary>

```
journalctl -S '2026-07-15 13:55:30' -U '2026-07-15 13:57:00' -> 'etckeeper[676054]: fatal: Unable to create /etc/.git/index.lock: File exists.' ... 'etckeeper-commit.service: Main process exited, code=exited, status=128' followed immediately by a second 'Starting Commit /etc changes with etckeeper...'. journalctl -S -14days | grep 'Failed to start Commit /etc changes' -> 23 timestamps Jul 07-15. sudo ls /etc/.git/index.lock -> 'No such file or directory' (no stale lock).
```

</details>

### M3. One-shot media maintenance (unpackerr wedge clear) FAILED on 2026-07-11 and will never retry — timer is dead

**Host:** mini · **Component:** media-window-maint.service/.timer · **Auditor:** host:mini


media-window-maint.timer was a one-shot (OnCalendar=2026-07-11 08:30:00 UTC, Persistent=false) meant to clear an unpackerr wedge + retune rclone in the maintenance window. It ran and FAILED: phase-A gave 'unpackerr health=nohealth' on all 18 attempts over ~3 minutes, script exited 1 ('FAIL: phase-A unpackerr health'). Because the OnCalendar date is in the past, the timer now shows NEXT=n/a and will never fire again, so the wedge-clear silently never happened. Whether unpackerr is currently wedged is a NAS-side question outside this host audit, but the maintenance objective was not met and nothing rescheduled it. The dead timer+service units are also leftovers.


<details><summary>Evidence</summary>

```
systemctl list-timers --all -> 'n/a  n/a  Sat 2026-07-11 08:30:00 UTC ... media-window-maint.timer'. journalctl -u media-window-maint -> 'attempt 18: unpackerr health=nohealth' / 'FAIL: phase-A unpackerr health' / 'Main process exited, code=exited, status=1/FAILURE'. systemctl cat media-window-maint.timer -> 'OnCalendar=2026-07-11 08:30:00 UTC' 'Persistent=false'.
```

</details>

### M4. All three data volumes are single-disk with no RAID redundancy (only off-site Hyper Backup protects them)

**Host:** nas · **Component:** storage / mdraid · **Auditor:** host:nas


md2 (vol1, WD161KFGX 16TB), md3 (vol2, WD120 12TB) and md4 (vol3, ST18000 18TB) are each 'raid1 [1/1] [U]' — a single physical disk apiece, zero parity/mirror. DSM confirms all three storagePools are 'shr_without_disk_protect' with one disk each. A single disk failure loses that entire volume; the only recovery path is the B2 Hyper Backup, which (known issue 6) has no Object Lock and client-side encryption OFF. Likely an intentional 3x-Basic layout on this 4-bay unit, but the resilience exposure is real and compounds the backup gaps. md0/md1 (system/swap) ARE 3-way mirrored ([4/3][UUU_], 4th member absent because only 3 disks — normal).


<details><summary>Evidence</summary>

```
cat /proc/mdstat:
md4 : active raid1 sata3p5[0] 17567598528 blocks super 1.2 [1/1] [U]
md3 : active raid1 sata1p5[0] 11708154880 blocks super 1.2 [1/1] [U]
md2 : active raid1 sata2p5[0] 15615154816 blocks super 1.2 [1/1] [U]
DSM Storage API: POOL reuse_3 normal shr_without_disk_protect disks=['sata3'] / reuse_2 ['sata1'] / reuse_1 ['sata2']
```

</details>

### M5. NAS host timezone is US/Pacific while the entire fleet + all containers use America/New_York

**Host:** nas · **Component:** system / timezone · **Auditor:** host:nas


The Synology host runs on US/Pacific (PDT), but _meta.timezone is America/New_York and every container sets TZ=America/New_York. This produces skewed/ambiguous timestamps across the fleet: soularr logs stamp -0400 (EDT) while the host `date` reports PDT -0700, and /var/log/rclone-seedbox.log interleaves both -07:00 and container-local -0400 lines. It also makes DSM scheduled-task run-times (all interpreted in host-local Pacific) ambiguous relative to the operator's 4-7AM EST maintenance window.


<details><summary>Evidence</summary>

```
ssh nas 'date' -> Wed Jul 15 09:20:54 PDT 2026
readlink -f /etc/localtime -> /usr/share/zoneinfo/US/Pacific
grep timezone /etc/synoinfo.conf -> timezone="Pacific"
(container/log stamps are -0400; secrets _meta.timezone: America/New_York)
```

</details>

### M6. soularr parked on the same failed import for 5 days, re-running every 5 min with nothing to do

**Host:** nas · **Component:** soularr · **Auditor:** host:nas


failed_imports.json holds one permanently-parked entry (Eminem - The Marshall Mathers LP, album_id 5030, failed_at 2026-07-10T01:08). Since then soularr fires every 5 minutes, logs 'Skipping failed import album ... (ID: 5030)' then 'No releases wanted ... Soularr finished. Exiting.' — i.e. it has done no productive work for ~5 days and just churns the log (soularr.log 784KB live + 3x 1MB rotations). The album is never re-attempted or cleared. Adjacent to the known MusicSeerr/Lidarr monitored=False phantom class but this is a distinct soularr-side stuck item.


<details><summary>Evidence</summary>

```
tail soularr.log (repeats every 5 min):
12:19:09 Skipping failed import album: Eminem - The Marshall Mathers LP (ID: 5030)
12:19:09 No releases wanted that aren't on the deny list and/or blacklisted
12:19:09 Soularr finished. Exiting...
failed_imports.json: "5030": {... "failed_at": "2026-07-10T01:08:12", "folder_path": ".../failed_imports/Eminem - The Marshall Mathers LP (2000)"}
```

</details>

### M7. health.env is world-readable (0777) and contains an ntfy publish token; broad 0777 across /volume1/docker

> **RESOLVED (fix-23, 2026-07-17):** health.env → root:root 600 and the leaked token (admin-scoped, printed in this doc) was rotated and revoked (old token now 401). World-write stripped across /volume1/docker + /volume1/scripts; five *arr config.xml, stash/.env, media-automation/.env → 600. Guards: checks.d/secrets.yaml (nas-health-env-perms, nas-secret-file-perms, nas-worldwritable-sweep, ntfy-anon-publish-denied), runbook wiki/runbooks/secrets-hygiene.md.

**Host:** nas · **Component:** security / secrets perms · **Auditor:** host:nas


/volume1/scripts/nas/health.env is mode 0777 (rwxrwxrwx+) and holds NTFY_TOKEN=tk_ahl18uonl83eaj3pbqi57h01mfg87 in plaintext, readable by any local user/container. Most service dirs and files under /volume1/docker are likewise 0777 (adguard-nas, beets, soularr logs, stash .env, etc.). Impact is bounded (scoped ntfy publish token, LAN), but it is a plaintext secret with no read restriction. By contrast soularr/config.ini and immich/.env are correctly 0600/root — so the tight perms exist elsewhere, this file just drifted.


<details><summary>Evidence</summary>

```
ls -la health.env -> -rwxrwxrwx+ 1 root root 104 ... health.env
cat health.env -> NTFY_TOKEN=tk_ahl18uonl83eaj3pbqi57h01mfg87
(stash/.env, beets/*, soularr/*.log all -rwxrwxrwx+)
```

</details>

### M8. 131G of extracted/renamed media leftovers accumulating in ~/media/extracted (102 files, never reaped)

**Host:** seedbox · **Component:** ~/media/extracted (leftover imported media) · **Auditor:** host:seedbox


~/media/extracted holds 102 .mkv files (131G) dated Jul 2-10 (e.g. smiley.face...veto 6.6G, several sex.life S02 2.4-3.1G, andor repacks, Animaniacs S01). These are filebot/olaris post-extract copies, already imported to the NAS (imports are copies), but they are NOT Deluge torrents so the deluge-reaper cron (which only removes sonarr-labelled torrents in ~/files/ older than 14d) will never clean them. This is roughly 5% of the 2862G quota held indefinitely and growing with each extracted release.


<details><summary>Evidence</summary>

```
$ du -sh ~/media/extracted -> 131G; ls | wc -l -> 102
$ du -sh ~/media/extracted/* | sort -h | tail: 6.6G smiley.face.2007...veto.mkv, 3.1G sex.life...s02e06, 2.8G sex.life...s02e05/e04
newest: archer.2009.s10e03 (Jul 10 03:42). reaper LABELS={sonarr,sonarr-imported}, scans torrent state only.
```

</details>

### M9. HA Core 1 monthly release behind; HAOS two major versions behind (16.3 vs 18.1)

**Host:** ha (192.168.10.50) · **Component:** core/OS version · **Auditor:** host:ha


Core 2026.6.4 vs stable 2026.7.2 (one monthly release + patch behind). More significant: Home Assistant OS installed 16.3 vs latest 18.1 — two major OS releases behind. Matter Server add-on 9.0.3 vs 9.0.4. Supervisor is current (2026.07.3). Config state=RUNNING, safe_mode=false, all 18 config entries state=loaded. Updates are surfaced by on update entities but not applied; upgrade is maintenance-window work.


<details><summary>Evidence</summary>

```
GET /api/states (update domain): update.home_assistant_core_update on installed=2026.6.4 latest=2026.7.2 | update.home_assistant_operating_system_update on installed=16.3 latest=18.1 | update.matter_server_update on installed=9.0.3 latest=9.0.4 | update.home_assistant_supervisor_update off 2026.07.3. GET /api/config: version=2026.6.4, state=RUNNING, safe_mode=False, recovery_mode=False
```

</details>

### M10. ha.tabaska.us is a dead path: caddy proxies to HA but HA rejects proxied requests with 400 (trusted_proxies never configured)

**Host:** mini + ha · **Component:** caddy reverse proxy -> HA · **Auditor:** host:ha


The caddy container on mini has an ha.{$DOMAIN} site proxying to {$HA_IP}:8123, but HA's http integration has no use_x_forwarded_for/trusted_proxies for the mini's docker networks, so every request through the proxy gets 400 Bad Request (live-confirmed). The Caddyfile comment says this would be 'configured in run-5' — that step never landed. HA's own system_log shows the matching error from 192.168.10.2. LAN users hitting ha.tabaska.us get a hard 400; direct http://192.168.10.50:8123 works.


<details><summary>Evidence</summary>

```
curl -sk https://ha.tabaska.us/ -> HTTP 400 '400: Bad Request'. /opt/stacks/caddy/caddy/Caddyfile:338-345: '# NOTE: HA will answer 400 "Bad Request" through this proxy until its http.use_x_forwarded_for + trusted_proxies include the mini's Docker networks — configured in run-5. ha.{$DOMAIN} { import local_tls; reverse_proxy {$HA_IP}:8123 }'. WS system_log/list: 2026-07-07 ERROR homeassistant.components.http.forwarded 'A request from a reverse proxy was received from 192.168.10.2, but your HTTP integration is not set-up for reverse proxies'
```

</details>

### M11. All 11 iPhone companion-app sensors unavailable (only device_tracker still updates)

**Host:** ha (192.168.10.50) · **Component:** mobile_app (Btiphone companion) · **Auditor:** host:ha


Every sensor from the mobile_app integration for 'Btiphone' is unavailable (audio_output, bssid, connection_type, geocoded_location, kiosk_brightness, kiosk_volume, last_update_trigger, sim_1, sim_2, ssid, storage) and notify.brandon_iphone is unknown. device_tracker.brandon_iphone=home and person.brandon_tabaska=home still work, so presence is fine, but the sensor telemetry pipeline from the phone is dead (app sensors disabled or app not reporting). This is the single biggest 'unavailable' cluster after excluding cosmetic states.


<details><summary>Evidence</summary>

```
GET /api/states: 11x 'unavailable' sensor.btiphone_* (audio_output, bssid, connection_type, geocoded_location, kiosk_brightness, kiosk_volume, last_update_trigger, sim_1, sim_2, ssid, storage); notify.brandon_iphone=unknown; device_tracker.brandon_iphone=home; person.brandon_tabaska=home
```

</details>

### M12. Seerr request 10 (A Virtual Princess Bride Reunion) has zero Radarr history — never grabbed, stuck PROCESSING 10 days

**Host:** mini + nas · **Component:** seerr -> radarr · **Auditor:** svc:request-layer


Request 10 (movie tmdb 742922, a 2020 charity livestream special) was added to Radarr (movieId 313, monitored=True, released/available) on 2026-07-05 but Radarr history is completely empty — the initial search found no releases and nothing has been found since. It sits in Radarr's missing list, and the seerr request shows PROCESSING with no signal to the user that no release likely exists. Note: request 2 (Supergirl tmdb 1081003) is also PROCESSING but is legitimately status=inCinemas/not-yet-available — not a bug.


<details><summary>Evidence</summary>

```
curl radarr /api/v3/movie?tmdbId=742922 -> monitored=True hasFile=False status=released isAvailable=True
curl radarr /api/v3/history/movie?movieId=313 -> events= 0 []
curl radarr /api/v3/wanted/missing -> movieId 313 in missing: True (total 119)
seerr /api/v1/request: id 10 movie req=APPROVED media=PROCESSING added=2026-07-05
```

</details>

### M13. Phantom 'downloading' request: 3OH!3 self-titled stuck since 07-13; Lidarr album 6037 never grabbed, artist unmonitored, excluded from wanted `known-issue`

**Host:** mini + nas · **Component:** musicseerr -> lidarr · **Auditor:** svc:request-layer


musicseerr request_history has one active request: 3OH!3 - '3OH!3' (lidarr_album_id 6037) status='downloading' since 2026-07-13T20:17, completed_at NULL. In Lidarr the album is monitored=True but artistMonitored=False (monitor_artist=0 on the request), has 0/11 track files, empty history (never grabbed — initial search returned nothing), empty queue, and is NOT in wanted/missing (total=1) — so it will never be auto-retried. musicseerr polls Lidarr queue+history for it every 60 seconds, indefinitely, and will show downloading/0% forever. This is the known phantom-download class (KI-12) with a variant mechanism: album IS monitored, but zero grabs + unmonitored artist = permanently stuck. The other 13 musicseerr requests all imported successfully. queue.db pending_jobs/dead_letters are both empty.


<details><summary>Evidence</summary>

```
ssh mini sqlite3 library.db request_history -> {'artist_name':'3OH!3','album_title':'3OH!3','status':'downloading','lidarr_album_id':6037,'monitor_artist':0,'requested_at':'2026-07-13T20:17','completed_at':None}; 13 others status=imported
curl lidarr /api/v1/album/6037 -> monitored=True artistMonitored=False trackFileCount=0/11 sizeOnDisk=0
curl lidarr /api/v1/history?albumId=6037 -> (empty); /api/v1/queue total: 0; wanted/missing total: 1, 6037 not present
docker logs musicseerr -> GET /api/v1/history?albumId=6037... every 60s (continuous since 07-13)
```

</details>

### M14. YouTube bot-check failures on 2026-07-14 while pinchflat is NOT wired to the bgutil POT provider (provider idle since 07-09)

**Host:** mini · **Component:** pinchflat + bgutil-pot · **Auditor:** svc:media-aux


7 pending media items all failed on 2026-07-14 (15:10-17:19) with 'Sign in to confirm you're not a bot' — exactly the failure class the bgutil-pot container exists to solve. But pinchflat's image (misleadingly named pinchflat-bgutil:local) does not install the bgutil plugin (Dockerfile only adds nightly yt-dlp + /etc/yt-dlp.conf with player_client=default,tv,web_safari; the conf comment says 'add the plugin + base_url arg then' as a future step). metube IS wired (pip install bgutil-ytdlp-pot-provider + YTDL_OPTIONS base_url http://bgutil-pot:4416). bgutil-pot itself is healthy (/ping OK, uptime 5.8d) but has generated zero POTs since its 2026-07-09 20:29 start. Last successful pinchflat download was 2026-07-13 21:12; the 7 bot-checked items remain undownloaded. No bot-check errors in today's (07-15) log — retries backed off to ~07-18.


<details><summary>Evidence</summary>

```
ssh mini 'grep -c "Sign in to confirm" /opt/stacks/pinchflat/config/logs/pinchflat.log.0' -> 28 (log rotated 07-15 00:23)
ERROR: [youtube] wb6vLZSeHt8: Sign in to confirm you're not a bot. Use --cookies-from-browser...
sqlite3 pinchflat.db "select id, media_filepath is not null, datetime(updated_at) from media_items where last_error like '%Sign in to confirm%'" -> 409|0, 702|0, 895|0, 915|0, 939|0, 1008|0, 1333|0 (all 2026-07-14, none downloaded)
cat /opt/stacks/pinchflat/Dockerfile -> FROM ghcr.io/kieraneglin/pinchflat:latest; ADD yt-dlp nightly; COPY yt-dlp.conf  (no bgutil plugin install)
cat /opt/stacks/pinchflat/yt-dlp.conf -> only: --extractor-args "youtube:player_client=default,tv,web_safari"
docker logs -t --tail 12 bgutil-pot -> last 'Generating POT' 2026-07-08T14:31; container StartedAt=2026-07-09T20:29:59, RestartCount=0
curl http://172.25.0.26:4416/ping -> {"server_uptime":503915.09,"version":"1.3.1"}
```

</details>

### M15. Nightly DB backup silently disabled: ND_BACKUP_SCHEDULE set but no backup path configured

**Host:** mini · **Component:** navidrome · **Auditor:** svc:media-aux


Container env has ND_BACKUP_SCHEDULE='0 2 * * *' and ND_BACKUP_COUNT=7 (intent: nightly DB backup, keep 7), but Navidrome logs 'Periodic backup is DISABLED' at startup because ND_BACKUP_PATH is not set and compose mounts no backup volume. The configured backup never runs — silent failure of an intended protection.


<details><summary>Evidence</summary>

```
ssh mini 'docker inspect navidrome --format ...Env' -> ND_BACKUP_SCHEDULE=0 2 * * *  ND_BACKUP_COUNT=7  (no ND_BACKUP_PATH)
docker logs navidrome -> time=2026-07-13T19:17:19Z level=info msg="Periodic backup is DISABLED"
/opt/stacks/navidrome/compose.yaml volumes -> only ./data:/data and $MUSIC_FOLDER:/music:ro (no backup mount)
```

</details>

### M16. Kometa daily run completes but MDBList list fetches fail 401 every run — 2 playlist builders broken

**Host:** mini · **Component:** kometa · **Auditor:** svc:media-aux


Last scheduled run (KOMETA_TIME=05:00) finished OK today: Start 05:00:22, Finished 05:01:03, Run Time 0:00:41. But the Error Summary shows 'MDBList Error: Could not fetch list items: 401 Authentication required' x2 — the mdblist apikey is blank while playlist/collection templates use mdblist lists, so those playlists silently never update. MDBList now requires an API key; this fails on every daily run.


<details><summary>Evidence</summary>

```
tail /opt/stacks/kometa/config/logs/meta.log:
[2026-07-15 05:01:03] | 2 | MDBList Error: Could not fetch list items: MDBList Error: 401 - {"error":"Authentication required..."}
[2026-07-15 05:01:03] | 1 | Config Error: mdblist sub-attribute apikey is blank
[2026-07-15 05:01:03] | Finished 05:00 Run ... Start Time: 05:00:22 2026-07-15  Finished: 05:01:03 2026-07-15  Run Time: 0:00:41
docker inspect kometa -> KOMETA_TIME=05:00 KOMETA_RUN=False
```

</details>

### M17. Homepage Maintainerr tile points at a nonexistent container and a nonexistent vhost (202 widget errors in 96h)

**Host:** mini · **Component:** homepage · **Auditor:** svc:infra-mini


services.yaml (modified today 2026-07-15 13:46 UTC) still contains a Maintainerr tile with siteMonitor http://maintainerr:6246 and href https://maintainerr.tabaska.us. No maintainerr container exists on mini (docker ps -a: none; /opt/stacks/maintainerr contains only a data dir), and maintainerr.tabaska.us has no Caddyfile vhost, so both the monitor and the link are dead. 202 'getaddrinfo EAI_AGAIN maintainerr' errors in the last 96h, recurring whenever the dashboard is viewed. A separate dead widget (http://192.168.10.4:9010, 28 ECONNREFUSED errors, last 2026-07-15T01:19Z) was removed in today's 13:46 config edit and no longer appears in services.yaml.


<details><summary>Evidence</summary>

```
$ docker logs homepage --since 96h | grep -oE ... | sort | uniq -c -> '202 getaddrinfo EAI_AGAIN maintainerr / 202 Error calling http://maintainerr:6246/... / 28 ECONNREFUSED 192.168.10.4:9010'
$ grep -n maintainerr services.yaml -> lines 102-105 (still present)
$ docker ps -a | grep -i maintainerr -> no container; Caddyfile has no maintainerr vhost
```

</details>

### M18. RomM library is completely empty — 0 ROMs in DB, NAS games share contains zero files; every scan finds nothing

**Host:** mini · **Component:** romm · **Auditor:** svc:infra-mini


RomM itself is healthy (login works, IGDB/Twitch token fetch succeeds, MariaDB up), but the library is an empty shell: the roms table has 0 rows, and the CIFS-mounted NAS share //192.168.10.4/games contains 37 platform directories that are ALL empty (0 files each; the only file on the whole share is #recycle/desktop.ini). The 2026-07-14 21:19 scan logged 'No roms found, verify that the folder structure is correct' + 'No firmware found' for every platform. Either the library was never populated (retro-02 shipped as a shell) or the content was removed — either way the service is green-but-empty. No IGDB auth failures and no hard errors in 96h of logs.


<details><summary>Evidence</summary>

```
$ docker exec romm-db mariadb -u root -p*** romm -e 'select count(*) from roms' -> 0
$ docker exec romm sh -c 'for d in /romm/library/roms/*; do ...' -> all 37 platform dirs: 0 entries
$ find /mnt/share/Games -maxdepth 4 -type f | wc -l -> 1 (#recycle/desktop.ini)
$ docker logs romm: '[scan][2026-07-14 21:19:23] No roms found, verify that the folder structure is correct' (x37 platforms); '[igdb_handler] Twitch token fetched!'
```

</details>

### M19. Verification LLM auto-triage broken since ai-01 Ollama demotion: /etc/verification/env pins retired endpoint+model, every triage 404s

**Host:** mini · **Component:** verification / llm_triage · **Auditor:** svc:monitoring-stack


The daily verification sweep's LLM triage layer fails on every run. /etc/verification/env still pins LLM_BASE_URL=http://cachyos.tailb31641.ts.net:11434/v1 and LLM_MODEL=qwen3-coder:30b; on 2026-07-15 Ollama :11434 was demoted to a 3-small-model shim (big models moved behind llama-swap :9292). The shim answers /v1/models 200 but a qwen3-coder:30b completion returns 404, so triage-2026-07-15.md records 'triage failed — model did not return valid JSON / HTTP Error 404' with confidence 0.0 and escalate:true for BOTH failed checks. /opt/verification/bin/llm-triage.sh was already updated (defaults to :9292) but the EnvironmentFile override wins. Checks and ntfy alerting still work; only auto-diagnosis is dead.


<details><summary>Evidence</summary>

```
ssh mini 'grep -E "LLM|MODEL" /etc/verification/env' -> LLM_BASE_URL=http://cachyos.tailb31641.ts.net:11434/v1, LLM_MODEL=qwen3-coder:30b. curl -w on 11434: 'shim /v1/models on 11434: 200' then POST /v1/chat/completions model=qwen3-coder:30b -> 'completion: 404'. /var/lib/verification/triage-2026-07-15.md header: 'model `qwen3-coder:30b` @ http://cachyos.tailb31641.ts.net:11434/v1' with both checks: '"likely_cause": "LLM request failed (attempt 2): HTTP Error 404: Not Found"'. llm-triage.sh:17 default is :9292 (overridden by env file).
```

</details>

### M20. restic-snapshot-fresh-rig is a FALSE POSITIVE: backup succeeded today at 01:40 EDT, but the 06:50 rig reboot wiped the systemd success record and the marker file is only updated by the checker, not the backup unit

**Host:** rig · **Component:** verification / restic-latest-age · **Auditor:** svc:monitoring-stack


Today's main sweep (14:16 UTC) reports restic-snapshot-fresh-rig FAIL 'STALE age_hours=36 (marker)' and ntfy alerted it at 10:16 EDT as a NEW failure. But journalctl proves restic-backup.service on rig completed successfully at 01:40:59 EDT today (12/12 snapshots checked, 'no errors were found', 'All done'), and healthchecks restic-backup-rig got its success ping at 05:40:59Z. The rig rebooted at 06:50:56 EDT (maintenance window), which cleared ExecMainExitTimestamp (now empty), so /usr/local/bin/restic-latest-age fell back to its persisted marker /var/lib/restic-mon/last-success — last touched 2026-07-13 21:44 EDT, because the marker is only refreshed when the CHECKER runs while systemd still holds the record. Design gap: any reboot between the nightly backup and the next sweep loses the success signal and raises a false STALE. Fix direction (not applied): touch the marker from restic-backup.service itself (ExecStartPost).


<details><summary>Evidence</summary>

```
ssh rig 'sudo /usr/local/bin/restic-latest-age' -> 'STALE age_hours=38 (marker)'. ssh rig 'uptime -s' -> 2026-07-15 06:50:56. systemctl show restic-backup.service -> Result=success, ExecMainStatus=0, ExecMainExitTimestamp= (empty). stat marker -> 2026-07-13 21:44:38 -0400. journalctl -u restic-backup.service --since '2026-07-15 00:00': 'Jul 15 01:40:58 ... [0:01] 100.00% 12 / 12 snapshots / no errors were found / Jul 15 01:40:59 ... All done. / systemd[1]: Finished restic backup to Backblaze B2.' Healthchecks restic-backup-rig last_ping 2026-07-15T05:40:59Z status up.
```

</details>

### M21. New 'NAS Whisparr' monitor (id 56) has no notification channel attached — it would go down silently

**Host:** mini · **Component:** uptime-kuma · **Auditor:** svc:monitoring-stack


bootstrap-nas-monitors.sh (run 2026-07-15 00:54, inserts monitors directly via SQL) added monitor 56 'NAS Whisparr' without a monitor_notification row. 53 monitors are active but only 52 notification links exist; the ntfy default channel's applyExisting only covered monitors existing when it was saved. All other 52 active monitors are linked to the single 'ntfy → homelab-alerts' channel. Whisparr is currently up (200 OK), but a future outage would produce no ntfy alert.


<details><summary>Evidence</summary>

```
docker exec uptime-kuma mariadb --socket=/app/data/run/mariadb.sock -D kuma -e 'SELECT COUNT(*) FROM monitor_notification;' -> 52; 'SELECT m.id FROM monitor m LEFT JOIN monitor_notification mn ON mn.monitor_id=m.id WHERE m.active=1 AND mn.id IS NULL;' -> 56. Monitor 56 = 'NAS Whisparr', first heartbeat 2026-07-15 00:54:45 (200 - OK), matching /opt/stacks/uptime-kuma/bootstrap-nas-monitors.sh mtime Jul 15 00:54.
```

</details>

### M22. Real wiki drift on main: 2 generated script-doc pages are stale vs regeneration — keeps the daily sweep red

**Host:** repo (local, main) · **Component:** wiki / verification wiki-drift · **Auditor:** svc:monitoring-stack


The wiki-drift check (warn) fails in today's sweep: committed generated pages are stale vs a fresh regeneration. Reproduced from a clean clone of the local repo (HEAD 3b87b1f): foss-setup/wiki/docs/reference/scripts/docs/index.md and foss-setup/wiki/docs/reference/scripts/docs/publish-deploy-sh.md drift — consistent with commit b0d8c83 (glue-08 repointed publish-deploy) changing the script without regenerating its doc page in the same commit. Until regenerated+committed, verification fails daily and alerts on ntfy (alert fatigue).


<details><summary>Evidence</summary>

```
Local: git clone /Users/brandontabaska/Documents/Home -> bash foss-setup/scripts/wiki/wiki-drift-check.sh -> 'WIKI DRIFT: committed generated pages are stale vs a fresh regeneration. / M foss-setup/wiki/docs/reference/scripts/docs/index.md / M foss-setup/wiki/docs/reference/scripts/docs/publish-deploy-sh.md'. mini /var/lib/verification/last-summary.md: '| wiki-drift | warn | wiki-05 | WIKI DRIFT: ...stale vs a fresh regeneration.' ntfy msg 2026-07-15T10:16:25 'Verification: 2 NEW failure(s) ... wiki-drift'.
```

</details>

### M23. Post-Import Category (queue-clog fix) not applied to readarr and whisparr Deluge clients

**Host:** nas (192.168.10.4) · **Component:** readarr + whisparr / Deluge download client · **Auditor:** svc:arr-stack


The known *arr queue-clog fix is setting a Deluge Post-Import Category so seeding items leave the arr's tracked category after import. Sonarr/radarr/lidarr have it (sonarr-imported/radarr-imported/lidarr-imported) but readarr and whisparr have importedCategory=None. Queues are empty right now so nothing is stuck, but any readarr/whisparr grab that keeps seeding will re-create the queue-clog class the fix was deployed for.


<details><summary>Evidence</summary>

```
curl http://192.168.10.4:{8787,6969}/api/{v1,v3}/downloadclient -H X-Api-Key:...
readarr: 2 Deluge Deluge | enable: True | host: 185.162.184.38 : 5945 | cat: readarr | postImportCat: None
whisparr: 1 Deluge Deluge | enable: True | host: 185.162.184.38 : 5945 | cat: tv-whisparr | postImportCat: None
(vs sonarr: cat: sonarr | postImportCat: sonarr-imported; radarr: radarr-imported; lidarr: lidarr-imported)
```

</details>

### M24. Soularr failed import parked since 2026-07-10, re-skipped every 5 minutes indefinitely

**Host:** nas · **Component:** soularr · **Auditor:** svc:nas-apps


Soularr is live (5-min cycle via SCRIPT_INTERVAL=300) but 'Eminem - The Marshall Mathers LP' (Lidarr album 5030) has sat in failed_imports.json since 2026-07-10T01:08, with files parked at /seedbox/slskd/failed_imports/Eminem - The Marshall Mathers LP (2000) on the seedbox. Every cycle logs 'Skipping failed import album' — it will never retry or clean up without manual action (fix/remove in Lidarr or clear failed_imports.json), and the download wastes seedbox disk. This resembles but is distinct from the known MusicSeerr monitored=False phantom class.


<details><summary>Evidence</summary>

```
ssh nas cat /volume1/docker/soularr/failed_imports.json -> {"5030":{"artist":"Eminem","title":"The Marshall Mathers LP","failed_at":"2026-07-10T01:08:12","folder_path":"/seedbox/slskd/failed_imports/Eminem - The Marshall Mathers LP (2000)"}}
tail soularr.log -> '[INFO|soularr|L414] 2026-07-15T12:29:11-0400: Skipping failed import album: Eminem - The Marshall Mathers LP (ID: 5030)' (repeats every ~5 min: 11:54, 11:59, 12:04, 12:09, 12:14, 12:19, 12:24, 12:29)
```

</details>

### M25. slskd API driven over plaintext HTTP to a public IP (API key in cleartext); docs claim Tailscale

> **RESOLVED 2026-07-17 (fix-21).** slskd binds 127.0.0.1:5030 (HTTPS 5031 disabled); soularr `host_url` → `http://100.119.134.94:5030` (WireGuard-encrypted; clean cycle verified). Root cause of the doc/intent drift: the NAS Tailscale package lacked TUN mode so outbound tailnet TCP never worked — fixed via `tailscale configure synology` + DSM task 13 (`configs/nas/tailscale/`). Guarded by `seedbox-slskd-e2e` (Connected+LoggedIn over tailnet, green).

**Host:** seedbox · **Component:** slskd / soularr · **Auditor:** svc:nas-apps


Soularr's config.ini points at http://185.162.184.38:5030 — plain HTTP to the seedbox's public IP — so the slskd API key transits the internet unencrypted on every 5-min cycle. slskd binds web to 0.0.0.0:5030 (world-reachable; auth IS enforced — unauthenticated /api/v0/session returns 401) and also listens on 5031 (HTTPS) which is unused. The media-automation compose comment explicitly says soularr 'drives remote slskd on Betty over Tailscale' — documentation/intent drift from the live config. Remediation path exists without new infra: tailnet hostname or https://...:5031.


<details><summary>Evidence</summary>

```
ssh nas cat /volume1/docker/soularr/config.ini -> [Slskd] host_url = http://185.162.184.38:5030
ssh seedbox ss -tln | grep 5030 -> 'LISTEN 0 512 0.0.0.0:5030' and '*:5031'; slskd.yml -> web: port: 5030, ip_address: 0.0.0.0
curl -o /dev/null -w '%{http_code}' http://185.162.184.38:5030/api/v0/session -> 401 (auth enforced); root -> 200
compose comment: 'drives remote slskd on Betty over Tailscale'
```

</details>

### M26. Vault drift: soulseek.* empty while slskd is live, whisparr API key missing, deluge.port stale

> **RESOLVED (fix-23, 2026-07-17):** soulseek.username/password/slskd_web_password backfilled from betty's slskd .env (api_key verified matching live); arr_api_keys.whisparr added from config.xml; deluge.port was already 5945 (fixed by fix-21). Guard: vault-lint.py now gates publish-deploy.sh.

**Host:** nas · **Component:** secrets vault · **Auditor:** svc:nas-apps


The 'ALL credentials live in .handoff-secrets.yaml' mandate is broken in three places found this pass: (1) soulseek.username/password/slskd_web_password/slskd_api_key are all EMPTY strings, yet slskd is running on the seedbox and soularr holds a working API key in /volume1/docker/soularr/config.ini (mode 600) — the service is NOT dead, the vault is just unpopulated; (2) arr_api_keys has no whisparr entry (key only recoverable from /volume1/docker/whisparr/config/config.xml); (3) deluge.port says 58846 but nothing listens there on betty — the live Deluge daemon port is 5945 (matches media-automation compose comments).


<details><summary>Evidence</summary>

```
vault: soulseek: {username: '', password: '', slskd_web_password: '', slskd_api_key: ''}; deluge: {host: betty, port: 58846}; arr_api_keys has sonarr/radarr/lidarr/readarr/prowlarr only
ssh nas ls -l /volume1/docker/soularr/config.ini -> -rw------- (contains live [Slskd] api_key; soularr.log active 12:29 today)
ssh seedbox ss -tln | grep -E ':5030|:58846|:5945' -> 5030, 5031, 5945, 50300 listening; 58846 ABSENT
ssh nas grep '<ApiKey>' /volume1/docker/whisparr/config/config.xml -> ffa708068d354043be79329b3526aa0e
```

</details>

### M27. Unpackerr has no [[whisparr]] block — whisparr archives will never be extracted

**Host:** nas · **Component:** unpackerr / whisparr · **Auditor:** svc:nas-apps


unpackerr.conf covers sonarr, radarr, lidarr, readarr but contains zero whisparr entries, even though whisparr (deployed 07-14) is download-touching, mounts the same /seedbox path, and uses the same Deluge client. Rar'd scene releases grabbed by whisparr will sit unextracted and stall as stuck imports — exactly the failure class unpackerr exists to prevent (and the class that already bit this stack on 2026-07-10 per the compose's own healthcheck comment). Whisparr's queue is empty today so nothing is stuck yet.


<details><summary>Evidence</summary>

```
ssh nas grep -c whisparr /volume1/docker/media-automation/unpackerr/unpackerr.conf -> 0
conf blocks present: [[sonarr]] [[radarr]] [[lidarr]] [[readarr]] only
compose: 'Whisparr v2 ... DOWNLOAD-TOUCHING -> /seedbox' with *seedbox-mount
curl 'http://192.168.10.4:6969/api/v3/queue?apikey=...' -> totalRecords: 0 (nothing stuck yet)
```

</details>

### M28. AdGuard-NAS healthy and genuinely used (52k queries/24h) but all client attribution lost to docker bridge NAT

**Host:** nas · **Component:** adguard-nas · **Auditor:** svc:nas-apps


adguardhome-nas v0.107.77 is up, protection enabled, upstream Quad9 DoH (avg 21ms), 969/52,389 queries blocked in 24h, and the *.tabaska.us -> 192.168.10.2 rewrite mirror plus minecraft split-horizon rewrites are present — so it IS serving real traffic as secondary DNS (fresh queries observed at 16:33Z). However 52,387 of 52,389 queries are attributed to 172.23.0.1 (the docker bridge gateway) because port 53 is published from a bridge network: real client IPs are lost, making per-client stats, client-specific rules, and querylog forensics impossible. Host networking or IPvlan would fix attribution. Minor doc drift: compose header says 'upstream tls://1.1.1.1 tls://9.9.9.9' but live upstream is https://dns10.quad9.net/dns-query.


<details><summary>Evidence</summary>

```
curl -u admin:... http://192.168.10.4:3000/control/stats -> num_dns_queries: 52389, top_clients: [{'172.23.0.1': 52387}, {'127.0.0.1': 2}]; blocked: 969; top_upstreams: {'https://dns10.quad9.net:443/dns-query': 27418} avg 0.021s
/control/status -> {"version":"v0.107.77","protection_enabled":true,"running":true,"dns_addresses":["127.0.0.1","172.23.0.2"]}
/control/rewrite/list -> [{"domain":"*.tabaska.us","answer":"192.168.10.2","enabled":true}, ...]
querylog newest: 2026-07-15T16:33:56Z teslafleet.akadns.net NOERROR (live traffic now)
```

</details>

### M29. 12G of frozen AMP backup zips dominate /opt game data and are shipped off-site by restic

**Host:** rig · **Component:** AMP Backups dir / restic repo bloat · **Auditor:** svc:gaming


MinecraftCross01 is 13G, of which 12G is the frozen Backups dir (28 x ~458MB hourly zips of a 445M world — the world itself is only 445M). Because rig restic BACKUP_PATHS includes the whole instance dir, these 28 compressed (poorly-deduplicating) zips are carried in the B2 restic repo, inflating it by roughly 12G for restore points that are all from Jul 9-10. Full game-data footprint under /opt: /opt/stacks/amp 14G (MinecraftCross01 13G [Backups 12G, Minecraft 445M], Main 177M, .ampdata/Versions 494M, java 190M) + /opt/stacks/palworld 5.4G (Pal install 4.9G incl. 69M Saved, backups 228M). Not covered by restic and not needed (re-downloadable): palworld Steam install ~4.8G, /opt/llm 212G models.


<details><summary>Evidence</summary>

```
ssh rig 'du -sh .../instances/MinecraftCross01/* | sort -rh | head -3'
12G  .../MinecraftCross01/Backups
445M .../MinecraftCross01/Minecraft
73M  .../MinecraftCross01/AMP_Linux_x86_64

ssh rig 'du -sh /opt/stacks/*'
14G /opt/stacks/amp
5.4G /opt/stacks/palworld

sudo grep BACKUP_PATHS /etc/restic/env:
BACKUP_PATHS="/etc /home/btabaska /opt/stacks/palworld/game/Pal/Saved /opt/stacks/palworld/game/backups /opt/stacks/amp/config/.ampdata/instances/MinecraftCross01"
```

</details>

### M30. playit currently connected (3 tunnels, verified) but UDP register errors recur ~daily across sessions — the known UDP-claim gotcha is still live `known-issue`

**Host:** rig · **Component:** playit agent (playit container) · **Auditor:** svc:gaming


Current session (daemon start 2026-07-15T10:51Z after host reboot): 'playit connected; tunnels loaded tunnel_count=3 pending=0 disabled=0 account_status=verified', and TCP claims for minecraft.tabaska.us are actively served (external probe connects every ~10 min from 162.0.177.18, latest 21:05Z). No UDP errors in the current session. However the full log shows 'ERROR ... got unexpected response from register request other=...UdpChannelDetails' on 07-10, 07-11 (x2), 07-13 (x2), 07-14, and 07-15 06:25 — i.e. the UDP-claim failure class recurs roughly daily and historically needed an agent restart; the 10:51 reboot cleared today's. Deployed SECRET_KEY matches vault playit_gg.secret_key (whether that key is the read-only one is a server-side property, not verifiable from the agent). Cosmetic: startup always logs an IPv6 'Network unreachable' ping error before falling back to IPv4, and on 07-09 account_status flapped email_not_verified/verified (stable 'verified' since).


<details><summary>Evidence</summary>

```
ssh rig 'docker logs playit | grep -aiE udp' →
2026-07-10T17:24 / 07-11T02:09 / 07-11T16:57 / 07-13T20:31 / 07-13T21:45 / 07-14T20:38 / 07-15T06:25 —
ERROR playit_agent_core::agent_control::connected_control: got unexpected response from register request other=Response(...UdpChannelDetails(...

docker logs --since 11h playit | grep account_status →
2026-07-15T10:51:20 INFO playitd::daemon: playit connected; tunnels loaded agent_id=9f821bee... tunnel_count=3 pending_tunnel_count=0 disabled_tunnel_count=0 account_status="verified"

docker inspect playit env: SECRET_KEY=83e2263969d3ced334c1f28e09a0c527dd73f49dfdcf75018c9f2cd4479a9817 (matches vault playit_gg.secret_key)
```

</details>

### M31. Two ISO 'imports' (81GB total) are green in Radarr but invisible/unplayable in Plex

**Host:** nas · **Component:** radarr + plex · **Auditor:** flow:movies-tv


Bodies Bodies Bodies (BODIES_BODIES_BODIES.iso, 62GB) and Scooby-Doo! WrestleMania Mystery (o0os-scoobywrestlemystery.iso, 18.9GB) have hasFile=True in Radarr but Plex does not index ISO files — both titles return 0 hits in Plex. Same green-but-not-watchable class as the sample imports, plus 81GB of effectively dead disk on /volume2.


<details><summary>Evidence</summary>

```
radarr: Bodies Bodies Bodies | size_MB: 62065.7 | BODIES_BODIES_BODIES.iso (dateAdded 2026-06-28)
Scooby-Doo! WrestleMania Mystery | size_MB: 18933.1 | o0os-scoobywrestlemystery.iso
Plex /library/sections/1/all?title=Bodies Bodies Bodies -> 0 hits (tmdb 520023 and 258893 absent from guid set)
```

</details>

### M32. 11 Plex movies have no external-ID match, including two fresh pipeline imports (Spider-Man: Homecoming, The Iron Giant, both imported 2026-07-14)

**Host:** nas · **Component:** plex (Movies agent matching) · **Auditor:** flow:movies-tv


Plex Movies has 410 items, 396 with tmdb guids. 11 items carry no Guid at all: fresh imports 'Spider Man Homecoming' (2017, 13.7GB proper file, addedAt 07-14) and 'The Iron Giant' (1999, addedAt 07-14) plus bulk-scan junk-titled items ('01 THE CURSE OF THE BLACK PEARL' etc x4 Pirates, 'LA Confidential {1997}', 'Fast and Furious 6', 'The Happy Time Murders', ' Playnow the Producers', 'Star Trek10 2002 Nemesis'). They are playable (Parts exist) but display with mangled titles/no metadata, and are invisible to guid-based checks and seerr availability sync. Notably Alien (imported 07-15) matched fine, so matching currently works — the two 07-14 failures coincide with the analysis-storm window.


<details><summary>Evidence</summary>

```
Plex /library/sections/1/all?includeGuids=1 -> movies=410, with_tmdb_guid=396; items without Guid (11):
('Spider Man Homecoming', '2017', addedAt 1784043630=07-14), ('The Iron Giant','1999', 1784045603=07-14),
('01 THE CURSE OF THE BLACK PEARL', None), ('LA Confidential {1997}', None), ('Star Trek10 2002 Nemesis', None) ...
radarr tmdb 315635 file verified on disk: 13723924328 bytes Jul 14 08:23
```

</details>

### M33. 4 more Sonarr series with files are missing or mismatched in Plex (Over the Garden Wall absent; Scooby-Doo Show wrong-series; Househusband ID-mismatch + 3 eps short; Delicious in Dungeon unmatched)

**Host:** nas · **Component:** sonarr + plex (TV matching) · **Auditor:** flow:movies-tv


(1) Over the Garden Wall: 10 files/1.3GB in per-part release folders ('Over.The.Garden.Wall.Part01...' 2021), Plex title search 0 hits — whole miniseries green in Sonarr but unwatchable. (2) The Scooby-Doo Show (tvdb 73817, 25 files at /tv/Scooby Doo): the files are actually 'Scooby-Doo, Where Are You!' episodes ('01 What A Night For A Knight...'); Plex has no 'The Scooby-Doo Show' — Sonarr is tracking the wrong series against these files. (3) The Way of the Househusband: Sonarr tvdb 386049 with 8 files, Plex matched tvdb 391005 with only 5 leaves. (4) Delicious in Dungeon: all 24 eps present and playable in Plex but the show is unmatched (guid local://51799, no external ids) — invisible to id-based checks and request-layer availability.


<details><summary>Evidence</summary>

```
sonarr series with files not in Plex tvdb set: Gossip Girl(80547,120), Over the Garden Wall(281643,10), The Scooby-Doo Show(73817,25), Way of the Househusband(386049,8), Delicious in Dungeon(423257,24)
ssh nas ls '/volume3/tv/Scooby Doo/' -> '01 What A Night For A Knight [cedar].avi' ... (=Where Are You! S1)
Plex: 'Over the Garden Wall' 0 hits; Househusband guids ['tvdb://391005'] leaf 5; Delicious in Dungeon guid local://51799 guids [] leaf 24
```

</details>

### M34. The Marshall Mathers LP is incomplete: 17/18 tracks on disk, track 1 'Public Service Announcement 2000' missing despite 18 imports logged 2026-07-10

**Host:** nas · **Component:** lidarr / plex+navidrome library · **Auditor:** flow:music


Lidarr album 5030 (Eminem - The Marshall Mathers LP) shows trackFileCount 17/18 and is the sole entry in wanted/missing; the missing track is #1 'Public Service Announcement 2000'. Lidarr history recorded 18 trackFileImported events for this album on 2026-07-10T05:00Z, so one imported file has since disappeared (or was displaced by an upgrade) — the NAS folder holds only 17 files. Album+artist are monitored so Lidarr will keep auto-searching, but until then Plex/Navidrome serve an incomplete album silently. Worth a manual AlbumSearch or import check (log-only, not performed).


<details><summary>Evidence</summary>

```
curl /api/v1/wanted/missing -> total 1: 5030 Eminem - The Marshall Mathers LP albumMon:True artistMon:True. curl /api/v1/album/5030 -> files: 17/18. curl /api/v1/track?albumId=5030 -> missing track: 1 Public Service Announcement 2000. ssh nas 'ls /volume1/music/Eminem/The Marshall Mathers LP (2000) | wc -l' -> 17. History 2026-07-10T05:00:33Z showed 18 tracks imported for 5030.
```

</details>

### M35. Kobo store passthrough is live-ENABLED (config_kobo_proxy=1), contradicting the documented intentional disable of 2026-07-09

**Host:** nas · **Component:** calibre-web-automated (Kobo store passthrough) · **Auditor:** flow:books


Known issue 9 and the secrets vault note say store passthrough was intentionally DISABLED 2026-07-09 by setting config_kobo_proxy=0 in app.db, because the real-Kobo-store relay stalled the 2nd device's sync. A WAL-aware read-only query of the live app.db shows config_kobo_proxy=1 (single settings row), i.e. passthrough is back ON. The app.db.bak-proxyoff backup also reads 1 (consistent with being the pre-change backup), so the live DB was flipped back to 1 at some point after 07-09 — possibly during the 07-09 redeploy to the calibre-web-nextgen v4.0.7 image, or via the UI. Live state now contradicts documentation and re-exposes the kobo2 sync-stall regression risk. Kobo sync itself (config_kobo_sync=1) still works (both endpoints 200). Drift is new, so known_issue=false despite referencing known issue 9.


<details><summary>Evidence</summary>

```
ssh nas sqlite3 "file:/volume1/docker/calibre-web-automated/config/app.db?mode=ro" "select count(*), group_concat(config_kobo_proxy) from settings;" -> 1|1 ; "select config_kobo_sync from settings;" -> 1 ; app.db.bak-proxyoff (immutable=1) -> 1 ; secrets cwa.store_passthrough: 'DISABLED 2026-07-09 (config_kobo_proxy=0 in app.db on NAS)'
```

</details>

### M36. Request statuses only update on UI-triggered POST /api/requests/refresh with swallowed exceptions — 'Rosemary and Rue' still shows 'processing 0%' 2 days after successful import

**Host:** mini · **Component:** libreseerr (app.py status tracking) · **Auditor:** flow:books


libreseerr has no background status refresher: GET /api/requests returns raw stored history, and statuses are only reconciled when the frontend POSTs /api/requests/refresh; that handler also does 'except Exception: pass' (keeps stale status silently on any readarr error). Result: 'Rosemary and Rue' (request 2026-07-13T20:16:40, readarr_book_id 305) was grabbed at 20:17:00 and imported at 20:17:31 — the file exists in readarr (474,601 B) and in the CWA library (61) — yet the stored request still reads status=processing, progress=0 on 2026-07-15. A refresh would fix this one (book 305 has bookFileCount 1), but the dashboard is misleading whenever the UI has not been opened. Could not trigger refresh myself (mutating POST, out of scope for this read-only pass).


<details><summary>Evidence</summary>

```
GET /api/requests -> {'title':'Rosemary and Rue','status':'processing','progress':0,'readarr_book_id':305,'created_at':'2026-07-13T20:16:40'}; readarr history: 2026-07-13T20:17:31Z bookFileImported Rosemary and Rue...; /api/v1/bookfile?bookId=305 -> /readarr-library/Seanan McGuire/Rosemary and Rue/Seanan McGuire - Rosemary and Rue.epub 474601; app.py lines 1099-1147: refresh_requests() is the only status updater, ends 'except Exception as e: pass  # Keep current status on error'
```

</details>

### M37. Confirmed still true: bucket-hyper-backup has NO Object Lock (fileLock disabled) and only SSE-B2 server-side encryption; 72.71 GB / 3695 file versions `known-issue`

**Host:** backblaze-b2 · **Component:** bucket-hyper-backup · **Auditor:** flow:backups


Known issue 6 re-verified live: fileLockConfiguration isFileLockEnabled=false, no lifecycle rules, encryption mode SSE-B2 (server-side only — protects nothing if the B2 account/master key is compromised, and HB client-side encryption remains OFF per known issue; the master key in .handoff-secrets.yaml can delete this bucket's contents outright). Size is sane: 72.71 GB across 3695 file versions for the TabaskaNAS_2.hbk task (photo/homes/docker/docs/backups/@AppConfig shares). bucket-restic size also sane at 6.88 GB / 871 versions (mini ~858 MiB latest + rig ~7 GiB with dedup/compression).


<details><summary>Evidence</summary>

```
b2_list_buckets:
bucket-hyper-backup | type: allPrivate
  fileLock: {"value": {"defaultRetention": {"mode": null, "period": null}, "isFileLockEnabled": false}}
  lifecycle: []
  encryption: {"value": {"algorithm": "AES256", "mode": "SSE-B2"}}
size sweep (b2_list_file_versions paginated):
bucket-restic: 871 file versions, 6.88 GB
bucket-hyper-backup: 3695 file versions, 72.71 GB
```

</details>

### M38. Deployed verification tree has drifted from the repo in BOTH directions — a fresh 'rsync -a --delete' deploy per the README would delete four live-only scripts that active checks and a systemd unit depend on

**Host:** mini · **Component:** /opt/verification vs repo foss-setup/verification · **Auditor:** flow:coverage-tripwire


Deployed-only (NOT in git): bin/mc-status-ping.py and bin/mc-bedrock-ping.py — referenced by the repo's own checks.d/rig.yaml lines 250/264 (playit-java-public, playit-bedrock-public), so the committed checks call scripts that do not exist in the repo; bin/wiki-rag-sync.py — referenced by live /etc/systemd/system/wiki-rag-sync.service (unit itself also not in repo); bin/window-maint-unpackerr-rclone.sh. Repo-only (never staged to /opt/verification/systemd): verification-fast.{service,timer} and verification-quick.{service,timer} (installed in /etc/systemd/system but staging copy stale), plus a stale env.example missing the PLEX/LIDARR var documentation. The documented deploy flow (README: rsync -a --delete foss-setup/verification/ -> /opt/verification) would silently delete the four live-only scripts, breaking both Minecraft public-path checks and the wiki-rag sync unit. Distinct from known issue #7 (backup-role/sops DR gap) — this is the verification suite itself being non-reproducible from git.


<details><summary>Evidence</summary>

```
md5 tree diff repo vs mini:/opt/verification (bin,checks.d,coverage,systemd,skills):
> deployed-only: bin/mc-bedrock-ping.py, bin/mc-status-ping.py, bin/wiki-rag-sync.py, bin/window-maint-unpackerr-rclone.sh
< repo-only: systemd/verification-fast.service, verification-fast.timer, verification-quick.service, verification-quick.timer; env.example md5 mismatch
grep -rn 'mc-status-ping|mc-bedrock-ping' repo checks.d -> rig.yaml:250 'python3 /opt/verification/bin/mc-status-ping.py 69.9.181.17 1105', rig.yaml:264 mc-bedrock-ping.py
ssh mini grep -rl -> /etc/systemd/system/wiki-rag-sync.service references wiki-rag-sync
README.md deploy: 'rsync -a --delete foss-setup/verification/ mini:/tmp/... && sudo rsync -a --delete ... /opt/verification/'
```

</details>

### M39. False-positive STALE in today's daily run: rig backup actually succeeded, but the freshness marker is only written by the checker, so any reboot between backup (01:38 EDT) and the daily sweep (10:15 EDT) fabricates a stale alert

**Host:** rig · **Component:** restic-snapshot-fresh-rig check (/usr/local/bin/restic-latest-age) · **Auditor:** flow:coverage-tripwire


Today's 14:16Z run reported 'STALE age_hours=36 (marker)' for restic-snapshot-fresh-rig, yet the backup demonstrably succeeded: restic-backup.timer LAST=01:40:38 EDT today and the healthchecks dead-man restic-backup-rig pinged up at 05:40:59Z (pings only fire on success). Root cause: restic-latest-age reads systemd's per-boot ExecMainExitTimestamp first, falling back to /var/lib/restic-mon/last-success; but the marker is touched only when restic-latest-age itself runs while the systemd record is still visible. Rig rebooted 06:51 EDT (after the 01:40 backup, before the 10:16 sweep), wiping the systemd record; the marker was last set 2026-07-13 21:44 -> false STALE. The marker should be written by restic-backup.service on success (e.g. ExecStartPost), not by the checker. Self-heals tomorrow if no reboot intervenes, but the false-positive class recurs on every post-backup pre-sweep reboot, and it erodes trust in a backup-freshness signal (ties into known 'monitoring vs reality' theme, but this exact bug is unlogged).


<details><summary>Evidence</summary>

```
last-summary.md: '[FAIL] restic-snapshot-fresh-rig (warn) ... STALE age_hours=36 (marker)'
ssh rig: restic-backup.timer LAST 'Wed 2026-07-15 01:40:38 EDT'; systemctl show restic-backup.service -> ExecMainExitTimestamp= (empty, post-reboot)
ssh rig who -b -> 'system boot 2026-07-15 06:51'; stat /var/lib/restic-mon/last-success -> mtime 2026-07-13 21:44:38 -0400
healthchecks API: 'restic-backup-rig' status=up last_ping=2026-07-15T05:40:59+00:00
restic-latest-age source: marker only updated inside the systemd-record branch ('touch -d @$epoch $MARKER')
```

</details>

### M40. 8 of 71 Hue lights unavailable — 7 continuously since HA start 2026-06-27 (18 days), 1 since 2026-07-14; bridge itself healthy

**Host:** ha (192.168.10.50) · **Component:** hue integration (bridge 192.168.20.100) · **Auditor:** flow:ha-deep


Unavailable: light.kitchen_kitchen_overhead_1/_2, light.kitchen_kitchen_counter_light, light.kitchen_kitchen_counter_2, light.basement_basement_ceiling, light.basement_hue_white_lamp_5, light.upstairs_bathroom_vanity_1 (all since 2026-06-27T22:56Z = HA start) and light.dining_hue_white_lamp_18 (since 2026-07-14T01:15Z). Pattern (whole rooms: kitchen, basement, upstairs bath) suggests bulbs cut at wall switches rather than bridge trouble — the bridge answers directly in 87ms and the other 63 hue lights are live. These 8 are also exported through the HomeKit bridge, where diagnostics show exactly 8 bridged accessories in state 'unavailable' (they appear 'No Response' to Apple clients). The 21 hue scene entities in 'unknown' are normal (never activated since restart). The 2 'is there a bridge alive on 192.168.20.100?' warnings were only on 2026-07-03 during a discovery/config-flow attempt — not current.


<details><summary>Evidence</summary>

```
curl /api/states + registry cross-ref: 8 light.* unavailable, all platform=hue, e.g. light.kitchen_kitchen_overhead_1 last_changed=2026-06-27T22:56:18Z; light.dining_hue_white_lamp_18 last_changed=2026-07-14T01:15:12Z
curl http://192.168.20.100/api/0/config -> {'name':'Hue Bridge','apiversion':'1.78.0','bridgeid':'ECB5FAFFFE99B37D'} http=200 time=0.087s
WS system_log: [WARNING] x2 hue.config_flow 'is there a bridge alive on IP 192.168.20.100 ?' first/last=2026-07-03 only
homekit diagnostics: 8x /data/bridge/<aid>/entity_state/state = unavailable
```

</details>

### M41. HomePod<->hub gap: bridge is running and paired to 2 clients, but an Apple client at 192.168.1.79 was rejected on pair-verify (stale/never-completed pairing) — and it sits on an unexpected subnet `known-issue`

**Host:** ha (192.168.10.50) · **Component:** homekit bridge (HASS Bridge:21064) · **Auditor:** flow:ha-deep


HomeKit bridge status=1 (running), mode=bridge, scoped to lights only, pairing_id 15:4A:C6:85:D1:4B, with TWO paired admin clients (uuids c209ff16..., 557bb22a...) — so pairing has progressed since the 07-13 memory snapshot ('awaiting iPhone pairing'). However on 2026-07-13 a THIRD client, uuid 51d8dbec-a1d5-4ed6-96a3-e2d691fc061c at 192.168.1.79, 'attempted pair verify without being paired first' and was rejected — classic stale-pairing signature (device, likely the HomePod, holds keys from a previous/reset bridge). Note 192.168.1.79 is not on the 192.168.10.x Trusted VLAN or 192.168.20.x — that device lives on a different subnet, which alone can break HomeKit hub residency (mDNS scope). Also the 8 unavailable Hue lights are exported as unresponsive HomeKit accessories. Cannot exercise a live HomePod session via REST; this is the extent verifiable read-only.


<details><summary>Evidence</summary>

```
curl /api/diagnostics/config_entry/01KXDTZPAWXB7P57PDXCN13J7M -> status: 1; pairing_id: 15:4A:C6:85:D1:4B; client_properties: {'c209ff16-0c8e-4b11-bc54-8180a58e7020':{'permissions':1},'557bb22a-7554-4aa0-bffa-2a2ccaa271e1':{'permissions':1}}; options.filter.include_domains=['light']
WS system_log: [ERROR] x1 pyhap.hap_handler 2026-07-13T09:59:54 "HASS Bridge: Client ('192.168.1.79', 55100) with uuid 51d8dbec-... attempted pair verify without being paired first"
```

</details>

### M42. 11 of 18 iPhone companion-app sensors unavailable since 2026-07-07 (kiosk pair since 07-11); core presence still works

**Host:** ha (192.168.10.50) · **Component:** mobile_app integration (Btiphone) · **Auditor:** flow:ha-deep


sensor.btiphone_{bssid,ssid,storage,connection_type,sim_1,sim_2,geocoded_location,last_update_trigger,audio_output} unavailable since 2026-07-07T23:13Z; kiosk_volume/kiosk_brightness since 2026-07-11T23:41Z. device_tracker.brandon_iphone='home', battery_level=85/Charging, app_version=2026.7.0 and location_permission='Authorized Always' still update, so the integration is alive but most telemetry sensors stopped — typical of sensors being disabled in the iOS app or an app update dropping them (notify.brandon_iphone 'unknown' is normal never-used state). No mobile_app errors in the log. Degradation only; nothing consumes these sensors today (there are zero automations).


<details><summary>Evidence</summary>

```
curl /api/states: sensor.btiphone_bssid=unavailable (last_changed=2026-07-07T23:13:52Z) ... 9 sensors same timestamp; sensor.btiphone_kiosk_volume=unavailable (2026-07-11T23:41:19Z); device_tracker.brandon_iphone=home; sensor.btiphone_battery_level=85
entity registry: mobile_app has 18 entities, 11 unavailable + 1 unknown
```

</details>

### M43. 15 GB stale migration snapshot with live secrets sits in iCloud-synced ~/Documents

> **RESOLVED (fix-23, 2026-07-17):** migration-snapshot/ deleted (15 GB, took 15 rm passes against iCloud sync); .gitignore entry removed. iCloud may retain deleted files ~30 days.

**Host:** macbook (local repo) · **Component:** migration-snapshot/ · **Auditor:** repo:junk-deadpaths


migration-snapshot/ (last touched 2026-06-29, git-ignored) is a 15 GB leftover from the server migration. It contains live credentials — Plex Preferences.xml has a PlexOnlineToken, and the .gitignore comment itself says it holds 'Plex tokens, API keys, indexer cookies'. Because the repo lives under iCloud-synced ~/Documents, these plaintext secrets replicate to Apple's cloud. It also contains 3 broken venv symlinks (compose/vpnqbtorrent/env/bin/python*). Migration completed weeks ago; this is stale junk plus a secrets-in-cloud exposure. Path: /Users/brandontabaska/Documents/Home/migration-snapshot


<details><summary>Evidence</summary>

```
du -sh migration-snapshot -> 15G
grep -o 'PlexOnlineToken="[^"]*"' 'migration-snapshot/configs/plex/.../Preferences.xml' -> PlexOnlineToken=REDACTED-PRESENT
.gitignore: '# Local server migration snapshot (contains Plex tokens, API keys, indexer cookies)'
find . -type l ! -exec test -e {} \; -print -> 3 broken symlinks under migration-snapshot/compose/vpnqbtorrent/env/bin/
```

</details>

### M44. Vault forgejo.admin_user/admin_password are empty while Forgejo is live and is the deploy control plane

> **RESOLVED (fix-23, 2026-07-17):** admin password reset via `forgejo admin user change-password` in the container, stored in vault, verified by API basic-auth login (is_admin: true). Guard: vault-lint.py.

**Host:** macbook (local repo) · **Component:** .handoff-secrets.yaml / forgejo · **Auditor:** repo:junk-deadpaths


forgejo: admin_user '' and admin_password '' in the vault, but Forgejo runs on mini (containers forgejo + forgejo_db up, git.tabaska.us via Caddy) with DISABLE_REGISTRATION=true — meaning the only admin credential exists nowhere in the handoff vault. Since Forgejo is the ansible-pull/publish-deploy control plane, losing the operator's ad-hoc credential would lock the fleet's deploy path out of admin recovery via documented secrets.


<details><summary>Evidence</summary>

```
python walk of .handoff-secrets.yaml -> EMPTY: forgejo.admin_user '' / EMPTY: forgejo.admin_password ''
ssh mini docker ps -> forgejo, forgejo_db Up
service-enrichment.yaml: 'DISABLE_REGISTRATION=true ... publish-deploy.sh pushes main ... to the forgejo:home/homelab repo, which every host then ansible-pulls'
```

</details>

### M45. All 4 soulseek vault keys empty while soularr is live on NAS with slskd creds only in its config.ini

> **RESOLVED (fix-23, 2026-07-17):** vault backfilled (see M26); config.ini.bak-wrong-path junk deleted from /volume1/docker/soularr.

**Host:** nas + macbook (vault) · **Component:** .handoff-secrets.yaml / soulseek + soularr · **Auditor:** repo:junk-deadpaths


Vault soulseek.username/password/slskd_web_password/slskd_api_key are all ''. But soularr IS deployed on the NAS (/volume1/docker/soularr with active config.ini, rotating soularr.log) and its config points at a remote slskd at http://185.162.184.38:5030 with a real api_key present in that file — i.e. live credentials exist only on the NAS filesystem, not in the vault that claims to hold all handoff creds. Also junk alongside: config.ini.bak-wrong-path leftover in the same dir.


<details><summary>Evidence</summary>

```
python walk of vault -> EMPTY: soulseek.username/password/slskd_web_password/slskd_api_key (all '')
ssh nas 'ls /volume1/docker/soularr' -> config.ini config.ini.bak-wrong-path failed_imports.json soularr.log*
ssh nas grep config.ini -> host_url = http://lidarr:8686 / api_key = REDACTED(present) / host_url = http://185.162.184.38:5030 / api_key = REDACTED(present)
```

</details>

### M46. Orphan done id nas-00e — closed in progress.json but the task never existed in tasks.json

**Host:** macbook (local repo) · **Component:** tracker: docs/progress.json vs docs/tasks.json · **Auditor:** repo:tracker-wiki


progress.json done contains 'nas-00e' (closed 2026-07-13 roadmap prune as 'NAS music mount at /mnt/nas/music') but tasks.json only defines nas-00a..d — no nas-00e task exists. Result: _meta.completed_count=166 counts a phantom, while generated todo.md correctly says '165/234 done', so the two published done-counts disagree by 1. The id survives only in prose inside another task's steps (tasks.json line 5055). Fix path: either add the nas-00e definition to tasks.json or drop the orphan key and decrement completed_count.


<details><summary>Evidence</summary>

```
python3 cross-check: "done: 166 entries; ids not in tasks.json: ['nas-00e']"; tasks.json has ['nas-00a','nas-00b','nas-00c','nas-00d']; head todo.md -> '**165/234 done**' vs progress.json _meta '"completed_count": 166'
```

</details>

### M47. Committed wiki man-page for publish-deploy.sh is stale — documents the retired subtree-split topology (same-commit rule wiki-05 violated)

**Host:** macbook (local repo) · **Component:** wiki: generated script man-pages · **Auditor:** repo:tracker-wiki


Commit b0d8c83 (2026-07-14) rewrote scripts/docs/publish-deploy.sh for the full-repo home/homelab topology, but wiki/docs/reference/scripts/docs/publish-deploy-sh.md was last regenerated in the older wiki waves (26a43c4/f7f8998). The published page still describes 'git subtree split', the [--force] flag and SPLIT_SHA/FORCE env vars — all removed. reference/scripts/docs/index.md carries the stale one-line description too. Re-running gen-script-pages.py produced a 29-line diff on exactly these 2 files; all other generator outputs were byte-identical. This is precisely the drift class the wiki-05 wiki-drift check on the mini exists to catch — worth confirming whether that check is currently red or being ignored (not probed here; local-repo scope). Files restored via git checkout after the test; repo clean.


<details><summary>Evidence</summary>

```
python3 gen-script-pages.py; git status --porcelain -> 'M .../scripts/docs/index.md' + 'M .../publish-deploy-sh.md'; git diff shows committed page: '> publish foss-setup/ as the deployment repo', 'Usage: ... [--force]', env 'FORCE, ROOT, SPLIT_SHA' vs regenerated 'plain push of main to both remotes', env 'ROOT'. git log: script last touched b0d8c83; md last touched 26a43c4.
```

</details>

### M48. forgejo stack (the ansible-pull control-repo server itself) runs live with NO repo mirror

**Host:** mini · **Component:** forgejo stack vs foss-setup/configs/docker-stack · **Auditor:** repo:live-drift


/opt/stacks/forgejo/docker-compose.yml + .env (keys: FORGEJO_DB_PASSWORD, FORGEJO_DISABLE_REGISTRATION, FORGEJO_DOMAIN, FORGEJO_GID, FORGEJO_REQUIRE_SIGNIN, FORGEJO_ROOT_URL, FORGEJO_SSH_PORT, FORGEJO_UID) drive containers forgejo (codeberg.org/forgejo/forgejo:15.0.1) and forgejo_db (postgres:17-alpine), both Up 6 days — but configs/docker-stack has no forgejo dir at all (neither compose nor .env.example). This is the git server every host's ansible-pull converges FROM; it is the one stack that cannot be rebuilt from the repo. Violates the live-stack-is-source-of-truth mirror mandate and the 100% coverage tripwire. All other 28 live mini stacks' compose files are byte-identical to their repo copies.


<details><summary>Evidence</summary>

```
$ ssh mini 'ls /opt/stacks/forgejo' -> docker-compose.yml, .env
$ diff loop over /opt/stacks/*/compose vs configs/docker-stack: '### forgejo: NO REPO COPY' (all 28 others IDENTICAL)
$ ssh mini docker ps | grep forgejo
forgejo  codeberg.org/forgejo/forgejo:15.0.1  Up 6 days (healthy)
forgejo_db  postgres:17-alpine  Up 6 days (healthy)
$ find configs/docker-stack -iname '*forgejo*' -> (nothing)
```

</details>

### M49. compose-images manifest polluted: junk libreseerr 'digest' comes from a stray .bak compose (it is a local image ID, not a pullable digest), plus 4 phantom hotio images from the trash-guides clone

**Host:** mini · **Component:** hosts/macmini/compose-images.txt + configs/inventory/inventory.md · **Auditor:** repo:live-drift


Of the two libreseerr pins, the REAL one is ghcr.io/zamnzim/libreseerr@sha256:820134e4... — it is the pin in the active /opt/stacks/libreseerr/compose.yaml and matches the running container's Config.Image; the running image's LOCAL ID is c2dbf74a5ab6.... The second manifest entry ...@sha256:c2dbf74a... is the JUNK pin: it comes from /opt/stacks/libreseerr/compose.yaml.bak-preselectionfix and is the image ID mis-written as a digest (docker pull of it would 404 — the image-ID-vs-digest gotcha). Root cause is export-manifests.sh line 78: it greps 'image:' recursively across ALL of /opt/stacks, sweeping in (a) the .bak compose, (b) recyclarr's embedded trash-guides git clone (source of the never-deployed ghcr.io/hotio/bazarr|radarr|sonarr|sabnzbd:latest entries — no such containers exist on mini), and (c) the built wiki under /opt/stacks/wiki/site. inventory.md lines 51-52 duplicate both libreseerr pins. The manifest is otherwise CURRENT (byte-identical to re-running the same grep live today). Also flagged: frigate:0.17.1 is in the manifest with no container and no pulled image — but service-catalog.yaml line 435 explicitly documents 'frigate — NOT DEPLOYED (stack dir staged, no container has ever run)', so that one is documented, not drift. recyclarr appears without a long-running container by design (weekly `docker compose run` cron).


<details><summary>Evidence</summary>

```
$ ssh mini docker inspect libreseerr --format '{{.Image}} {{.Config.Image}}'
sha256:c2dbf74a5ab6... ghcr.io/zamnzim/libreseerr@sha256:820134e44279...
$ ssh mini grep -rlE 'libreseerr@sha256:c2dbf74a' /opt/stacks
/opt/stacks/libreseerr/compose.yaml.bak-preselectionfix
$ ssh mini grep -rlE 'hotio/(bazarr|radarr|sonarr|sabnzbd)' /opt/stacks | head
/opt/stacks/wiki/site/search/search_index.json
/opt/stacks/recyclarr/config/resources/trash-guides/git/official/includes/docker/docker-compose.yml
$ diff hosts/macmini/compose-images.txt <(live re-grep) -> MANIFEST-MATCHES-LIVE-GREP
$ grep -n libreseerr configs/inventory/inventory.md -> lines 51+52 list both digests
$ ssh mini docker images | grep frigate -> (none)
```

</details>

### M50. NAS compose drift: calibre-web-automated repo copy stale (NETWORK_SHARE_MODE) and immich repo copy diverged from live (version-pin guard never deployed)

**Host:** nas · **Component:** configs/nas vs /volume1/docker live compose · **Auditor:** repo:live-drift


Two of six NAS composes differ from repo. (1) calibre-web-automated: live has NETWORK_SHARE_MODE=false (the intentional live setting since the Kobo-sync work), repo still says true — live changed, repo stale, a rebuild-from-repo would re-enable the unwanted mode. (2) immich: repo copy requires the version pin (image: ...:${IMMICH_VERSION:?set IMMICH_VERSION in .env}) while LIVE still uses the floating fallback ${IMMICH_VERSION:-release} on both immich-server and immich-machine-learning — the hardening was committed to the repo but never deployed to the NAS (NAS deploys need operator sudo), so repo and live disagree in the opposite direction. Live server currently reports v2.7.5. media-automation, stash, diun, adguard-nas composes and the beszel-agent compose (mirrored at configs/host/nas/beszel-agent) are byte-identical to live. Could not verify the NAS immich .env sets IMMICH_VERSION (file unreadable to the ssh user).


<details><summary>Evidence</summary>

```
$ diff configs/nas/calibre-web-automated/docker-compose.yml <(ssh nas cat /volume1/docker/calibre-web-automated/docker-compose.yml)
-      - NETWORK_SHARE_MODE=true
+      - NETWORK_SHARE_MODE=false
$ diff configs/nas/immich/docker-compose.yml <(live)
-    image: ghcr.io/immich-app/immich-server:${IMMICH_VERSION:?set IMMICH_VERSION in .env}
+    image: ghcr.io/immich-app/immich-server:${IMMICH_VERSION:-release}
(-/+ same for immich-machine-learning ...-openvino)
$ curl http://192.168.10.4:2283/api/server/version -> {"major":2,"minor":7,"patch":5}
media-automation/stash/diun/adguard-nas/beszel-agent: IDENTICAL
```

</details>

### M51. .env key drift on 6 mini stacks: live-added keys missing from repo examples (rebuild-from-repo would silently drop them)

**Host:** mini · **Component:** stack .env files vs repo .env.example templates · **Auditor:** repo:live-drift


Comparing live .env variable NAMES against repo .env.example templates (values redacted): live-only keys the examples never gained — caddy: ACME_EMAIL, RIG_IP (RIG_IP is load-bearing for rig-facing routes); musicseerr: LIDARR_API_KEY (without it MusicSeerr cannot talk to Lidarr); navidrome: ND_BACKUP_COUNT, ND_BACKUP_SCHEDULE, ND_ENABLEINSIGHTSCOLLECTOR (a rebuild loses DB backups); ntfy: NTFY_UPSTREAM_BASE_URL (loses iOS push relay). Repo-only keys absent live: paperless-ngx example still ships PAPERLESS_ADMIN_PASSWORD (first-run-only, cosmetic); wallabag example has WALLABAG_FROM_EMAIL + WALLABAG_MAILER_DSN that live dropped (live compose no longer references them — example stale). All other stacks' key sets match.


<details><summary>Evidence</summary>

```
key-set comm(1) of live .env vs repo .env.example:
caddy: live-only [ACME_EMAIL RIG_IP]
musicseerr: live-only [LIDARR_API_KEY]
navidrome: live-only [ND_BACKUP_COUNT ND_BACKUP_SCHEDULE ND_ENABLEINSIGHTSCOLLECTOR]
ntfy: live-only [NTFY_UPSTREAM_BASE_URL]
paperless-ngx: repo-only [PAPERLESS_ADMIN_PASSWORD]
wallabag: repo-only [WALLABAG_FROM_EMAIL WALLABAG_MAILER_DSN]
(all remaining stacks: keys match)
```

</details>

### M52. Known issue 7 quantified: ansible backup role is a no-op (its SOPS gate file doesn't exist) and its design contradicts the live restic setup in 6 concrete ways `known-issue`

**Host:** mini+rig · **Component:** configs/ansible/roles/backup vs live restic deployment · **Auditor:** repo:live-drift


The role's first task looks for secrets/restic.sops.env relative to playbook_dir; configs/ansible/secrets/ does not exist in the repo, so every pull run takes the 'Skip backup role — restic secret not seeded yet' branch — the entire live restic setup is hand-deployed, zero ansible coverage. If someone ever seeds the secret, the role would actively REGRESS live: (1) installs distro restic (apt = 0.12 on the mini, the exact version that hard-deleted B2 object locks and broke backups until 0.19.1 was hand-placed in /usr/local/bin); (2) its unit hardcodes ExecStart=/usr/bin/restic while live mini uses /usr/local/bin/restic 0.19.1 via /opt/scripts/restic-backup.sh; (3) env path /etc/restic/backup.env vs live /etc/restic/env; (4) no OnFailure=ntfy-notify@ nor healthchecks drop-in (live has both); (5) no RESTIC_CACHE_DIR (live sets CacheDirectory=restic); (6) timer 02:30/RandomizedDelay 20m vs live 01:30/15m. Backup set also differs from rig reality (role: /home + /opt/stacks + /var/lib/docker/volumes; rig live: /etc + /home only). Mitigating: live units ARE mirrored in the repo outside ansible — scripts/backup/restic-backup.service is byte-identical to the live mini unit. Roles present: backup, base, docker, state, tailscale (+ playbooks audit/patch/reboot, site.yml).


<details><summary>Evidence</summary>

```
$ ls configs/ansible/secrets -> No such file or directory
role main.yml: 'Skip backup role — restic secret not seeded yet ... when: restic_sops_env_file | length == 0'; 'ExecStart=/usr/bin/restic backup --verbose --exclude-caches /home {{ extra_backup_paths }}'; dest: /etc/restic/backup.env; apt/pacman restic
$ ssh mini 'which restic; restic version' -> /usr/local/bin/restic; restic 0.19.1
live unit: ENV_FILE=/etc/restic/env; ExecStart=/opt/scripts/restic-backup.sh; OnFailure=ntfy-notify@%n.service; OnCalendar 01:30
$ diff scripts/backup/restic-backup.service <(ssh mini cat /etc/systemd/system/restic-backup.service) -> MINI-RESTIC-SERVICE-MATCHES-REPO-SCRIPT
```

</details>

### M53. Four live scripts in /opt/verification/bin are not in repo verification/ — the README's rsync --delete deploy would delete them and break checks + a service; quick unit's ping URL exists only as a hand-edit

**Host:** mini · **Component:** verification deploy procedure (/opt/verification vs repo verification/) · **Auditor:** repo:verification-suite


Deployed-but-not-in-verification/: mc-status-ping.py + mc-bedrock-ping.py (repo copies live in scripts/gaming/ — used by playit-java-public / playit-bedrock-public), wiki-rag-sync.py (repo copy scripts/ai/ — ExecStart of wiki-rag-sync.service), window-maint-unpackerr-rclone.sh (repo copy scripts/media/). README's documented deploy is 'rsync -a --delete foss-setup/verification/ ... /opt/verification/', which would remove all four, breaking both Minecraft public-path checks and the RAG sync service. Additionally: (a) repo verification-quick.service carries the literal placeholder HC_QUICK_PING_URL in ExecStartPost (installed unit has the real URL hand-substituted) — installing the repo unit verbatim kills the quick dead-man ping; (b) the daily unit's verification-mini dead-man ping exists only in a drop-in /etc/systemd/system/verification.service.d/healthchecks.conf that is not in repo verification/systemd/ at all (tracked only by etckeeper). All other deployed files (bin/, checks.d/, coverage/, skills/) md5-match the repo.


<details><summary>Evidence</summary>

```
ssh mini 'ls /opt/verification/bin' → mc-bedrock-ping.py, mc-status-ping.py, wiki-rag-sync.py, window-maint-unpackerr-rclone.sh present; find repo verification/ → absent
rig.yaml: cmd: python3 /opt/verification/bin/mc-status-ping.py 69.9.181.17 1105 ...
systemctl cat wiki-rag-sync.service → ExecStart=/usr/bin/python3 /opt/verification/bin/wiki-rag-sync.py
repo systemd/verification-quick.service: ExecStartPost=/usr/bin/curl ... HC_QUICK_PING_URL (literal); installed: .../ping/be8120c5-...
systemctl cat verification.service → drop-in healthchecks.conf with ping e906c083-... (not in repo)
```

</details>

### M54. wiki->OWUI RAG sync failing since 2026-07-16 05:14 UTC (OWUI on rig returns HTTP 500) — homelab-wiki knowledge collection going stale

**Host:** mini · **Component:** wiki-rag-sync.service / OWUI RAG · **Auditor:** repo:verification-suite


wiki-rag-sync.service on mini failed at 05:14 UTC: GET http://rig OWUI /api/v1/knowledge/ → HTTP 500 (downstream of the rig read-only filesystem; OWUI can't write). wiki-rag-state.json last updated Jul 15 11:44 UTC, so the mini-wiki-rag-fresh check (26h window) will start failing at today's 14:16 UTC daily sweep. Currently surfaced only via the hourly systemd-failed-mini docker-fleet check (paged 05:42 UTC).


<details><summary>Evidence</summary>

```
ssh mini journalctl -u wiki-rag-sync.service →
urllib.error.HTTPError: HTTP Error 500: Internal Server Error (GET /api/v1/knowledge/)
Jul 16 05:14:45 macmini systemd[1]: wiki-rag-sync.service: Failed with result 'exit-code'.
results-docker-fleet.json: FAIL systemd-failed-mini | out: wiki-rag-sync.service loaded failed failed
ls /var/lib/verification/wiki-rag-state.json → mtime Jul 15 11:44
```

</details>

### M55. wiki-drift failing since the 2026-07-15 daily sweep — committed generated wiki pages are stale vs a fresh regeneration; unresolved

**Host:** mini · **Component:** wiki-drift check (git-hygiene domain) · **Auditor:** repo:verification-suite


Yesterday's daily run (results.json 2026-07-15T14:16Z) failed wiki-drift: 'WIKI DRIFT: committed generated pages are stale vs a fresh regeneration' — i.e. a source that feeds a generated wiki page changed without regenerating the page in the same commit (wiki-05 same-commit rule). Its LLM triage verdict was also lost to the 404 bug, so no diagnosis was recorded. Still unremediated (next daily run at 14:16 UTC will re-test). Given the tracker/wiki is the declared source of truth, drift here is meaningful, not cosmetic.


<details><summary>Evidence</summary>

```
ssh mini python3 (results.json 2026-07-15T14:16:25Z):
FAIL wiki-drift sev=warn | out: WIKI DRIFT: committed generated pages are stale vs a fresh regeneration.
triage-2026-07-15.md: wiki-drift verdict = 'triage failed ... HTTP Error 404' (escalate: true)
```

</details>

### M56. open-webui serves and reads OK but is write-dead: sqlite data volume sits on the RO root, and its LiteLLM upstream key is broken

**Host:** rig · **Component:** open-webui (:8080 / ai.tabaska.us) · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


OWUI /health=200, ai.tabaska.us=200 via mini caddy (reverse_proxy {$RIG_IP}:3000), and an authorized GET /api/models with the rag-sync key returns 200 — reads work. But its data volume (docker volume docker_open_webui_data -> /var/lib/docker/volumes on the RO root btrfs) and its overlay are both read-only ('touch: Read-only file system' inside the container), so any write — new chat rows, logins/last-active updates, the mini wiki RAG sync (openwebui_rag_sync_api_key), vector/RAG index writes — will fail with sqlite disk-I/O or OS errors. Chats are doubly broken because OWUI's LiteLLM virtual key hits the 503 no_db_connection. Container is 'healthy' because the healthcheck is a read. Write path not actively tested (read-only mandate); no write-error lines in the recent 80 log lines, consistent with no user activity since the remount.


<details><summary>Evidence</summary>

```
ssh rig 'curl http://127.0.0.1:8080/health' -> 200; GET /api/models with Bearer sk-122eb3... -> 200
docker inspect open-webui mounts -> volume /var/lib/docker/volumes/docker_open_webui_data/_data -> /app/backend/data (on RO /)
docker exec open-webui sh -c 'touch /tmp/_p' -> touch: cannot touch '/tmp/_p': Read-only file system
curl https://ai.tabaska.us -> 200; Caddyfile: ai.{$DOMAIN} -> reverse_proxy {$RIG_IP}:3000
docker logs --tail 80 open-webui | grep -iE 'error|read-only|sqlite|fail' -> (no matches)
```

</details>

### M57. All AI-stack monitoring still green during the outage: ai-stack-rig healthcheck pinged 'up' minutes ago while LiteLLM rejects every real client `known-issue`

**Host:** rig + mini · **Component:** monitoring (healthchecks ai-stack-rig, litellm health probes) · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


The ai-stack-rig healthcheck on mini shows status 'up' with a last ping at 2026-07-16T11:50:36Z — hours into the incident — and mini's periodic probes of litellm (/health/liveliness, /v1/models with what must be the master key) return 200 continuously per the litellm access log. Meanwhile every virtual-key client gets 503 and litellm-db is a corpse that docker ps mislabels healthy. Concrete new instance of known issue #15 (liveness-not-correctness): the AI stack's own tripwires cannot see this failure mode. Bonus signal actually caught by monitoring: restic-backup-rig is DOWN (last ping 2026-07-15T05:40:59Z — missed its nightly run, expected since restic cannot write cache/state on an RO root, and the source FS is corrupt).


<details><summary>Evidence</summary>

```
curl http://192.168.10.2:8001/api/v3/checks/ -H 'X-Api-Key: ...' ->
ai-stack-rig | up | last_ping: 2026-07-16T11:50:36+00:00
restic-backup-rig | down | last_ping: 2026-07-15T05:40:59+00:00
docker logs litellm (tail) -> continuous 'GET /health/liveliness 200' + 'GET /v1/models 200' from 192.168.10.2 while ops-key completion returns 503 no_db_connection
```

</details>

### M58. Second user (kaelyn92@icloud.com) was created with full admin rights and has never logged in; both accounts still flagged shouldChangePassword

**Host:** nas · **Component:** immich · **Auditor:** gap:NAS Immich — root-cause the ZERO-assets finding via the readable Postgres dump (not just filesystem emptiness)


The user row for kaelyn92@icloud.com (created 2026-07-14 15:29Z) has isAdmin=t — a family/secondary account holding full Immich admin on an internet-exposed instance (immich.tabaska.us). She has zero sessions and no user_metadata onboarding row, i.e. the account has never been used. Both users also carry shouldChangePassword=t, meaning the operator-set initial passwords were never rotated by the account holders. Low blast radius today (no assets), but it's a privilege misconfig on a public endpoint.


<details><summary>Evidence</summary>

```
COPY public."user" ... FROM stdin; (dump 2026-07-16):
b6be5585-152e-4330-86d2-f52a397ed706  kaelyn92@icloud.com  $2b$10$...  2026-07-14 15:29:43+00  ''  t  t  \N ...
(col 6 isAdmin=t, col 7 shouldChangePassword=t)
user_metadata rows: only 2, both for userId 936853a2 (brandon) — none for b6be5585
session rows: 1 total, userId 936853a2 — none for kaelyn
```

</details>

### M59. mini nut-monitor is a permanently dead client: active service retrying ups@192.168.10.4 every 5 seconds against a server that is disabled and hardware-less

**Host:** mini · **Component:** nut-monitor (upsmon netclient) · **Auditor:** gap:NAS-side NUT/UPS server — root-cause the dead UPS-monitoring chain (HIGH finding only diagnosed from mini)


mini runs MODE=netclient with 'MONITOR ups@192.168.10.4 1 monuser secret slave' and nut-monitor is 'active', but given the NAS-side root cause (DSM UPS support off, no UPS attached, upsd never starts) this config can never succeed. It fails with 'Connection refused' every ~5 seconds, spamming the journal continuously and giving a false impression that UPS protection is merely degraded rather than nonexistent. Either complete the NAS UPS setup or retire this unit; also note the monuser/'secret' credential in upsmon.conf matches no upsd.users on the NAS side (file exists but service disabled).


<details><summary>Evidence</summary>

```
$ ssh mini 'sudo grep -E "^MONITOR" /etc/nut/upsmon.conf; grep -v "^#" /etc/nut/nut.conf; systemctl is-active nut-monitor; journalctl -u nut-monitor -n 3'
MONITOR ups@192.168.10.4 1 monuser secret slave
MODE=netclient
active
Jul 16 10:53:01 macmini upsmon[777]: UPS [ups@192.168.10.4]: connect failed: Connection failure: Connection refused
Jul 16 10:53:06 macmini upsmon[777]: UPS [ups@192.168.10.4]: connect failed: Connection failure: Connection refused
Jul 16 10:53:06 macmini upsmon[777]: UPS ups@192.168.10.4 is unavailable
$ ssh mini 'timeout 3 bash -c "echo > /dev/tcp/192.168.10.4/3493"'
bash: connect: Connection refused
```

</details>

### M60. 606 unextracted rar/r00 files inside the Plex library roots: 289 release dirs, 252 with no playable video alongside — a legacy backlog unpackerr can never process

**Host:** nas · **Component:** media libraries (/volume2/movies, /volume3/tv) · **Auditor:** gap:NAS unpackerr — live wedge state and archive-extraction backlog never quantified (only 1 case evidenced)


The libraries themselves (not the download area) contain 606 .rar/.r00 files across 289 distinct release dirs; 252 of those dirs have no video >50MB within 2 levels. Unpackerr is queue-driven (polls the arr queue APIs), so nothing will ever extract these. Composition: (a) the 154 sample-tracked Sonarr items above (Gossip Girl S01-S06, Animaniacs 1993 S03-S05 blocks, etc.); (b) rar-only movie dirs where Radarr honestly shows hasFile=False but the only copy of the movie on disk is the unextracted archive set: Do Revenge, Fire Island, Castle in the Sky (Laputa), Last Night in Soho (2160p), Perfect Blue, Spider-Man: Across the Spider-Verse, The Matrix Resurrections (two release dirs), Death on the Nile 1978, Warriors of the Wind (Nausicaa), The Addams Family 1991, The Swan Princess — approx. 13 movies recoverable by extracting in place instead of re-downloading; (c) junk clutter where a real file exists elsewhere in the series/movie folder (e.g. Samurai Champloo S02E08-14 subdirs, Abbott Elementary S01E02, John Wick subtitle/screenshot rars). Side observation: 2 movies are tracked as large .iso images (Bodies Bodies Bodies 62GB, Scooby-Doo WrestleMania 18.9GB) which Plex cannot play. Affected apps: Sonarr and Radarr only — Lidarr/Readarr watched paths and libraries had zero archives.


<details><summary>Evidence</summary>

```
ssh nas: find /volume2/movies /volume3/tv -iname '*.rar' -o -iname '*.r00' | wc -l -> 606; distinct dirs (print0-safe) -> 289; dirs without video >50MB (maxdepth 2) -> 252.
radarr /api/v3/movie: Do Revenge hasFile=False path=/movies/Do.Revenge.2022.1080p.WEB.h264-WATCHER; Last Night in Soho hasFile=False; Perfect Blue hasFile=False; Spider-Man: Across the Spider-Verse hasFile=False; The Matrix Resurrections hasFile=False (x2 dirs); Death on the Nile hasFile=False; Warriors of the Wind hasFile=False; The Addams Family hasFile=False; The Swan Princess hasFile=False.
Bodies Bodies Bodies hasFile=True BODIES_BODIES_BODIES.iso 62065.7MB; Scooby-Doo! WrestleMania Mystery o0os-scoobywrestlemystery.iso 18933.1MB.
```

</details>

### M61. Plex port 32400 is directly reachable from the public internet (edge is NOT fully closed beyond 80/443/8123)

**Host:** nas (192.168.10.4) via home WAN 162.0.177.18 · **Component:** Plex Media Server (port 32400) / edge firewall · **Auditor:** gap:External WAN exposure — port probe was limited to 80/443/8123 from a single vantage


An external TCP-connect probe from the seedbox (betty, a true off-net vantage) against the current home WAN IP 162.0.177.18 found port 32400 OPEN and serving the NAS Plex directly (direct port-forward, not a plex.direct relay). The unauthenticated /identity endpoint returns HTTP 200 and discloses machineIdentifier 70ffcfbb5dc9389e315070cf3a8af99c5fb340b4 (identical to the LAN NAS Plex, confirming it is the home server), exact build version 1.43.3.10793-cd55560bb, and claimed=1. This is consistent with Plex Remote Access being enabled, but it directly refutes the audit's working assumption that the home edge is fully closed beyond 80/443/8123 — there is one additional internet-exposed service, a directly-forwarded media server with an unauthenticated version/identity info-leak. Token-protected endpoints (e.g. /library/sections) still require a valid X-Plex-Token from the WAN; the 200 seen on /library/sections was a LAN-side test from mini (LAN subnet is in Plex's allow-without-auth list) and does NOT indicate unauthenticated library access from the internet. Recommend confirming Plex Remote Access is intentional and the exposed build has no outstanding CVEs; otherwise close/forward via reverse proxy only.


<details><summary>Evidence</summary>

```
WAN IP: ssh mini 'curl -s https://ifconfig.me' -> 162.0.177.18
seedbox probe (18 ports): only 32400 OPEN; all others closed:
  OPEN 32400 / closed 22 2222 5000 5001 8123 8443 3254 5945 13091 8989 7878 8686 8787 9696 6969 3000 853
seedbox HTTP HEAD http://162.0.177.18:32400/identity -> HTTP/1.1 200 OK, X-Plex-Protocol: 1.0
/identity body: <MediaContainer size="0" apiVersion="1.2.2" claimed="1" machineIdentifier="70ffcfbb5dc9389e315070cf3a8af99c5fb340b4" version="1.43.3.10793-cd55560bb">
LAN cross-check (mini -> 192.168.10.4:32400/identity) machineIdentifier matches -> confirmed home NAS Plex
```

</details>

### M62. Broken daily cron entry '0 0 * * * /home/btabaska/bin' executes a directory and fails silently every night; the tv-torrent cleanup it points at never runs

**Host:** mini · **Component:** cron (btabaska crontab) · **Auditor:** gap:recyclarr (custom-format / quality-profile sync to radarr+sonarr) — deployed and monitored but never audited for sync correctness


Discovered while enumerating recyclarr's crontab. The entry runs the PATH /home/btabaska/bin, which is a directory (containing tv_maintenance.sh, dated Feb 2024). exec of a directory fails, so the job errors every midnight with output going to nonexistent local mail — a textbook silent failure. tv_maintenance.sh does 'find /mnt/share/torrents/tv/* -type d -mtime +7 -exec rm -rf {} +' i.e. a 7-day cleanup of the NAS tv-torrent share mounted on mini. That path exists and shows stale junk (e.g. directory '001-la-m-actamorphose-freedownloadvideo.net_202503' from 2025-03, ~16 months old), confirming the cleanup has not been running — old torrent payload accumulates on the share indefinitely. Either the entry should invoke the script (…/bin/tv_maintenance.sh) or, if the cleanup is deliberately retired (script predates the current seedbox/label topology), the crontab line is dead junk that should be removed. Not fixed per read-only mandate.


<details><summary>Evidence</summary>

```
ssh mini 'crontab -l' -> 0 0 * * * /home/btabaska/bin
ls -la /home/btabaska/bin -> drwxrwxr-x ... ; only file: tv_maintenance.sh (Feb 15 2024)
cat tv_maintenance.sh -> find $SOURCE_DIR/* -type d -mtime +7 -exec rm -rf {} +  (SOURCE_DIR=/mnt/share/torrents/tv)
journalctl -u cron: Jul 14/15/16 00:00:01 macmini CRON[...]: (btabaska) CMD (/home/btabaska/bin)  [fires daily]
ls /mnt/share/torrents/tv | head -> 001-la-m-actamorphose-freedownloadvideo.net_202503 (stale, >7d, never cleaned)
```

</details>


---

## LOW (95)

### L1. Nightly SBOM->Dependency-Track pipeline is dead: timer disabled since ~Jul 09 after a failed run; Dependency-Track stack itself is gone

**Host:** mini · **Component:** sbom-nightly.service/.timer + Dependency-Track · **Auditor:** host:mini


sbom-nightly.timer and .service are both 'disabled' (timer inactive/dead, Trigger n/a), so nothing uploads SBOMs to Dependency-Track anymore. Last run Jul 09 03:43-03:50 failed twice over: syft version fetch failed via the tailnet DNS resolver ('lookup toolbox-data.anchore.io on [fd7a:115c:a1e0::53]:53: server misbehaving') and the upload curl couldn't connect ('curl failed uploading host:macmini'). /opt/stacks/dependency-track now contains only an orphan .env (compose removed Jul 11 16:39), i.e. the D-T server was retired but the unit files and orphan dir remain. If retirement was deliberate it violates only hygiene; per the 100%-coverage-manifest mandate this retire should be reflected in the coverage manifest. Weekly export-manifests (git SBOM refresh) still works, so SBOM data isn't entirely gone — only the D-T/nightly path.

### L2. Orphan stack dirs with no running container (litellm, tdarr, maintainerr, dependency-track .env-only; frigate never deployed) plus macOS junk file ._litellm

**Host:** mini · **Component:** /opt/stacks hygiene · **Auditor:** host:mini


Directories under /opt/stacks with no matching container in docker ps: dependency-track, litellm, tdarr, maintainerr (all stripped to just a stale .env on Jul 11 16:39 — .env files may still hold secrets), frigate (compose.yaml + .env present but never deployed), plus recyclarr and wiki which are legitimately containerless (recyclarr = one-shot config dir, wiki/site = caddy-served build artifact). Also '/opt/stacks/._litellm' — a 163-byte executable macOS AppleDouble resource-fork file, pure junk from a Mac-side copy. The litellm dir matches the memory note 'mini litellm dir never deployed / phantom'. No *.bak/*.old/*~ files found anywhere under /opt/stacks (gitignore+cleanup working). apply-static-ip.timer is another spent one-shot unit still loaded (LAST Jul 10, NEXT n/a) — deliberate fix, cosmetic leftover.

### L3. Verification units exit 1 on any warn/crit check, then the next run's systemd-failed-mini check fails BECAUSE of that failed unit — self-referential noise; 16 failed runs incl. a 13-hour block Jul 10 `known-issue`

**Host:** mini · **Component:** verification-quick.service / verification framework · **Auditor:** host:mini


verification-quick.service exits 1 whenever any check fails (e.g. Jul 13 18:41 'FAIL [crit] pinchflat-plex-visible' during the Plex analysis storm), which leaves the unit in failed state; the following docker-fleet tier then reports 'FAIL [warn] systemd-failed-mini' purely because verification-quick itself is the failed unit — a feedback loop that keeps the failure signal alive one extra cycle after the real issue clears. 16 'Failed to start Hourly quick verification' in 14 days: Jul 10 00:41-12:41 hourly (13 consecutive hours) and Jul 13 17:41-19:41 (pinchflat-plex-visible crit era, known Plex storm). All verification tiers currently pass (19/19, 9/9, 14/14 at 15:41 today) and systemctl --failed is clean now. This is a monitoring-design wart consistent with the known 'monitoring tests liveness not correctness' theme; the self-referential loop itself is a new observation.

### L4. macOS junk (.DS_Store, ._AppleDouble files) and a test artifact synced into /volume1/docker service dirs

**Host:** nas · **Component:** filesystem junk · **Auditor:** host:nas


macOS metadata files are present inside NAS docker dirs: /volume1/docker/.DS_Store (10244 bytes), and AppleDouble ._ files e.g. immich/._.env.example, immich/._docker-compose.yml, calibre-web-automated/._docker-compose.yml, and media-automation/._.env.example ._README.md ._docker-compose.yml ._migration-from-ubuntu.md. media-automation also has a leftover empty 'test-write' file (Jul 2). Cosmetic dead weight from SMB writes off a Mac; harmless but pollutes compose dirs and can confuse tooling that globs the directory.

### L5. .bak backup copies accumulating alongside live scripts and configs

**Host:** nas · **Component:** config hygiene / .bak sprawl · **Auditor:** host:nas


Multiple ad-hoc .bak files linger next to their live counterparts: beets/config.yaml.bak-preweb, soularr/config.ini.bak-wrong-path, calibre-web-automated/docker-compose.yml.bak-netshare, readarr/scripts/readarr-copy-to-cwa-ingest.sh.bak-debug + .bak-prexargsfix, scripts/nas/immich-db-dump.sh.bak-audit-20260709, scripts/media/rclone-seedbox-mount.sh.bak-preretune. Harmless but they are dead paths that make it easy to edit/exec the wrong file and add noise to any config-diff.

### L6. Scheduled 04:22 ansible-pull run failed on stale playbook path; repointed unit succeeded at 09:55 — now healthy

**Host:** rig · **Component:** ansible-pull.service (glue-08) · **Auditor:** host:rig


The 2026-07-15 04:22 timer-fired run failed with exit 5/NOTINSTALLED: it pulled the new full-repo topology but still invoked the old path 'configs/ansible/site.yml' ('File does not exist' / 'Could not find a playbook to run'), so one convergence cycle was missed. The unit was repointed (commit b0d8c83) and the 09:55 run this boot used 'foss-setup/configs/ansible/site.yml' and finished cleanly. systemctl --failed is now 0 units (reboot also cleared state). Next scheduled run Thu 04:21 should confirm. Transient topology-switch fallout, already fixed — logging as dead-path evidence, no action needed beyond watching tomorrow's run.

### L7. Persistent journal history truncated to 2 boots (~46.5M, oldest entry Jul 14 17:43) — pre-Jul-14 forensics gone on a box with crash history

**Host:** rig · **Component:** systemd-journald · **Auditor:** host:rig


journalctl --list-boots shows only boots -1 and 0 (first retained entry 2026-07-14 17:43:45); total journal usage is just 46.5M with /var/log/journal persistent and no explicit SystemMaxUse/MaxRetentionSec overrides found in journald.conf(.d). Something removed older journals around the Jul 14 -Syu/reboot (vacuum, or the upgrade). Consequence: the requested 7-day error review only actually covers ~19h, and any future NVMe/PCIe crash investigation (known issue 3 class) loses history older than a day or two. Within the retained window the error log is very quiet: 37 total -p err entries (2 on Jul 14, 35 on Jul 15 — all shutdown/boot noise: dbus activation failures, powerdevil i2c EACCES, ACPI _DSM AE_ALREADY_EXISTS BIOS bug, snd_hda 'no codecs', gkr-pam keyring).

### L8. ~1.7G of dead *arr self-update/backup dirs and orphaned dotnet sockets in ~/tmp from Jun 27

**Host:** seedbox · **Component:** ~/tmp (stale *arr self-update artifacts) · **Auditor:** host:seedbox


~/tmp contains sonarr_update (559M), radarr_update (569M), prowlarr_update (510M) plus *_backup dirs and clr-debug-pipe/dotnet-diagnostic sockets, all dated Jun 27. No sonarr/radarr/prowlarr/dotnet processes run on the seedbox anymore (the arr stack lives on the NAS), so these are orphaned leftovers from a past on-seedbox arr install occupying ~1.7G.

### L9. qBittorrent-nox running since Jun 27 with zero torrents loaded (vestigial second client)

> **RESOLVED 2026-07-17 (fix-21).** Daemon stopped, `~/.startup/qbittorrent` launcher removed (config data left in place). `seedbox-services-manifest` check alerts if it reappears.

**Host:** seedbox · **Component:** qBittorrent-nox · **Auditor:** host:seedbox


A qBittorrent-nox daemon has run since Jun 27 but its BT_backup dir is empty and total app data is only 8M, i.e. it manages no torrents. Deluge is the sole active client (375 torrents). The idle qBittorrent process is dead weight and, per the finding above, also exposes an internet-reachable WebUI on 13091. The ~/.startup/qbittorrent launcher is still active.

### L10. deluged.log is 0 bytes — daemon error logging effectively disabled

**Host:** seedbox · **Component:** ~/.config/deluge/deluged.log · **Auditor:** host:seedbox


The task-requested deluged.log check yielded nothing because ~/.config/deluge/deluged.log is 0 bytes and unmodified since Jun 27 02:37; the running deluged (started Jun 28, --pidfile only, no --logfile) writes no daemon log there. Only filebot.log (671K, actively written) carries any operational history. There is currently no captured error trail for the Deluge daemon should it misbehave.

### L11. 8 of 73 Hue lights unavailable (integration itself healthy)

**Host:** ha (192.168.10.50) · **Component:** hue · **Auditor:** host:ha


Hue Bridge config entry loaded; 65/73 lights report real states. 8 individual bulbs are unavailable: basement ceiling, basement hue white lamp 5, dining hue white lamp 18, kitchen counter x2, kitchen overhead x2, upstairs bathroom vanity 1 — pattern consistent with bulbs cut at wall switches rather than an integration fault. Also one-time hue config_flow warnings (2026-07-03) probing a non-existent bridge at 192.168.20.100 (stale discovery, live bridge is a different unit).

### L12. Error log is quiet: only 15 entries since ~06-27, all transient/one-off (elgato blip, 07-03 DNS outage, stale roomba creds for a removed integration, one-off hassio /mounts schema error)

**Host:** ha (192.168.10.50) · **Component:** system_log · **Auditor:** host:ha


No recurring setup failures or retry loops. Notable one-offs: (a) elgato fetch errors x13 on 07-10 for 192.168.10.182 — both Elgato lights currently available, recovered; (b) 2026-07-03 cluster of met.no/homeassistant_alerts DNS failures + one matter 'Connection failed' — a transient DNS/network outage that day; (c) roomba 'Bad username or password' x4 on 06-27 — but NO roomba config entry exists today and no vacuum entities, so the integration was removed; errors are dead residue; (d) hassio /mounts call error x1 on 07-13 ('not a valid value ... data[version] Got 3.0') during the backup CIFS mount work — mount works (nas_backups agent succeeding daily), so one-off. REST /api/error_log returns 404 on this core version; WS system_log/list used instead.

### L13. Stale UI clutter: 1 week-old failed-login notification (mini token now works) + 2 pending Apple TV discovery flows awaiting PIN

**Host:** ha (192.168.10.50) · **Component:** persistent notifications / pending flows · **Auditor:** host:ha


(a) Persistent notification 'Login attempt failed ... from macmini (192.168.10.2)' dated 2026-07-08 still displayed; re-tested the mini's /etc/verification/env HA_TOKEN just now and it authenticates HTTP 200, so the failure was transient (matching http.ban log entries also show a curl from the operator Mac 192.168.10.253 on 07-07) and the notification is stale clutter. (b) Two zeroconf-discovered apple_tv config flows sit at step pair_with_pin: 'Basement (2)' and 'Entertainment Room' (both Apple TV 4K gen 3) — discovered devices never paired, harmless but lingering.

### L14. Libreseerr request status only refreshes on UI-driven POST /api/requests/refresh; 'Rosemary and Rue' imported 07-13 still shows 'processing', and refresh swallows all exceptions

**Host:** mini · **Component:** libreseerr request status sync · **Auditor:** svc:request-layer


app.py's GET /api/requests returns cached requests_history; status transitions happen only in POST /api/requests/refresh (called by the UI). Book 305 (Rosemary and Rue) was grabbed AND imported 2026-07-13T20:17 (474KB epub on disk in Readarr) yet its request still reads 'processing' 2 days later because nobody has opened the UI since (last UI log activity 2026-07-13 16:17). The refresh loop also has 'except Exception: pass' — Readarr connectivity errors during refresh are silently ignored, keeping stale statuses with no log trace. Cosmetic for available books, but it makes the request list untrustworthy as a status surface.

### L15. Navidrome indexes the Synology #recycle bin of the music share — deleted tracks reappear in the library

**Host:** mini · **Component:** navidrome · **Auditor:** svc:media-aux


The scanner processes folder '#recycle/YouTube' (audioCount=2) every scan and 2 media_file rows have paths under #recycle. Anything deleted from the music share via CIFS lands in the NAS recycle bin and stays playable/visible in Navidrome. Needs a .ndignore for #recycle or DSM recycle-bin exclusion (not applied — log-only pass).

### L16. 70 tracks flagged missing in Navidrome DB (whole Chappell Roan album chunk + mgk 'lost americana' mp3s)

**Host:** mini · **Component:** navidrome · **Auditor:** svc:media-aux


70 media_file rows have missing=1 — files that were deleted/renamed on the NAS but remain in the DB as 'missing' entries (14 under 'Chappell Roan/The Rise and Fall of a Midwest Princess', ~20 under 'mgk/lost americana' .mp3, etc.). Likely re-tagged/re-formatted replacements; harmless but shows as missing-file cruft in the UI until purged.

### L17. Kometa config dead paths: nonexistent 'Anime' Plex library, missing /config/Music.yml, blank radarr/sonarr/tautulli creds flagged every run

**Host:** mini · **Component:** kometa · **Auditor:** svc:media-aux


Every run logs: Plex Error: Library 'Anime' not found (Plex has Movies, TV Shows, Music, YouTube); File Error: /config/Music.yml does not exist; and Config Errors x3 each for radarr token, sonarr token, tautulli apikey being blank (integrations declared per-library but never credentialed — dead config). Also /config/assets path missing. Cosmetic-to-drift level: the run still completes, but the config references things that don't exist while real creds (arr keys, tautulli apikey) are available in the vault. Version drift too: running 2.3.1.4, newest 2.4.4.

### L18. 3 Oban retry jobs at attempt 18/20 grinding on permanently-impossible videos (members-only/unavailable); 31 of 38 pending items are permanent content failures

**Host:** mini · **Component:** pinchflat · **Auditor:** svc:media-aux


Jobs 31/34/35 (MediaDownloadWorker) are at attempt 18 of 20, next scheduled 2026-07-18, retrying content that can never succeed — e.g. media item #10 (Vj1lIsrFbds) fails with 'Join this channel to get access to members-only content'. Of 38 pending (undownloaded) items, 31 have members-only/'Video unavailable' errors. Harmless retry churn that burns yt-dlp calls until attempts exhaust; overall pipeline is otherwise healthy (1364 items downloaded, files landing on /mnt/nas-youtube/pinchflat, last success 2026-07-13 21:12).

### L19. Leftover empty /opt/stacks/pinchflat/downloads directory (real target is /mnt/nas-youtube/pinchflat)

**Host:** mini · **Component:** pinchflat · **Auditor:** svc:media-aux


.env sets PINCHFLAT_DOWNLOADS=/mnt/nas-youtube/pinchflat and the container correctly bind-mounts that to /downloads, but the compose-default ./downloads directory still exists in the stack dir, empty — a dead path that could mislead (e.g. someone checking 'downloads' locally sees nothing, as this audit initially did).

### L20. ~14h docker-DNS outage window on mini 2026-07-08 21:18 -> 2026-07-09 11:18 UTC (all lookups 'server misbehaving')

**Host:** mini · **Component:** docker embedded DNS (127.0.0.11) · **Auditor:** svc:docs-life


Every external DNS lookup from at least the miniflux container failed with 'lookup <host> on 127.0.0.11:53: server misbehaving' for ~14 hours, i.e. the docker embedded DNS forwarder could not reach the host's upstream resolver (mini resolves via tailscale 100.100.100.100 / local unbound-adguard stack). Multiple container restarts occurred on 07-09 (wallabag_db 11:55/15:23/20:29, vaultwarden SIGTERMs 11:23/16:29), after which DNS recovered. DNS confirmed healthy now from a container on the same host. Any container doing outbound fetches in that window failed silently; miniflux is the confirmed casualty. Root cause of the window not identified from logs alone — watch for recurrence.

### L21. Wallabag past incident (resolved): ~2 days of per-request CRITICAL 'jms_serializer_default is not writable'; prod.log silent since 2026-07-07

**Host:** mini · **Component:** wallabag · **Auditor:** svc:docs-life


var/logs/prod.log (5.9MB) shows request.CRITICAL 'The directory /var/www/wallabag/var/cache/prod/jms_serializer_default is not writable' plus cache pool fopen failures on every request (including the per-minute /api/info healthcheck) up to 2026-07-07 20:20; the container restart at 20:21 and the recreate on 07-09 20:31 fixed it — cache dirs now exist owned nobody:nobody, /api/info returns 200 locally, via host port 8085 and via https://wallabag.tabaska.us, and there are zero 5xx in the last 48h of nginx access logs. Residual oddity: nothing has been written to prod.log since 2026-07-07 20:20 despite continuous traffic, so either monolog verbosity changed or file logging is dead — future wallabag errors may be invisible. Task brief noted wallabag is 'known finicky' but this specific incident/logging gap is not in the known-issue list.

### L22. Mealie docker log file corrupted with NUL bytes — full-history 'docker logs' aborts mid-stream

**Host:** mini · **Component:** mealie / docker json-log · **Auditor:** svc:docs-life


Reading mealie's full container log history aborts with 'error from daemon in stream: Error grabbing logs: invalid character \x00 looking for beginning of value' — the json-file log on disk contains NUL bytes, the classic artifact of an unclean host shutdown (consistent with the 07-09 mini events). Service itself is healthy: Up 5 days (healthy), v3.4.0, allowSignup=false, recent logs are only 200 OK healthcheck/uptime-kuma hits, no application errors. Impact is forensic only: log history before the corruption point is unreadable via docker logs.

### L23. Leftover bootstrap: CREATE_ADMIN creds still active in .env and a second feed-less 'admin' account exists; feeds owned by 'btabaska'

**Host:** mini · **Component:** miniflux · **Auditor:** svc:docs-life

> **Resolution (2026-07-16, task `fix-33`):** `admin` (id=2) deleted from the DB;
> `CREATE_ADMIN`/`ADMIN_*` stripped from compose and `.env`; an API key for `btabaska` was
> minted and stored in the vault under `miniflux.api_key` (closing the "not in vault" gap).
> Regression check `mini-miniflux-no-bootstrap-admin` guards against reappearance.


/opt/stacks/miniflux/.env still carries CREATE_ADMIN=1 with ADMIN_USERNAME/ADMIN_PASSWORD in plaintext, despite the compose comment saying these may be removed after first login. The DB shows two admin users: id=1 btabaska (owns all 52 feeds) and id=2 admin (owns none — API basic-auth as 'admin' returns an empty feed list, which can mislead API-based monitoring/audits into thinking there are no feeds). Dead-path/cred-hygiene junk, not a live outage. Also note these miniflux admin creds are not in .handoff-secrets.yaml, only in the stack .env.

### L24. deptrack.tabaska.us is a dead path: in vault + wildcard DNS, but no Caddy vhost and no Dependency-Track container anywhere on mini

**Host:** mini · **Component:** caddy / secrets-vault · **Auditor:** svc:infra-mini


The secrets vault carries dtrack admin creds and url https://deptrack.tabaska.us, and the LAN wildcard *.tabaska.us -> 192.168.10.2 makes the name resolve, but the Caddyfile has no deptrack/dtrack vhost (Dependency-Track only appears in a comment as a 'candidate'), no dtrack container exists (running or stopped), and /opt/stacks/dependency-track is an empty directory. Clients connecting get a TLS 'internal error' alert. Public DNS (1.1.1.1) does not resolve the name. Vault entry + empty stack dir are stale drift; nothing depends on it.

### L25. Homepage siteMonitors false-negative on Sunshine/Apollo (self-signed TLS) and Healthchecks (HTTP parse error) while both services are up

**Host:** mini · **Component:** homepage · **Auditor:** svc:infra-mini


Two more recurring widget failures: (1) Sunshine tile siteMonitor https://192.168.10.12:47990 fails with ECONNRESET/'socket hang up' (119 errors/96h) because Apollo serves a self-signed cert homepage won't accept — caddy's apollo vhost (with tls_insecure_skip_verify) works fine (307). (2) Healthchecks tile siteMonitor http://healthchecks:8000 logs 'Parse Error: Expected HTTP/, RTSP/ or ICE/' (119 errors/96h) even though a manual GET from inside the homepage container returns a clean 302->200 and health.tabaska.us works — the widget probe itself misfires. Both tiles show a broken state for healthy services (dashboard lies). Related in spirit to known-issue #15 (monitoring != correctness) but these are specific new tile bugs.

### L26. stash vhost sends literal '{server_port}' as X-Forwarded-Port ({server_port} is not a valid Caddyfile placeholder)

**Host:** mini · **Component:** caddy · **Auditor:** svc:infra-mini


The stash.tabaska.us block sets `header_up X-Forwarded-Port {server_port}`, but {server_port} is not a Caddyfile shorthand, so the upstream receives the literal string '{server_port}' — proven by caddy's own access log which records the outbound header verbatim. Harmless for Stash today but it is a silent misconfig; the intended placeholder is {port} (or drop the line, caddy sets sane forwarding headers itself).

### L27. Forgejo docker json-log is corrupted (NUL byte) — `docker logs --since` aborts mid-stream; also repo 'etc-macmini' is empty since 2026-07-03

**Host:** mini · **Component:** forgejo · **Auditor:** svc:infra-mini


Retrieving forgejo logs with `docker logs forgejo --since 168h` fails with "Error grabbing logs: invalid character '\x00' looking for beginning of value" (classic json-file corruption from an unclean stop); `--tail N` works around it. Forgejo itself is healthy: /api/healthz passes (cache+db), last 5000 log lines contain zero [E]/[W], ssh :2222 is open, 0 Actions runs (unused), no mirror repos (3 repos, is_mirror=f). One oddity: repo 'etc-macmini' is_empty=true and untouched since 2026-07-03 — looks like an /etc-backup push flow that was never completed (docker-stacks and homelab repos are fresh, updated 2026-07-15).

### L28. Beszel email notifications are a dead path: user_settings lists an email destination but the hub has no SMTP configuration

**Host:** mini · **Component:** beszel · **Auditor:** svc:monitoring-stack


user_settings has emails:[brandon.tabaska@protonmail.com] alongside the working ntfy webhook, but the beszel container env contains only APP_URL and PATH — no SMTP_* vars — so any email alert send silently fails. The ntfy webhook (ntfy://:tk_78rb...@ntfy:80/homelab-alerts) is the only functional channel; its token was last used 09 Jul (test), and no alert has triggered since.

### L29. Uptime-kuma 16h uptime explained: clean operator restart 2026-07-15 00:54 UTC for the NAS-monitor bootstrap; history shows an embedded-MariaDB crash class (InnoDB crash recovery, fatal 'Connection lost' traces, NUL-corrupted log region)

**Host:** mini · **Component:** uptime-kuma · **Auditor:** svc:monitoring-stack


The recent restart is benign: exit=0, FinishedAt 00:54:07Z / StartedAt 00:54:08Z, coinciding with bootstrap-nas-monitors.sh (mtime Jul 15 00:54) which seeded the Whisparr monitor at 00:54:45 (matches git commit b6f1f48 'uptime-kuma NAS bootstrap'). However the container has had 5 process starts since creation Jul 2 (Jul 2 19:51, Jul 3 19:02, Jul 5 16:11, Jul 7 16:21, Jul 14 20:54 EDT); Jul 3 and Jul 5 starts logged 'InnoDB: Starting crash recovery', logs contain repeated fatal 'Trace: Error: Connection lost: The server closed the connection' via process.unexpectedErrorHandler plus KnexTimeoutError pool exhaustion on Jul 6, and the log stream around Jul 3-7 is corrupted with NUL bytes ('invalid character \x00' when reading that range) — consistent with the pre-fix mini DHCP/outage era hard stops. Kuma runs the embedded-mariadb backend, which is the fragile piece. Currently healthy: all 53 active monitors up, heartbeats fresh at 16:28 UTC.

### L30. NAS system timezone is US/Pacific (PDT) while the fleet standard is America/New_York — DSM-scheduled tasks and log timestamps are 3h off fleet convention

**Host:** nas · **Component:** system clock / timezone · **Auditor:** svc:monitoring-stack


date on the NAS returns PDT (clock itself is accurate, only the zone differs). Containers that set TZ explicitly (e.g. diun with TZ=America/New_York) behave correctly, but anything using DSM local time (Task Scheduler entries, DSM logs, file mtimes shown in ls) is displayed/scheduled in Pacific — e.g. diun.db mtime shows 03:30 PDT for the 06:30 EDT run, which initially reads as a schedule miss. _meta.timezone in the secrets vault says America/New_York.

### L31. Radarr health warning: update available (only non-empty health across the stack)

**Host:** nas (192.168.10.4) · **Component:** radarr · **Auditor:** svc:arr-stack


Verbatim health warning: type=warning, source=UpdateCheck, message="New update is available: v6.3.0.10514" (running 6.2.1.10461). Sonarr, lidarr, readarr, prowlarr and whisparr all return [] from /health. Versions: Sonarr 4.0.19.2979, Radarr 6.2.1.10461, Lidarr 3.1.0.4875, Readarr 0.4.18.2805, Prowlarr 2.4.0.5397, Whisparr 2.2.0.108.

### L32. Single wanted/missing album stalled 5 days: The Marshall Mathers LP missing 1 track

**Host:** nas (192.168.10.4) · **Component:** lidarr · **Auditor:** svc:arr-stack


Lidarr's only monitored missing item is Eminem — The Marshall Mathers LP at 17/18 tracks (94.4%); the gap is track 1 'Public Service Announcement 2000' (a skit often absent from releases). Last grab 2026-07-10; no re-grab since. Likely permanently unfillable at current release availability rather than a broken flow.

### L33. 45 unmapped folders in /movies root — untracked junk: '- Copy' duplicates, multi-movie packs, scene-named leftovers, 'Moviesnew'

**Host:** nas (192.168.10.4) · **Component:** radarr root folder /movies · **Auditor:** svc:arr-stack


Radarr reports 45 unmappedFolders in its /movies root. These are invisible to Radarr (no upgrades, no monitoring, not counted). Categories: literal duplicates ('Guardians...Atmos-FGT - Copy', 'Hannah Gadsby Nanette (2018) - Copy'), unmappable multi-movie packs (Star Wars saga, Indiana Jones 1-4, Matrix Trilogy, Pirates pack, Star Trek 13-movie pack, Back to the Future trilogy, Hobbit trilogy, Fast&Furious 1-6, Bad Boys/Grown Ups duologies, Men in Black trilogy, 'Muppets 9 Pack'), low-quality relics (DVDScr, HDRip.XviD), a stray TV item (Ed.Edd.n.Eddy.S05) and a mystery 'Moviesnew' folder. Dead data occupying the 11.5TB volume (8.9TB free, not urgent).

### L34. 25 unmapped folders in /tv root, incl. loose per-episode release folders (Euphoria S03E02-06, I Love LA S01E01-05) and whole untracked series

**Host:** nas (192.168.10.4) · **Component:** sonarr root folder /tv · **Auditor:** svc:arr-stack


Sonarr reports 25 unmappedFolders in /tv. Notable: 5 loose Euphoria S03 single-episode release folders and 6 I Love LA S01 folders sitting directly in the library root (look like manually dropped/never-imported downloads — Sonarr will never import from a root folder), plus whole series not added to Sonarr (One Piece, Black Sails, Roseanne, Harper's Island, Reign, Russian Doll, BATMAN TAS, Justice League Unlimited, The Office Extended...) and Synology '#recycle'. These get no monitoring/upgrades and per-episode scene folders in the root are likely invisible to Plex naming conventions too.

### L35. Whisparr effectively inert (1 series, zero lifetime history) and its API key is absent from the secrets vault

**Host:** nas (192.168.10.4) · **Component:** whisparr · **Auditor:** svc:arr-stack


Whisparr 2.2.0.108 is healthy (health [], queue 0) with 4 prowlarr-synced indexers and root /data accessible, but has exactly 1 monitored series and history totalRecords=0 — it has never grabbed or imported anything. Its API key is not in foss-setup/.handoff-secrets.yaml arr_api_keys (only sonarr/radarr/lidarr/readarr/prowlarr); had to extract it from /volume1/docker/whisparr/config/config.xml on the NAS. Also note its Deluge category is 'tv-whisparr' (inconsistent with the other apps' '<app>' naming) with no post-import category.

### L36. Plex credits detection failing on ~31% of items with 'incomplete marker attributes'

**Host:** nas · **Component:** plex · **Auditor:** svc:nas-apps


Within the current 1h40m log window, 82 of 262 credits-detection jobs completed with 'success: 0, failures: 1', each paired with ERROR '[CreditsDetectionManager/Response::fetch/MarkerResponse] incomplete marker attributes' and 'BufferingLineReader: failed to read line (error: -1)'. The scanner child process exits 0 but no marker is produced, so ~1/3 of episodes silently get no credits markers. The queue still advances (not stuck), but this failure pattern is new detail beyond the known storm.

### L37. Stale core dumps at /volume1 root incl. Plex Transcoder (Jul 7) and qbittorrent-nox (app no longer in stack)

**Host:** nas · **Component:** dsm / crash artifacts · **Auditor:** svc:nas-apps


Five core.gz crash dumps sit at /volume1/ root: '@Plex Transcoder' (Jul 7 2026, 1.4MB — a transcoder crash days before the analysis storm), @python (Jul 3 2026, 45MB), two @qbittorrent-nox cores (Dec 2025 and Apr 2026 — qbittorrent is not part of the current NAS stack, leftover from the old-server layout), and @snmpd (Sep 2025). Junk worth clearing; the Plex Transcoder core is the only recent one and Plex has been stable since (crash reports dir shows uploads for 1.41.5 and current 1.43.3).

### L38. Dead crontab entry on mini executes a directory nightly: '0 0 * * * /home/btabaska/bin'

**Host:** mini · **Component:** crontab · **Auditor:** svc:nas-apps


Found while tracing the MeTube/beets flow: mini's user crontab's first entry runs /home/btabaska/bin at midnight daily, but that path is a directory (containing only tv_maintenance.sh, dated Feb 2024 — old-server era). cron cannot execute a directory, so this fails silently every night. Either the intent was to run tv_maintenance.sh (which then hasn't run since migration) or the entry is pure junk to remove.

### L39. Residue from this morning's RAG recovery: 239 dangling knowledge_file rows + ~245 orphaned file records and stale 768-dim vector data left behind

**Host:** rig · **Component:** open-webui (webui.db + vector_db) · **Auditor:** svc:ai-stack


The recovery from the dimension mismatch created a fresh collection but never cleaned up the old one: knowledge table has only 1 row (448325ab homelab-wiki), yet knowledge_file holds 239 rows pointing at deleted knowledge_id 594903ad-41f7-49b6-8bb1-9f595c33343a, and the file table has 487 rows (242 live + 239 stale + 6 orphans). The stale files' 768-dim embeddings remain inside the 255MB vector_db. No functional impact on current retrieval (verified working), but it is dead data that doubles the wiki footprint, and a future global reindex or file-level operation touching the stale entries could resurface dimension errors. Cleanup (delete dangling knowledge_file/file rows + orphaned chroma collections) is an easy maintenance-window item. NOT fixed — log-only pass.

### L40. ~17.9GB of unreferenced GGUFs sitting in /opt/llm/models outside the archive/ dir

**Host:** rig · **Component:** llama-swap model store (/opt/llm/models) · **Auditor:** svc:ai-stack


Two model files in /opt/llm/models are referenced by no llama-swap config entry: Qwen3.6-27B-UD-Q4_K_XL.gguf (17.6GB — the non-MTP variant superseded 2026-07-15 by Qwen3.6-27B-MTP-UD-Q4_K_XL.gguf) and nomic-embed-text.gguf (274MB — replaced by Qwen3-Embedding-0.6B the same day). An archive/ directory exists for exactly this purpose but these were left in the active dir. Dead weight on NVMe; harmless otherwise (dir is mounted ro into the container). llama3.2-3b.gguf, qwen2.5-coder-7b.gguf etc. are all still referenced and fine.

### L41. Apollo healthy and auth works, but journal shows constant Avahi service re-registration churn (~every 20s)

**Host:** rig · **Component:** Apollo (apollo.service, systemd user unit) · **Auditor:** svc:gaming


Apollo runs as a systemd USER unit (/usr/lib/systemd/user/apollo.service, enabled), active 10h, 43MB RSS, PID 3977. Web UI answers on https://192.168.10.12:47990 (GET / → 307 redirect to login) and POST /api/login with vault creds returns HTTP 200. However the journal is dominated by an mDNS loop: 'Adding avahi service cachyos' followed by 'Avahi service cachyos successfully established' repeating every ~20 seconds continuously — the mDNS registration is being dropped and re-added in a tight cycle, which is log spam and may cause the host to flap in discovery clients (Moonlight). The interleaved 'Web UI: [192.168.10.2] -- redirecting' every 60s is just the uptime-kuma probe from mini. Note: the unit is invisible to system-level journalctl/systemctl ('-u apollo' returns no entries; must use systemctl --user with XDG_RUNTIME_DIR) — worth knowing for monitoring.

### L42. 273 of 375 torrents are 100% done >48h but still in pre-import labels; reaper only covers sonarr labels (radarr/lidarr/readarr residue accumulates)

**Host:** seedbox · **Component:** deluge + deluge-reaper · **Auditor:** flow:movies-tv


Labels: sonarr 257, sonarr-imported 84, radarr 4, radarr-imported 13, lidarr 5, readarr 7. 273 torrents are finished (100%, seeding, up to 313h old) but never relabeled to *-imported — spot-checks (Teen Titans Go S09E25/26/31/32, Simpsons S09E01-03, Big Fish, Ghost in the Shell, D.E.B.S.) confirm all WERE imported into the library, so no silent import misses; these predate the imported-category config (new flow works: 84 sonarr-imported/13 radarr-imported exist, arr queues are 0). deluge-reaper runs daily --live but LABELS={sonarr,sonarr-imported} only and age>=14d (oldest sonarr residue is 13d, so 'LIVE: 0 eligible' every day so far); radarr/lidarr/readarr-labeled residue will never be reaped. No error-state or stuck-incomplete torrents. 1.4TB in files/, 5.8TB free on the slot.

### L43. Junk/unmanaged content in library roots: ~45 unmapped folders in /movies (incl. ' - Copy' dupes, 'Moviesnew') and loose episode release folders in /tv for shows not in Sonarr

**Host:** nas · **Component:** radarr/sonarr library roots · **Auditor:** flow:movies-tv


Radarr reports ~45 unmappedFolders in /movies (e.g. 'Guardians...FGT - Copy', 'Hannah Gadsby Nanette (2018) - Copy', 'Moviesnew', multi-movie pack folders) — content invisible to Radarr management; several surface in Plex as the unmatched junk items above. /tv root holds loose single-episode release folders for Euphoria S03E02-E06 and I Love LA S01E01-E05; neither show exists in Sonarr (Plex serves them: Euphoria (US) 13 leaves, I Love LA 8 leaves) — unmanaged/dead paths that Sonarr can never upgrade or track.

### L44. Navidrome indexes the Synology recycle bin: 2 deleted YouTube-rip MP3s live in the music library via #recycle

**Host:** mini + nas · **Component:** navidrome / NAS music share · **Auditor:** flow:music


The read-only CIFS mount //192.168.10.4/music on mini exposes the Synology #recycle folder, and Navidrome has no exclusion for it: 2 media_file rows with missing=0 point at '#recycle/YouTube/Me at the zoo.mp3' and '#recycle/YouTube/Numb (Official Music Video) [4K UPGRADE] - Linkin Park.mp3' — deleted junk that resurfaces as browsable/searchable library tracks (also visible to MusicSeerr's /music local-files mount, same path). The scanner re-processes #recycle/YouTube on scans (audioCount=2 each time). Fix options (log-only): drop a .ndignore, disable Recycle Bin on the music share, or mount below the recycle level.

### L45. Junk empty duplicate album folder '/volume1/music/Eminem/The Death Of Slim Shady (Coup De Grace)' (0 bytes) beside the managed folder

**Host:** nas · **Component:** NAS music share · **Auditor:** flow:music


The Eminem artist dir contains both the Lidarr-managed 'The Death of Slim Shady (Coup de Grâce) (2024)' (19 tracks, verified in Navidrome+Plex) and a completely empty leftover 'The Death Of Slim Shady (Coup De Grace)' (different casing/diacritics, no year suffix, created 2026-07-10 13:16, 0 bytes). Dead path from an earlier naming scheme or aborted import; safe deletion candidate (not deleted, log-only).

### L46. Ghost duplicate albums in Navidrome DB: 4 missing albums / 70 missing media_files, incl. shadow 'Hotel Diablo' and 'lost americana' rows

**Host:** mini · **Component:** navidrome DB · **Auditor:** flow:music


The Navidrome DB retains missing=1 ghost rows from pre-upgrade imports: duplicate album rows 'Hotel Diablo' (missing ghost song_count=20 vs live 14/14) and 'lost americana' (ghost 13 vs live 13/13); 4 missing albums and 70 missing media_file rows total. Navidrome hides missing items in the default UI so impact is cosmetic (they can surface in 'missing files' views and inflate mbid indexes); housekeeping candidate via Navidrome's missing-files cleanup. MusicSeerr request tracking was not confused by them (both albums show imported).

### L47. Library junk: split author identities, one duplicate title, and 6 foreign-language editions from bulk grabs; no 'name (1).epub' dupes

**Host:** nas · **Component:** CWA library (/volume1/books) · **Auditor:** flow:books


Full file listing of /volume1/books (excluding @eaDir) shows: (a) duplicate author dirs 'Eoin Colfer' vs 'Colfer, Eoin' (Illegal, Iron Man under the comma form) and 'George R. R. Martin' vs 'George R.R. Martin' (Armageddon Rag, Fevre Dream, Sandkings, Windhaven, The Princess and the Queen under the R.R. form) — splits series/author views on Kobo; (b) duplicate book: 'A Game of Thrones_ A Song of Ice and Fire_ Book One (42)' AND 'A Game of Thrones (52)'; (c) 6 non-English editions likely unwanted: Le trone de fer, La bataille des rois (FR), L'invincible forteresse, L'ombre malefique (FR), Urzeala tronurilor (RO), Festin de cuervos (ES); (d) 'Hunter's Run (32)' missing cover.jpg. No literal 'name (1).epub' collision patterns; the '(N)' dir suffixes are normal calibre book IDs. Every book has matching .epub + .kepub pairs (kepubify working).

### L48. Pinchflat burning retries on 3 permanently-impossible members-only videos (attempt 18/20, rescheduled to Jul 18)

**Host:** mini · **Component:** pinchflat (oban job queue) · **Auditor:** flow:youtube-photos


All 38 undownloaded media_items across both sources are members-only or 'Video unavailable' items (yt-dlp: 'Join this channel to get access to members-only content' / 'available to this channel's members on level ...') — these can never succeed without channel-membership cookies. 3 oban MediaDownloadWorker jobs (media_items 6, 9, 10 — Yellow Cherry Jam members-only sessions) are in state 'retryable' at attempt 18/20 with error {:error, :download_failed}, rescheduled for 2026-07-18. Harmless but wasted yt-dlp calls; they will hit max_attempts and discard. No real download failures exist.

### L49. MeTube manual downloads work, but every audio file it ever produced was silently deleted from /volume1/music/YouTube (now only in #recycle); landing zone empty

**Host:** mini + nas · **Component:** metube -> NAS music share (audio download path) · **Auditor:** flow:youtube-photos


MeTube (mini, Up 6 days) logs show its last manual download completed successfully 2026-07-08T14:31:43Z ('Numb ... Linkin Park' -> /audio/*.mp3, i.e. /mnt/nas-music-rw/YouTube on //nas/music). However /volume1/music/YouTube is now EMPTY, and both audio files ever produced ('Me at the zoo.mp3' Jul 8 03:10, 'Numb...mp3' Jul 8 14:31) sit in /volume1/music/#recycle/YouTube — something deleted them after download. Most likely culprit is the since-retired rig push music-mirror (rsync --delete-after, cf. known issue 2 / media-06): the surviving rig unit nas-music-mirror.service is now pull-direction ('Mirror NAS music library -> ~/Music') and cannot delete NAS files, and the old music-mirror.service no longer exists on rig (no journal entries). So the deleter is probably gone, but this is unverified: there have been zero metube downloads since Jul 8, so nothing has tested whether new audio output persists. User-facing effect: metube reports 'completed' but the file vanished — silent failure. Video path note: /volume1/youtube/metube is empty and the docker log contains exactly one 'Download completed' ever; metube is barely used. Recovery: both mp3s are intact in the share recycle bin.

### L50. //nas/youtube #recycle holds 1357 deleted video files consuming 81GB

**Host:** nas · **Component:** youtube share recycle bin · **Auditor:** flow:youtube-photos


The youtube share's recycle bin contains 1357 video files totalling 81GB — residue of the 2026-07-13 ACL-fix / re-ingest churn (nearly mirrors the 1364 live pinchflat files). Plex does not see it (section count matches live files exactly), so it is purely wasted space. Volume has headroom (1.3T/14T used), so no urgency; emptying the share's recycle bin (or letting a DSM recycle-retention schedule do it) reclaims 81GB.

### L51. Five process core dumps sitting at /volume1 root, including a 45MB python core (Jul 3) and a Plex Transcoder core (Jul 7)

**Host:** nas · **Component:** DSM system (crash artifacts) · **Auditor:** flow:youtube-photos


Root of /volume1 contains crash core dumps: '@Plex Transcoder...core.gz' (1.4MB, Jul 7 13:09 — a Plex transcoder crash during the pre-storm period), '@python...core.gz' (45MB, Jul 3 11:52), two '@qbittorrent-nox...core.gz' (Dec 8 2025, Apr 25 2026) and '@snmpd...core.gz' (Sep 26 2025). Evidence of past crashes (none recurring since Jul 7) plus ~51MB of junk. Nothing correlates with a current outage; worth a periodic look if Plex transcoder cores keep appearing, and safe to clean during a maintenance window (root-owned, not touchable read-only anyway).

### L52. deptrack.tabaska.us is a dead name: Dependency-Track retired 2026-07-11, but vault creds + leftover stack dir remain

**Host:** mini · **Component:** secrets vault + /opt/stacks/dependency-track + DNS wildcard · **Auditor:** flow:dns-proxy


Answer to 'where IS it?': nowhere — progress.json records Dependency-Track FULLY RETIRED 2026-07-11 (3 NAS containers compose-downed, Kuma monitor, caddy vhost, homepage tile all removed); NAS /volume1/docker has no dependency-track dir, and no dtrack container exists on mini or rig. Leftovers: (1) .handoff-secrets.yaml still carries dtrack.admin_user/admin_password/url=https://deptrack.tabaska.us; (2) mini /opt/stacks/dependency-track/ still holds a template .env with placeholder DB password 'change_this_strong_db_password'; (3) the *.tabaska.us wildcard rewrite makes deptrack.tabaska.us resolve to caddy on both adguards, where TLS handshake fails (no vhost). Same partial-deletion pattern for litellm/tdarr (.env left) and maintainerr (.env + data/ dir left) despite progress notes saying those dirs were DELETED — live-vs-tracker drift.

### L53. www.tabaska.us has a PUBLIC A record pointing at private LAN IP 192.168.10.2

**Host:** cloudflare (public DNS) · **Component:** tabaska.us public zone · **Auditor:** flow:dns-proxy


Every other service name is correctly NXDOMAIN in public DNS, but www.tabaska.us resolves publicly (1.1.1.1 and 8.8.8.8) to 192.168.10.2 — an RFC1918 address. The record is dead for external users (unroutable) and leaks internal addressing (reveals the reverse-proxy host's LAN IP). Should be deleted from the Cloudflare zone or repointed per split-horizon design.

### L54. Secondary AdGuard (NAS) forwards to Quad9 DoH instead of an Unbound recursor — diverges from documented design

**Host:** nas · **Component:** adguardhome-nas upstream DNS · **Auditor:** flow:dns-proxy


adguard-mini upstreams to udp://unbound:5335 (local recursive DNSSEC resolver, per design). adguard-nas upstreams to https://dns10.quad9.net/dns-query. The unbound compose doc explicitly says the second AdGuard should point at 'its own Unbound (or this one over Tailscale)'. Functional (external names resolve fine) but the privacy/DNSSEC posture differs between primary and secondary resolvers, and secondary queries leave the LAN to a third party. Additionally adguard-nas sees ALL clients as 172.23.0.1 (docker bridge NAT), so per-client stats/rules are impossible on the secondary.

### L55. stash vhost sends literal '{server_port}' as X-Forwarded-Port (invalid Caddy placeholder)

**Host:** mini · **Component:** caddy stash vhost · **Auditor:** flow:dns-proxy


The stash.tabaska.us block uses `header_up X-Forwarded-Port {server_port}` but {server_port} is not a valid Caddyfile shorthand placeholder, so the literal string '{server_port}' is sent upstream to Stash on every request (visible in caddy's own access-log capture of proxied headers). Cosmetic unless Stash ever uses that header for URL generation.

### L56. Rig restic fresh and nightly-consistent (0.19.1, dailies 07-10..07-15) but /opt gap persists: AMP 'Main' ADS controller instance and /opt/stacks/playit config are NOT in the backup set `known-issue`

**Host:** rig · **Component:** restic include set (/opt gap) · **Auditor:** flow:backups


Known issue 5 current state: rig BACKUP_PATHS = /etc /home/btabaska /opt/stacks/palworld/game/Pal/Saved /opt/stacks/palworld/game/backups /opt/stacks/amp/config/.ampdata/instances/MinecraftCross01 (MinecraftCross01 first captured in the 2026-07-15 01:40 snapshot). Snapshots are fresh: dailies exist for every day 07-10 through 07-15 (latest 1d8c27ca 2026-07-15 01:40:42, 7.069 GiB); timer last ran 01:40:38 EDT, next 01:38 tomorrow. Live /opt contents NOT covered: /opt/stacks/amp/config/.ampdata/instances/Main (the AMP ADS controller — losing it means rebuilding AMP config/instances; licence key is in the vault), /opt/stacks/playit (agent config; secret also in vault), /opt/scripts + /opt/pcie-aer-monitor (regenerable from repo/ansible), /opt/llm + /opt/stacks/beszel-agent (regenerable). The Main instance is the only item of real value missing.

### L57. Leftover 8-byte 'ao-verify'/'ao-verify2' test snapshots in both restic repos will never be expired by the forget policy

**Host:** backblaze-b2 · **Component:** restic repos (mini+rig) · **Auditor:** flow:backups


Both repos contain tiny verification snapshots of /etc/hostname created during the 07-14 append-only-key validation: rig repo d09ec7b1 2026-07-14 17:54:39 host 'rig' tag ao-verify (8 B); mini repo 916fa844 2026-07-14 21:58:48 host 'mini' tag ao-verify2. They use synthetic hostnames ('rig'/'mini') different from the real snapshot hosts ('cachyos'/'macmini'), so restic forget's default host+paths grouping puts each in its own group where keep-daily always retains it — they will persist forever as junk unless manually forgotten. Cosmetic, but they also pollute 'restic snapshots --latest 1' output (they appear as a separate latest snapshot per host).

### L58. Orphan empty bucket 'bucket-rustic' (apparent typo of bucket-restic) — 0 files, no lock, no lifecycle

**Host:** backblaze-b2 · **Component:** bucket-rustic · **Auditor:** flow:backups


A third bucket exists in the account: bucket-rustic (id 26aef2674aa534fe9efe0a1e), allPrivate, SSE-B2, fileLock disabled, zero file versions. Name is one letter off from bucket-restic — almost certainly a creation typo left behind. Dead path/junk; also a footgun (a future config typo pointing a repo at it would 'work' silently against an unprotected bucket).

### L59. NAS timezone is US/Pacific while the fleet/operator timezone is America/New_York — all DSM schedules fire 3h later than Eastern wall-clock

**Host:** nas · **Component:** system timezone · **Auditor:** flow:backups


ssh nas 'date' returns PDT and /etc/localtime -> /usr/share/zoneinfo/US/Pacific, but the secrets vault _meta.timezone says America/New_York and every other host runs Eastern (rig timer shows EDT). Practical effects: Hyper Backup 'daily 19:10' actually runs 22:10 Eastern, Immich dump '02:30' runs 05:30 Eastern, HA backup tars named 04.45 (Eastern-derived HA time) carry 01:45 NAS mtimes, and log/mtime correlation across hosts is skewed by 3h. Could be deliberate but nothing documents it; likely a set-up-time leftover.

### L60. Crash core dumps littering /volume1 root: qbittorrent-nox (x2), Plex Transcoder, python, snmpd — evidence of past process crashes, never cleaned

**Host:** nas · **Component:** DSM system / crash artifacts · **Auditor:** flow:backups


The /volume1 root contains compressed core dumps: '@Plex Transcoder.synology_geminilake_920+.72806.core.gz', two '@qbittorrent-nox...core.gz', '@python...core.gz', '@snmpd...42661.core.gz'. Two qbittorrent-nox cores suggest a repeat-crashing DSM qbittorrent package; the Plex Transcoder core may relate to the ongoing metadata/analysis load. These are junk (disk + signal noise) and worth a look at what crashed and when before deleting. Also noted: /volume1/vault is an empty share (28K, only #recycle/@eaDir) — dead path, unsurprisingly excluded from Hyper Backup.

### L61. wiki-drift check FAILING in today's daily run: committed generated wiki pages are stale vs fresh regeneration

**Host:** mini · **Component:** wiki-drift check / generated wiki pages · **Auditor:** flow:coverage-tripwire


Second of the two failures in the 14:16Z daily run: '[FAIL] wiki-drift (warn) — wiki generated pages in sync with sources (same-commit rule)' with output 'WIKI DRIFT: committed generated pages are stale vs a fresh regeneration.' Guards task wiki-05. Given the tracker/wiki-is-source-of-truth mandate, this is real drift to review (regenerate + commit via the documented gen scripts), not a flaky check — it recovered/regressed alongside git-hygiene checks that recovered this run.

### L62. macOS AppleDouble junk files shipped to /opt/verification (bin/._llm-triage.sh, skills/._docker-triage.md)

**Host:** mini · **Component:** /opt/verification deploy hygiene · **Auditor:** flow:coverage-tripwire


The rsync deploy from the operator's Mac carried AppleDouble resource-fork files into the live verification tree: /opt/verification/bin/._llm-triage.sh and /opt/verification/skills/._docker-triage.md. Harmless today but they are junk, get chmod 755'd by the deploy step's 'chmod 755 bin/*.sh', and will multiply on future Mac-side rsyncs unless --exclude='._*' (or COPYFILE_DISABLE=1) is added to the README deploy command.

### L63. Fast-tier dead-man ping URL is not recorded in the secrets vault — exists only in mini:/etc/verification/env

**Host:** mini · **Component:** secrets vault (.handoff-secrets.yaml) healthchecks inventory · **Auditor:** flow:coverage-tripwire


The vault's healthchecks section records verification_mini_ping_url and verification_quick_mini_ping_url but has no entry for the fast tier; verification-fast.service pings ${VERIFY_FAST_PING_URL} sourced from /etc/verification/env only. The healthchecks check 'verification-fast-mini' (schedule 600s) exists and is up, so monitoring works, but the vault — the documented single source for creds/URLs — cannot reproduce the fast tier's dead-man wiring on a mini rebuild. Small inventory/DR gap in the same spirit as the tree-drift finding.

### L64. Dead path: Roomba (192.168.10.231) onboarding failed with bad credentials on 2026-06-27 and was never completed — no config entry exists

**Host:** ha (192.168.10.50) · **Component:** roomba integration (abandoned) · **Auditor:** flow:ha-deep


8 log entries (4 ERROR 'Bad username or password', 4 WARN 'Not authorised') from roombapy during a config-flow attempt on 2026-06-27; the config-entry list contains no roomba entry, so the attempt was abandoned. There is a Roomba on the LAN at 192.168.10.231 that HA cannot talk to. Either finish pairing with fresh BLID/password or drop the intent; also generated 'blocking call inside event loop' warnings from the roomba config flow (upstream, cosmetic).

### L65. Matter server + integration loaded with ZERO devices/entities (idle dead weight); one 'Connection failed' on 2026-07-03; matter server add-on has a pending update

**Host:** ha (192.168.10.50) · **Component:** matter integration · **Auditor:** flow:ha-deep


The matter config entry is state=loaded and the Matter Server add-on runs, but the device registry has no matter devices and the entity registry no matter entities — nothing uses it (Thread also loaded, likely for the same future use). One transient 'Unexpected exception: Connection failed' on 2026-07-03 (server restart, recovered). update.matter_server_update=on means an add-on update is pending. Harmless, but it is a running service serving nothing.

### L66. Pending updates: HA Core, HA OS and Matter Server all have updates available (running core 2026.6.4)

**Host:** ha (192.168.10.50) · **Component:** core/OS updates · **Auditor:** flow:ha-deep


update.home_assistant_core_update=on, update.home_assistant_operating_system_update=on, update.matter_server_update=on; only the Supervisor is current (off). Maintenance-window work; noting for drift tracking.

### L67. /api/error_log (and /api/error/all) return 404 on core 2026.6.4 — any monitoring/scripts that scrape the REST error log will silently fail

**Host:** ha (192.168.10.50) · **Component:** REST API surface · **Auditor:** flow:ha-deep


Both classic REST log endpoints 404 with a valid admin token (the same token reads /api/config/config_entries fine, so it is not an auth problem). Error visibility now requires the WebSocket system_log/list command (worked via foss-setup/scripts/ha/haws.py) or Supervisor log endpoints. If anything in the verification stack still curls /api/error_log, it has been getting 404s.

### L68. Four compiled __pycache__ .pyc files are tracked in git despite __pycache__/ being ignored

**Host:** macbook (local repo) · **Component:** .gitignore / git index · **Auditor:** repo:junk-deadpaths


git ls-files -i -c shows 4 .pyc files under foss-setup/scripts/docs/__pycache__/ (apply-workstream-sequencing, generate-task-overrides, migrate-to-tracks, sync-rollout-with-plan — all cpython-314) committed before __pycache__/ was added to .gitignore and never de-indexed. Compiled junk in history/index; needs git rm --cached (not done — read-only pass).

### L69. agent-fix-tasks.md is stale, superseded junk that still points at the retired index.html tracker

**Host:** macbook (local repo) · **Component:** repo root / agent-fix-tasks.md · **Auditor:** repo:junk-deadpaths


47 KB root file, last commit 2026-07-08. Its own header says 'partially superseded — live status now tracked as the audit-fixes track in foss-setup/docs/index.html (Plan v3)' — but index.html was retired 2026-07-14 (wiki is source of truth), so its pointer is now doubly dead. The 2026-07-06 audit remediation it specs is long executed. Candidate for deletion (history keeps it).

### L70. keynote.html is an unrelated one-off ('Apple Hearth' marketing page) tracked at repo root

**Host:** macbook (local repo) · **Component:** repo root / keynote.html · **Auditor:** repo:junk-deadpaths


26 KB standalone HTML marketing/keynote mock ('Apple Hearth — Your digital life. Finally yours.'), last commit 2026-07-08, referenced by nothing in scripts/configs/wiki. Pure leftover creative one-off in an ops repo root.

### L71. Generated wiki roadmap index still claims it mirrors the retired docs/index.html

**Host:** macbook (local repo) · **Component:** scripts/docs/gen-roadmap-pages.py + generated wiki roadmap · **Auditor:** repo:junk-deadpaths


gen-roadmap-pages.py's docstring (line 4) and its emitted page text (line 67) still say the roadmap is 'mirrored from `docs/index.html` + `docs/progress.json`', and that text is live in the published wiki page foss-setup/wiki/docs/roadmap/index.md line 3 — even though index.html was retired 2026-07-14 (line 17 of the same script acknowledges this). Every wiki rebuild re-bakes the stale claim; visitors are pointed at a non-existent source of truth.

### L72. Four dead stack dirs on mini: dependency-track, litellm, tdarr (empty) + maintainerr (orphaned data/sqlite)

**Host:** mini · **Component:** /opt/stacks (dead stack dirs) · **Auditor:** repo:junk-deadpaths


ls /opt/stacks shows 35 dirs vs 38 running containers covering ~31 stacks. Dead dirs with no container: dependency-track (empty — service retired 2026-07-11), litellm (empty — the never-deployed 'mini fallback' phantom, now stripped to an empty dir), tdarr (empty — removed from plan 2026-07-08), maintainerr (only data/ with maintainerr.sqlite + logs + overlays left; removed from plan 2026-07-08). frigate has compose staged but is documented NOT DEPLOYED (intentional); recyclarr is a weekly cron `docker compose run` (not dead); backups/wiki are non-container dirs. The 4 dead dirs are host junk. litellm-phantom is a known memory item; the empty dependency-track/tdarr dirs and orphaned maintainerr sqlite are newly logged.

### L73. Dependency-Track fully retired live, but vault creds + 3 repo code references remain

**Host:** macbook (local repo) + fleet · **Component:** dependency-track remnants · **Auditor:** repo:junk-deadpaths


Live state: NO dtrack anywhere — mini /opt/stacks/dependency-track is empty, NAS has no /volume1/docker/dependency-track dir, Caddyfile has no deptrack site block (comment mentions only), no wiki services page generated. Remnants: (1) vault .handoff-secrets.yaml lines 132-135 keep a dtrack: section with creds + url https://deptrack.tabaska.us for a service that no longer exists (credential hygiene: delete/rotate); (2) scripts/nas/apply-compose-restart-policy.sh:43 still `compose_up /volume1/docker/dependency-track` (harmless — compose_up skips missing dirs — but dead path); (3) scripts/docs/gen-wiki-services.py keeps 'dependency-track' in its URL map (line 68) and Monitoring & Ops CATEGORIES (line 96); (4) stale prose mentions in service-enrichment.yaml (homepage), homepage/compose.yaml and caddy/.env.example comments.

### L74. Homepage LiteLLM tile still describes the phantom 'mini fallback for resilience' `known-issue`

**Host:** macbook (local repo) · **Component:** homepage config (stacks/homepage/config/services.yaml) · **Auditor:** repo:junk-deadpaths


The LiteLLM tile (services.yaml line ~177-181) says 'LLM gateway (mini fallback for resilience)' — the mini fallback was never deployed (catalog itself notes 'NEVER deployed — decision pending', and mini's litellm dir is now empty). The tile's href/siteMonitor correctly point at rig (llm.tabaska.us / 192.168.10.12:4000), so only the description text lies. Matches the known 'LiteLLM on mini is a phantom' memory item.

### L75. service-catalog.yaml has no llama-swap entry and stale ollama/maintainerr notes after the 2026-07-15 ai-01 ship

**Host:** macbook (local repo) · **Component:** service-catalog.yaml (docs drift post ai-01) · **Auditor:** repo:junk-deadpaths


Caddy serves llamaswap.tabaska.us -> rig:9292 (added ai-01 2026-07-15) and verification/coverage/rig.containers lists llama-swap, but service-catalog.yaml (which feeds gen-wiki-services) has no llama-swap entry, and its ollama entry still reads 'Native Ollama API (verified up 2026-07-07). Rig runs 24/7.' with no mention of the demotion to HA/Obsidian compat shim. Separately, the maintainerr catalog entry claims 'Compose kept for reference' but no maintainerr compose exists anywhere in the repo (find returns nothing) nor on mini (only data/). Catalog = wiki source, so this drift propagates to published docs.

### L76. Two scripts still cite the retired handoff docs as their rationale reference

**Host:** macbook (local repo) · **Component:** scripts (retired-handoff comments) · **Auditor:** repo:junk-deadpaths


scripts/uptime-kuma/seed-monitors.sh:13 ('Status-code choices were probed live 2026-07-09 (see handoff)') and scripts/docs/gen-wiki-services.py:52 ('Known URL overrides (handoff key-URLs)') point readers at handoff docs that were retired (handoff = memory + wiki now). Comment-only dead pointers; the scripts themselves work. All other retirement sweeps came back clean: no ollama-on-mini references anywhere (all ollama refs target rig), and subtree topology mentions are historical comments only (publish-deploy.sh HISTORY note; wiki-drift-check.sh intentionally supports both layouts).

### L77. Published wiki roadmap shows a negative open count (ops track: -2) and todo.md summary arithmetic is off (165+43+18+10=236≠234)

**Host:** macbook (local repo) · **Component:** tracker/wiki: generated roadmap + todo.md · **Auditor:** repo:tracker-wiki


Root cause: sbom-01 and sbom-04 are members of BOTH progress.json done and retired (intentional per _meta.note: 'left in done as completed setup work, feature retired'). gen-roadmap-pages.py computes open = len - done - retired - deferred per track, double-subtracting the 2 dual-status tasks, so wiki/docs/roadmap/index.md line 23 renders '| ops | 24 | 20 | -2 | 2 | 4 |' — a user-visible negative Open cell on wiki.tabaska.us. gen-todo.py similarly double-counts them in the summary line (165 done + 43 open + 18 deferred + 10 retired = 236 for 234 tasks). Generators should treat status as mutually exclusive (e.g. retired-and-done counts once).

### L78. media-03/media-04 are 'REMOVED FROM PLAN — won't-do' but sit in done instead of retired; seed-12 was 'declined' in the meta note yet remains open

**Host:** macbook (local repo) · **Component:** tracker: status classification · **Auditor:** repo:tracker-wiki


media-03 (Maintainerr) and media-04 (Tdarr) steps open with 'REMOVED FROM PLAN 2026-07-08 — won't-do' yet both are in progress.json done, inflating completed_count by 2 and rendering ✅ done on the wiki roadmap for features that were explicitly rejected — retired is the accurate bucket (the sbom precedent). Separately, _meta.note 2026-07-14 records 'seed-12/seed-13 (Bitmagnet, Whisparr) similarly declined'; seed-13 was later reversed and built, but seed-12 is still tracker-OPEN with no un-decline note, so the tracker's next-up list contradicts the recorded decision.

### L79. Generated roadmap index still says it mirrors 'docs/index.html' — retired 2026-07-14

**Host:** macbook (local repo) · **Component:** wiki: gen-roadmap-pages.py output · **Auditor:** repo:tracker-wiki


wiki/docs/roadmap/index.md line 3 (baked into gen-roadmap-pages.py's idx template) reads 'mirrored from `docs/index.html` + `docs/progress.json`'. index.html was retired 2026-07-14 (per memory + README); the script's own docstring was updated but the emitted page text was not, so the live wiki points readers at a nonexistent tracker. One-line fix in the generator + regen.

### L80. tracker-meta.json has no programmatic consumer and is already drifting (trackMeta missing the 'ai' track)

**Host:** macbook (local repo) · **Component:** tracker: docs/tracker-meta.json · **Auditor:** repo:tracker-wiki


tracker-meta.json (tierMeta/trackMeta/runMeta/aiHandoffMap, extracted from the retired index.html) is referenced only in prose (README.md:80, wiki operations/tracker.md:10); no generator or script reads it — grep across *.py/*.sh/*.html finds zero code consumers. It is not being maintained: tasks.json now has 21 tracks but trackMeta lacks the 'ai' track added with the ai-01 initiative. Dead-ish data; either wire it into the roadmap generator (track titles/subs) or mark it archival.

### L81. foss-analogue-progress-2026-07-05.json is a byte-identical duplicate of progress-backup-2026-07-05.json; two older superseded backups also retained

**Host:** macbook (local repo) · **Component:** tracker: docs/ junk files · **Auditor:** repo:tracker-wiki


cmp confirms the two 07-05 files are identical (4055 bytes each, exported one minute apart). progress-backup-2026-06-28.json and -2026-07-03.json are explicitly superseded per the 07-05 _meta note and use the pre-fix-16 schema (done as list, partial_or_deferred/next_up) that nothing reads; all three reference the retired 'Import via docs/index.html' flow. Harmless history but pure junk in docs/ — candidates for deletion or an archive/ subdir. Untracked docs/.DS_Store present on disk but gitignored (not in the index).

### L82. Leftover detached-HEAD worktree .claude/worktrees/libreseerr-diagnosis-34241d still registered, holding a pre-retirement repo snapshot (incl. docs/index.html)

**Host:** macbook (local repo) · **Component:** git: stale worktree · **Auditor:** repo:tracker-wiki


git worktree list shows a second worktree at .claude/worktrees/libreseerr-diagnosis-34241d pinned to c1f98d3 (detached), a leftover from a past Libreseerr diagnosis session. It contains the retired docs/index.html and old handoff-rollout-state.md, which pollutes repo-wide greps (it matched several searches in this audit). Excluded from git status via .git/info/exclude, so it is invisible junk. 'git worktree remove' when convenient (not done — read-only pass).

### L83. Two iCloud conflict-copy dupes live in wiki/docs and will be rsynced to the published wiki as orphan pages

**Host:** macbook (local repo) · **Component:** wiki: docs tree hygiene · **Auditor:** repo:tracker-wiki


wiki/docs/reference/scripts/backup/'restore-test-sh 2.md' and setup/'install-haos-vm-sh 2.md' exist on disk — the iCloud '* 2.md' duplication class already documented in operator memory. They are gitignored ('* [0-9].*', .gitignore:24) so the repo stays clean, but build-wiki.sh rsyncs the whole wiki/ tree to the mini, so both dupes get built and served on wiki.tabaska.us as out-of-nav orphan pages (they are the only 2 orphans). Not on this pass's known-issues list; the durable fix (exclude repo from iCloud) remains with the operator. Safe local cleanup: delete the two files.

### L84. Two junk cron entries execute nothing useful: btabaska runs a DIRECTORY nightly; root runs the retired pterodactyl scheduler every minute

**Host:** mini · **Component:** crontabs (btabaska + root) · **Auditor:** repo:live-drift


btabaska crontab line '0 0 * * * /home/btabaska/bin' points at a directory (drwxrwxr-x, Feb 2024) — cron forks it and fails every midnight; dead entry. root crontab runs 'php /var/www/pterodactyl/artisan schedule:run' EVERY MINUTE for a pterodactyl panel installed Jul 2025 that is fully retired: no wings container, no ptero systemd units, no caddy route — 1440 pointless php executions/day (plus the leftover /etc/cron.d/php and phpsessionclean.timer that exist only to serve it). Both entries are faithfully mirrored in hosts/macmini/crontabs.txt (the manifest matches live exactly — so this is live junk, not manifest drift). The recyclarr weekly sync cron is legitimate and its healthchecks ping (recyclarr-sync-mini) is up.

### L85. Four orphan stack dirs with leftover .env but no compose (litellm, dependency-track, tdarr, maintainerr) + unused whisparr image + an elapsed one-shot timer still enabled

**Host:** mini · **Component:** /opt/stacks dead paths + misc junk · **Auditor:** repo:live-drift


Dead live paths from retired/never-deployed services, all with .env files dated Jun 27: /opt/stacks/litellm (the documented 'LiteLLM on mini' phantom — never deployed, real LiteLLM is rig-only), /opt/stacks/dependency-track (dtrack retired 2026-07-11 per group_vars comment; the secrets vault still advertises dtrack url https://deptrack.tabaska.us with no live backend on mini — no caddy route found), /opt/stacks/tdarr (its Caddyfile route is commented out), /opt/stacks/maintainerr (.env + data/, no compose, no container). None of these have repo counterparts, and none have containers — pure junk that also feeds noise risk into the recursive manifest grep. Additional junk: ghcr.io/hotio/whisparr:latest image is pulled on mini but whisparr runs on the NAS — unused image; media-window-maint.timer (OnCalendar=2026-07-11 one-shot, Persistent=false) already fired and can never fire again but is still 'enabled'. Repo-side dead configs: none found — every repo stack dir has a live counterpart (adguard-nas maps to NAS, identical; configs/docker-stack/alternatives/{dockhand,pihole} are an explicitly-shelved alternatives dir).

### L86. Installed ansible-pull.timer on both mini and rig is an older comment revision than the repo copy (schedule itself identical)

**Host:** mini+rig · **Component:** ansible-pull.timer unit files · **Auditor:** repo:live-drift


The repo's configs/ansible/ansible-pull.timer header was rewritten (rig-is-24/7 wording, 2026-07-08 era) but the deployed /etc/systemd/system/ansible-pull.timer on BOTH hosts still carries the old 'On-demand rig ... wake hook' comments. Functional directives (OnCalendar=04:20, RandomizedDelaySec=30m, Persistent=true) are unchanged — cosmetic drift only, but it shows unit files aren't converged by the pull flow (nothing in site.yml installs these units; they're hand-copied per the file's own header). ansible-pull.service files match the repo exactly on both hosts.

### L87. Stale vault entry (deluge.port 58846 vs live 3254) and hosts/ manifests exist only for macmini (rig has no export-manifests.timer)

**Host:** repo · **Component:** foss-setup/.handoff-secrets.yaml + hosts/ manifests coverage · **Auditor:** repo:live-drift


(1) The secrets vault says deluge port 58846 but the live daemon listens on 3254 (core.conf daemon_port=3254, deluged bound to 0.0.0.0:3254); the wiki already documents 3254 and calls 58846 a stale-docs gotcha — the vault never got the fix. (2) export-manifests.sh is 'designed for every host' but hosts/ contains only macmini; the rig has no export-manifests.timer at all, so rig package lists/timers/crontabs are not captured in git (reproducibility gap that overlaps known issue 7 but is a distinct mechanism). The macmini manifests themselves are CURRENT: systemd-timers.txt lists the same 28 units as live, crontabs.txt and cron.d-listing.txt match live byte-for-byte.

### L88. Fast-tier ntfy pages are titled 'Verification [None tier]' — tier label uses args.host even for --tier runs

**Host:** mini · **Component:** bin/checks_runner.py (ntfy titles) · **Auditor:** repo:verification-suite


checks_runner.py builds the notification tag as `tier = f" [{args.host} tier]" if filtered else ""`. For the scheduled fast tier (--tier fast, no --host) args.host is None, so every fast-tier transition page reads 'Verification [None tier]: N NEW failure(s)' — confusing at page time (it hides which tier fired). Cosmetic but it is the primary crit-outage alert channel.

### L89. Scheduled quick tier runs with --host (operator-override semantics) so it would resurrect enabled:false checks; 5 media checks also run twice per cycle

**Host:** mini · **Component:** verification-quick.service semantics · **Auditor:** repo:verification-suite


checks_runner treats --host as an operator action and deliberately includes disabled checks; --tier respects `enabled`. But verification-quick.service is a SCHEDULED unit using `--host url`, `--host docker-fleet`, `--host media` — so any future `enabled: false` check in those domains/hosts would keep running and paging hourly, contradicting the documented --tier design intent. No live impact today (the only disabled check, sys-seedbox-ssh, is host:local/domain:system). Separately, the 5 host:url checks in media.yaml (sonarr/radarr queue-stuck, pipeline-health, indexer-redundancy) match BOTH `--host url` and `--host media`, so they execute twice per hourly cycle with independent transition state (results-url.json total=19 includes them; results-media.json total=14 includes them again) — duplicate probes and potential double transition pages.

### L90. skills/ is live (consumed by llm_triage.py) but carries stale environment facts, and 5 of 12 domains have no mapped skill (generic fallback)

**Host:** mini · **Component:** skills/ (LLM triage prompts) + DOMAIN_SKILL map · **Auditor:** repo:verification-suite


All 5 skill files are wired (DOMAIN_SKILL + system-triage.md default) — none orphaned. But their 'self-contained environment facts' have drifted: docker-triage.md says 'mini cannot SSH to it [rig]: tailnet ACL' (mini→rig SSH works since 07-09 and several host:rig checks depend on it); dns-triage.md calls the NAS secondary resolver 'Known-broken; guarded by task dns-02' (dns-02 closed, resolver live per dns.yaml header); system-triage.md says 'Tailscale connects mini, nas, rig, seedbox, HA' (HA is not on the tailnet); backup-triage.md claims /etc/crontab is unreadable on the NAS (the passing alert-dsm-* checks grep it as btabaska). Wrong facts degrade verdict quality by design (prompts are the model's only context). Also DOMAIN_SKILL maps only dns/mini-services/nas-services/rig/backups/git-hygiene/system — alerting, docker-fleet, ha, media, network (35 checks incl. the complex media pipeline probes) fall back to the generic system-triage.md. Moot until the 404 bug (separate finding) is fixed, but both should be corrected together.

### L91. README materially stale (LLM endpoint, 'Known state 2026-07-07', no quick/fast tiers, no ack flow, no dead-man drop-in) and an AppleDouble junk file sits in /opt/verification/bin

**Host:** mini · **Component:** verification/README.md + env.example + junk file · **Auditor:** repo:verification-suite


README documents only the daily 07:15 timer and says the LLM default is ollama :11434 / qwen3-coder:30b (now a 404 — llm-triage.sh default moved to :9292 / qwen3.6-35b-a3b). It omits: verification-quick + verification-fast tiers (installed and running for days), the ack-check.sh suppress flow, the tier/--notify runner flags, and the healthchecks drop-in on verification.service. Its 'Known state (2026-07-07)' section describes failures (dns-nas-*, backup-immich-dump-fresh) that now pass. env.example carries the dead LLM endpoint too. Junk: /opt/verification/bin/._llm-triage.sh — a 163-byte executable macOS AppleDouble left by an scp (the same artifact class that crashed the runner from checks.d on 2026-07-10; harmless in bin/ but junk). Repo __pycache__/ is properly gitignored.

### L92. Confirmed: no [[whisparr]] block in unpackerr.conf although whisparr is download-touching — currently zero-impact (whisparr has never downloaded anything)

**Host:** nas · **Component:** unpackerr · **Auditor:** gap:NAS unpackerr — live wedge state and archive-extraction backlog never quantified (only 1 case evidenced)


unpackerr.conf covers sonarr/radarr/lidarr/readarr only; no [[whisparr]] and no [[folder]] blocks. The compose file explicitly lists whisparr among the download-touching services that mount /seedbox and share the same Deluge client + remote path mapping, so any rar'd adult release whisparr grabs will never be extracted and will strand in its queue. However the gap is latent today: whisparr 2.2.0.108 has history totalRecords=0, queue totalRecords=0, and its library dir /volume1/stash/root/whisparr is empty (0 rar files, no content). Fix is a one-block config addition whenever whisparr goes live, using its API key from /volume1/docker/whisparr/config/config.xml.

### L93. Seedbox residue: ~20 extraction leftovers delete_delay never cleaned + 8 orphaned Animaniacs (2020) rar releases for a series that is not in Sonarr

**Host:** seedbox · **Component:** seedbox files/tv (deluge + unpackerr cleanup) · **Auditor:** gap:NAS unpackerr — live wedge state and archive-extraction backlog never quantified (only 1 case evidenced)


Of the 55 rar'd release dirs in files/tv, 20 still contain the extracted mkv next to the archive even though the corresponding episodes were imported (e.g. the 6 Archer releases imported 2026-07-10; unpackerr's delete_delay=10m should have removed the extracted copies afterwards). These duplicates burn seedbox quota; the rars themselves must stay (seeding, delete_orig=false by design). Separately, 8 Animaniacs.2020.* release dirs (S01E02-E13, S02E04/E05, plus the Andor S01E00 'A Disney Day Special Look' special) sit unextracted or part-extracted, and 'Animaniacs (2020)' does not exist as a Sonarr series (only the 1993 Animaniacs, id 231) — so no arr will ever import or clean them; the Andor special (S01E00) maps to a special Sonarr will not grab. Dead data with no owner.

### L94. Unpackerr liveness is invisible to every external monitor: port 5656 unpublished, no Uptime-Kuma monitor, no healthchecks entry — only the in-container healthcheck consumed by the sudo-SSH containers-health-nas sweep

**Host:** nas · **Component:** unpackerr monitoring · **Auditor:** gap:NAS unpackerr — live wedge state and archive-extraction backlog never quantified (only 1 case evidenced)


The [webserver] metrics endpoint added after the 2026-07-10 two-day wedge listens on 0.0.0.0:5656 but the compose service publishes no host port, so nothing off-box can probe it (curl from LAN returns an empty response). Uptime-Kuma monitors every other NAS media service by HTTP (NAS Sonarr/Radarr/Lidarr/Readarr/Prowlarr/FlareSolverr/Whisparr/Plex/Stash) but has no unpackerr monitor; healthchecks (192.168.10.2:8001) has no unpackerr entry either. The only consumer of unpackerr's health is verification/checks.d/docker-fleet.yaml check 'containers-health-nas' (runs from mini, sudo docker ps over SSH, flags unhealthy/restarting containers). That path is currently green — verification-* healthchecks entries are 'up' (verification-fast-mini last ping 2026-07-16T11:55:31Z), so no NAS container is unhealthy, which is the best available read-only confirmation that unpackerr is up. Net: unpackerr is indirectly monitored for the wedge class, but a direct external probe of its metrics is impossible; publishing 5656 (LAN-only) or adding a kuma HTTP monitor would close the gap.

### L95. 2 monitored Sonarr series sit on the unmanaged 'Any' quality profile, bypassing all recyclarr/TRaSH custom-format scoring

**Host:** nas · **Component:** sonarr · **Auditor:** gap:recyclarr (custom-format / quality-profile sync to radarr+sonarr) — deployed and monitored but never audited for sync correctness


Archer (2009) (id 261) and Players (2022) (id 262) are monitored but assigned quality profile 'Any' (id 1), which recyclarr does not manage (only 1 nonzero CF score vs 37 in the managed WEB-1080p profile, cutoffFormatScore 0). Grabs for these two series ignore the TRaSH junk-blocking scores (LQ, x265(HD), BR-DISK, scene/tier scores), so they can pull low-quality or junk releases despite the otherwise fully-synced setup. The other 160 series use the managed profile. Likely just profile-assignment drift when the series were added.


---

## INFO (113)

### I1. wiki-rag-sync failed 4x on Jul 15 with OWUI embedding-dimension mismatch (768 vs 1024), then recovered by recreating the collection; timer's first scheduled run is tomorrow 05:14

**Host:** mini · **Component:** wiki-rag-sync.service (ai-01) · **Auditor:** host:mini


The new wiki-rag-sync unit failed 4 times this morning: Open WebUI rejected adds with 'Collection expecting embedding with dimension of 768, got 1024' (the known OWUI reindex-doesn't-rebuild-dims gotcha from the ai-01 rollout). At 11:44 a run recreated collection homelab-wiki (448325ab-...) and synced all 242 docs successfully (exit 0). The timer has never fired on schedule yet (LAST n/a, NEXT Thu 05:14:44) — today's runs were manual/ad-hoc. State is healthy now; first unattended run tomorrow is the real test.

### I2. Persistent swap usage: 1.9Gi of 4Gi swap in use on the 8GB box (RAM 3.2Gi used + 4.3Gi cache, 192Mi free)

**Host:** mini · **Component:** memory / swap · **Auditor:** host:mini


With 38 containers plus the dead Pterodactyl LEMP stack (mariadb, redis, php-fpm, nginx) the 7.6Gi box keeps ~1.9Gi swapped. Load is trivial (0.06/0.24/0.30) and 4.0Gi is 'available', so this is likely cold pages, not active thrash — but it means there is no headroom, and retiring the Pterodactyl stack (see separate finding) would recover real RAM. Top RSS: node ~200MB, python3.13 ~184MB, AdGuardHome ~174MB, node ~153MB, celeryd workers ~140MB+111MB, java ~131MB.

### I3. ~9.3GB reclaimable docker data: 6.8GB unused images (14 of 48), 838MB dangling volumes (8 of 15), 1.65GB build cache

**Host:** mini · **Component:** docker disk usage · **Auditor:** host:mini


docker system df shows 33% of image space, 82% of volume space, and 100% of build cache reclaimable. Root disk is only 24% used (91G/402G) so there is no pressure — this is hygiene, not urgency. The 8 dangling local volumes are worth an owner review before any prune (could hold data from retired stacks like maintainerr/tdarr/litellm).

### I4. All 4 CIFS mounts currently healthy; one 180s NAS stall + 6 'malformed interface info' kernel messages in the past week (transient)

**Host:** mini · **Component:** CIFS mounts to NAS · **Auditor:** host:mini


All four CIFS mounts (/mnt/share/Games, /mnt/nas-youtube, /mnt/nas/music ro, /mnt/nas-music-rw) stat and list fine — no stale/EBADF state. Note /mnt/nas-music-rw appears in findmnt but not in plain df output (df dedupes the second mount of //192.168.10.4/music; verified alive via stat+ls). Journal shows one 'CIFS: VFS: \\192.168.10.4 has not responded in 180 seconds. Reconnecting...' event plus 6 'parse_server_interfaces: malformed interface info' (benign Synology SMB quirk) and one FS-Cache duplicate-cookie warning over 7 days — all recovered; soft mounts + the x-systemd.automount self-heal pattern are doing their job.

### I5. Clean bill elsewhere: 38/38 containers Up with RestartCount=0, no failed units, unattended-upgrades ran today, 0 pending security updates (119 non-security), NTP synced, ansible-pull + restic succeeded today

**Host:** mini · **Component:** docker containers / updates / time / ansible-pull · **Auditor:** host:mini


docker ps -a: all 38 containers Up (none exited/restarting/unhealthy); docker inspect shows RestartCount=0, OOMKilled=false for every container. systemctl --failed: 0 units. unattended-upgrades enabled and completed 06:44 today (vim/wget/httplib2 etc.). apt simulation: 119 upgradable packages, 0 from security pockets — normal for security-only auto-updates, but a moderate non-security backlog. timedatectl: clock synchronized, NTP active (host runs UTC). ansible-pull.service finished cleanly 13:54:08 today; restic-backup.service last exit 0 at 12:57:48. dmesg tail shows only benign docker veth churn matching the 15:05 export-manifests run — no hardware/fs errors.

### I6. All disks SMART-normal and cool; system temp 63C under warning threshold

**Host:** nas · **Component:** disk health / SMART / thermals · **Auditor:** host:nas


Unprivileged smartctl is blocked (Permission denied) but the DSM Storage API (read session as btabaska) reports all three disks healthy: sata1 WD120EMFZ 39C, sata2 WD161KFGX 38C, sata3 ST18000NM002J 38C — each smart=normal, status=normal, health=normal. All three btrfs volumes status=normal (vol3 43% / vol2 23% / vol1 9% used). System board temp 63C with temperature_warning=False. No SMART/thermal concerns at this time.

### I7. beets, soularr, stash, whisparr, rreading-glasses are all LIVE — none abandoned (rreading-glasses dir is DB-only by design)

**Host:** nas · **Component:** docker service inventory · **Auditor:** host:nas


Task asked whether these dirs are stale/abandoned. All are active: beets ran a scheduled import today (import.log 'import started Wed Jul 15 06:15:12'); soularr fires every 5 min (see stuck-import finding); stash answers HTTP 200 in the health log and stash/config mtime 07-14 17:52; whisparr/config mtime today 09:15; rreading-glasses has a running postgres (ps shows 'postgres: rreading-glasses ... idle') and its dir intentionally holds only the DB (app config lives in media-automation/docker-compose.yml, image pinned by digest). @eaDir bloat is negligible (music/photo @eaDir 24K each, docker/@eaDir 4K).

### I8. S3 Hyper Backup ran on schedule last night — inodedb freshness marker is current `known-issue`

**Host:** nas · **Component:** Hyper Backup / off-site DR · **Auditor:** host:nas


Two DSM tasks (id=11 daily 19:10, id=12 daily 21:10, both 'S3 Backup enc' -> dsmbackup --backup 3) drive the B2 Hyper Backup. Freshness signal per the DR notes = last_version_inodedb mtime, which is 2026-07-14 19:12 (54MB), matching the 19:10 daily run — so the off-site job is executing. Task Status shows 'Not Available' in synoschedtask (DSM app-task quirk, not a failure). Note this remains the bucket-hyper-backup that per known issue 6 has NO Object Lock and client-side encryption OFF.

### I9. Root partition 69% full and moderate swap/memory pressure — worth monitoring, not urgent

**Host:** nas · **Component:** memory / root partition · **Auditor:** host:nas


DSM system partition /dev/md0 is at 69% (1.5G used / 2.3G, 707M free) — normal but trending; worth watching so a full / does not break DSM. Memory: 433MB free of 19.8GB with 16.7GB in buff/cache and 1.29GB swap in use; kswapd0 has accumulated 228 min CPU since Jul 2, indicating steady (not alarming) reclaim pressure under Plex + *arr + postgres + rclone load. Load average 2.4-2.9 on this 4-core box, driven partly by a live Plex transcode + credits/thumbnail scan at capture time.

### I10. 5h-ago boot was a clean operator reboot, not a crash

**Host:** rig · **Component:** system/boot · **Auditor:** host:rig


Boot at 2026-07-15 06:50:56 followed a clean shutdown of the previous boot (same kernel 7.1.3-2-cachyos on both sides; prev boot Jul 14 17:43 came right after the -Syu). last -x shows a proper 'shutdown' record at 06:50 (crashes in this box's history show 'crash' instead), previous-boot journal ends with orderly unmounts of /home, /srv, /tmp, and operator tty sessions were active 06:45-06:46 (inside the 4-7AM maintenance window). coredumpctl: 'No coredumps found' in last 36h; the shutdown-time 'Failed to send coredump datagram: Broken pipe' at 06:49:58 was systemd-coredump racing shutdown, cosmetic.

### I11. Music-mirror timer conflict is RESOLVED on-box: rsync unit retired, single transcode-mirror unit remains, ALAC files intact `known-issue`

**Host:** rig · **Component:** nas-music-mirror.service / ~/Music · **Auditor:** host:rig


Known issue 2 (05:00 transcode vs 05:30 rsync --delete-after fighting) no longer matches live state. Only ONE unit pair exists: nas-music-mirror.timer -> nas-music-mirror.service ('Mirror NAS music library -> ~/Music as iPod-playable ALAC/MP3', runs /home/btabaska/bin/nas-music-to-alac-mirror.sh); the unit file comment explicitly says the healthcheck ping was 'inherited from the retired rsync music-mirror.service'. No user timers exist (systemctl --user list-timers: 0). ~/Music contains 0 FLAC, 1928 .m4a, 1472 .mp3 (58G) — the transcodes were NOT wiped. Last runs: Jul 14 17:45->17:57 success (full transcode pass, 40G memory peak) and Jul 15 05:01 success (1s no-op). Dead-man ping to health.tabaska.us fires only on success.

### I12. AER error rate is ZERO this boot; OS NVMe SMART clean (1% used, 0 media errors) — note drive is a WD SN750-class WDS200T3X0C, not SN570 `known-issue`

**Host:** rig · **Component:** OS NVMe @ 74:00.0 / PCIe AER · **Auditor:** host:rig


Known issue 3 currently quiet: 0 kernel AER messages since boot (5.5h), and the pcie-aer-monitor timer (every ~20min) reports corr=0 fatal=0 crit=0x00 on every run, ntfy alert never fired. SMART on /dev/nvme2 (= PCI 74:00.0 per boot log, the btrfs root device): PASSED, Percentage Used 1%, Available Spare 100%, Media and Data Integrity Errors 0, Error Information Log Entries 0, 37C, 43.1TB written, 5793 POH. Unsafe Shutdowns lifetime counter is 523 (consistent with this box's crash history, not incrementing abnormally now). Minor doc drift: memory/known-issue calls it 'SN570' but the device at 74:00.0 is WDS200T3X0C-00SJG0 (WD Black SN750 2TB SKU). Reseat/replace remains open per known issue, but nothing degrading today.

### I13. pacman sync-db staleness RESOLVED: full -Syu completed 2026-07-14 17:38 (121 pkgs), sync dbs ~19h old; 140 new updates already pending (rolling churn) `known-issue`

**Host:** rig · **Component:** pacman · **Auditor:** host:rig


Known issue 4 (stale sync db blocking installs / glue-02 / foss-02) is cleared as of yesterday: pacman.log shows 'starting full system upgrade' at 2026-07-14T17:38:29 with 121 packages upgraded and no errors in the transaction tail, followed by reboot into the new kernel 7.1.3-2-cachyos at 17:43. Sync dbs in /var/lib/pacman/sync are dated Jul 14 (cachyos.db 17:16, extra.db 17:13) — ~19h old at audit time, well within safe install range. checkupdates already reports 140 pending updates, which is normal CachyOS rolling-repo churn but means the db will re-stale within days; the 404-on-install risk returns if installs are attempted after mirrors purge again.

### I14. Overall system health good: disks 57%, 0 failed units, all 9 containers healthy with 0 restarts, GPU idle at 42C, btrfs error counters all zero

**Host:** rig · **Component:** system resources / docker / GPU / filesystems · **Auditor:** host:rig


df: btrfs root (nvme2n1p2) 1.9T at 57% (805G free), /boot 70%. Memory 8.3Gi/62Gi used, 51Gi cache, swap 3.4Gi (zswap-normal). Load 2.40 is explained by PalServer-Linux at 91.6% CPU (Palworld game server, expected) + tailscaled 20%. systemctl --failed: 0 units (system and user). 14 system timers, all with successful last runs except the already-reported ansible-pull 04:22 failure; restic-backup last fired Jul 15 01:40 with no error-level output. Docker: 9/9 containers Up 4-5h, RestartCount=0 across the board, all defined healthchecks 'healthy' (open-webui, palworld, llama-swap, litellm-db). GPU: RTX 3090 Ti, driver 610.43.03, 42C, 3% util, 643/24564 MiB, 20W, no stuck processes. Sensors nominal (CPU pkg 33C, NVMe composites 27-37C, all under thresholds). btrfs device stats /: write/read/flush/corruption/generation errors all 0; no BTRFS/ext4/I-O error lines in this boot's dmesg.

### I15. Deluge session healthy: 375 torrents all Seeding, 0 Error, 0 stuck>7d, 0 tracker errors; reaper cron working; no disk-full risk

**Host:** seedbox · **Component:** Deluge session + reaper + quota · **Auditor:** host:seedbox


RPC (127.0.0.1:3254, daemon 2.2.0 / libtorrent 2.0.13) reports 375 torrents ALL in Seeding state — 0 Error, 0 with 0-seed stuck >7d, 0 tracker errors sampled. Upload 208 KB/s, DHT 378 nodes, incoming connections OK. Label plugin ENABLED with the full post-import flow (sonarr/sonarr-imported, radarr/radarr-imported, lidarr/lidarr-imported, readarr); by-label: sonarr 257, sonarr-imported 84, radarr-imported 13, readarr 7, etc. deluge-reaper cron (05:00 daily) is healthy and logging '0 eligible' correctly — oldest torrent is sonarr Simpsons S09 at 12.8d, still under the 14d threshold. Disk: filesystem 65% (11T/17T shared); user quota 1479G used of 2862G soft / 2909G hard (~52%); deluge get_free_space reports 5.8T free. No disk-full risk. Sonarr queue on NAS is 0 (no arr queue-clog).

### I16. HA is LAN-only: 8123 open on LAN, ha.tabaska.us absent from public DNS, no external_url, not on tailnet

**Host:** ha (192.168.10.50) · **Component:** network exposure (port 8123) · **Auditor:** host:ha


Port 8123 answers on the LAN IP. ha.tabaska.us resolves to 192.168.10.2 (mini/caddy) only via the local split-horizon wildcard; public resolvers return NXDOMAIN/empty, so nothing on the internet routes to HA. /api/config external_url=None. HomeKit bridge port 21064 is also open on LAN (expected, HASS Bridge:21064). No public exposure found.

### I17. Known issue 8 is HALF-STALE: automatic encrypted backups are now live and succeeding (fixed 2026-07-13); HACS still not installed `known-issue`

**Host:** ha (192.168.10.50) · **Component:** backup · **Auditor:** host:ha


Backups are no longer absent: daily 04:45 encrypted backups to BOTH agents (hassio.local eMMC + hassio.nas_backups CIFS //192.168.10.4/backups), retention 3 copies, password set. Last automatic backup completed 2026-07-15T04:45:01-04:00 (today), agent_errors={}, both copies protected=True, next scheduled 2026-07-16T04:45. Backup manager idle, event entity shows event_type=completed. The other half of known issue 8 remains true: HACS is NOT installed (absent from 184 loaded components).

### I18. 139 total entities; 47 unavailable/unknown, but 28 of those are cosmetic 'unknown' (scenes never activated, buttons never pressed)

**Host:** ha (192.168.10.50) · **Component:** entities overview · **Auditor:** host:ha


Breakdown of the 47: 21 scene.* 'unknown' (scene state = last-activated timestamp; never activated = unknown, normal), 4 button.* 'unknown' (never pressed, incl. 2 Elgato identify + 2 restart), tts.google_translate 'unknown' and conversation.home_assistant 'unknown' (normal for these domains). Real problems reduce to the 11 btiphone sensors + 8 Hue bulbs reported separately. No integration is wholesale down.

### I19. Zero automations configured — nothing to trigger or error

**Host:** ha (192.168.10.50) · **Component:** automation · **Auditor:** host:ha


The automation component is loaded but there are no automation.* entities at all: this HA instance runs no automations (it is a device-control/scene/HomeKit-bridge box only). Consequently no automation errors exist; the 'any that error?' question is vacuously clean. Worth knowing: presence (person.brandon_tabaska) and 73 lights exist but nothing acts on them automatically.

### I20. Ollama integration to rig is loaded and actively used (last conversation today 10:29 UTC); rig Ollama answers `known-issue`

**Host:** ha (192.168.10.50) + rig (192.168.10.12) · **Component:** ollama shim (Assist LLM) · **Auditor:** host:ha


Config entry ollama 'http://192.168.10.12:11434' state=loaded; agent entity conversation.rig_ollama_assist state timestamp 2026-07-15T10:29:54Z (used this morning). rig Ollama daemon responds (version 0.30.8). Default Assist pipeline remains the intent engine conversation.home_assistant (state unknown = never conversed, by design so device control keeps working). Shim healthy.

### I21. HomeKit bridge live on :21064; one unpaired pair-verify attempt from off-subnet client 192.168.1.79 on 2026-07-13

**Host:** ha (192.168.10.50) · **Component:** homekit bridge · **Auditor:** host:ha


HomeKit config entry 'HASS Bridge:21064' loaded and port 21064 accepts connections. System log shows a single pair-verify attempt from 192.168.1.79 with an unknown pairing uuid — an unpaired (or previously-paired-to-old-bridge) client. Note the source IP is on 192.168.1.x, not the home 192.168.10.x/20.x scheme, suggesting a device with a stale/foreign address or the iPhone during pairing churn; per operator notes the iPhone pairing to this bridge was still pending as of 07-13. One occurrence, not recurring.

### I22. Libreseerr local patch and digest pin verified intact (KI-10 healthy) `known-issue`

**Host:** mini · **Component:** libreseerr container/image · **Auditor:** svc:request-layer


Container config image is ghcr.io/zamnzim/libreseerr@sha256:820134e4... which matches the compose pin and the local image's RepoDigest (image ID c2dbf74a...); app.py and readarr.py are bind-mounted read-only from /opt/stacks/libreseerr/. Logs (400 lines) show no 500s; one harmless openlibrary 422 on a 2-char search. Login + /api/requests work. The pinned-digest-vs-image-ID mixup documented in compose comments is resolved as described.

### I23. Seerr core is healthy: connected to NAS Radarr/Sonarr/Plex, sync jobs running on schedule, 0 pending/failed requests; update available (v3.2.0 -> newer)

**Host:** mini · **Component:** seerr (container, config, jobs) · **Auditor:** svc:request-layer


seerr v3.2.0 (Up 5 days, healthy): settings point at 192.168.10.4:7878/8989/32400 (both arr defaults, non-4k), 400-line log window has zero errors/warnings — Plex Recently Added scans complete every 5 min, Watchlist Sync every 3 min. Request counts: 23 total, 0 pending, 0 declined, 8 approved/processing (all dissected in other findings), 15 completed; recent requests (21-23, 2026-07-11..13) flowed end-to-end to AVAILABLE, proving the radarr/sonarr/plex connections and availability updates work. All 11 jobs have future nextExecutionTime, none wedged 'running'. /api/v1/status reports updateAvailable:true (Radarr on the NAS likewise warns v6.3.0 available) — routine update debt, not a fault.

### I24. musicseerr config sane: env-var API-key workaround in place, Lidarr sync succeeding, healthy container

**Host:** mini · **Component:** musicseerr config · **Auditor:** svc:request-layer


v1.4.2, Up 45h healthy. The documented encrypt-but-never-decrypt config.json bug workaround is correctly deployed: LIDARR_API_KEY provided via ./.env and absent from config.json (only a .bak-encrypted-key remnant from 07-10 remains). lidarr_settings shows last_sync_success=true at epoch 1784056643 (2026-07-14, within the 24hr sync_frequency). Plex integration enabled against 192.168.10.4:32400 library 3. Logs show no errors. Note: /api/requests requires session auth and no musicseerr credentials exist in .handoff-secrets.yaml (auth_users live in library.db via provider login) — request state was audited directly from the SQLite DBs instead.

### I25. Scanner healthy: ND_SCANNER_SCHEDULE active, hourly scans succeeding, zero EBADF/CIFS errors, library count matches NAS `known-issue`

**Host:** mini · **Component:** navidrome · **Auditor:** svc:media-aux


ND_SCANNER_SCHEDULE='@every 1h' confirmed in container env (the 0.62 fix from the known Navidrome scan-config issue is in place, ND_SCANNER_WATCHERWAIT=0 as intended). Scans run hourly; last successful scan 2026-07-15T16:17:19Z (555.6ms). Zero 'error' or 'EBADF' lines in the entire docker log since the 07-13 container start; /mnt/nas/music CIFS ro mount has x-systemd.automount. Count check: DB has 3476 media_file rows, 70 flagged missing, 2 in #recycle -> 3406 present; filesystem count is 3404 audio files excl. #recycle + 2 in #recycle = 3406. Exact match.

### I26. Tautulli connected to Plex now; heavy connection-error bursts 07-13/07-14 correlate with the Plex analysis storm; zero errors today `known-issue`

**Host:** mini · **Component:** tautulli · **Auditor:** svc:media-aux


API cmd=server_status returns connected:true and get_activity works (0 streams). Rotated log (07-02 -> 07-13) contains 5664 ERROR lines ending in WebSocket 'Connection refused' and 503 'Plex Media Server is currently running startup maintenance tasks' at 07-13 16:12; current log has 44 ERRORs, last burst 07-14 12:58-13:22 (read timeouts to 192.168.10.4:32400 /status/sessions + plex.tv ping). 0 ERROR lines dated 2026-07-15. Consistent with known issue #1 (Plex bulk-ingest analysis storm draining); Tautulli itself is healthy.

### I27. MeTube healthy: last download completed end-to-end (video -> mp3 to Navidrome YouTube folder); correctly wired to bgutil-pot; one benign DRM-skip warning

**Host:** mini · **Component:** metube · **Auditor:** svc:media-aux


Log shows the most recent job ('Numb ... Linkin Park', kXYiU_JCYtU) downloaded fully and post-processed to /audio (= /mnt/nas-music-rw/YouTube, indexed by Navidrome). Its Dockerfile pip-installs bgutil-ytdlp-pot-provider + yt-dlp pre-release, and YTDL_OPTIONS points youtubepot-bgutilhttp at http://bgutil-pot:4416 — confirmed working (that download generated POTs on 07-08). One WARNING: 'Some tv client https formats have been skipped as they are DRM protected' (upstream yt-dlp issue #12563, non-fatal — download succeeded). No errors since; idle since the 07-09 container restart.

### I28. Paperless healthy but completely empty: 0 documents, 0 mail accounts; mail-fetch task is a scheduled no-op

**Host:** mini · **Component:** paperless-ngx · **Auditor:** svc:docs-life


The 5-container stack (paperless 2.20.11, tika 3.2.1, gotenberg 8.21, postgres 17, redis 7) is up 5 days and clean: 0 failed tasks (235 recent tasks all SUCCESS), no OCR errors anywhere in log history, consume dir empty (no stuck files), media dir contains only media.lock. However documents_total=0 and there are zero configured mail accounts, so 'Check all e-mail accounts' runs every 10 minutes and returns 'No new documents were added' as a no-op — scheduled email fetch is not actually configured. Only errors in full log history are redis connection-refused bursts exactly at the 07-09 11:23/16:29 stack restarts (shutdown ordering noise, not ongoing). Instance appears deployed-but-unused.

### I29. Vaultwarden clean: signups disabled (verified live), admin panel token-gated and reachable, zero failed logins, no icon-fetch spam

**Host:** mini · **Component:** vaultwarden · **Auditor:** svc:docs-life


SIGNUPS_ALLOWED=false confirmed both in /opt/stacks/vaultwarden/.env and in the running container's environment (docker inspect). https://vault.tabaska.us/alive returns 200; GET /admin returns 200 with the admin-token login prompt (not open). Full log history contains no 'incorrect password' lines (count 0), no icon-fetch errors, no errors at all — only clean SIGTERM/restart cycles on 07-09 and a version probe on 07-14. Version 1.36.0, healthy 5 days.

### I30. Mini AdGuard is the LAN-primary resolver and healthy; NAS AdGuard only serves NAS-local traffic; note: mini admin password differs from vault's adguard entry

**Host:** mini · **Component:** adguardhome · **Auditor:** svc:infra-mini


Mini AdGuard (v0.107.77, protection on) is actively serving real LAN clients: 84,480 queries, top clients 192.168.10.2/.253/.186 + ~7 more LAN IPs; sole upstream udp://unbound:5335 (avg 43ms), no fallback_dns configured. Last 1000 queries (16-min window): 998 NOERROR, 2 NXDOMAIN, 0 SERVFAIL. Error log is quiet (113 lines/7d: benign TCP resets from .186 plus one transient unbound i/o-timeout burst 2026-07-14 18:56 affecting 3 queries — with no fallback DNS those queries failed). NAS AdGuard (:3000) is also live but ALL 52,290 of its queries come from 172.23.0.1 (its own docker bridge), upstream Quad9 DoH — so it serves NAS containers only, not LAN clients. Vault gap: mini AdGuard admin password is Wbef#90332 (vault only has adguard_nas with a different password; no mini entry).

### I31. Unbound clean: only cosmetic startup warnings (so-rcvbuf sysctl, subnetcache) and no runtime errors in 7 days

**Host:** mini · **Component:** unbound · **Auditor:** svc:infra-mini


Log since last start (2026-07-09) contains only repeated startup warnings: 'so-rcvbuf 4194304 was not granted. Got 425984' (host net.core.rmem_max too small for the configured buffer — cosmetic under this load) and 'subnetcache: serve-expired/prefetch ... not working for subnet module cache' (config-option noise). 12 warn lines total in 168h, zero resolution errors. One transient stall on 2026-07-14 18:56 was visible only from AdGuard's side (3 query timeouts). Single point of DNS failure for the LAN since AdGuard has no fallback upstream (see adguard finding).

### I32. Caddy overall healthy: certs renewing (LE, expiries Oct 2026), 7-day 5xx total = one transient whisparr 502 + one homepage widget 500; all other 42 vhosts respond

**Host:** mini · **Component:** caddy · **Auditor:** svc:infra-mini


Full vhost sweep through caddy (42 of 44 routes) returned expected 2xx/3xx/401 codes, including seedbox (deluge/slskd via tailscale IP), rig (ai/llm/ollama/amp/apollo/mcpo — mcpo root 404 is normal FastAPI, /docs=200), NAS *arr stack, metube, wiki (static content served). Access-log aggregation over 168h shows only: 1x 502 whisparr.tabaska.us at 2026-07-15T00:25Z ('dial tcp 192.168.10.4:6969: connection refused' — whisparr now answers 302), 1x 500 home.tabaska.us Lidarr widget proxy 2026-07-14T16:30Z, and 121 'aborting with incomplete response' warns (client-closed stash/plex video streams — benign). Zero ACME/renewal errors; sampled certs (seerr/git/romm/ntfy) are Let's Encrypt, notAfter Oct 6-7 2026. Tdarr and Frigate vhosts are commented out with dated rationale (deliberate, not dead routes).

### I33. ntfy, dockge and bedrock-connect all clean: no auth failures, no errors; bedrock-connect healthy 2h after image bump (v2.7.8)

**Host:** mini · **Component:** ntfy / dockge / bedrock-connect · **Auditor:** svc:infra-mini


ntfy v2.19.2: 7 days of logs contain only per-minute stats lines and daily visitor resets — 0 auth failures, 0 publish failures (messages_published=157, emails_*_failure=0, 3 users, 6 active topics, 1 subscriber). dockge 1.5.0: 34 log lines in 7 days, zero errors, UI 200 via caddy. bedrock-connect (diun-bumped image built 2026-07-14, v2.7.8, openjdk 26-ea base): started 14:23 UTC today, RestartCount=0, health=healthy, mc-monitor healthcheck exec exiting 0 every 30s, loaded its 2 custom servers (192.168.10.12:19132 + bedrock.tabaska.us:1111), listening 0.0.0.0:19132; only benign netty sun.misc.Unsafe deprecation warnings on the new JVM.

### I34. Healthchecks: all 11 checks up, all wired to the single ntfy channel, none paused/never-pinged; health.tabaska.us is the same instance (identical UUIDs)

**Host:** mini · **Component:** healthchecks · **Auditor:** svc:monitoring-stack


Full check list (status/last_ping UTC): ai-stack-rig up 16:20, verification-fast-mini up 16:25, music-mirror-rig up 09:01, restic-backup-mini up 12:57, immich-dump-nas up 09:30, restic-backup-rig up 05:40, ansible-pull-mini up 13:54, ansible-pull-rig up 13:55, recyclarr-sync-mini up 07-12 03:00 (weekly, next due 07-19), verification-mini up 14:16, verification-quick-mini up 15:41. Every check has channels=2bf0e736... ('ntfy (self-hosted)'). No check has never pinged; none paused/late/down right now. The public route https://health.tabaska.us returns the same 11 checks with identical UUIDs, confirming it is the same instance behind caddy. Minor cosmetic: verification-fast-mini has an empty slug.

### I35. restic-backup-mini flipped DOWN 07:45Z -> UP 12:57Z today — tail of the known restic 0.12/Object-Lock 401 failure, now recovered; first unattended 0.19.1 run is tonight `known-issue`

**Host:** mini · **Component:** healthchecks / restic-backup-mini · **Auditor:** svc:monitoring-stack


The 01:41 UTC nightly on mini failed to signal (restic 0.12 apt binary vs B2 Object Lock -> 401, per known issue), healthchecks marked it down at 07:45:03Z and ntfy delivered the DOWN alert at 03:45 EDT; after the 0.19.1 fix a successful run pinged at 12:57:48Z and the UP alert was delivered at 08:57 EDT. Flip history also shows a down/up on 07-09. restic-snapshot-fresh-mini now PASSES in the 14:16 UTC sweep. The systemd restic-backup.timer next fires 2026-07-16 01:34 UTC — that will be the first unattended run on 0.19.1, worth watching.

### I36. ntfy delivery chain verified end-to-end: healthchecks, uptime-kuma, beszel, both diuns, and verification all authenticate and publish successfully; iOS upstream relay configured

**Host:** mini · **Component:** ntfy delivery chain · **Auditor:** svc:monitoring-stack


ntfy v2.19.2 healthy (up 5d, host port 8080). Token audit proves each producer works: healthchecks token last used TODAY 08:57 EDT (restic UP alert), diun-mini today 06:00, diun-nas today 06:30 (from 192.168.10.4), verification today 10:41, uptime-kuma 07-11 04:34 EDT (exactly matching kuma's last real DOWN event at 08:33Z 07-11 — proves kuma alerting fired), beszel 07-09, rig-aer 07-09, nas-health 07-14 13:00 EDT. ACLs sane: admin rw-all with per-service tokens, 'phone' user read-only * + rw wake-rig, anonymous denied. 16 cached messages in the last ~7h all well-formed. Server stats show subscribers=1 (single live subscriber — presumably the phone via upstream relay; verification's alert-ntfy-upstream-relay check PASSes).

### I37. Beszel hub 0.18.7: all 3 agents (mini/nas/rig) connected and reporting within the last minute; 9 alert rules (Status/Disk 85%/Memory 90% per system), none triggered

**Host:** mini · **Component:** beszel · **Auditor:** svc:monitoring-stack


systems collection shows nas, mini, rig all status=up with 'updated' timestamps within ~60s of query time. Alert rules exist for each system: Status (min 5m), Disk 85%, Memory 90% — all triggered=false. Hub and mini agent both 0.18.7, up 5 days. Only caveat is the dead email path reported separately.

### I38. Both diun instances healthy: mini ran today 06:00 (35 images, 0 failed), NAS ran today 06:30; both notified ntfy successfully. NAS diun found pending updates: lidarr 3.1.0, prowlarr 2.4.0, valkey:9 digest

**Host:** mini + nas · **Component:** diun (both instances) · **Auditor:** svc:monitoring-stack


mini diun 4.33.0 (healthy, up 5d): cron '0 6 * * *', runs 07-10..07-15 all 'Jobs completed ... failed=0'; today found romm:4.9.2 (new watch after yesterday's bump) and a bedrock-connect update — both published to ntfy at 06:00:07/08 EDT. NAS diun 4.33.0 (schedule '30 6 * * *', TZ set in container): diun.db mtime = 06:30 EDT today; three notifications landed on ntfy at 06:30:05-09 EDT (valkey:9 digest change, lidarr:3.1.0 updated, prowlarr:2.4.0 updated) and the diun-nas token authenticated from 192.168.10.4 at 06:30 — full chain working without docker access on the NAS. Note for operator: the NAS lidarr/prowlarr/valkey image updates are detected but not yet applied.

### I39. All 53 active kuma monitors currently up (none paused, none down); this morning's rig reboot (06:44-07:30 EDT flapping) never crossed the 3-retry threshold so no DOWN events fired

**Host:** mini · **Component:** uptime-kuma monitors · **Auditor:** svc:monitoring-stack


Latest heartbeat per active monitor: all status=1 at 16:28 UTC. 'Rig MCPO' shows '404 - Not Found' but is intentionally up (accepted_statuscodes includes 404). During the rig reboot window (uptime -s 06:50:56) monitors 30-34/45/49-51/54 logged Pending EHOSTUNREACH/ECONNREFUSED with retries resetting before max=3, so no down/notification — by design, though it means sub-3-minute outages are invisible. NAS Lidarr/Prowlarr briefly ECONNREFUSED at 10:28 EDT (arr restarts) — also recovered within retries. No monitors with active=0; monitor ids 1, 9, 52 deleted historically.

### I40. Phantom-request signature: 6 of 11 recently grabbed albums tied to monitored=False artists/albums, but all completed — no active phantom `known-issue`

**Host:** nas (192.168.10.4) · **Component:** lidarr · **Auditor:** svc:arr-stack


30-day history shows 12 grabs across 11 albums. 6 involve unmonitored entities: Chappell Roan (artistMon False), Sabrina Carpenter x2 (artistMon False), Olivia Rodrigo x3 (BOTH albumMon and artistMon False). All 6 are at 100% trackfiles and queue is empty, so no 'Downloading 0%' phantom exists right now. However 3 artists remain monitored=False, so future MusicSeerr batch requests against them can re-trigger the known class. Broader context: 930/1252 albums unmonitored (918 at 0% tracks) — normal add-artist-unmonitored noise, not phantoms.

### I41. Sample-junk import scan clean: 0 of last 30 imports under 100MB; prior sample.avi was purged 07-14 `known-issue`

**Host:** nas (192.168.10.4) · **Component:** radarr · **Auditor:** svc:arr-stack


All 24 distinct movies from the last 30 downloadFolderImported events have files 4.8–24.6 GB; no sub-100MB sample-junk imports. History also shows the previously known sample case self-healed: /movies/Spider-Man.Homecoming.2017.HDRip.XviD.AC3-EVO/sample.avi was deleted 2026-07-14T15:24 and replaced by a 13.7 GB Bluray import at 15:49. Known issue 13 currently not manifesting.

### I42. All 7 indexers enabled and RSS-healthy; IPT text search currently returns full results (known weak-search issue not manifesting at query level) `known-issue`

**Host:** nas (192.168.10.4) · **Component:** prowlarr + indexers · **Auditor:** svc:arr-stack


indexerstatus is [] (no disabled/failing/backoff indexers). All 7 indexers (IPTorrents, MyAnonamouse, SexTorrent, Zenith, RetroToon, OnlyEncodes+, BitPorn) enabled; last ~7h of history (500 events of 15,849 total) shows RSS firing on all 7 and 1 grab (Zenith). No failed queries in the sampled window. A one-off read-only search probe: IPT returned 100 results for 'matrix' vs Zenith 43 — IPT search itself works today; the known 'IPT-only search returns ~0 grabs' issue would be at the grab/quality-match layer, not raw search. All 5 apps fullSync'd from prowlarr.

### I43. Fleet-wide single download path: Deluge on betty only — no sabnzbd exists anywhere (briefing expectation is a phantom)

**Host:** nas + mini · **Component:** download client topology · **Auditor:** svc:arr-stack


All 5 arr apps have exactly one download client: Deluge at 185.162.184.38:5945 (betty). No sabnzbd client is configured in any app, and mini's /opt/stacks contains no sabnzbd stack at all — the 'sabnzbd on mini' expectation in the audit briefing does not match live state (no usenet path). Connectivity is demonstrably working: radarr grabbed Alien 1979 at 15:16 today and imported at 15:30; sonarr imported ~200 Phineas and Ferb episodes today. Single-client topology means Deluge/betty is a single point of failure for all acquisition.

### I44. Queues empty across all 6 apps; recent history clean (no failures in last 200 events except 6 stale readarr bookImportIncomplete from 06-28); no import lists configured

**Host:** nas (192.168.10.4) · **Component:** arr stack — queues/history/import lists · **Auditor:** svc:arr-stack


queue totalRecords=0 for sonarr/radarr/lidarr/readarr/whisparr. Last-200 history per app shows no downloadFailed/grabFailed loops: sonarr 200x downloadFolderImported (Phineas and Ferb bulk today), radarr 63 imports/62 grabs/28 upgrades-deletes, lidarr retag+import only, readarr 65 grabs/62 imports plus 6 bookImportIncomplete all dated 2026-06-28 (resolved since — later imports succeeded). importlist is empty in every app, so 'import list errors' cannot exist. Root folders all accessible=True with ample space (/tv 9.7TB free, /movies 8.9TB, /music + /readarr-library 14TB). Lidarr and prowlarr were restarted today at 14:28 UTC (others up since 07-11).

### I45. Plex analysis storm effectively drained; server fast, 0x 408/503, only credits pass still churning `known-issue`

**Host:** nas · **Component:** plex · **Auditor:** svc:nas-apps


Plex 1.43.3.10793 healthy: 0 active sessions, all 4 libraries scanned today (2026-07-15 morning), all probed endpoints answer in <=20ms with 200s. The 2026-07-13 bulk-ingest analysis storm has drained to a single serial background activity (credits detection walking TV episodes item-by-item, currently Phineas and Ferb S02). The current server log window (07:49-09:30 local, 47,956 lines) contains zero 408s and zero 503s. Butler tasks look sane (BackupDatabase enabled, DeepMediaAnalysis enabled, nothing stuck).

### I46. Immich v2.7.5 healthy; nightly pg dumps fresh with working 14-day retention

**Host:** nas · **Component:** immich · **Auditor:** svc:nas-apps


Immich answers ping/version on LAN and 200 via https://immich.tabaska.us. Nightly pg_dumpall via /volume1/docker/immich/immich-pg-dump.sh runs at 02:30 (today's dump present, 16.6MB, 8 consecutive days retained, retention pruning at 14 days per script), and the healthchecks 'immich-dump-nas' check is up (last ping 2026-07-15T09:30Z). Compose pins v2.7.5 with digest-pinned DB/Redis. Authenticated endpoints (/api/server/about, /storage, job queues) return 401 — no Immich API key exists in the vault, so internal job/queue state could not be audited.

### I47. CWA healthy: both Kobo sync tokens 200, ingest dir empty, no stuck queue, readarr bridge working

**Host:** nas · **Component:** calibre-web-automated · **Auditor:** svc:nas-apps


https://books.tabaska.us/login returns 200 (0.04s). Both Kobo sync endpoints (admin + kobo2 tokens) return 200 on GET /v1/initialization. Ingest dir /volume1/docker/calibre-web-automated/ingest is empty (no stuck files); cwa_ingest_retry_queue is 0 bytes; processed_books shows 5 imported / 2 converted / 0 failed; epub-fixer.log and log_archive are empty. The Readarr->CWA connect script (with the 2026-07-13 apostrophe/xargs bugfix in place) last ran successfully 07-13 ('Rosemary and Rue' copied). app.db WAL active as of today 09:31.

### I48. Known rig music-timer conflict appears RESOLVED: rsync mirror retired, only ALAC transcode timer remains `known-issue`

**Host:** rig · **Component:** music-mirror timers · **Auditor:** svc:nas-apps


Known issue 2 said two ~/Music timers fight (05:00 transcode vs 05:30 rsync --delete-after). Live state now shows only nas-music-mirror.timer (running nas-music-to-alac-mirror.sh, NAS->rig transcode) in list-timers; the unit's own comments describe the dead-man ping as 'inherited from the retired rsync music-mirror.service'. The healthchecks 'music-mirror-rig' check is up with last ping matching the 05:01 EDT run. The mirror direction is NAS->rig, so it cannot delete NAS-side files. An owner decision seems to have landed; memory/known-issue list is stale.

### I49. beets is live but the MeTube->beets YouTube-audio flow is essentially unused (one test download ever); quarantine dir empty

**Host:** nas · **Component:** beets / metube audio flow · **Auditor:** svc:nas-apps


beets container is up (web UI :8337 answers 200), daily 06:15 imports run on schedule (import.log entries every day 07-09..07-15), config is the approved tag-in-place/never-move design. But /volume1/music/YouTube — the MeTube audio landing + beets quarantine dir — is completely empty, and MeTube's history shows only a single test audio download ever ('Me at the zoo', ~2026-07-07). The beets DB hasn't changed since Jul 8 and daily imports find nothing. The dir mtime changed today 07:16 (the leftover test file was removed by someone/something un-audited). Flow is wired correctly end-to-end but idle — another 'green but unused' path per the monitoring-vs-reality theme.

### I50. All 'live-or-abandoned' candidate dirs are LIVE; whisparr is a day-old fresh deploy with empty library

**Host:** nas · **Component:** stash / whisparr / rreading-glasses · **Auditor:** svc:nas-apps


None of the audited dirs are abandoned: stash v0.31.1 up (GraphQL answers, job queue empty, config mtime 07-14); rreading-glasses answers 200 on :8788 with active postgres data (07-11) serving Readarr metadata; whisparr v2.2.0.108 up since 07-15 00:30Z with clean health, 4 Prowlarr-synced indexers (BitPorn, IPTorrents, RetroToon, SexTorrent), Deluge client enabled, empty queue, and its stash-scan.sh connect script in place — but the library at /volume1/stash/root/whisparr is empty (created 07-14 17:45, no imports yet, stash-scan never fired). Oddity: whisparr /api/v3/movie returns 404 (size 0) while system/status, health, queue, indexer, downloadclient endpoints all work; library enumeration was done via filesystem instead.

### I51. media-automation stack coherent: seedbox rclone mount healthy, invariants hold, healthchecks all up; minor junk files in dir

**Host:** nas · **Component:** media-automation · **Auditor:** svc:nas-apps


The rclone SFTP mount seedbox:/home/hd34/btabaska/files is mounted at /volume1/mounts/seedbox-files and browsable (books/manual/movies/music/slskd). unpackerr conf has all four *arr blocks with delete_orig=false and its webserver healthcheck enabled per the 07-10 wedge lesson. All 11 healthchecks are 'up' (restic mini/rig, immich dump, ansible-pulls, verifications, recyclarr weekly, music-mirror, ai-stack). .env PUID=1026/PGID=100 set. Junk: macOS AppleDouble files (._docker-compose.yml, ._README.md etc.) and an empty 'test-write' file from 07-02 litter /volume1/docker/media-automation and /volume1/docker/immich; soularr/beets/whisparr dirs carry .bak files by convention. DSM Task Scheduler jobs are opaque synoschedtask IDs (root-only) — the 02:30 immich dump and 15-min watchdog cadences are inferred from outputs, not task definitions.

### I52. AI-stack core path healthy: e2e completion via LiteLLM->llama-swap in 1.34s, DB connected, all 8 aliases + 9 backing models present

**Host:** rig · **Component:** litellm + llama-swap · **Auditor:** svc:ai-stack


llama-swap (host port 9292) healthy: /health=OK, /v1/models lists all 9 configured models with no metadata errors, /running=[] (correct idle state, TTL unloads working per log 'fast-3b Unloading model, TTL of 300s reached'). All GGUF files referenced by /home/btabaska/Documents/GitHub/local-ai-tooling/docker/llama-swap-config.yaml exist in /opt/llm/models. LiteLLM /health/readiness reports db connected; /v1/models returns all 8 aliases (coder, code, coder-strong, chat, chat-creative, fast, utility, embed). A tiny completion with the opencode key through alias 'utility' returned 200 in 1.34s wall (includes cold model load; generation itself 34ms). docker logs --tail 400 of llama-swap, litellm, open-webui, mcpo, litellm-db show no model-load failures, no OOM, no CUDA errors, no timeout loops; litellm-db's only 5 FATAL lines are benign 'terminating connection due to administrator command' at container restart times (07-14 21:42Z, 07-15 10:49Z). NOTE: full LiteLLM GET /health was deliberately skipped because it fires a live test-completion at every model entry, which would sequentially load/swap 7 large models through the GPU (disruptive); readiness + real completion used instead.

### I53. OWUI reachable via ai.tabaska.us; wiki RAG sync recovered from this morning's 768-vs-1024 dimension mismatch; retrieval verified live `known-issue`

**Host:** rig · **Component:** open-webui / wiki-rag-sync · **Auditor:** svc:ai-stack


https://ai.tabaska.us returns 200 via Caddy. The known 'reindex-doesn't-rebuild-dims' gotcha manifested today: wiki-rag-sync on mini failed at 11:23 and 11:33 UTC with 'Collection expecting embedding with dimension of 768, got 1024' (old nomic-dim collection vs new qwen3-embed 1024-dim), then recovered at 11:44 UTC by creating a fresh collection homelab-wiki (448325ab-...) and syncing all 242 wiki files (+242 ~0 -0 !0, exit 0). DB confirms 242 file attachments in knowledge_file. A live retrieval query ('navidrome scanner schedule') returned the correct wiki chunk, proving query-time embedding via LiteLLM 'embed' alias -> llama-swap qwen3-embed works. wiki-rag-sync.timer enabled, next run Thu 05:14 UTC (timer restarted 10:55 UTC today so 'last: n/a' is expected). open-webui log window (tail 400, ~7h) is clean: only per-minute Kuma GET / 200s. Note: GET /api/v1/knowledge/{id} returns files:null even though 242 files are attached (membership lives in the knowledge_file table in this OWUI build) — don't rely on that API field for monitoring.

### I54. No key-scanning; the only auth failures are mini's own hourly verification probe that deliberately expects 401

**Host:** rig · **Component:** litellm (auth) · **Auditor:** svc:ai-stack


In the 400-line log window (~7h) the only 401s are one per hour from 100.97.245.80 (= macmini's tailscale IP), generated by mini's verification-quick.service check 'rig-litellm' which curls /v1/models WITHOUT a key and accepts '^(200|401)$' ('401 without key = up' is the documented intent). Each probe also triggers an ERROR-level traceback line in litellm's log ('No api key passed in'), which is self-inflicted noise that could mask real auth-failure spam when eyeballing logs. Immediately after each 401 the same runner does an authenticated POST /v1/chat/completions -> 200 (the rig-ai-e2e real-completion check), so the e2e tier is genuinely exercising the stack hourly. No unknown source IPs appear anywhere in the window. Caveat: window is only ~7h; also note the LiteLLM UI is published publicly at llm.tabaska.us per the vault, which was not audited in this pass.

### I55. mcpo up and bridging fleet tools correctly, but no real tool consumption observed; per-minute Kuma probe of / returns 404 by design `known-issue`

**Host:** rig · **Component:** mcpo · **Auditor:** svc:ai-stack


mcpo serves its configured servers (time, fetch, sequential-thinking, context7, serena, fleet); /fleet/openapi.json returns 200 with the gpu_status route (verified hourly-to-10-minutely by mini's rig-mcpo-fleet-tools check, which exists precisely to catch the 'Up but bridge broken' UFW regression). However, in the entire tail-400 log window there is not a single actual tool invocation — traffic is exclusively: (a) Uptime-Kuma monitor 'Rig MCPO' GETting / every 60s and receiving 404 (mcpo has no root route; the monitor is configured to accept it and shows UP=1), and (b) verification probes of /docs and /fleet/openapi.json. So mcpo is healthy but idle — nothing (OWUI chats included) used its tools in the window, and the per-minute 404s are liveness-only monitoring noise (the monitoring-tests-liveness-not-correctness class), partially mitigated by the tool-route check. Also observed: mcpo re-creates an MCP transport session to fleet-mcp every ~10 min (each verification probe) and each attempt logs a 406 on the bare GET /mcp, which the check comments document as 'transport alive'; fleet-mcp memory stable at 22MB so no leak concern.

### I56. UFW docker->host 8765 gotcha still correctly configured; fleet-mcp active and reachable from the mcpo container

**Host:** rig · **Component:** fleet-mcp / UFW (docker->host 8765) · **Auditor:** svc:ai-stack


The ai-01 UFW regression class (docker containers unable to reach host port 8765) remains fixed: UFW is active with explicit ALLOW rules for 8765/tcp from 172.16.0.0/12 (docker), 10.201.0.0/16 (docker pool2) and 192.168.10.0/24 (trusted VLAN). fleet-mcp.service is active (running, 10h uptime, enabled), python listening on 0.0.0.0:8765, and the mcpo container (172.19.0.5) demonstrably reaches it — journal shows its transport sessions, and /fleet/openapi.json served through mcpo returns the tool schema (the exact end-to-end path the 2026-07-09 regression broke).

### I57. ai-stack-rig healthchecks ping fresh: last ping 5 min before audit, fed by ai-stack-watchdog.timer every ~10 min

**Host:** rig · **Component:** healthchecks (ai-stack-rig dead-man) · **Auditor:** svc:ai-stack


The ai-stack-rig check on healthchecks (grace 1500s = 25 min) is 'up' with last ping 2026-07-15T21:10:36Z, which matches to the second the last run of ai-stack-watchdog.timer on the rig (17:10:35 EDT). The dead-man wiring is alive and the whole AI stack's watchdog loop is functioning. All other checks in the healthchecks project are also 'up' (none late/down).

### I58. Known issue 5 is outdated for game data: rig restic explicitly backs up palworld saves+backups AND the full MinecraftCross01 instance; last run succeeded `known-issue`

**Host:** rig · **Component:** restic-backup (game-data coverage) · **Auditor:** svc:gaming


The documented state 'rig restic covers /etc + /home only; /opt not backed up except Palworld saves' understates coverage: /etc/restic/env BACKUP_PATHS also includes /opt/stacks/palworld/game/backups and the entire /opt/stacks/amp/config/.ampdata/instances/MinecraftCross01 dir (world + config + the 12G frozen zips). The nightly service ran today with Result=success and healthchecks restic-backup-rig is 'up' (last ping 2026-07-15T05:40:59Z). So the Minecraft world IS off-site (nightly), which partially mitigates the frozen AMP hourly backups. Memory/known-issue text should be refreshed.

### I59. AMP healthy: API login OK, 2 instances running, Advanced Lifetime licence present, sleep-mode trap defused (explicitly disabled) `known-issue`

**Host:** rig · **Component:** AMP (amp container / amp.tabaska.us) · **Auditor:** svc:gaming


https://amp.tabaska.us API login succeeded (needs Accept: application/json header — bare POST gets 'Invalid accept header value'). ADSModule/GetInstances: Main (ADS controller, Running=True) and MinecraftCross01 (Minecraft module, Running=True, AppState=20 Ready — not Sleeping/50), neither Suspended. Today's logs for both instances show 'Licence Present: AMP Advanced Edition - Lifetime Licence'. The sleep-mode trap is defused: activity log shows 'Changing setting MinecraftModule.Limits.SleepMode to False' and zero sleep/wake events in any AMP log. Minecraft reachable from LAN on TCP 25565; UDP 19132 (bedrock/Geyser) bound on host. Container amp Up 10h, 0 restart loops.

### I60. Palworld healthy: COMMUNITY=false confirmed (home-IP leak guard intact), 0 restarts, hourly save backups fresh, port bound on LAN

**Host:** rig · **Component:** palworld container · **Auditor:** svc:gaming


Container Up 10h, Health=healthy, RestartCount=0, no crash-loop or error lines (log tail is only REST /v1/api/info|players|metrics OK polls — homepage tile/healthcheck traffic). Env verified: COMMUNITY=false, PUBLIC_IP/PUBLIC_PORT empty, PORT=8211, RCON on 25575, BACKUP_ENABLED=true hourly with DELETE_OLD_BACKUPS after 30 days. Host is listening on 0.0.0.0:8211/udp and a UDP probe from the MacBook completed without ICMP-unreachable (UDP reachability is best-effort to verify). Container-level save backups are current: newest palworld-save-2026-07-15_17-00-00.tar.gz (2.7MB), hourly cadence intact; Saved dir 69M; both paths also in rig restic.

### I61. sabnzbd does not exist on mini — download path is Deluge-only; audit premise stale

**Host:** mini · **Component:** sabnzbd (absent) · **Auditor:** flow:movies-tv


No /opt/stacks/sabnzbd directory, no sab/nzb container (running or stopped), and neither Radarr nor Sonarr has any download client besides Deluge (185.162.184.38:5945, categories radarr/sonarr with radarr-imported/sonarr-imported post-import categories set). 'Recent sab failures / incomplete-dir disk space' is not applicable; mini root fs is at 24% (295G free) regardless.

### I62. Known Plex analysis storm appears fully drained: no running activities, 0 sessions, API fast, same-day scan+match for 07-15 import `known-issue`

**Host:** nas · **Component:** plex (analysis storm state) · **Auditor:** flow:movies-tv


Live state of known issue 1: /activities returns an empty container, /status/sessions size=0, all API probes responded promptly, and Alien (imported 07-15 15:30Z) was scanned AND agent-matched by 11:30 local same day. The only suspected residue is the two 07-14 imports that landed unmatched (separate finding). No 503s encountered during ~30 Plex API calls.

### I63. Pipeline currently healthy: 8/8 sampled imports on disk with sane sizes and playable in Plex; 5/5 seerr 'available' requests verified; queues empty; arr-plex-journey passes both

**Host:** nas · **Component:** end-to-end movie/TV flow verification · **Auditor:** flow:movies-tv


Sample of 8 recent imports (Alien, Terminator: Dark Fate, Madame Web, RRR; Phineas & Ferb S04E45 + S03E27, Bob's Burgers S08E01, House of the Dragon S03E04): all files exist at /volume2/movies|/volume3/tv (0.85-21.9GB, all > thresholds) and all resolve in Plex by tmdb/tvdb guid with playable Parts matching the exact file path. All 12 seerr requests marked available were checked via ratingKey for the 5 most recent (Backrooms, RRR, Bluey 154/154 eps with parts, The Raid 2, D.E.B.S.) — every one exists with Parts. Radarr and Sonarr queues: 0 records (nothing stuck). Repo checker verdicts: COVERAGE_OK radarr ratio=0.929 (169/182 in Plex, 13 missing = the sample/ISO/wrong-file/unmatched findings), COVERAGE_OK sonarr ratio=0.962 (125/130, 5 missing = the TV findings) — both pass the 0.90 threshold while the missing sets are precisely the broken items reported above (illustrates known issue 15's tolerance band).

### I64. Last 10 Lidarr imports fully verified end-to-end: files on NAS, present in Navidrome DB and Plex Music section

**Host:** mini + nas · **Component:** lidarr import -> NAS share -> navidrome + plex · **Auditor:** flow:music


Last 10 imported albums (6033 Maybe I'm Dreaming, 6035 Coco Moon, 6034 Cinematic, 5932 Hotel Diablo, 6031 All Things Bright and Beautiful, 6029 The Midsummer Station, 6030 Ocean Eyes, 6032 Mobile Orchestra, 5028 Death of Slim Shady, 5968 lost americana): Lidarr statistics show trackFileCount==trackCount for all 10; files exist at /volume1/music/<Artist>/<Album (Year)>/ on the NAS with matching track counts (e.g. Coco Moon 11, Cinematic 18, Hotel Diablo 14, Death of Slim Shady 19); fresh Navidrome DB copy shows each album with full non-missing media_file counts; Plex Music section (key 3) returns exactly 1 album hit for each of the 10 titles. Navidrome media_file total=3476, LastScanError empty. The musicseerr->lidarr->import->share->navidrome+plex pipe is healthy for completed work.

### I65. Known issue 14 mitigations confirmed live: ND_SCANNER_SCHEDULE=@every 1h active, hourly scans running, last scan 2026-07-15T20:17Z, watcher disabled `known-issue`

**Host:** mini · **Component:** navidrome scanner · **Auditor:** flow:music


Navidrome 0.62.0 container env has the correct new-style key ND_SCANNER_SCHEDULE=@every 1h (not legacy ND_SCANSCHEDULE) plus ND_SCANNER_WATCHERWAIT=0 (CIFS watcher intentionally off). docker logs show a scan starting every hour on the :17 for the last 48h with no errors; DB property LastScanStartTime=2026-07-15T20:17:19Z, library.last_scan_at=2026-07-15 20:17:21 (within the 1h window at audit time ~21:15Z), LastScanError empty. The 20:17Z scan imported 27 new tracks (Linkin Park/The Hunting Party), proving new NAS content flows in within an hour.

### I66. Known issue 2 (dueling ~/Music timers) is RESOLVED live: rsync unit retired, only the 05:00 transcode mirror remains, ALACs intact, this morning's run succeeded `known-issue`

**Host:** rig · **Component:** nas-music-mirror (systemd) · **Auditor:** flow:music


The conflicting 'music-mirror' rsync --delete-after unit no longer exists on the rig ('Unit music-mirror.timer could not be found'); only nas-music-mirror.timer (OnCalendar 05:00, Persistent) survives, running ~/bin/nas-music-to-alac-mirror.sh with a dead-man healthchecks ping — the unit file comment says the rsync unit was retired (media-06). ~/Music holds 1928 .m4a + 1472 .mp3 and 0 .flac; newest ALACs (Owl City Maybe I'm Dreaming, transcoded 2026-07-14 17:57) were NOT deleted this morning. 2026-07-15 run: timer LAST=05:01:14 EDT, service Result=success, healthchecks 'music-mirror-rig' status=up last_ping 2026-07-15T09:01:15Z. No ALAC leakage back to the NAS: the 160 .m4a under /volume1/music are source purchases (e.g. Sabrina Carpenter 'fruitcake'), matching Navidrome's 160 m4a rows; mirror is one-way NAS->rig. The known-issues list/memory note ('both enabled, awaiting owner decision') is stale and can be closed. Caveat: journalctl (even with sudo) returned no entries for the unit since 07-13 — likely volatile/rotated journal; run success is corroborated by systemctl show + the healthchecks ping instead.

### I67. MusicSeerr overall state: 14 requests (13 imported, 1 phantom), retry queue empty, Lidarr sync healthy at 2026-07-15T19:17Z

**Host:** mini · **Component:** musicseerr · **Auditor:** flow:music


request_history: 13 imported + 1 downloading (the 3OH!3 phantom). queue.db pending_jobs=0, dead_letters=0 (no stuck retry jobs). config.json lidarr_settings.last_sync=1784143043 (2026-07-15T19:17:23Z) with last_sync_success=True; Lidarr URL http://192.168.10.4:8686, root /music, Plex integration enabled against section 3. The v1.4.2 encrypted-API-key bug is worked around via LIDARR_API_KEY env as documented in the compose file. Note: the authenticated API/UI could not be exercised (no musicseerr creds in the vault, Plex login_enabled=False, auth tokens hashed in library.db) — request state was audited from the container's own sqlite store, which is what the UI renders.

### I68. CWA runs a third-party fork image ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7 from a 7-month-old GitHub account with a typosquat-style name — story verifies, but trust anchor is thin

**Host:** nas · **Component:** calibre-web-automated (container image supply chain) · **Auditor:** flow:books


The compose file documents a June 2026 decision to switch off upstream crocodilestick/calibre-web-automated (stalled at v4.0.6) to the community fork 'Calibre-Web-NextGen' by GitHub user 'new-usemame' for the CVE-2026-7713 fix (Kobo auth-token IDOR). Verification: CVE-2026-7713 is real in NVD (published 2026-05-04, affects crocodilestick CWA <=4.0.6, vulnStatus Deferred); upstream's last release is indeed v4.0.6 (2026-02-04); the fork repo exists (created 2026-05-02, 141 stars, 27 forks, active push 2026-07-15, 118 open issues) and the account ('nate', created 2025-12-06, 19 repos, 6 followers) predates the CVE. So this is a documented operator decision that checks out, not an obvious typosquat compromise — but the NAS books service (and the Kobo-facing endpoint on books.tabaska.us) now trusts images built by a young pseudonymous account whose name reads like 'new-username' with an rn->m swap. Worth periodic re-vetting on image bumps.

### I69. Delivered-book path is healthy: readarr clean, ingest pipeline empty/idle, last 5 imports all in CWA, both Kobo sync endpoints 200 JSON, apostrophe copy-script bug fixed 07-13

**Host:** nas · **Component:** books flow end-to-end (readarr -> ingest -> CWA -> Kobo) · **Auditor:** flow:books


Readarr: /api/v1/health returns [], queue empty, root folder /readarr-library accessible with 14.0 TB free; metadata source correctly points at http://rreading-glasses:8788 — that container answers on host port 8788 (/ 200, /v1/status 200, swagger UI) and its postgres data dir is present at /volume1/docker/rreading-glasses/postgres; lookups through it work. CWA ingest: /volume1/docker/calibre-web-automated/ingest is empty, cwa_ingest_status='idle', retry queue 0 bytes, processed_books/failed=0, imported=5 — nothing stuck. All 5 most recent readarr imports (Rosemary and Rue, Miranda and Caliban, Naamah's Curse [via the 262 mis-map], Kushiel's Chosen, Naamah's Blessing) are present in /volume1/books with epub+kepub. Kobo: both secrets endpoints return 200 application/json with valid sync payloads (admin: NewEntitlement objects incl. the 07-13 imports; kobo2: ChangedReadingState objects). The readarr-copy-to-cwa-ingest.sh apostrophe/xargs bug (silently dropped every Kushiel's/Naamah's title) was fixed 2026-07-13 per in-script changelog and post-fix apostrophe titles did reach CWA. libreseerr container logs since its 07-12 21:39 restart contain no errors and no 400/404 phantom-author signatures.

### I70. YouTube archive flow is healthy end-to-end; counts match 1:1 and Plex indexes new downloads within seconds

**Host:** mini + nas · **Component:** pinchflat -> NAS youtube share -> Plex YouTube library · **Auditor:** flow:youtube-photos


Pinchflat (mini, Up 6 days healthy) has 2 sources, both enabled: 'Yellow Cherry Jam' (index every 1440min, last_indexed 2026-07-15T00:23Z, 25/31 downloaded) and 'Kaji Pm' (index every 43200min=30d, last_indexed 2026-07-12, 1339/1371 downloaded). Downloads land on CIFS mount /mnt/nas-youtube/pinchflat (//192.168.10.4/youtube). NAS pinchflat dir holds exactly 1364 video files; Plex 'YouTube' section (key 4, path /volume1/youtube) totalSize is exactly 1364. Newest download (media_downloaded_at 2026-07-13T21:12:01Z) exists on NAS with mtime 21:12:02Z and appears in Plex with addedAt 2026-07-13T17:12:14 EDT (=21:12:14Z, 13s later). Newest items have real Media parts (3.7MB-2.0GB, valid durations) — not the 'green but not watchable' pattern. Zero PO-token/bot-check errors in current+previous logs (yt-dlp nightly + player_client=default,tv,web_safari workaround holding; bgutil-pot container Up 6 days). No new uploads since last downloads (newest uploaded_at per source: 2026-06-25 / 2026-07-11), so no missed content. Minor design note: Kaji Pm's 30-day index frequency means new uploads from that channel can lag up to a month.

### I71. Known Plex analysis storm from the 1363-item bulk ingest has fully drained; zero background activities, server responsive `known-issue`

**Host:** nas · **Component:** Plex (metadata analysis storm) · **Auditor:** flow:youtube-photos


The 2026-07-13 bulk-ingest metadata-analysis backlog (known issue 1) is no longer present: /activities returns an empty MediaContainer (size 0), and all library API calls in this audit returned promptly (section list, 1364-item count, recentlyAdded) with no 503s. The 1363/1364 pinchflat items are fully indexed with media parts and durations populated. Storm resolved; no residual queue.

### I72. Immich Postgres dump pipeline healthy and doubly redundant: nightly 02:30 dumps current through 2026-07-15, healthchecks 'up', retention working

**Host:** nas + mini · **Component:** Immich DB dump backup job · **Auditor:** flow:youtube-photos


/volume1/docker/immich/immich-pg-dump.sh (DSM Task Scheduler, root, ~02:30) produced dumps every day Jul 8-15 (latest immich-2026-07-15.sql.gz, Jul 15 02:30, 16.6MB); the 14-day find-delete retention is active (8 files present). Healthchecks check 'immich-dump-nas' (uuid df506ce5...) status=up, last ping 2026-07-15T09:30:07Z, n_pings=9, 86400s period. Additionally Immich's own internal backup job writes to /volume1/photo/backups (latest immich-db-backup-20260715T020000-v2.7.5-pg14.19.sql.gz) — two independent nightly dump mechanisms, ~33MB/day combined; harmless redundancy worth knowing about. Caveat: both faithfully back up an empty library (see the zero-assets finding).

### I73. 42 of 44 configured vhosts healthy; all LE certs valid to Oct 2026; auth-gated responses as expected

**Host:** mini · **Component:** caddy vhosts + TLS · **Auditor:** flow:dns-proxy


Full sweep of every Caddyfile vhost from the LAN: 42/44 return healthy codes (200/302/303/307/401-auth). Only failures are llamaswap (unloaded config, separate finding) and deptrack (retired, separate finding). mcpo returns 404 at / by design (FastAPI; /docs=200). plex=401 (auth), ha=400 (separate finding). Every served cert is Let's Encrypt via Cloudflare DNS-01 expiring Oct 6-12 2026 (~83 days out) — renewal pipeline healthy. Seedbox-backed routes (deluge, slskd via Tailscale 100.119.134.94) and NAS-backed and rig-backed routes all proxied correctly.

### I74. Split-horizon consistent: both AdGuards carry identical 14-entry rewrite sets; both actively used (64k + 33k queries/day)

**Host:** mini + nas · **Component:** AdGuard split-horizon DNS · **Auditor:** flow:dns-proxy


No rewrite drift: adguard-mini and adguard-nas both hold the same wildcard '*.tabaska.us -> 192.168.10.2' plus identical game-related entries (minecraft->192.168.10.12 rig, palworld/bedrock->69.9.181.17 playit dedicated IP, 10 bedrock-connect hijack domains->mini). All 45 tested names resolve identically to 192.168.10.2 from both servers. Public DNS is NXDOMAIN for service names (by design), with game names correctly NS-delegated to playit-dns.com. Neither resolver is unused junk: mini answered 64,340 queries/24h (real client spread: .2 itself 23.7k, .253 17.6k, .186 12.9k, ...), nas answered 32,966/24h — the secondary is genuinely in the DHCP rotation. Both run AdGuardHome v0.107.77.

### I75. Unbound confirmed as adguard-mini's sole upstream; resolution path healthy end-to-end

**Host:** mini · **Component:** unbound · **Auditor:** flow:dns-proxy


adguard-mini's only upstream is udp://unbound:5335 (bootstrap 127.0.0.11 docker DNS, no fallback_dns), so the client -> AdGuard -> Unbound -> roots path is exactly as designed. Unbound container is healthy and resolves recursively; external resolution through both AdGuards returns matching answers.

### I76. No public exposure: WAN IP answers nothing from the internet (80/443/8123 all filtered); LAN-side WAN hits are the UniFi gateway, not caddy

**Host:** wan / seedbox vantage · **Component:** external exposure · **Auditor:** flow:dns-proxy


From a true external vantage (seedbox betty), home WAN IP 162.0.177.18 times out on 80, 443, and 8123, including with vault.tabaska.us SNI — no port-forwards to caddy or HA exist. The 200/301 seen when probing the WAN IP from inside the LAN is the UniFi gateway's own web UI (self-signed cert CN=unifi.local), i.e. hairpin to the router, a red herring not an exposure. Game traffic egresses via the playit tunnel IP 69.9.181.17, keeping the home IP out of public DNS entirely (only blemish: the www record, separate finding).

### I77. Secondary AdGuard admin UI still on 'break-glass' port 3000, never fronted by caddy; its admin creds are the only AdGuard creds in the vault

**Host:** nas · **Component:** adguardhome-nas admin UI · **Auditor:** flow:dns-proxy


The adguard-nas compose comment says port 3000 is 'wizard / break-glass admin until Caddy fronts it' — no caddy vhost was ever added, so the UI remains plain-HTTP LAN-wide on 192.168.10.4:3000 (auth-protected, basic-auth works). Conversely dns.tabaska.us fronts only the mini instance, whose admin password (Wbef#90332) is NOT recorded in .handoff-secrets.yaml (vault only has adguard_nas creds) — a credential-documentation gap discovered by trial.

### I78. Mini nightly restic FAILED 2026-07-15 01:45 UTC (restic 0.12 hard-delete vs append-only key, 401 loop) — fixed same day; 12:57 UTC re-run with 0.19.1 succeeded and repo is clean `known-issue`

**Host:** mini · **Component:** restic-backup.service · **Auditor:** flow:backups


The 01:30 UTC nightly created snapshot 2ac7c049 but then looped on 'Delete: b2_delete_file_version: 401' trying to remove its lock (old apt restic 0.12 hard-deletes; append-only key forbids), left a stale repo lock, and the unit exited 1/FAILURE — no healthcheck ping. Operator installed /usr/local/bin/restic 0.19.1 (mtime Jul 15 12:57) and re-ran: backup, forget, and 'restic check' all passed at 12:57:48, healthcheck pinged. This matches the known restic-0.12-on-mini issue recorded as fixed 2026-07-15. Current live state verified healthy: latest snapshot 2d054dce 2026-07-15 12:57:29 (857.954 MiB, paths /opt/stacks /etc /home dotfiles), check 'no errors were found', restic-backup-mini healthcheck status up. Nightly cadence otherwise intact (dailies 07-11..07-15 in journal).

### I79. Vaultwarden IS backed up: /opt/stacks/vaultwarden (incl. data/ and db) verified inside the latest mini snapshot, plus a fresh vaultwarden.sqlite.sql.gz pre-backup dump

**Host:** mini · **Component:** restic include set / vaultwarden · **Auditor:** flow:backups


BACKUP_PATHS on mini = '/opt/stacks /etc /home/btabaska/.ssh /home/btabaska/.config /home/btabaska/.docker /home/btabaska/.bashrc'. /etc/restic/excludes.txt explicitly documents vaultwarden/data as intentionally NOT excluded. Verified in the live repo (read-only 'restic ls latest --no-lock /opt/stacks/vaultwarden'): the latest snapshot contains /opt/stacks/vaultwarden/{.env,compose.yaml,data,...}. Additionally the pre-backup DB dump dir /opt/stacks/backups/db/ now contains vaultwarden.sqlite.sql.gz (5,097 B, mtime Jul 15 12:57) alongside forgejo/healthchecks/mealie/miniflux/paperless/wallabag dumps — so the vault has both a raw-file snapshot and a proper sqlite dump (the older 'no sqlite dump, flagged' caveat in the script header is superseded by the dump actually being produced).

### I80. Hyper Backup to B2 is fresh: last_version_inodedb mtime 2026-07-14 19:12:39 PDT (~19h ago), daily ~19:10 schedule; covers @AppConfig, backups, docker, docs, homes, photo

**Host:** nas · **Component:** Hyper Backup (TabaskaNAS_2 -> B2) · **Auditor:** flow:backups


Freshness signal per runbook: /volume1/@img_bkp_cache/ClientCache_cloud_image_aws_s3.L35Ey1/last_version_inodedb mtime = 2026-07-14 19:12:39 -0700 (= 2026-07-15 02:12 UTC), consistent with the daily 19:10 local cron slot (root synoschedtask id=11 at '10 19 * * *') — last run completed normally, next due tonight. The task's cached .hbk Config/@Share dir enumerates the protected shares: @AppConfig, backups, docker, docs, homes, photo. That means both the Immich DB dumps (/volume1/docker/immich/backups) and the HA backup tars (/volume1/backups) DO ship off-site. Two empty stale cache dirs from 07-07 (ClientCache_...kj5SoZ, aws_s3_...wYiFyM) are leftover remnants. Not covered (by design, media tier / regenerable): music, books, games, youtube, stash, frigate, PlexMediaServer, vault (empty share).

### I81. Known issue 8 is STALE: HA automatic backups now exist and succeeded today — daily 08:45 UTC to NAS /volume1/backups (which is inside the Hyper Backup off-site set) `known-issue`

**Host:** ha · **Component:** Home Assistant backups · **Auditor:** flow:backups


The known-issues list says 'HA backups absent', but live state shows a working pipeline: HA API reports sensor.backup_last_successful_automatic_backup = 2026-07-15T08:45:01+00:00, next scheduled 2026-07-16T08:45, manager idle. Matching artifacts land on the NAS via the ha-backup SMB user (secrets hosts.ha.backup_smb_user): Automatic_backup_2026.6.4_2026-07-15_04.45_00002949.tar (1.88 MB) plus 07-14's tar and a 07-13 offsite-verify tar. /volume1/backups is in the Hyper Backup share set, so HA backups reach B2. Note only 2 automatic tars are retained (small, plausible retention=2 config) and backups are ~1.8 MB (config-only scale — sane for a lean HA). HACS still not installed (separate half of known issue 8, not re-checked here).

### I82. Immich nightly pg_dumpall healthy: /volume1/docker/immich/immich-pg-dump.sh, daily 02:30 PT, latest dump today (16.6 MB, gzip OK), 14-day retention, off-site via HB 'docker' share

**Host:** nas · **Component:** Immich DB dump job · **Auditor:** flow:backups


Script /volume1/docker/immich/immich-pg-dump.sh (root, DSM Task Scheduler, matches cron id=9 '30 2 * * *') runs 'docker exec immich_postgres pg_dumpall --clean --if-exists | gzip' into /volume1/docker/immich/backups/immich-YYYY-MM-DD.sql.gz and prunes >14 days. Latest: immich-2026-07-15.sql.gz, 16,658,872 B, mtime Jul 15 02:30 PT, 'gzip -t' passes. 9 daily dumps present (07-07..07-15, plus 07-02); sizes stable ~16.6 MB (no sudden truncation). Healthchecks 'immich-dump-nas' is up, last ping 2026-07-15T09:30:07Z (= 02:30 PT, same run). Destination is inside the Hyper Backup 'docker' share, so dumps replicate to B2. A second copy of the script (/volume1/scripts/nas/immich-db-dump.sh, root-only 750, revised 07-09) exists but is unreadable to the SSH user — appears to be the deployed original; the two should be assumed duplicates (minor drift risk only).

### I83. All five requested dead-man checks are 'up' with fresh pings: restic-mini, restic-rig, immich-dump, ansible-pull x2, verification

**Host:** mini · **Component:** healthchecks (192.168.10.2:8001) · **Auditor:** flow:backups


Via the healthchecks API key: restic-backup-mini up (last ping 2026-07-15T12:57:48Z — the post-fix re-run; only 8 pings total, reflecting this morning's missed nightly), restic-backup-rig up (05:40:59Z, matches 01:40 EDT snapshot), immich-dump-nas up (09:30:07Z), ansible-pull-mini up (13:54:08Z), ansible-pull-rig up (13:55:00Z), verification-mini up (14:16:25Z); bonus verification-quick-mini/verification-fast-mini also up (20:41/21:15Z). The restic-mini check correctly caught the 01:45 failure (ExecStartPost only pings on success) — the dead-man wiring works as designed.

### I84. 100% coverage tripwire is intact: all three manifests match live fleet, no dead entries, backing monitors all exist and are up

**Host:** mini/nas/rig · **Component:** verification coverage manifests + monitoring stack · **Auditor:** flow:coverage-tripwire


mini.containers (38) and rig.containers (9) match live docker ps exactly (self-verified with the same sort|diff the check uses); nas.containers (21) confirmed by the runner's own containers-manifest-nas COVERAGE_OK at 20:40Z today (runner uses NAS sudo docker which auditors may not). Repo copies of all three manifests are byte-identical to deployed /opt/verification/coverage/. Zero dead entries (diff is bidirectional). The tripwire is enforced hourly (verification-quick --host docker-fleet) plus daily. Backing monitors verified live: Uptime Kuma 53 active monitors / 0 down (incl. Seedbox Deluge :8112 + slskd :5030 via tailnet, HA :8123, NAS Plex :32400, NAS DSM); Beszel hub shows mini/nas/rig all up; healthchecks 11/11 checks up. Non-container services (Plex pkg, HA appliance, seedbox deluge) are all covered by Kuma + checks.d even though not in a containers manifest. Cosmetic: the alert-kuma-none-down check name still says '47 fleet monitors seeded 2026-07-09' but 53 are active.

### I85. Verification suite is running on schedule across all three tiers; last daily run today 14:16 UTC passed 114/116 (0 crit)

**Host:** mini · **Component:** verification suite scheduling · **Auditor:** flow:coverage-tripwire


Daily verification.timer (07:15 America/Los_Angeles = 14:15 UTC) last ran 2026-07-15 14:16 UTC, ExecMainStatus=0, summary 114/116 passed, 2 warn failures (restic-snapshot-fresh-rig, wiki-drift — see separate findings), 1 skipped (sys-seedbox-ssh, disabled by design/ACL). Hourly quick tier (*:40, url+docker-fleet+media) last ran 20:41Z exit 0, 42 checks 0 fails. 10-min fast tier (*:05/10) last ran 21:15Z, 18 checks 0 fails. Dead-man pings all wired and up in healthchecks: verification-mini (14:16:25Z), verification-quick-mini (20:41:04Z), verification-fast-mini (21:15:34Z). Deployed timer units in /etc/systemd/system match repo definitions exactly.

### I86. Zero automations and zero scripts exist — nothing to trigger, nothing has ever triggered

**Host:** ha (192.168.10.50) · **Component:** automation / script · **Auditor:** flow:ha-deep


The automation and script components are loaded, but the full /api/states dump (139 entities) contains no automation.* or script.* entities, and the error log has no automation/script errors. HA is currently a pure device bridge (Hue/Elgato -> HomeKit + Ollama assist); the 'never triggered' audit question is vacuously satisfied. Worth knowing because any assumption that HA runs house logic (e.g., in monitoring or docs) is false.

### I87. Ollama AI shim HA->rig is healthy: entry loaded, model present, live completion returned 'OK' in 2.9s `known-issue`

**Host:** ha (192.168.10.50) + rig (192.168.10.12) · **Component:** ollama integration / conversation.rig_ollama_assist · **Auditor:** flow:ha-deep


Config entry 01KXEDMVP3Y19DG8AD90JD2RDY (domain ollama, title http://192.168.10.12:11434) state=loaded, no errors in log since setup. Rig Ollama answers /api/tags with llama3.2:3b present (plus nomic-embed-text, tag:fast — consistent with the 2026-07-15 demotion to HA/Obsidian shim). One permitted tiny test completion through /api/conversation/process with agent_id=conversation.rig_ollama_assist returned speech 'OK' in 2.9s. The agent entity's state shows it was last used 2026-07-15T10:29Z (before this audit), so it sees real use. Default pipeline remains the intent engine conversation.home_assistant ('unknown' state is normal), as designed.

### I88. Error-log clustering (since core start 2026-06-27): only the reverse-proxy 400s are still recurring; elgato, roomba, met-DNS, hue-discovery clusters are all historical

**Host:** ha (192.168.10.50) · **Component:** system_log / error log clusters · **Auditor:** flow:ha-deep


15 deduped clusters in the in-memory system log. By count: elgato coordinator fetch errors x13 (192.168.10.182/.183, 2026-06-30..2026-07-10, RESOLVED — both elgato lights now respond, state 'off' not 'unavailable'); http.forwarded x6 (2026-07-07..2026-07-15, ONGOING — see high finding); roomba x8 (4 ERROR 'Bad username or password' + 4 WARN 'Not authorised' for 192.168.10.231, all 2026-06-27); met.no DNS x4 + homeassistant_alerts DNS x1 (2026-07-03 transient DNS outage, weather currently 'cloudy' i.e. recovered); hue discovery warn x2 (2026-07-03); http.ban invalid-auth x2 (2026-07-07 curl from operator Mac 192.168.10.253 and mini 192.168.10.2 — looks like token-less test curls, one-off); pyhap pair-verify x1 (2026-07-13); hassio /mounts schema error x1 (2026-07-13 backup setup work); recorder unclean-shutdown warnings x2 (2026-06-27 startup); blocking-call warns x2 (roomba config flow). No database/recorder errors after startup, no automation errors.

### I89. Recorder/DB healthy and fast; single unclean-shutdown warning at 2026-06-27 boot only

**Host:** ha (192.168.10.50) · **Component:** recorder / sqlite · **Auditor:** flow:ha-deep


/api/states (139 entities) answers in 18-19ms; a 1-day history query answers in 83ms. The only recorder log items are from startup on 2026-06-27: 'Ended unfinished session (id=1)' and 'could not validate that the sqlite3 database ... was shutdown cleanly' — evidence the Green box was hard-powered-off before that boot, no corruption reported and nothing since (18 days). No 'database is locked' or migration errors anywhere in the log.

### I90. Known-issue #8 'backups absent' is STALE: daily encrypted automatic backups are live and fresh (last success today 08:45 UTC) `known-issue`

**Host:** ha (192.168.10.50) · **Component:** backup · **Auditor:** flow:ha-deep


sensor.backup_last_successful_automatic_backup = 2026-07-15T08:45:01Z (equals last_attempted, i.e. no failed attempt), next scheduled 2026-07-16T08:45Z, backup manager idle. Matches the 2026-07-13 fix in memory (dual agents incl. NAS CIFS mount). The other half of known issue #8 remains true: HACS is still NOT installed (no 'hacs' in the 130+ loaded components), which continues to block midea_ac_lan/emporia_vue.

### I91. No iCloud conflict copies tracked or on disk — mitigations holding `known-issue`

**Host:** macbook (local repo) · **Component:** git / iCloud conflict copies · **Auditor:** repo:junk-deadpaths


Swept the whole repo for ' 2.*'/' 3.*'/'conflicted copy' patterns in both tracked files (git ls-files) and the working tree (find). Zero real hits; the single find match is a legitimate filename ('Sony PlayStation 3.xml' inside the ignored migration-snapshot/). The .gitignore patterns ('* [0-9].*', '* [0-9][0-9].*') are in place and effective.

### I92. foss-setup-plan-2.md and research.md are intentional deprecation stubs awaiting the 'final cleanup pass'

**Host:** macbook (local repo) · **Component:** repo root / deprecation stubs · **Auditor:** repo:junk-deadpaths


Both files (committed 2026-07-14) are 10-line stubs pointing at their wiki replacements and explicitly say 'Stub kept so links resolve; removed in the final cleanup pass.' Not junk yet — but the cleanup pass that removes them (and would presumably sweep agent-fix-tasks.md/keynote.html too) has not happened.

### I93. Root todo.md IS the generated tracker output — current, not an orphan

**Host:** macbook (local repo) · **Component:** repo root / todo.md · **Auditor:** repo:junk-deadpaths


gen-todo.py writes REPO_ROOT/todo.md by design ('(REPO_ROOT / "todo.md").write_text(...)'), and the file header self-identifies as generated from docs/tasks.json + progress.json. Last commit 2026-07-15 (ai-01 SHIPPED), counts 165/234 done — matches current tracker state. Intentionally tracked; no action needed.

### I94. Remaining empty vault keys are consistent with undeployed lanes (hetzner/borgmatic, unifi_protect/frigate, HA integrations, mini sudo)

**Host:** macbook (vault) · **Component:** .handoff-secrets.yaml / other empty keys · **Auditor:** repo:junk-deadpaths


hetzner_storage_box.username '' — borgmatic is only an example config in scripts/backup/ (header: 'borgmatic config example'); no borg units on mini (only restic-backup.timer), so the empty key matches an undeployed lane. unifi_protect.* '' — frigate is documented NOT DEPLOYED, consistent. roborock/vesync/emporia/withings '' — HA integration placeholders. sudo.mini_password '' — harmless: mini sudo is passwordless (verified sudo -n true). None of these currently break a live service.

### I95. Tracker integrity otherwise sound; true open count is 43 (not the naive 40) — open list by track

**Host:** macbook (local repo) · **Component:** tracker: docs/tasks.json + docs/progress.json · **Auditor:** repo:tracker-wiki


No duplicate ids in tasks.json (234 unique). All retired (10), deferred (18), reopened (0) ids exist in tasks.json. No done+deferred or deferred+retired overlaps. Zero depends_on references to nonexistent ids. Spot-check of the 10 most recent done closes (ai-01, seed-13, sec-03, media-06, wiki-05, wiki-06, seed-11, game-13, docker-14, nas-30): all exist and none contradicts done — repo convention keeps original instruction steps, with closure evidence in _meta.note. ha-18 has 'DONE 2026-07-08' in step 1 but is correctly open (step 2 = pending HUMAN room-mapping answers). Reconciliation: 234 = 165 valid-done + 8 retired-only (+2 retired-also-done) + 18 deferred + 43 OPEN; naive 234-166-18-10=40 is off by 3 (nas-00e orphan + sbom dual-status). OPEN by track: agent-handoff: handoff-12. desktop: glue-02, glue-04b, foss-02, foss-03. ebook-mgmt: ebook-06. gaming: game-09, game-12, retro-03..06, retro-08. media-pipeline: seed-12, media-05. photos: nas-08b. reading: read-02, read-05, read-06, read-08, read-09, read-12. security: sec-01, sec-04, foss-01, foss-04. smart-home: ha-04, ha-06, ha-07, ha-09, ha-10, ha-14, ha-18, ha-19, ha-21, ha-22, ha-23, ha-25, ha-26, ha-27, ha-28, ha-31, ha-32.

### I96. todo.md, roadmap pages, service pages, checks pages and mkdocs nav are all fresh — regeneration is byte-identical (except the publish-deploy pages)

**Host:** macbook (local repo) · **Component:** wiki: generated artifacts freshness · **Auditor:** repo:tracker-wiki


Ran all five tracker/wiki generators in place (gen-todo.py, gen-roadmap-pages.py, gen-wiki-services.py [37 stacks, PyYAML+catalog+enrichment], gen-script-pages.py [63 pages], gen-checks-pages.py [117 checks/12 domains]). git status showed zero diff except the 2 publish-deploy files (separate finding). service-enrichment.yaml and service-catalog.yaml both exist and are wired in gen-wiki-services.py (CATALOG/ENRICH, lines 41-42) — no hand-edit drift in any generated services/*.md. Touched files restored with git checkout; final git status clean.

### I97. Wiki link health is good: 0 broken internal links across 244 pages, all 242 nav entries resolve; one literal Obsidian-style [[ha-control-plane]] renders as dead text

**Host:** macbook (local repo) · **Component:** wiki: internal links · **Auditor:** repo:tracker-wiki


Custom link-check over wiki/docs: every relative markdown link target exists (0 broken), no absolute-path links, and all 242 mkdocs.yml nav entries point at existing files (consistent with build-wiki.sh's --strict build). Only blemish: generated page reference/scripts/ha/haws-py.md line 16 contains 'See memory [[ha-control-plane]]' inherited from the haws.py docstring — mkdocs-material has no wikilink plugin (pymdownx only) so it renders literally and references an operator-memory file wiki readers can't reach. Cosmetic; fix wording in the script docstring and regen. The other [[...]] hit is a bash conditional in a code block (false positive).

### I98. retro-01/retro-02 have steps:null; docs/wiki-design.md is a fully-superseded proposal still citing the retired index.html

**Host:** macbook (local repo) · **Component:** tracker: data quality nits · **Auditor:** repo:tracker-wiki


retro-01 (NAS ROM library layout) and retro-02 (RomM) are the only tasks with steps:null (both done; generators tolerate it, but they render with no body anywhere the steps would show). docs/wiki-design.md (Jul 8) is the pre-build wiki proposal — 'This document is a proposal only — nothing is built yet' — now that wiki-06 build-out is complete; it references docs/index.html 5+ times. Clearly headed 'APPROVED 2026-07-07' so it reads as historical, but it is the last docs/ file that still describes the retired tracker as current ('index.html already does that — 134 tasks').

### I99. Pull topology verified healthy on mini: unit enabled, last run succeeded today, and forgejo home/homelab main is in lockstep with this repo

**Host:** mini+forgejo · **Component:** ansible-pull convergence topology · **Auditor:** repo:live-drift


mini ansible-pull.timer enabled; last run started 2026-07-16 04:49:33 UTC and finished successfully ('Finished ansible-pull fleet convergence', healthchecks ansible-pull-mini pinged 04:50:09). Units pull git@forgejo:home/homelab.git with site.yml at foss-setup/configs/ansible/ (the glue-08 full-repo topology). forgejo's main (3b87b1f) == local repo main == mini's /home/btabaska/.ansible-pull checkout — no fork drift. The rig side authenticates fine to forgejo (deploy key works) but its checkout is stale at b0d8c83 solely because of the read-only-filesystem failure reported separately. Healthchecks pings for both hosts are wired via /etc/systemd/system/ansible-pull.service.d/healthchecks.conf ExecStartPost drop-ins (success-only, correct dead-man semantics).

### I100. Seedbox is clean: reaper script byte-identical to repo, cron running daily with healthy output, live core.conf matches the wiki-documented settings, slskd-native live

**Host:** seedbox · **Component:** deluge + reaper + slskd vs repo · **Auditor:** repo:live-drift


~/scripts/deluge-reaper.py matches configs/host/seedbox/deluge-reaper.py exactly; cron '0 5 * * *' runs it --live, log shows daily runs (last: 2026-07-16 05:00:09, '0 eligible', err log 0 bytes). Live core.conf keys match the wiki reference (deluge-queue-hygiene.md): daemon_port 3254, allow_remote true, enabled_plugins [Bytesized, Label, ltConfig, AutoAdd], stop_seed_at_ratio false, max_active_seeding/limit 700. slskd runs natively (~/bin/slskd --app-dir ~/slskd-native, up since Jul 08) and its .env key names match the repo's slskd-native.example.env template; the live slskd.yml itself has no committed mirror (repo ships only examples — template-by-design, noted).

### I101. 117 checks defined (116 enabled, 1 disabled): ~38 (33%) are bare liveness pings; ~79 test invariants, function, or outcomes — gap #15 is real but overstated for this framework `known-issue`

**Host:** mini · **Component:** checks.d inventory / liveness-vs-e2e classification · **Auditor:** repo:verification-suite


Inventory: 12 yaml domains, 117 unique check ids (no duplicates), 1 disabled (sys-seedbox-ssh, ACL), 18 tagged tier:fast. Host split: mini 78, url 19, nas 10, rig 9, local 1. Classification: (a) liveness-only = ~38 checks — bare HTTP-status-code probes (17 mini-services, 10 nas-services, 5 rig, ha-http, sys-home-assistant), container-state (2 diun, caddy/adguard running), ssh-echo (nas-ssh), TCP connect (net-trusted-to-iot). (b) config/inventory invariants = ~20 (3 container manifests, DSM crontab greps, keep-alive/power-tune/subnet-squat, git-clean x3, plex ACL, no-flac). (c) functional/outcome/e2e = ~59, including genuinely end-to-end probes: 5 backup-freshness dead-mans, disk-vs-Plex coverage (pinchflat/radarr/sonarr-in-plex), real Minecraft protocol pings through the playit edge, a real LLM completion (rig-ai-e2e), an agentic tool-loop (rig-ops-agent-e2e), queue-stuck/phantom-request/copy-drop data cross-checks, wiki-drift regeneration, meta-monitors (healthchecks/kuma/beszel none-down). So roughly one third of the surface is ping-only, concentrated in mini-services/nas-services; the media/backup/rig domains are largely outcome-based. Note one policy deviation: rig-ai-gpu-yield is not read-only — it POSTs /api/models/unload (state-changing) inside a framework whose README declares 'probes only observe'.

### I102. All 3 timers enabled+active; installed units match repo (modulo ping-URL substitutions); both healthchecks ping URLs firing; last 3 daily runs: 2 unit-FAILED (pre-fix, by design flaw since fixed) then clean

**Host:** mini · **Component:** systemd timers / run history / dead-man cross-check · **Auditor:** repo:verification-suite


Wiring: all 12 checks.d files are loaded by the runner (sorted *.yaml glob) — no orphan check files, no runner references to missing checks; the four helper scripts checks reference exist on mini (see deploy-divergence finding for the repo gap). Timers: verification.timer (daily 07:15 PT), verification-quick.timer (hourly :40), verification-fast.timer (*:05/10) all enabled/active. Last 3 scheduled daily runs: Jul 13 76/81 passed (1 crit) — unit 'Failed' (old rc-propagating verify-cycle); Jul 14 87/93 (2 crit) — unit 'Failed' (same, fixed 22:34 that day; manual 22:35 rerun finished clean, 129s); Jul 15 114/116, 0 crit — success, ~26s. Quick tier ~8-45s/cycle, fast tier ~5-6s, both green history. Dead-men: verification-mini (period 1d) pinged by the daily unit's drop-in ExecStartPost — status up, last ping Jul 15 14:16:25Z; verification-quick-mini (period 1h) pinged by the hardcoded ExecStartPost in verification-quick.service — up, pinging hourly; a third, verification-fast-mini (period 10m), is pinged via ${VERIFY_FAST_PING_URL} from /etc/verification/env — up. Minor vault gap: the fast tier's ping URL (bffb602f-...) is absent from .handoff-secrets.yaml healthchecks section (verification_mini/verification_quick_mini/others are present).

### I103. Coverage manifest format matches exactly what the runner consumes; manifests currently in sync with all three hosts

**Host:** mini · **Component:** coverage/ manifests · **Auditor:** repo:verification-suite


Format contract: one container name per line, LC_ALL=C sorted, no '-run-' one-shots — diffed verbatim by containers-manifest-{mini,nas,rig} (`docker ps --format {{.Names}} | grep -v -- '-run-' | LC_ALL=C sort | diff /opt/verification/coverage/<host>.containers -`). Repo files (mini 38, nas 21, rig 9 lines) md5-match the deployed copies, and all three manifest checks passed on every hourly docker-fleet run in the last 26h (the only docker-fleet failures are the two systemd-failed checks). The 100%-coverage tripwire (extra/missing container detection) is functioning as designed.

### I104. systemd-failed-rig failing hourly since ~04:40 UTC: ansible-pull.service exit 5 (downstream of read-only filesystem)

**Host:** rig · **Component:** docker-fleet / ansible-pull · **Auditor:** repo:verification-suite


The hourly docker-fleet tier has flagged rig ansible-pull.service failed (exit status 5, 04:21 EDT) — ansible cannot write on the ro filesystem. Paged once at 04:40 UTC (transition), correctly not re-paged since. Listed separately so the parent merge sees the rig convergence pipeline is down along with everything else in the cascade; glue-08's ansible-pull-rig healthchecks dead-man last pinged Jul 15 13:55Z and will go into grace later today.

### I105. llama-swap fully functional under RO FS; verification LLM-triage is UNAFFECTED (it bypasses LiteLLM)

**Host:** rig · **Component:** llama-swap (:9292) + verification LLM-triage · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


llama-swap serves /v1/models (9 aliases: deckard-heretic, devstral-24b, fast-3b, gemma4-31b-qat, qwen2.5-coder-7b, qwen3-coder-30b, qwen3-embed, qwen3.6-27b, qwen3.6-35b-a3b) and a live tiny completion on fast-3b returned 'OK' in 1.3s — model load/serve is a read-only path (GGUF mmap) so the RO FS does not break it. Crucially, verification/bin/llm-triage.sh defaults LLM_BASE_URL to http://cachyos.tailb31641.ts.net:9292/v1 (llama-swap, no auth, model qwen3.6-35b-a3b), explicitly NOT LiteLLM :4000 — so LLM-triage of failed checks keeps working despite the LiteLLM outage. /running was empty (idle, TTL unloads at 300s, normal).

### I106. HA Ollama Assist unaffected: live conversation round-trip through rig Ollama succeeded

**Host:** ha (192.168.10.50) + rig · **Component:** HA Assist -> rig Ollama shim (:11434) · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


The native Ollama compat shim on rig :11434 still serves its 3 shim models (nomic-embed-text, llama3.2:3b, tag:fast) and a live HA /api/conversation/process request routed to agent conversation.rig_ollama_assist returned a generated reply ('Ok'). HA's default agent also answers. Blast radius of the rig RO incident on HA Assist: none observed — Ollama generation is a read path and the systemd Ollama service survived the remount.

### I107. mcpo container up and HTTP-responsive; overlay read-only like the rest

**Host:** rig · **Component:** mcpo (:8000) · **Auditor:** gap:rig AI stack (llama-swap/litellm/open-webui/mcpo) — re-verify under the active read-only-root-FS incident


mcpo is running, GET /docs returns 200, recent logs show only routine 404s on / from mini probes (its healthcheck probing the root path — cosmetic). Its overlay FS is read-only ('touch: Read-only file system'), so any MCP tool that needs local writes would fail, but no write errors appear in recent logs. Functional for read/tool-proxy use as far as HTTP surface shows; deep per-tool testing not performed.

### I108. Nightly Immich DB dump pipeline is healthy and healthchecked; minor gap Jul 3-6 before the schedule took effect

**Host:** nas · **Component:** immich-pg-dump · **Auditor:** gap:NAS Immich — root-cause the ZERO-assets finding via the readable Postgres dump (not just filesystem emptiness)


/volume1/docker/immich/immich-pg-dump.sh (root, DSM Task Scheduler ~02:30, 14-day retention) has produced dumps 2026-07-07 through 2026-07-16 plus the initial 07-02; Jul 3-6 are missing (scheduler evidently enabled ~Jul 7; 07-07 20:00 and 07-09 13:23 look like manual runs). The healthchecks check 'immich-dump-nas' on mini is status=up, last_ping 2026-07-16T09:30Z, n_pings=10 — the ping is wired outside the script (script body contains no curl), presumably in the DSM task command; that wrapper could not be verified (no sudo on nas). Retention find -mtime +14 is working. Dumps are readable and restore-grade (full pg_dumpall --clean).

### I109. Immich pinned at v2.7.5 while the server's own update check reports v3.0.3 available

**Host:** nas · **Component:** immich · **Auditor:** gap:NAS Immich — root-cause the ZERO-assets finding via the readable Postgres dump (not just filesystem emptiness)


Compose pins IMMICH_VERSION to v2.7.5 (deliberate, with matching digest-pinned postgres/valkey). system_metadata.version-check-state in last night's dump shows releaseVersion v3.0.3 (checked 2026-07-16T09:11Z), i.e. a full major version behind. Not urgent given zero content, but worth scheduling before the library gets populated — a major-version migration is cheapest while the DB is empty.

### I110. No live unpackerr wedge: all 5 arr queues empty, rar pipeline demonstrably worked end-to-end through 2026-07-10

**Host:** nas · **Component:** unpackerr · **Auditor:** gap:NAS unpackerr — live wedge state and archive-extraction backlog never quantified (only 1 case evidenced)


Live config /volume1/docker/media-automation/unpackerr/unpackerr.conf has 4 blocks: [[sonarr]] paths=['/seedbox/tv'], [[radarr]] ['/seedbox/movies'], [[lidarr]] ['/seedbox/music'], [[readarr]] ['/seedbox/books']; interval=2m, parallel=1, delete_orig=false everywhere, delete_delay=10m. Current wedge state: sonarr/radarr/lidarr/readarr/whisparr queues all totalRecords=0, so there is nothing pending extraction. End-to-end proof the extractor worked recently: 6 Archer rar-only releases landed on the seedbox 2026-07-10 and their extracted mkvs were imported by Sonarr 2026-07-10T15:55-16:01Z (554-976MB files in /tv/Archer (2009)/...). Every other recent seedbox rar release cross-checked (Teen Titans Go S07E41-48, South Park S25E01-06, Simpsons S33E14+S07E22, Futurama S10E06, Sex/Life S02E03/04/06, Spy x Family S02E03, Hacks S01) has hasFile=True with proper multi-hundred-MB library files. Seedbox archive census: rars exist ONLY under files/tv (55 of 318 release dirs); files/movies, files/music, files/books, files/slskd, files/manual, ~/media = 0 archives. 35 of the 55 have no extracted video alongside = extracted, imported, then cleaned by delete_delay (by design). The extraction gap is NOT a broad live wedge; it is historical/legacy (see separate findings).

### I111. 17 of 18 previously-unchecked WAN ports are filtered from the external vantage — edge is otherwise closed

**Host:** home WAN 162.0.177.18 (edge firewall) · **Component:** External port exposure (gap-fill probe) · **Auditor:** gap:External WAN exposure — port probe was limited to 80/443/8123 from a single vantage


Gap-fill external probe from the seedbox confirms the home edge is closed for every previously-unchecked service port except Plex 32400. Filtered (no TCP handshake, 4s timeout) from the public internet: 22 and 2222 (SSH), 5000 and 5001 (Synology DSM HTTP/HTTPS), 8123 (Home Assistant — confirms the known-filtered state), 8443, 3254, 5945, 13091, 8989/7878/8686/8787/9696/6969 (the entire sonarr/radarr/lidarr/readarr/prowlarr/whisparr arr stack), 3000, and 853 (DNS-over-TLS). No SSH, DSM admin, arr APIs, or DoT are exposed. This is a positive posture confirmation; only the Plex finding above is actionable.

### I112. Recyclarr weekly sync is healthy end-to-end: last run clean, live arr state matches exactly, dead-man up

**Host:** mini · **Component:** recyclarr · **Auditor:** gap:recyclarr (custom-format / quality-profile sync to radarr+sonarr) — deployed and monitored but never audited for sync correctness


Recyclarr 8.4.0 runs as a one-shot docker compose job (/opt/stacks/recyclarr, restart:no) from btabaska's crontab: '0 3 * * 0 cd /opt/stacks/recyclarr && docker compose run --rm recyclarr sync >> config/logs/cron-sync.log && curl <hc ping>'. Config targets exactly the two live NAS instances (sonarr http://192.168.10.4:8989 profile WEB-1080p trash_id 72dae..., radarr http://192.168.10.4:7878 profile 'HD Bluray + WEB' trash_id d1d67...) with API keys matching .handoff-secrets.yaml. Last run 2026-07-12: 0 WRN/ERR/FTL lines; radarr '40 CFs skipped/up to date', sonarr '37 CFs skipped/up to date', quality sizes, media naming (incl. radarr plex-tmdb) and both quality profiles all synced/up-to-date. Previous run 2026-07-05 also 0 errors (updated 1 radarr CF, 1 sonarr profile). Live verification: radarr has exactly 40 custom formats and sonarr exactly 37, matching recyclarr's managed set; managed profiles exist with TRaSH scores wired (radarr 'HD Bluray + WEB' 25 nonzero CF scores cutoff 10000; sonarr 'WEB-1080p' 37 nonzero scores cutoff 10000) and are actually in use (318/318 radarr movies, 160/162 sonarr series). Healthchecks check 'recyclarr-sync-mini' (uuid fb109ef5, 7d timeout + 1d grace) is status=up, never flipped down (single up-flip 2026-07-09 at creation; n_pings=2: one manual 07-09 from the MacBook, one automated 07-12 from mini). Note the dead-man only has one automated cycle of history so far (check created 2026-07-09). Log files at /opt/stacks/recyclarr/config/logs/cron-sync.log and config/logs/cli/.

### I113. mini host clock is Etc/UTC, so the '0 3 * * 0' recyclarr cron actually fires Saturday 23:00 EDT, not Sunday 3 AM local

**Host:** mini · **Component:** recyclarr / host timezone · **Auditor:** gap:recyclarr (custom-format / quality-profile sync to radarr+sonarr) — deployed and monitored but never audited for sync correctness


timedatectl on mini shows Time zone: Etc/UTC while the recyclarr compose/.env deliberately set TZ=America/New_York for the container. Result: cron entries on mini are interpreted in UTC — the 'Sunday 03:00' recyclarr sync really runs Saturday 23:00 Eastern (container logs are stamped 23:00 Jul 11 for the run whose host mtime is Jul 12 03:00 UTC), and the broken midnight bin job fires at 20:00 EDT. Functionally harmless for recyclarr (one-shot, non-disruptive, healthchecks period is relative), but all mini cron times drift 4-5h from Eastern intent, and any job the operator schedules 'inside the 4-7AM EST maintenance window' via mini cron would actually run at midnight-3AM EST. Flagging as intent-drift, not breakage.

# Rollout handoff state

### playit.gg public access LIVE + AMP sleep-mode gotcha (2026-07-09 late)

- **Decision: friends connect via playit.gg tunnels** (not raw static-IP port-forward, not Tailscale — consoles can't run TS). Agent container on rig `/opt/stacks/playit` (ghcr.io/playit-cloud/playit-agent, host network, SECRET_KEY in on-host .env + vault `playit_gg.secret_key`; repo mirror configs/gaming/playit/). One agent, many tunnels — account allows **4 TCP + 4 UDP**; Palworld etc. = just more dashboard tunnels later.
- **Both tunnels VERIFIED end-to-end from off-host** (real MC status ping + RakNet pong through the public edge): Java `analysis-conditioning.gl.joinmc.link:14450` (SRV → port optional in client) · Bedrock `stop-spain.gl.at.ply.gg:58804`. Agent API key is READ-ONLY (`NotAllowedWithReadOnly` on tunnels/create) — tunnel creation is dashboard-only.
- **Gotcha found while verifying — AMP sleep mode**: `Limits.SleepMode=True` (default, 5-min empty timeout) stopped the app mid-verification; AMP's wake listener answers **Java protocol only** on 25565 (MOTD "Powered by AMP") — so (a) a Java status ping is NOT proof the real server is up, and (b) **Bedrock/Geyser is completely dark while asleep** and Bedrock joins can never wake it. Set `Limits.SleepMode=False` (rig is 24/7). If sleep is ever wanted again, know that it silently breaks the Bedrock side.
- **User's playit account email still unverified** (agent logs `account_status=email_not_verified`) — remind to verify or playit may cap/expire things.
- Still open: whitelist before the address leaves the friend group (recommended, one command away) · BedrockConnect for Switch (todo Task 09) · mc.tabaska.us (Task 10).

### AMP white-screen fixed + Minecraft crossplay server LIVE, fully automated (2026-07-09 night)

- **White screen root cause**: after the rig's reboots, the AMP container came up but the ADS panel instance ("Main") had **no start-on-boot flag** → nothing on :8080 → Caddy 502 → blank browser. Fixed durably: `ampinstmgr --SetStartBoot` set for BOTH Main and MinecraftCross01; verified by a full container recreate (panel came back unattended).
- **The "first instance must be born in the UI" claim is DEAD**: `docker exec -u abc amp ampinstmgr …` bypasses the BusyBox `su` failure (that failure was root-exec-only), and `--CreateInstance` takes the licence key as an argument. Created `MinecraftCross01` (friendly "MinecraftCross") entirely from the CLI. Gotchas: ampinstmgr refuses create/rebind/setboot while ADS runs (stop Main briefly); the CLI's [Port] arg is the instance's WEB port, not the game port (rebound web→8081, game stays 25565).
- **Licence is machine-id-bound** — container recreate invalidated it (NoMatchingMachineId) until reactivated; compose now **pins hostname c5f46f35aee3** so future recreates keep activations. Reactivate cmd in the runbook.
- **Java saga (all persisted)**: Alpine image has no java → openjdk21 via `INSTALL_PACKAGES` env (survives recreates). Minecraft 26.x demands **Java 25** → Temurin 25 musl JRE at `/config/java/jdk-25.0.3+9-jre` behind wrapper `/config/java/java25-paperfix.sh` (strips `--log-strip-color`, which AMP module 2.8 passes but Paper 26.x removed). Instance `Java.JavaVersion` → wrapper.
- **Version matrix that actually works**: Paper **26.1.2** + Geyser 2.10.1-b1183 + Floodgate 2.2.5. Geyser latest does NOT support MC 26.2 (ExceptionInInitializerError in shaded incendo/cloud on enable) — AMP's manifest "26.2-rc-2" and real Paper 26.2 both fail the same way. Real Paper versions: `fill.papermc.io/v3` (v2 API is sunset). Plugins installed as jars from the GeyserMC download API into `Minecraft/plugins/`. eula.txt seeded.
- **VERIFIED from the mini**: Java TCP 25565 reachable; **Bedrock RakNet unconnected-ping → real pong** ("Powered by AMP", 0/20, protocol 26.32). Compose now maps 25565 + 19132/udp (they were never published before — LAN players couldn't have connected). Kuma monitor **"Rig Minecraft Java"** added (48 total, all up, ntfy-linked).
- **API path for instance management** (documented in runbook): panel `/API/Core/Login` → proxied instance login at `/API/ADSModule/Servers/{id}/API/Core/Login` → proxied SetConfig/UpdateApplication/Start/GetUpdates. Instance auth is ADS-delegated; rig `.mc-admin-password` is unused.
- **Repo**: configs/gaming/amp/compose.yaml mirror updated (hostname pin, java envs, port maps; secrets stay ${AMP_*}); minecraft-crossplay-finish.md rewritten as live-state runbook; todo-guide TASK 02 marked done; progress.json game-02 → done (140/223 — concurrent sessions closed more tasks today; len(done)==meta count verified).
- **Hygiene note**: the rig's live /opt/stacks/amp/compose.yaml has the panel PASSWORD and LICENCE as literals (pre-existing); they surfaced in a session transcript today — rotate the panel password when convenient.
- **Still open (user decisions)**: BedrockConnect self-host for Switch 2 (todo Task 09) · mc.tabaska.us (Task 10) · whitelist before sharing the address. AMP image/module update would obsolete the java wrapper — retest after module >2.8.

### Kuma + Beszel pass COMPLETE — fleet-wide monitoring live (2026-07-09 evening)

- **Uptime Kuma: 11 → 47 monitors, ALL UP** (todo-guide TASK 07 closed). Seeded via direct MariaDB inserts + container restart (v2 loads at startup) — script: `foss-setup/scripts/uptime-kuma/seed-monitors.sh` (idempotent by name; run with `NTFY_TOKEN` from vault `ntfy.kuma_token`). Coverage: every catalog service on mini/NAS/rig/HA/seedbox by direct host:port (status codes probed live first — seerr-family 3xx, mcpo 404-on-/, apollo https+ignore_tls), 3 full-chain vhost checks (home/vault/books.tabaska.us → DNS+Caddy+LE-cert expiry alerts), DNS checks, 5 host pings. **Gotchas encoded in the script**: container→host-IP UDP hairpin TIMES OUT on mini, so "DNS AdGuard mini" + "DNS Unbound mini" are TCP checks by container name (`adguardhome:53`, `unbound:5335` on the shared edge network); NAS AdGuard is a real dns-type query. Notification = ntfy type via `http://ntfy:80` (edge network, no Caddy/DNS dependency), topic `homelab-alerts` (phone subscribed), `is_default=1` + linked to all 47 via monitor_notification. **Maintainerr was NOT seeded — it's removed from the fleet but still in service-catalog.yaml (stale entry, cleanup pending).**
- **Beszel: mini + NAS + rig all registered and UP with alerts.** Root cause of the stale "only MacBook shows" state: the sole system record ("MacBook", 192.168.10.253) had the fingerprint token that the MINI's agent connects with — i.e. it was mini data mislabeled (no agent runs on the MacBook; port closed). Renamed that record to `mini`/192.168.10.2 (agent connection preserved). Created `nas` + `rig` systems + fingerprint records via PocketBase superuser API (auth `/api/collections/_superusers/auth-with-password` with vault beszel.admin_*), tokens in vault `beszel.agent_token_nas/_rig`. Agents deployed in **WebSocket mode** (dial hub, no inbound port): rig `/opt/stacks/beszel-agent/`, NAS `/volume1/docker/beszel-agent/` (Synology doesn't auto-create bind dirs — mkdir first; scp subsystem broken to NAS, use `ssh nas 'cat > file'`). Repo: `configs/host/{rig,nas}/beszel-agent/` (+.env.example; real .env with token never committed). Alerts: Status(5m)/Disk(85%)/Memory(90%) × 3 systems, webhook = shoutrrr `ntfy://:<token>@ntfy:80/homelab-alerts?scheme=http` in user_settings; **test-verified end-to-end via `POST /api/beszel/test-notification` → 200 → phone**.
- **ntfy: two new admin tokens** (labels uptime-kuma, beszel) → vault `ntfy.kuma_token` / `ntfy.beszel_token` (follows fleet convention of labeled admin tokens).
- **Sweep: 63/63 pass, 0 crit** (2 new checks: `alert-kuma-none-down`, `alert-beszel-none-down`; the latter needs BESZEL_ADMIN_USER/PASSWORD in mini `/etc/verification/env` — added + etckeeper-committed). Cleared en route: stale `/etc/.git/index.lock` on mini (recurring issue — second time now) which had also failed `etckeeper-commit.service` (reset).
- Note: Kuma monitors live in its MariaDB (data, not compose) — re-seed from the script on rebuild. Beszel "MacBook" is gone as a name; if the user wants the MacBook genuinely monitored, install an agent there and add a 4th system.

### rig NVMe fix APPLIED (out of window, user-authorized) + AER→ntfy monitor live (2026-07-09)

- **NOTE for the concurrent session**: the NVMe kernel-param fix is **DONE** — do NOT re-apply it in the 4-7AM window (the earlier RCA entry's "await window" is superseded).
- **Applied to rig `/etc/default/limine` `KERNEL_CMDLINE[default]`** (backup at `/etc/default/limine.bak-preaspm`): added `nvme_core.default_ps_max_latency_us=0` (disable NVMe APST) + `pcie_aspm=off`. Ran `limine-update`, verified generated `/boot/limine.conf` default entries carry the params + `root=UUID` intact, **rebooted rig** (came back clean in ~40s).
- **VERIFIED**: `/proc/cmdline` has both params; APST latency now `0`; **PCIe AER errors = 0** over 2 min uptime (was **8-16 in the first 2 min** pre-fix). So the RxErr storm is stopped. (`pcie_aspm=off` still shows "ASPM L1 Enabled" in lspci LnkCtl, so APST was the dominant trigger; errors stopped regardless.)
- **Drive mapping is by PCI addr, not nvmeX** (the number reshuffles on reboot): `0000:74:00.0` = WD Blue SN570 = OS drive (root btrfs `/`,`/home`,`/var/*` + `/boot`). Currently enumerates as `nvme2`. Use SMART/PCI, never the `nvmeN` name.
- **AER→ntfy monitor deployed on rig** (self-contained, because tailnet ACL blocks mini→rig SSH so the mini runner can't read rig's journal): `/opt/pcie-aer-monitor/pcie-aer-monitor.sh` + systemd timer (every 20 min, root). Counts AER on `74:00.0` this boot; POSTs to ntfy `verification` topic (same iOS push you already get) only if correctable climbs ≥25/interval, any fatal/uncorrectable, or SMART critical!=0x00. Silent when healthy. Token: vault `ntfy.rig_aer_token` (label `rig-aer`). Repo: `foss-setup/configs/host/rig/pcie-aer-monitor/`. One `[TEST]` ntfy sent + delivered (200); no more test pings.
- **Still open (physical/durable, user's call)**: reseat the SN570 M.2 / try a CPU-direct slot; consider dropping `nowatchdog` for auto-recovery; if AER ever returns, migrate OS to the Corsair MP600 PRO or replace the SN570. The software fix treats the trigger, not the marginal link itself.

### Kobo sync live + rig back + regressions cleared (2026-07-09 afternoon)

- **Rig is BACK as of 08:59 EDT** — it came up within a minute of a `wakeonlan 50:eb:f6:b5:82:c6` fired from mini at ~08:58 (vault MAC, same as wake-rig.sh — verified identical, so the earlier failed WoL was state-dependent, not a wrong MAC; a user power-cycle at that moment is the alternative explanation). All services healthy post-boot: ollama/litellm/open-webui all 200, Apollo user-unit active, restic ran. NVMe RCA below explains the crash; fixes still await the 4-7AM window.
- **Sweep regressions cleared: 54/61 (2 crit) at session start → 59/61 on re-run → remaining 2 self-clear**: stale restic snapshots on mini (its 01:41 UTC run died in the DHCP outage) and rig (was off) — both kicked manually, both completed + pinged Healthchecks ("All done" / "Finished"). Healthchecks now 0 down (ansible-pull mini/rig + immich-dump-nas in *grace*, self-clear on next scheduled run). Mini DHCP mitigations re-verified this boot: net-selfheal.timer active, KeepConfiguration drop-in present, netplan still bare-DHCP — **static IP still staged, not applied** (window tomorrow 4-7AM ET, lease expiry ~11:55 UTC).
- **CWA Kobo sync ENABLED end-to-end (server half of todo-guide TASK 08)**: `config_kobo_sync=1` + `config_kobo_proxy=1` (store passthrough) in app.db, container restarted, `https://books.tabaska.us/kobo/<token>/v1/initialization` verified **200** with the real token (401 with a bogus one = auth active). Sync token minted for the admin user (remote_auth_token, token_type=1, no expiry) → vault `cwa.kobo_sync_token_admin` + full URL at `cwa.kobo_api_endpoint_admin`. todo-guide TASK 08 rewritten to the device-side steps (edit `Kobo eReader.conf` `[OneStoreServices] api_endpoint`). Add a second CWA user + token if the user wants per-Kobo progress separation.
- **iPod toolchain preinstalled on rig (read-10 done)**: rhythmbox 3.4.9 + libgpod 0.8.3 (repo script) + gpodder 3.11.5 (read-12 install half). Human half remaining: plug in the iPod and follow `scripts/media/ipod-sync-cachyos.md` (FirewireGuid/SysInfoExtended gotchas documented there). Note: rig has **no NAS music mount** — mount `/volume1/music` (SMB) or sync from a local copy before read-11.
- **Hygiene**: the ntfy read-only `phone` user's password is visible in `ps` output on mini (curl `-u` on the wake-rig-listener cmdline). Low risk, but rotate when convenient and switch the listener to `--config`/netrc so it stays out of the process list.

### RCA: rig freeze (2026-07-08 20:02 EDT) = NVMe PCIe link instability on the OS drive (2026-07-09)

- **Event**: rig froze **2026-07-08 20:02:39 EDT**, stayed dead ~13h until user hard-rebooted 07-09 08:59. Boot -1 log ends abruptly mid-operation — **no shutdown sequence, no kernel panic, no pstore dump**. Boot -2 ended cleanly (deliberate reboot 08:46), so the freeze is a single event, but the underlying fault is chronic.
- **PRIMARY CAUSE (strongly supported)**: NVMe **nvme1 = WD Blue SN570 2TB** at PCI **0000:74:00.0** throws continuous **PCIe correctable AER errors** (`RxErr`, Physical Layer, Receiver ID): **764 (boot -2), 724 (boot -1), 8-16 within 2 min of the new boot** — ~2/min at idle, happening right now. ALL AER is on this one device (362 "PCIe Bus Error" headers in boot -1, 0 on other slots).
- **It's a LINK/signal problem, not a dying drive**: SMART clean — Critical Warning 0x00, **0 Media/Data Integrity Errors, 0 error-log entries**, 1% used, 34°C, 5647 POH. Link trains full Gen3 x4. So NAND/controller are fine; the PCIe **physical layer** is marginal.
- **Why it froze the whole box**: per `/etc/fstab`, the root btrfs `UUID=e4b84b06` (subvols `/`, `/home`, `/root`, `/srv`, `/var/cache`, `/var/tmp`, `/var/log`) **AND `/boot`** all live on this same SN570. A transient link wedge blocks ALL OS I/O → journald can't write (hence abrupt stop, no panic) → hard hang. Kernel cmdline has **`nowatchdog`** so nothing auto-recovers → frozen till manual power-cycle. **Unsafe Shutdowns = 523** (high) ⇒ this freeze/hard-reboot cycle has likely recurred.
- **Aggravator = power management**: **PCIe ASPM L1 Enabled** on the link + **NVMe APST enabled** (`nvme_core.default_ps_max_latency_us=100000`). Power-state transitions on a marginal link are the classic trigger for RxErr storms + occasional drops.
- **Ruled out**: thermal (28°C, no throttle/critical-temp), OOM (none), MCE/hardware-error (none), GPU (no Xid/NVRM errors — NVIDIA 610.43.02 clean).
- **FIXES — #1 APPLIED & VERIFIED 2026-07-09 (user waived window); see the newest top entry. #2-4 still open.** (bootloader = limine)**:**
  1. Kernel params via `/etc/default/limine` `KERNEL_CMDLINE[default]`: add **`nvme_core.default_ps_max_latency_us=0`** (kill NVMe APST) + **`pcie_aspm=off`** (or gentler `pcie_aspm.policy=performance`). Regenerate limine + reboot. Most common cure for RxErr AER storms + associated hangs.
  2. Physical (user): power down, **reseat the SN570 M.2** (clean contacts); try a CPU-direct M.2 slot if free.
  3. Resilience: consider dropping `nowatchdog` / enabling a watchdog so a future hang auto-reboots (this box is meant to be 24/7 — 13h dead is the cost of no watchdog).
  4. If AER persists after 1+2: slot/controller marginal → migrate OS to the healthier Corsair MP600 PRO (nvme0) or replace the SN570. It hosts the whole OS, so this is the durable fix.
- **Monitoring gap**: nothing alerted on the AER storm. TODO: add a verification check = count `PCIe Bus Error` in `dmesg`/journal, warn if > threshold.

### Follow-ups after queue fix — RIG DOWN, Radarr/Lidarr fixed, Hacks E01 desync (2026-07-09)

- **RIG IS FULLY OFFLINE (needs physical power-on)**: no LAN ping (192.168.10.12), SSH "host down", Tailscale "offline, last seen ~12h ago". Supposed to be 24/7 (suspend masked) so this is a crash or power event, not a sleep. **WoL recovery FAILED** — fired `wake-rig.sh` from mini (MAC 50:eb:f6:b5:82:c6), no response after 90s (WoL from full S5/crash isn't waking it). Impact: AI stack (ollama/litellm/open-webui), Apollo, AMP panel all down. **Action needed: user power-cycles rig physically**, then recheck. (User said they separately fixed the *mini* reboot in another window — mini not investigated here.)
- **Radarr + Lidarr got the same Post-Import Category fix** (they had the identical empty-category gap): Radarr `movieImportedCategory=radarr-imported` (v3), Lidarr `musicImportedCategory=lidarr-imported` (v1); Deluge labels created; removeCompletedDownloads stays False. All three *arr now auto-declog while seeding.
- **Hacks S01E01 — STILL UNRESOLVED (Sonarr DB quirk)**: deleted the ghost `-scene` file (user OK'd) and re-imported the pack's `-glhf` E01 via ManualImport (Copy). The file physically lands correctly (`Season 01/...S01E01...-scene.mkv`, 1.87GB, valid), episode is monitored, no conflicting episodefile record — **but `hasFile` stays False** after ManualImport ×2 + RescanSeries ×3. Content IS on disk and Plex-playable; only Sonarr's tracking is stuck (46/47 S01... i.e. still shows E01 missing). Next lever = **Sonarr container restart** to clear its internal cache (not done — mild downtime, user's call). Risk if left: Sonarr may keep trying to re-grab a "missing" E01 → lands on existing file → could re-stick the queue.

### Sonarr queue declogged 57→0 + seed-preserving architecture (2026-07-09)

- **Symptom**: Sonarr queue stuck at 57 items "for a while." Diagnosis: only **9 distinct torrents** behind 57 rows (one 48-episode season pack = 48 rows). All Deluge/torrent on the seedbox.
- **ROOT CAUSE**: Sonarr's Deluge download client had **no Post-Import Category** (`tvImportedCategory` empty) and `removeCompletedDownloads=False`. So every imported torrent stayed in the `sonarr` label, kept getting re-scanned, got pinned with an "already imported" *warning*, and never left the queue. (Deluge carried **266** `sonarr`-labeled torrents; only the warning-pinned ones showed in the queue.)
- **FIX (live, reversible — user wanted seeding preserved for ratio, NOT deletion)**:
  1. Created Deluge label `sonarr-imported` (RPC via `~/venvs/deluge/bin/python`, Label plugin).
  2. Set Sonarr Deluge **`tvImportedCategory = sonarr-imported`** → future imports auto-relabel out of the tracked `sonarr` label the moment they import → they leave the queue while Deluge keeps seeding. `removeCompletedDownloads` left **False** so nothing is auto-deleted.
  3. Relabeled the existing done torrents `sonarr`→`sonarr-imported` (Phineas&Ferb pack, South Park, both HotD, hacks, INSECURE). All 6 verified **still Seeding**.
- **Stragglers handled**: 3 dead `Sex.Life S02` downloads (0%, ratio -1, 3 days) → removed + blocklisted + re-searched. `INSECURE THE END` = an S00 special the user doesn't collect (0/42) → relabeled/kept seeding.
- **DISCOVERED pre-existing desync (NOT fixed — needs user OK, unrelated to queue)**: **Hacks S01E01** shows missing in Sonarr (9/10 S01) but a valid 1.87GB MKV (`...S01E01 - There Is No Line...-scene.mkv`, correct EBML magic) sits on disk at the library path — **Plex can play it now**. Sonarr's disk scan silently refuses to enumerate/register that specific file (RescanSeries completes, hasFile stays False; ManualImport hits "Destination already exists" because the ghost is there; folder scan lists E02–E10 but not E01). Likely fix = delete the ghost `-scene` file and re-import the pack's `-glhf` E01 (still seeding, importable) — held pending user OK since it's a deletion.
- **Reaper (user chose age-only 14d, remove+data)**: `deluge-reaper.py` on betty (`~/scripts/`), cron `0 5 * * *` CEST, `--live`. Removes `sonarr`/`sonarr-imported` torrents (+seedbox data only; NAS library is a separate copy) once age ≥14d. Dry-run now = **0 eligible** (oldest torrent 6.7d — seedbox populated ~1 wk ago); first reaps ~next week. Repo: `foss-setup/configs/host/seedbox/` (script + README).
- **Latent same-gap**: Radarr/Lidarr Deluge clients also have no Post-Import Category — apply the same fix if they clog.
- **Side observations (not acted on)**: rig SSH timed out at session start (supposed to be 24/7 — recheck); all mini containers showed "Up ~4 min" (mini rebooted recently, consistent with the DHCP-lease RCA below).

### RCA: recurring mini "freeze" = 24h DHCP lease expiry (2026-07-09)

- **Symptom**: every ~1-2 days mini stops answering everything (no ARP/ping/SSH/DNS); it's still powered ("frozen"); hard reboot fixes it. Took out `home.tabaska.us` (Homepage → mini) and, worse, mini's own AdGuard DNS.
- **NOT a freeze**: journald is persistent and logged continuously right up to each manual reboot — CPU/OS were alive the whole time. **Ruled out**: kernel panic/lockup (none in pstore or `-k`), thermal (`intel_powerclamp` fired *after* the outage; pkg ~75°C is high but not the trigger), OOM (`sbom-nightly`/`syft` OOM'd Jul-08 04:14 and the box survived — separate issue, see below).
- **ROOT CAUSE**: `enp3s0f0` is bare-DHCP netplan (`/etc/netplan/00-installer-config.yaml`: `dhcp4: true`, no static/`critical`). UniFi hands a **24h lease** (`LIFETIME=86400`, T1 12h, T2 21h). The **in-lease RENEW/REBIND path fails silently** (UniFi not honoring renewals for the existing lease; a *fresh DISCOVER* on reboot always succeeds — that's why reboot fixes it). At the 24h hard expiry, systemd-networkd **withdraws the IP and flushes every route** (`RTM_DELROUTE` burst) → box alive but off-network until power-cycle.
- **Proof / exact-24h pattern**: boot -1 acquired `Jul07 20:21:12` → routes flushed `Jul08 20:21:13` (24h to the second). boot -3 acquired `Jul02 19:40:21` → "network unreachable" storm began `Jul03 19:40:21` (again 24h). Log rate jumps ~1.3k→~13k lines/hr at the death moment (retry spam) and stays pinned until reboot. No `tg3`/carrier-down logged (link stayed up; only L3 config was pulled).
- **FIXES DEPLOYED (both reversible, verified)**:
  1. **`net-selfheal.timer`** (every 60s) → `/usr/local/sbin/net-selfheal.sh`: if default route/gateway `192.168.10.1` unreachable, escalates `networkctl renew` → link bounce → `systemctl restart systemd-networkd`, logging every step (journal tag `net-selfheal`). Guaranteed recovery in ≤60s + full capture next time. No-op verified when healthy. Repo copies: `foss-setup/configs/host/mini/net-selfheal/`.
  2. **`KeepConfiguration=dhcp`** drop-in at `/etc/systemd/network/10-netplan-enp3s0f0.network.d/10-keepconfiguration.conf` → networkd keeps the address instead of flushing it when a lease can't be renewed. Load + parse **confirmed** via invalid-value test.
- **STATIC IP — user chose to apply in the 4-7AM ET window (STAGED, not yet applied)**: proposed netplan + apply runbook committed at `foss-setup/configs/host/mini/static-ip/` (`00-installer-config.static.yaml` + `README-apply.md`). Sets `192.168.10.2/24` static, gw .1, nameservers [.2,.4,.1]. Prereq: user adds UniFi **Fixed IP** reservation for `98:5a:eb:ca:b2:ef`→.2. Apply via `netplan try` (auto-reverts). Do it before the next expiry (~Jul-10 11:55 UTC — the window lands just before). Removes the lease dependency entirely; watchdog + KeepConfiguration stay as backstop. Secondary open q: why UniFi ignores in-lease RENEW/REBIND for this client (static makes it moot).
- **Secondary (separate) issue — user chose "investigate first" (NO change made yet)**: `sbom-nightly.service`/`syft` OOMs **every night** — 7 kills total, one per run (Jul-04 04:51, 05 04:55, 06 05:24, 07 05:12, 08 04:14…), each grabbing ~6-6.5GB RSS. On this 2014 dual-core/**8GB** Mac mini (+4GB swap) running ~40 containers (~3.5GB resident at idle, Committed_AS ~16GB = 2× overcommit), syft's nightly ~6GB balloon blows past RAM+swap → global OOM. The OOM killer has (so far) correctly picked syft, but it's fragile — during the event the box thrashes into swap and networkd route ops can time out (saw `Could not set route: Connection timed out` 3 min before the Jul-08 OOM), so this may *aggravate* DHCP renewal too. **Proposed fix (awaiting go-ahead): `MemoryMax=`/`MemoryHigh=` on `sbom-nightly.service`** so syft is contained to its own cgroup and can't drag the whole box down; alternatively reduce syft scope/parallelism. Timer: `sbom-nightly.timer`, ~03:40 UTC nightly, ExecStart `/opt/scripts/inventory/sbom-nightly.sh`.
- **Ansible note**: the two fixes live only on-disk + in repo `configs/host/mini/net-selfheal/`; fold into the ansible mini role so a reprovision keeps them.

### Tracker repair + state sync (2026-07-08 night)

- **The Plan v3 guide (docs/index.html) had been rendering BLANK (0/223 tasks)** — the retro-01..07 stubs (added earlier without `host`/`type`/`estimate`, and with `detail` as an HTML string instead of the sectioned array) crashed `esc()`/`renderDetail()` before the first paint. Fixed: `esc` is now null-safe (one malformed task can no longer blank the whole tracker) and the retro tasks were filled to schema (async, hosts, verify lines, markdown-lite sectioned detail). **If you add tasks to taskData: title/host/type/estimate are required, and `detail` must be an array of `{h, body, sub, cmds}` sections — validate by loading the page.**
- **State synced to reality**: game-11 marked done (verified live on rig: `display-policy.service` active, dummy plug HDMI-A-1, Apollo dd_* per-client resolution config present). game-02 rescoped Pelican→AMP (deployed at amp.tabaska.us, licensed; remaining = human creates first Minecraft instance via web UI, then agent finishes crossplay). Stale "Pelican on the Mac mini" prose fixed. progress.json meta corrected to **124/223 (56%)**; run bars: R0 87 · R1 80 · R2 88 · R3 36 · R4 65 · R5 6 · R6 17 · R7 0.
- **Sweep at session start: 61/61 pass, 0 crit, 1 skipped** (61st = new sys-docker-subnet-squat guard). No regressions.
- Tracker has no served vhost — view via `file://` + Import progress, or any HTTP serve of docs/ (auto-merges progress.json). `.claude/launch.json` config `foss-docs` serves it on :8899 for sessions.

### Apollo resolutions + AMP Minecraft (2026-07-08 evening)

- **Apollo per-client resolution**: dd_configuration_option=ensure_active, dd_resolution_option=automatic, dd_refresh_rate_option=automatic, dd_config_revert_on_disconnect=enabled (rig ~/.config/sunshine/sunshine.conf). Follows each Moonlight client's requested res/fps, reverts after. User sets Deck=1280x800@90, TV=4K@30 client-side. Caveat: 1280x800@90 not in dummy EDID → may negotiate to 60 until the 4K120 dummy arrives.
- **Dummy plug**: HDMI-A-1, supports up to 3840x2160@30 (+4096x2160@24). Single-display policy service live (see below).
- **AMP Minecraft**: could NOT create the instance autonomously — this minimal AMP container breaks two ways: (1) API CreateInstance needs the deployment-defaults licence key which is only settable via the AMP UI (node not in settings spec); (2) ampinstmgr CLI CreateInstance hits BusyBox `su -f` incompatibility ("su: unrecognized option: f"). Both mean the FIRST instance must be born via the AMP web UI. Prepared everything else: firewall 25565/tcp + 19132/udp open (LAN+tailnet), instance admin pw at rig:/opt/stacks/amp/.mc-admin-password, runbook `configs/gaming/minecraft-crossplay-finish.md`. USER STEPS: set deployment licence in UI → create Minecraft Java instance (Paper) → install Geyser+Floodgate from plugin browser → then I verify + configure crossplay + Switch 2 (BedrockConnect DNS for the console). AMP panel healthy, no partial instance left.

### Run 5 kickoff — smart home context + plan (2026-07-08, day session)

- **Full house/device context captured** → `docs/research/11-ha-home-context.md` (71 Culver Rd profile, canonical rooms↔HA-areas table, 18-device integration map, IoT firewall policy, ~$550 Zigbee shopping list, 12 pitched opportunities, fut-01..06 future projects). Read it before touching Run 5.
- **Live HA audit** (192.168.10.50, core 2026.6.4): Hue (73 lights/21 scenes) + 2× Elgato + Matter/Thread + companion app already integrated — tracker was behind reality. ha-01/ha-02 closed with verification. 16 lights `unavailable` = wall-switch power cuts.
- **HA registry work (AI, reversible, verified)**: 4 floors created; areas renamed to canonical rooms (6 renames); Laundry/Gym/Storage areas added; all areas floor-assigned; misassigned bathtub light Kitchen→Bathroom. 4 room-name ambiguities await human answer (see context doc §open questions).
- **Long-lived HA token minted** (client "homelab-agent", 10 y) → vault `hosts.ha.api_token`; also on mini in `/etc/verification/env` as `HA_TOKEN`. Hue bridge located at **192.168.20.100 (already on IoT VLAN 20, 0 B WAN)** → vault `hue.bridge_ip`. Hue app shows stale 192.168.1.115 (pre-VLAN cache; harmless).
- **Tracker (Plan v3 → 222 tasks)**: ha-06 RESCOPED — new-in-box **ecobee Premium replaces Nest 3rd gen**, integrated locally via homekit_controller; Google SDM cloud path dropped. New tasks ha-18..ha-32 (rooms, IoT migration ledger, Level locks stay Apple-native, Roborock, Roomba, LG TVs, ThinQ, Apple TV/HomePods, VeSync, Emporia, Withings, non-integratables, sensor wave 1, automations pack, ops glue) + fut-01..06 (irrigation, plug-in solar, weather station, Meshtastic, sump, grow tent) in run 7. ha-01 stale IP fixed (.13→.50).
- **Verification**: new `checks.d/ha.yaml` (3 checks, HA_TOKEN-authed) deployed; sweep **60/60 pass, 0 crit** after committing /opt/stacks drift (AMP vhost + homepage tile — another session's work, committed+pushed+mirrored to repo).
- **Findings**: (1) Trusted→IoT is REJECTED for mini while HA (10.50) gets through — narrower than plan §1 assumes; reconcile in UniFi (ha-19). (2) Concurrent session did the TLS/Apollo work above mid-session — watch for races when two agents run at once.
- **⚠ Cloudflare token hygiene**: the token value has now appeared in TWO chat transcripts (user paste + this session's masking slip during a vault inspection). Rotation recommended: Cloudflare dash → API Tokens → Roll, update vault + Caddy env on mini, restart caddy, verify a cert renewal.

### TLS cutover + Apollo (2026-07-08 late)

- **REAL TLS LIVE**: NS delegated to Cloudflare (courtney/ryan.ns.cloudflare.com), zone active, email verified safe (MX/SPF/verification intact + Cloudflare added Proton DKIM ×3 + DMARC the old zone lacked). Flipped Caddy `local_tls` snippet from `tls internal` → Cloudflare DNS-01; **42 vhosts obtained Lets Encrypt certs** (valid→Oct 6, auto-renew). Unblocks ntfy iOS push, Kobo sync, Bitwarden repoint. Token in vault cloudflare.api_token (came via chat — user may rotate).
- **Sunshine → Apollo**: sunshine pkg removed; apollo 0.4.8 (AUR, NVENC) installed, creds vault apollo.*, KMS capture, autostart enabled, all ports listening, web UI auths, caddy apollo.tabaska.us (sunshine alias kept) w/ real cert. Docs migrated (19 files). **Display note**: rig is NOT headless — it's the user's daily workstation with a real monitor, just off when they're away. Apollo captures fine when monitor is on. For monitor-off remote streaming → HDMI/DP dummy plug (~$8, recommended) or leave monitor on. Finish test: `~/apollo-enable.sh` on rig + Moonlight pairing (needs monitor on / dummy plug).
- **AMP purchased** — license in vault cubecoders_amp.license_key. INSTALL METHOD PENDING USER DECISION: rig is their daily-driver workstation + Arch (AMP bare-metal officially supports Debian/Ubuntu/CentOS only). Options: Docker (least invasive, fits fleet) / Debian VM-LXC (official support, isolated) / bare-metal (intrusive on daily driver, unofficial distro). Recommend Docker. Not installed yet — don't install a big service on their personal machine without the method call.
- Sweep: 57/57 green.

### Interactive session (2026-07-08 daytime — rig→24/7 + big batch)

- **DECISION: rig runs 24/7** (~130W idle accepted for availability). Repo-wide contradiction sweep applied across 63 files (plans, tracker, wiki, verification, ansible, gaming docs). sleep.target/suspend.target MASKED on rig (it kept entering s2idle despite logind — KDE/PowerDevil); WoL kept only as recovery. Rig verification checks re-enabled → sweep now **57/57 green**.
- **Rig maintenance done**: pacman -Syu (441 pending → 0; corrupt proton-cachyos-native pkg + stale keyring fixed), kernel 7.1.3, reboot, containers recreated (log caps now apply), GPU 300W verified + resume hook, dead CIFS mounts (pointed at old //192.168.1.3 shares that no longer exist) cleaned.
- **Plex updated** 1.41.5 → 1.43.3 (DSM package).
- **Dependency-Track unblocked end-to-end**: admin pw reset via DB (v5 uses sha512+bcrypt-14; vault dtrack.admin_*), granted Automation team PROJECT_CREATION_UPLOAD, SBOM uploads now 200. Three root-cause bugs fixed (OOM excludes, bogus multipart Content-Type→415, PUT→POST).
- **AdGuard**: HaGeZi Multi Normal + OISD Big added to both instances (verified).
- **Mini Immich fully removed** (real compose was at ~/server/compose/immich-app, not /opt/stacks — that's why it kept resurrecting; data preserved). Maintainerr removed (no auto-deletion wanted). tdarr removed from plan (re-encode conflicts with TRaSH).
- **YouTube pipeline now actually works**: root-caused the 403s — stale/blind yt-dlp failing YouTube's JS n-signature challenge. Fix = nightly yt-dlp + bgutil PO-token provider container baked into custom metube & pinchflat images. MeTube verified end-to-end (download → /volume1/music/YouTube). beets deployed (youtube-ingest config: tag strong matches in place, quarantine weak by skip; daily DSM task id=10). bgutil-pot container on edge net.
- **litellm secrets rotated** (was CHANGE-ME pg pw + salt==webui secret): unique pg pw (role ALTERd live), salt, webui secret — all vaulted (litellm.*, open_webui.*). Sunshine web creds set + streaming ports opened (vault sunshine.*); switched to KMS capture; **awaiting your Moonlight PIN pairing**. Rig UFW scoped to LAN+tailnet (dropped Anywhere rules for 11434/3000, stale 3030); tailnet AI access re-verified.
- **wake-rig recovery**: ntfy topic `wake-rig` + host listener service on mini + homepage tile (publish → WoL). Verified.
- **Vaultwarden signups closed** (you registered). Vault additions: dtrack.*, litellm.*, open_webui.*, sunshine.*, uptime_kuma.*, beszel.* (you added the last two).
- **Handed back (creds ready, method fiddly — NOT done)**: Uptime Kuma monitors (socket.io API needs uptime-kuma-api client) and Beszel agent registration (mini agent is socket-mode; API-created rows show down; needs UI Add-System or agent→TCP + NAS/rig agent deploy).
- **Docs delivered**: docs/cloudflare-cutover.html (+ .md) and docs/game-hosting-design.html (incl. panel comparison: AMP vs Pterodactyl/Pelican/Crafty — AMP is the only one with in-game player-state tracking).

### Deep-audit second pass (2026-07-08, later the same night)

- **5 read-only agents audited the ~20 services the first sweep missed** → `docs/research/10-deep-audit.md` + report §3b. Report converted to light theme + proper HTML skeleton (was white-on-white in some viewers).
- **Fixed (all verified)**: musicseerr Lidarr key (was 401-dead) · paperless default admin password rotated (vault: paperless.*) · wallabag data-dir perms (65534) · navidrome nightly DB backup on + telemetry off · mealie+vaultwarden sqlite added to pre-backup dumps · vaultwarden ADMIN_TOKEN → argon2 PHC (login verified; compose .env needs single-quoted single-$) · mini sbom stale script → SCAN_EXCLUDES deployed (run passed old OOM point; one HTTP 415 on metube:latest image upload — watch) · seedbox 6 secret files chmod 600 · NAS rclone watchdog (flock, empty-ls=stall, find timeout, deduped container restart) fixed in repo + deployed · recyclarr restart=no + cron log off /tmp · 9 new verification checks (alerting.yaml; sweep now 52; scoped sudoers /etc/sudoers.d/verification-diun on NAS).
- **Top new decisions** (see report §3b): Stash NO AUTH · rig partial-upgrade (441 pending) · Sunshine firewall/pairing · litellm CHANGE-ME password + shared salt key · rig UFW Anywhere rules · Plex update + transcoder core dump · tdarr never-deployed / maintainerr inert · AdGuard-NAS .3 interface dead.

### Overnight remediation run (2026-07-08, post-audit)

- **Verification sweep**: 41/43 pass, 0 crit (2 fails = intentional git drift, cleared by this session's commits); rig checks 5/5.
- **restic mystery solved**: mini timer deployed 01:29 UTC, first backup succeeded 01:30:50 UTC (B2); rig backup ran 21:32 EDT; next fires Jul 9 01:30 UTC / 01:33 EDT. Dead-man pings now wired (see below).
- **Fixed on mini**: etckeeper stale index.lock (0 failed units now); healthchecks+mealie healthchecks (images dropped curl → python3 urllib); unbound root.key gitignored; zombie Immich stopped + restart=no (125 restarts; teardown still needs approval); generated inventory manifests folded into repo.
- **ntfy**: NTFY_BASE_URL=https://ntfy.tabaska.us, NTFY_UPSTREAM_BASE_URL=https://ntfy.sh (iOS push ready); read-only `phone` user created (vault: ntfy.phone_password, admin_password also vaulted). Verified publish/read/403.
- **Diun**: mini instance now publishes via http://ntfy:80 on edge network (was https vhost Go would reject; test notif verified); second Diun deployed on NAS watching 21 containers (test verified; vault: ntfy.diun_nas_token).
- **Healthchecks LIVE**: superuser bootstrapped (creds = HC_SUPERUSER_* in mini:/opt/stacks/healthchecks/.env), HC_SITE_ROOT=https://health.tabaska.us, ntfy integration + 6 dead-man checks (restic mini/rig, immich-dump-nas, ansible-pull mini/rig, verification); pings wired via systemd drop-ins on mini+rig and NAS dump script; all seeded green. Ping URLs in vault (healthchecks.*).
- **NAS DSM scheduler**: root-cause of "every 15 min" tasks only running 00:00-00:45 = `last work hour=0` in .task files; fixed tasks 4+5 + crond restart (crontab regenerated, verified). **DSM had wiped the immich-dump crontab line** — replaced with proper DSM task id=9 (02:30 daily) + new /volume1/scripts/nas/immich-db-dump.sh (pg_dumpall, size guard, 14-day retention, healthchecks ping; test run OK 16.7MB). health.env created (ntfy token). Installer script bug fixed on NAS + repo.
- **YouTube pipeline**: Plex "YouTube" library created (section 4, /volume1/youtube, Personal Media agent, scan verified); MeTube → /mnt/nas-youtube/metube + AUDIO_DOWNLOAD_DIR → /volume1/music/YouTube (end-to-end test download verified, then removed); Pinchflat → NAS confirmed + "YouTube (Plex)" media profile seeded (visible in UI). Human still adds sources/channels.
- **Security**: HSTS + access logs on all vhosts (local_tls snippet); vaultwarden /admin gated to LAN+tailnet at Caddy; fstab plaintext passwords scrubbed (all CIFS mounts → /etc/samba/cred-nas; new rw music mount /mnt/nas-music-rw). Vaultwarden signups left OPEN — 0 users, human must register first. Forgejo offsite backup confirmed already working (restic B2: repos as files + nightly pg_dump).
- **Reopened**: media-02 (Kometa) — was marked done but config was untouched template; plex url/token fixed from vault, runs still blocked on human TMDb key.
- **Blocked on creds** (not in vault, nowhere on disk): Uptime Kuma admin (0 notification channels, 34/45 services unmonitored) and Beszel hub admin (only MacBook monitored) — need creds dropped in vault or approval to reset.

### Run 0 results (2026-07-07 evening)

- **ansible-pull converges GREEN on mini** (first success ever): ok=34 failed=0, apply mode. Fixes: SOPS gates on backup+sbom roles, un-ignored break-glass pubkey, removed conflicting docker apt source on mini, chezmoi via installer on Debian.
- Repo topology fixed: forgejo `home/homelab` = foss-setup/ subtree, published via `scripts/docs/publish-deploy.sh` (fast-forwards).
- mini: /opt/stacks drift committed+pushed; etckeeper repaired; 3 dead CIFS mounts disabled (systemctl --failed = 0); maintainerr healthy; duplicate mini Immich stopped (Caddy->NAS verified).
- Secrets: leaked ntfy diun token REVOKED + rotated (vault: ntfy.diun_token); wallabag admin rotated (vault: wallabag.*). NAS AdGuard password rotation still blocked on container being up.
- migration-snapshot archived to nas:/volume1/backups/migration-snapshot-2026-07-07 (92,128/92,128 files verified).
- gpu-power-tune awk/read bug fixed in repo (deployed copy on rig pending sudo).
- Rig BLOCKED on two gates: btabaska sudo needs password (vault sudo slots empty; NOPASSWD or password needed) and rig forgejo deploy key unregistered (rig pubkey staged; register in Forgejo web or provide forgejo admin creds). Units staged at rig:~/staging/.
- HA discovered live at 192.168.10.50:8123 (creds in vault); not on tailnet yet.

### Runs 1-2 autonomous results (2026-07-07 night)

- **Verification framework LIVE** (verify-01..05): 41 checks across 7 domains; daily timer 07:15 on mini; ntfy topic `verification` (dedicated token); LLM triage on rig via ollama qwen3-coder:30b — first cycle: 35 pass, 6 fail (all expected: dns-02 x2, nas-08 dump, 3 git-drift), 6/6 valid triage verdicts; reopen-suggestions.json feeds session starts.
- **home.tabaska.us rebuilt** (home-01..04): 40-service catalog (service-catalog.yaml), 39 verified Caddy vhosts incl. ha + wiki + NAS/rig services; categorized Homepage with live widgets (vault keys, values only on mini).
- **wiki.tabaska.us LIVE** (wiki-01..04): 51 pages — hosts, 7 runbooks, operations, network + 32 generated service pages (gen-wiki-services.py); build via build-wiki.sh (pinned mkdocs-material 9.5).
- Notes: mini->rig SSH denied by tailnet ACL (rig checks are HTTP); mini->nas SSH key added; Sunshine down on rig (502 expected at the time — superseded 2026-07-08: rig is 24/7 now, a 502 is an incident); all *.tabaska.us certs are Caddy-internal CA by design (Cloudflare token would enable real certs).

### Gates cleared wave (2026-07-07 late)

- **dns-02 CLOSED (verified)**: NAS AdGuard up; missing *.tabaska.us rewrite added + enabled; admin password rotated (vault: adguard_nas). Verification cycle: ALL crit checks green fleet-wide (exit 0).
- **nas-08 CLOSED**: immich pg_dump in root crontab (02:30) + run once, fresh 16.7MB dump verified. Caveat: DSM Task Scheduler edits may rewrite /etc/crontab; freshness check is backstop.
- **game-10 CLOSED**: fixed gpu-power-tune deployed, GPU capped 300W.
- **fix-13 CLOSED**: rig ansible-pull green (ok=21 changed=9 failed=0), timer enabled; sbom-nightly timer live; NOPASSWD sudoers on rig; rig deploy key (read-only) in Forgejo.
- mini->rig SSH via LAN enabled (sshd + key). Sunshine 502 fixed (ufw allow 47990 from LAN); Moonlight stream ports 47984-48010 still closed (open when game streaming starts).
- Discovery: Dependency-Track runs on the NAS (healthy) — docs said mini; corrected. Overseerr on NAS Exited(1) 2mo ago (retire candidate, fix-18/D-list).
- Human leftovers: delete two Forgejo API tokens (Settings -> Applications: rig-setup-1783471946, token-cleanup-1783471996); tag seedbox tag:server in Tailscale; optional Cloudflare NS move for real TLS.

## Session 4 — 2026-07-07 (Plan v3)

- **Full repo + fleet audit** performed (every host inspected against the guide and configs).
- **Guide refactored into 8 staged runs** (Plan v3 in `docs/index.html`) — **194 tasks** total.
- **Regressions found and reopened:** `dns-02`, `game-10`, `nas-08` — previously marked done but no longer true on the fleet.
- **Run 0 execution started** (docs/repo reorganization, hygiene, tracker groundwork).
- Docs reorganized: validation report archived, wiki/home-hub designs moved under `docs/`, NAS schema and game-server guide moved next to their configs, root `README.md` added.

# Rollout handoff state — 2026-07-05 (session 3)

Import this into the tracker (`docs/index.html`) so checkmarks match reality for the next agent.

## Quick import (browser)

1. Open `foss-setup/docs/index.html` in your browser (file:// or served).
2. Click **Import progress** and choose `docs/progress-backup-2026-07-05.json`.

**Or** paste in DevTools console:

```javascript
fetch('../docs/progress-backup-2026-07-05.json')
  .then(r => r.json())
  .then(obj => {
    const done = obj.done || obj;
    const key = 'foss-analogue-progress-v1';
    const merged = { ...(JSON.parse(localStorage.getItem(key) || '{}')), ...done };
    localStorage.setItem(key, JSON.stringify(merged));
    location.reload();
  });
```

## Progress snapshot

| Metric | Value |
|--------|-------|
| Completed | **79 / 162** (49%) |
| Previous backup | `progress-backup-2026-07-03.json` (67 done) |
| This session | +12 tasks |

## Completed this session (2026-07-05)

| Wave | Tasks |
|------|-------|
| **DNS resilience** | dns-02 NAS secondary AdGuard (API configured, `*.tabaska.us → 192.168.10.2`) |
| **Life apps** | read-07 Wallabag, doc-01 Paperless-ngx (mini), read-14 Pinchflat |
| **Reading** | nas-09 CWA verified running, ebook-04 Libreseerr |
| **Ops** | docker-12 Diun (ntfy topic `diun`) |
| **Plex polish** | media-01 Tautulli, media-02 Kometa, media-03 Maintainerr |
| **Gaming** | game-08 WoL on rig, game-05 Sunshine installed + active |

## Ansible / glue-08 fixes pushed to Forgejo (`home/homelab`)

- `configs/ansible/files/id_ed25519.pub` (break-glass key)
- `admin_user: btabaska` in group_vars
- base role: missing pkglist manifest + check_mode fixes
- tailscale role: skip `tailscale up` when already connected

**Still partial:** ansible-pull timer runs but playbook may still fail on later roles; rig ansible-pull not deployed.

## Partial / deferred (do NOT mark done without verifying)

| Task | State |
|------|-------|
| **dns-02** | Deployed — **change NAS AdGuard admin password** (temp: set via API install; login at http://192.168.10.4:3000) |
| **dns-03** | UniFi DHCP fail-open chain — **you** (UniFi GUI) |
| **dns-04** | Outage drill — run `scripts/network/dns-resilience-verify.sh` after dns-03 |
| **dns-05** | NAT :53 + DoH blocking — **you** (UniFi GUI); only after dns-04 |
| **glue-01** | No UPS — nut-client on mini ready |
| **glue-08** | mini timer active; playbook still exits non-zero on some roles |
| **sbom-02** | mini + NAS scheduled; rig not done |
| **nas-08** | Immich healthy; pg_dump backup exists (2026-07-02); **schedule cron in DSM**; admin/Quick Sync pending |
| **read-07** | Change default Wallabag password; create API client for KOReader |
| **doc-01** | Paperless on **mini** (not NAS); complete first-visit admin wizard |
| **media-02** | Kometa needs `config/config.yml` Plex + TMDb keys |
| **read-14** | Pinchflat downloads to local `./downloads` — point at NAS YouTube library |
| **ebook-04** | Libreseerr needs Readarr API wiring in UI |
| **game-05** | Sunshine web UI pairing at https://192.168.10.12:47990 |
| **game-10** | gpu-power-tune script fixed in repo; verify service on rig |
| **B2 / sec-03 / handoff-05** | User skip until B2 ready |

## Key URLs

| Service | URL |
|---------|-----|
| Miniflux | https://rss.tabaska.us |
| Navidrome | https://music.tabaska.us |
| Mealie | https://recipes.tabaska.us |
| Wallabag | https://wallabag.tabaska.us |
| Paperless | https://paperless.tabaska.us |
| Pinchflat | https://pinchflat.tabaska.us |
| Homepage | https://home.tabaska.us |
| AdGuard (mini) | https://dns.tabaska.us |
| AdGuard (NAS) | http://192.168.10.4:3000 |
| Uptime Kuma | https://uptime.tabaska.us |
| DepTrack | https://deptrack.tabaska.us |
| Immich | https://immich.tabaska.us (LAN :2283) |
| CWA | http://192.168.10.4:8083 |
| Forgejo | http://macmini.tailb31641.ts.net:3030 |
| Libreseerr | http://192.168.10.2:8789 |

DNS: **Still gateway-only DHCP** until dns-03. Target chain: `#1` mini `192.168.10.2`, `#2` NAS `192.168.10.4`, `#3` gateway `192.168.10.1`.

## Suggested next_up

1. **dns-03** UniFi fail-open DHCP chain (~15 min in UniFi UI)
2. **dns-04** Run outage drill script
3. **read-03 / ebook-02** CWA ingest + Readarr hook
4. **ha-01** Home Assistant onboarding
5. **nas-08b** SD card import (after Immich admin)

## Secrets / hygiene

- NAS AdGuard temp admin password set during API install — **rotate immediately**
- ntfy Diun token: (rotated — see vault: `ntfy.diun_token` in `.handoff-secrets.yaml`; never store literal tokens in this doc)
- Wallabag/Paperless secrets generated on mini `.env` files — not in vault yet
- Seedbox SSH blocked by Tailscale ACL — add SSH policy for operator MacBook → betty

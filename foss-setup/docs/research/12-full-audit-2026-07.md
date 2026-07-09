# Full independent fleet audit — 2026-07-09 (Fable 5, read-only sweep)

**Method:** independent read-only sweep of every host (mini, nas, rig, seedbox) plus the
public game surface, treating every "done/live/verified/backed-up" claim in the handoff,
tracker, and progress.json as a hypothesis to test against live state. Four parallel
per-host read-only auditors + direct cross-cutting checks (playit API, split-horizon DNS,
Healthchecks ORM, restic snapshot enumeration). No service was mutated during discovery.

## TL;DR — true fleet health

**The fleet is in good shape.** The scary-sounding items in the handoff mostly held up:
rig's NVMe fix and AER monitor are real and working; the AMP Minecraft world **and** Palworld
saves **are** in rig's restic→B2; the NAS **does** have a working HyperBackup→B2 offsite
covering Immich photos + DB dumps; both AdGuards are consistent; BedrockConnect + the
featured-domain hijack are live on both resolvers; Minecraft Java+Bedrock are listening.

The real problems are a cluster of **silently-failing background jobs** that the tracker
still marks "done," plus **two monitoring checks that lie in opposite directions** (one
false-red, one masking a real failure). Nothing is on fire; several set-and-forget layers
have quietly stopped converging.

- **True verification state:** `61/63` as the timer runs it (User=btabaska), *not* the
  `63/63` the last scheduled run logged — two checks regressed since 14:15 UTC.
- **3 tasks reopened:** `glue-08` (ansible-pull failing nightly), `sbom-02` (SBOM pipeline
  dead on both hosts), `sbom-03` (etckeeper auto-commit failed).
- **Backups are genuinely healthy** across all three restic/HyperBackup targets — the one
  "backup down" alert is a false alarm (the job runs; only its dead-man ping is missing).

---

## CRIT
None. No data-loss-imminent condition, no down public service, no active security breach.

---

## HIGH

### H1 — `ansible-pull` on mini fails every night (exit 2) → fleet no longer self-converges
- **Evidence:** `journalctl -u ansible-pull.service` (mini):
  `Jul 09 04:27:09 … ansible-pull.service: Main process exited, code=exited, status=2/INVALIDARGUMENT`
  `… Failed to start ansible-pull fleet convergence (glue-08)`. Timer is `enabled`+`active`
  (next 07-10 04:35), so it fires nightly and fails nightly. Healthchecks `ansible-pull-mini`
  = **down**, last ping `2026-07-08 04:49` (the failing runs never ping).
- **Root cause:** ansible exit 2 = playbook ran but ≥1 role/task failed (consistent with the
  long-standing "playbook still exits non-zero on some roles" note). Convergence executes but
  aborts partway.
- **Blast radius:** the "set-and-forget" layer is inert on mini. Config drift is not being
  reconciled, and — critically — the DHCP mitigations (`net-selfheal`, `KeepConfiguration`,
  the staged static IP) live **only on-disk + in repo**, not in the ansible role. A reprovision
  or a successful future converge could *revert* the DHCP fixes. `ansible-pull-rig` is healthy
  (pinged 07-09 13:33), so this is mini-specific.
- **Fix:** run `ansible-pull … --limit macmini -vv` by hand to surface the failing task; fix
  that role; fold the netplan/net-selfheal/KeepConfiguration changes into the mini role so
  convergence owns them. **Effort:** M. **Risk:** low to diagnose; medium to re-enable
  (a converge that clobbers the DHCP fixes is the thing to guard against — do it in-window).
- **Tracker:** `glue-08` **reopened**.

### H2 — SBOM / Dependency-Track pipeline is dead on BOTH hosts
- **Evidence (mini):** `journalctl -u sbom-nightly` shows OOM-kills on Jul 04, 05, 06, 08
  (`syft … Killed`, `Failed with result 'oom-kill'`); the Jul 09 run didn't OOM but failed on
  `curl: (7) Couldn't connect` uploading to Dependency-Track + a DNS failure for
  `toolbox-data.anchore.io`. **Evidence (rig):** `systemctl --failed` lists
  `sbom-nightly.service` — `Failed to load environment files: No such file or directory`
  (missing env file); fails once/day at ~03:33.
- **Root cause:** mini — syft scanning `/` balloons to ~6 GB on an 8 GB box (cgroup OOM);
  plus an unresolved D-Track upload/permission path. rig — the service references an env file
  that doesn't exist.
- **Blast radius:** Dependency-Track portfolio is not being populated from either host; the
  whole SBOM/vuln-tracking objective (`sbom-01..04`) is non-functional. On mini the nightly
  ~6 GB balloon also thrashes swap and has coincided with networkd route timeouts (may
  *aggravate* the DHCP renewal path).
- **Fix:** mini — cap it (`MemoryMax=`/`MemoryHigh=` on `sbom-nightly.service`) and/or narrow
  syft scope; fix the D-Track upload (API key still needs `PROJECT_CREATION_UPLOAD` per the
  prior deep-audit). rig — create/point the missing env file or disable the timer if SBOM
  isn't wanted on rig. **Effort:** M. **Risk:** low.
- **Tracker:** `sbom-02` **reopened**.

### H3 — `etckeeper-commit.service` failed on mini → `/etc` changes not captured in git
- **Evidence:** `systemctl --failed` → `etckeeper-commit.service loaded failed failed`.
  Prior run logged `fatal: cannot lock ref 'HEAD': is at 185b37e… but expected c4cfc08…`
  (exit 128), triggered by `etc-watch.path`. Last successful /etc commit:
  `9c7b75a etckeeper: stabilize .etckeeper metadata` (a prior attempt to stabilize it that
  did not hold). This is the check failing the sweep (`sys-failed-units`, glue-03).
- **Root cause:** the `/etc` git ref is in an inconsistent state (HEAD ref mismatch), so every
  path-triggered auto-commit aborts. This is the third+ recurrence of etckeeper wedging on mini
  (prior sessions cleared stale `index.lock` twice).
- **Blast radius:** /etc changes are silently not versioned — config history/rollback for the
  most important host is broken until fixed. Working tree is currently clean (no uncommitted
  drift, no stale lock), so nothing is lost *yet*.
- **Fix:** in-window, reconcile the /etc git ref (`git -C /etc` inspect HEAD vs reflog, reset
  the ref to the real HEAD), then `systemctl reset-failed etckeeper-commit.service` and trigger
  a test commit. Consider why it keeps happening (concurrent committers? the verification
  sweep's git calls racing etc-watch?). **Effort:** S. **Risk:** low (reversible; /etc content
  untouched, only the git metadata).
- **Tracker:** `sbom-03` **reopened**.

---

## MED

### M1 — `immich-dump-nas` dead-man monitor is falsely DOWN (backup is actually healthy)
- **Evidence:** Healthchecks ORM: `immich-dump-nas` = **down**, last ping `2026-07-08 09:30`.
  BUT on the NAS: `/volume1/docker/immich/backups/immich-2026-07-09.sql.gz` dated **07-09 02:30,
  16.6 MB**; DSM task id=9 enabled + fired; and the dump is inside HyperBackup→B2. The script's
  `PING_URL` UUID (`…182809d3b77a`) **matches the vault** exactly, and NAS→mini:8001 is reachable
  now (curl → 302, 3 ms).
- **Root cause:** the DSM-scheduled 02:30 run's ping isn't landing (a manual 09:30 run's did) —
  the ping is a best-effort `curl … || echo WARN` at the end of the script, and the scheduled
  run's environment/timing drops it. So the monitor shows down regardless of backup health.
- **Blast radius:** the dead-man for the Immich DB backup is **untrustworthy** — it cries wolf,
  which trains the operator to ignore it, and a *real* dump failure would look identical to this
  false-down. This is the more dangerous failure mode of the two monitoring lies.
- **Fix:** make the scheduled ping reliable (log its HTTP result; ping via a wrapper that runs
  in the same env as the manual path; or ping `/start` + `/success`/`/fail` so partial failures
  are distinguishable). **Effort:** S. **Risk:** low.
- **Tracker:** `nas-08` **NOT reopened** — Immich is deployed, healthy (v2.7.5, `/api/server/ping`
  → pong), dumped daily, and offsite. Only the monitor needs repair.

### M2 — mini static IP still not applied → 24h DHCP-lease outage root fix outstanding
- **Evidence:** `/etc/netplan/*.yaml` = `dhcp4: true` only; `ip route` default `proto dhcp`.
  Mitigations ARE live and working: `KeepConfiguration=dhcp` drop-in present; `net-selfheal.timer`
  active, firing every 60 s cleanly.
- **Root cause / blast radius:** the permanent fix (static IP + UniFi reservation) is staged but
  needs the 4-7 AM window + a UniFi Fixed-IP reservation (user step). Until then the box relies on
  the watchdog + KeepConfiguration backstop to survive lease expiry (~24h cadence).
- **Fix:** apply staged netplan via `netplan try` in-window after the UniFi reservation exists.
  **Effort:** S. **Risk:** medium (network cutover — `netplan try` auto-reverts).

### M3 — rig `/boot` 68% full → snapper skipping boot-menu entries for new snapshots
- **Evidence:** `/boot` 1.4G/2.0G (68%); `limine-snapper-sync` logs hourly
  `Boot partition usage from 67.1% to 90.1% … will exceed the 85.0% limit` → new boot entries
  **skipped** (~11×/day).
- **Blast radius:** btrfs snapshots are still being *created*, but they won't have limine boot
  entries — so booting directly into a recent snapshot from the menu isn't available. Not
  service-affecting today.
- **Fix:** prune old kernels/boot entries (`limine-snapper-sync` cleanup or remove stale
  `/boot` entries). **Effort:** S. **Risk:** low (don't delete the running kernel).

### M4 — Palworld public access is NOT live (no playit tunnel)
- **Evidence:** `POST api.playit.gg/tunnels/list` returns exactly **2 tunnels** — `minecraft-java`
  (14450 → 127.0.0.1:25565) and `minecraft-bedrock` (58804 → 127.0.0.1:19132), both active.
  **No UDP tunnel to 8211.** `udp_alloc: claimed 1/4`. Server itself is healthy (v0.7.3.90464,
  REST 8212 → 401 = up, 8211/udp listening, local+restic backups running).
- **Root cause:** the agent API key is read-only; adding the Palworld tunnel is a dashboard-only
  step the user hasn't done. Also: playit account `account_status=email_not_verified` (from the
  agent logs) — unverified accounts risk tunnel caps/expiry.
- **Fix (user):** playit dashboard → Add Tunnel → Palworld (UDP 8211 → 127.0.0.1:8211) on the
  existing `tabaska-home-agent`; verify the account email. **Effort:** S (user). **Risk:** none.
- **RESOLVED (concurrent session, 2026-07-09 eve):** user upgraded to playit.plus, recreated all
  tunnels on a **dedicated IP** (Java/Bedrock/**Palworld** all verified) and **verified the account
  email**. The 2-free-tunnel / no-Palworld / unverified-email state above is superseded — see the
  "playit PREMIUM cutover" handoff entry.

### M5 — 21 of 31 mini `/opt/stacks` `.env` files are world-readable and contain secrets
- **Evidence:** `find /opt/stacks -name .env -perm -o=r` → 21 hits (`-rw-r--r--`), ≥8 with
  literal password/token/secret values (ntfy, diun, frigate, healthchecks, dependency-track,
  paperless-ngx, wallabag, libreseerr). Values not printed.
- **Blast radius:** any local user or a container with host-FS access can read fleet secrets.
- **Fix:** `chmod 640` (or 600) the `.env` files; verify containers still read them.
  **Effort:** S. **Risk:** low (verify each stack post-chmod).

### M6 — verification sweep is fragile when run as root (produces 9 false failures)
- **Evidence:** run as `btabaska` (how `verification.service` runs it, `User=btabaska`) →
  **61/63**. The same `run-checks.sh` under `sudo` (root) → **54/63, 9 failed (4 crit)** — the
  extra 7 failures are all `Host key verification failed` / `Could not resolve hostname rig`
  because root has no `known_hosts` and no ssh `Host` aliases. `restic-snapshot-fresh-rig` and
  `nas-ssh` depend on btabaska's ssh config (`Host nas → nas.tailb31641.ts.net`,
  `Host rig → 192.168.10.12`).
- **Blast radius:** an operator or agent who runs the sweep with `sudo` (reasonable, since many
  checks call sudo internally) gets a wildly misleading "NAS is down / 4 crit" picture. During
  this audit that exact artifact briefly looked like a NAS outage — it wasn't.
- **Fix:** guard `run-checks.sh` to refuse/​warn when `EUID==0`, or make the ssh-based checks
  user-agnostic (explicit `known_hosts`/`-o UserKnownHostsFile`). **Effort:** S. **Risk:** low.

### M7 — Kometa's last run hit a ConnectionError (watch, not yet a regression)
- **Evidence:** `docker logs kometa` — last cycle raised `tenacity.RetryError[… ConnectionError]`
  then resumed its schedule (next run 05:00). Container Up, image pinned `kometateam/kometa:v2.3.1`.
- **Interpretation:** likely a transient Plex/TMDb reach failure (possibly during the NAS's
  evening HyperBackup load). Not reopening `media-02` on a single transient; watch the 05:00 run.
  **Effort:** — **Risk:** low.

---

## LOW / documentation

- **L1 — rig OS drive is a WD Blue SN770, not SN570.** SMART model `WDS200T3X0C-00SJG0` (SN770)
  at PCI `0000:74:00.0` — matches the AER-monitor target exactly, so monitoring is correct; only
  the model string in the handoff/memory is wrong. *(Corrected in memory + handoff this session.)*
- **L2 — `ssh seedbox` alias is broken.** The FQDN `seedbox.tailb31641.ts.net` times out on :22;
  the host is reachable via `ssh -o HostKeyAlias=seedbox.tailb31641.ts.net btabaska@100.119.134.94`.
  Deluge RPC is on **:3254**, not the :58846 some docs reference.
- **L3 — world-readable secret backup on seedbox.** `~/slskd-native/slskd.yml.bak-2026-07-07`
  is `-rw-r--r--` with ~14 secret-bearing keys (the live `slskd.yml` is correctly 600).
- **L4 — rig firewall/creds nits.** `6112/udp` open to Anywhere (Blizzard LAN discovery, low
  risk); `/etc/restic/env` holds a plaintext `NTFY_TOKEN` alongside the (redacted) B2 secrets;
  ollama binds `*:11434` but UFW correctly scopes it to LAN+tailnet (not world-exposed).
- **L5 — CWA `book_format_checksums` table missing** → repeated non-blocking DB errors; Kobo
  sync works regardless (live sync traffic confirmed 07-09). Likely a pending migration on v4.0.7.
- **L6 — unpinned `:latest` images:** mini (bedrock-connect, romm, bgutil-pot, libreseerr),
  nas (rreading-glasses). Diun watches both and notifies, so drift is caught.
- **L7 — cruft:** 8 dangling docker volumes + several linkdown `br-*` networks on mini
  (no functional impact); seedbox `tv-sonarr`/`readarr` labels defined with 0 torrents.

---

## Monitoring blind spots (what could break tomorrow with no alert)

1. **SBOM job failures trip no check** — mini has OOM'd nightly for a week and rig fails on a
   missing env file; nothing in verification or Healthchecks flags it. (Would be caught by a
   dead-man ping on `sbom-nightly` on each host.)
2. **The Immich dead-man lies (M1)** — a genuine Immich DB dump failure is indistinguishable
   from the current false-down, so a real backup loss would go unnoticed.
3. **Kometa run failures unmonitored** — the container being "Up" says nothing about whether the
   nightly collections run succeeded.
4. **mini memory pressure has no proactive alert** — the only signal is the OOM killer after the
   fact (Beszel memory alert is 90% but the syft balloon is a short spike the poll may miss).
5. **The sweep behaves differently as root (M6)** — no guard, so a sudo run silently misreports.
6. **etckeeper failure only surfaces via `sys-failed-units`** — a coarse count; if two units are
   failed for different reasons the check can't tell them apart.

---

## Tracker re-verification (sampled "done" claims vs live state)

| Task | Claim | Live state | Verdict |
|---|---|---|---|
| `game-02` | Minecraft crossplay live on rig | AMP `Main`+`MinecraftCross01` both Up, ADS :8080 → 200; Java 25565 + Bedrock 19132/udp listening | **TRUE** |
| `nas-08` | Immich on NAS + pg_dump | Immich v2.7.5 healthy, dump fresh (07-09 02:30, 16.6 MB), offsite in B2 | **TRUE** (monitor ping broken — M1) |
| `dns-02` | NAS secondary AdGuard + `*.tabaska.us` rewrite | 11 rewrites present+enabled on .4; resolves `→192.168.10.2` | **TRUE** |
| `media-02` | Kometa (Plex+TMDb) wired | Container Up, pinned; last run ConnectionError (M7) | **TRUE** (watch) |
| `retro-01/02` | RomM live on mini | (not individually re-probed; container present) | assumed TRUE |
| rig NVMe fix | AER storm stopped + monitor live | `/proc/cmdline` has both params; AER=0; `pcie-aer-monitor.timer` firing every 20 min | **TRUE** |
| AMP world backup | world in restic→B2 | snapshot `39763ef8` contains `MinecraftCross01` world + Palworld saves | **TRUE** |
| `glue-08` | ansible-pull self-converges | fails exit 2 nightly | **FALSE → reopened** |
| `sbom-02` | nightly SBOM → D-Track | dead on both hosts | **FALSE → reopened** |
| `sbom-03` | etckeeper auto-commit | service failed | **FALSE → reopened** |

---

## Verified clean (coverage appendix — a clean subsystem is a result)

**rig:** kernel NVMe/PCIe params present; AER count 0 since boot; AER→ntfy monitor alive+firing;
OS-drive SMART clean (0 media errors, 1% wear, 38 °C); all 8 containers Up, 0 restarts; AMP both
instances + ADS 200; Minecraft Java+Bedrock listening; Palworld healthy + local+restic backups;
ollama/litellm/open-webui/mcpo up; restic BACKUP_PATHS include Palworld saves + MinecraftCross01
world, latest snapshot `39763ef8` verified; RAM/disk/GPU ample; `.env` all 0600; UFW default-deny
with sensitive ports scoped to LAN+tailnet.

**mini:** 38 containers, 0 exited/restarting/unhealthy, 0 restart counts; RAM 4.1/7.8 GB, swap
60 MB, load 0.38, disk 24%; no kernel OOM since 07-07; IP correct, net-selfheal firing,
KeepConfiguration present; `/opt/stacks` git clean; BedrockConnect Up + 19132/udp listening + all
10 featured-domain hijacks + `*.tabaska.us` → .2; Caddy 43 vhosts, **no cert obtain/renew errors**;
restic 2 snapshots (07-08, 07-09) daily w/ retention, paths cover `/opt/stacks`+`/etc`+dotfiles.

**nas:** 24 containers all running; full *arr stack + Immich (4 containers healthy) + CWA + secondary
AdGuard + Diun + Beszel agent; DSM 7.2.2u5 current; HyperBackup→B2 (id=7 19:20) ran 07-08 20:02
covering /photo+/docker+/docs+/homes+/backups; immich dump fresh; rclone seedbox mount healthy +
watchdog passing; RAID all `[U]` healthy, volumes 8/22/42%; 16 GB RAM free; no dmesg errors.

**seedbox:** deluge + deluge-web up (RPC :3254); 273 torrents; declog labels
`sonarr-imported`/`radarr-imported`/`lidarr-imported` present (Post-Import Category fix in place);
reaper script safe (defaults dry-run, 14d age-only), dry-run 0 eligible; slskd up + logged in;
quota 776 G / 2.86 T (~27%); config files 600 (except the .bak, L3).

**DNS / TLS:** `tabaska.us` NS delegated to Cloudflare (courtney/ryan.ns.cloudflare.com), zone
active — cert renewal path intact. Split-horizon correct: `*.tabaska.us` resolves only internally
(→192.168.10.2 on both resolvers), nothing leaked to public DNS. Both AdGuards return identical
answers for hijacked + internal names.

**playit:** agent `tabaska-home-agent` online, both MC tunnels active + serving (Java tunnel had
live TCP clients); allocations 1/4 TCP + 1/4 UDP.

---

## Recommended fix order

1. **H3 etckeeper ref** (S, in-window) — restores /etc versioning; cheapest real win.
2. **M1 immich dead-man ping** (S) — stop the monitor from lying before it masks a real loss.
3. **H2 SBOM** (M) — cap mini's syft, create rig's env file, finish the D-Track grant.
4. **H1 ansible-pull** (M, in-window) — diagnose the failing role; fold in the DHCP fixes.
5. **M2 static IP** (S, in-window + UniFi step) — retire the DHCP-lease outage class entirely.
6. **M5 .env perms** (S), **M3 /boot prune** (S), **M6 sweep root-guard** (S).
7. **M4 Palworld tunnel + playit email** (user), then verify public reachability.

---

## Remediation applied (2026-07-09, same session, user-authorized)

After the read-only audit, the user directed: retire SBOM, fix the hygiene issues,
and take care of all recommended fixes (window items to run tonight). Applied and
verified:

| # | Fix | Verification | State |
|---|---|---|---|
| H1 | **ansible-pull** — accepted the `ondrej/php` apt releaseinfo change (`apt-get update --allow-releaseinfo-change`); the failing task was the apt-cache update. | Real converge via `systemctl start ansible-pull.service`: `ok=30 changed=3 failed=0`; `ansible-pull-mini` Healthchecks now **up**. | ✅ glue-08 re-closed |
| H2/#4 | **SBOM retired** (user decision) — disabled+stopped `sbom-nightly.timer` on mini **and** rig; removed the `sbom` role from `ansible/site.yml` so convergence won't redeploy it. | mini + rig timers `disabled/inactive`; converge did NOT re-enable sbom. | ✅ sbom-01/02/04 retired |
| H3 | **etckeeper** — cleared the stale `/etc/.git/index.lock` + reset the failed unit; later broke the ref-lock race by briefly stopping `etc-watch.path` for a clean `etckeeper commit`. | `systemctl --failed` empty; `/etc` clean; commits succeed; `sys-failed-units` + `git-etckeeper-clean` both pass. | ✅ sbom-03 re-closed |
| M1 | **immich dead-man** — hardcoded `/bin/curl` in `immich-db-dump.sh` (DSM cron's minimal PATH couldn't find bare `curl`); ran it to verify. | `immich-dump-nas` Healthchecks flipped **up** (ping 20:23). | ✅ |
| M3 | **rig /boot** — lowered `MAX_SNAPSHOT_ENTRIES` 8→4 in `limine-snapper-sync.conf` (backup kept); `limine.conf` intact. | Config applied; space reclaims on next kernel/snapshot regen (did **not** force an initramfs regen on the daily driver). | ✅ (root cause) |
| M5 | **mini `.env` perms** — `chmod o-rwx` on all `/opt/stacks/*/.env`. | world-readable count 21 → **0**. | ✅ |
| M6 | **sweep root-guard** — `run-checks.sh` now warns (overridable via `VERIFY_ALLOW_ROOT=1`) when run as root. | warns as root; silent + green as btabaska. | ✅ |
| — | **fix-19 regression** (found while remediating H1) — the ansible docker role's daemon.json template omitted `default-address-pools`, so every converge stripped fix-19 and bounced docker. Restored the pools in the role template **and** in mini's on-disk daemon.json. | daemon.json has all 3 keys; committed. **Pools apply on the next docker restart** (not forced now to avoid a second container bounce). | ✅ |
| L3 | **seedbox** — `chmod 600 slskd.yml.bak`. | now `-rw-------`. | ✅ |
| M2 | **static IP** — deployed a **guarded, self-testing, auto-reverting** apply (`/usr/local/sbin/apply-static-ip.sh`) + one-shot timer for **08:35 UTC / 04:35 EDT tonight**. Applies the static netplan, self-tests (IP + gateway + external + DNS), and reverts to DHCP + pings ntfy if anything fails. | timer armed (`apply-static-ip.timer`, next 2026-07-10 08:35 UTC). ⚠️ Still needs the UniFi Fixed-IP reservation for `98:5a:eb:ca:b2:ef`→.2 to prevent a future lease conflict (the ntfy on success reminds of this). | ⏳ scheduled |

**Final sweep after remediation: `63/63 passed, 0 failed, 0 crit, 1 skipped`** (seedbox SSH, known ACL). All 38 mini containers healthy after the one converge-induced docker bounce.

**Left to the user (per their instructions):** NTFY token rotation (M-hygiene — the NAS `health.env` token surfaced in the audit output); the Palworld playit tunnel + account-email verification (handled in a separate agent); and adding the UniFi Fixed-IP reservation before/after tonight's static-IP apply.

**Note on the docker bounce:** the first successful ansible converge in a while applied the daemon.json log-cap config, which restarted Docker once and bounced all mini containers (~1 min recovery, verified all 38 back healthy). Future converges are idempotent (on-disk daemon.json now matches the role template).

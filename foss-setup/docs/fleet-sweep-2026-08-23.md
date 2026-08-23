# Fleet sweep — 2026-08-23 (ultracode full read-only audit)

> **Method**: `/fleet-sweep` full run orchestrated for the "ultracode full-fleet holistic audit" — read-only auditor lanes fanned out via the Workflow tool across six phases: Phase 1 verification triage (audit-safe full run 394 checks → 358 pass/30 fail/6 skip, one triage lane per non-pass + skips + baseline delta), Phase 2 per-service deep scans (103 service + host lanes, one agent per deployed service), Phase 3 end-to-end chain probes (39 chains), Phase 4 cross-cutting (coverage/exposure/secrets/tracker/open-queue), Phase 5 adversarial verification (51 refutation skeptics + completeness critic + gap-fillers), Phase 6 clustering. ~222 lanes, ~16.2M subagent tokens, ~4,700 tool calls across the fan-outs. The run started on Fable 5, hit the Fable usage limit mid-Phase-2, and completed on Opus 4.8 (workflow resume replayed cached lanes, re-ran the errored ones).
> **Nothing was modified on any host.** The only mutations of the entire sweep were the authorized self-cleaning e2e probes already deployed under `/opt/verification/bin` (journaling-e2e, bug-intake-e2e), a single-file restic **restore drill** to a scratch dir on mini (first-ever restore proof, scratch removed), scratch `VERIFICATION_STATE_DIR` under `/tmp/verify-audit-uc` on mini, and the repo artifacts of this commit. No host config, container, unit, or package was changed.
> Machine-readable twin: `fleet-sweep-2026-08-23.json` (severity-sorted; position within each block derives the id — `UC1…` critical, `UH1…` high, `UM1…` medium, `UL1…` low, `UI1…` info). Work items: `fleet-sweep-2026-08-23-worklist.md` → new tasks `fix-82`…`fix-104`, drive with `/resolve-finding fix-NN`.
> Lane roster: triage:<per-failing-check> · svc:<per-service ~103> (caddy, adguard, unbound, homepage, kuma, healthchecks, beszel, scrutiny, syncthing, seerr, musicseerr, libreseerr, tautulli, kometa, navidrome, metube, pinchflat, bgutil-pot, paperless, wallabag, miniflux, booklogr, mealie, memos, n8n, faster-whisper, romm, forgejo, ntfy, diun, dockge, photon, pmtiles, searxng, wiki, mini-host-units · llama-swap, litellm, open-webui, comfyui-stack, mcpo, fleet-mcp, bioclip, unsloth-studio, ldr, kokoro, ollama-shim, marinara, lumiverse, immich-ml, amp, palworld, playit, suwayomi, rig-host-timers · deluge, slskd, seedbox-glue · ha-core, ha-integrations · plex, jellyfin, adguard-nas, abs, bazarr, bitmagnet, cwa, kiwix, komga, prowlarr, sonarr, radarr, lidarr, soularr, beets, rreading-glasses, bookshelf, mylar3, scrutiny-hub, shelfmark, stash, syncthing-hub, immich, nas-dsm-tasks · host:mini|nas|rig|seedbox|ha) · flow:movies-tv|music|books-kobo|shelfmark-mam|audiobooks-ipod|manga-comics|photos-ml|youtube|subtitles|kometa|journaling|ai-chat-serving|ai-ops-agent|ai-web-search|local-deep-research|offline-zim|wiki-rag|plant-scout|offline-maps|voice-tts-stt|ai-image-gen|opencode-memory|owui-code-exec|unsloth-studio|remote-ai-coding|bug-intake-triage|monitoring-alerting|disk-smart|backups-restore-drill|syncthing-mesh|git-control-plane|edge-dns|home-assistant|game-servers|retro|adult-whisparr-stash|reading-web|chat-bakeoff · meta:<per-checks.d-domain ×41> · cross:coverage-tripwire|lan-exposure|secrets-hygiene|docs-tracker-truth|open-queue-reality · completeness-critic.

**Totals: 951 findings — 4 critical / 4 high / 121 medium / 251 low / 571 info** (11 candidates refuted during adversarial verification; 18 severity-adjusted; cross-lane duplicates merged during consolidation).

---

## CRITICAL (4)

### UC1. restic B2 bucket is NOT immutable — governance-mode lock, deletable by a compromised key `known-issue`
**Host:** mini · **Component:** B2 bucket-restic object-lock (fix-22) · **Auditor:** flow:backups-restore-drill · **Work item:** `fix-82` · *skeptic-confirmed*

Known crit from the 10:29 + 22:23 baseline (task fix-22), RE-VERIFIED still holding. b2-bucket-guard.py --immutable reports mini/config carries only a GOVERNANCE-mode retention lock (bypassable by any key with bypassGovernance), not COMPLIANCE-mode, so a ransomware/compromised-key actor could delete the restic snapshots. Backups are fresh and (now) proven restorable, but they are NOT tamper-proof. NOT fixed — read-only audit. (Re-running the guard standalone errors 'B2_OPS_KEY_ID/B2_OPS_KEY not set' because it needs the verification runner env; per the env-source-leak rule I did not source /etc/verification/env — citing the authoritative failing output from the 22:23 EDT runner instead. Companion check b2-bucket-policy still PASSes: both buckets present.)

*Verify note:* Fresh probes reproduce the crit defect: today's authoritative daily run (results.json, mtime 2026-08-23 10:29:25 EDT) fails b2-restic-immutable with the identical output, and the restic bucket's sampled config version is genuinely unprotected — so "restic B2 bucket is NOT immutable / critical / fix-22 reopen" HOLDS. Mini clock (2026-08-23 21:40 UTC) matches my local clock, no RTC skew; the lone PASS I found (results-mini.json "IMMUTABLE ... sampled=3 locked") is STALE — mtime 2026-08-14 13:42 EDT, i.e. before the 2026-08-16 expiry — not a live refutation. HOWEVER the finding's STATED MECHANISM is a misdiagnosis and must not be actioned as written: it claims the fault is a "governance-mode lock (bypassable by bypassGovernance), not COMPLIANCE-mode." The guard source refutes that — governance IS the intended/required mode (EXPECTED["bucket-restic"].retention_mode="governance"; b2-bucket-guard.py lines 44, 109, 123 all mandate governance; compliance is never wanted). The check fails on the SECOND clause at line 124, retainUntilTimestamp <= now_ms: the per-file lock EXPIRED. retainUntil=1786887603882 = 2026-08-16 13:40:03 UTC, 7 days in the past (fix-22's one-time 2026-07-17 +30d backfill elapsed and nothing re-stamps never-rewritten files). The sibling triage finding at index 14 has the correct root cause (expiry, 1239 versions decayed). Severity stays critical (NOT downgraded): an EXPIRED lock is if anything worse than the finding implies — deletion needs no bypassGovernance capability at all. Net: defect real and live; keep the reopen, but adopt index 14's expiry mechanism and discard the "switch to compliance mode" framing.

<details><summary>Evidence</summary>

```
results.json (2026-08-22T22:23 runner): id=b2-restic-immutable status=fail sev=crit task=fix-22
cmd: python3 /opt/verification/bin/b2-bucket-guard.py --immutable
out: 'BAD file mini/config not retention-locked: {"mode": "governance", "retainUntilTimestamp": 1786887603882}'
companion: b2-bucket-policy=pass -> "POLICY-OK buckets=['bucket-hyper-backup', 'bucket-restic']"
```

</details>

### UC2. bucket-restic object-lock immutability decayed: 1239 file versions expired incl. both repos' config+keys — reopen fix-22 `known-issue`
**Host:** mini · **Component:** backups/b2-object-lock (fix-22) · **Auditor:** triage:b2-restic-immutable · **Work item:** `fix-82` · *skeptic-confirmed*

Failing since 2026-08-16 (first /var/lib/verification/triage-2026-08-16.md entry; daily 10:29 EDT run). Root cause: fix-22 (commit ec4d78b, 2026-07-17) applied a ONE-TIME 30d governance backfill to all pre-existing files — retainUntil = 2026-07-17 + 30d = 2026-08-16 13:40:03 UTC, exactly the failing file's timestamp (1786887603882 ms). B2 default retention only protects each file version for 30d after ITS upload and nothing re-stamps, so protection decays permanently for never-rewritten files. Live re-verified scope (read-only listing, full bucket pagination): 1239/5673 upload versions EXPIRED (0 with no mode) — mini/config, rig/config, mini/keys (1), rig/keys (1), 488 mini + 704 rig data packs, 30 snapshots, 13 index files; everything uploaded 2026-07-08..2026-07-23, and the set GROWS DAILY as uploads cross 30d (2026-07-23 packs expired this morning 05:40 UTC). Restic dedup means current snapshots reference those July packs, and deleting config or keys destroys the whole repo — so effectively no snapshot is fully object-lock protected. Compensating controls verified still holding: ops key caps clean + lock enabled + default governance/30d all pass (check fails only at the per-file step), b2-bucket-policy POLICY-OK tonight, newest uploads auto-locked to 2026-09-21, host keys append-only, delete-capable master key offline — but object lock was built to be independent of key hygiene (guard docstring: 'even if every config assertion above rots'), and that layer is now void for all >30d data. Side effect: the check exits before its live delete-refusal (401) probe, so that leg is also unverified since 2026-08-16. Known-residual: fix-22 reopen candidate per today's baseline; fix-22 is in progress.json 'done', NOT yet in 'reopened' — this triage confirms reopen with expanded scope. Structural fix needs a decision (periodic re-stamp job with retainUntil comparison, or accept+document a rolling-30d-only guarantee). NOT fixed per read-only mandate. Note: the 2026-08-16 auto-triage diagnosis ('lock step was skipped') was wrong — it is expiry, not a skipped step.

*Verify note:* Tried to refute on four angles; all failed. (1) Stale-cache: found results-mini.json showing b2-restic-immutable PASS "IMMUTABLE ... sampled=3 locked, delete-probe=401" — but its run_ts is 2026-08-14T13:42, BEFORE the 08-16 decay date, so it is the pre-decay pass, not a refutation. The comprehensive run that generated today's triage-2026-08-23.md failed it. (2) Check-bug/sampling: read check_immutable() — it lists only the first SAMPLE_VERSIONS=5 file versions in lexicographic order; "mini/config" sorts first in the bucket namespace, so it is checked deterministically every run, not randomly. Its retainUntilTimestamp 1786887603882 = 2026-08-16 13:40:03 UTC = fix-22 ship 2026-07-17 + 30d exactly, now in the past → deterministic hard-fail. Real breakage, not a sampling artifact. (3) RTC skew: N/A — this is mini (authoritative clock, verified Sun Aug 23 17:46 EDT). (4) Transient backup-window: triage files exist for 08-16,17,18,19,21,22,23 — chronic daily since the retainUntil crossed, not a self-clearing spike. Compensating controls the finding lists (offline master key, append-only scoped ops key with FORBIDDEN_CAPS incl bypassGovernance, governance/30d default) reduce exploitability but this is a defense-in-depth backup-immutability control that is now void for all >30d data (restic dedup means live snapshots reference the expired July packs); baseline + independent index-3 lane both classify fix-22 crit. Severity critical stands. Not independently re-run: the full-bucket pagination that produced the exact 1239/5673 count (needs scoped ops key + heavy read); the load-bearing core (config+keys expired, repo not immutable, chronic fail) is deterministically proven without it. known_issue=true, fix-22.

<details><summary>Evidence</summary>

```
Tonight's run (results.json): b2-restic-immutable fail exit=1: BAD file mini/config not retention-locked: {"mode": "governance", "retainUntilTimestamp": 1786887603882}
$ python3 -c 'import datetime; print(datetime.datetime.fromtimestamp(1786887603.882, datetime.timezone.utc))' -> 2026-08-16 13:40:03.882 UTC (fix-22 ship date 2026-07-17 + 30d)
$ git log --oneline -- foss-setup/verification/bin/b2-bucket-guard.py -> ec4d78b 2026-07-17 fix-22: make restic B2 backups actually immutable
$ ssh mini 'grep -l b2-restic-immutable /var/lib/verification/triage-*.md' -> first hit triage-2026-08-16.md, then every day 08-17..08-22 (attempts 1 each)
Read-only listing (ssh mini sudo python3, B2_OPS_KEY_ID/B2_OPS_KEY parsed from /etc/verification/env inside the process, b2_list_file_versions paginated 1000/page, no secrets printed):
 total_upload_versions=5673 other_actions=1228
 status_counts={'EXPIRED': 1239, 'LOCKED': 4434}
 unprotected_by_prefix={'mini/config': 1, 'mini/data': 488, 'mini/index': 5, 'mini/keys': 1, 'mini/snapshots': 9, 'rig/config': 1, 'rig/data': 704, 'rig/index': 8, 'rig/keys': 1, 'rig/snapshots': 21}
 mini/config EXPIRED uploaded 2026-07-08 01:30 retainUntil 2026-08-16 13:40
 mini/data/00/008373bb... EXPIRED uploaded 2026-07-23 05:40 retainUntil 2026-08-22 05:40 (expired TODAY — rolling decay)
 unprotected upload dates: oldest 2026-07-08 01:30 newest 2026-07-23 05:44
 newest-5 by uploadTimestamp: all LOCKED retainUntil 2026-09-21 (rolling default retention works for new uploads)
```

</details>

### UC3. KNOWN (fix-22): B2 restic bucket is NOT immutable — a live delete is not refused 401 `known-issue`
**Host:** mini · **Component:** restic-backup B2 bucket (adjacent to restic-backup unit) · **Auditor:** svc:mini-host-units · **Work item:** `fix-82` · *skeptic-confirmed*

The restic-backup UNIT itself is fully healthy (see restic green finding), but the remote B2 bucket lacks object-lock/immutability: the audit check 'bucket-restic is actually immutable (retention + live delete refused 401)' FAILED in last night's audit-safe run. This means a compromised RESTIC/B2 key could delete or prune backups (no ransomware-grade immutability). Backups themselves exist and are current. Classified known_issue fix-22 (CRIT b2-restic-immutable) per the pre-existing failure baseline. NOT re-run live and NOT fixed per read-only mandate — the immutability probe attempts a live delete (mutating), so I relied on the 2026-08-22 22:23 audit result rather than re-executing it; the residual still stands as of that run.

*Verify note:* Independently reproduced via a fresh read-only B2 API query (not the runner cache the finding relied on). mini/config, rig/config, mini/keys and rig/keys all carry governance retention with retainUntil=2026-08-16, which is EXPIRED against mini's authoritative clock (2026-08-23 21:56 UTC, ~7.3 days past) — the object-lock immutability layer is void for the restic repo config+keys, so a compromised delete-capable key could destroy the repo (restic dedup). Not stale (expiry 7d old, growing daily), no RTC skew (mini clock, not rig), not operator-intent (fix-22 is an OPEN known CRIT; bucket-restic is REQUIRED locked in the guard manifest, unlike ACCEPTED-unlocked bucket-hyper-backup), not a check-bug (verified raw B2 state directly). Sole imprecision is the title's 'live delete not refused 401' framing: the check actually fails at the per-file retention-lock step and the read-only ops key delete would still 401 (it lacks deleteFiles) — but the substantive CRIT claim and severity stand. Corroborated by results.json (b2-restic-immutable=fail crit fix-22) and audit findings idx 3 and idx 14.

<details><summary>Evidence</summary>

```
$ python3 parse /tmp/verify-audit-uc/results.json (runner 2026-08-22T22:23:20-04:00): 'fail | bucket-restic is actually immutable (retention + live delete refused 401) | mini'
```

</details>

### UC4. btrfs data checksum corruption incrementing on single-device root FS (3 files, latest 10 min before scan) while SSD SMART is clean
**Host:** rig · **Component:** btrfs / nvme2n1p2 (root+/home, WDS200T3X0C SN850) · **Auditor:** svc:host-rig · **Work item:** `fix-83` · *skeptic-confirmed*

rig's root+/home single-device btrfs (nvme2n1p2, no mirror redundancy) has logged three unrecoverable data-checksum failures, and the count is climbing: mount-time baseline corrupt 1 (Aug 03), then Aug 20 04:45:46 (root 257 ino 85429), then Aug 23 15:49:03 TODAY (root 256 ino 1626645) — the newest ~10 min before this scan. `btrfs device stats` now reads corruption_errs 3 with wr/rd/flush all 0. No forced RO remount / transaction abort yet — the RW write-probe check still passes — so this is the leading edge of taxonomy pattern #1 (btrfs corrupt leaf -> RO cascade), not yet a cascade. Notably the drive's own SMART reports Media and Data Integrity Errors: 0, Error Information Log Entries: 0, Percentage Used 1%, Critical Warning 0x00 — so the NAND is not degrading; corruption entered in-flight (DRAM/memory-controller/PCIe/write-path). This correlates with the heavy memory-pressure signatures in the same window (kernel __alloc_pages_slowpath, lowmem_reserve, NVKMS GEM alloc failures, OOM) on a consumer no-ECC box. Because the FS is single-device there is no second mirror to repair from — those blocks return EIO on read. If an affected inode belongs to a model/DB/config file, a service will silently break. Recommend (maintenance window, NOT done per read-only mandate): `btrfs scrub` to enumerate/quantify, identify affected paths, and a memtest pass. Not covered by any open task.

*Severity adjusted high→critical during adversarial verification.*

*Verify note:* Fully reproduced and WORSENED on fresh independent probe. Refutation attempts all failed: (1) RTC-skew angle killed — mini and rig clocks are within 1s (both 1787522320 UTC) and rig timedatectl reports "System clock synchronized: yes", RTC in UTC, so the journal EDT timestamps are trustworthy, not skewed/stale. (2) check-bug angle killed — `btrfs device stats /` is the authoritative kernel counter, not a check script. (3) historical/one-off angle killed — the counter went from corruption_errs 3 at audit time to 5 NOW, with two BRAND-NEW csum failures logged AFTER the audit scan: Aug 23 17:30:17 (corrupt 4, root 256 ino 474561) and Aug 23 17:48:22 (corrupt 5, root 256 ino 474924), the last one ~11 min before my probe (current 17:59 EDT). All on subvolid 256 = the root subvol /@, single-device no-mirror = unrecoverable EIO on those blocks (exactly the operator note that these ARE unrecoverable). SMART still clean (Media/Data Integrity Errors 0, Percentage Used 1%) confirming in-flight/memory-path corruption, not NAND wear, on a no-ECC box under ongoing OOM pressure. Corrected mechanism → SEVERITY-UP to critical: the "high" rating rested on a slow 3-files-over-20-days trickle; the live picture is an ACCELERATING failure — 3 corruptions in a single afternoon (corrupt 3→4→5 between 15:49 and 17:48 EDT) — on the root filesystem of a 24/7 host with no redundancy and a persistent root cause, i.e. an active unrecoverable data-integrity failure in progress, not a leading edge. (FS is still mounted rw with no transaction abort / RO remount, so no cascade yet — that keeps it from being an outage, but the acceleration outweighs the pre-cascade state.)

<details><summary>Evidence</summary>

```
ssh rig 'btrfs device stats /'
[/dev/nvme2n1p2].corruption_errs  3
[/dev/nvme2n1p2].write_io_errs 0 / read_io_errs 0 / flush_io_errs 0 / generation_errs 0
---
journalctl -k --since 2026-08-02 | grep -iE btrfs
Aug 20 04:45:46 cachyos kernel: BTRFS warning (device nvme2n1p2): csum failed root 257 ino 85429 off 87150592 csum 0x4201864f expected 0x1bdddcb6 mirror 1
Aug 20 04:45:46 BTRFS error: bdev /dev/nvme2n1p2 errs: ... corrupt 2
Aug 23 15:49:03 cachyos kernel: BTRFS warning (device nvme2n1p2): csum failed root 256 ino 1626645 off 575737856 csum 0x354eb1bb expected 0xfc9cd46d mirror 1
Aug 23 15:49:03 BTRFS error: bdev /dev/nvme2n1p2 errs: ... corrupt 3
---
ssh rig 'smartctl -a /dev/nvme2n1' | grep -iE ...
Model Number: WDS200T3X0C-00SJG0
Critical Warning: 0x00 | Available Spare: 100% | Percentage Used: 1%
Media and Data Integrity Errors: 0 | Error Information Log Entries: 0 | Unsafe Shutdowns: 531 | Power On Hours: 6,722
```

</details>

## HIGH (4)

### UH1. B2 restic bucket not truly immutable (backups run, delete not refused 401) `known-issue`
**Host:** mini · **Component:** host-mini · **Auditor:** svc:host-mini · **Work item:** `fix-82` · *skeptic-confirmed*

Backup leg for the whole mini host: BACKUP_PATHS covers /opt/stacks (21G) + /etc + ~/.ssh/.config/.docker/.bashrc, restic->B2 snapshot is fresh (<26h audit PASS) and the deployment byte-matches roles/backup source (no drift). The gap is defense-in-depth only: the check 'bucket-restic is actually immutable (retention + live delete refused 401)' FAILS — the B2 bucket lock/lifecycle policy does not actually refuse a live delete, so a compromised key could purge backups. Backups themselves ARE flowing. Baseline classifies this CRIT; tracked as fix-22. NOT fixed per read-only mandate.

*Verify note:* Fresh independent probe (mini, 17:59 EDT 2026-08-23, not the 22:23 daily run) reproduces the defect: b2-bucket-guard.py --immutable exits 1, mini/config governance retention retainUntil=2026-08-16 13:40:03 UTC is 7 DAYS EXPIRED -> object-lock immutability is void, a compromised key can purge those versions. Not stale/wrong-vantage/check-bug. The finding's companion claim 'backups ARE flowing' is also confirmed live: restic-backup.service last run exit 0, snapshot b5a18048 saved (20.2 GiB), restic-snapshot-fresh-mini pass age 20h. Mini clock sane (no RTC skew; this is mini not rig). Known_issue duplicate of fix-22 (also filed critical at idx 3 and idx 14 with deeper triage: 1239 expired versions spanning config/keys/data, growing daily). Two caveats, neither refuting: (a) minor imprecision -- the check exits at the retention step BEFORE its live-delete 401 probe, so 'delete not refused 401' is technically unverified, but immutability failure is proven via the expired governance retention; (b) severity: filed 'high' is a defensible current-state read (backups intact & restorable, gap is defense-in-depth), but the check is severity:crit and the baseline/sibling lanes classify it critical -- the finding transparently acknowledges this. Left CONFIRMED at filed severity rather than SEVERITY-UP because the auditor's 'high' is a documented, reasonable operational judgment, not an error.

<details><summary>Evidence</summary>

```
sudo grep '^BACKUP_PATHS' /etc/restic/env -> BACKUP_PATHS="/opt/stacks /etc /home/btabaska/.ssh ..."
results.json: pass 'restic B2 snapshot for mini newer than 26h'; pass 'mini restic deployment byte-matches roles/backup source'; FAIL 'bucket-restic is actually immutable (retention + live delete refused 401)' (crit_failed:2 in summary)
```

</details>

### UH2. Committed audit report leaks a STILL-LIVE playit SECRET_KEY (+ a since-rotated ntfy token) into git
**Host:** mini · **Component:** secrets / repo-committed audit report · **Auditor:** cross:secrets-hygiene · **Work item:** `fix-84` · *skeptic-confirmed*

foss-setup/docs/quality-gate-2026-07-16.json and its .md twin paste real secret VALUES into their evidence/detail fields. Two secrets confirmed via key-name-anchored scan: (1) playit SECRET_KEY (len 64) whose sha256[:16]=8a0b3881c8741b0b EXACTLY MATCHES the current vault playit_gg.secret_key (also 8a0b3881c8741b0b) -> the value is STILL LIVE, never rotated; playit is the public tunnel agent (minecraft/game ports at 69.9.181.17) so this is a real credential in a git-tracked doc and its history. (2) an ntfy token (tk_ prefix, len 32) copied from NAS health.env; its committed sha256[:16]=7097be7ab084d801 DIFFERS from live NAS health.env / vault nas_health_token (both aedd140e2caa03b6) -> that one WAS rotated and is now dead (stale-in-history only). NOT covered by sec-10 (unpackerr) or sec-11 (bookshelf transcript). NOT fixed per read-only mandate: playit key needs rotation + both values scrubbed from the docs and git history.

*Verify note:* Independent probe from the authoritative sources reproduces the defect exactly. Fresh vantage: structural regex extraction of the raw file text (vs the original key-anchored line scan) + direct vault load, hashing only (no value ever printed). Committed playit SECRET_KEY sha256[:16]=8a0b3881c8741b0b (len 64) in BOTH the .json and .md == live vault playit_gg.secret_key sha256[:16]=8a0b3881c8741b0b (len 64) -> STILL LIVE, never rotated. Committed ntfy tk_ token sha256[:16]=7097be7ab084d801 (len 32) DIFFERS from live vault ntfy.nas_health_token aedd140e2caa03b6 -> rotated/dead (secondary claim also holds). Files are git-tracked, not ignored, clean in working tree, and the 64-hex key is present in the committed HEAD blob (count=1) since commit c851fba 2026-07-16, pushed to origin GitHub (btabaska/home-config) + forgejo (home/homelab). No refutation angle applies: not wrong-vantage (repo's own tracked files + vault are authoritative), not stale cache (values hashed fresh), no RTC/GPU/operator-intent/known-normal factor. Not covered by sec-10 (unpackerr) or sec-11 (bookshelf) -> known_issue:false is correct. Severity high is right: real live credential leaked, but scoped to the playit tunnel agent, not fleet-wide, so not critical.

<details><summary>Evidence</summary>

```
# key-anchored scan of tracked files (values redacted at source):
foss-setup/docs/quality-gate-2026-07-16.json
  line 436: key="NTFY_TOKEN" <REDACTED mixed len=32>
  line 692: key="SECRET_KEY" <REDACTED hex len=64>
foss-setup/docs/quality-gate-2026-07-16.md lines 930/937 (NTFY_TOKEN) + 1453 (SECRET_KEY)

# hash comparison (no value echoed):
committed playit SECRET_KEY sha256[:16]: 8a0b3881c8741b0b len 64
vault playit_gg.secret_key   sha256[:16]: 8a0b3881c8741b0b len 64   <-- MATCH = LIVE
committed NTFY_TOKEN sha256[:16]: 7097be7ab084d801 (tk_..., len 32)
vault ntfy.nas_health_token   sha256[:16]: aedd140e2caa03b6
live NAS health.env NTFY_TOKEN sha256[:16]: aedd140e2caa03b6   <-- differs = rotated/dead
```

</details>

### UH3. sec-10 unresolved: 4 arr API keys still committed cleartext in unpackerr.conf `known-issue`
**Host:** nas · **Component:** secrets / repo-committed config · **Auditor:** cross:secrets-hygiene · **Work item:** `sec-10` · *skeptic-confirmed*

foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf carries Sonarr (line 47), Radarr (56), Lidarr (65) and Whisparr (83) API keys as 32-hex cleartext values in api_key= fields, git-tracked. Re-verified still present this evening; matches open task sec-10 ('rotate + externalize to a gitignored env'). NOT fixed per read-only mandate. Broad repo scan found NO other tracked non-example file with a secret-shaped api_key value besides this and the quality-gate report leak.

*Verify note:* Fresh independent probes reproduce and strengthen the defect. (1) git ls-files confirms unpackerr.conf is TRACKED; git check-ignore returns exit 1 = NOT gitignored. (2) The api_key values at lines 47/56/65/83 (Sonarr/Radarr/Lidarr/Whisparr) are real 32-char hex — not placeholders (is_placeholder=False), not env-refs (is_envref=False), not empty (len=32); line 74 is only the bookshelf-externalized comment. (3) sec-10 is a genuine open task in tasks.json ("arr API keys committed in cleartext in the repo (unpackerr.conf) — rotate + externalize to a gitignored env"), absent from progress.done and reopened => known_issue:true is correct. (4) DECISIVE: hash-comparison (sha256[:16], no values echoed) of the committed keys EXACTLY MATCHES the live arr keys pulled from mini /etc/verification/env — Sonarr 3964b4aae9f821c7, Radarr 59f50dce8ebb0423, Lidarr d2b3005bd17920b4, Whisparr 9ca3a21bcd953a4d all identical. The committed keys are LIVE, unrotated credentials, not stale/dead. No wrong-vantage, stale-cache, placeholder, or operator-intent explanation applies. Severity high stands (LAN-scoped arr keys, not inflated to crit).

<details><summary>Evidence</summary>

```
$ grep -nE 'api_key' unpackerr.conf | grep -E '[a-f0-9]{32}' | sed 's/[a-f0-9]\{32\}/<REDACTED-32HEX>/g'
47:  api_key = "<REDACTED-32HEX>"  # Sonarr
56:  api_key = "<REDACTED-32HEX>"  # Radarr
65:  api_key = "<REDACTED-32HEX>"  # Lidarr
83:  api_key = "<REDACTED-32HEX>"  # Whisparr
(repo-wide key-anchored scan of all tracked non-example files: only this + quality-gate-2026-07-16.json hit)
```

</details>

### UH4. STILL-OPEN-VALID: arr API keys still committed in CLEARTEXT in tracked repo file pushed to GitHub+Forgejo `known-issue`
**Host:** nas · **Component:** unpackerr.conf cleartext arr keys (sec-10) · **Auditor:** cross:open-queue-reality · **Work item:** `sec-10` · *skeptic-confirmed*

sec-10 condition persists. foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf is git-TRACKED (not gitignored) and still contains cleartext api_key literals for the *arr apps (4 api_key lines; bookshelf was externalized per line-74 comment, but sonarr/radarr/lidarr/whisparr remain). The repo is pushed to origin GitHub (btabaska/home-config) + forgejo. Keys not moved to a gitignored env, not rotated. (Values NOT printed.) Separately, unpackerr-host-retired FAILS (unit=1 proc=1 pkg=1) — unpackerr is running on mini again (fix-69 residual). NOT fixed per read-only mandate.

*Verify note:* Both claims reproduced from fresh vantage. (1) foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf is git-tracked (ls-files --error-unmatch=TRACKED), NOT gitignored (check-ignore=NOT-IGNORED), and contains 4 exactly-32-hex api_key values at lines 47/56/65/83 (sonarr/radarr/lidarr/whisparr); bookshelf externalized per the line-74 comment. Its last commit daa523c is contained in BOTH origin/main (github.com:btabaska/home-config) and forgejo/main (mini) = pushed to both. LEAKED-SECRET adjudication (no values echoed): committed sha256[:16] == live sha256[:16] from mini /etc/verification/env for ALL FOUR keys (sonarr 3964b4aae9f821c7, radarr 59f50dce8ebb0423, lidarr d2b3005bd17920b4, whisparr 9ca3a21bcd953a4d) -> keys are STILL LIVE / never rotated, so NOT merely stale-in-history. (2) unpackerr running on mini: unit active+running+enabled, proc /usr/bin/unpackerr PID 104964, dpkg unpackerr 0.15.2-960 = unit=1 proc=1 pkg=1. Not a check-bug/stale-cache/RTC/GPU/IO-window artifact; covered by open sec-10 + fix-69 residual. Severity high stands.

<details><summary>Evidence</summary>

```
git ls-files unpackerr.conf -> TRACKED
grep -nE api_key unpackerr.conf -> lines 47,56,65,83 (values redacted)
git check-ignore -> not ignored
unpackerr-host-retired [fail]: 'unit=1 proc=1 pkg=1 UNPACKERR_BACK'
```

</details>

## MEDIUM (121)

### UM1. Liveness-only consumer-check gap confirmed for 4 manifested services — surface exists but only probes liveness, not the consumer end
**Host:** fleet · **Component:** consumer-check coverage (paperless/dockge/flaresolverr/palworld) · **Auditor:** cross:coverage-tripwire · **Work item:** `fix-100`

Cross-referencing the per-service scan lanes: 4 manifest entries have a monitoring surface (Homepage tile + Kuma monitor) but their ONLY dedicated verification check is liveness, violating standing mandate #1 (verify end-to-end, not liveness) and matching taxonomy #2 (green-but-broken liveness masking). paperless: mini-paperless scrapes the /accounts/login/ page title 'Paperless' — proves the web UI renders but NEVER exercises the OCR/ingest pipeline; its 4 sidecars (paperless_tika=OCR, paperless_gotenberg=PDF, redis, db) have zero function-level probe (they share the same single login-scrape check). dockge: mini-dockge is a bare 'curl -o /dev/null -w %{http_code} :5001/' (HTTP 200 only). flaresolverr: nas-flaresolverr hits :8191/health only — the actual Cloudflare-challenge-solve path (its whole purpose, consumed by Prowlarr indexers) is not probed through it. palworld: palworld-rest-liveness curls the admin-auth /v1/api/metrics endpoint but never confirms a player can join (no gamedig/handshake), unlike its sibling game servers terraria (terraria-join-handshake + terraria-world-loaded) and minecraft (game-* handshake). All 4 PASS today on liveness while their consumer end is unverified. NOT fixed per read-only mandate — these are fresh consumer-probe gaps surfaced by this audit, not an existing open task.

<details><summary>Evidence</summary>

```
results.json check cmds:
mini-paperless: curl -sf :8000/accounts/login/ | grep -o 'Paperless'
mini-dockge: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:5001/
nas-flaresolverr: curl -sm 8 http://localhost:8191/health
palworld-rest-liveness: curl -sm 8 -u admin:*** http://cachyos...:8212/v1/api/metrics
CONTRAST (real consumer probes exist for peers): terraria-join-handshake, terraria-world-loaded, game-bedrockconnect-serverlist
```

</details>

### UM2. 3 HA updates left pending >=21 days (fix-36 reopen candidate, re-verified holding) `known-issue`
**Host:** ha · **Component:** ha-core/updates · **Auditor:** svc:ha-core · **Work item:** `fix-104`

ha-updates-pending is failing. Three update.* entities have sat 'on' past the 21-day threshold: Core 2026.7.2->2026.8.3 pending 26 days (since 2026-07-28), HAOS 18.1->18.2 pending 22 days (since 2026-08-01), Matter Server 9.1.0->9.2.0 pending 25 days (since 2026-07-29). (Terminal&SSH 10.3.0->10.4.0 is 4 days, not yet stale.) Same 3-entity set as this morning's 10:29 baseline and the 22:23 audit-safe run — not silently worsened, stable-known. Human action gated to the 4-7AM maintenance window; NOT fixed per read-only mandate. Known open task fix-36.

<details><summary>Evidence</summary>

```
curl -s -H 'Bearer $HA_TOKEN' http://192.168.10.50:8123/api/states | python3 (age of update.* state=='on'):
update.home_assistant_core_update: pending since 2026-07-28T16:54:02Z = 26 days | 2026.7.2 -> 2026.8.3 | STALE(>=21)=True
update.home_assistant_operating_system_update: pending since 2026-08-01T01:45:04Z = 22 days | 18.1 -> 18.2 | STALE=True
update.matter_server_update: pending since 2026-07-29T07:54:02Z = 25 days | 9.1.0 -> 9.2.0 | STALE=True
---
mini /tmp/verify-audit-uc/results.json (2026-08-22T22:23:20-04:00): ha-updates-pending | fail | updates=STALE:update.home_assistant_core_update,update.home_assistant_operating_system_update,update.matter_server_update
```

</details>

### UM3. 3 HA updates pending >=21 days: Core 25d (2026.7.2->2026.8.3), Matter Server 24d (9.1.0->9.2.0), HAOS 22d (18.1->18.2) — grew from 2 to 3 stale entities today `known-issue`
**Host:** ha · **Component:** home-assistant updates (ha-updates-pending / fix-36) · **Auditor:** triage:ha-updates-pending · **Work item:** `fix-104`

Known residual, known fix-36 class (lane-context baseline maps ha-updates-pending -> fix-36). fix-36 was resolved 2026-07-19 by installing Core 2026.7.2 / HAOS 18.1 / Matter 9.1.0; the NEXT update round then sat unapplied, which is precisely the failure class the >=21d guard was added to catch. Timeline: check green through 2026-08-18 (0 mentions in mini triage-2026-08-18.md); first fail 2026-08-19 with 2 entities (core, matter_server); HAOS 18.2 (published 2026-08-01) crossed the 21-day line on 2026-08-22, so tonight's fail lists 3 entities — a same-class widening, not a new failure mode. Current drift is mild compared with the original fix-36 finding (then: HAOS 2 major versions behind, 16.3 vs 18.1; now: one monthly core release train 2026.7->2026.8 with 3 accumulated patches, one OS point release, one matter minor). Supervisor is current (2026.07.5, state off). Remediation = update.install service calls (with pre-update backup, per ha-health.md runbook and the fix-36 done-note precedent) — disruptive, belongs in the 4-7AM EST window; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ TOK=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['hosts']['ha']['api_token'])") && curl -s -m 15 -H "Authorization: Bearer $TOK" http://192.168.10.50:8123/api/states | python3 -c '<filter update.* entities>'
update.home_assistant_core_update                       state=on   installed=2026.7.2     latest=2026.8.3     last_changed=2026-07-28T16:54:02 (25d ago)
update.home_assistant_operating_system_update           state=on   installed=18.1         latest=18.2         last_changed=2026-08-01T01:45:04 (22d ago)
update.matter_server_update                             state=on   installed=9.1.0        latest=9.2.0        last_changed=2026-07-29T07:54:02 (24d ago)

Tonight's runner output (results.json, check ha-updates-pending, status=fail):
updates=STALE:update.home_assistant_core_update,update.home_assistant_operating_system_update,update.matter_server_update

$ ssh mini 'ls /var/lib/verification/triage-2026-08-18.md && grep -c "ha-updates-pending" /var/lib/verification/triage-2026-08-18.md'
/var/lib/verification/triage-2026-08-18.md
0    # green on 08-18; first triage entry is triage-2026-08-19.md (2 entities: core + matter_server)
```

</details>

### UM4. iPhone presence pipeline silently FROZEN 4.2 days — beyond btiphone-stale baseline, and ha-iphone-presence false-greens it `known-issue`
**Host:** ha · **Component:** iPhone companion presence pipeline (device_tracker.brandon_iphone + sensor.btiphone_battery_*) · **Auditor:** flow:home-assistant · **Work item:** `fix-104`

ADJUDICATION of the 'iPhone presence FROZEN ~4 days' item: this IS beyond the accepted baseline. The accepted 'btiphone_* <=11 stale' baseline covers 11 permanently-UNAVAILABLE kiosk/network sensors that froze 26.2d ago at 2026-07-28T16:54:21 (the last HA restart; kiosk features unused) — those are expected. The freeze in question is a DIFFERENT set: the ACTIVE presence entities device_tracker.brandon_iphone (state=home), sensor.btiphone_battery_level (90), sensor.btiphone_battery_state (Not Charging). All THREE hold real values but are frozen at the IDENTICAL second 2026-08-19T17:26:22 (4.2d ago) — i.e. they were reporting live AFTER the 07-28 restart, then the companion app stopped pushing 4.2d ago. Battery pinned at exactly 90 for 4.2d while reporting 'home'/'Not Charging' is physically implausible for an in-use phone = classic taxonomy #13 (silently-frozen poller, green-but-frozen). This is worsening (was ~3.2d at the 08-22 22:23 baseline run). The ha-iphone-presence check PASSES falsely because it only asserts the state is a real non-null value, never freshness — recommend adding a last_updated>24-48h assertion on device_tracker/battery. Consumer impact: any away/home presence automation is stuck on 'home' and will not fire away-mode logic. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -s -H 'Authorization: Bearer $HA_TOKEN' http://192.168.10.50:8123/api/states | python3 (age vs now_utc=2026-08-23T21:10:14Z):
device_tracker.brandon_iphone   state=home         last_updated=2026-08-19T17:26:22 (4.2d)
sensor.btiphone_battery_level   state=90           last_updated=2026-08-19T17:26:22 (4.2d)
sensor.btiphone_battery_state   state=Not Charging last_updated=2026-08-19T17:26:22 (4.2d)
-- baseline btiphone kiosk sensors (accepted, separate): 11 unavailable, all last_updated=2026-07-28T16:54:21 (26.2d)
-- ha-iphone-presence check output (results.json): 'presence=ok' (value-only, no freshness) — FALSE GREEN
```

</details>

### UM5. iPhone companion presence pipeline FROZEN ~4 days — all btiphone active sensors stuck at last_updated 2026-08-19T17:26:22Z (taxonomy 13, green-but-broken)
**Host:** ha · **Component:** mobile_app-presence · **Auditor:** svc:ha-integrations · **Work item:** `fix-104`

Zero-throughput finding. The mobile_app (Btiphone) config_entry is 'loaded', but NO data has flowed for 98.5h. device_tracker.brandon_iphone, sensor.btiphone_battery_level (stuck 90%), and sensor.btiphone_battery_state (Not Charging) all have last_updated (not merely last_changed) frozen at 2026-08-19T17:26:22Z — an in-use phone's battery/location would push far more often, and all active sensors froze at the same instant, indicating the companion app stopped reporting on 2026-08-19. This degrades any presence/arrival automations to stale last-known-good. The fix-36 'iPhone companion presence pipeline alive' check is GREEN-BUT-BROKEN: it only asserts battery is a digit and device_tracker != unavailable, so a frozen last-known-good value passes (mandate 1: verify throughput, not liveness). This is beyond the accepted baseline (baseline accepts 11 stale/unavailable btiphone_* sensors — exactly 11 seen — but presumes the ACTIVE sensors carry recent values; they do not). NOT covered by an open task (fix-36 tracks updates-pending, not presence freshness). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl .../api/states (2026-08-23T19:57:58Z):
device_tracker.brandon_iphone state=home last_updated=2026-08-19T17:26:22.072390+00 (98.5h)
sensor.btiphone_battery_level state=90 last_updated=2026-08-19T17:26:22.171477+00 (98.5h)
sensor.btiphone_battery_state state=Not Charging last_updated=2026-08-19T17:26:22.172111+00 (98.5h)
results.json fix-36 'iPhone companion presence pipeline alive' pass presence=ok (check asserts only isdigit(battery) + dt!=unavailable)
config_entries: 'mobile_app | Btiphone | state= loaded'
```

</details>

### UM6. STILL-OPEN-VALID (partial): 3 regenerated manifests uncommitted + /opt/foss-setup clone 23 days behind main `known-issue`
**Host:** mini · **Component:** /opt/foss-setup manifests + clone drift (fix-80) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-80`

3 of the 4 fix-80-driven checks self-healed (stack-mirror-drift, ansible-site-converged-mini, unit-file-drift all pass). git-foss-setup-clean STILL FAILS: /opt/foss-setup carries 3 uncommitted regenerated files (inventory.md, macmini/compose-images.txt, macmini/systemd-timers.txt). Additionally the clone HEAD is f683cfd (2026-07-28) while repo main is ab54803 (2026-08-20) — ~23 days / many commits behind, confirming the 'lag main' condition (not asserting ansible-pull broken; ansible-site-converged is green). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'sudo git -C /opt/foss-setup status --porcelain' ->
 M foss-setup/configs/inventory/inventory.md
 M foss-setup/hosts/macmini/compose-images.txt
 M foss-setup/hosts/macmini/systemd-timers.txt
opt-foss-setup HEAD=f683cfd 2026-07-28; repo main=ab54803 2026-08-20
git-foss-setup-clean [fail]: out='3'
```

</details>

### UM7. lai-28 residual: rig.containers manifest updated in repo but NOT deployed to mini — unsloth-studio missing from live manifest `known-issue`
**Host:** mini · **Component:** /opt/verification/coverage/rig.containers / containers-manifest-rig (verify-06) · **Auditor:** cross:docs-tracker-truth · **Work item:** `fix-97`

97a672e (lai-28) added unsloth-studio to the REPO manifest foss-setup/verification/coverage/rig.containers (line 21), but the DEPLOYED copy on mini /opt/verification/coverage/rig.containers still ends at suwayomi (20 lines, no unsloth-studio). This is the classic 'scp to /opt/verification fails silently' deploy quirk — repo side fixed, live side not pushed. Consequence: containers-manifest-rig diffs live rig (has unsloth-studio, verified Up 5 days) vs the stale deployed manifest and FAILs (20a21 > unsloth-studio). bioclip-api (lai-22) IS present in the deployed manifest, so lai-22's coverage leg was deployed correctly — only lai-28's was missed. NOT fixed per read-only mandate. known_issue: verify-06 in baseline.

<details><summary>Evidence</summary>

```
$ ssh mini 'grep -c unsloth /opt/verification/coverage/rig.containers' -> 0  (bioclip -> 1)
$ diff <(git show HEAD:foss-setup/verification/coverage/rig.containers) <deployed> -> 21d20 < unsloth-studio  (REPO!=DEPLOYED)
$ ssh rig docker ps | grep unsloth -> unsloth-studio unsloth/unsloth:latest Up 5 days
results.json containers-manifest-rig: FAIL task=verify-06 :: 20a21 > unsloth-studio
$ git log -S unsloth-studio -- foss-setup/verification/coverage/rig.containers -> 97a672e lai-28
```

</details>

### UM8. STILL-OPEN-VALID: verification runner env still holds the WRITE-capable Cloudflare token; no read-only DNS token minted `known-issue`
**Host:** mini · **Component:** Cloudflare token least-privilege (sec-09) · **Auditor:** cross:open-queue-reality · **Work item:** `sec-09`

sec-09 condition unchanged. /etc/verification/env still references CLOUDFLARE_API_TOKEN (the edit/delete-capable token); no DNS_READ-scoped var exists. Vault cloudflare section holds only 'api_token' — no 'dns_read_token' key was ever created. A leak from the runner env would still allow public-DNS tampering incl. Proton MX. The consumer check edge-public-dns-no-rfc1918 passes (ZONE_CLEAN) but that only proves the token works, not that it's least-privilege. (Probed by var/key NAME only — no secret values read.) NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'sudo grep -oE ^[A-Z_]*CLOUDFLARE[A-Z_]*= /etc/verification/env' -> CLOUDFLARE_API_TOKEN=
grep DNS_READ -> (none)
vault cloudflare keys present: ['api_token'] (no dns_read_token)
```

</details>

### UM9. Immich DB dumps are fresh, but the library they protect has received 0 new assets in 7 days `known-issue`
**Host:** mini · **Component:** Immich phone-photo ingestion (fix-35) · **Auditor:** flow:backups-restore-drill · **Work item:** `fix-86`

Adjacent to this chain: the Immich pg_dump leg is healthy (see green above), but the thing being backed up is not receiving new photos. nas-immich-backup-freshness (task fix-35) reports 36,208 total assets and 0 assets createdAfter now-7d — phone backup into Immich has stalled, so the fresh nightly dumps are snapshotting a library that stopped growing a week ago. This is a consumer-end freshness gap for 'my photos are being protected' even though the backup mechanics work. Known/open (fix-35; related fix-60 immich-user-zero-assets, fix-71 Kaelyn Immich also failing in baseline). NOT fixed — read-only.

<details><summary>Evidence</summary>

```
results.json (2026-08-22T22:23): id=nas-immich-backup-freshness status=fail task=fix-35
out: 'backup=STALE assets=36208 fresh_7d=0'  (also immich-user-zero-assets=fail fix-60, nas-immich-ffmpeg-nocrash=fail fix-60)
```

</details>

### UM10. IPTorrents junk-grab storm worsening: 71% of grabs (fix-50) `known-issue`
**Host:** mini · **Component:** Prowlarr / IPTorrents indexer · **Auditor:** flow:movies-tv · **Work item:** `fix-94`

Known fix-50 grab storm, re-verified live and WORSENED: IPTorrents (via Prowlarr) now accounts for 71% of the last 80 automatic grabs (was 69% at 22:23 tonight; fix-50 baseline was 'worsened 70%'), auto_enabled=YES. A single live indexer dominating auto-grabs is the classic junk-grab pattern. Consumer impact is currently masked — media-arr-file-quality passed and files land in Plex correctly — so this is an efficiency/junk-torrent risk (bandwidth, ratio, wrong-release grabs) rather than a hard consumer break today. Bitmagnet was correctly demoted to interactive-only (bitmagnet-demoted-interactive-only PASS; bitmagnet-torznab-via-prowlarr = manual-only fallback, expected). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
[live 16:48 EDT, keys exported] python3 /opt/verification/bin/arr-grab-indexer-share.py share -> SHARE_STORM top='IPTorrents (Prowlarr)' share=71% n=80 auto_enabled=YES
[22:23 run] same probe: share=69% n=80 auto_enabled=YES
```

</details>

### UM11. Public registration still OPEN on booklogr-api — lock precondition (an account exists) now met; deliberate-but-stale per fix-51/SM24 `known-issue`
**Host:** mini · **Component:** booklogr-api (AUTH_ALLOW_REGISTRATION) · **Auditor:** svc:booklogr · **Work item:** `fix-85`

AUTH_ALLOW_REGISTRATION=True on booklogr-api: the audit posture check reports BOOKLOGR_REG=True envfile=True match=yes, and I independently confirmed the route is live via a non-mutating GET /v1/register -> 405 Method Not Allowed (route exists+enabled; a @disable_route-disabled route returns 404, and my bogus-route control DID return 404). This is a KNOWN, deliberate operator posture: fix-51 finding SM24 (progress.json, 2026-08-02) states 'BookLogr registration deliberately LEFT OPEN per operator — only DOCUMENTED the posture, no flip', and the booklogr-registration-posture check is by design 'passes on True OR False, fails only on drift — does not assert False' (so monitoring will never alert on this staying open). RE-VERIFIED it still holds today and note the trigger condition is now satisfied: the read-26 deploy note and booklogr-quirks memory (2026-07-28) both say 'flip AUTH_ALLOW_REGISTRATION=False once accounts exist' — the DB now holds exactly 1 user account (see throughput finding), so the household-signup rationale for leaving it open has been served. Risk is bounded by edge exposure (fix-51 treats the flat LAN as trusted with Caddy as the auth edge; whether booklogr(-api).tabaska.us has any WAN ingress is out of this lane's scope and should be confirmed by the caddy/network lane). NOT fixed per read-only mandate — reported for operator flip + redeploy.

<details><summary>Evidence</summary>

```
audit results.json: booklogr-registration-posture status=pass output='BOOKLOGR_REG=True envfile=True match=yes' (task_id fix-51)
$ curl -sk --resolve booklogr-api.tabaska.us:443:192.168.10.2 -H 'Origin: https://booklogr.tabaska.us' https://booklogr-api.tabaska.us/v1/register -> HTTP=405 (Method Not Allowed = route enabled) ; /v1/login -> 405 ; /v1/definitely-not-a-route -> 404 (control)
progress.json fix-51: 'SM24: BookLogr registration deliberately LEFT OPEN (AUTH_ALLOW_REGISTRATION=True) per operator ... booklogr-registration-posture RECORDS the reg value ... passes on True OR False, fails only on drift — does not assert False'
docker exec booklogr-api sqlite3(ro) SELECT count(*) FROM users -> 1
```

</details>

### UM12. caddy_data cert volume (76 LE certs) excluded from restic backup set despite compose marking it non-ephemeral
**Host:** mini · **Component:** caddy · **Auditor:** svc:caddy · **Work item:** `fix-93`

The live restic env overrides BACKUP_PATHS to '/opt/stacks /etc /home/btabaska/...' — the script default that covered /var/lib/docker/volumes is NOT in effect, so the caddy_data named volume is unprotected. compose.yaml itself says 'caddy_data:/data # certs & keys — treat as non-ephemeral (avoids LE rate limits)'. The volume holds 76 issued certificates; Let's Encrypt caps ~50 new certs per registered domain per week, so a mini rebuild/volume loss would leave ~26+ *.tabaska.us vhosts unable to re-issue TLS for up to a week. /opt/stacks/caddy (Caddyfile + static sites, 4.5M) IS backed up and the restic run 20h ago was clean. NOT fixed per read-only mandate. Not covered by any open task (fix-22 is B2 immutability, unrelated).

<details><summary>Evidence</summary>

```
$ ssh mini 'sudo grep "^BACKUP_PATHS" /etc/restic/env'
BACKUP_PATHS="/opt/stacks /etc /home/btabaska/.ssh /home/btabaska/.config /home/btabaska/.docker /home/btabaska/.bashrc"
$ ssh mini 'docker exec caddy sh -c "find /data/caddy/certificates -name \"*.crt\" | wc -l; du -sh /data"'
76
1.6M	/data
$ grep -A2 caddy_data foss-setup/configs/docker-stack/stacks/caddy/compose.yaml
- caddy_data:/data # certs & keys — treat as non-ephemeral (avoids LE rate limits)
$ ssh mini 'journalctl -u restic-backup.service --since "3 days ago" ... | tail -3'
Aug 22 01:34:44 macmini restic-backup.sh[2079359]: no errors were found
```

</details>

### UM13. KNOWN/re-verified: crit immutability guard still failing — newest mini/config pack's governance retention expired ~2026-08-16, ransomware-immutability window lapsed `known-issue`
**Host:** mini · **Component:** checks.d/backups.yaml: b2-restic-immutable · **Auditor:** meta:backups · **Work item:** `fix-82`

Baseline-listed fix-22 residual, RE-VERIFIED still failing in today's 10:29 daily run: b2-bucket-guard.py --immutable reports the newest mini/config pack file has mode=governance but retainUntilTimestamp=1786887603882 (= ~2026-08-16 13:40 UTC, ~6 days in the past), i.e. no longer retention-locked — new packs are not receiving a rolling retention window. The CHECK itself is the gold-standard consumer probe of this file (live b2_delete_file_version attempt expecting 401) and is doing its job; this is the underlying condition. Note a tracker wrinkle: fix-22 shows done in progress.json and is absent from the reopened-ledger keys (fix-28/23/24/25/27/35/37-40/42/43/45/ai-03/glue-03/nas-01/net-05/sec-03/seed-12/wiki-05) even though the audit baseline maps this fail to fix-22 — worth confirming the reopen bridge actually carries it. NOT fixed per read-only mandate (deliberately did NOT re-run the guard: if immutability is broken, its delete-attempt probe could succeed and mutate the bucket).

<details><summary>Evidence</summary>

```
/var/lib/verification/results.json (timestamp 2026-08-22T10:29:50-04:00):
b2-restic-immutable | fail | BAD file mini/config not retention-locked: {"mode": "governance", "retainUntilTimestamp": 1786887603882}
progress.json: fix-22 -> done entry: True, not in reopened ledger keys
```

</details>

### UM14. Rig coverage manifest fixed in repo but never deployed — check fails every hourly quick run `known-issue`
**Host:** mini · **Component:** containers-manifest-rig · **Auditor:** meta:docker-fleet · **Work item:** `fix-97`

The known verify-06 baseline failure (unsloth-studio missing from rig manifest), re-verified and SHARPENED: repo commit 97a672e (lai-28) already added unsloth-studio to foss-setup/verification/coverage/rig.containers (21 lines, md5 91f84f43...), and that repo manifest matches live rig containers exactly (diff exit 0). But the deployed copy at mini:/opt/verification/coverage/rig.containers is the stale 20-line pre-lai-28 version (md5 b4e80f10...), so the check fails on every hourly quick run (last: 2026-08-22T21:40:25-04:00, status fail). This is the verification-deploy-quirk class (scp to root-owned /opt/verification fails silently; deploy = ssh sudo tee). Remediation is a one-file deploy of the already-committed manifest. NOT fixed per read-only mandate. known_issue: verify-06 reopen (in today's 10:29 baseline).

<details><summary>Evidence</summary>

```
$ ssh mini 'md5sum /opt/verification/coverage/rig.containers' -> b4e80f103eea94f3d485f3707da78617
$ md5 -r foss-setup/verification/coverage/rig.containers -> 91f84f438faa50cb11f5827062cdbe8c
$ ssh mini 'cat /opt/verification/coverage/rig.containers' | diff - foss-setup/verification/coverage/rig.containers
20a21
> unsloth-studio
$ ssh rig "docker ps --format '{{.Names}}'" | grep -vE -- '(-run-|^immich_machine_learning$)' | LC_ALL=C sort | diff foss-setup/verification/coverage/rig.containers - ; echo diff_exit=$?
diff_exit=0
$ git log --oneline -1 -- foss-setup/verification/coverage/rig.containers -> 97a672e lai-28: Unsloth Studio on the rig
$ mini results-docker-fleet.json (2026-08-22T21:40:25-04:00): containers-manifest-rig fail 0.41 ; output: '20a21 > unsloth-studio'
```

</details>

### UM15. rig deployed coverage manifest lags repo by one line — unsloth-studio missing → containers-manifest-rig FAIL `known-issue`
**Host:** mini · **Component:** coverage/rig.containers (deployed) · **Auditor:** cross:coverage-tripwire · **Work item:** `fix-97`

The repo manifest foss-setup/verification/coverage/rig.containers was updated to include unsloth-studio (lai-28, mtime 2026-08-17), and unsloth-studio is live on rig, but the DEPLOYED copy at mini:/opt/verification/coverage/rig.containers (mtime 2026-08-16 19:19) still has only 20 lines and omits it. So the tripwire diffs live(21) against manifest(20) and flags unsloth-studio as an 'extra' container every run. This is a repo→deployed drift: the fix already exists in the repo and just needs scp'ing to /opt/verification/coverage/rig.containers on mini (the verification-deploy quirk: scp fails silently root-owned → ssh sudo tee). NOT fixed per read-only mandate. Covered by verify-06 (containers-manifest-rig) in today's baseline.

<details><summary>Evidence</summary>

```
$ diff foss-setup/verification/coverage/rig.containers <(ssh mini 'cat /opt/verification/coverage/rig.containers')
21d20
< unsloth-studio
$ ssh rig "docker ps --format '{{.Names}}'" | grep -c '^unsloth-studio$' → 1 (live)
$ stat deployed rig.containers → mtime 2026-08-16 19:19; repo mtime 2026-08-17
results.json containers-manifest-rig: status=fail exit=1 output="20a21\n> unsloth-studio"
```

</details>

### UM16. Dockge covered by bare HTTP-200 liveness only — no consumer probe
**Host:** mini · **Component:** dockge · **Auditor:** meta:coverage-diff · **Work item:** `fix-100`

The only dockge check is `mini-dockge` (mini-services.yaml): curl -o /dev/null -w '%{http_code}' http://localhost:5001/ — a bare status-code check with no app-level assertion. This is exactly the 'container up / HTTP 200 is not the feature works' anti-pattern from standing mandate 1. Dockge is the stack-management UI; a consumer probe would assert it can enumerate the /opt/stacks stacks or return an authenticated API payload. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
mini-dockge cmd: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:5001/  (asserts http_code only)
```

</details>

### UM17. /opt/foss-setup checkout is 99 commits / 26 days stale with uncommitted regenerated manifests — export leg never propagates to origin `known-issue`
**Host:** mini · **Component:** git-control-plane / /opt/foss-setup manifest-export checkout (glue-08 + fix-80) · **Auditor:** flow:git-control-plane · **Work item:** `fix-80`

git-foss-setup-clean (glue-08) FAIL is NOT the in-flight WIP — it is 3 auto-regenerated export manifests left uncommitted: foss-setup/configs/inventory/inventory.md, hosts/macmini/compose-images.txt, hosts/macmini/systemd-timers.txt. Deeper probe: the /opt/foss-setup checkout HEAD is f683cfd (glue-15, dated 2026-07-28), 99 commits behind origin main ab548032 (dated 2026-08-20) and doesn't even have that commit locally (cat-file -t = unknown) — it hasn't fetched in ~26 days. export-manifests regenerates host manifests from live docker/systemd state into this abandoned checkout, and they are never committed/pushed. This is the ROOT of the manifest-purity failure below: origin's committed compose-images.txt keeps its stale content because the clean regeneration never lands upstream. Not fixed (read-only). known_issue: glue-08 baseline + fix-80 open task. Flagging the DEPTH (26 days / 99 commits stale) as a worsened residual worth an operator's eye, not a transient dirty-file.

<details><summary>Evidence</summary>

```
mini$ sudo git -C /opt/foss-setup status --porcelain:
 M foss-setup/configs/inventory/inventory.md
 M foss-setup/hosts/macmini/compose-images.txt
 M foss-setup/hosts/macmini/systemd-timers.txt
mini$ sudo git -C /opt/foss-setup log -1 --format='%h %ci' -> f683cfd 2026-07-28 13:12:49 -0400 (glue-15)
mini$ sudo git -C /opt/foss-setup cat-file -t ab5480325670... -> commit-unknown-locally
mac$ git rev-list --count f683cfd..ab548032 -> 99 ; origin ab548032 dated 2026-08-20
```

</details>

### UM18. STILL-OPEN-VALID + AGING: mini kernel reboot still pending, uptime 44d — 1 day from tripping STALE (45d) `known-issue`
**Host:** mini · **Component:** kernel reboot / mini-reboot-not-stale (fix-74) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-74`

Reboot is still pending (/var/run/reboot-required present). Check passes only because uptime (44d) is <=45d threshold; it will flip to REBOOT_STALE at 45d, i.e. imminently. A mini reboot is a fleet-wide outage (Caddy TLS, DNS, ntfy/Healthchecks/Kuma, verification, Forgejo deploy) requiring a 4-7AM drain window — human-gated. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
mini-reboot-not-stale [pass]: out='reboot_pending=yes uptime_days=44\nREBOOT_OK' (threshold <=45)
```

</details>

### UM19. mini-scratch-hygiene red re-verified and WORSENED: 103 aged scratch items in /tmp vs threshold 10 (original finding cited 53+) `known-issue`
**Host:** mini · **Component:** mini-scratch-hygiene · **Auditor:** meta:host-hygiene · **Work item:** `fix-96`

Known baseline failure (fix-69). Re-verified live: scratch7d=103 files/dirs older than 7 days in mini /tmp — nearly double the 53+ that motivated the original SL40/SL41 finding, so the accumulation is actively growing, not static residual. The critical sub-signal is clean: secrets=0 (no cookies/pem/id_* auth material in /tmp). The check design is sound (thresholds 10 scratch / 0 secrets / 14d results-staleness are reasonable and not drifted); the red is a genuine unremediated condition, not check rot. NOT fixed per read-only mandate — remediation is the fix-69 residual cleanup plus whatever agent-session discipline stops the pile from regrowing.

<details><summary>Evidence</summary>

```
ssh mini find-based check logic → secrets=0 scratch7d=103 (threshold: scratch -le 10)
```

</details>

### UM20. ListenBrainz popularity API auth rot: 401 storm + circuit-breaker open twice daily since at least 2026-08-02 (taxonomy 11)
**Host:** mini · **Component:** musicseerr · **Auditor:** svc:musicseerr · **Work item:** `fix-89`

musicseerr's twice-daily discovery/refresh job (~04:27 and ~16:28 EDT, drifting later each day) calls api.listenbrainz.org /1/popularity/top-release-groups-for-artist without an auth token. ListenBrainz now rejects unauthenticated calls: '{"code":401,"error":"Due to bad actors and AI scrapers... you need to provide an Auth token for this endpoint."}'. Every run retries 3x per artist, fails ~10+ times, then 'Circuit breaker listenbrainz opening after 10 failures'. Present on every run 2026-08-02 through today 2026-08-22 16:28 EDT (~50-150 log lines per burst). Popularity enrichment on the discover surface silently degrades while the app stays green — core request->Lidarr->import flow is unaffected. Fix path = configure a ListenBrainz token in musicseerr (or disable the popularity fetch). No matching open task found in tasks.json (grep 'listenbrainz' returned nothing). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker logs -t musicseerr --since 2026-08-22T16:27:00 --until 2026-08-22T16:31:00 2>&1 | grep -vE "GET /health" | head'
2026-08-22T20:28:03.233Z ... httpx - INFO - HTTP Request: GET https://api.listenbrainz.org/1/popularity/top-release-groups-for-artist/7746d775-... "HTTP/1.1 401 UNAUTHORIZED"
2026-08-22T20:28:03.233Z ... infrastructure.resilience.retry - ERROR - _request failed after 3 attempts: ListenBrainz GET failed (401): {"code":401,"error":"Due to bad actors and AI scrapers causing undue traffic on our sites, you need to provide an Auth token for this endpoint. Sorry for this mess."}
2026-08-22T20:28:13.053Z ... ERROR - Circuit breaker 'listenbrainz' opening after 10 failures
(timestamp histogram: bursts every day ~08:27 UTC and ~20:28 UTC, 2026-08-02..2026-08-22)
```

</details>

### UM21. Paperless document/OCR pipeline has NO consumer probe — whole 5-container stack rests on one login-page render
**Host:** mini · **Component:** paperless-ngx stack (paperless, paperless_gotenberg, paperless_tika, paperless_db, paperless_redis) · **Auditor:** meta:coverage-diff · **Work item:** `fix-100`

The only check touching the entire paperless stack is `mini-paperless` (mini-services.yaml), which curls http://localhost:8000/accounts/login/ and greps for the literal 'Paperless' string — i.e. it confirms the login page renders. That is liveness-plus, not a consumer probe: it never verifies documents ingest, that OCR completes, or that the consume folder is draining. gotenberg (PDF conversion) and tika (text extraction) — two functional pipeline components — have ZERO functional coverage; a silent break in either (mandate-1 green-but-broken: consume dir stuck, OCR queue frozen, tika/gotenberg unreachable from paperless) would go undetected. Per standing mandate 1, a consumer probe should assert document count > 0 and/or ingestion freshness and/or OCR-not-stuck. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
mini-paperless cmd: curl -sf -m 8 http://localhost:8000/accounts/login/ | grep -o 'Paperless' | head -1
(token search across all 41 checks.d yaml for paperless/gotenberg/tika returns ONLY mini-paperless; no ingestion/OCR/gotenberg/tika functional check exists)
```

</details>

### UM22. RomM database (romm_romm_db_data, 222M) is in no backup set — not in restic paths and not dumped by the pre-backup hook
**Host:** mini · **Component:** romm-db / restic backup · **Auditor:** svc:romm · **Work item:** `fix-93`

The romm-db MariaDB data lives in named volume romm_romm_db_data at /var/lib/docker/volumes/romm_romm_db_data/_data (222M, outside /opt/stacks). mini's restic env overrides BACKUP_PATHS to '/opt/stacks /etc /home/btabaska/.ssh /home/btabaska/.config /home/btabaska/.docker /home/btabaska/.bashrc' — it does NOT include /var/lib/docker/volumes (the script's DEFAULT_BACKUP_PATHS does, but the env override wins). The PRE_BACKUP_SCRIPT /opt/scripts/pre-backup-db-dumps.sh dumps only paperless/wallabag/miniflux/healthchecks/forgejo/mealie — romm is absent, and the dump dir /opt/stacks/backups/db/ contains no romm*.sql.gz. Net effect: the RomM DB (37 platforms, 8364-rom metadata, user accounts, RetroAchievements sync progress, collections, play stats, manual IGDB edits) has zero backup coverage. Mitigation: ROM files themselves are on the NAS games share (backed up separately + re-scannable), and user saves/states bind-mount /opt/stacks/romm/assets IS covered by restic — but assets is currently empty (4.0K). This is the ONLY stateful DB on mini not dumped while all 6 others are; a clear deviation from the established backup pattern. NOT fixed per read-only mandate. Not covered by any open task (tasks.json romm entries are deployment-only). Fix path: add a dump_mariadb romm-db line to pre-backup-db-dumps.sh (writes into backed-up /opt/stacks/backups/db/).

<details><summary>Evidence</summary>

```
$ docker inspect -f '{{range .Mounts}}{{.Type}} {{.Name}} -> {{.Source}}{{end}}' romm-db
volume romm_romm_db_data -> /var/lib/docker/volumes/romm_romm_db_data/_data
$ sudo du -sh /var/lib/docker/volumes/romm_romm_db_data/_data
222M	/var/lib/docker/volumes/romm_romm_db_data/_data
$ sudo grep -E '^BACKUP_PATHS=' /etc/restic/env
BACKUP_PATHS="/opt/stacks /etc /home/btabaska/.ssh /home/btabaska/.config /home/btabaska/.docker /home/btabaska/.bashrc"
$ sudo grep -iE 'romm' /opt/scripts/pre-backup-db-dumps.sh   # (no output)
$ sudo ls /opt/stacks/backups/db/
forgejo.sql.gz healthchecks.sql.gz mealie.sqlite.sql.gz miniflux.sql.gz paperless.sql.gz vaultwarden.sqlite.sql.gz wallabag.sql.gz   # no romm
```

</details>

### UM23. Documented repair tool cannot re-lock the expired files: --backfill skips any version that already has a retention mode
**Host:** mini · **Component:** scripts/backup/b2-apply-bucket-policy.py --backfill · **Auditor:** triage:b2-restic-immutable · **Work item:** `fix-82`

The runbook (wiki/docs/runbooks/backup-restore.md) names scripts/backup/b2-apply-bucket-policy.py as 'the repair tool' for this check's failures. But its --backfill loop at line 94 does `if f["action"] != "upload" or ret.get("mode"): continue` — it only stamps versions with NO retention mode. All 1239 expired versions still carry mode 'governance' with a past retainUntilTimestamp (live listing shows status_counts EXPIRED:1239, NONE:0), so running the documented repair with the offline master key would update 0 files and the check would keep failing. The fix-22 reopen must extend the tool to compare retainUntilTimestamp against now (b2_update_file_retention with governance mode allows EXTENDING retention without bypassGovernance). Flagging now so the operator doesn't burn a master-key-retrieval session on a no-op. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/scripts/backup/b2-apply-bucket-policy.py lines 92-95:
 for f in page['files']:
     ret = (f.get('fileRetention') or {}).get('value') or {}
     if f['action'] != 'upload' or ret.get('mode'):
         continue
Live bucket state: status_counts={'EXPIRED': 1239, 'LOCKED': 4434} — zero versions have mode unset, so the backfill filter matches nothing.
```

</details>

### UM24. .handoff-secrets.yaml.example covers only 20 of 61 live vault sections (template drift)
**Host:** mini · **Component:** secrets / DR handoff template parity · **Auditor:** cross:secrets-hygiene · **Work item:** `fix-93`

The DR/handoff template declared in CLAUDE.md is a strict subset of the real vault: 20 top-level sections vs 61 live. 41 credential groups have NO template scaffold, incl. immich, jellyfin, stash, syncthing, litellm, playit_gg, komga, lidarr, navidrome, paperless, romm, vaultwarden, wallabag, audiobookshelf, cwa, cubecoders_amp, open_webui, mealie, miniflux, etc. A fresh provision from the template would silently omit these. vault-lint.py checks only empty keys in the REAL vault, not example parity, so this drift is unmonitored. New finding; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ python3 -c 'import yaml; r=yaml.safe_load(open(...real)); e=yaml.safe_load(open(...example)); print(len(r),len(e))'
61 20
# sections in real vault absent from .example (40):
['adguard_nas','alerting','apollo','audiobookshelf','beszel','bitmagnet','books','calibre-web','civitai','comicvine','cubecoders_amp','cwa','discord','emporia','homepage_widgets','immich','jellyfin','komga','libreseerr','lidarr','litellm','mdblist','mealie','miniflux','mylar3','navidrome','open_terminal','open_webui','palworld','paperless','playit_gg','roborock','romm','stash','syncthing','tmdb','uptime_kuma','vaultwarden','vesync','wallabag','withings']
# sections only in .example: NONE
```

</details>

### UM25. Download Tracker retry storm: 1766 'Unable to get queue from NAS Sonarr/Radarr' errors since 2026-08-16, worsening daily and still firing now
**Host:** mini · **Component:** seerr · **Auditor:** svc:seerr · **Work item:** `fix-91`

seerr's minute-interval Download Tracker intermittently fails to fetch the queue from NAS Sonarr (192.168.10.4:8989) and Radarr (:7878). 1766 identical error lines in the last 20000 log lines (window starts 2026-08-16T03:10Z), trending UP: 83 on 08-16 -> 247 on 08-21 -> 295 on 08-22, and firing at probe time (2026-08-23T02:20:10Z). Root cause points at NAS IO load, not seerr config: both arrs return HTTP 200 from mini, but Sonarr /ping took 3.46s (Radarr 0.80s) — the tracker's timeout loses the race intermittently (~10% of polls). Impact: download-progress display in seerr is intermittently blind; availability updates still land via Plex scans (18 AVAILABLE proves the pipeline). Correlates with the known NAS-IO-load baseline (fix-23 timeout correlation noted in today's context) but no open task covers this seerr-side storm specifically; taxonomy 7 (>1000 identical lines). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker logs seerr --tail 20000 2>&1 | grep -c "Unable to get queue"' -> 1766
per-day (UTC): 83 2026-08-16 / 221 08-17 / 175 08-18 / 260 08-19 / 272 08-20 / 247 08-21 / 295 08-22 / 213 08-23
last lines: 2026-08-23T02:20:10.008Z [error][Download Tracker]: Unable to get queue from Sonarr server: NAS Sonarr
reachability from mini: curl -m 10 http://192.168.10.4:8989/ping -> host-to-sonarr:200 time:3.455601 ; :7878/ping -> host-to-radarr:200 time:0.803000
seerr settings: sonarr 'NAS Sonarr' 192.168.10.4:8989, radarr 'NAS Radarr' 192.168.10.4:7878 (correct targets)
```

</details>

### UM26. seerr-request-rot re-verified: SEERR_ROT 3 — 2 dangling requests (Sonarr series deleted) + 1 never-grabbed movie, all stuck PROCESSING 12 days (fix-26 reopen confirmed) `known-issue`
**Host:** mini · **Component:** seerr · **Auditor:** svc:seerr · **Work item:** `fix-90`

Known fix-26 reopen candidate from this morning's baseline — re-verified live and quantified. 7 of 33 requests are APPROVED + media-status PROCESSING for 12 days (all created 2026-08-10); the deployed consumer audit classifies 3 of them as genuine rot: tv tmdb#220150 (mapped Sonarr series id 271 no longer exists in Sonarr), tv tmdb#31654 (Sonarr id 269 gone), movie tmdb#20455 (12d old, zero Radarr history — never grabbed). The other 4 PROCESSING requests have live arr history and are tolerated by the check. Users see these 3 as perpetually 'Processing' with nothing ever arriving (taxonomy 5, request-layer phantom). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'S=$(sudo grep -m1 "^SONARR_API_KEY=" /etc/verification/env | cut -d= -f2-); R=$(sudo grep -m1 "^RADARR_API_KEY=" /etc/verification/env | cut -d= -f2-); SONARR_API_KEY="$S" RADARR_API_KEY="$R" python3 /opt/verification/bin/request-layer-audit.py seerr'
-> SEERR_ROT 3: dangling:tv#220150(sonarr 271 gone); never-grabbed:movie#20455(12d, 0 history); dangling:tv#31654(sonarr 269 gone)

API /api/v1/request?take=200 (key from /opt/stacks/seerr/config/settings.json .main.apiKey):
total requests: 33; media-status counts: {'AVAILABLE': 18, 'PROCESSING': 7, 'DELETED': 2, 'PARTIAL': 6}
stale(>48h, not available/partial): 7 — ids 25,27,29,30,32,33,34 all APPROVED/PROCESSING createdAt 2026-08-10 (12d)
```

</details>

### UM27. lai-28 shipped unsloth.tabaska.us without a service-catalog row — deploy-process gap failing the parity check for 5 daily runs `known-issue`
**Host:** mini · **Component:** service-catalog / fix-68 (catalog-vhost-parity) · **Auditor:** triage:catalog-vhost-parity · **Work item:** `fix-97`

The unsloth vhost went live in /opt/stacks/caddy/caddy/Caddyfile via live-repo commit c70cb83 (2026-08-17 18:22:28 EDT) and Home-repo mirror 97a672e (18:35:40 EDT, lai-28), including a committed Homepage AI tile (services.yaml 'Unsloth Studio') — but no row was added to foss-setup/configs/docker-stack/service-catalog.yaml (the declared home-surface + gen-wiki-services source of truth, docs mandates 2/3). The row is absent from the local working tree, origin/main, and the check's own clone at mini /var/lib/verification/wiki-drift-repo, so committing the current in-flight WIP will NOT clear this half. catalog-vhost-parity has failed every daily run since 2026-08-18 (first run after the deploy; triage entries 08-18/19/21/22 all list the same two names — stable, not worsened). Same-commit scope gap also explains tonight's verify-06 failure (unsloth-studio missing from the rig containers manifest), matching the memory-documented process gap 'deploys skip coverage-manifest + wiki regen'. Service itself is healthy (vhost serves 200 to rig :8210). Fix = add the unsloth catalog row (+ rig manifest entry for verify-06); NOT fixed per read-only mandate. known_issue: fix-68 is in tonight's reopen-bridge baseline.

<details><summary>Evidence</summary>

```
$ ssh mini 'sudo grep -n -A3 -E "^unsloth\." /opt/stacks/caddy/caddy/Caddyfile'
315:unsloth.{$DOMAIN} {
316-	import local_tls
317-	reverse_proxy {$RIG_IP}:8210
$ ssh mini 'cd /opt/stacks/caddy && sudo git show -s --format="%h %ci %s" c70cb83'
c70cb83 2026-08-17 18:22:28 -0400 unsloth-studio: unsloth.tabaska.us vhost (rig :8210) + Homepage AI tile
$ git show -s --format="%h %ci %s" 97a672e
97a672e 2026-08-17 18:35:40 -0400 lai-28: Unsloth Studio on the rig — web UI, llama-swap lanes, MCP tools
$ grep -nE 'unsloth|principal' foss-setup/configs/docker-stack/service-catalog.yaml; echo exit=$?
exit=1   (85 'name:' rows total, neither present)
$ ssh mini 'grep -E "unsloth|principal" /var/lib/verification/wiki-drift-repo/foss-setup/configs/docker-stack/service-catalog.yaml; echo catalog-grep-exit=$?'
catalog-grep-exit=1
tonight's results.json: "output": "VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth'] (live Caddy vhost, no catalog row/url — add it)", exit_code 1
$ ssh mini 'grep -l catalog-vhost-parity /var/lib/verification/triage-*.md'
triage-2026-08-18.md triage-2026-08-19.md triage-2026-08-21.md triage-2026-08-22.md (08-18 entry already names both principal-ai and unsloth)
```

</details>

### UM28. lai-28 residual: unsloth.tabaska.us vhost live+committed but never added to the service catalog `known-issue`
**Host:** mini · **Component:** service-catalog.yaml / catalog-vhost-parity (fix-68) · **Auditor:** cross:docs-tracker-truth · **Work item:** `fix-97`

lai-28 is DONE-marked (progress.json) and its Caddy vhost unsloth.{$DOMAIN} is committed at HEAD (repo Caddyfile line 315) and live, but service-catalog.yaml never got an unsloth row. `git log -S unsloth -- service-catalog.yaml` is EMPTY — it was added to the Caddyfile, homepage services.yaml (line 350) and rig.containers by 97a672e, but the catalog leg was skipped. catalog-vhost-parity FAILs on ['principal-ai','unsloth'] (principal-ai = the KNOWN in-flight session, not filed). Matches the 'deploys skip coverage-manifest' process gap. NOT fixed per read-only mandate — repo edit needed (add catalog row + regen). known_issue: covered by open task fix-68 (catalog-vhost-parity in the baseline), but the unsloth content is a lai-28 completion residual.

<details><summary>Evidence</summary>

```
$ grep -rn 'unsloth' foss-setup/configs/docker-stack/service-catalog.yaml  -> (no matches)
$ git log --oneline -S 'unsloth' -- foss-setup/configs/docker-stack/service-catalog.yaml -> (empty)
$ git show HEAD:.../caddy/Caddyfile | grep -n unsloth -> 315:unsloth.{$DOMAIN} {
$ grep unsloth .../homepage/config/services.yaml (HEAD) -> 350:- Unsloth Studio: ... 352: href: https://unsloth.tabaska.us
results.json catalog-vhost-parity: FAIL :: VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth']
```

</details>

### UM29. Reconciler timer check's 'last run not failed' clause is a dead guard — compares systemd Result against a value it never takes ('failed')
**Host:** mini · **Component:** soularr-reconcile-timer-healthy (verification check, checks.d/soularr-backlog.yaml:38) · **Auditor:** meta:soularr-backlog · **Work item:** `fix-100`

Check 2 cmd: `systemctl is-active --quiet ...timer && [ "$(systemctl show -p Result --value soularr-denylist-reconcile.service)" != failed ] && echo RECONCILE_TIMER_OK || echo RECONCILE_TIMER_BAD`. The file comment (lines 31-34) states the check must catch 'if the timer stops OR the last run failed'. The timer-stopped half works. The last-run-failed half is DEAD: systemd's service `Result` property uses the ServiceResult enum (success/exit-code/timeout/signal/core-dump/oom-kill/...) and NEVER the literal string `failed`. A failed one-shot run reports `Result=exit-code` (or timeout/signal), so `[ "exit-code" != failed ]` is always true and the check still emits RECONCILE_TIMER_OK — a false green. The 'failed' state lives in ActiveState / `systemctl is-failed`, not Result. Live-verified on mini 2026-08-23: Result=success on last (successful) run; across ALL 137 loaded services Result is only ever `success` (68 valued + 69 blank), never `failed`; ActiveState=inactive and is-failed=inactive carry the actual state. This is failure-pattern #6 (silent scheduled-job failure) — exactly what the check purports to guard, yet cannot. Impact is bounded: the service carries OnFailure=ntfy-notify (independent alert), and the paired consumer probe (check 1, soularr-denylist-no-ghosts) still catches ghost re-accumulation within 6h-3d, so a failed reconcile is not wholly silent. Correct fix: use `systemctl is-failed --quiet ...service` (invert) or compare `Result = success` or `ActiveState != failed`. NOT fixed per read-only mandate. known_issue=false: fix-56 is DONE (in progress.json done) — the bug is inside the shipped deliverable and is not covered by any open task.

<details><summary>Evidence</summary>

```
$ grep -n 'Result --value' /opt/verification/checks.d/soularr-backlog.yaml
38:    cmd: 'systemctl is-active --quiet soularr-denylist-reconcile.timer && [ "$(systemctl show -p Result --value soularr-denylist-reconcile.service)" != failed ] && echo RECONCILE_TIMER_OK || echo RECONCILE_TIMER_BAD'

$ ssh mini 'systemctl show -p Result --value soularr-denylist-reconcile.service'
success
$ ssh mini 'systemctl show -p ActiveState --value soularr-denylist-reconcile.service; systemctl is-failed soularr-denylist-reconcile.service'
inactive
inactive

# Proof 'failed' is never a Result value across the whole host:
$ ssh mini "systemctl show '*.service' -p Result 2>/dev/null | sort | uniq -c"
     68 
     69 Result=success

# 'failed' lives in ActiveState/is-failed, not Result (verified on the live unit above).
```

</details>

### UM30. fix-69 REGRESSION: host-level unpackerr reinstalled on mini via automated apt, retirement didn't stick `known-issue`
**Host:** mini · **Component:** unpackerr (host deb service) · **Auditor:** svc:unpackerr · **Work item:** `fix-96`

fix-69 retired the mini host-level unpackerr on 2026-08-03 (apt purge). It came back ~14h later: apt history shows an unattended, scripted reinstall on 2026-08-04 04:30:08 (force-confdef/force-confold flags, 04:30 maintenance window) of unpackerr=0.15.2-960 (newer than the purged 0.13.1-613). It is now unit enabled+active, PID 104964 running ~19.5d, deb in 'ii' state, /etc/unpackerr recreated 2026-08-04 04:30. This is the fix-69 residual named in the failure baseline (check unpackerr-host-retired, red since Aug 4), confirmed still failing and re-characterized: it is a full reinstall, not a leftover unit file — root cause is that whatever provisioning ran at 04:30 still DECLARES the unpackerr host package, so the manual purge is auto-reverted. Operational impact is LOW: the reinstalled instance runs the stock example config (only sonarr+radarr blocks, pointing at placeholder http://192.168.1.2:{7878,8989} which does not exist on this LAN), so it reaches no real arr, extracts/deletes nothing, and is journal-silent (1 line since Aug 4). The REAL extractor is the NAS container (proven green above). Risk is a persistent false 'unpackerr runs on mini' signal + a red monitoring check that will keep recurring until the package is removed from provisioning. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini: systemctl list-unit-files unpackerr.service -> 'unpackerr.service enabled enabled'; is-active -> active; pgrep -x unpackerr -> 104964 (ELAPSED 19-11:53:57); dpkg -l unpackerr -> 'ii unpackerr 0.15.2-960'
/var/log/apt/history.log:
  2026-08-03 14:33:16 'apt-get purge -y unpackerr' Purge: unpackerr:amd64 (0.13.1-613)
  2026-08-04 04:30:08 '/usr/bin/apt-get -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold install unpackerr=0.15.2-960' Install: unpackerr:amd64 (0.15.2-960)
journalctl -u unpackerr --since 2026-08-04 05:00 | wc -l -> 1 ; --since 2026-08-22 -> 'No entries'
/etc/unpackerr/unpackerr.conf blocks: sonarr=1 radarr=1 lidarr=0 readarr=0 whisparr=0 (stock example, targets 192.168.1.2)
results.json: unpackerr-host-retired=fail 'unit=1 proc=1 pkg=1 | UNPACKERR_BACK'
```

</details>

### UM31. unpackerr-host-retired red re-verified — ROOT CAUSE FOUND: ansible package manifest still declares unpackerr, reinstalling it nightly `known-issue`
**Host:** mini · **Component:** unpackerr-host-retired / ansible-pull · **Auditor:** meta:host-hygiene · **Work item:** `fix-96`

Known baseline failure (fix-69 reopen candidate) — re-verified still failing: unit=1 proc=1 pkg=1, unpackerr.service enabled and running since 2026-08-04 04:30:10 EDT (2 weeks 4 days). Root cause pinned: fix-69 purged the package live on 2026-08-03 14:33 but never removed line 59 (`unpackerr`) from foss-setup/hosts/macmini/pkglist.apt-manual.txt — the sbom-04 manifest the ansible-pull base role enforces as state=present (M-an1 'manifest becomes the enforcer'). ansible-pull.timer (daily ~04:2x) reinstalled unpackerr=0.15.2-960 at 04:30:08 on 2026-08-04, one day after the purge, and re-converges it every night — the retirement will keep being reverted until that manifest line is deleted (repo edit + next pull, or export-manifests.sh re-run post-purge). Mitigating: /etc/unpackerr/unpackerr.conf now contains zero 192.168.x.x IPs (the original SL18 dead-subnet polling + cleartext arr keys are absent) and the journal is empty over 6h — it runs idle. The check itself is doing its job (caught the resurrection next-day). NOT fixed per read-only mandate. Classic repo-vs-live drift: the live fix never landed in the repo manifest.

<details><summary>Evidence</summary>

```
ssh mini 'systemctl status unpackerr' → Active: active (running) since Tue 2026-08-04 04:30:10 EDT; Loaded: enabled
zgrep apt history → Start-Date: 2026-08-03 14:33:16 / Commandline: apt-get purge -y unpackerr ; then Start-Date: 2026-08-04 04:30:08 / Commandline: /usr/bin/apt-get -y -o Dpkg::Options::=--force-confdef ... install unpackerr=0.15.2-960
journalctl -u ansible-pull --since 2026-08-04: 'ansible-ansible.builtin.apt Invoked with name=[... unpackerr ...] state=present'
grep -rn unpackerr foss-setup/hosts/ → foss-setup/hosts/macmini/pkglist.apt-manual.txt:59:unpackerr
sudo grep -oE '192\.168\.[0-9]+\.[0-9]+' /etc/unpackerr/unpackerr.conf → (no matches)
```

</details>

### UM32. Deployed rig.containers manifest on mini lags repo — unsloth-studio missing (containers-manifest-rig fails daily) `known-issue`
**Host:** mini · **Component:** verification-coverage/rig.containers (deployed asset) · **Auditor:** meta:coverage-diff · **Work item:** `fix-97`

The coverage manifest deployed at mini:/opt/verification/coverage/rig.containers is MISSING the `unsloth-studio` entry that exists in the repo copy. Repo md5 91f84f4... vs deployed b4e80f1..., diff shows exactly one line (`unsloth-studio`) present in repo but absent from deployed. The container IS running live on rig (verified in docker ps), so the deployed containers-manifest-rig check sees a running-but-unlisted container and FAILs on every run. This is the classic deploy-lag: lai-28 added unsloth-studio to the repo manifest but the yaml was never scp'd to the root-owned /opt/verification/coverage/. Matches reopen-bridge item verify-06 (containers-manifest-rig — unsloth-studio missing from manifest). RE-VERIFIED live 2026-08-23 15:2x EDT: still holds. NOT fixed per read-only mandate — the fix is to copy the repo manifest to the deployed path (root: ssh sudo tee).

<details><summary>Evidence</summary>

```
$ md5 repo coverage: 91f84f438faa50cb11f5827062cdbe8c rig.containers
$ ssh mini 'md5sum /opt/verification/coverage/rig.containers' -> b4e80f103eea94f3d485f3707da78617
$ diff <(ssh mini cat .../rig.containers|sort) <(sort repo rig.containers)
20a21
> unsloth-studio
$ ssh rig 'docker ps --format {{.Names}}' | grep unsloth -> unsloth-studio  (running live)
```

</details>

### UM33. Guard samples lexicographically-first 5 files, not 'newest N' as documented — catches this failure only by luck and masks its scope
**Host:** mini · **Component:** verification/b2-bucket-guard.py --immutable · **Auditor:** triage:b2-restic-immutable · **Work item:** `fix-82`

foss-setup/verification/bin/b2-bucket-guard.py check_immutable() calls b2_list_file_versions with maxFileCount=5 and no startFileName; B2 returns versions in LEXICOGRAPHIC fileName order, so the sample is mini/config + the alphabetically-first mini/data packs — never anything under rig/. The docstring (line 11-12) claims 'the newest N upload versions each carry per-file GOVERNANCE retention'. Two consequences: (1) had the code matched its stated intent, this failure would be INVISIBLE (newest uploads are always freshly locked) — the check catches the decay only because mini/config sorts first; (2) fail-fast on the first bad file reports 1 filename while 1239 versions across both repos are actually expired, so daily triage under-scoped the problem for 6 days. Verified live: the check-sampled first-5 are mini/config EXPIRED, 3 LOCKED packs, 1 EXPIRED pack; rig/ files (716 expired) are never sampled. The fix-22 reopen should make the check assert the aging class explicitly (e.g., scan for any expired-retention upload version, or sample per-prefix) and fix the docstring. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/verification/bin/b2-bucket-guard.py lines 114-125: files = call(..., 'b2_list_file_versions', {'bucketId': br['bucketId'], 'maxFileCount': SAMPLE_VERSIONS})['files'] ... for f in uploads: ... fail(f"file {f['fileName']} not retention-locked...")  # no startFileName -> B2 lexicographic order; docstring line 11: '2. the newest N upload versions each carry per-file GOVERNANCE retention'
Live listing, check-sampled first 5 (lexicographic, as guard sees):
 mini/config EXPIRED
 mini/data/00/004d315f... LOCKED
 mini/data/00/004e6c32... LOCKED
 mini/data/00/00586fba... EXPIRED
 mini/data/00/007be98a... LOCKED
rig/ prefix holds 3363 of 5673 versions (716 expired) and is never reachable within the first 5 lexicographic names.
```

</details>

### UM34. locks probe fails open: unreachable/500ing arr APIs and missing keys count as 0 locks, so the check prints status=OK exactly when the storm is worst
**Host:** mini · **Component:** verification/bin/nas-io-storm-probe.py (arr-sqlite-not-locked) · **Auditor:** meta:nas-io-storm · **Work item:** `fix-100`

In probe_locks (/Users/brandontabaska/GitHub/Home/foss-setup/verification/bin/nas-io-storm-probe.py lines 74-77 nokey and 84-86 err), a missing env key or ANY urllib exception (timeout, connection refused, HTTP 500) appends '<arr>=nokey'/'<arr>=err' and contributes 0 to the total; line 102 then emits status=OK whenever total<=5. The check's own header documents that a severe lock storm makes the arr log API itself 500 ('database is locked' -> API 500s, the surface musicseerr/soularr failed against) — so in the worst-case regression, all three arrs fast-500, the probe prints 'arr_locked_last15m=0 ... status=OK [lidarr=err radarr=err whisparr=err]' and the regression guard PASSES vacuously. Today's live run proves keys/ports/API versions are currently fine (real counts came back for all three arrs), so this is a latent fail-open, not an active miss. Secondary: worst-case runtime is 3 x 15s urllib timeouts = 45s+ against the check's 40s runner timeout — an accidental fail-closed backstop that only triggers when all three HANG, not when they fast-500. Fix (not applied, read-only mandate): emit a non-OK status (e.g. status=ERR) when any — or at minimum all — arrs report nokey/err.

<details><summary>Evidence</summary>

```
foss-setup/verification/bin/nas-io-storm-probe.py:
  74-76:  key = os.environ.get(f"{name.upper()}_API_KEY")
          if not key: parts.append(f"{name}=nokey"); continue
  84-86:  except Exception: parts.append(f"{name}=err"); continue
  102:    status = "OK" if total <= LOCK_MAX else "STORM"
checks.d/nas-io-storm.yaml:40: expect: 'status=OK'  # matches the vacuous all-err line
Live proof the surface currently works: arr_locked_last15m=5 max=5 status=OK [lidarr=2 radarr=0 whisparr=3]
```

</details>

### UM35. Only verification check for paperless is liveness-grade (login-page render), no consumer flow-through probe
**Host:** mini · **Component:** verification/checks.d · **Auditor:** svc:paperless · **Work item:** `fix-100`

The sole check `mini-paperless` (checks.d/mini-services.yaml, task_id docker-05) greps 'Paperless' out of the login page — it proves app+backend render but not that documents are searchable/retrievable (the consumer feature). Per mandate 2 (30+ green-but-broken services found 2026-07-16) this is a coverage gap for a Tier-1-data service. A flow-through check exists trivially: token-authed /api/documents/?query=... asserting count>0 and a document download asserting bytes (both proven working in this audit). Lane reference had pre-flagged this as liveness-only; no open fix-NN covers it. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
grep -A6 'mini-paperless' foss-setup/verification/checks.d/mini-services.yaml
  - id: mini-paperless
    name: "paperless-ngx renders its login page (app+backend, not just a redirect)"
    cmd: curl -sf -m 8 http://localhost:8000/accounts/login/ | grep -o 'Paperless' | head -1
    expect: '^Paperless$'
    severity: crit
    task_id: docker-05
(today's audit run /tmp/verify-audit-uc/results.json: {"id": "mini-paperless", "status": "pass", "output": "Paperless"} — only paperless-matching check in the 388-check run)
```

</details>

### UM36. Liveness check masquerading as substantive: name claims 'docker socket + probes' healthy but the chain is docker-inspect -> /healthz -> unconditional 200
**Host:** mini · **Component:** verification/checks.d/bug-intake.yaml: bug-triage-evidence-armed · **Auditor:** meta:bug-intake · **Work item:** `fix-100`

The fast-tier check runs `docker inspect --format '{{.State.Health.Status}}' bug-triage-evidence` and the container's own healthcheck only hits http://localhost:8410/healthz — whose handler (foss-setup/configs/docker-stack/stacks/journaling/bug-triage/evidence-server.py line 368-370) returns {"ok": True, "services": [...]} unconditionally, touching neither the docker socket nor any probe target. The check name asserts "read-only collector is healthy (docker socket + probes)" which the probe does not verify: a broken docker-socket mount or dead probe target would still report 'healthy' at fast-tier cadence. Impact is bounded: the daily bug-triage-e2e exercises the evidence path on BOTH branches (BUGTRIAGE_OK and the SKIP_MODEL_UNAVAILABLE degrade still requires a machine-gathered evidence comment, per bugtriage-e2e.py lines 12-13), so detection lag is at most ~24h, not indefinite. Remedy (NOT applied per read-only mandate): either rename the check to state honestly what it verifies (process serves /healthz), or deepen the container healthcheck to hit /evidence?service=<known-service> so the docker-socket leg is actually exercised fast-tier. Not covered by any open task (fix-67 covered the ntfy leg; bug-02 is the shipped feature).

<details><summary>Evidence</summary>

```
$ ssh mini "docker inspect --format '{{json .Config.Healthcheck.Test}}' bug-triage-evidence"
["CMD-SHELL","python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8410/healthz')\" || exit 1"]
$ grep -n -A2 '/healthz' foss-setup/configs/docker-stack/stacks/journaling/bug-triage/evidence-server.py
368:        if parsed.path == "/healthz":
369:            self._send(200, {"ok": True, "services": sorted(PLAYBOOKS)})
370:            return
$ grep -n 'evidence' foss-setup/verification/bin/bugtriage-e2e.py | head -3
12:       * an evidence-only degrade comment (model unavailable  -> BUGTRIAGE_SKIP_MODEL_UNAVAILABLE
13:         under rig GPU contention; the pipeline still posted the machine-gathered evidence)
```

</details>

### UM37. WAN exposure sweep probes a 22-port list frozen at the 2026-07-17 fix-24 audit; the fleet listener surface has since grown to ~90 distinct ports, so a mistaken forward of any post-audit service port is invisible to the crit check
**Host:** mini · **Component:** verification/checks.d/edge.yaml — edge-wan-port-posture · **Auditor:** meta:edge · **Work item:** `fix-101`

The check's design is consumer-grade (true off-net seedbox vantage, avoiding the NAT-hairpin blind spot), but its fixed port list (22 80 443 853 2222 3000 3254 5000 5001 5945 6969 7878 8123 8443 8686 8787 8789 8790 8989 9696 13091 32400) predates the entire local-AI buildout and other 2026-08 deploys. The repo's own expected-listeners baselines (verification/assets/expected-listeners/{mini,nas,rig}.ports) now enumerate ~90 distinct listener ports, and none of the high-value newcomers are swept: syncthing 22000 (deliberately opened on rig's LAN firewall per the no-cloud mesh — a classic accidental-forward candidate), minecraft 25565, immich 2283, seerr 5055, comfyui 8188/8189, bioclip 8199, unsloth-studio 8210, sunshine 47984/47989/47990/48010, memos 5230, n8n 5678, searxng 8888, kiwix 8092. The check title claims 'no unexpected WAN ports open' — a class-level claim it can only back for 21 non-Plex ports. Mitigations: the Dream Wall offers no UPnP/NAT-PMP (verified in the fix-24 audit), so only a manual GUI forward can open a port; and a live spot-check of 4 high-value new-era ports (22000 25565 47989 8210) found all closed, only 32400 answering. Recommended fix (NOT applied per read-only mandate): regenerate the probe list from the expected-listeners baselines (or top-N nmap-common + all baseline ports batched to stay under the 60s cap) so the list tracks deploys, per the 100%-coverage tripwire mandate. fix-24 is closed and no open task tracks refreshing this list.

<details><summary>Evidence</summary>

```
$ cat foss-setup/verification/assets/expected-listeners/*.ports | grep -oE '^[0-9]+' | sort -n | uniq | tr '\n' ' '
22 53 80 111 139 443 445 662 853 892 1716 2049 2222 2283 2322 3000 3001 3002 3010 3030 3261 3263 3264 3265 3333 3334 4000 4045 4533 5000 5001 5055 5230 5355 5357 5566 5656 5678 6767 6969 7777 7878 8000 8001 8010 8020 8080 8081 8082 8083 8084 8085 8090 8092 8096 8181 8188 8189 8191 8199 8210 8212 8337 8384 8686 8688 8765 8789 8790 8880 8888 8899 8931 8945 8989 8998 9000 9292 9696 9999 11434 13378 22000 25565 25600 32400 47984 47989 47990 48010
(check probes only: 22 80 443 853 2222 3000 3254 5000 5001 5945 6969 7878 8123 8443 8686 8787 8789 8790 8989 9696 13091 32400)
$ WAN=$(ssh mini 'curl -s -m 10 https://ifconfig.me'); ssh seedbox "for p in <check's 22 ports> 22000 25565 47989 8210; do (timeout 4 bash -c \"</dev/tcp/$WAN/\$p\" >/dev/null 2>&1 && echo \$p) & done; wait" | sort -n
32400
```

</details>

### UM38. Runbook wiki/runbooks/docker.md is a dead path on 5 of 12 ha checks (live wiki 404)
**Host:** mini · **Component:** verification/checks.d/ha.yaml (runbook metadata) · **Auditor:** meta:ha · **Work item:** `fix-99`

ha-http (crit), ha-api-auth, ha-hue-lights, ha-lights-available, ha-assist-rig-llm-reachable all carry runbook: wiki/runbooks/docker.md. No wiki/runbooks/ directory exists in the repo, no wiki/docs/runbooks/docker.md exists, and the live wiki 404s at /runbooks/docker/ — so the alert an operator gets for a full HA outage (ha-http is crit) links a nonexistent doc. The sibling form wiki/runbooks/backup-restore.md (ha-backup-offsite-fresh) DOES resolve on the live site (/runbooks/backup-restore/ = 200) because wiki/docs/runbooks/backup-restore.md exists — the wiki/runbooks/ prefix maps to the mkdocs site root, so only docker.md is truly dead. Note for other lanes: the same wiki/runbooks/* legacy form appears 130+ times fleet-wide (rig.md x32, docker.md x27, verification.md x24, nas.md x16, alerting.md x13) — each target needs the same existence check. Correct fix for the ha file: repoint the 5 checks at wiki/docs/runbooks/ha-health.md (exists, 200), which is already this file's canonical runbook. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ls foss-setup/wiki/runbooks -> No such file or directory
$ ls foss-setup/wiki/docs/runbooks/docker.md -> No such file or directory (backup-restore.md, ha-health.md, reverse-proxy.md all EXIST there)
$ curl -sk --resolve wiki.tabaska.us:443:192.168.10.2 -o /dev/null -w '%{http_code}' https://wiki.tabaska.us/runbooks/docker/ -> 404
$ ... /runbooks/backup-restore/ -> 200 ; /runbooks/ha-health/ -> 200
$ grep -rh 'runbook:' verification/checks.d/ | sort | uniq -c | sort -rn | head -5 -> 32 wiki/runbooks/rig.md; 27 wiki/runbooks/docker.md; 24 wiki/runbooks/verification.md; 18 wiki/docs/runbooks/git-hygiene.md; 16 wiki/runbooks/nas.md
```

</details>

### UM39. Storm tripwire is a chronic false positive: legit IPTorrents primary-source dominance trips the 60% share threshold with no rate dimension `known-issue`
**Host:** mini · **Component:** verification/checks.d/media-indexers.yaml :: arr-grab-source-not-storming · **Auditor:** meta:media-indexers · **Work item:** `fix-100`

Failing in this morning's 10:29 EDT run and re-verified still failing live this evening (share 68%->69%, n=80). Sampled the 16 most recent grab records across radarr+sonarr: all are legitimate English 1080p BluRay/WEB-DL releases of monitored titles spread over ~9 days (2026-08-13..08-22, ~2 grabs/day) — nothing like the original fix-50 storm (~hourly re-grabs of OWNED titles as foreign-audio junk). IPTorrents is the fleet's designated main content source (per this same file's iptorrents check comment), so it will legitimately dominate the last-80-grabs window indefinitely; DOMINATE_SHARE=0.60 + auto_enabled=YES therefore warns forever. Worse, a REAL storm would produce an identical SHARE_STORM output line, so the chronic red masks the exact signal the check exists for (the SM23/SM38 alert-fatigue anti-pattern the file's own comments rail against). Missing dimension is grab RATE (grabs/hour) and/or owned-title re-grab detection; alternatives: exempt/raise threshold for the designated primary indexer. Covered by today's reopen-bridge baseline mapping this check id to fix-50 (reopen-candidate). NOT fixed per read-only mandate. Script: /Users/brandontabaska/GitHub/Home/foss-setup/verification/bin/arr-grab-indexer-share.py (DOMINATE_SHARE=0.60, MIN_GRABS=10, pageSize=40 per arr).

<details><summary>Evidence</summary>

```
ssh mini 'python3 …results.json…' -> arr-grab-source-not-storming | fail | SHARE_STORM top='IPTorrents (Prowlarr)' share=68% n=80 auto_enabled=YES (run_ts 2026-08-22T10:29:50-04:00)
ssh mini 'sudo sh -c "RADARR_API_KEY=… SONARR_API_KEY=… python3 /opt/verification/bin/arr-grab-indexer-share.py share"' -> SHARE_STORM top='IPTorrents (Prowlarr)' share=69% n=80 auto_enabled=YES — a live indexer is dominating grabs (junk-grab storm)
radarr history sample (eventType=1, desc): 2026-08-22T20:31 | IPTorrents (Prowlarr) | The Matrix Resurrections 2021 Proper 1080p BluRay…; 2026-08-21T11:36 | … Backrooms 2026 NORDiC 1080p BluRay…; 2026-08-18T13:28 | … Booksmart 2019 1080p BluRay… (8 grabs span 08-13..08-22 — ~2/day, varied monitored titles, no dub-junk re-grabs)
```

</details>

### UM40. 22 of 28 checks carry dead runbook pointers (wiki/runbooks/docker.md, dns.md, mini.md do not exist anywhere in the repo)
**Host:** mini · **Component:** verification/checks.d/mini-services.yaml (runbook fields) · **Auditor:** meta:mini-services · **Work item:** `fix-99`

The runbook field is propagated into the runner's results/alert payload (checks_runner.py line ~229), so during an incident the pointer is the operator's jump-off — and for 22 checks in this file it 404s. wiki/runbooks/docker.md (19 checks, incl. crit mini-caddy-running, mini-paperless, mini-forgejo, mini-ntfy), wiki/runbooks/dns.md (crit mini-adguard-running), wiki/runbooks/mini.md (both wiki-rag checks) resolve to nothing: runbooks live at foss-setup/wiki/docs/runbooks/ and no docker.md/dns.md/mini.md exists there or anywhere else (closest real files: dns-outage.md, update-images.md, hosts/mini.md). The 6 checks written after the mkdocs restructure use correct wiki/docs/... paths and all resolve (reverse-proxy.md, services/miniflux.md, dns-outage.md, rig-btrfs-readonly-recovery.md — all FOUND). This is a fleet-wide legacy pattern, not unique to this file: the wiki/runbooks/ prefix appears ~140+ times across checks.d (rig.md x32, docker.md x27, verification.md x24, nas.md x16, alerting.md x13...) — recommend a repo-wide lint (extend bin-refs-present.sh) rather than a per-file patch. Not fixed per read-only mandate.

<details><summary>Evidence</summary>

```
cd foss-setup && for r in wiki/runbooks/docker.md wiki/runbooks/dns.md wiki/runbooks/mini.md; do [ -f $r ] || [ -f verification/$r ] || echo "NOT-DIRECT $r"; done
-> NOT-DIRECT all three; ls wiki -> docs mkdocs.yml (no runbooks/ dir)
find . -name docker.md -o -name dns.md -o -name mini.md -> only wiki/docs/hosts/mini.md and wiki/docs/reference/checks/dns.md (neither is the referenced path)
grep -rh 'runbook:' verification/checks.d/*.yaml | sort | uniq -c | sort -rn -> 32 wiki/runbooks/rig.md, 27 wiki/runbooks/docker.md, 24 wiki/runbooks/verification.md ...
```

</details>

### UM41. 8 checks decayed at bare status-code liveness despite the fix-62/SL35 deepening pass: forgejo, ntfy, healthchecks, uptime-kuma, navidrome, seerr, beszel, dockge
**Host:** mini · **Component:** verification/checks.d/mini-services.yaml (8-check liveness cohort) · **Auditor:** meta:mini-services · **Work item:** `fix-100`

fix-62/SL35 deepened paperless/wallabag/mealie/tautulli to app-layer probes but left these at 'curl -w %{http_code}' against / (200 or a login-redirect 302/307). Per the standing mandate these are liveness, not consumer probes: forgejo (crit!) could serve 200 from the front layer while git/db is wedged; each has a cheap app endpoint available (forgejo /api/v1/version or /api/healthz, ntfy /v1/health, healthchecks /api/v3/status or a real ping, kuma /api/status-page/*, navidrome /ping subsonic, seerr /api/v1/status, beszel/dockge app APIs). Deliberately NOT filed for: mini-miniflux (deep DB siblings mini-miniflux-feeds-fresh/articles-flowing cover the consumer end), mini-caddy-running (companioned by the consumer-grade mini-caddy-live-config-current drift check), mini-adguard-running (dns.yaml dns-mini-internal/external do real resolution). Staleness angle re-verified live: all six hardcoded expected codes from 2026-07-07 still match today (3030=200, 8080=200, 8001=302, 3001=302, 4533=302, 5055=307, 8090=200, 5001=200) — the baselines are current, the probes are just shallow. Not fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'for u in "3030 /" "8080 /" "8001 /" "3001 /" "4533 /" "5055 /" "8090 /" "5001 /"; do set -- $u; printf "%s=%s\n" $1 "$(curl -s -o /dev/null -m 8 -w %{http_code} http://localhost:$1/)"; done'
-> 3030=200 8080=200 8001=302 3001=302 4533=302 5055=307 8090=200 5001=200 (all match the yaml expects)
repo: mini-services.yaml lines 69-77 (forgejo, severity crit, expect ^200$ on /), 79-88, 100-118, 211-229, 245-263
```

</details>

### UM42. Systematic task_id drift: 14 checks point at the wrong tasks.json task (tracker renumbering never propagated), including one 'Removed from plan' task
**Host:** mini · **Component:** verification/checks.d/mini-services.yaml (task_id fields) · **Auditor:** meta:mini-services · **Work item:** `fix-100`

Every task_id passes an existence grep, but the semantic mapping is shifted for most of the 2026-07-07-era checks — alert triage and the generated checks reference pages route responders to unrelated tasks. Mismatches (check -> declared task = actual title | correct task): mini-paperless -> docker-05 = 'Deploy Navidrome' | doc-01; mini-forgejo -> docker-09 = 'Deploy ntfy' | glue-05; mini-ntfy -> docker-10 = 'Deploy Beszel' | docker-09; mini-homepage -> docker-06 = 'Deploy Caddy' | docker-15; mini-healthchecks -> docker-07 = 'Deploy AdGuard Home' | sec-03; mini-uptime-kuma -> docker-08 = 'Deploy Dockge' | docker-11; mini-miniflux -> read-14 = 'Deploy Pinchflat' | docker-04; mini-mealie -> docker-11 = 'Deploy Uptime Kuma' | doc-02; mini-navidrome -> media-03 = '(Removed from plan) Deploy Maintainerr' | docker-05; mini-seerr -> media-02 = 'Deploy Kometa' | docker-03; mini-tautulli -> media-02 = 'Deploy Kometa' | media-01; mini-beszel -> docker-13 = 'Commit stack to Git' | docker-10; mini-dockge -> docker-01 = 'Install Docker Engine' | docker-08; mini-caddy-running -> docker-02 = 'shared edge network' | docker-06 (borderline). metube-serving/bgutil-pot-serving -> docker-02 also look misfiled (they belong to the YouTube pipeline, read-14/fix-37 territory). Correct mappings verified against current tasks.json titles. The newer checks (fix-32, fix-33, fix-20, ai-01, retro-02, read-07) are all correct. Fix is repo-side only (yaml + gen-checks-pages.py in the same commit per convention). Not fixed per read-only mandate.

<details><summary>Evidence</summary>

```
python3 tasks.json title dump:
docker-05 | Deploy Navidrome music streaming
docker-09 | Deploy ntfy push-notification backbone
docker-10 | Deploy Beszel monitoring hub + agent
docker-06 | Deploy Caddy reverse proxy with automatic HTTPS
docker-07 | Deploy AdGuard Home network DNS filtering
docker-08 | Deploy Dockge container manager
read-14 | Deploy Pinchflat — archive YouTube channels
media-02 | Deploy Kometa (Plex collections...)
media-03 | (Removed from plan) Deploy Maintainerr
media-01 | Deploy Tautulli (Plex analytics + monitoring)
docker-03 | Deploy Seerr media request portal
docker-04 | Deploy Miniflux + PostgreSQL
doc-01 | Deploy Paperless-ngx
doc-02 | Deploy Mealie
glue-05 | Self-host Forgejo
sec-03 | Immutable backups ... + Healthchecks dead-man's-switch
docker-15 | Deploy Homepage
vs mini-services.yaml task_id fields at lines 11, 65, 75, 86, 96, 106, 116, 140, 206, 216, 226, 240, 251, 261
```

</details>

### UM43. mini-homepage probes the static SPA shell (/ -> 200), a documented green-but-broken trap; /api/services JSON probe is available and unused
**Host:** mini · **Component:** verification/checks.d/mini-services.yaml:mini-homepage · **Auditor:** meta:mini-services · **Work item:** `fix-100`

The check asserts a bare 200 on http://localhost:3010/. The Homepage / response is a static skeleton that stays 200 even when services.yaml is broken or the container's DNS is dead (exactly what happened in net-16: 159 EAI_AGAIN errors/2h while / stayed green). The operator's own quirks doc says to verify via :3010/api/services JSON, not the HTML shell. Verified live today that the deeper endpoint answers (homepage_api=200), so deepening is a drop-in change: assert /api/services returns a non-empty JSON array. Classified: liveness. Not fixed per read-only mandate. Extra caution for any fixer: another session has in-flight edits to homepage services.yaml right now.

<details><summary>Evidence</summary>

```
ssh mini 'curl -s -o /dev/null -m 8 -w "%{http_code}" http://localhost:3010/' -> 200
ssh mini 'curl -s -m 8 http://localhost:3010/api/services -o /dev/null -w "homepage_api=%{http_code}"' -> homepage_api=200
repo: foss-setup/verification/checks.d/mini-services.yaml lines 90-98 (cmd: curl ... :3010/ ; expect ^200$)
```

</details>

### UM44. runbook pointer 'wiki/runbooks/nas.md' is dead for 16 checks including all 3 crits
**Host:** mini · **Component:** verification/checks.d/nas-services.yaml · **Auditor:** meta:nas-services · **Work item:** `fix-99`

16 of 24 checks (nas-ssh, nas-immich, nas-plex [all crit], nas-flaresolverr, nas-rreading-glasses-hc, nas-cwa, nas-sonarr, nas-radarr, nas-lidarr, nas-prowlarr, nas-bookshelf, stash-serving, nas-beets, nas-beets-ingest-fresh, nas-whisparr, nas-jellyfin-serves) carry runbook: wiki/runbooks/nas.md. No wiki/runbooks/ directory exists in the repo, and no nas.md exists under the real tree wiki/docs/runbooks/ either (closest: nas-host-hygiene.md, hosts/nas.md) — an operator following the alert pointer for a crit NAS outage lands nowhere. Two more checks (nas-immich-backup-freshness, nas-immich-mobile-paired) use the legacy prefix wiki/runbooks/photos.md whose page DOES exist at wiki/docs/runbooks/photos.md — mappable but stale. The runner (checks_runner.py line 229) carries the runbook string verbatim into results/alerts. The same legacy-prefix class exists in other checks.d files (wiki/runbooks/rig.md x32, docker.md x27, dns.md x6, backups.md x6 — none exist under wiki/docs/runbooks/) — other lanes own those files, noted here for the cross-file pattern. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ for p in wiki/runbooks/nas.md wiki/docs/runbooks/photos.md; do [ -f foss-setup/$p ] && echo EXISTS $p || echo MISSING $p; done
MISSING wiki/runbooks/nas.md
EXISTS wiki/docs/runbooks/photos.md
$ ls foss-setup/wiki/docs/runbooks/ | grep -E '^(rig|docker|verification|alerting|dns|backups|secrets-hygiene|nas|photos)\.md'
alerting.md
photos.md
secrets-hygiene.md
verification.md   # no nas.md, rig.md, docker.md, dns.md, backups.md
$ grep -c 'runbook: wiki/runbooks/nas.md' foss-setup/verification/checks.d/nas-services.yaml
16
```

</details>

### UM45. Sole network check is a raw TCP handshake (port-open liveness) guarding a consumer outcome the header itself names 'smart-home control'
**Host:** mini · **Component:** verification/checks.d/network.yaml — net-trusted-to-iot-reachable · **Auditor:** meta:network · **Work item:** `fix-100`

The check's cmd is `timeout 4 bash -c 'echo > /dev/tcp/192.168.20.100/80'` — a bare TCP connect. The file header states the guarded outcome is that 'phones / Home Assistant on Trusted control smart-home gear on IoT' and that on regression 'smart-home control silently dies'; the consumer end of that is the Hue HTTP API, not an L4 handshake. Concrete false-green scenario, drawn from this check's own fix-66 history: that incident was the 192.168.16.0/20 docker bridge SWALLOWING the IoT subnet — i.e. this subnet's known failure family is routing/misdirection. In the inverse variant (any container/host that claims 192.168.20.100 and listens on :80 — a web container on a mis-pinned bridge), the handshake succeeds and the check stays green while actual Hue control is dead. A same-cost consumer-grade upgrade exists and was verified working live during this audit: the Hue bridge answers unauthenticated `GET http://192.168.20.100/api/config` with identity JSON (name 'Hue Bridge', modelid BSB002) — asserting `"modelid":"BSB002"` (or bridgeid prefix) pins that the reachable listener IS the bridge, converting the probe from path-open to control-path-identity. Mitigating honesty: the check is transparently labeled a reachability probe (SH6 renamed tok=→reach= for exactly this clarity) and the sibling structural check sys-docker-vlan-overlap (system.yaml) guards the specific fix-66 recurrence, so the residual gap is the spoofed/wrong-listener case only. NOT fixed per read-only mandate. Repo and deployed copies are identical (md5 8f836d74bf8bf0401776b1cf4464a8e6 both sides), so the fix lands in the repo file + scp per verification-deploy-quirk.

<details><summary>Evidence</summary>

```
$ grep -A2 'cmd:' foss-setup/verification/checks.d/network.yaml
    cmd: >-
      timeout 4 bash -c 'echo > /dev/tcp/192.168.20.100/80' 2>/dev/null && echo reach=ok || echo reach=BAD
    expect: '^reach=ok$'

$ ssh -o ConnectTimeout=10 mini "curl -s -m 5 http://192.168.20.100/api/config" | python3 -c "...print name/modelid/swversion/apiversion..."
{'name': 'Hue Bridge', 'modelid': 'BSB002', 'swversion': '1978074000', 'apiversion': '1.78.0'}
```

</details>

### UM46. Port 8210 drift is a repo-vs-deployed baseline gap: rig.ports with 8210 (unsloth-studio, lai-28) was committed 08-17 but never deployed to /opt/verification `known-issue`
**Host:** mini · **Component:** verification/expected-listeners (fix-51) · **Auditor:** triage:lan-listeners-drift-rig · **Work item:** `fix-97`

Port 8210 is the unsloth-studio docker container (lai-28, shipped 08-16), published 0.0.0.0:8210->8000/tcp. Commit 97a672e (2026-08-17 18:35 EDT) added '8210 # unsloth-studio' to foss-setup/verification/assets/expected-listeners/rig.ports, but the deployed copy on mini (/opt/verification/assets/expected-listeners/rig.ports, root-owned, mtime 2026-08-16 19:19) predates the commit and lacks the line — so the check has flagged 8210 daily since 08-18 (triage-2026-08-17 shows only 27036,59999; 08-18 onward shows all three). This is the known silent /opt/verification deploy failure mode (root-owned dir, scp fails silently; deploys need ssh sudo tee). Same lai-28 session also missed the rig containers manifest: tonight's containers-manifest-rig fails with 'unsloth-studio' missing (verify-06 in the morning baseline) — a repeat of the documented process gap 'deploys skip coverage-manifest + wiki regen'. No exposure change: the port itself is sanctioned and repo-blessed. NOT fixed per read-only mandate; fix = sudo-deploy repo rig.ports to mini and add unsloth-studio to the manifest in the same pass.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker ps --format "{{.Names}}\t{{.Ports}}" | grep 8210'
unsloth-studio	22/tcp, 8888/tcp, 0.0.0.0:8210->8000/tcp, [::]:8210->8000/tcp

$ diff <(ssh mini 'cat /opt/verification/assets/expected-listeners/rig.ports') foss-setup/verification/assets/expected-listeners/rig.ports
26a27
> 8210    # unsloth-studio — Unsloth Studio web UI (2026-08-17)

$ ssh mini 'stat -c "%y %n" /opt/verification/assets/expected-listeners/rig.ports'
2026-08-16 19:19:44.279526620 -0400 /opt/verification/assets/expected-listeners/rig.ports  (dir owned root:root)

$ git log --format='%h %ad %s' -- foss-setup/verification/assets/expected-listeners/rig.ports | head -1
97a672e 2026-08-17 18:35:40 -0400 lai-28: Unsloth Studio on the rig — web UI, llama-swap lanes, MCP tools

tonight results.json: containers-manifest-rig fail | 20a21 > unsloth-studio
```

</details>

### UM47. fix-69 residual re-verified and worsening: 103 stale /tmp scratch entries (threshold 10), no recurring reaper, ~35 more age in within a week `known-issue`
**Host:** mini · **Component:** verification/host-hygiene (fix-69) · **Auditor:** triage:mini-scratch-hygiene · **Work item:** `fix-96`

Known residual (task fix-69, failing every daily triage since 2026-08-05; listed in tonight's reopen-bridge baseline). All 103 counted items are >=8 days old (check uses -mtime +7): 14 from 07-27, 4 from 07-28, 1 from 08-01, 5 from 08-02, 18 from 08-03, 7 from 08-05, 53 from 08-06 (lai buildout day: 48 mktemp dirs + maps/kiwix files), 1 from 08-14. Trend: 102 at the 10:29 daily run -> 103 tonight; the +1 is /tmp/tmp.dDyoRA88cY (mtime 08-14) crossing the 192h boundary during the day, not new mess. Structural cause of monotonic growth: the fix-69 (2026-08-03) SL40 remediation was a one-shot delete ('removed 56 stale /tmp agent artifacts') with a guard check but no cleanup mechanism; mini's tmpfiles.d /tmp policy has no age field (boot-only wipe) and uptime is 6w2d (fix-74 reboot deferred), so nothing is ever reaped while agent sessions keep depositing (53 entries on 08-06 alone; 18 more on 08-16, 15 on 08-17, 2 on 08-19 queued to age in -> ~138 by ~08-26). secrets=0: the SL40 world-readable session-cookie class has NOT recurred. NOT fixed per read-only mandate. Remediation candidate for /resolve-finding: a tmpfiles.d age rule or weekly reaper scoped to agent-scratch patterns, or fold into the fix-74 reboot.

<details><summary>Evidence</summary>

```
check output (tonight, results.json): secrets=0 scratch7d=103 staleresults14d=6 / HYGIENE_DIRTY
ssh mini 'find /tmp -maxdepth 1 -mtime +7 ( -type f -o -type d ) ! -path /tmp ! -name ".*-unix" ! -name "systemd-private-*" ! -name "tmux-*" -printf "%TY-%Tm-%Td\n" | sort | uniq -c' ->
 14 2026-07-27 / 4 2026-07-28 / 1 2026-08-01 / 5 2026-08-02 / 18 2026-08-03 / 7 2026-08-05 / 53 2026-08-06 / 1 2026-08-14  (total 103)
ssh mini python3 .../results.json (10:29 daily) -> 'secrets=0 scratch7d=102 staleresults14d=6\nHYGIENE_DIRTY'
newest stale item: find ... -newermt 2026-08-14 -> /tmp/tmp.dDyoRA88cY (2026-08-14)
queued to age in: find /tmp -maxdepth 1 -mtime -7 ... -> 35 items dated 2026-08-16..2026-08-19 (vstate-bake*, verif-plantfix*, tmp.*)
ssh mini grep tmpfiles.d -> 'D /tmp 1777 root root -' (no age); uptime -p -> 'up 6 weeks, 2 days'
grep -l mini-scratch-hygiene /var/lib/verification/triage-*.md -> every file 2026-08-05..2026-08-22
```

</details>

### UM48. Deployed rig.ports baseline is stale vs repo — the Aug-17 commit blessing 8210 (unsloth-studio) never landed in /opt/verification, so the rig drift check fails daily on an already-triaged port `known-issue`
**Host:** mini · **Component:** verification/lan-listeners-drift-rig · **Auditor:** meta:lan-exposure · **Work item:** `fix-97`

Repo foss-setup/verification/assets/expected-listeners/rig.ports (mtime Aug 17, md5 4ee5c763...) contains '8210 # unsloth-studio — Unsloth Studio web UI (2026-08-17)'; the deployed copy /opt/verification/assets/expected-listeners/rig.ports (mtime Aug 16 19:19, md5 650e5a6b...) does not. listener-drift.sh reads the deployed copy, so lan-listeners-drift-rig fails on port 8210 even though the repo already blessed it — the exact 'Verification deploy quirk' failure mode (scp to root-owned /opt/verification fails silently; deploy needs ssh sudo tee + verify). A stale rig.ports.bak (Aug 16) beside it shows a manual edit session that predates the repo change. This noise degrades the SM56 tripwire: a real rogue-listener alert on rig is now indistinguishable from known deploy drift. mini.ports and nas.ports deployed copies match repo exactly (md5 identical), and the deployed listener-drift.sh script matches repo (md5 1c8b03f9...). Check fails today and is mapped to fix-51 in the reopen bridge — known, but the committed-yet-undeployed baseline is the actionable root cause. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ md5sum foss-setup/verification/assets/expected-listeners/rig.ports
4ee5c763d6db7860be111dfb8cd2cc7b  (repo)
$ ssh mini 'md5sum /opt/verification/assets/expected-listeners/rig.ports'
650e5a6b9dfe23b65043fe3a3c9bb465  (deployed)
$ diff <(deployed rig.ports) foss-setup/verification/assets/expected-listeners/rig.ports
26a27
> 8210    # unsloth-studio — Unsloth Studio web UI (2026-08-17)
$ ssh mini '/opt/verification/bin/listener-drift.sh rig'
LISTENER_DRIFT=rig:8210,27036,59999 (NEW all-interface listener not in baseline — investigate: sudo ss -tlnp | grep the port)
$ ssh mini 'ls -l /opt/verification/assets/expected-listeners/'
-rw-r--r-- 1 root root 1805 Aug 16 19:19 rig.ports
-rw-r--r-- 1 root root 1743 Aug 16 19:19 rig.ports.bak
```

</details>

### UM49. Diun coverage is container-liveness only — the notify-only service's consumer end (update detection + ntfy delivery) is unprobed
**Host:** mini,nas · **Component:** checks.d/alerting.yaml: alert-diun-mini-up / alert-diun-nas-up · **Auditor:** meta:alerting · **Work item:** `fix-101`

Both Diun checks assert only container state (mini: health status; NAS: running). Diun's entire job is detecting image updates and delivering ntfy notifications; a green container with a rotten notifier config or a silently-failing watch loop is exactly the 2026-07-08 'green-but-dead chain' failure mode this file's header says it guards against. No check probes a successful recent watch cycle or notification send (e.g. journal/log freshness of a completed run, or a drill via Diun's webhook). Both checks pass live today (mini=healthy, nas=running — the mini healthcheck exists so the {{.State.Health.Status}} template does not nil out, and the NAS scoped sudoers /etc/sudoers.d/verification-diun still permits the exact inspect). Classified liveness. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini "docker inspect -f '{{.State.Health.Status}}' diun" -> healthy
ssh nas "sudo -n /usr/local/bin/docker inspect -f '{{.State.Status}}' diun" -> running
(alerting.yaml lines 25-45: expect '^healthy$' / '^running$' — no probe of a watch cycle or notification)
```

</details>

### UM50. /volume1/docker share root is world-writable (0777, no sticky bit) — fix-23 regression dated 2026-08-11 `known-issue`
**Host:** nas · **Component:** /volume1/docker share-root POSIX permissions (fix-23 world-writable class) · **Auditor:** triage:nas-worldwritable-sweep · **Work item:** `fix-92`

nas-worldwritable-sweep genuinely fails (count=1), not merely times out. The SOLE world-writable entry under /volume1/docker + /volume1/scripts is the docker share ROOT directory itself: mode 0777 (drwxrwxrwx), owned root:root, with NO sticky bit. Because there is no sticky (+t) bit, any local account or container able to traverse into /volume1/docker can create, rename, or delete ANY top-level app config directory regardless of its owner — exactly the 'compromised low-priv container tampers with a neighbour's config' vector this check was written to guard (secrets.yaml comment). This is the class fix-23 closed on 2026-07-17: the sibling share /volume1/scripts remains correctly hardened at 0755 with a permission-ctime of 2026-07-17 10:18 (the fix-23 resolution day, untouched since), whereas /volume1/docker's permission-ctime is 2026-08-11 16:14:52 EDT — i.e. the docker share root was reset back to 0777 on Aug 11, silently regressing the sweep. This morning's quiet-IO daily run (io-load 3.06) confirmed the failure by completing with count=1; it is real and reproducible, not a timeout artifact. known_issue: reopen candidate under fix-23 (present in today's reopen-suggestions.json), BUT the specific root cause was previously undiagnosed because daily LLM-triage only surfaced the CRIT sibling nas-secret-file-perms' timeout, never this warn-severity sweep — so per the audit's 'silently-worsened residual = new finding' mandate this is a genuine active regression. NOT fixed (read-only). Remediation lives in wiki/runbooks/secrets-hygiene.md; note DSM shared-folder roots carry Synology-ACL layering over POSIX bits and DSM re-applies 0777 at the mount root on shared-folder permission edits — verify the ACL (synoacltool -get /volume1/docker) and identify the Aug-11 trigger (Control Panel share edit / package update) before re-hardening, or it will drift again.

<details><summary>Evidence</summary>

```
# tonight's audit run (scratchpad results.json, generated 2026-08-22T22:23:20-04:00)
nas-worldwritable-sweep :: fail :: TIMEOUT after 60s

# this morning's quiet-IO daily run (mini /var/lib/verification/results.json, 2026-08-23 10:29)
nas-worldwritable-sweep :: fail :: '1'      # COMPLETED, count=1 -- not a timeout
nas-io-pressure         :: pass :: nas_io_load15=3.06 threshold=12 status=OK

# re-verify count this session (240s wrapper so it can finish):
$ ssh nas 'timeout 240 find /volume1/docker /volume1/scripts \( -name @eaDir -o -name "#recycle" \) -prune -o ! -type l -perm -0002 -print 2>/dev/null | wc -l'
worldwritable_count=1 find_exit=0 elapsed=240s      # find_exit=0 => completed on its own (timeout would be 124)

# identify the offending entry:
$ ssh nas 'find /volume1/docker /volume1/scripts \( -name @eaDir -o -name "#recycle" \) -prune -o ! -type l -perm -0002 -printf "TYPE=%y MODE=%m OWNER=%u:%g PATH=%p\n" 2>/dev/null'
TYPE=d MODE=777 OWNER=root:root PATH=/volume1/docker
listing_exit=1 elapsed=122s                          # exactly one match; exit 1 = suppressed perm-denied on container subdirs

# permission ctime proves the regression date vs the still-hardened sibling:
$ ssh nas 'stat /volume1/docker; stat /volume1/scripts'
/volume1/docker : Access: (0777/drwxrwxrwx)  Uid:(0/root) Gid:(0/root)  Change: 2026-08-11 16:14:52 -0400
/volume1/scripts: Access: (0755/drwxr-xr-x)  Uid:(0/root) Gid:(0/root)  Change: 2026-07-17 10:18:15 -0400   # = fix-23 resolution day
```

</details>

### UM51. STILL-OPEN-VALID: both stale 2026-07-02 @sharesnap snapshots still present, pinning media-09's reclaimed ~180GB `known-issue`
**Host:** nas · **Component:** Btrfs @sharesnap snapshots vol2/vol3 (media-13) · **Auditor:** cross:open-queue-reality · **Work item:** `media-13`

Both snapshots named in media-13 are intact: @sharesnap/movies/GMT-07-2026.07.02-16.31.06 (vol2, ID 275) and @sharesnap/tv/GMT-07-2026.07.02-16.31.03 (vol3, ID 263). While present they hold the pre-07-02 extents so media-09's reclaimed space cannot free. df: /volume2 44% used, /volume3 49% used. This is a data-protection decision (do NOT delete the only recovery point without operator sign-off) — human-gated. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh nas 'sudo btrfs subvolume list /volume2' -> path @sharesnap/movies/GMT-07-2026.07.02-16.31.06
ssh nas 'sudo btrfs subvolume list /volume3' -> path @sharesnap/tv/GMT-07-2026.07.02-16.31.03
df: /volume2 4.6T/11T 44%, /volume3 7.7T/16T 49%
```

</details>

### UM52. Active NAS IO storm at audit time flipped 4+ checks pass→fail vs this morning's daily (load15=26.57 vs 3.06); environmental, not a regression `known-issue`
**Host:** nas · **Component:** NAS IO storm (fix-55 / fix-23 cluster) · **Auditor:** triage:baseline-delta · **Work item:** `fix-91`

The only fails present tonight (22:23) but NOT in this morning's 10:29 daily run all trace to one active NAS IO storm. nas-io-pressure: tonight load15=26.57 (threshold 12, HIGH) vs 3.06 OK this morning. arr-sqlite-not-locked: tonight 20 sqlite locks in 15m (max 5, STORM: lidarr=10 radarr=4 whisparr=6) vs 0 this morning — direct consequence of the same /volume1 IO contention. metadata-search-canary (bmig-06, rreading-glasses book lookup on NAS :8790): connection error/timeout tonight vs CANARY_OK rank=4 results=14 this morning. The two fix-23 find-based checks (nas-secret-file-perms CRIT, nas-worldwritable-sweep) both TIMEOUT after 60s tonight (find over /volume1/docker starved) — nas-secret-file-perms has timed out chronically since baseline (noted verbatim in triage-2026-08-06). This matches lane-context line 27 ('NAS is under heavy IO load right now') and the fix-55 nas-io-storm cluster. Environmental-gated and currently ACTIVE — expect these to clear when NAS load normalizes; re-verify off-storm before treating as durable. NOT fixed / read-only.

<details><summary>Evidence</summary>

```
# tonight (results.json 22:23)
nas-io-pressure: nas_io_load15=26.57 threshold=12 status=HIGH  (FAIL)
arr-sqlite-not-locked: arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]  (FAIL)
metadata-search-canary: urllib connection error to 192.168.10.4:8790/api/v1/book/lookup, exit1 45s (FAIL)
nas-worldwritable-sweep: TIMEOUT after 60s (exit 124)  |  nas-secret-file-perms: TIMEOUT after 60s (exit 124)

# this morning (mini /var/lib/verification/results.json 10:29)
nas-io-pressure: nas_io_load15=3.06 threshold=12 status=OK  (PASS)
arr-sqlite-not-locked: arr_locked_last15m=0 max=5 status=OK  (PASS)
metadata-search-canary: CANARY_OK rank=4 results=14  (PASS)
```

</details>

### UM53. STILL-OPEN + WORSENED: NAS Plex frozen at 1.43.3.10793; now 103 builds behind latest, check green only via grace window `known-issue`
**Host:** nas · **Component:** Plex / edge-plex-version-current (fix-70) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-70`

fix-70 filed when exposed .10793 vs latest .10828 (past 14d grace). Live: exposed version UNCHANGED at 1.43.3.10793 — the pending Synology Plex package update was never applied — while latest advanced to 1.43.3.10896. The daily check passes as 'VERSION_OK:grace_10d' only because .10896 is a recent release inside the check's grace window; the underlying update is now further behind than at filing. Green status masks the still-pending user-facing update. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
WAN=$(curl -s https://ifconfig.me); exp via seedbox->WAN:32400/identity = 1.43.3.10793-cd55560bb
curl plex.tv/api/downloads/5.json -> latest Linux = 1.43.3.10896-cb3ebc72d
daily check edge-plex-version-current: pass, out='VERSION_OK:grace_10d'
```

</details>

### UM54. KNOWN fix-50 IPT storm has WORSENED (grab share 60%->70% over 18 days; ~430 IPT searches/day = ~72% of 600/24h budget) and is now collateral-flaking verify-06 `known-issue`
**Host:** nas · **Component:** Prowlarr / IPTorrents auto-grab + RSS (fix-50 arr-grab-source-not-storming) · **Auditor:** triage:iptorrents-idsearch-returns-results · **Work item:** `fix-94`

The co-failing arr-grab-source-not-storming (fix-50, in this morning's 10:29 baseline) is the root driver of tonight's verify-06 flake. IPTorrents is auto-grab/RSS enabled (auto_enabled=YES) and dominating the grab stream at 69% of the last 80 grabs. Triage history shows this is CHRONIC and WORSENING: IPT grab share was 60% (08-05, 08-11) -> 64% (08-12) -> 66% (08-18/19) -> 68% (08-21/22) -> 69-70% (08-23). Prowlarr logs show ~17-21 empty-term full-category IPT sweeps/hour around the clock, totalling 425 (08-21) / 432 (08-22) / 280-so-far (08-23) IPT search executions per day — roughly 72% of IPT's 600-queries/24h budget consumed by automated sync alone, leaving little headroom. This load intermittently throttles IPT (8 'ServiceUnavailable'/'Invalid Credentials' warns on 08-21), which is what flaked the verify-06 imdbid probe. Per lane rule, a silently-worsened residual is a new finding: the storm now has a NEW consumer-visible cost (first-ever verify-06 failure) and risks tipping over the 600/24h budget on a busier day, which WOULD reproduce the 2026-08-11 backlog incident (over-budget IPT searches return 0). Note IPT is a legit private tracker (not DHT junk like the original SC2/Bitmagnet incident), so the dominance itself is partly benign — but the query volume against IPT's hard budget is the real risk. NOT fixed per read-only mandate. Recommend (human): confirm which arrs still have IPT RSS/Automatic-Search on and consider throttling IPT RSS sync intervals or narrowing categories to cut the ~430/day baseline. known_issue: fix-50.

<details><summary>Evidence</summary>

```
# tonight's co-fail (local results.json)
arr-grab-source-not-storming | status=fail | "SHARE_STORM top='IPTorrents (Prowlarr)' share=69% n=80 auto_enabled=YES"

# worsening trend across mini /var/lib/verification/triage-*.md
08-05: IPTorrents 60% | 08-11: 60% | 08-12: 64% | 08-18/19: 66% (80 total) | 08-21/22: 68% | 08-23: 70%

# daily IPT search volume (grep 'Searching indexer(s): [IPTorrents]' prowlarr logs) vs 600/24h budget
2026-08-21 IPT_searches=425
2026-08-22 IPT_searches=432
2026-08-23 IPT_searches=280  (partial, ~15:1x EDT)
# empty-term category sweeps/hour on 08-22: 16-21 every hour, around the clock

# IPT throttle warns (load symptom) — nas prowlarr.txt
2026-08-21 21:37:55.2|Warn|IPTorrents|Request for IPTorrents failed with status ServiceUnavailable. Retrying in 0.63s.
2026-08-21 21:43:52.2|Warn|IPTorrents|Invalid Credentials for IPTorrents [https://iptorrents.com/t?...]
# count by day: 8 on 2026-08-21; 0 on 08-22/08-23
```

</details>

### UM55. Persistent Quad9 DoH upstream error flood — 98% of recent logs are 'unexpected EOF'/502 from the sole upstream
**Host:** nas · **Component:** adguardhome-nas / dnsproxy upstream (Quad9 DoH) · **Auditor:** svc:adguard-nas · **Work item:** `fix-89`

The adguardhome-nas log is dominated by upstream failures against its only resolver, Quad9 DoH (https://dns10.quad9.net:443/dns-query). Of the last 3000 log lines (spanning 2026/08/21 10:39 -> 2026/08/23 20:07, ~2.4 days) 2948 are 'unexpected EOF' and 2940 are 'dnsproxy: exchange failed' — roughly 1225 upstream errors/day. Also observed: HTTP 502 from Quad9 (2026/08/22 12:56:31) and TCP 'connection reset by peer' from ONE client 192.168.10.186 (client-side abort, not the resolver's fault). CONSUMER IMPACT IS CURRENTLY NIL: a live 20-name external-resolution test (single-try, 4s, no retries) via @192.168.10.4 returned 20/20 successes, so AdGuard is retrying/caching around the EOFs (most failing queries are AAAA/HTTPS record types on stale keepalive DoH connections; A lookups succeed). This is why the verification check dns-nas-external needs 3 built-in retries to stay green (checks.d/dns.yaml lines 57-59) — the retries mask a real, elevated intermittent upstream-failure rate. Concerns: (a) a resilience-purposed secondary resolver has a single upstream with no fallback configured (Quad9 DoH is by design per lane notes + README, but no second upstream means a real Quad9 outage takes the secondary down entirely, defeating its 'survive mini reboot' purpose); (b) the flood buries real signal and undermines the M28 querylog-forensics purpose. NOT fixed per read-only mandate — reported only. Suggested operator follow-up (not actioned): add a fallback upstream and/or tune DoH keepalive/parallel mode.

<details><summary>Evidence</summary>

```
$ sudo docker logs adguardhome-nas --tail 3000 | (counts)
TOTAL_TAIL=2999  QUAD9_EOF=2948  UPSTREAM_ERR=2940 (dnsproxy: exchange failed)  OTHER_ERR=33
FIRST_TS=2026/08/21 10:39:05   LAST_TS=2026/08/23 20:07:00
sample: 2026/08/23 20:00:00 [error] dnsproxy: exchange failed upstream=https://dns10.quad9.net:443/dns-query question=";frontdoor.nest.com. IN A" err="...: unexpected EOF"
2026/08/22 12:56:31 [error] dnsproxy: handling request proto=tcp err="expected status 200, got 502 from https://dns10.quad9.net:443/dns-query"
2026/08/23 19:10:07 [error] dnsproxy: reading msg proto=tcp err="reading len: read tcp 192.168.10.4:53->192.168.10.186:64333: read: connection reset by peer"
--- live client-impact probe (single-try, no retries) ---
$ for d in github.com wikipedia.org cloudflare.com ... bbc.co.uk; do dig +short +time=4 +tries=1 @192.168.10.4 $d A; done
OK=20 FAIL=0
```

</details>

### UM56. arr SQLite 'database is locked' storm (20 in 15min) was the downstream IO-starvation cascade of the same backup window; cleared by morning `known-issue`
**Host:** nas · **Component:** arr-sqlite-not-locked (fix-55) / lidarr,radarr,whisparr · **Auditor:** triage:nas-io-pressure · **Work item:** `fix-91`

Sibling check in the same nas-io-storm.yaml (task_id fix-55). At the 22:23 audit sample it read arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6] — the exact fix-55 regression signal. This is the documented consequence of the IO saturation above: under backup-window IO pressure the arrs' SQLite fsync exceeded their busy_timeout, so writers hit SQLITE_BUSY -> 'database is locked'. It self-cleared identically to the IO load: the 10:29 EDT daily run read arr_locked_last15m=0 status=OK [lidarr=0 radarr=0 whisparr=0]. Same root cause (routine Saturday Hyper Backup window), same self-clear, so this is environmental/transient, not a chronic lock storm. Corroborating same-window fallout in the audit baseline (owned by other lanes, cross-referenced not re-filed): nas-secret-file-perms (fix-23, CRIT) = 'TIMEOUT after 60s' (a /volume1 walk stalling under the same IO saturation, exactly the correlation the baseline predicts), and deluge-preimport-stuck / nas-soularr-failed-imports-fresh consistent with import contention during the window. known_issue=true, task_id fix-55. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ cat results.json -> id=arr-sqlite-not-locked status=fail
 output='arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]'  (ts 2026-08-22T22:23:20-04:00)

$ ssh mini python3 -c 'json /var/lib/verification/results.json (10:29 daily)'
 arr-sqlite-not-locked :: pass :: arr_locked_last15m=0 max=5 status=OK [lidarr=0 radarr=0 whisparr=0]

# correlated same-window fallout (other lanes' primaries, from results.json):
 nas-secret-file-perms :: fail :: TIMEOUT after 60s   (fix-23 CRIT, baseline notes 'correlates with NAS IO load')
 deluge-preimport-stuck :: fail :: PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 ...
 nas-soularr-failed-imports-fresh :: fail :: stale=2:cycling=yes JJK ...
```

</details>

### UM57. Zero-throughput / frozen-green: 0 tracks tagged in 45+ days despite daily runs
**Host:** nas · **Component:** beets (nas-30 YouTube-audio tagging layer) · **Auditor:** svc:beets · **Work item:** `fix-89`

The beets library DB (/config/beets-youtube.db) is completely empty (Tracks:0, Artists:0, Albums:0). Across 48 scheduled runs since 2026-07-08 the import.log records 36 'skip' actions and ZERO 'added'/'asis' (tagged) actions. The source dir /volume1/music/YouTube contains only the 2 initial test files from setup ('Me at the zoo.mp3' Jul 7, 'Numb (Official Music Video) [4K UPGRADE] - Linkin Park.mp3' Jul 8) - both still UNTAGGED. Two overlapping causes: (a) MeTube has produced no new YouTube audio since Jul 8, so the pipeline is effectively dormant; and (b) the DSM task runs 'beet import -q /music/YouTube' in ALBUM mode, which groups the flat directory of unrelated loose singletons into one bogus 'album' with no MusicBrainz match and skips the whole path ('skip /music/YouTube') - so even the slam-dunk strong-match 'Numb - Linkin Park' never gets tagged. The feature would not tag loose singletons even with real input; it would need '-qs' (singleton) mode. Non-destructive design is intact (copy:no/move:no, files stay in place) so nothing downstream is harmed - but the stated consumer purpose has delivered nothing. Frozen-green per taxonomy 13. NOT fixed per read-only mandate. Not covered by any open task (both beets checks pass, so it is invisible to the tracker).

<details><summary>Evidence</summary>

```
$ sudo docker exec beets beet stats
Tracks: 0
Total time: 0.0 seconds
Approximate total size: 0.0 B
Artists: 0
Albums: 0
Album artists: 0

$ grep -oE '^(skip|added|asis|import started)' /volume1/docker/beets/import.log | sort | uniq -c
     48 import started
     36 skip
(no 'added' / no 'asis' lines exist)

$ ls -la /volume1/music/YouTube
-rw-r--r-- 1 btabaska users  364408 Jul  7 23:10 Me at the zoo.mp3
-rw-r--r-- 1 btabaska users 6199886 Jul  8 10:31 Numb (Official Music Video) [4K UPGRADE] - Linkin Park.mp3

$ tail -6 /volume1/docker/beets/import.log
import started Sat Aug 22 03:15:21 2026
skip /music/YouTube
import started Sun Aug 23 03:15:32 2026
skip /music/YouTube
```

</details>

### UM58. Persistent per-container docker-stats timeouts (44,152 error lines since 2026-08-02) degrade nas container-level monitoring
**Host:** nas · **Component:** beszel-agent · **Auditor:** svc:beszel-agent-nas · **Work item:** `fix-89`

beszel-agent cannot reliably collect per-container Docker stats on the NAS: the docker stats one-shot API call (/containers/<id>/stats?stream=0&one-shot=1) repeatedly times out with 'context deadline exceeded (Client.Timeout exceeded while awaiting headers)'. 44,152 such ERROR lines since 2026-08-02 (~21 days, ~2100/day), continuing into the audit window (bursts of ~26 at 20:01:14, ongoing at 20:08:14 on 2026-08-23). HOST-level metrics are unaffected (gathered via gopsutil, not the docker socket) so the hub still shows nas up/fresh — hence this is masked at the down-status check level. Consumer impact: beszel's per-container CPU/mem breakdown for the NAS is intermittently missing/incomplete. Root cause is NAS dockerd being slow to answer the stats API under the current heavy IO load (correlates with the fleet-context NAS IO-load note and fix-23's 60s-timeout symptom, and the dockerd-slowness memory note); not a beszel-agent crash (RestartCount=0). Log read completed cleanly (no taxonomy-15 NUL corruption). NOT fixed per read-only mandate. Candidate for a new tripwire (no open task specifically tracks beszel container-stats collection loss).

<details><summary>Evidence</summary>

```
$ sudo docker logs beszel-agent --since 2026-08-02T00:00:00 2>&1 | wc -l
44152
$ sudo docker logs beszel-agent --since 2026-08-02T00:00:00 2>&1 | tail
2026/08/23 20:08:14 ERROR Error getting container stats err="Get \"http://localhost/containers/45d2bac8daed/stats?stream=0&one-shot=1\": net/http: request canceled (Client.Timeout exceeded while awaiting headers)"
2026/08/23 20:08:14 ERROR Error getting container stats err="Get \"http://localhost/containers/d0262f922c11/stats?stream=0&one-shot=1\": context deadline exceeded"
```

</details>

### UM59. Torznab keyword search returns 0 hits for every tested term — search consumer value currently zero (I/O-starved) `known-issue`
**Host:** nas · **Component:** bitmagnet · **Auditor:** svc:bitmagnet · **Work item:** `fix-89`

The reason bitmagnet earns its keep as an indexer is that Prowlarr/arrs can query its Torznab endpoint and get real hits. Right now it returns ZERO items for terms that must have hundreds of thousands of matches in a 3.9M-torrent index: q=ubuntu, q=1080p, q=x265, q=dvd all returned 0 <item> elements. GraphQL full-text search returned totalCount:0 (and on q=1080p the totalCount subquery hung past a 2min wall). Direct psql count(*) on the classified torrent_contents table also timed out >2min while the lighter torrents count(*) returned instantly — consistent with the classified-content queries being starved by the live NAS I/O storm (bitmagnet's own logs show 1068 SLOW SQL≥30s events, individual inserts up to 868s). Root cause attributed to the fix-55 I/O storm; could not fully rule out a deeper classified-index issue within the read-only budget. bitmagnet is DEMOTED to interactive-only manual fallback (fix-50), and its guard check bitmagnet-torznab-via-prowlarr is deliberately designed to PASS in this SLOW/empty-under-load state (endpoint answers caps = alive), so it does not page — but the manual-search consumer value is effectively nil while the storm persists. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ for term in 1080p x265 dvd; do curl -sm 38 "http://192.168.10.4:3333/torznab/?t=search&q=${term}&limit=10" | grep -oc "<item>"; done
torznab q=1080p items=0
torznab q=x265 items=0
torznab q=dvd items=0
$ curl -sm 40 "http://192.168.10.4:3333/torznab/?t=search&q=ubuntu&limit=10" | grep -oc "<item>" => 0
$ psql ... -tAc "SELECT count(*) FROM torrent_contents" => Command timed out after 2m 0s (SIGTERM 143)
/tmp/verify-audit-uc/results.json: bitmagnet-torznab-via-prowlarr | pass | BITMAGNET_PROWLARR_SLOW indexer=8 search=timeout endpoint=alive (manual-only fallback, load-degraded — not paging)
```

</details>

### UM60. NAS I/O storm evidenced bitmagnet-side: 1068 slow-SQL≥30s (inserts up to 868s), io-load 26.57 — chronic, re-verified `known-issue`
**Host:** nas · **Component:** bitmagnet-postgres · **Auditor:** svc:bitmagnet · **Work item:** `fix-91` · *skeptic-confirmed*

bitmagnet remains the NAS's top steady I/O consumer (fleet-sweep-2026-08-02 documented this and gap:nas-io-rootcause). Since 2026-08-02 the container logged 1068 'SLOW SQL >= 30s' gorm warnings; sampled INSERT INTO torrent_contents durations were 868949ms, 818252ms, 337295ms, 182000ms — i.e. single writes taking 3-14min. The three most recent log lines are all dhtcrawler infohash_triage slow-SQL warnings (35s/30s/47s), so the DB is degraded at probe time. The audit-safe run's nas-io-pressure check reads 26.57 vs threshold 12 (status=HIGH). NOTE: this figure is likely partly inflated by the concurrent full-fleet audit's own NAS-heavy lanes (observer effect, explicitly documented in fleet-sweep-2026-08-02 gap:nas-io-rootcause), so treat the exact 26.57 as an upper bound; the CHRONIC storm is nonetheless real and predates today. This is what degrades the torznab search above. Root cause open under fix-55 follow-up. NOT fixed per read-only mandate.

*Verify note:* Fresh independent probe (docker logs -t per-day histogram, different vantage than the original's raw grep|uniq -c) reproduces the defect and defeats the transient/backup-window refutation. Slow-SQL warnings occur EVERY day 08-16..08-23 (80-209/day) with NO Saturday clustering (Sat 08-22=155 is not an outlier); today Sun 08-23 (a non-backup day) has the HIGHEST count at 209 plus a fresh 92.4s INSERT logged at 16:20 today = DB degraded at probe time confirmed. The chronic counts on 08-16..08-21 pre-date this audit's ~08-22 start, so observer effect cannot explain the chronic slow-SQL (only the peak load figure). Last-8-day sum = 1089 ≥ the cited 1068, i.e. not decayed. The one soft spot, io-load=26.57, was a Sat-night Hyper Backup peak driven by synoimgbkptool (idx 15/22) that self-cleared to 0.90 by day and reads 10.36 now — but the finding already hedges that number as an observer-effect upper bound and the chronic bitmagnet DB degradation stands independent of it. Severity medium is appropriate: known_issue under fix-55 follow-up, impact is the background DHT-crawler write path (bitmagnet is interactive-only demoted; auto-grabs flow via IPT text search).

<details><summary>Evidence</summary>

```
$ docker logs bitmagnet --since 2026-08-02T00:00:00 | grep -oE '(SLOW SQL >= 30s|exceeded its 10m0s timeout|missing [0-9]+ info hashes)' | sort | uniq -c
   1068 SLOW SQL >= 30s
     54 exceeded its 10m0s timeout
     27 missing 1 info hashes
      6 missing 2 info hashes
$ docker logs bitmagnet ... slowLog samples: elapsed 868949.05249 / 818252.74468 / 337295.907603 (INSERT INTO torrent_contents)
/tmp/verify-audit-uc/results.json: nas-io-pressure | fail | nas_io_load15=26.57 threshold=12 status=HIGH
```

</details>

### UM61. Bookshelf book/lookup metadata search times out >45s (metadata-search-canary FAIL, reproduced live)
**Host:** nas · **Component:** bookshelf · **Auditor:** svc:bookshelf · **Work item:** `fix-89`

The primary front-of-funnel consumer path — resolving book metadata for search/requests — is currently degraded. The metadata-search-canary check (task bmig-06, the C2 canary that looks up the warm-cache canonical 'Pride and Prejudice Jane Austen') FAILED in the audit-uc run with a urllib traceback, and I reproduced it live twice: the lookup hangs the full 45s timeout. The underlying rreading-glasses metadata provider on :8789 is up and its /search returns real results in ~4.5s, so the container is fine; the timeout is in Bookshelf's full per-result metadata HYDRATION step. This is NOT in this morning's 10:29 baseline (it passed then), so it degraded during the day and correlates with the acute NAS IO storm (nas-io-pressure fail load15=26.57 vs 12; arr-sqlite-not-locked fail STORM). It degrades real libreseerr book requests too (per the check's own rationale). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
# live re-verify (key sourced on mini, never printed)
ssh mini 'K=$(grep -oP "^BOOKSHELF_API_KEY=\K.*" /etc/verification/env); BOOKSHELF_API_KEY=$K python3 -c "...book/lookup?term=Pride and Prejudice Jane Austen, timeout=45..."'
-> CANARY_EXC after 45.0s: TimeoutError('timed out')
# provider search alone is fast:
ssh mini python3 urlopen http://192.168.10.4:8789/search?query=Pride+and+Prejudice
-> 200 4.5s [{"bookId":17456445,"workId":2459845,"author":{"id":132049}}...
# audit-uc results.json: metadata-search-canary fail Traceback ... urllib.request.urlopen
```

</details>

### UM62. bookshelf SQLite 'database is locked' storm — 1610 events since Aug 2, RefreshMonitoredDownloads tasks failing; arr-sqlite check omits bookshelf
**Host:** nas · **Component:** bookshelf · **Auditor:** svc:bookshelf · **Work item:** `fix-91`

bookshelf's own SQLite DB is under lock contention: 1610 'database is locked' (SQLiteException 0x800007AF, code=Busy(5)) errors since 2026-08-02, driving downstream 'CommandExecutor: Error occurred while executing task RefreshMonitoredDownloads' failures. This is bookshelf's slice of the NAS-wide arr sqlite lock storm (arr-sqlite-not-locked fail STORM arr_locked_last15m=20). Coverage gap: that storm check's breakdown enumerates only lidarr=10/radarr=4/whisparr=6 — bookshelf is not tracked by it, so bookshelf's lock contention is invisible to the dedicated monitor. Chronic (3 weeks) and acutely worse now under the current IO storm (nas-io-pressure fail). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
PW=... ; printf '%s\n' "$PW" | ssh nas 'sudo -S docker logs bookshelf --since 2026-08-02T00:00:00 2>&1 | grep -c "database is locked"'
-> DBLOCKED_COUNT=1610
# tail sample:
[Error] TaskExtensions: Task Error [v0.4.20.129] code = Busy (5), message = System.Data.SQLite.SQLiteException (0x800007AF): database is locked / INSERT INTO Commands ...
[Error] CommandExecutor: Error occurred while executing task RefreshMonitoredDownloads
# audit-uc: arr-sqlite-not-locked fail STORM [lidarr=10 radarr=4 whisparr=6]  (bookshelf absent from breakdown)
```

</details>

### UM63. Both Bookshelf->CWA checks pass vacuously if their NAS path disappears — violates the file's own fail-loud philosophy
**Host:** nas · **Component:** bookshelf-cwa-copy-drops / cwa-ingest-not-stuck · **Auditor:** meta:media · **Work item:** `fix-100`

bookshelf-cwa-copy-drops greps /volume1/docker/bookshelf/config/logs/readarr-copy-to-cwa-ingest.log with 2>/dev/null; if the log file is missing, grep emits nothing, c is empty, and the ${c:-0} default prints drops=0 -> PASS. cwa-ingest-not-stuck runs find over /volume1/docker/calibre-web-automated/ingest with 2>/dev/null; a missing/renamed dir yields wc -l = 0 -> ingest=ok -> PASS. Both paths have already been renamed once in this pipeline's history (readarr->bookshelf migration, bmig-06 2026-07-20), so path drift is a demonstrated failure mode, and the exact original incident these checks guard (apostrophe titles silently dropped) would go invisible again. This contradicts the file's own stated invariant ('fails loudly if the mount is down/empty — a vacuous pass would hide exactly the failures we care about', used correctly by music-library-dupes, pinchflat-plex-visible, and the *-in-plex checks). Live-verified 2026-08-22 evening: both paths currently EXIST, so today's passes are real — this is a latent structural defect, not an active miss. Fix shape: assert path existence before counting (e.g. test -f/-d, else emit MISSING sentinel). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
PW=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['sudo']['nas_password'])") && printf '%s\n' "$PW" | ssh -o BatchMode=yes -o ConnectTimeout=10 nas "sudo -S -p '' sh -c 'test -f /volume1/docker/bookshelf/config/logs/readarr-copy-to-cwa-ingest.log && echo log=present || echo log=MISSING; test -d /volume1/docker/calibre-web-automated/ingest && echo ingest_dir=present || echo ingest_dir=MISSING'" 2>/dev/null
-> log=present
-> ingest_dir=present
media.yaml line 228: c=$(... grep -cE ... 2>/dev/null); [ "${c:-0}" = "0" ] && echo drops=0  # empty c from missing file defaults to 0 -> pass
media.yaml line 246: n=$(... find ... 2>/dev/null | wc -l ...); [ "${n:-1}" = "0" ] && echo ingest=ok  # find on missing dir -> wc -l prints 0 -> pass
```

</details>

### UM64. Check named 'newest immich DB dump is >1MB' actually passes if ANY dump ever was >1MB — a truncated/empty newest dump is undetectable
**Host:** nas · **Component:** checks.d/backups.yaml: backup-immich-dump-nonempty · **Auditor:** meta:backups · **Work item:** `fix-100`

cmd is `find /volume1/docker/immich/backups -name '*.sql.gz' -size +1M | grep .` (backups.yaml line 46) — no mtime filter, no sort-by-newest. With ~8+ daily 256MB dumps retained, if tonight's cron produces a 0-byte or truncated dump (the exact failure mode the check name promises to catch), the check stays green forever on the old files. Today's pass output demonstrates it: the first match printed is the week-old immich-2026-08-15.sql.gz, not the newest. Fix shape: `ls -t .../*.sql.gz | head -1 | xargs -I{} find {} -size +1M` or stat the lexicographically-last file. Companion check backup-immich-dump-fresh only proves a file was WRITTEN in 26h, not that the newest is non-trivial, so the two together still miss a fresh-but-empty dump. Classification: consumer intent, defective implementation. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh nas 'ls -lt /volume1/docker/immich/backups | head -6'
-rw-r--r-- 1 root root 256584329 Aug 22 02:31 immich-2026-08-22.sql.gz
-rw-r--r-- 1 root root 256583285 Aug 21 02:31 immich-2026-08-21.sql.gz
(... daily 256MB dumps back to Aug 18+)
Today's results.json (10:29): backup-immich-dump-nonempty | pass | /volume1/docker/immich/backups/immich-2026-08-15.sql.gz ; immich-2026-08-16.sql.gz ; ... (matches ALL dumps, oldest first — newest never singled out)
```

</details>

### UM65. REGRESSION: NAS chronic I/O-saturation storm is back — root cause is insufficient-memory btrfs metadata thrash, amplified by fix-50 grab-storm `known-issue`
**Host:** nas · **Component:** host-nas / btrfs volume1 + arr SQLite (fix-55 regression) · **Auditor:** svc:host-nas · **Work item:** `fix-91` · *skeptic-confirmed*

fix-55 was marked DONE 2026-08-02 ('NAS chronic I/O pressure + SQLite database-is-locked storm degrading 5 arr apps, killing soularr, hanging docker CLI and healthchecks') but the exact syndrome is LIVE again and sustained (phase-1 caught it at 22:02 2026-08-22; still active 16:02 2026-08-23; DSM flagged it Aug 20). Live state: load 13.7/19.7/20.7 with the IO component dominant (IO 9.94/21.45/20.58, CPU ~1.0), top shows 66.3% wa and only 1 running task — read-heavy (Dirty 744kB, Writeback 336kB) so NOT a write/backup flood. NO RAID scrub/resync (mdstat all [U]; the [UUU_] on md0/md1 is normal DS920+ system-partition state), NO active Hyper Backup/rsync/img_backup process, and NO single CPU or memory hog (all containers total ~5GB; biggest radarr 1.7GB; docker BlockIO unreported by Synology). ROOT MECHANISM: DSM's own volume_monitor logged 'Detected volume low performance due to insufficient memory' with btrfs metadata-cache misses (volume_eb_miss=14267) — the 20GB DS920+ (MemFree 261MB, ~6.4GB swapped) cannot keep the btrfs metadata working set + all containers + Plex + immich cached, so metadata is re-read from disk constantly => iowait storm. AMPLIFIER: fix-50 (arr grab-storm, also DONE 2026-08-02, failing again this morning per baseline) drives constant seedbox imports — rclone vfs cache churned 35->44.8GB at ~1GB/min while 'in use 1' during the sample. DOWNSTREAM (consumer impact, PROVEN): arr SQLite 'database is locked' storm = 20 in 15min (lidarr=10 radarr=4 whisparr=6); soularr degraded (fix-40); the mount watchdog logs 'already running — skipping this cycle'; and the fix-23 secret-perms CRIT check times out. NOT fixed per read-only mandate — reported for reopen of fix-55 (+fix-50). NB the DS920+ is already at its 20GB max, so the real remedy is reducing footprint (e.g. move bitmagnet off-NAS / cut the grab-storm), not more RAM.

*Severity adjusted high→medium during adversarial verification.*

*Verify note:* Transient weekly-backup-window spike, not the chronic HIGH memory-thrash regression claimed. Three distinctive claims refuted by fresh probes: (1) CHRONIC/SUSTAINED — the storm was caught at 22:02 Saturday 2026-08-22 (the routine weekly Hyper Backup window) and self-cleared within ~2h: at Sunday 17:59 EDT the sanctioned probe reads nas_io_load15=9.40 status=OK (below threshold 12) and arr_locked_last15m=0 status=OK (zero lock storm), down from the 13.7/19.7/20.7 the finding reported at 16:02 — matches the 'backup-window spike that self-clears is NOT a regression' taxonomy. (2) INSUFFICIENT-MEMORY BTRFS THRASH root cause — MemAvailable=12.2GB (low MemFree 233MB is normal Linux buff/cache, not starvation); the DSM volume_monitor 'insufficient memory' log is sporadic (5x in ~2 weeks, all ~19:1x EDT, most recent Aug 20 — TWO DAYS before the Aug 22/23 storm), never fired during the actual storm window, so it cannot be the mechanism. (3) 'NOT a write/backup flood / NO active img_backup process' — sibling finding idx 22 caught synoimgbkptool (Synology image-backup) as the dominant D-state process tapering like a backup winding down, Saturday timing = backup window, synobackupd resident; this is a backup-driven flood, not read-heavy metadata thrash. The fix-55 recurrence around the backup window is genuine and is already the known reopen candidate (idx 15/22) with real windowed consumer impact (SQLite locks during peak), so downgrade to medium (reschedule backup into 4-7AM / ack) rather than refute outright — but the HIGH chronic-memory-starvation framing does not hold.

<details><summary>Evidence</summary>

```
$ ssh nas 'cat /proc/loadavg' -> 13.73 19.66 20.67 3/2451 ... [IO: 9.94,21.45,20.58 CPU: 1.04,1.64,1.19]
$ ssh nas 'top -b -n1|head' -> %Cpu(s): 8.4 us, 6.0 sy, 19.3 id, 66.3 wa ; GiB Mem: 19.387 total, 0.301 free, 12.610 buff/cache ; Swap: 6.074 used
$ ssh nas 'grep MemFree /proc/meminfo' -> MemFree: 261044 kB ; Dirty: 744 kB ; Writeback: 336 kB
$ ssh nas 'cat /proc/mdstat' -> md2/md3/md4 raid1 [1/1] [U]; md0/md1 [4/3] [UUU_] (no resync/recovery line)
$ sudo tail /var/log/messages -> 2026-08-20T19:13:04 synostgd-volume[12013]: volume_monitor.c:335 Detected volume low performance due to insufficient memory (volume_eb_miss=14267, volume=/volume1)
$ sudo tail /var/log/rclone-seedbox.log -> vfs cache: cleaned ... total size 44.795Gi (was 44.795Gi) ... [15:44-15:52 grew 35.9->44.8Gi 'in use 1'] ; 2026-08-23T16:00:05 INFO: watchdog already running — skipping this cycle
verify-audit-uc/results.json -> fix-55 'NAS 15-min I/O-load below threshold' FAIL: nas_io_load15=26.57 threshold=12 status=HIGH ; fix-55 'no SQLite database-is-locked storm' FAIL: arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]
progress.json -> fix-55 done=True '2026-08-02 ... resolved — NAS chronic I/O saturation + arr SQLite database is locked...'
```

</details>

### UM66. Zero new photo uploads in 7 days — ingestion side of photos-ml appears stalled (KNOWN fix-35) `known-issue`
**Host:** nas · **Component:** immich asset ingestion / mobile auto-backup (nas-immich-backup-freshness, fix-35) · **Auditor:** flow:photos-ml · **Work item:** `fix-86`

Corroborated fix-35 still holds and did not silently worsen. Library has 36,208 assets (34,866 photos + 1,342 videos) but /api/search/metadata with createdAfter=last-7-days returns total=0 — no asset has been UPLOADED in the past week. Combined with nas-immich-mobile-paired being disabled/skipped, this points at phone auto-backup not delivering new photos (or simply no new captures uploaded). This is the 'photos' consumer half of the chain being idle; it does NOT affect smart-search (which queries the existing embedded corpus and is proven working). NOT fixed per read-only mandate — reported only. Covered by open task fix-35.

<details><summary>Evidence</summary>

```
$ curl -sk POST https://immich.tabaska.us/api/search/metadata -d '{"createdAfter":"2026-08-16T20:52:19Z","size":1}'
assets created (uploaded) since 2026-08-16 = 0
$ /api/server/statistics → photos 34866 videos 1342 total 36208
baseline (mini, fix-35): nas-immich-backup-freshness = FAIL 'backup=STALE assets=36208 fresh_7d=0'; nas-immich-mobile-paired = skipped/disabled
```

</details>

### UM67. Phone photo backup zero-throughput: newest asset 9 days old, fresh_7d=0 (taxonomy 13) `known-issue`
**Host:** nas · **Component:** immich phone-photo-backup ingest · **Auditor:** svc:immich · **Work item:** `fix-86`

Immich's primary purpose (phone photo backup) shows no new assets in >9 days. server/statistics reports 36208 assets (34866 photos + 1342 videos, ~447GB) but /api/search/metadata order desc gives a newest fileCreatedAt of 2026-08-14T18:04:41Z (9 days before today 2026-08-23). The consumer check 'immich library has assets and a file landed in the last 7 days (phone backup flowing)' (task_id fix-35) fails with backup=STALE fresh_7d=0. fix-35 is marked done in the roadmap, so this is a reopen candidate. From a strictly read-only vantage I cannot distinguish a broken sync from mere user inactivity (no photos taken/synced) — and the corroborating 'immich has a mobile session paired' check is deliberately disabled (enabled:false), so there is a monitoring blind spot on whether a phone is even paired/active. NOT investigated further per read-only mandate. Covered by open task fix-35 (reopen candidate).

<details><summary>Evidence</summary>

```
$ curl -s -H "x-api-key: <immich.verify_api_key>" http://192.168.10.4:2283/api/server/statistics
{"photos":34866,"videos":1342,"usage":447863285556,...}

$ curl -s ... -X POST .../api/search/metadata -d '{"size":3,"order":"desc"}'
IMAGE fileCreatedAt=2026-08-14T18:04:41.000Z originalFileName=IMG_1902.WEBP  # newest

(audit run) 'phone backup flowing' [fix-35] => fail  backup=STALE assets=36208 fresh_7d=0
```

</details>

### UM68. REGRESSION/residual: ffmpeg SIGSEGV core dump recurs EVERY night (Aug 21/22/23 @ 00:00) on IMG_3674.mov, regenerating core.gz at /volume1 root `known-issue`
**Host:** nas · **Component:** immich thumbnail pipeline (jellyfin-ffmpeg) / core dumps (fix-60 + fix-45) · **Auditor:** svc:host-nas · **Work item:** `fix-87`

fix-60 (done 2026-08-03) and fix-45 core-dump checks both fire on the single file /volume1/@ffmpeg.synology_geminilake_920+.72806.<hash>.core.gz. /var/log/messages shows the SAME crash three consecutive nights in this window (2026-08-21, -22, -23 all at 00:00:xx): ffmpeg (/usr/lib/jellyfin-ffmpeg/ffmpeg, invoked by Immich for a preview thumbnail) dumps core on signal 11 processing /data/library/admin/2021/2021-06-28/IMG_3674.mov (fix-60's 'nightly ffmpeg segfault on one corrupt .mov'). Latest core.gz is dated Aug 23 00:00, 23,283,178 bytes — so the crash is still live and the /volume1-root core dump is regenerated nightly, keeping both fix-45 and fix-60 core-dump checks red (each output=1). Low IO impact but a persistent unresolved data-hygiene defect (corrupt source .mov never quarantined). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh nas 'ls -la /volume1/ | grep -iE core' -> -rw------- root root 23283178 Aug 23 00:00 @ffmpeg.synology_geminilake_920+.72806.45d2bac8...core.gz
$ sudo tail /var/log/messages -> 2026-08-{21,22,23}T00:00:1x coredump: Process ffmpeg[...](/usr/lib/jellyfin-ffmpeg/ffmpeg) dumped core on signal [11]. Cmdline [... -i /data/library/admin/2021/2021-06-28/IMG_3674.mov ... _preview.jpeg]
verify-audit-uc/results.json -> fix-45 'no core.gz crash dumps at /volume1 root' FAIL output=1 ; fix-60 'no Immich ffmpeg core dump at /volume1 root' FAIL output=1
```

</details>

### UM69. nas-core-dumps FAIL: recurring nightly immich_server ffmpeg SIGSEGV leaves core.gz at /volume1 root (fix-45/fix-60, still active) `known-issue`
**Host:** nas · **Component:** immich_server (bundled jellyfin-ffmpeg 7.1.4, AssetGenerateThumbnails transcode) · **Auditor:** triage:nas-core-dumps · **Work item:** `fix-87`

Known residual, re-verified STILL ACTIVE. nas-core-dumps (task fix-45, warn) expects zero core.gz at /volume1 root but found 1. The single dump is @ffmpeg.synology_geminilake_920+.72806.45d2bac8daed7bc273b669e02f6fe6988ec1d1ff64e7d8e9ba88598fd0ce0c2a.core.gz — root:root 0600, 23,283,178 bytes, mtime 2026-08-23 00:00:28.541 -0400. Binary = ffmpeg (PID 72806). The 64-hex token in the filename is the full Docker container ID and maps exactly to immich_server (ghcr.io/immich-app/immich-server:v3.0.3), which reports Up 11 days (healthy) — the container survives while its ffmpeg thumbnail child segfaults (green-but-broken liveness masking, taxonomy #2/#3). Immich log at 08/23/2026 12:00:28 AM: '(AssetGenerateThumbnails): Error: ffmpeg was killed with signal SIGSEGV' (jellyfin-ffmpeg 7.1.4, job 8a5d0a66-9ee4-47d3-a058-c80eea7d53ba) — matches the core mtime to the second. This is a nightly ~midnight AssetGenerateThumbnails job crashing ffmpeg on malformed media. The sibling sharper check nas-immich-ffmpeg-nocrash (task fix-60, SM1 class) also FAILs on this same core. Both checks were also failing in yesterday's daily state on mini (/var/lib/verification/results.json). The core is fresh tonight (generated after the 22:23 EDT audit run), so the crash-loop persists and the offending asset has NOT been quarantined. Fresh since the ~08-02 fix-45 sweep = immich_server ffmpeg. Count still 1 = not worsened vs the residual. NOT fixed per read-only mandate; fix path is fix-60 (quarantine the corrupt asset feeding the nightly thumbnail job) + fix-45 (sweep /volume1 core.gz).

<details><summary>Evidence</summary>

```
$ ssh nas 'ls --full-time /volume1/*.core.gz'
-rw------- 1 root root 23283178 2026-08-23 00:00:28.541873287 -0400 /volume1/@ffmpeg.synology_geminilake_920+.72806.45d2bac8daed7bc273b669e02f6fe6988ec1d1ff64e7d8e9ba88598fd0ce0c2a.core.gz

$ ssh nas 'ls /volume1/ | grep -c core\.gz'   # nas-core-dumps cmd, expect ^0$
1

# container-id attribution (sudo -S docker via vault sudo.nas_password)
$ ssh nas 'sudo -S /usr/local/bin/docker ps -a --no-trunc --format "{{.ID}} {{.Image}} {{.Names}} {{.Status}}"'
45d2bac8daed7bc273b669e02f6fe6988ec1d1ff64e7d8e9ba88598fd0ce0c2a ghcr.io/immich-app/immich-server:v3.0.3 immich_server Up 11 days (healthy)

# immich log — SIGSEGV timestamp matches core mtime
$ ssh nas 'sudo -S /usr/local/bin/docker logs immich_server --since 30h | grep -iE "ffmpeg|SIGSEGV"'
08/23/2026, 12:00:28 AM ERROR [Microservices:MediaRepository] ffmpeg version 7.1.4-Jellyfin ...
08/23/2026, 12:00:28 AM ERROR (AssetGenerateThumbnails): Error: ffmpeg was killed with signal SIGSEGV   (job 8a5d0a66-9ee4-47d3-a058-c80eea7d53ba)

# yesterday's daily state on mini — both checks already failing
$ ssh mini 'python3 -c ... /var/lib/verification/results.json'
nas-core-dumps fail '1'
nas-immich-ffmpeg-nocrash fail '1'
```

</details>

### UM70. fix-60 stuck-asset crash-loop: IMG_3674.mov segfaults Immich ffmpeg nightly, regenerating a /volume1 core dump `known-issue`
**Host:** nas · **Component:** immich_server / jellyfin-ffmpeg transcode (AssetGenerateThumbnails) · **Auditor:** triage:nas-immich-ffmpeg-nocrash · **Work item:** `fix-87`

Root-caused the fix-60 residual behind check nas-immich-ffmpeg-nocrash (baseline list, task_id fix-60, known_issue). The check `ls /volume1/ | grep -c '@ffmpeg.*core\.gz'` expects 0 but returns 1. The core file present is dated Aug 23 00:00 (fresh, not stale leftover): -rw------- root root 23283178 Aug 23 00:00 @ffmpeg.synology_geminilake_920+.72806.<hash>.core.gz. Immich server logs show jellyfin-ffmpeg 7.1.4 killed with signal SIGSEGV during job AssetGenerateThumbnails for asset id 8a5d0a66-9ee4-47d3-a058-c80eea7d53ba, at 08/23/2026 12:00:28 AM. This is a STUCK-ASSET crash-loop: the identical asset id crashed at ~00:00 every single night for 7 consecutive nights (Aug 17,18,19,20,21,22,23) — the nightly scheduled thumbnail-regen queue re-hits the same file and segfaults each time, writing a new core dump. Triage history (mini /var/lib/verification/triage-*.md) shows this check failing daily since at least Aug 06 (log retention only exposes 7d). The asset is IMG_3674.mov, a 4.13 MB iPhone video from 2021-06-29 at /data/library/admin/2021/2021-06-28/IMG_3674.mov; on disk it is mode 000 root:root (root still reads it, so the SIGSEGV is from malformed container content, not a permission error), and its asset_exif row is EMPTY (metadata extraction also failed on this file), consistent with a truncated/corrupt MOV that crashes the ffmpeg demuxer. RE-VERIFIED: steady state, NOT worsened (one crash/night, one core file — not accumulating, no disk-fill risk yet). User impact is bounded to this one asset (permanently missing thumbnail + exif in the timeline) plus a recurring 23 MB core dump. NOT fixed per read-only audit mandate. The nightly triage repeatedly proposes `rm -f /volume1/@ffmpeg*core.gz` (see triage-2026-08-06..14) but that only clears the symptom; the durable fix is to quarantine/re-transcode or drop IMG_3674.mov so the nightly job stops re-crashing. Note: the sibling check nas-immich-corrupt-mov-quarantined passed (quarantined=yes), so a corrupt-MOV quarantine mechanism exists but did NOT catch this asset — a gap worth folding into fix-60's remediation.

<details><summary>Evidence</summary>

```
$ ssh nas "ls -la /volume1/ | grep -i 'ffmpeg\|core'"
-rw-------   1 root root  23283178 Aug 23 00:00 @ffmpeg.synology_geminilake_920+.72806.45d2bac8...core.gz

$ printf '%s\n' "$PW" | ssh nas "sudo -S docker logs immich_server --since 30h 2>&1 | grep -iE 'ffmpeg|SIGSEGV'"
08/23/2026, 12:00:28 AM ERROR [Microservices:{"id":"8a5d0a66-9ee4-47d3-a058-c80eea7d53ba"}] Unable to run job handler (AssetGenerateThumbnails): Error: ffmpeg was killed with signal SIGSEGV
ffmpeg version 7.1.4-Jellyfin ...

# same asset every night, 7 consecutive nights:
$ ... docker logs immich_server --since 168h | grep -B1 'killed with signal SIGSEGV'
08/17/2026 12:00:18 AM -> id 8a5d0a66-...-c80eea7d53ba (AssetGenerateThumbnails)
08/18/2026 12:00:22 AM -> id 8a5d0a66-...-c80eea7d53ba
08/19/2026 12:00:25 AM -> id 8a5d0a66-...-c80eea7d53ba
08/20/2026 12:00:19 AM -> id 8a5d0a66-...-c80eea7d53ba
08/21/2026 12:00:26 AM -> id 8a5d0a66-...-c80eea7d53ba
08/22/2026 12:00:22 AM -> id 8a5d0a66-...-c80eea7d53ba
08/23/2026 12:00:28 AM -> id 8a5d0a66-...-c80eea7d53ba

$ ... docker exec immich_postgres psql -U postgres -d immich -tAc "SELECT type,originalFileName,fileCreatedAt,originalPath FROM asset WHERE id='8a5d0a66-9ee4-47d3-a058-c80eea7d53ba'"
VIDEO|IMG_3674.MOV|2021-06-29 02:24:42+00|/data/library/admin/2021/2021-06-28/IMG_3674.mov

$ ... psql -tAc "SELECT videoCodec,audioCodec,width,height,fileSizeInByte FROM asset_exif WHERE assetId='8a5d0a66-...'"
(0 rows -- exif/metadata never extracted)

$ ... docker exec immich_server ls -la '/data/library/admin/2021/2021-06-28/IMG_3674.mov'
---------- 1 root root 4130161 Jul  6  2021 /data/library/admin/2021/2021-06-28/IMG_3674.mov

# history: failing daily since Aug 06
$ ssh mini "grep -l 'ffmpeg-nocrash' /var/lib/verification/triage-*.md"
triage-2026-08-06.md ... triage-2026-08-23.md (every day)
```

</details>

### UM71. Immich ffmpeg SIGSEGV core-dump crash-loop still recurring nightly despite green quarantine check (green-but-broken, taxonomy 2/7) `known-issue`
**Host:** nas · **Component:** immich_server nightly thumbnail/transcode job · **Auditor:** svc:immich · **Work item:** `fix-87`

The nightly AssetGenerateThumbnails job SIGSEGVs jellyfin-ffmpeg on asset 8a5d0a66 EVERY midnight (observed 08/21, 08/22, AND 08/23 00:00 EDT), dumping a fresh 23MB @ffmpeg...core.gz to the /volume1 root (file dated 2026-08-23T00:00). The dedicated nas-immich-corrupt-mov-quarantined check (fix-60) reports quarantined=yes because a preview asset_file row exists, yet the SIGSEGV + core dump still fire on the same asset — the quarantine does NOT actually stop the crash. Three additional corrupt assets also fail thumbnail gen nightly: 40a901a5 (/data/library/admin/2019/2019-12-23/IMG_0628.heic bad seek to 11911017), eebd5867 (PersonGenerateThumbnail extract_area width not set), f6a8735f (HEIF corrupt header, ipma box 258 items > 256 limit). 286 error lines since 2026-08-02, concentrated at midnight (bounded, not a >1000 retry storm). Consumer impact is low (individual corrupt assets lack thumbnails; core files slowly accrue at /volume1 root) but the residual is unresolved and the green quarantine check masks it. NOT fixed per read-only mandate. Covered by open task fix-60.

<details><summary>Evidence</summary>

```
$ printf '%s\n' "$PW" | ssh nas "sudo -S sh -c 'ls -la --time-style=+%Y-%m-%dT%H:%M /volume1/ | grep ffmpeg'"
-rw------- 1 root root 23283178 2026-08-23T00:00 @ffmpeg.synology_geminilake_920+.72806.45d2bac8...core.gz

$ ssh nas "sudo -S sh -c '/usr/local/bin/docker logs immich_server --since 2026-08-02T00:00:00 2>&1 | grep -icE \"error|fatal|exception|SIGSEGV\"'"
286

(tail sample)
08/23/2026, 12:00:28 AM ERROR [Microservices:{"id":"8a5d0a66-..."}] Unable to run job handler (AssetGenerateThumbnails): Error: ffmpeg was killed with signal SIGSEGV
08/23/2026, 12:00:13 AM ERROR [...40a901a5...] .../IMG_0628.heic: bad seek to 11911017
08/23/2026, 12:00:23 AM ERROR [...f6a8735f...] heif: Security limit exceeded: ipma box wants 258 items, limit 256

(audit run) nas-immich-corrupt-mov-quarantined => pass quarantined=yes  # green yet crash recurs
```

</details>

### UM72. SQLite 'database is locked' storm hit lidarr under NAS heavy-IO load (transient, cleared) `known-issue`
**Host:** nas · **Component:** lidarr · **Auditor:** svc:lidarr · **Work item:** `fix-91`

The audit-safe run at 22:23 flagged arr-sqlite-not-locked=STORM [lidarr=10 radarr=4 whisparr=6] (max tolerated=5) — 10 'database is locked' events on lidarr in a 15-min window (taxonomy 1/7, DB lock contention under IO load; check task fix-55). Re-verified live at 16:18-16:21 EDT: the storm has cleared (0 'database is locked' in last 30m, 0 errors in last 2h), BUT sporadic contention persists — my first /api/v1/artist call timed out at 20s, an immediate retry returned in 0.1s. Correlates with the standing 'NAS under heavy IO load' condition (same class as baseline fix-23 nas-secret-file-perms 60s-timeout). Not consumer-breaking now (API responsive, no data loss, write path healthy), but degrades lidarr/soularr/musicseerr API reliability during IO spikes. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
results.json@22:23: arr-sqlite-not-locked=fail => arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]
LIVE re-check 16:18: docker logs lidarr --since 30m | grep -ic 'database is locked' => 0 ; --since 2h errors => 0
API probe: /api/v1/artist first attempt => TimeoutError timed out (20s); retry => took=0.1s (38 artists)
```

</details>

### UM73. Re-verified known failure: one unread ffmpeg core.gz crash dump at /volume1 root (fix-45; correlates fix-60 ffmpeg-nocrash) `known-issue`
**Host:** nas · **Component:** nas-core-dumps · **Auditor:** meta:nas-host · **Work item:** `fix-87`

known_issue: fix-45 (nas-core-dumps in this morning's failing baseline). Live re-run confirms 1 dump still present: @ffmpeg.synology_geminilake_920+.72806.<hash>.core.gz — a Synology-platform ffmpeg crash, which correlates with fix-60's nas-immich-ffmpeg-nocrash also failing in the same morning run (likely the same crash event surfacing in both checks). Per the check's own comment discipline, the dump's name/date is an unread crash signal that must be read before deletion. The check is working exactly as designed (direct artifact evidence, correct warn severity). NOT fixed / NOT deleted per read-only mandate.

<details><summary>Evidence</summary>

```
ssh nas 'ls /volume1/ | grep core\.gz' -> @ffmpeg.synology_geminilake_920+.72806.45d2bac8daed7bc273b669e02f6fe6988ec1d1ff64e7d8e9ba88598fd0ce0c2a.core.gz
count=1
```

</details>

### UM74. nas-flaresolverr is liveness masquerading as a service probe, and is the ONLY flaresolverr coverage fleet-wide
**Host:** nas · **Component:** nas-flaresolverr check · **Auditor:** meta:nas-services · **Work item:** `fix-100`

The check curls GET /health (returns {"status": "ok"}) — FlareSolverr's health endpoint answers without spawning a browser or solving anything. Yet the in-file comment explicitly claims it guards the consumer class: 'an up but broken flaresolverr silently zeroes Prowlarr indexer results' and says 'These probe the actual service, not just container presence.' /health cannot catch a solver whose headless browser is wedged/crash-looping while the HTTP frontend stays up — exactly the documented failure class. grep across all of checks.d shows no other check touches :8191 or flaresolverr, so solver-broken-but-healthy is fully dark. Standing mandate 1 (liveness masquerading as consumer probe). Remediation shape: a daily-tier POST /v1 {"cmd":"request.get"} solve canary against a stable target (a real solve is too heavy for the fast tier — keep /health as the gate, add the solve as the consumer probe). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh nas 'curl -sm 8 http://localhost:8191/health'
{"status": "ok"}
$ grep -rn '8191\|flaresolverr' foss-setup/verification/checks.d/ | grep -v nas-services.yaml
(no output — nas-services.yaml /health is the only coverage)
check cmd: curl -sm 8 http://localhost:8191/health ; expect: '"ok"'
```

</details>

### UM75. RE-VERIFIED known fail fix-60: Immich ffmpeg core dump present AND fresh — crash loop recurred last midnight `known-issue`
**Host:** nas · **Component:** nas-immich-ffmpeg-nocrash (live state) · **Auditor:** meta:nas-services · **Work item:** `fix-87`

Known issue fix-60 (on today's 10:29 EDT fail baseline). Re-verified per lane contract: 1 core.gz at /volume1 root, timestamped 2026-08-22 00:00 — i.e. the nightly transcode/preview crash recurred LAST NIGHT, this is not a stale corpse awaiting cleanup. Nuance: the sibling check nas-immich-corrupt-mov-quarantined (asserts asset 8a5d0a66/IMG_3674.MOV keeps its placeholder preview row) was NOT on this morning's fail list, so the original quarantine appears intact — the fresh core points at a SECOND corrupt asset entering the nightly QUEUE_GENERATE_THUMBNAILS re-queue, which is precisely the recurrence class the check was designed to catch. The check itself is well-designed (consumer-outcome class, stdout-only via grep -c, || true guards the no-match exit). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh nas 'ls /volume1/ | grep -c "@ffmpeg.*core\.gz"; ls -la /volume1/ | grep "@ffmpeg" | head -1'
1
-rw------- 1 root root 23292174 Aug 22 00:00 @ffmpeg.synology_geminilake_920+.72806.45d2bac8daed...core.gz
```

</details>

### UM76. NAS IO storm (load15=26.57) was the routine weekly Saturday-night Hyper Backup window; self-cleared, not a fix-55 regression `known-issue`
**Host:** nas · **Component:** nas-io-pressure (fix-55) / DSM Hyper Backup · **Auditor:** triage:nas-io-pressure · **Work item:** `fix-91`

The audit-safe run at 2026-08-22T22:23:20-04:00 read nas_io_load15=26.57 (threshold 12, status=HIGH). Root cause: the sample landed inside the routine weekly Saturday-evening Hyper Backup window. DSM task scheduler defines two 'S3 Backup enc' jobs against the same encrypted-S3 target (Hyper Backup task 3): 11.task = daily 19:10 '/var/packages/HyperBackup/target/bin/dsmbackup --backup 3', and 12.task = WEEKLY Saturday (week=0000001) 21:10 '/var/packages/HyperBackup/target/bin/detect_monitor -t -k 3 -f -T -1' (a full-read backup integrity verification that runs >1h). The Hyper Backup S3 client-cache dir mtime is 'Aug 22 22:24' — the backup was actively writing at the sampled minute. Layered on the always-on bitmagnet DHT-crawler baseline (~3.0), the backup pushed the 15-min IO load to 26.57. This is a TRANSIENT backup-window peak, NOT a regression of the fix-55 root cause: the chronic baseline is now ~3.0 (morning daily run 10:29 EDT read 3.06 OK; live now 0.91-1.32), dramatically better than the pre-fix chronic 17-22, so the bitmagnet workload-reduction (DHT_CRAWLER_SCALING_FACTOR 10->3) still holds. The 26.57 exceeding the documented 17-22 storm range is NOT 'worsened residual' — the old figure was chronic all-day saturation; this is a distinct weekly-backup transient the pre-fix monitoring never measured. Ruled out: no btrfs scrub ran (last volume1 scrub Sep 26 2025); no runaway userspace D-state process (only md0_raid1, a normal kernel RAID thread). known_issue=true, task_id fix-55; check is severity:warn by design. NOT fixed / nothing killed per read-only mandate. Note the monitoring blind-spot: the normal daily verification runs at 10:29 EDT (calm) and never samples the Sat-night backup window, so this IO peak is invisible to daily monitoring and only surfaced because the audit-safe run sampled Saturday 22:23.

<details><summary>Evidence</summary>

```
$ cat results.json -> id=nas-io-pressure status=fail output='nas_io_load15=26.57 threshold=12 status=HIGH' (timestamp 2026-08-22T22:23:20-04:00)

$ ssh nas 'uptime' (2026-08-23 15:20:42 EDT)
 15:20:42 up 51 days, load average: 0.90, 0.99, 1.21 [IO: 0.72, 0.73, 0.91 CPU: 0.18, 0.25, 0.26]

$ ssh mini python3 -c 'json results.json (daily 10:29 run)'
 run ts: 2026-08-23T10:29:25-04:00
 nas-io-pressure :: pass :: nas_io_load15=3.06 threshold=12 status=OK

$ ssh nas sudo cat 12.task (base64 cmdArgv decoded)
 type=weekly  week=0000001  run hour=21 run min=10  name=S3 Backup enc
 cmdArgv -> /var/packages/HyperBackup/target/bin/detect_monitor -t -k 3 -f -T -1
$ ssh nas sudo cat 11.task (decoded)
 type=daily  run hour=19 run min=10  name=S3 Backup enc
 cmdArgv -> /var/packages/HyperBackup/target/bin/dsmbackup --backup 3

$ ssh nas sudo 'ls -lat /volume1/@img_bkp_cache/'
 drwxrwxrwx 1 root root 76 Aug 22 22:24 ClientCache_cloud_image_aws_s3.L35Ey1

$ ssh nas sudo 'btrfs scrub status /volume1'
 scrub started at Fri Sep 26 20:02:53 2025 and finished after 03:19:38 (0 errors)  # no scrub Sat night
$ ssh nas sudo 'ps axo pid,stat,comm | grep " D"'
 5101 D md0_raid1  # kernel RAID thread only, normal
```

</details>

### UM77. crit find over /volume1/docker has no timeout/ionice guard — false-CRITs under NAS IO load `known-issue`
**Host:** nas · **Component:** nas-secret-file-perms (+ sibling nas-worldwritable-sweep) · **Auditor:** meta:secrets · **Work item:** `fix-92`

nas-secret-file-perms (crit) walks the entire /volume1/docker tree with a bare `find | wc -l` and no `timeout`/`ionice` in the cmd. Under NAS IO load it exceeds the runner's per-check budget and flaps to CRIT — this is exactly today's 10:29 EDT baseline failure (fix-23, noted 60s timeout correlating with NAS IO). The find LOGIC is sound (prunes @eaDir/#recycle, -perm /0044 for group/world read, strict expect ^0$), so the failure is check-fragility, not a real perms regression — but a crit that flaps on load creates crit-channel noise and can mask a genuine world-readable-cred regression. Sibling nas-worldwritable-sweep (warn) has the identical unbounded-find design over /volume1/docker+/volume1/scripts and is one IO spike from the same false-fail (it passed this morning only by luck of timing). NOT re-run live per read-only mandate (hard rule: no finds over /volume1 under current IO load). Recommend wrapping the finds in `timeout 90 ionice -c3` or scoping to config-dir depth so a slow tree yields a distinguishable timeout state rather than a crit. known_issue=true (fix-23 reopen candidate).

<details><summary>Evidence</summary>

```
cmd (L30): sh -c 'find /volume1/docker \( -name @eaDir -o -name "#recycle" \) -prune -o -type f \( -name "*.env" ... \) -perm /0044 -print 2>/dev/null | wc -l'  (no timeout/ionice)
Lane baseline: 'fix-23 (nas-secret-file-perms CRIT — 60s timeout, correlates with NAS IO load)'
Sibling L43: same pattern over /volume1/docker /volume1/scripts, expect ^0$, also unbounded
```

</details>

### UM78. Coverage gap: world-readable (0644) secret files escape the check's name filter — bazarr config.yaml, unpackerr.conf
**Host:** nas · **Component:** nas-secret-file-perms name filter (coverage gap) + world-readable secret files · **Auditor:** triage:nas-secret-file-perms · **Work item:** `fix-92`

The check only matches *.env/.env/config.ini/config.xml, so secret-bearing files in other formats slip through. Two real ones are world-readable (0644): /volume1/docker/bazarr/config/config/config.yaml (bazarr config.yaml holds provider creds / arr API keys) and /volume1/docker/media-automation/unpackerr/unpackerr.conf (unpackerr.conf embeds arr API keys). The unpackerr one is low-impact — unpackerr is retired (fix-69 unpackerr-host-retired), leftover dir. The bazarr config.yaml at 0644 is a genuine (if minor) hygiene gap: on a multi-service NAS any account/container with read+traverse can read those keys. Neither is a regression of MY crit check (both are outside its name filter), but both indicate the fix-23 check under-covers its own stated intent ('no group/world-readable secret files'). NOT repaired (read-only). Recommend broadening the name filter to include *.yaml/*.yml/*.conf/*.toml secret configs, or confirming these are acceptable. known_issue:false (not tracked; the unpackerr file is adjacent to fix-69).

<details><summary>Evidence</summary>

```
$ ssh nas 'stat -c "%a %U:%G %n" /volume1/docker/bazarr/config/config/config.yaml /volume1/docker/media-automation/unpackerr/unpackerr.conf'
644 btabaska:users /volume1/docker/bazarr/config/config/config.yaml
644 btabaska:users /volume1/docker/media-automation/unpackerr/unpackerr.conf

check name filter (secrets.yaml:30): -name '*.env' -o -name '.env' -o -name 'config.ini' -o -name 'config.xml'  (no *.yaml/*.conf)
```

</details>

### UM79. Re-verified known failure: 2 soularr failed imports parked >3 days while the 5-min cycle runs healthy (fix-40 reopen) `known-issue`
**Host:** nas · **Component:** nas-soularr-failed-imports-fresh · **Auditor:** meta:nas-host · **Work item:** `fix-95`

known_issue: fix-40 (listed in this morning's 10:29 EDT failing baseline as nas-soularr-failed-imports-fresh). Live re-run of the check's exact logic confirms it still holds this evening: stale=2 parked entries in failed_imports.json older than 3 days (titles include 'JJK'/'Masters of Slang'), while cycling=yes with soularr.log written 10.4 min ago — so the loop is alive and re-grinding the same parked failures, the precise M6/M24 silent-park pattern this check exists to catch. The check itself is healthy and consumer-grade; this is the guarded condition firing, not check rot. Not silently worsened in kind since the morning run. NOT fixed per read-only mandate — resolution is the fix-40 runbook path (triage the parked entries, clear or route them).

<details><summary>Evidence</summary>

```
ssh nas python3 (check's exact logic + log age) -> stale=2:cycling=yes log_age_min=10.4 JJK Masters of Slang
```

</details>

### UM80. IPTorrents imdbid ID-search through Prowlarr returns ZERO items (backlog ID-search path degraded)
**Host:** nas · **Component:** prowlarr -> IPTorrents (check iptorrents-idsearch-returns-results) · **Auditor:** svc:prowlarr · **Work item:** `fix-100`

The dedicated 2026-08-11-backlog-incident regression check is FAILing: an imdbid movie search scoped to IPTorrents (t=movie&imdbid=tt0133093) returns 0 items where it must return >0. Root cause is rate-limit/budget class, NOT auth or a dead indexer: IPT grabs are succeeding (168 grabs, numberOfFailedQueries=0), so cookie/auth is intact and caps list imdbid. Most likely IPT's 600-queries/24h budget is exhausted (over-budget searches silently return 0) — consistent with the concurrent fix-50 grab-storm hammering IPT. Per lane notes rate-limit-class indexer flap is deliberately not filed as availability flap, BUT the ID-search *consumer path* (arr backlog ID-searches routed to IPT) is currently returning nothing, so filing as a real caveat. NOT fixed per read-only mandate. Note: this check's task_id is set to verify-06, which the reopen-bridge maps to the unrelated rig-containers-manifest task — a mislabel that will misattribute this failure.

<details><summary>Evidence</summary>

```
results.json: 'prowlarr->IPT: imdbid search returns results' STATUS=fail OUT='ipt_idsearch_items=0' task=verify-06
check cmd: curl 'http://localhost:9696/1/api?t=movie&imdbid=tt0133093&apikey=***' | grep -c '<item>' -> 0
corroboration: /api/v1/indexerstats IPTorrents q=1148 grabs=168 fails=0 (auth OK, budget-suspect)
```

</details>

### UM81. Live radarr API key committed in plaintext in git-tracked unpackerr.conf
**Host:** nas · **Component:** radarr · **Auditor:** svc:radarr · **Work item:** `sec-10`

The radarr API key hard-coded in the repo file foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf (line 56, git-tracked, dual-remoted to GitHub + Forgejo) is NOT stale — its sha256 is byte-identical to the LIVE key in /volume1/docker/radarr/config/config.xml. That key grants full radarr API access (add/delete movies, trigger downloads/imports). unpackerr's host unit is slated for retirement (fix-69, unpackerr-host-retired) but the NAS unpackerr CONTAINER is the real consumer, so the conf is live config, not dead scaffolding. Recommend rotating the radarr API key and moving it to the gitignored .env (the stack's .env.example already parameterizes seedbox creds), then re-seeding unpackerr. Sibling arr keys (sonarr/lidarr) in the same file are almost certainly exposed the same way (cross-lane note). NOT fixed per read-only mandate. Value never pasted here — evidence is sha256 match only.

<details><summary>Evidence</summary>

```
git ls-files foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf -> (tracked)
repo:  sed -n '54,57p' unpackerr.conf | grep -oE '[a-f0-9]{32}' | shasum -a256 -> c9bb43bf33cc664aa6f91f72756948f8423c79b529e05b81ad14b7ddfe07a813
live:  ssh nas 'sudo grep -oE "<ApiKey>[a-f0-9]+</ApiKey>" /volume1/docker/radarr/config/config.xml | grep -oE "[a-f0-9]{32}" | sha256sum' -> c9bb43bf33cc664aa6f91f72756948f8423c79b529e05b81ad14b7ddfe07a813 (IDENTICAL => live key is committed)
```

</details>

### UM82. SQLite 'database is locked' storm hits radarr under current heavy NAS IO load (self-recovering)
**Host:** nas · **Component:** radarr · **Auditor:** svc:radarr · **Work item:** `fix-91`

The shared nas-io-storm check arr-sqlite-not-locked FAILED in the audit run with radarr contributing 4 of 20 locks in a 15-min window (STORM > max 5 combined). radarr's own log corroborates: 56 'database is locked' (SQLite Busy 0x87AF00AA) lines in today's radarr.txt, plus an error cluster during the overnight scan (00:23-00:27 ExistingExtraFileService failed on MovieScannedEvent; 00:26:50 RefreshMovieService couldn't rescan 'Heathers (1989)') and a failed 06:15:32 RadarrErrorPipeline [GET /api/v3/movie]. This correlates with the documented current heavy NAS IO load (and fix-23's IO-load correlation). It is transient/self-recovering — radarr still imported at 19:40/19:53 today and health is clean — but it produces real functional hiccups (dropped rescans, 5xx on movie API). Not in this morning's 10:29 baseline, so it is an intermittent trip worth watching, not a codified known-fail. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
mini /tmp/verify-audit-uc/results.json: arr-sqlite-not-locked=fail 'arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]'
ssh nas 'sudo grep -c "database is locked" /volume1/docker/radarr/config/logs/radarr.txt' -> 56
sample: '[v6.3.0.10514] code = Busy (5) ... System.Data.SQLite.SQLiteException (0x87AF00AA): database is locked'
errors: 2026-08-23 00:23-00:27 |Error|EventAggregator ExistingExtraFileService failed [MovieScannedEvent]; 00:26:50 |Error|RefreshMovieService Couldn't rescan movie [Heathers (1989)]; 06:15:32 |Error|RadarrErrorPipeline [GET /api/v3/movie]
```

</details>

### UM83. New-book metadata lookup slow/flaky — Hardcover upstream 429 rate-limiting (consumer impact corroborated) `known-issue`
**Host:** nas · **Component:** rreading-glasses-hc (Bookshelf metadata provider) · **Auditor:** flow:books-kobo · **Work item:** `fix-89`

KNOWN issue bmig-06 (metadata-search-canary FAIL in baseline) re-verified and STILL HOLDS, with root cause corroborated live. The add-new-book consumer path (Bookshelf /api/v1/book/lookup, which fans out to rreading-glasses-hc -> Hardcover) is degraded: three fresh samples ran 12.9s / 26.9s / 40.9s, straddling the canary's 45s urllib timeout (baseline run at 22:23 hit TimeoutError => FAIL). When it does return, ranking is correct (Pride & Prejudice/Austen at rank 3-6 of 14). Root cause is NOT the token (hardcover-token-valid=OK, 332 days left, user RobitFarmer) but upstream rate-limiting: rreading-glasses-hc logs show repeated 'batched query error ... returned error 429' bursts within the last hour (2026-08-23T20:26-20:27Z, cross-checked current). Matches memory note hardcover-rg-hc: 60/min quota + refresh-herd 403/429s. Consumer verdict for this hop: AMBER — adding a new book works but is slow and intermittently times out. NOT fixed per read-only mandate. Cite task bmig-06.

<details><summary>Evidence</summary>

```
$ curl -H X-Api-Key(BOOKSHELF) 'http://192.168.10.4:8790/api/v1/book/lookup?term=Pride and Prejudice Jane Austen' (from mini, key never printed)
sample: http_code=200 time_total=26.905961s size=19546
sample1 http_code=200 time_total=12.858596s results=14 austen_exact_rank=6
sample2 http_code=200 time_total=40.899337s results=14 austen_exact_rank=3
results.json baseline: metadata-search-canary => TimeoutError: timed [out] (urllib timeout=45)
---
$ docker logs rreading-glasses-hc --since 2h | grep 429
{"time":"2026-08-23T20:26:35Z","level":"warn","msg":"batched query error","count":5,"err":"returned error 429: {\"data\":null}"}
... (repeats 20:26:35 through 20:27:46Z)
---
results.json: hardcover-token-valid=HC_TOKEN_OK days_left=332 user=RobitFarmer
```

</details>

### UM84. metadata-search-canary urllib TimeoutError = slow metadata lookup (25-56s) straddling 45s timeout, NOT check-bug or endpoint-down `known-issue`
**Host:** nas · **Component:** rreading-glasses-hc (rg-hc, NAS :8789) → Bookshelf book/lookup (NAS :8790); check runs from mini · **Auditor:** triage:metadata-search-canary · **Work item:** `fix-89`

Tonight's audit-safe run (results.json timestamp 2026-08-22T22:23:20-04:00) shows metadata-search-canary (task bmig-06, checks.d/reading.yaml) FAILED exit 1 duration 45.16s with a Python urllib traceback ending 'TimeoutError: timed out'. The traceback bottoms out in getresponse()/_read_status()/recv_into — i.e. the TCP connection was ESTABLISHED and the HTTP response simply never arrived within the check's timeout=45. This is not a bug in the check code and not the endpoint being down. I proved the endpoint is up and correct: NAS :8790/ping returns 200 in 0.44s, /api/v1/system/status returns 401 in 0.02s, and the actual canary lookup (term 'Pride and Prejudice Jane Austen') returns http=200 with 14 results, canonical 'Pride and Prejudice' by Austen present at rank 7 — the canary's own logic would print CANARY_OK rank=7 results=14 if the request had completed in time. The problem is latency: cold lookup total=55.7s, warm/second lookup total=25.2s (measured 2026-08-23 ~15:2x EDT). The 45s check timeout sits between the warm (~25s) and cold (~56s) latency, so cold hits (the nightly run) trip it while warm daytime runs pass — this matches the history exactly: same 'Bookshelf API ... timing out' diagnosis on 08-07/09/10/12 morning triage, absent 08-13..08-23 mornings, and PASSED in both the 08-22 and 08-23 10:32 daily runs (not in triage). Root cause is the documented rg-hc quota-storm: the rreading-glasses-hc controller runs background Hardcover author-refresh bursts that serialize sequential upstream fetches against Hardcover's ~60 req/min quota, batch-starving concurrent book/lookup searches (runbook foss-setup/wiki/docs/runbooks/books-metadata.md: 'background author refreshes batch-starve searches ... Wait for refreshes to go quiet and re-run'). This is a KNOWN residual tracked by OPEN task books-hc-upstream-swap (swap rg-hc off the temporary local image once upstream fixes the Hardcover batch limit, #574); the canary itself was shipped by bmig-06 (DONE 2026-07-20) and is working as designed — it caught real latency. NOT fixed per read-only mandate. Operator note (report-only): the 45s check timeout is marginal against a lookup path that legitimately runs 25-56s; either speeding up rg-hc (upstream swap / batch fix) or widening the check timeout would stop the intermittent false-crash. The other three bmig-06 checks (hardcover-token-valid, request-author-parity, shelfmark-mam-path-ready) all PASSED tonight.

<details><summary>Evidence</summary>

```
# tonight's failing record (results.json)
$ python3 -c '...load results.json, find metadata-search-canary...'
status=fail exit_code=1 duration_s=45.16
output: Traceback ... File "/usr/lib/python3.10/http/client.py", line 284, in _read_status\n  line = str(self.fp.readline(_MAXLINE + 1), "iso-8859-1")\n  ... socket.py line 705 recv_into\nTimeoutError: timed out

# endpoint is UP (from mini)
$ ssh mini 'curl -s -o /dev/null -w "connect=%{time_connect}s total=%{time_total}s http=%{http_code}\n" --connect-timeout 5 --max-time 15 http://192.168.10.4:8790/ping'
connect=0.000246s total=0.437277s http=200
$ ssh mini 'curl ... http://192.168.10.4:8790/api/v1/system/status'
connect=0.000266s total=0.022711s http=401

# live lookup: SLOW but correct (key read from /etc/verification/env into shell var, only key_len printed)
$ ssh mini 'K=$(grep -m1 ^BOOKSHELF_API_KEY= /etc/verification/env | cut -d= -f2-); curl -s -o /tmp/bs_lookup.json -w "total=%{time_total}s http=%{http_code} size=%{size_download}\n" --max-time 60 -H "X-Api-Key: $K" "http://192.168.10.4:8790/api/v1/book/lookup?term=Pride%20and%20Prejudice%20Jane%20Austen"'
key_len=32
total=55.728738s http=200 size=19546
# second (warm) run
total=25.216360s http=200 size=19546
# canary logic on captured result
results=14 ; canary rank= 7
0 Pemberley: Mr. Darcy's Dragon | grace, maria
1 Pride & Prejudice | butler, nancy
...

# rg-hc quota-storm mechanism (NAS logs, UTC)
$ printf '%s\n' "$PW" | ssh nas 'sudo -S docker logs rreading-glasses-hc --since 30m | grep -iE refresh|queue'
{"time":"2026-08-23T19:27:05Z","msg":"fetching all works for author","authorID":431511}
{"time":"2026-08-23T19:27:08Z","msg":"getting work",...}
{"time":"2026-08-23T19:27:22Z","msg":"fetched all works for author","authorID":431511,"count":13,"duration":"17.543147917s"}
{..."refreshWaiting":1,"denormWaiting":14...}

# history: same timeout diagnosis on prior days
$ ssh mini 'grep -A6 "### metadata-search-canary" /var/lib/verification/triage-2026-08-07.md'
"diagnosis": "Bookshelf API at 192.168.10.4:8790 is unreachable and timing out."
# present in triage 08-07/09/10/12 only; NOT in 08-13..08-23 mornings

# tracked by OPEN task
$ python3 (tasks.json + progress.json) => books-hc-upstream-swap | done=False | 'Swap rreading-glasses-hc off the temporary local image once upstream fixes Hardcover batch limit (#574)'
# bmig-06 => done True (2026-07-20); this canary is one of its 3 shipped tripwires
```

</details>

### UM85. metadata-search-canary consumer probe reproducibly times out >50s on prolific-author (Pride & Prejudice / Austen) lookup
**Host:** nas · **Component:** rreading-glasses-hc / Bookshelf metadata lookup (bmig-06) · **Auditor:** svc:rreading-glasses · **Work item:** `fix-89`

The consumer-faithful books-metadata canary (Bookshelf /api/v1/book/lookup for 'Pride and Prejudice Jane Austen', 45s client timeout) FAILED in the 08-22 22:23 audit run with a socket TimeoutError, and I reproduced it live at 16:24 EDT on 08-23 (still timing out at 50.1s). Isolation proves rreading-glasses-hc is NOT the hard fault: direct hc probes return the P&P records fast (/work/2459845 200 in 0.0016s/290KB, /author/132049 200 in 0.0096s/2.6MB, /book/17456445 303 in 0.001s, /search 200 in 4.3s returning the correct bookId 17456445). Root cause is Bookshelf's lookup fan-out hydrating a maximally-prolific author (Austen, 2.6MB author record with hundreds of works) combined with Hardcover's account-wide 60/min quota: cold /author refreshes get 429-throttled and take multiple seconds each (a Bookshelf /author/238290 fetch took 14.617s HTTP200 at 08-23 02:20), and enough of these accumulate to blow the 45-50s client timeout. Impact: book metadata SEARCH for prolific authors times out in the Bookshelf/Shelfmark frontend; cached and less-prolific lookups are fine. NOT in today's pre-existing failure baseline (bmig-06 unlisted) and no open task covers it, so this is a newly-surfaced/worsened consumer degradation. NOT fixed per read-only mandate — reported only. Likely belongs to the Bookshelf lane; filed here because it is the metadata-stack's consumer canary.

<details><summary>Evidence</summary>

```
mini /tmp/verify-audit-uc/results.json -> metadata-search-canary status=fail output=TimeoutError('timed out') at File \"<string>\", line 6 (urlopen)
live repro (mini, key sourced from /etc/verification/env, not printed): CANARY_ERR time=50.1s TimeoutError('timed out')
isolation (ssh nas, direct hc :8789): /author/431511 http=200 time=0.001980s size=28498 | /search?query=Pride%20and%20Prejudice... http=200 time=4.308168s -> [{\"bookId\":17456445,\"workId\":2459845,\"author\":{\"id\":132049}}] | /work/2459845 http=200 time=0.001652s size=290580 | /author/132049 http=200 time=0.009633s size=2642707 | /book/17456445 http=303 time=0.001197s
slow served requests (hc access log, ip 172.19.0.8=bookshelf): 2026-08-23T02:20:28Z /author/238290 14.617405897s HTTP 200 ; 2026-08-23T19:27:05Z /author/431511 4.563705874s HTTP 200 ; 2026-08-22T18:54:55Z /author/132049 1.729478875s HTTP 200
```

</details>

### UM86. Recurring bundled-InfluxDB write/query timeouts under NAS IO load — degrades temp-history and has 500'd /api/summary
**Host:** nas · **Component:** scrutiny (bundled InfluxDB) · **Auditor:** svc:scrutiny-hub · **Work item:** `fix-91`

The omnibus's bundled InfluxDB intermittently times out under NAS IO contention, in two windows: (a) the 06:00Z daily SMART-collection burst — 'context deadline exceeded' on POST /api/v2/write, 'database is locked (5) (SQLITE_BUSY)', 'unexpected error writing points to database: timeout', and 'An error occurred while publishing SMART data for device (...): context deadline exceeded' returning 500 to the collectors; (b) the 01:00Z InfluxDB retention/compaction task-executor runs — 'Error exhausting result iterator error=timeout', 'Write failed engine: context canceled', 'Failed to finish run ... error=timeout'. On 2026-08-11 17:23Z and 2026-08-12 01:50Z/02:10Z this cascaded to GET /api/summary itself returning 500 (20-30s latency) — i.e. the consumer check WOULD have transiently failed those days. Recurs roughly daily/every-few-days (observed 08-11,12,15,16,17,18,22,23). Net data impact TODAY is nil — all 7 disks show fresh 06:00Z records and device_status=0 (the SQLite device-registry side lands even when the metrics/time-series write times out), so the health rollup is current; the loss is temp-history graph gaps plus the transient API 500 risk during a bad IO window. This is a green-but-degraded telemetry-write condition, NOT a retry storm (log volume 6118 lines / 21 days ~= 290/day of normal access logging). Correlates with the fleet-wide 'NAS under heavy IO load' state and the fix-23 60s-timeout cluster noted in the audit baseline, but is not itself tracked by an open task. NOT fixed — read-only audit mandate.

<details><summary>Evidence</summary>

```
$ docker logs scrutiny --since 2026-08-02 | grep -iE 'error|panic|fatal|fail' (trimmed):
2026-08-12T06:00:35Z level=error msg="An error occurred while updating device data from smartctl metrics: database is locked (5) (SQLITE_BUSY)"
2026-08-12T06:01:08Z level=error msg="An error occurred while registering devices [database is locked (5) (SQLITE_BUSY)]" ... POST /api/devices/register 500 (50983ms)
2026-08-12T06:01:54Z level=error msg="An error occurred while saving smartctl temp data Post http://localhost:8086/api/v2/write...: context deadline exceeded"
2026-08-11T17:23:03Z GET /api/summary 500 (20263ms); 2026-08-12T01:50:36Z GET /api/summary 500 (30026ms) [InfluxDB query context deadline exceeded]
2026-08-16T01:03:29Z lvl=error msg="Failed to finish run" service=task-executor error=timeout; 2026-08-23T01:03:50Z same
2026-08-23T06:01:05Z level=error msg="An error occurred while publishing SMART data for device (0x5000cca298c083de): Post http://localhost:8080/api/device/.../smart: context deadline exceeded"
$ docker logs scrutiny --since 2026-08-02 | wc -l -> 6118
$ recent tail: GET /api/summary 200 (but latency spikes 2590ms, 6444ms observed) — read path 200 now, occasionally slow
```

</details>

### UM87. shelfmark-mam-path-ready has decayed toward liveness: health-200 + mountinfo propagation flag, but the MAM→CWA-ingest consumer path it claims to guard is never exercised
**Host:** nas · **Component:** shelfmark (check shelfmark-mam-path-ready) · **Auditor:** meta:reading · **Work item:** `fix-100`

The check name promises 'MAM→CWA-ingest path intact' but the cmd only asserts (a) http://127.0.0.1:8084/api/health returns 200 — pure app liveness — and (b) /proc/self/mountinfo shows a shared:N propagation tag on the seedbox-files mount. Neither proves the path works: a dead rclone/FUSE mount (this fleet's documented NAS FUSE failure mode — 'FUSE remount = restart all /seedbox consumers') keeps its mountinfo entry AND its shared: peer-group tag while every read returns ENOTCONN, so the copy path can be fully broken while this check stays green (SHELFMARK_OK health=200 prop=shared:2 as of today's run). It guards the one regression it was written for (NAS reboot resetting rshared→private) but not the consumer end per standing mandate 1. Cheap deepening: stat/read one real file through /volume1/mounts/seedbox-files inside the check (or ls the download dir Shelfmark ingests from) so a broken-transport mount fails loudly. NOT fixed per read-only mandate. Passing today (verified live), so this is a probe-depth gap, not an outage.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/reading.yaml:623 → cmd: 'h=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 http://127.0.0.1:8084/api/health); p=$(grep seedbox-files /proc/self/mountinfo 2>/dev/null | grep -oE "shared:[0-9]+" | head -1); if [ "$h" = "200" ] && [ -n "$p" ]; then echo "SHELFMARK_OK …"'
Today's daily results.json: shelfmark-mam-path-ready pass 'SHELFMARK_OK health=200 prop=shared:2' — no file is ever read through the mount and no search/ingest is exercised.
```

</details>

### UM88. fix-45 residual re-confirmed: 10 monitored series still on the unmanaged 'Any' quality profile (qualityProfileId=1) `known-issue`
**Host:** nas · **Component:** sonarr · **Auditor:** svc:sonarr · **Work item:** `fix-94`

The sonarr-unmanaged-profile check (task_id fix-45, media-library-correctness.yaml) FAILED in today's audit-safe run, and live re-verification confirms it STILL holds and appears to have grown: 10 monitored series sit on the default 'Any' profile (id=1) rather than a managed profile — Teen Titans Go!, Animaniacs, Freakazoid!, The Grim Adventures of Billy & Mandy, Johnny Bravo, Kodocha, Cardcaptor Sakura, Hamtaro (+2 more). The morning check output showed 5 (its truncation cap); live count is 10, consistent with the ongoing cartoon/anime backfill (same series appear in the deluge/seerr rot below). These grab at unmanaged quality with no upgrade/cutoff control. NOT fixed per read-only mandate. Known fix-45 residual.

<details><summary>Evidence</summary>

```
live /api/v3/series:
UNMANAGED_PROFILE_ANY monitored_qp1=10 :: Teen Titans Go!, Animaniacs, Freakazoid!, The Grim Adventures of Billy & Mandy, Johnny Bravo, Kodocha, Cardcaptor Sakura, Hamtaro: Little Hamsters, Big Adventures

audit-run /tmp/verify-audit-uc/results.json:
ID: sonarr-unmanaged-profile | STATUS: fail
  OUT: PROFILE_BAD Teen Titans Go!,Animaniacs,Freakazoid!,The Grim Adventures of Billy & Mandy,Johnny Bravo
```

</details>

### UM89. fix-45 residual WORSENED: 10 monitored series on unmanaged 'Any' profile (up from 5), 5 new anime added 2026-08-10 `known-issue`
**Host:** nas · **Component:** sonarr (192.168.10.4:8989) · **Auditor:** triage:sonarr-unmanaged-profile · **Work item:** `fix-94`

Live re-verification of the failing check sonarr-unmanaged-profile (fix-45). The audit-safe/daily output is PROFILE_BAD with exactly 5 names (Teen Titans Go!, Animaniacs, Freakazoid!, The Grim Adventures of Billy & Mandy, Johnny Bravo) — but that is a truncation artifact of `bad[:5]` in the check cmd with no total emitted. Live, 10 monitored series sit on qualityProfileId==1 ('Any'), the Sonarr default/unmanaged profile. The 5 printed are simply the 5 lowest series-IDs (155,231,237,238,243; added 2026-02-15..2026-06-28) that always fill the first 5 slots, so the doubling has been invisible in the audit output. The 5 hidden additions were all added 2026-08-10 (12d before this run): Cardcaptor Sakura (266), Hamtaro (267), Kodocha (265), Zoids: Chaotic Century (272), Zoids: New Century Zero (273) — an anime batch. Root cause is the same fix-45 class: series added without selecting the managed profile fall back to 'Any'; the managed default is WEB-1080p (id 7), used by 157 of 168 monitored series. Consumer-end impact: Cardcaptor Sakura already grabbed 7 episodes at Bluray-1080p (outside the WEB-1080p policy); the older cartoons hold large libraries on 'Any' (Teen Titans Go! 230.9GB/387 files, Animaniacs 103.7GB/236 files, Grim Adventures 86.4GB/81 files); the other 4 new anime are 0-file and will grab at any quality on the next monitored search. This is a known reopen candidate for fix-45 (fix-45 marked done 2026-07-19 but this check regressed and is in tonight's failure baseline). NOT fixed per read-only mandate — reassigning each series to qualityProfileId 7 (WEB-1080p) is the remediation, deferred to fix-45 reopen.

<details><summary>Evidence</summary>

```
$ ssh mini 'export SONARR_API_KEY=$(grep "^SONARR_API_KEY=" /etc/verification/env | sed ...); python3 - <<PY ... /api/v3/qualityprofile + /api/v3/series ... PY'
PROFILES: {"1":"Any","2":"SD","3":"HD-720p","4":"HD-1080p","5":"Ultra-HD","6":"HD - 720p/1080p","7":"WEB-1080p"}
TOTAL_SERIES: 168
PROFILE1_NAME: Any
PROFILE1_TOTAL: 10 MONITORED: 10 UNMONITORED: 0
  BAD: 155 | Teen Titans Go! | added: 2024-02-15
  BAD: 231 | Animaniacs | added: 2026-06-28
  BAD: 237 | Freakazoid! | added: 2026-06-28
  BAD: 238 | The Grim Adventures of Billy & Mandy | added: 2026-06-28
  BAD: 243 | Johnny Bravo | added: 2026-06-28
  BAD: 265 | Kodocha | added: 2026-08-10
  BAD: 266 | Cardcaptor Sakura | added: 2026-08-10
  BAD: 267 | Hamtaro: Little Hamsters, Big Adventures | added: 2026-08-10
  BAD: 272 | Zoids: Chaotic Century | added: 2026-08-10
  BAD: 273 | Zoids: New Century Zero | added: 2026-08-10
MONITORED_BY_PROFILE: 1 Any -> 10 ; 7 WEB-1080p -> 157
--- grabbed qualities (5 new) ---
265 no files ; 266 {'Bluray-1080p': 7} ; 267 no files ; 272 no files ; 273 no files
(check cmd truncates: print(... 'PROFILE_BAD '+','.join(bad[:5])) )
```

</details>

### UM90. Re-verified fix-45 reopen: 10 monitored Sonarr series now on the unmanaged 'Any' profile (original fix covered 2) `known-issue`
**Host:** nas · **Component:** sonarr / sonarr-unmanaged-profile check · **Auditor:** meta:media-library-correctness · **Work item:** `fix-94`

sonarr-unmanaged-profile was in this morning's 10:29 EDT failure baseline (fix-45 reopen). Re-verified live: still failing, and the scope is now 10 monitored series on qualityProfileId=1 (Teen Titans Go!, Animaniacs, Freakazoid!, The Grim Adventures of Billy & Mandy, Johnny Bravo, +5 more) — the original fix-45 incident was 2 series, so this has grown, consistent with a recent batch add of cartoon series bypassing TRaSH custom-format junk-blocking at series-add time. The CHECK itself is healthy and doing exactly its job (it caught the class regression it was built for); the hardcoded profile id is not stale — live API confirms profile id 1 is still named 'Any'. This is a live content-quality regression to remediate via /resolve-finding, NOT a check defect. NOT fixed per read-only mandate. known issue: fix-45 reopen.

<details><summary>Evidence</summary>

```
ssh mini '... python3 -c "bad=[x[title] for x in series if monitored and qualityProfileId==1]"' ->
PROFILE_BAD Teen Titans Go!,Animaniacs,Freakazoid!,The Grim Adventures of Billy & Mandy,Johnny Bravo
count=10
profile_id1_name=Any
```

</details>

### UM91. arr sqlite lock storm is bursty-slow, NOT import-stalling (corroborates new HIGH fix-55) `known-issue`
**Host:** nas · **Component:** sonarr/radarr/lidarr sqlite (NAS IO contention) · **Auditor:** flow:movies-tv · **Work item:** `fix-91`

Corroboration of the freshly-found sonarr/arr WAL lock storm (fix-55, arr-sqlite-not-locked). CONSUMER IMPACT VERDICT: imports are slowed during the night/backup IO-contention window but are NOT stalled — they complete. Live evidence at 16:47-16:48 EDT: the lock storm has fully subsided (arr_locked_last15m dropped from 20 at 22:23 to 2 now, back under the max=5 threshold, status=OK). The claimed sonarr 427MB WAL is NOT present live — sonarr.db-wal is only 1.45MB (checkpointed normally); the 210MB is the main DB, healthy for 132 series. Note the arr-sqlite-not-locked probe tracks lidarr/radarr/whisparr only (the 22:23 storm was lidarr=10 radarr=4 whisparr=6; sonarr not even in its list). Both sonarr and radarr queues show 0 warning records and radarr imported <1h before probe, so the lock/WAL contention did not block the import stage. NOT fixed per read-only mandate; the underlying transient IO contention (correlates with the NAS backup window) remains and warrants the fix-55 remediation, but downgrade consumer impact from 'imports stalling' to 'imports slow during contention bursts'.

<details><summary>Evidence</summary>

```
[22:23 run] arr-sqlite-not-locked: arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]
[live 16:48 EDT, keys exported] python3 /opt/verification/bin/nas-io-storm-probe.py locks -> arr_locked_last15m=2 max=5 status=OK [lidarr=2 radarr=0 whisparr=0]
[live, NAS sudo ls] sonarr.db=210743296 (210MB)  sonarr.db-wal=1454392 (1.45MB)  radarr.db-wal=3576192  lidarr.db-wal=2451432  (no 427MB WAL anywhere)
[live] SONARR queue total=1 warning=0 ; RADARR queue total=0 warning=0 ; radarr last import 2026-08-23T19:53Z (<1h before probe)
```

</details>

### UM92. sec-10: arr API keys still stored cleartext in unpackerr.conf (live and git-committed repo mirror) `known-issue`
**Host:** nas · **Component:** unpackerr.conf (live + repo mirror) · **Auditor:** svc:unpackerr · **Work item:** `sec-10`

Open task sec-10. The NAS live config /volume1/docker/media-automation/unpackerr/unpackerr.conf and its git-committed repo mirror foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf both contain literal 32-hex api_key values for [[sonarr]], [[radarr]], [[lidarr]] and [[whisparr]] (only the Bookshelf/Readarr key was moved to UN_READARR_0_* env / vault). Values NOT reproduced here per the no-secrets mandate. This means the repo mirror carries cleartext arr keys. NOT fixed per read-only mandate; tracked under sec-10.

<details><summary>Evidence</summary>

```
Read foss-setup/configs/nas/media-automation/unpackerr/unpackerr.conf -> [[sonarr]]/[[radarr]]/[[lidarr]]/[[whisparr]] each has 'api_key = <32-hex literal>' (redacted). Live NAS copy (sudo sed -E 's/[0-9a-f]{32}/APIKEY_REDACTED/g') is byte-identical modulo comments -> confirms same cleartext literals live. Config comment itself notes bookshelf key is 'deliberately NOT a cleartext literal here (sec-10)'.
```

</details>

### UM93. fix-23 NAS perms checks time out (exit 124) and the world-writable check is ACL-blind — the regression is invisible to its own guard `known-issue`
**Host:** nas · **Component:** verification / fix-23 monitoring efficacy · **Auditor:** cross:secrets-hygiene · **Work item:** `fix-92`

On the 2026-08-22 22:23 run both fix-23 NAS finds returned exit 124 TIMEOUT after 60s: nas-secret-file-perms (CRIT) and nas-worldwritable-sweep. Root cause = full recursive find over /volume1/docker's huge media/library trees (kiwix ZIMs, jellyfin, immich, komga, audiobookshelf). Compounding: nas-worldwritable-sweep uses find -perm -0002, and GNU find 4.4.2 on the NAS reports /volume1/docker's POSIX mode as 555 (ACL-masked) while stat/ls report 777 — so even if it completed it would NOT flag the world-writable top dir. Net: fix-23's own monitoring cannot detect the 0777 regression it exists to catch. I re-probed with bounded depth+pruning (see other findings). NOT fixed per read-only mandate; suggest depth-bounded/pruned find + a stat-based (not find -perm) world-writable assertion.

<details><summary>Evidence</summary>

```
# from results.json (2026-08-22T22:23):
nas-secret-file-perms  status=fail exit=124 output='TIMEOUT after 60s'
nas-worldwritable-sweep status=fail exit=124 output='TIMEOUT after 60s'
# find vs stat disagreement on the known-777 dir:
$ ssh nas 'sudo find /volume1/docker -maxdepth 0 -printf "%m %p\n"'
555 /volume1/docker
$ ssh nas 'stat -c "%a %n" /volume1/docker'
777 /volume1/docker
$ ssh nas 'sudo find /volume1/docker -maxdepth 0 -perm -0002'   # (empty: -perm -0002 misses it)
```

</details>

### UM94. fix-23 secret-perms CRIT is failing on 60s TIMEOUT (IO-load casualty of fix-55), NOT a proven perms exposure — sampled secrets are correctly 600 `known-issue`
**Host:** nas · **Component:** verification/secrets.yaml (fix-23 nas-secret-file-perms CRIT) · **Auditor:** svc:host-nas · **Work item:** `fix-92`

The two fix-23 checks ('no group/world-readable .env|config.ini|config.xml under /volume1/docker' and 'no world-writable files under /volume1/docker or /volume1/scripts') are reported as fail with output 'TIMEOUT after 60s' — the find over /volume1/docker cannot complete inside the check budget while the volume is IO-saturated (fix-55). This morning's baseline already noted fix-23 'CRIT — 60s timeout, correlates with NAS IO load'; it is the same casualty, not a re-discovered exposure. ADJUDICATION: a light spot-check (glob + stat, no recursive find) of the representative secret files shows they are all -rw------- (600) owned by btabaska:users or root:root — no group/world-readable violation in the sampled set. So the CRIT alert is currently a false-fail masked by the IO storm; the underlying secrets that were sampled are NOT exposed. A stray file elsewhere in the tree cannot be fully ruled out without the full find (deliberately not run per read-only + no-find-over-/volume1 rules). Fixing fix-55 (or raising the check timeout) will let this CRIT self-clear. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
verify-audit-uc/results.json -> fix-23 'no group/world-readable ...' FAIL output='TIMEOUT after 60s' ; fix-23 'no world-writable files...' FAIL output='TIMEOUT after 60s'
$ sudo ls -la /volume1/docker/*/.env -> -rw------- btabaska:users bitmagnet/.env, media-automation/.env, stash/.env, beszel-agent/.env ; -rw------- root:root diun/.env, immich/.env
$ sudo stat -c '%A %U:%G %n' .../config.xml -> -rw------- btabaska:users prowlarr/config/config.xml ; -rw------- btabaska:users radarr/config/config.xml ; -rw------- btabaska:users sonarr/config/config.xml
(cross-check: verify check 'health.env is root:root 600' = pass)
```

</details>

### UM95. CURRENT SQLite 'database is locked' storm hitting whisparr (fix-55 recurrence) `known-issue`
**Host:** nas · **Component:** whisparr / SQLite (NAS I/O) · **Auditor:** svc:whisparr · **Work item:** `fix-91`

Taxonomy-7/13. whisparr logs since 2026-08-02 show a recurring SQLite Busy (code=5, 0x800007AF) 'database is locked' storm failing RefreshMonitoredDownloads, CheckHealth and ApplicationUpdateCheck; 6 'database is locked' lines in the last 30 min. The audit-safe verify run's arr-sqlite-not-locked probe reports status=STORM [lidarr=10 radarr=4 whisparr=6] (max=5). This maps to fix-55 (NAS chronic I/O pressure + SQLite lock storm), which is marked done in progress.json but is clearly RE-EMERGED under the current heavy NAS I/O load noted in the audit context — a reopen candidate / silently-worsened residual. A transient Prowlarr Torznab connect timeout also appears (same I/O root cause; indexer apikey in that log line redacted, not reproduced). No genuine data loss for whisparr (it isn't grabbing), but the storm degrades all NAS arrs. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ docker logs whisparr --since 2026-08-02 | grep -iE 'error|locked' -> [Error] CommandExecutor: Error occurred while executing task RefreshMonitoredDownloads; code = Busy (5) System.Data.SQLite.SQLiteException (0x800007AF): database is locked (also CheckHealth, ApplicationUpdateCheck)
$ docker logs whisparr --since 30m | grep -c 'database is locked' -> 6
verify-audit-uc results.json: id=arr-sqlite-not-locked status=fail output='arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]'
tasks.json fix-55 present; progress.json done['fix-55']=True
```

</details>

### UM96. Zero-throughput frozen-green: 0 files, 0 history across 1055 tracked scenes (sole site unmonitored)
**Host:** nas · **Component:** whisparr / library throughput · **Auditor:** svc:whisparr · **Work item:** `fix-88`

Taxonomy-13 zero-throughput. whisparr's only series 'Girlsway' has monitored=False (qualityProfileId 6, added 2026-07-21), 1055 totalEpisodes, episodeFiles=0, sizeOnDisk=0.0GB, and the history table is completely empty (totalRecords=0) — the app has NEVER grabbed or imported a single scene since seed-13 (2026-07-14). The pipeline is otherwise wired (Deluge enabled, 3 Prowlarr indexers RSS+search on, rootfolder /data accessible w/ 9.3TB free) and the DB is actively written (whisparr2.db mtime 2026-08-23 15:40, fresh WAL), so the poller runs — nothing is grabbed because the site is left unmonitored. The consumer purpose (feed the Stash sub-library with scenes) has produced zero output; end-to-end grab->import->Stash-scan is UNPROVEN because it has demonstrably never happened. This mirrors the fix-60 Immich zero-assets 'green but never used' pattern but no task tracks it for whisparr. Dormant-by-config, not erroring — NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
$ curl -s -H X-Api-Key:*** localhost:6969/api/v3/series -> title Girlsway | monitored False | qualityProfileId 6 | path /data/Girlsway | added 2026-07-21T19:33:27Z
$ series stats -> series 1 | episodeFiles 0 | totalEpisodes 1055 | sizeOnDiskGB 0.0
$ curl .../api/v3/history?pageSize=8&sortKey=date -> totalHistory 0
$ curl .../api/v3/queue?pageSize=200 -> total 0
```

</details>

### UM97. seed-13 whisparr->stash auto-scan is silently broken (metadataScan POSTed without ApiKey -> 401)
**Host:** nas · **Component:** whisparr->stash chain-36 (seed-13 auto-scan) · **Auditor:** svc:stash · **Work item:** `fix-88`

The LIVE Whisparr Connect custom script /volume1/docker/whisparr/config/stash-scan.sh POSTs the metadataScan mutation to http://192.168.10.4:9999/graphql with NO ApiKey header. Stash now enforces auth (config.yml dangerous_allow_public_without_auth:"false"); an unauthenticated GraphQL POST returns 401 (proven live). The script uses 'curl -s ... >/dev/null 2>&1' and 'exit 0', so Whisparr always records success (taxonomy 6 silent-scheduled-job-fail + 9 config-edited-never-reloaded + 11 upstream-auth-rot-under-exit-0). Net effect: when Whisparr imports a scene, Stash will NOT auto-index it; requires a manual scan. Currently LATENT — Whisparr has zero history and empty queue (TOTAL_HISTORY 0, QUEUE_TOTAL 0), so nothing is flowing through the pipe right now. Related prior fix fix-62/SM9 added the ApiKey to the MONITORING check (stash-serving) on ~2026-07-22 but did NOT patch this integration script, which carries the identical auth-rot. Repo mirror foss-setup/configs/nas/media-automation/whisparr/stash-scan.sh is identical (also keyless) so live==repo, not drift. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
cat /volume1/docker/whisparr/config/stash-scan.sh ->
  QUERY='{"query":"mutation{metadataScan(input:{paths:[\"/data/whisparr\"]})}"}'
  curl -s -m 20 -X POST "$STASH_URL" -H 'Content-Type: application/json' -d "$QUERY" >/dev/null 2>&1  (no ApiKey header; exit 0)
[NOAUTH graphql POST {version{version}}] -> HTTP 401
config.yml: dangerous_allow_public_without_auth: "false"
whisparr /api/v3/history -> TOTAL_HISTORY 0 ; /api/v3/queue -> QUEUE_TOTAL 0
docker logs stash --since 2026-08-02 | grep -i metadatascan|scanning -> (no scan tasks in window)
```

</details>

### UM98. Dead runbook references: wiki/runbooks/backups.md (on a CRIT check) and wiki/runbooks/media.md resolve to no file
**Host:** repo · **Component:** checks.d/alerting.yaml: runbook references · **Auditor:** meta:alerting · **Work item:** `fix-99`

Repo convention: 'wiki/runbooks/X.md' is the published-site path backed by foss-setup/wiki/docs/runbooks/X.md (alerting.md resolves fine this way). But alert-dsm-immich-task-scheduled (severity CRIT) points at wiki/runbooks/backups.md and media-youtube-mounts-rw at wiki/runbooks/media.md — neither backups.md nor media.md exists under foss-setup/wiki/docs/runbooks/ (nearest real pages: backup-restore.md; media-aux.md/media-watchable.md/media-library-correctness.md). A crit alert's runbook link dead-ends exactly when an operator needs it. Repo-wide grep shows 6 uses of the dead backups.md path across checks.d (other lanes' files affected too). Fix is a repo edit + redeploy of the yaml — NOT done per read-only mandate.

<details><summary>Evidence</summary>

```
ls foss-setup/wiki/docs/runbooks/ | grep -E '^(backups|media)\.md' -> (no output; backup-restore.md, media-aux.md etc. exist)
find foss-setup -name backups.md -o -name media.md -> only foss-setup/wiki/docs/reference/checks/{backups,media}.md (generated check-index pages, not runbooks)
grep -rhoE 'runbook: .*' foss-setup/verification/checks.d/*.yaml | sort | uniq -c | grep -E 'backups|media\.md' -> 6 runbook: wiki/runbooks/backups.md, 6 runbook: wiki/docs/runbooks/media-aux.md ...
```

</details>

### UM99. 5 of 6 dns checks reference a nonexistent runbook (wiki/runbooks/dns.md) — dead link in the crit alert chain
**Host:** repo · **Component:** verification/checks.d/dns.yaml · **Auditor:** meta:dns · **Work item:** `fix-99`

dns-mini-internal, dns-mini-external, dns-mini-unbound-upstream, dns-nas-internal, dns-nas-external all carry runbook: wiki/runbooks/dns.md. No such file exists anywhere in the repo — foss-setup/wiki/ contains only docs/ + mkdocs.yml, and the only DNS runbook is foss-setup/wiki/docs/runbooks/dns-outage.md. checks_runner.py line 229 copies the runbook field verbatim into results JSON (consumed by ntfy alerts and llm-triage), so a responder to a crit DNS page is pointed at a dead path during the exact incident the runbook exists for. The 6th check (mini-container-dns-egress) uses the newer wiki/docs/runbooks/fleet-hygiene.md convention, which resolves. Broader pattern: ~150 runbook refs across checks.d/*.yaml still use the legacy wiki/runbooks/* prefix (rig.md x32, docker.md x27, verification.md x24, nas.md x16, ...) — none of which exist on disk; flagged here scoped to this lane's file, fleet-wide sweep belongs to the harness meta-audit rollup. NOT fixed per read-only mandate. No open task covers runbook-path rot.

<details><summary>Evidence</summary>

```
$ ls foss-setup/wiki/runbooks/dns.md
"foss-setup/wiki/runbooks/dns.md": No such file or directory
$ find foss-setup -name 'dns.md'
foss-setup/wiki/docs/reference/checks/dns.md   # generated checks page, not a runbook
$ ls foss-setup/wiki/docs/runbooks/ | grep -i dns
dns-outage.md
$ grep -c 'runbook: wiki/runbooks/dns.md' foss-setup/verification/checks.d/dns.yaml
5
$ grep -h 'runbook:' foss-setup/verification/checks.d/*.yaml | sort | uniq -c | sort -rn | head -3
  32     runbook: wiki/runbooks/rig.md
  27     runbook: wiki/runbooks/docker.md
  24     runbook: wiki/runbooks/verification.md   # wiki/runbooks/ dir does not exist
```

</details>

### UM100. Crit-severity DR-convergence check is exit-status-only liveness — no freshness assertion, passes vacuously if the timer dies or on a rebuilt host that never ran
**Host:** rig · **Component:** checks.d/backups.yaml: ansible-pull-ok-rig · **Auditor:** meta:backups · **Work item:** `fix-100`

The check (backups.yaml line 229-237) asserts only `systemctl show ansible-pull.service -p ExecMainStatus` == 0. ExecMainStatus is systemd's LAST exit code: it stays 0 forever if ansible-pull.timer is later disabled or stops firing, and `systemctl show` prints the default 0 for a service that has never run this boot — so a freshly rebuilt rig (the exact fix-42/M52 DR scenario this crit check exists to guard) passes before ansible-pull has ever converged it. This is pattern #12 (stale last-success dead-man) with no dead-man at all. Contrast: the sibling restic-latest-age wrapper on the same hosts reads the same systemd record but ALSO asserts age < 26h and persists a reboot-surviving marker — the fix is to apply the same shape (assert ExecMainExitTimestamp age, e.g. < 26h, alongside status). Live today the loop is healthy (last run 2026-08-22 04:20:46 EDT, 17h ago vs mini clock 22:11 EDT, timer enabled, next 04:40) so the check is currently truthful, but only by luck of the mechanism it doesn't test. fix-42 is in the reopened ledger for role-drift reasons; this check-design gap is not itself tracked. Classification: liveness. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
cmd: systemctl show ansible-pull.service -p ExecMainStatus / expect: '^ExecMainStatus=0$' (severity: crit)
$ ssh rig 'systemctl show ansible-pull.service -p ExecMainStatus,ExecMainExitTimestamp,ActiveState,Result; systemctl list-timers --all | grep -i ansible; systemctl is-enabled ansible-pull.timer'
ActiveState=inactive
Result=success
ExecMainExitTimestamp=Sat 2026-08-22 04:20:46 EDT
ExecMainStatus=0
Sun 2026-08-23 04:40:32 EDT  6h  Sat 2026-08-22 04:20:18 EDT  17h ago  ansible-pull.timer  ansible-pull.service
enabled
$ ssh mini date -> Sat Aug 22 10:11:08 PM EDT 2026
Today's 10:29 run: ansible-pull-ok-rig | pass | ExecMainStatus=0 (no timestamp in the signal)
```

</details>

### UM101. unsloth-studio running on rig but missing from the verification coverage manifest `known-issue`
**Host:** rig · **Component:** coverage-manifest · **Auditor:** flow:unsloth-studio · **Work item:** `fix-97`

Re-verified the pre-existing baseline fail containers-manifest-rig (task verify-06). The unsloth-studio container has been up 5 days (deployed lai-28 2026-08-17) yet is absent from /opt/verification/coverage/rig.containers, so the coverage-drift gate fails ('20a21 > unsloth-studio'). This violates the 100%-monitoring-coverage tripwire (the service IS monitored by unsloth-studio-e2e, but the container-manifest row was never added on deploy). Consumer feature is unaffected — this is a coverage-manifest bookkeeping gap only. NOT fixed per the read-only audit mandate; fix = add the unsloth-studio row to the rig containers manifest.

<details><summary>Evidence</summary>

```
results.json check containers-manifest-rig: status=fail exit=1 output='20a21\n> unsloth-studio'
cmd: ssh rig "docker ps --format '{{.Names}}'" | grep -vE -- '(-run-|^immich_machine_learning$)' | sort | diff /opt/verification/coverage/rig.containers -
$ ssh rig docker ps --filter name=unsloth-studio -> unsloth-studio  Up 5 days  0.0.0.0:8210->8000/tcp (running, not in manifest)
```

</details>

### UM102. rig: two uncodified all-interface listeners 27036 (Steam) + 59999 (MoonDeckBuddy) — owners confirmed benign, drift real, not in ANY baseline `known-issue`
**Host:** rig · **Component:** lan-exposure / rig.ports baseline (fix-51) · **Auditor:** cross:lan-exposure · **Work item:** `fix-98`

The daily rig listener-drift check FAILs on 27036 and 59999. Confirmed owners (task asked to confirm): 27036 = the Steam client (in-home streaming / discovery), pid 667715 user btabaska; 59999 = MoonDeckBuddy (the MoonDeck host agent that exposes a REST control API to launch/control Steam from a Steam Deck), pid 651837 user btabaska. Both are legitimate gaming-host desktop apps, NOT rogue listeners — the tripwire fired correctly on genuine but un-baselined exposure. Neither port is in the repo baseline OR the deployed baseline, so this is true drift needing codification (add both to foss-setup/verification/assets/expected-listeners/rig.ports, then redeploy). Note the 59999 MoonDeck REST agent is an unauthenticated all-interface control-plane surface on the trusted VLAN — accepted under the same flat-LAN tradeoff as the AI ports pending ha-19 IoT segmentation, but worth codifying with an explicit WHY comment. Covered by open reopen-candidate fix-51 (lan-listeners-drift-rig) per today's failure baseline. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh rig 'id -un'  ->  btabaska
$ ssh rig 'ss -tlnp | grep -E ":(27036|59999) "'
LISTEN 0 128    0.0.0.0:27036 0.0.0.0:*  users:(("steam",pid=667715,fd=140))
LISTEN 0 50          *:59999      *:*     users:(("MoonDeckBuddy",pid=651837,fd=18))
$ ssh rig 'ps -o pid,user,comm -p 667715,651837'
 667715 btabaska steam
 651837 btabaska MoonDeckBuddy
# neither port present in repo or deployed rig.ports baseline
```

</details>

### UM103. lumiverse-data volume (master key + user/chat/secrets) NOT in restic backup set, contradicting its own compose comment
**Host:** rig · **Component:** lumiverse / restic-backup · **Auditor:** svc:lumiverse · **Work item:** `fix-93`

The lumiverse data volume docker_lumiverse-data (/app/data, 9.1M -- holds lumiverse.db with the LLM/image connections, user account, chats, characters, encrypted secrets, AND data/lumiverse.identity which the compose itself calls 'the master key for stored secrets') is NOT included in the rig restic backup. restic-backup.service sources /etc/restic/env (Environment=ENV_FILE=/etc/restic/env; script self-sources it), and that env explicitly overrides BACKUP_PATHS to a narrow list containing only palworld/amp/playit paths + docker_litellm_pgdata + docker_open_webui_data -- NOT docker_lumiverse-data. Today's 01:43 snapshot confirms it (paths: /etc, /home/btabaska, palworld saves; no lumiverse). This directly contradicts docker-compose.yml:277 'data/lumiverse.identity in here is the master key for stored secrets -- back it up.' On rig disk loss the identity key + encrypted secrets + chat/character/user data are unrecoverable. Mitigation (partial): connections are rebuildable via scripts/seed-lumiverse-connections.sh (per runbook), but the identity master key, user accounts, and chat/character history are not. Marinara is in the same gap. NOT fixed per read-only mandate. Not covered by any open task in the baseline.

<details><summary>Evidence</summary>

```
/etc/systemd/system/restic-backup.service: Environment=ENV_FILE=/etc/restic/env; ExecStart=/opt/scripts/restic-backup.sh (script sources env itself)
/etc/restic/env: BACKUP_PATHS="/etc /home/btabaska /opt/stacks/palworld/game/Pal/Saved /opt/stacks/palworld/game/backups /opt/stacks/amp/config/.ampdata/instances /opt/stacks/playit /var/lib/docker/volumes/docker_litellm_pgdata /var/lib/docker/volumes/docker_open_webui_data"  (no docker_lumiverse-data)
docker-compose.yml:277 '# data/lumiverse.identity in here is the master key for stored secrets -- back it up.'  volume: lumiverse-data:/app/data
journalctl restic-backup (2026-08-23 01:43): snapshot paths /etc, /home/btabaska, palworld -- no lumiverse
du -sh /var/lib/docker/volumes/docker_lumiverse-data/_data = 9.1M
```

</details>

### UM104. rig-marinara-connections is STALE (asserts obsolete public-gateway URL) — connections are actually present and correct `known-issue`
**Host:** rig · **Component:** marinara / verification check rig-marinara-connections · **Auditor:** svc:marinara · **Work item:** `fix-100`

Adjudicated the KNOWN-STALE ai-01 reopen candidate: the FAIL is the CHECK, not the connections. The check (Home repo verification/checks.d/rig.yaml:157-165) GETs marinara /api/connections and its expect regex requires the token 'https://comfyui.tabaska.us'. Live marinara returns 200 with all 6 connection rows, and every other regex token matches (LiteLLM Creative, https://llm.tabaska.us/v1, Anime Image, Z-Image Turbo, Flux.2 Klein). The ONLY unmatched token is 'https://comfyui.tabaska.us': all 4 image_generation conns use baseUrl 'http://comfyui-arbiter:8189' — the internal docker alias, BY DESIGN (memory: 'image conns MUST use comfyui-arbiter:8189 alias'). This live state matches the canonical rig ai-tooling scripts/seed-marinara-connections.sh byte-for-byte (LiteLLM Creative=llm.tabaska.us/v1/goetia; Anime Image/Z-Image Turbo/CyberRealistic NSFW/Flux.2 Klein all baseUrl=comfyui-arbiter:8189; OpenRouter Free re-seeded by the image). So there is NO drift live<->canonical; the check simply encodes the 2026-07-18 deploy-time public-gateway URL that was later switched to the arbiter alias and never updated. Impact: chronic false-red in the daily run (also present in the 10:29 EDT baseline), which additionally defeats the check's stated purpose (it can no longer catch a genuinely wiped/re-pointed comfyui conn since it is already red for the wrong reason). Fix (NOT applied per read-only mandate) = re-point line 161 to accept comfyui-arbiter:8189 (e.g. (?=.*comfyui-arbiter:8189) or comfyui\.tabaska\.us|comfyui-arbiter:8189). Same class affects rig-lumiverse-connections (lumiverse lane).

<details><summary>Evidence</summary>

```
ssh rig 'curl -s -m 8 http://localhost:3002/api/connections | python3 ...' ->
count= 6
- 'Anime Image' | provider= image_generation | baseUrl= http://comfyui-arbiter:8189 | model= NoobAI-XL-v1.1.safetensors
- 'Realistic Image (Z-Image Turbo)' | baseUrl= http://comfyui-arbiter:8189 | model= z_image_turbo_bf16.safetensors
- 'Realistic NSFW (CyberRealistic)' | baseUrl= http://comfyui-arbiter:8189 | model= cyberrealistic-nsfw-zimage-turbo.safetensors
- 'Realistic Image (Flux.2 Klein)' | baseUrl= http://comfyui-arbiter:8189 | model= klein-9b-comfyui
- 'LiteLLM Creative' | provider= openai | baseUrl= https://llm.tabaska.us/v1 | model= goetia | hasKey= True
- 'OpenRouter Free' | provider= openrouter | baseUrl= https://openrouter.ai/api/v1 | hasKey= True
--- check expects (rig.yaml:161): (?s)(?=.*LiteLLM Creative)(?=.*https://llm\.tabaska\.us/v1)(?=.*Anime Image)(?=.*Z-Image Turbo)(?=.*Flux\.2 Klein)(?=.*https://comfyui\.tabaska\.us)
--- audit run: rig-marinara-connections | fail
--- canonical seed (rig ai-tooling scripts/seed-marinara-connections.sh): dict(name='Anime Image',... baseUrl='http://comfyui-arbiter:8189'...) [all image conns]; dict(name='LiteLLM Creative', baseUrl='https://llm.tabaska.us/v1', model='goetia')
```

</details>

### UM105. STILL-OPEN-VALID: nvidia-cdi-refresh.service enabled + GPU containers up, but NO reboot-recovery check exists and reboot-survival is unproven `known-issue`
**Host:** rig · **Component:** nvidia-cdi-refresh + GPU-container reboot recovery (fix-81) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-81`

nvidia-cdi-refresh.service is enabled (oneshot, inactive=normal post-run); /etc/cdi/nvidia.yaml present; llama-swap (Up 4d healthy), comfyui (Up 6d), comfyui-mcp all running. However fix-81's acceptance — 'add/confirm a check that GPU containers come back after a reboot' — is NOT met: grep of verification/checks.d finds NO cdi/gpu-reboot-recovery check (only rig-gpu-arbiter-unload-hook / rig-gpu-power-tune, unrelated). Reboot-survival itself is UNPROBED per read-only mandate (cannot reboot rig).

<details><summary>Evidence</summary>

```
ssh rig 'systemctl is-enabled nvidia-cdi-refresh.service' -> enabled
docker ps: llama-swap Up 4 days (healthy), comfyui Up 6 days
grep -rniE 'cdi|gpu.*reboot' checks.d -> no reboot-recovery check; grep 'fix-81' checks.d -> (none)
```

</details>

### UM106. Palworld covered by liveness metric only — no player-join / public-connectivity consumer probe
**Host:** rig · **Component:** palworld game server · **Auditor:** meta:coverage-diff · **Work item:** `fix-100`

The only palworld check is `palworld-rest-liveness` (rig.yaml) which curls the REST :8212 /v1/api/metrics and reads serverfps. The check name itself says 'liveness'. serverfps proves the process is simulating, but nothing probes the consumer end — that a player can actually join. Contrast terraria, which has both terraria-join-handshake AND terraria-world-loaded. The playit-bedrock-public / playit-java-public checks probe the TUNNEL, not the palworld join handshake, and neither maps to palworld's port. A green-but-unjoinable palworld (auth wall, world not loaded, tunnel-to-game mismatch) would pass. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
palworld-rest-liveness cmd: curl -sm 8 -u admin:$PALWORLD_ADMIN_PASSWORD http://cachyos.tailb31641.ts.net:8212/v1/api/metrics
(no join-handshake / world-loaded / connectivity probe exists for palworld; terraria has terraria-join-handshake + terraria-world-loaded)
```

</details>

### UM107. Suwayomi rig-local data dir (library DB) is EXCLUDED from the rig restic backup set
**Host:** rig · **Component:** suwayomi · **Auditor:** svc:suwayomi · **Work item:** `fix-93`

The rig restic backup (last run today 2026-08-23 01:43 EDT, Result=success, timer active daily) uses an explicit BACKUP_PATHS override, and its latest snapshot's paths do NOT include /opt/stacks/suwayomi/data (266M). That directory holds Suwayomi's SQLite library DB, installed extensions, server.conf and thumbnails — i.e. the definitions of the 19-series library, the category, and download/reader settings (the compose header itself documents this state as living on rig at ./data). If the rig data dir is lost, that config is gone and must be manually rebuilt (re-add 19 series across sources, re-install 2 extensions). Downloaded CBZ CONTENT is safe (it lives on the NAS manga share, not rig), so impact is config/library-definition loss, not content loss. NOT fixed per read-only mandate — reported only. Not covered by any open task (fix-78 is about the download backlog, not backup coverage), so not a known issue.

<details><summary>Evidence</summary>

```
$ ssh rig 'sudo sh -c ". /etc/restic/env; restic snapshots latest --json"' | jq .paths
snapshot_time=2026-08-23T01:42:43 host=cachyos
paths=['/etc','/home/btabaska','/opt/stacks/amp/config/.ampdata/instances','/opt/stacks/palworld/game/Pal/Saved','/opt/stacks/palworld/game/backups','/opt/stacks/playit','/var/lib/docker/volumes/docker_litellm_pgdata','/var/lib/docker/volumes/docker_open_webui_data']
# /opt/stacks/suwayomi/data is absent

$ ssh rig 'docker inspect suwayomi --format "{{json .Mounts}}"'
Source=/opt/stacks/suwayomi/data -> /home/suwayomi/.local/share/Tachidesk (266M, rig-local DB/extensions/config)
Source=/mnt/nas-manga -> .../downloads (1.9G CBZ, on NAS)

$ ssh rig 'systemctl show restic-backup.service -p Result -p ExecMainExitTimestamp'
Result=success  ExecMainExitTimestamp=Sun 2026-08-23 01:43:19 EDT
```

</details>

### UM108. Suwayomi backfill backlog: 15 of 19 in-library series have 0 downloaded chapters (fix-78) — re-counted, NOT worsened vs baseline 16 `known-issue`
**Host:** rig · **Component:** suwayomi (manga acquisition backlog) · **Auditor:** flow:manga-comics · **Work item:** `fix-78`

Re-counted the fix-78 manga-backfill backlog live via Suwayomi GraphQL. 19 series in library; only 4 have any downloaded chapters (downloadCount>0), 15 have zero downloads on disk. Baseline in the task ledger was '16 series 0 chapters' — current count is 15, so it has NOT worsened (improved by 1). This is a tracked OPEN task (fix-78 manga backfill), a backlog/user-action matter, not a broken pipe: the acquisition chain itself is proven functional (mount writable, container sees mount, chain reaches Komga), so new chapters for the 4 active series still flow. Notable un-downloaded subscriptions with many source chapters available: Berserk (403 src ch, 0 dl), Welcome to Demon School! Iruma-kun (552, 0), No Guard Wife (181, 0), Why Raeliana... Mansion (150, 0), The Reason Why Raeliana... (91, 0). Also 2 of the 4 'active' series are near-empty partials — His and Her Circumstances (1 of 109) and Yotsuba&! (1 of 130) — so effectively only My Dress-Up Darling (124/124) and Spy x Family (155/155) are fully backfilled; those two = the 281 CBZ Komga indexes. NOT fixed / not actioned per read-only audit mandate; reported for the fix-78 queue.

<details><summary>Evidence</summary>

```
ssh mini 'curl -s -m20 -XPOST http://192.168.10.12:4567/api/graphql -H "content-type: application/json" -d "{\"query\":\"{mangas(condition:{inLibrary:true}){totalCount nodes{id title downloadCount chapters{totalCount}}}}\"}"' | python3 (count)
in_library_total: 19
series_with_downloads: 4
series_ZERO_downloads: 15
--- ZERO-download (fix-78 backlog) ---
  id=941 dl=0 src_ch=403 'Berserk'
  id=35  dl=0 src_ch=552 'Welcome to Demon School! Iruma-kun'
  id=823 dl=0 src_ch=181 'No Guard Wife'
  id=1094 dl=0 src_ch=150 "Why Raeliana Ended Up at the Duke's Mansion"
  id=436 dl=0 src_ch=91 'The Reason Why Raeliana...'
  ... (10 more: Berserk Gaiden, InuYasha, Looking for My One-Night Villainess, My Bride is His Wife, My Dress-Up Darling XOXO!, Okaeri, Sugar Girl Drip, The Day We Become Husband and Wife, Villainess Level 99, Why Raeliana (Volume))
--- WITH downloads ---
  id=934 dl=124 src_ch=124 'My Dress-Up Darling'
  id=932 dl=155 src_ch=155 'Spy x Family'
  id=219 dl=1   src_ch=109 'His and Her Circumstances'
  id=4   dl=1   src_ch=130 'Yotsuba&!'
```

</details>

### UM109. Unsloth Studio state volumes are NOT in the rig restic backup set (curated BACKUP_PATHS override excludes them)
**Host:** rig · **Component:** unsloth-studio / restic-backup · **Auditor:** svc:unsloth-studio · **Work item:** `fix-93`

rig's restic backup is fresh and healthy (restic-backup.timer active, last-success 2026-08-23 01:43 EDT), but /etc/restic/env overrides BACKUP_PATHS with a curated list that does NOT include either unsloth volume. The container mounts docker_unsloth_studio_data -> /workspace/studio (the DB-canonical config: the llama_cpp provider, 2 scan folders, 4 MCP servers, and UI-minted API keys) and docker_unsloth_work -> /workspace/work (3.0G). The override backs up docker_litellm_pgdata and docker_open_webui_data but neither docker_unsloth_studio_data nor docker_unsloth_work. lai-28 shipped 2026-08-17, after this backup include was last curated, so the new service's state was never added — same 'deploys skip the follow-on hygiene step' process gap seen with the coverage manifest. Impact is bounded: the config is re-seedable via seed-unsloth-studio.py (DB canonical), but that seed script is not currently checked out anywhere on the rig filesystem (sudo find / -maxdepth 6 found neither it nor an ai-tooling repo), so recovery would require re-cloning the ai-tooling repo and re-running the seed, and any UI-minted API keys / work-volume artifacts would be lost. NOT fixed per read-only mandate. Not covered by an existing open task.

<details><summary>Evidence</summary>

```
$ ssh rig 'sudo grep -E "^export BACKUP_PATHS" /etc/restic/env'
export BACKUP_PATHS="/etc /home/btabaska /opt/stacks/palworld/game/Pal/Saved /opt/stacks/palworld/game/backups /opt/stacks/amp/config/.ampdata/instances /opt/stacks/playit /var/lib/docker/volumes/docker_litellm_pgdata /var/lib/docker/volumes/docker_open_webui_data"
# -> no docker_unsloth_studio_data, no docker_unsloth_work

$ ssh rig 'docker inspect unsloth-studio --format "{{range .Mounts}}...{{end}}"'
volume /var/lib/docker/volumes/docker_unsloth_studio_data/_data -> /workspace/studio (RW=true)
volume /var/lib/docker/volumes/docker_unsloth_work/_data -> /workspace/work (RW=true)

$ ssh rig 'sudo stat -c "%y %n" /var/lib/restic-mon/last-success'
2026-08-23 01:43:19 -0400 /var/lib/restic-mon/last-success

$ ssh rig 'sudo find / -maxdepth 6 -name seed-unsloth-studio.py 2>/dev/null'
(no output)
```

</details>

### UM110. 8210 drift is a baseline DEPLOY gap: repo rig.ports blesses unsloth-studio 8210 but the mini runner's deployed baseline was never updated (worsened residual since 08-17) `known-issue`
**Host:** rig · **Component:** unsloth-studio / verification baseline (fix-51, verify-06) · **Auditor:** triage:lan-listeners-drift-rig · **Work item:** `fix-97`

Port 8210 on rig is the unsloth-studio container (lai-28), a legitimate service — 0.0.0.0:8210->8000/tcp per docker. The drift is NOT the service; it is a codify-vs-deploy gap. The REPO baseline foss-setup/verification/assets/expected-listeners/rig.ports line 27 already contains '8210 # unsloth-studio' (committed in 97a672e, file mtime Aug 17 18:23), but the DEPLOYED copy on the mini runner at /opt/verification/assets/expected-listeners/rig.ports still jumps 8199 -> 8212 with no 8210. So listener-drift.sh diffs live-8210 against a stale deployed baseline and fails. This is the same process gap tracked by verify-06 (unsloth-studio missing from containers-manifest-rig) — the lai-28 deploy updated the repo but the mini-runner assets/manifests were never re-synced. WORSENED residual: triage-2026-08-17 recorded drift as only '27036 and 59999'; triage-2026-08-23 records '8210, 27036, 59999' — 8210 entered the drift set after 08-17. Remediation (NOT applied, read-only mandate): scp the repo rig.ports to /opt/verification/assets/expected-listeners/rig.ports on mini (per CLAUDE.md verification deploy path). unsloth-studio itself has app-level auth (diceware bootstrap) so LAN exposure risk is bounded; this is a monitoring-accuracy defect, not a service defect.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker ps --format "{{.Names}}\t{{.Ports}}" | grep -E "8210|unsloth"'
unsloth-studio	22/tcp, 8888/tcp, 0.0.0.0:8210->8000/tcp, [::]:8210->8000/tcp

$ ssh mini 'cat /opt/verification/assets/expected-listeners/rig.ports' | grep -vE '^\s*#' | grep -E '8199|821'
8199    # bioclip-api — BioCLIP 2 plant/species ID (lai-22)
8212    # palworld — REST admin API   # <-- NO 8210 in DEPLOYED baseline

$ sed -n '26,28p' foss-setup/verification/assets/expected-listeners/rig.ports   # REPO baseline
8199    # bioclip-api — BioCLIP 2 plant/species ID (lai-22)
8210    # unsloth-studio — Unsloth Studio web UI (2026-08-17)
8212    # palworld — REST admin API

$ git log --oneline -1 -- foss-setup/verification/assets/expected-listeners/rig.ports
97a672e lai-28: Unsloth Studio on the rig — web UI, llama-swap lanes, MCP tools

# triage worsening
08-17: "Two new TCP listeners on rig (ports 27036 and 59999)"
08-23: "New TCP listeners on rig (ports 8210, 27036, 59999)"
```

</details>

### UM111. fix-51 lan-listeners-drift-rig still failing: 27036 (Steam) & 59999 (MoonDeck) undocumented; 8210 (unsloth) is a deployed-asset-vs-repo lag `known-issue`
**Host:** rig · **Component:** verification / listener-drift baseline (expected-listeners/rig.ports) · **Auditor:** svc:host-rig · **Work item:** `fix-98`

Re-verified fix-51 still holds (baseline: failing in the 22:23 EDT audit run). LISTENER_DRIFT=rig:8210,27036,59999. Breakdown after mapping each port to its owner (`ss -tlnp`): 8210=docker-proxy(unsloth-studio), 27036=steam (In-Home Streaming/Remote Play discovery), 59999=MoonDeckBuddy. All three are legit, benign LAN services on the trusted VLAN — 59999 is even actively monitored elsewhere (check 'MoonDeckBuddy API answers TLS on rig:59999 (game-06)' passes). Nuance worth codifying: the repo baseline foss-setup/verification/assets/expected-listeners/rig.ports ALREADY lists port 8210 (and 8199), but the DEPLOYED asset on mini /opt/verification/assets/expected-listeners/rig.ports does NOT (its tail ends at 48010, missing the 8210 line) — so 8210 is a deploy-lag (fix = scp the updated asset), whereas 27036 and 59999 are genuinely absent from both repo and deployed baseline. NOT fixed per read-only mandate. Covered by fix-51.

<details><summary>Evidence</summary>

```
/tmp/verify-audit-uc/results.json -> 'rig all-interface TCP listeners...(SM58)' = fail
LISTENER_DRIFT=rig:8210,27036,59999
---
ssh rig 'ss -tlnp | grep -E :8210|:27036|:59999'
0.0.0.0:8210 => docker-proxy (unsloth-studio)
0.0.0.0:27036 => steam
*:59999 => MoonDeckBuddy
---
repo foss-setup/.../rig.ports contains: '8210  # unsloth-studio' (present)
ssh mini 'grep -E ^(8210|27036|59999) /opt/verification/assets/expected-listeners/rig.ports' -> (empty: none present in deployed asset)
```

</details>

### UM112. Connection checks fail as false-positives: they assert the deprecated comfyui.tabaska.us URL while live config correctly uses the comfyui-arbiter:8189 alias `known-issue`
**Host:** rig · **Component:** verification checks rig-marinara-connections / rig-lumiverse-connections · **Auditor:** svc:comfyui-stack · **Work item:** `fix-100`

Both frontend connection checks (rig.yaml:157-185, task ai-01, severity:warn) FAILED in today's audit-safe run. Root cause is check staleness, NOT a service defect: the expect-regexes hardcode 'https://comfyui.tabaska.us' for the image connections, but the LIVE marinara AND lumiverse connections all route through 'http://comfyui-arbiter:8189' — which is the CORRECT internal take-turns alias (per memory 'Marinara/Lumiverse wiring: image conns MUST use comfyui-arbiter:8189'). comfyui.tabaska.us maps to ComfyUI :8188 DIRECTLY, bypassing the GPU arbiter and reintroducing the 24GB VRAM OOM class — so the checks are effectively asserting a MISCONFIGURATION and can never pass against a correctly-wired system (a re-seed will not fix them; the check regex must be updated to comfyui-arbiter:8189). The LLM row ('LiteLLM Creative | https://llm.tabaska.us/v1 | key1') matches; only the image-conn URL lookaheads fail. Lumiverse also now has a 4th image conn (Realistic NSFW / CyberRealistic) beyond the documented 3. NOT fixed per read-only mandate. This is a monitoring-accuracy defect that generates permanent alert noise and would mask a genuine connection regression. Covered by ai-01 reopen candidates.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker exec lumiverse bun -e "...select name,api_url from image_gen_connections..."'
img=Anime Image (NoobAI-XL)|http://comfyui-arbiter:8189;Realistic Image (Z-Image Turbo)|http://comfyui-arbiter:8189;Realistic Image (Flux.2 Klein)|http://comfyui-arbiter:8189;Realistic NSFW (CyberRealistic)|http://comfyui-arbiter:8189
llm=LiteLLM Creative|https://llm.tabaska.us/v1|key1

$ ssh rig 'curl -s http://localhost:3002/api/connections'  (keys stripped)
'Anime Image'                     baseUrl=http://comfyui-arbiter:8189
'Realistic Image (Z-Image Turbo)' baseUrl=http://comfyui-arbiter:8189
'Realistic Image (Flux.2 Klein)'  baseUrl=http://comfyui-arbiter:8189  model=klein-9b-comfyui
'Realistic NSFW (CyberRealistic)' baseUrl=http://comfyui-arbiter:8189
'LiteLLM Creative'                baseUrl=https://llm.tabaska.us/v1

check expect (rig.yaml:161): ...(?=.*Z-Image Turbo)(?=.*Flux\.2 Klein)(?=.*https://comfyui\.tabaska\.us)
check expect (rig.yaml:181): ...(?=.*NoobAI-XL\)\|https://comfyui\.tabaska\.us)...

audit results (/tmp/verify-audit-uc/results.json):
fail  rig-marinara-connections
fail  rig-lumiverse-connections
```

</details>

### UM113. game-moondeck-buddy is TLS-listener liveness, not a Buddy API probe (only liveness-grade check in the lane)
**Host:** rig · **Component:** verification/checks.d/gaming.yaml: game-moondeck-buddy · **Auditor:** meta:gaming · **Work item:** `fix-100`

The check curls https://192.168.10.12:59999/ and passes on any bare 404 — it proves a TLS socket answers HTTP, not that MoonDeckBuddy's launch API works. Any HTTPS service squatting the port, or Buddy with a wedged API handler behind a working HTTP server, stays green while deck Steam launches fail. Per the standing mandate (liveness masquerading as a consumer probe = finding), this is the lane's one liveness-grade check. Mitigants: severity is only warn, the in-file comment honestly scopes the claim ("listener + TLS stack are up"), and Buddy's real API is pairing-gated which limits unauthenticated depth — but the probe could at least assert a Buddy-specific response signature (server header or a known /api route returning an auth-specific status rather than a generic 404) to distinguish Buddy from an arbitrary listener. Live baseline verified today: port answers 404 as expected. NOT fixed per read-only mandate. Not covered by an open task.

<details><summary>Evidence</summary>

```
repo foss-setup/verification/checks.d/gaming.yaml lines 256-259: cmd: c=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 8 https://192.168.10.12:59999/); if [ "$c" = "404" ] ...
live verify: ssh mini 'c=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 8 https://192.168.10.12:59999/); echo "buddy-code=$c"'
buddy-code=404
```

</details>

### UM114. polkit leg of rig-poweroff-inhibit is an always-pass tautology — cannot detect removal of the desktop-poweroff deny rule
**Host:** rig · **Component:** verification/checks.d/rig-host-stability.yaml:rig-poweroff-inhibit · **Auditor:** meta:rig-host-stability · **Work item:** `fix-100`

The check asserts two guards: logind HandlePowerKey=ignore (genuine — busctl reads live logind state) and 'polkit deny rule present' via pkcheck from the runner's SSH session. The pkcheck leg is vacuous: an SSH session is a non-active polkit subject, and systemd's stock defaults for org.freedesktop.login1.power-off-multiple-sessions are auth_admin_keep for any/inactive subjects — pkcheck without --allow-user-interaction returns 'not authorized' (=denied) on ANY host, rule or no rule. Proven live: mini, which has no deny rule installed, returns denied for the identical pkcheck. So deleting /etc/polkit-1/rules.d/10-inhibit-desktop-poweroff.rules from the rig would leave this check green. Worse, the actual guarded threat path — an ACTIVE desktop session invoking org.freedesktop.login1.power-off, where the stock default is allow_active=yes — is exactly the vantage the check cannot occupy. The runner also cannot fall back to asserting file presence: /etc/polkit-1/rules.d on rig is drwxr-x--- root:polkitd, NOT readable by the ssh user (verified). Suggested repair for a future session (NOT fixed per read-only mandate): compare a sha256 of the deployed rule via a sudo-less mechanism (e.g. a root-owned world-readable copy or a rig-side exporter, as done for export-manifests), or at minimum drop the pol= leg so the check name stops overclaiming. Repo rule source: /Users/brandontabaska/GitHub/Home/foss-setup/configs/host/rig/polkit/10-inhibit-desktop-poweroff.rules (denies prefix org.freedesktop.login1.power-off + .halt). Not covered by any open task (fix-64 is closed; this is a defect in its check).

<details><summary>Evidence</summary>

```
$ ssh mini 'pkcheck --action-id org.freedesktop.login1.power-off-multiple-sessions --process $$ >/dev/null 2>&1 && echo mini_pol=allowed || echo mini_pol=denied'
mini_pol=denied   # mini has NO deny rule installed — denied is the stock default from a non-active session
$ ssh rig '…same pkcheck…'
hpk=ignore pol_multi=denied pol_single=denied
$ ssh rig 'ls -ld /etc/polkit-1/rules.d; test -r /etc/polkit-1/rules.d && echo READABLE || echo NOT_READABLE'
drwxr-x--- 1 root polkitd 66 Aug  3 11:37 /etc/polkit-1/rules.d
NOT_READABLE   # runner ssh user cannot even assert the rule file exists
```

</details>

### UM115. Two ai-01 connection checks stuck permanently RED on a stale expect (comfyui.tabaska.us vs live comfyui-arbiter:8189) `known-issue`
**Host:** rig · **Component:** verification/checks.d/rig.yaml — rig-marinara-connections (L157) + rig-lumiverse-connections (L171) · **Auditor:** meta:rig · **Work item:** `fix-100`

Both checks' expect regex requires the 3 image connections to point at https://comfyui.tabaska.us (per the 2026-07-18 comment at L106-109). Live, both apps' image connections were DELIBERATELY re-pointed to the internal alias http://comfyui-arbiter:8189 — which is the correct wiring per the ops memory note (marinara/lumiverse: 'image conns MUST use comfyui-arbiter:8189 alias; arbiter recreate-not-restart'). So the expect is stale, not the wiring. Consequence: both checks are permanently failing (they are in this morning's 10:29 EDT baseline, mapped to ai-01), which INVERTS their purpose — a check wedged red can no longer distinguish a real wiped-connection row (the exact failure mode these exist to catch) from the stale expectation. Only the comfyui lookahead fails; the LLM row (LiteLLM Creative | https://llm.tabaska.us/v1 | key1) still matches live. Fix = update both expects from comfyui.tabaska.us to comfyui-arbiter:8189 (repo-only edit). NOT fixed per read-only mandate. known_issue: ai-01.

<details><summary>Evidence</summary>

```
marinara (rig curl :3002/api/connections, names filtered): PRESENT LiteLLM Creative / llm.tabaska.us/v1 / Anime Image / Z-Image Turbo / Flux.2 Klein ; ABSENT comfyui.tabaska.us
marinara URL hosts present: http://comfyui-arbiter:8189 , https://llm.tabaska.us , https://openrouter.ai (baseUrl key)
lumiverse (docker exec lumiverse bun readonly sqlite): IMG rows all = http://comfyui-arbiter:8189 (Anime Image (NoobAI-XL), Z-Image Turbo, Flux.2 Klein, +new Realistic NSFW (CyberRealistic)); LLM = LiteLLM Creative | https://llm.tabaska.us/v1 | key1
```

</details>

### UM116. deluge-preimport-stuck: Animaniacs S01 100% >48h stuck in 'sonarr' pre-import label `known-issue`
**Host:** seedbox · **Component:** deluge (import pipeline) · **Auditor:** svc:host-seedbox · **Work item:** `fix-73`

Grabbed-but-never-imported stall (taxonomy 4). One torrent is 100% complete but has sat >48h in the pre-import 'sonarr' label, meaning Sonarr never imported/relabeled it. Re-verified live tonight — still exactly 1 stuck item, not worsened. NOT fixed per read-only mandate. Covered by open task fix-25 (deluge-preimport-stuck, in today's 10:29 baseline) and related to fix-73 (deluge stuck grab). This is the specific item currently tripping the check.

<details><summary>Evidence</summary>

```
ssh seedbox '~/venvs/deluge/bin/python ~/scripts/deluge-preimport-stuck.py':
PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M
---
mini audit results.json: fail seedbox: no torrent 100% done >48h still in a pre-import label
```

</details>

### UM117. deluge-preimport-stuck TRUE POSITIVE re-verified: Animaniacs S01 season-pack orphaned 11.9d in pre-import 'sonarr' label (partial 19/160 import, rest marked-failed but not removed from client) `known-issue`
**Host:** seedbox · **Component:** deluge / sonarr import pipeline · **Auditor:** triage:deluge-preimport-stuck · **Work item:** `fix-73`

Re-verified live, still failing (fix-25 class; open task fix-73 'deluge stuck grab'). The torrent 'Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M' is 100% complete, state=Seeding, label='sonarr' (a PRE-import label), age 286.5h (~11.9d) at path /home/hd34/btabaska/files/tv. Root cause from Sonarr history (series 231): the S01 season pack was grabbed 2026-08-11T20:53 (160 grab events); only 19/160 episodes imported (last downloadFolderImported 2026-08-11T21:25:43Z); the remaining 106 episodes were 'Manually marked as failed' 2026-08-12T12:12-12:21Z (Season1 now total=160 hasFile=19 monitored=160). Marking-failed blocklists the release and drops it from the Sonarr queue (queue now holds only Teen Titans Go, seriesId 155) but does NOT remove the torrent from Deluge, so it sits orphaned in the pre-import label. The stuck item CHANGED from fix-73's named Only Murders S02E05 to this — the class recurs (streak=10 confirmed consecutive fails). Same count (1 stuck) as baseline, NOT worsened. Self-clean IS functioning (see reaper finding): the 14d reaper will auto-remove this after time_added+14d (~2026-08-25 20:53 -> next 05:00 run 08-26), at which point the 141 still-missing monitored S01 episodes will need a fresh Sonarr search to backfill. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh seedbox '~/venvs/deluge/bin/python ~/scripts/deluge-preimport-stuck.py'
PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M

# deluge status (read-only query, all pre-import labels):
now=2026-08-23 21:30:07  age_h=286.5 label=sonarr prog=100.0 state=Seeding tracker=stackoverflow.tech
  name=Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M  path=/home/hd34/btabaska/files/tv

# Sonarr history (series 231) S01/D00oo00M event-type counts:
{'grabbed': 160, 'downloadFolderImported': 19, 'downloadFailed': 106}
first grabbed: 2026-08-11T20:53:18Z ; last import: 2026-08-11T21:25:43Z
S01 downloadFailed: [106x] 'Manually marked as failed'  (range 2026-08-12T12:12:35Z .. 12:21:46Z)
Season1: total=160 hasFile=19 monitored=160

# Sonarr queue (Animaniacs NOT present -> dropped from tracking):
QUEUE total=1 -> id=1531220303 seriesId=155 'Teen Titans Go S06E32...'

# streak state (mini):
deluge-preimport-stuck streak=10, confirmed=True
```

</details>

### UM118. Pre-import stuck grab: Animaniacs S01 seeding 100% for ~287h in raw 'sonarr' label (fix-25; fix-73 Only Murders CLEARED) `known-issue`
**Host:** seedbox · **Component:** deluge preimport / arr import stall · **Auditor:** svc:deluge · **Work item:** `fix-73`

Taxonomy 4 (grabbed-but-never-imported). One torrent sits 100% complete in the raw 'sonarr' pre-import label for ~287h (~12 days) and was never relabelled to sonarr-imported: 'Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M'. Notably Animaniacs S02 and S08 DID import (both in sonarr-imported), so only S01 stalled. Re-verified the fix-73 item per lane notes: 'Only Murders S02E05' is NO LONGER present anywhere in the daemon (fix-73 = CLEARED), but the underlying fix-25 pre-import-stuck condition persists with a new title. The mini-side fix-25 check (GRABS_OK checked=53) is green while the seedbox-side check fails — classic seedbox orphan where sonarr dropped the queue item but the labeled torrent lingers. NOT remediated (read-only mandate).

<details><summary>Evidence</summary>

```
RPC name-grep: MATCHES 3 -> ('sonarr','Seeding',100,'Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M'); ('sonarr-imported','Seeding',100,'Animaniacs S08 ...'); ('sonarr-imported','Seeding',100,'Animaniacs.S02 ...'). RAW_PREIMPORT_LABELS {'shelfmark':1,'sonarr':2}. No 'only murders' match.
/tmp/verify-audit-uc/results.json fix-25 seedbox check status=fail msg='PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M'
```

</details>

### UM119. deluged.log floods to 73MB/day of libtorrent WARNINGs while fix-69 'log bounded' check stays green (daemon still -L warning since Jul30) `known-issue`
**Host:** seedbox · **Component:** deluged.log / libtorrent warning flood + fix-69 check blind spot · **Auditor:** svc:deluge · **Work item:** `fix-95`

Taxonomy 7 (retry/warning flood) + taxonomy 9 (config-edited-never-reloaded) + a monitoring blind spot. Live deluged.log is 73,736,007 bytes (~70MiB, over the 50M threshold the fix-69 check guards), 5643 WARNING lines, ~4016 of the last 5000 being one torrent (The.Lost.Boys.1987.1080p.BluRay.H264-VALUE: 'max outstanding piece requests reached, outstanding_request_limit_reached') firing several times/sec. Root cause: the running deluged (PID 2458058, started Jul30 03:38) still launches with '-L warning'; the Aug-03 fix-69 remediation (switch to '-L error' in ~/.startup/deluge + daily 04:20 copytruncate logrotate) is present in the repo/startup script but DORMANT because the daemon has never been restarted to pick it up. The fix-69 check passed (deluged_log=0M LOG_BOUNDED) in the 22:23 audit only because it samples file size at a moment shortly after the 04:20 copytruncate; it is blind to the intra-day balloon to 73MB. So the check is green-but-the-guarded-condition-is-violated most of each day = silently-worsened residual. Also one benign 'too_high_disk_queue_limit' tuning warning and 3 startup 'Torrent id not in torrents loading list'. No auth rot, no ERROR crash loop, no NUL corruption. NOT restarted/fixed (read-only mandate).

<details><summary>Evidence</summary>

```
seedbox$ ls -la ~/.config/deluge/deluged.log -> 73736007 Aug 23 21:37 (rotations .1.gz..5.gz daily Aug18-22, each ~70KB compressed)
ps: /home/hd34/btabaska/venvs/deluge/bin/deluged --pidfile ... -L warning (STARTED Jul30)
tail -5000 | uniq -c | sort -rn: 4016 '...The.Lost.Boys...outstanding_request_limit_reached'; 436 Backrooms...; grep -c error|warning full log = 5643
fix-69 check cmd: b=$(stat -c %s ~/.config/deluge/deluged.log); [ "$b" -lt 52428800 ] && echo LOG_BOUNDED; audit msg='deluged_log=0M LOG_BOUNDED' status=pass (comment: '-L warning->-L error ... on next restart')
```

</details>

### UM120. Check is RED live: libtorrent WARNING flood returned, deluged.log at 69M past the 50M guard `known-issue`
**Host:** seedbox · **Component:** seedbox-deluged-log-bounded (deluged.log / fix-69 SM18) · **Auditor:** meta:seedbox · **Work item:** `fix-95`

The seedbox-deluged-log-bounded check is currently FAILING against the live host. deluged.log is 73,386,474 bytes (~69M), above the check's 52428800-byte (50M) threshold, so the cmd emits LOG_FLOOD and does NOT match expect 'LOG_BOUNDED$'. Root cause per the check's own comment: the SM18 libtorrent performance WARNING flood ('outstanding_request_limit_reached') has RETURNED at ~1/sec — the fix-69 launcher change (-L warning -> -L error in ~/.startup/deluge) only takes effect on a deluge restart, and deluge evidently has not restarted, so the flood is live again and the daily copytruncate logrotate (04:20, size 20M) is not keeping pace (log grew back to 69M by 21:20 same day). This was NOT in this morning's 10:29 fix-69 failing set (which listed mini-scratch-hygiene + unpackerr-host-retired), so it is a silently-worsened residual = effectively a new breach of an already-tracked task. Side note: deluged.log now contains NUL bytes (grep reports 'binary file matches'); this does not affect this check (stat only), but is the taxonomy-#15 log-corruption class. NOT fixed — read-only mandate. Remediation path per runbook: restart deluge so -L error applies; durable quota reclaim is media-09/media-10.

<details><summary>Evidence</summary>

```
ssh seedbox 'stat -c "%s" ~/.config/deluge/deluged.log' -> 73386474  (mtime 2026-08-23 21:20:02, actively growing)
check logic: [ 73386474 -lt 52428800 ] is FALSE => echo LOG_FLOOD ; expect 'LOG_BOUNDED$' => NO MATCH => FAIL
tail -n3 deluged.log:
  21:20:00 [WARNING][deluge.core.torrentmanager:1616] on_alert_performance: The.Lost.Boys.1987...: performance warning: ...outstanding_request_limit_reached
  21:20:01 [WARNING] ...outstanding_request_limit_reached
  21:20:02 [WARNING] ...outstanding_request_limit_reached
grep -c outstanding_request_limit_reached (last 20000 lines) = 4027  (grep also: 'binary file matches' -> NUL bytes in log)
```

</details>

### UM121. Disabled check's justification is stale — seedbox IS reachable over SSH from the runner now
**Host:** seedbox · **Component:** sys-seedbox-ssh (enabled:false) · **Auditor:** meta:system · **Work item:** `fix-100`

sys-seedbox-ssh is enabled:false with the comment 'SSH blocked by provider network ACL — no probe path from the LAN. Re-enable if/when an API or SSH route exists.' That justification is now FALSE: (1) the mini runner executes the check's EXACT command successfully — `ssh -o BatchMode=yes -o ConnectTimeout=8 seedbox 'echo seedbox-ok'` returns seedbox-ok exit 0 (tailnet route 100.119.134.94); (2) seedbox.yaml already runs 9 enabled checks with host:seedbox (seedbox-loopback-binds, seedbox-services-manifest, deluge-preimport-stuck, seedbox-quota-headroom, etc.) that actively ssh into the box. So a probe path plainly exists and is in daily use. This check should be RETIRED (redundant with seedbox.yaml's active coverage) or revived — but the disable rationale must not stay. NOT changed per read-only mandate. Not tracked by an open task (seed-01 is the closed provisioning task).

<details><summary>Evidence</summary>

```
ssh mini "ssh -o BatchMode=yes -o ConnectTimeout=8 seedbox 'echo seedbox-ok'; echo EXIT=$?"
# -> seedbox-ok
# -> EXIT=0
python3 -c 'import yaml;d=yaml.safe_load(open("verification/checks.d/seedbox.yaml"));[print(c["id"],c.get("host"),c.get("enabled",True)) for c in d["checks"] if c.get("host")=="seedbox"]'
# 9 checks, host=seedbox, enabled=True
```

</details>

## LOW (251)

### UL1. ESPHome not deployed in HA — no config_entry, zero entities, absent from catalog (lane inventory overstates)
**Host:** ha · **Component:** esphome · **Auditor:** svc:ha-integrations · **Work item:** `fix-102`

The lane inventory lists ESPHome as a component of this service, but it does not exist in HA. /api/config/config_entries/entry (18 entries) contains no esphome domain (present: hue, mobile_app, matter, backup, +14 others). A full /api/states dump (140 entities) has zero entities mentioning esphome and no device-class sensors consistent with ESPHome nodes. ESPHome is also absent from service-catalog.yaml. Conclusion: ESPHome integration was never adopted / has no devices — nothing to probe as a live service. UNPROBED for a possible standalone ESPHome dashboard add-on (HA SSH refused by design and no supervisor add-on API access this lane); if such an add-on exists it has no HA-adopted devices. Recommend correcting the lane/service inventory. NOT a live failure.

<details><summary>Evidence</summary>

```
curl .../api/config/config_entries/entry => 18 entries; grep esphome => (none). Loaded: matter, backup, hue (Hue Bridge ecb5fa99b37d), mobile_app (Btiphone)
python3 scan of ha-states.json (140 entities): '=== entities mentioning esphome: []'
grep -niE 'esphome' configs/docker-stack/service-catalog.yaml => (no match)
```

</details>

### UL2. Re-verified: ha-updates-pending still failing — core/OS/Matter updates pending 22-25 days `known-issue`
**Host:** ha · **Component:** ha-updates-pending (fix-36) · **Auditor:** meta:ha · **Work item:** `fix-104`

Known failure from this morning's 10:29 baseline (reopen bridge -> fix-36); re-verified live this evening and it still holds, not worsened in kind: update.home_assistant_core_update pending 25 days, update.matter_server_update 24 days, update.home_assistant_operating_system_update 22 days (update.terminal_ssh_update at 3 days is inside the 21-day grace). Corroborated independently: today's NAS backup filename still embeds core 2026.7.2. The check itself is healthy and consumer-grade — it is correctly red; the remediation (apply the updates) is the tracked human/maintenance leg. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ curl -s -H "Authorization: Bearer $TOK" http://192.168.10.50:8123/api/states | python3 ... -> updates_on=[('update.home_assistant_core_update', 25), ('update.home_assistant_operating_system_update', 22), ('update.matter_server_update', 24), ('update.terminal_ssh_update', 3)]
$ ssh nas 'ls -lt /volume1/backups/ | head -3' -> Automatic_backup_2026.7.2_2026-08-22_04.45_00003126.tar (core version 2026.7.2 still current)
```

</details>

### UL3. sys-docker-subnet-squat=3 on the HA VLAN (ha-19, re-verified holding) `known-issue`
**Host:** ha · **Component:** ha-vlan/docker-networking · **Auditor:** svc:ha-core · **Work item:** `ha-19`

sys-docker-subnet-squat (task_id ha-19, warn) reports 3 docker networks squatting subnet space overlapping the HA Trusted VLAN. Value 3 matches this morning's baseline — stable-known, not worsened. This is a mini docker-networking concern surfaced in the HA lane because of VLAN overlap; it does not affect HA-core reachability (ha-http/ha-proxy-e2e both green). NOT fixed per read-only mandate. Known open task ha-19.

<details><summary>Evidence</summary>

```
mini /tmp/verify-audit-uc/results.json (2026-08-22T22:23): sys-docker-subnet-squat | status: fail | output: 3 | task_id: ha-19 | sev: warn
```

</details>

### UL4. 3 HA updates left pending 22-26 days (Core 2026.7.2->2026.8.3, OS 18.1->18.2, Matter 9.1.0->9.2.0) `known-issue`
**Host:** ha · **Component:** host-ha · **Auditor:** svc:host-ha · **Work item:** `fix-104`

ha-updates-pending FAILs in the audit run (the ONLY non-pass among 11 enabled HA checks). Live-verified 2026-08-23: update.home_assistant_core_update state=on inst=2026.7.2 latest=2026.8.3 pending 26d (one full monthly release behind); update.home_assistant_operating_system_update inst=18.1 latest=18.2 pending 22d; update.matter_server_update inst=9.1.0 latest=9.2.0 pending 25d. All exceed the check's >=21d threshold. update.terminal_ssh_update (inst 10.3.0->10.4.0, age 4d) and update.home_assistant_supervisor_update (state=off, up to date 2026.07.5) are correctly NOT flagged, confirming the check is accurate not stuck. Known baseline / open task fix-36 (ha-updates-pending) — RE-VERIFIED still holds, not silently worsened (same class the original fix-36 audit found: Core one release behind, OS one minor behind). Human update-apply leg; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -s -H 'Bearer $HA_TOKEN' http://192.168.10.50:8123/api/states | filter update.*:
update.home_assistant_core_update state=on inst=2026.7.2 latest=2026.8.3 age=26d
update.home_assistant_operating_system_update state=on inst=18.1 latest=18.2 age=22d
update.matter_server_update state=on inst=9.1.0 latest=9.2.0 age=25d
update.terminal_ssh_update state=on inst=10.3.0 latest=10.4.0 age=4d (not flagged)
update.home_assistant_supervisor_update state=off inst=2026.07.5 latest=2026.07.5
results.json ha-updates-pending:fail => updates=STALE:update.home_assistant_core_update,update.home_assistant_operating_system_update,update.matter_server_update
```

</details>

### UL5. service-catalog note for home-assistant is stale (still claims proxy answers 400)
**Host:** ha · **Component:** host-ha · **Auditor:** svc:host-ha · **Work item:** `fix-102`

service-catalog.yaml row home-assistant (host ha, port 8123, url https://ha.tabaska.us, category Smart Home — all correct) carries note 'Answers 400 via proxy until trusted_proxies configured (run-5); direct :8123 works.' That condition was resolved by fix-32 (trusted_proxies added); ha-proxy-e2e now PASSES and serves the real frontend through caddy. The note misleads any reader into thinking the proxy path is still broken. Doc drift only, not a runtime issue. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/configs/docker-stack/service-catalog.yaml:336-342 notes: 'Answers 400 via proxy until trusted_proxies configured (run-5); direct :8123 works.'
vs results.json ha-proxy-e2e:pass(<title>Home Assistant</title>) and checks.d/ha.yaml fix-32 comment (trusted_proxies fix shipped)
```

</details>

### UL6. service-catalog note for home-assistant is stale (claims proxy '400' — actually 200/works)
**Host:** ha · **Component:** service-catalog · **Auditor:** svc:ha-core · **Work item:** `fix-102`

configs/docker-stack/service-catalog.yaml:342 notes 'Answers 400 via proxy until trusted_proxies configured (run-5); direct :8123 works.' That condition was resolved by fix-32 — ha.tabaska.us now returns 200 with the real frontend through caddy (ha-proxy-e2e green; live probe confirms). A reader would be misled into thinking the proxy currently 400s. Minor doc-drift; NOT edited per read-only mandate.

<details><summary>Evidence</summary>

```
sed -n '336,342p' service-catalog.yaml -> notes: Answers 400 via proxy until trusted_proxies configured (run-5); direct :8123 works.
Live contradiction (mini through caddy):
$ curl -sk --resolve ha.tabaska.us:443:127.0.0.1 https://ha.tabaska.us/ | grep -o '<title>Home Assistant</title>' -> <title>Home Assistant</title>
$ curl -sk -o /dev/null -w '%{http_code}' ... -> 200
```

</details>

### UL7. 3 HA updates left pending >=21 days (fix-36); a 4th freshly pending will cross threshold in ~17d `known-issue`
**Host:** ha · **Component:** update.* entities (core / OS / matter-server) · **Auditor:** flow:home-assistant · **Work item:** `fix-104`

Confirms fix-36 (ha-updates-pending FAIL). 3 updates on >=21d: home_assistant_core 26d (2026.7.2 -> 2026.8.3), operating_system 22d (18.1 -> 18.2), matter_server 25d (9.1.0 -> 9.2.0). Live /api/config confirms running version is still 2026.7.2. A 4th (terminal_ssh, 4d, 10.3.0 -> 10.4.0) is freshly pending and currently sub-threshold — it will trip the 21d check in ~17 days. Maintenance debt / human-install leg; not a broken consumer feature. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -s -H 'Authorization: Bearer $HA_TOKEN' .../api/states | python3 (update.* state=on):
update.home_assistant_core_update             pending 26d  2026.7.2 -> 2026.8.3
update.home_assistant_operating_system_update pending 22d  18.1 -> 18.2
update.matter_server_update                   pending 25d  9.1.0 -> 9.2.0
update.terminal_ssh_update                    pending 4d   10.3.0 -> 10.4.0 (sub-threshold)
results.json ha-updates-pending -> FAIL: 'updates=STALE:...core_update,...operating_system_update,...matter_server_update'
```

</details>

### UL8. git-foss-setup-clean fail = open fix-80 manifest residual, re-verified not worsened; dirty set is NOT the in-flight session WIP `known-issue`
**Host:** mini · **Component:** /opt/foss-setup git clone (glue-08 / git-foss-setup-clean) · **Auditor:** triage:git-foss-setup-clean · **Work item:** `fix-80`

Known issue: open task fix-80 ('Commit the regenerated /opt/foss-setup manifests + clear clone drift') names this exact state. The 3 dirty entries are the regenerated-but-uncommitted manifest outputs (configs/inventory/inventory.md, hosts/macmini/compose-images.txt, hosts/macmini/systemd-timers.txt), refreshed by the weekly export-manifests run Mon 2026-08-17 04:01 EDT. Diff content is pure generated churn (lai-era images added: open-terminal, go-pmtiles, photon, searxng, booklogr; kometa v2.4.4->v2.4.6; container count 45->50, timers 24->30) — no hand edits, no secret material. Not worsened: this morning's 10:29 EDT daily run also failed with output '3'; identical file set both runs; failure history in triage-*.md spans 2026-07-08 through 2026-08-22. The lane's working hypothesis (dirty set = tonight's in-flight Mac-session WIP) is WRONG for this check: the Caddyfile + homepage services.yaml WIP does not appear here — that maps to git-stacks-clean/docker-12. NOT fixed per read-only mandate; the fix is fix-80's prescribed reconcile+commit.

<details><summary>Evidence</summary>

```
$ ssh mini 'sudo git -C /opt/foss-setup status --porcelain'
 M foss-setup/configs/inventory/inventory.md
 M foss-setup/hosts/macmini/compose-images.txt
 M foss-setup/hosts/macmini/systemd-timers.txt
$ ssh mini 'sudo git -C /opt/foss-setup diff --stat'
 foss-setup/configs/inventory/inventory.md   | 16 +++++---
 foss-setup/hosts/macmini/compose-images.txt |  8 +++-
 foss-setup/hosts/macmini/systemd-timers.txt | 64 ++++++++++++++++-------------
$ ssh mini python3 …/var/lib/verification/results.json (morning daily): {"status": "fail", "output": "3", "exit_code": 0}
tonight audit-safe results.json: {"id": "git-foss-setup-clean", "status": "fail", "output": "3"}
inventory.md diff: -> Generated: 2026-08-17T04:01:41-04:00 (was 2026-07-28T13:11:51)
tasks.json fix-80 summary: 'The mini and rig /opt/foss-setup clones carry regenerated-but-uncommitted inventory/manifest output … driving … git-foss-setup-clean …'
todo.md:27: - [ ] **`fix-80`** Commit the regenerated /opt/foss-setup manifests + clear clone drift
```

</details>

### UL9. fix-80 'self-heals on next ansible-pull' assumption disproven — clone frozen at 2026-07-28, now 99 commits behind main and growing `known-issue`
**Host:** mini · **Component:** /opt/foss-setup git clone vs origin/main · **Auditor:** triage:git-foss-setup-clean · **Work item:** `fix-80`

fix-80's summary claims the /opt/foss-setup drift 'self-heals on the next ansible-pull', but ansible-pull's checkout dir is /home/btabaska/.ansible-pull (dest= in the unit journal), not /opt/foss-setup. ansible-pull ran successfully this morning (2026-08-22 04:25:57 EDT, timer healthy, next run Sun 04:27) yet /opt/foss-setup HEAD remains f683cfd (2026-07-28, 'glue-15'), which is 99 commits behind origin/main as of tonight. The lag grows mechanically as main advances, so no automated path will ever clear this check — closing fix-80 requires its prescribed manual reconcile+commit (review manifest truth, commit, fast-forward the clone). Same residual class as fix-80, filed as a scoping correction to that task, not a new regression. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'sudo git -C /opt/foss-setup log --oneline -1'
f683cfd glue-15: clear pre-existing fleet git-hygiene regressions surfaced by glue-14
$ git show -s --format='%h %ci %s' f683cfd
f683cfd 2026-07-28 13:12:49 -0400 glue-15: …
$ git log --oneline f683cfd..origin/main | wc -l
99
$ ssh mini 'journalctl -u ansible-pull.service -n 25 --since -36h' | head
Aug 22 04:25:57 macmini systemd[1]: Starting ansible-pull fleet convergence (glue-08)...
Aug 22 04:25:58 macmini python3[2363128]: ansible-git Invoked with name=git@forgejo:home/homelab.git dest=/home/btabaska/.ansible-pull …
$ ssh mini 'systemctl list-timers ansible-pull.timer --no-pager'
NEXT Sun 2026-08-23 04:27:21 EDT … LAST Sat 2026-08-22 04:25:57 EDT 18h ago ansible-pull.timer
```

</details>

### UL10. Re-surfacing the one practical UNPROBED gap: MeTube yt-dlp is ~7 weeks stale and its fresh-download leg is untested
**Host:** mini · **Component:** MeTube (docker-02) yt-dlp staleness — latent extraction-failure risk · **Auditor:** completeness-critic · **Work item:** `fix-101`

Of all 55 UNPROBED legs, this is the only one representing a live latent risk (the rest are human hops / deliberate day-window / read-only mutation-avoidance). MeTube's embedded yt-dlp is 2026.07.06 (container Up 6 weeks, never restarted) vs pinchflat's 2026.08.20 — old yt-dlp routinely fails current YouTube extraction, so the MeTube->beets->Navidrome audio-ingest chain may be silently broken at the fetch step. It could not be proven either way read-only: no new MeTube input has arrived since 2026-07-08 and triggering a real download is not an authorized self-cleaning probe. Not a confirmed failure — an untested-and-aging surface. Recommend the operator either pull a newer MeTube image or run one manual test download. NOT changed per read-only mandate. (Already captured by the audit at finding #47; re-surfaced here because it is the single UNPROBED leg with real operational risk rather than a by-design boundary.)

<details><summary>Evidence</summary>

```
# finding #47 evidence, re-affirmed:
curl localhost:8081/version => "yt-dlp": "2026.07.06.234510"
pinchflat yt-dlp --version: 2026.08.20.234504 (newer)
docker ps: metube Up 6 weeks (never restarted)
source dir /volume1/music/YouTube newest file: 2026-07-08 (no fresh input to exercise the chain)
```

</details>

### UL11. 46/3525 (1.3%) greyed-out missing tracks across 4 albums — stable vs baseline `known-issue`
**Host:** mini · **Component:** Navidrome library (media_file.missing) · **Auditor:** flow:music · **Work item:** `fix-103`

Read-only sqlite count confirms 46 tracks flagged missing=1 (greyed-out in the UI) out of 3525, 1.3%, concentrated in 4 albums (Charli xcx/Vroom Vroom, Lana Del Rey/Greatest Songs, Linkin Park/The Hunting Party, +1). Identical to the baseline navidrome-scan-integrity/library-present output (missing=46/3525), so stable and not worsening; well under the PRESENT_OK threshold. The remaining 3479 tracks stream fine (proven above). Minor library-hygiene caveat — a handful of album folders whose files no longer exist on /volume1/music while the DB rows persist. NOT fixed (read-only).

<details><summary>Evidence</summary>

```
sqlite3 -readonly navidrome.db -> missing=46 total=3525 pct=1.3
select count(distinct album) where missing=1 -> 4
affected: Charli xcx/Vroom Vroom, Lana Del Rey/Greatest Songs, Linkin Park/The Hunting Party (+1)
baseline navidrome-scan-integrity -> INTEGRITY_OK missing=46/3525 ; navidrome-scan-fresh -> SCAN_FRESH age_min=7.9
```

</details>

### UL12. 3 rotted Seerr requests (fix-26) `known-issue`
**Host:** mini · **Component:** Seerr request layer · **Auditor:** flow:movies-tv · **Work item:** `fix-90`

Known fix-26 request-layer rot, present in tonight's run: 3 rotted requests — 2 dangling TV requests pointing at Sonarr series that were deleted (tv#220150→sonarr 271 gone, tv#31654→sonarr 269 gone) and 1 movie never grabbed after 12 days with 0 history (movie#20455). Consumer impact: the requesters see permanently-stuck requests. Low volume, stable. The dangling pointers also positively confirm Seerr↔Sonarr linkage is live. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
[22:23 run] request-layer-audit.py seerr -> SEERR_ROT 3: dangling:tv#220150(sonarr 271 gone); never-grabbed:movie#20455(12d, 0 history); dangling:tv#31654(sonarr 269 gone)
```

</details>

### UL13. STILL-OPEN-VALID: alert SEND path green (drill 5d, deadman armed) but device RECEIPT still unproven (human leg) `known-issue`
**Host:** mini · **Component:** alert delivery / dead-man (fix-76) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-76`

fix-63 send-path is healthy: alert-delivery-drill-fresh (5d) and alert-offmini-deadman-armed (58s) both green. fix-76's core deliverable — proving an actual phone RECEIVES the dead-man + drill topics (mandate-2) — is a phone-subscription human leg, unprovable read-only. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
alert-delivery-drill-fresh [pass]: 'drill_age_days=5 FRESH'
alert-offmini-deadman-armed [pass]: 'armed age=58s FRESH'
```

</details>

### UL14. Two transient, self-recovered API failures since 2026-08-02 — paged and recovered, not a current fault
**Host:** mini · **Component:** arr-queue-reconcile / sonarr-backlog-season-search · **Auditor:** svc:mini-host-units · **Work item:** `fix-103`

arr-queue-reconcile failed once Aug 11 16:17:58 on 'API_ERR ConnectionResetError [Errno 104]', and sonarr-backlog-season-search failed once Aug 13 20:17:41 on 'API_ERR TimeoutError: timed out'. Both are single transient upstream-API blips (not retry-storms: 41 and 4 error-ish lines across 126/146 runs; zero 401/403 auth-rot). Both units carry OnFailure=ntfy-notify@%n so the failures paged rather than failing silently, and both recovered on the very next run (continuous RECONCILE_OK/SEARCHED since). arr-queue also self-retries by design ('WARN delete failed; will retry next run', Aug 08). No action needed; reported for completeness. NOT modified per read-only mandate.

<details><summary>Evidence</summary>

```
$ journalctl -u arr-queue-reconcile --since 2026-08-02 | grep -iE 'error|failed with': 'Aug 11 16:17:58 API_ERR ConnectionResetError: [Errno 104]' + 'Failed with result exit-code' (1 occurrence)
$ journalctl -u sonarr-backlog-season-search: 'Aug 13 20:17:41 API_ERR TimeoutError: timed out' + 'Failed with result exit-code' (1x); 'Aug 14 06:19:24 SEARCHED series=... commandId=1791932' (recovered)
$ systemctl cat arr-queue-reconcile.service | grep OnFailure -> OnFailure=ntfy-notify@%n.service
```

</details>

### UL15. Monitoring gap: the AdGuard featured-server DNS-rewrite leg (console entry point) has no verification check `known-issue`
**Host:** mini · **Component:** bedrock-connect / AdGuard rewrites · **Auditor:** svc:bedrock-connect · **Work item:** `fix-101`

The console-join feature has two legs: (A) AdGuard rewriting featured-server domains (hivebedrock/mineplex/cubecraft/lbsg/inpvp/galaxite/pixelparadise) to 192.168.10.2, and (B) bedrock-connect answering the serverlist at mini:19132. Leg B IS covered by a consumer check (game-bedrockconnect-serverlist / game-04, passing). Leg A -- the DNS rewrite that actually steers a console to the box -- has NO check in verification/checks.d (grep for hivebedrock/mineplex/cubecraft/featured returns nothing). If a rewrite were silently dropped (AdGuard config edit, or a console using a non-AdGuard resolver), consoles would land on the vendor's real server and the whole feature would break while both the container and game-04 stayed green -- the exact class mandate-2 targets. Risk is bounded: the rewrites live in version control (configs/docker-stack/stacks/adguard) and are backed up, and I verified them live today (dig returns 192.168.10.2). This matches the lane's documented 'console path has zero checks' note. NOT fixed per read-only mandate; recommend a checks.d probe that digs one featured domain against AdGuard and asserts it resolves to 192.168.10.2 (and optionally chains a RakNet ping).

<details><summary>Evidence</summary>

```
$ grep -rln 'hivebedrock|mco.mineplex|featured' foss-setup/verification/checks.d/
NONE: no check asserts the featured-server DNS-rewrite leg

$ sudo grep -niE 'hivebedrock|mineplex|cubecraft' /opt/stacks/adguard/conf/AdGuardHome.yaml
183: - domain: hivebedrock.network
184:   answer: 192.168.10.2
189: - domain: mco.mineplex.com
190:   answer: 192.168.10.2
201: - domain: mco.cubecraft.net
202:   answer: 192.168.10.2
(9 featured domains total, all -> 192.168.10.2; live dig confirms active)
```

</details>

### UL16. BookLogr self-registration remains OPEN (AUTH_ALLOW_REGISTRATION=True) -- known, pending lockdown `known-issue`
**Host:** mini · **Component:** booklogr · **Auditor:** flow:reading-web · **Work item:** `fix-85`

BookLogr allows open self-registration: container env and /opt/stacks/booklogr/.env both = AUTH_ALLOW_REGISTRATION=True (baseline check booklogr-registration-posture passed, recording BOOKLOGR_REG=True match=yes). This is a pre-existing security posture item already found (per lane notes 'KNOWN: booklogr registration OPEN' and booklogr-quirks memory 'registration OPEN pending lockdown'), tracked under the lan-exposure/fix-51 posture check family. The consumer reading feature itself is fully functional; this is an exposure caveat, NOT a break. NOT changed (read-only mandate). Anyone reaching booklogr.tabaska.us/booklogr-api can create an account until lockdown lands.

<details><summary>Evidence</summary>

```
$ (baseline results.json check id=booklogr-registration-posture, task_id=fix-51, status=pass)
output: BOOKLOGR_REG=True envfile=True match=yes
# env source: docker inspect booklogr-api AUTH_ALLOW_REGISTRATION vs /opt/stacks/booklogr/.env -> both True
```

</details>

### UL17. Near-zero adoption / frozen since deploy day — 1 book, 1 user, no writes since 2026-07-28 (user-driven, not a broken poller)
**Host:** mini · **Component:** booklogr-api (books.db) · **Auditor:** svc:booklogr · **Work item:** `fix-85`

Zero-throughput probe (taxonomy 13): the SQLite store holds 1 user, 1 book (id=1, status 'Currently reading', created_on 2026-07-28 19:34:59), 0 notes, 1 reading_session; books.db mtime is 2026-07-28 19:34 — no writes in ~3.5 weeks. This is a user-driven reading tracker (catalog on_demand:false but functionally on-demand), so idle-since-deploy is ADOPTION, not a frozen background poller or write-dead storage — explicitly not filed as a fault. The write path is proven historically (the book+session rows were written post-startup on deploy day) but was NOT re-verified live because that requires an authenticated mutation, barred by the read-only mandate. Flag purely so the operator knows the service is effectively unused (a single smoke-test book) — relevant when deciding whether the open-registration exposure is even worth keeping the app internet-reachable.

<details><summary>Evidence</summary>

```
docker exec booklogr-api python3 sqlite3(file:/app/instance/books.db?mode=ro): tables=[alembic_version,books,files,notes,profiles,reading_sessions,revoked_tokens,tasks,user_settings,users,verification]; books=1 notes=0 reading_sessions=1 users=1
newest books: [(1,'Currently reading','2026-07-28 19:34:59.021514')]
ls -la /app/instance/books.db -> 69632 bytes, mtime Jul 28 19:34 ; host du -sh /opt/stacks/booklogr/data -> 76K
```

</details>

### UL18. STILL-OPEN-VALID / rotation UNPROBED: leaked bookshelf key not confirmably rotated; all consumers green `known-issue`
**Host:** mini · **Component:** bookshelf API key rotation (sec-11) · **Auditor:** cross:open-queue-reality · **Work item:** `sec-11` · *skeptic-confirmed*

sec-11 (rotate bookshelf key leaked in a bmig-06 transcript) cannot be verified read-only — confirming rotation would require comparing to the leaked value, which is forbidden. All bookshelf consumers are green (nas-bookshelf pass, libreseerr-request-rot pass, bookshelf-* reading checks pass), so the service functions, but that does NOT prove the key was rotated. Treat as still-open until an operator confirms rotation. (metadata-search-canary [fail] in the reading domain is unrelated to sec-11.) NOT fixed per read-only mandate.

*Severity adjusted medium→low during adversarial verification.*

*Verify note:* sec-11 is genuinely open (not in progress.json done/reopened), so the finding is not false — but medium overstates it. Fresh probe: the live bookshelf key (32-hex, sha256[:12]=ef9cdc4f6ffe) appears in 0 git-tracked files and 0 commits across ALL history — it was NEVER a public push; the only exposure was the local bmig-06 session transcript (per tasks.json source). This is the identical class as sec-12, a CLOSED sibling security task whose operator decision explicitly states transcript-only leaks are NOT rotated ('never a public push... recommended only if operator treats the transcript as compromised'). Contrast the genuinely git-committed secrets in this same audit (playit idx11, arr keys idx13) that correctly carry high/crit — this one is not committed anywhere (corroborated by the secrets-hygiene lane's repo-wide scan at idx13). All bookshelf consumers verified green tonight (nas-bookshelf 302, libreseerr-request-rot pass, bookshelf-foreign-records NONE); no evidence of abuse. The finding is self-admittedly UNPROBED (rotation undeterminable read-only) so it reproduces no live defect, it restates a tracked-open task. Minor: finding lists host=mini; service+task are host=nas (mini holds only a consumer env var). Operator-intent + transcript-only-vs-public-push + all-green consumers demote this to low.

<details><summary>Evidence</summary>

```
nas-bookshelf [pass]; libreseerr-request-rot [pass]; bookshelf-foreign-records/grab-history [pass]
rotation state: UNPROBED (cannot compare to leaked value)
```

</details>

### UL19. Docker log retention (json-file 3x10m) gives only ~34h of access-log history — per-vhost 5xx audit since 08-02 impossible
**Host:** mini · **Component:** caddy · **Auditor:** svc:caddy · **Work item:** `fix-96`

The audit ask 'scan for level:error and per-vhost 5xx storms since 08-02' can only see back to 2026-08-21 ~13:40 EDT: json-file driver with max-file:3/max-size:10m rotates ~19.8k lines in ~34h. Within that window logs are quiet (11 error lines, no storms, --since worked without NUL aborts), but any earlier 5xx storm is unrecoverable. If per-vhost error history matters for future audits, a larger max-size or log shipping would be needed. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'docker inspect caddy --format "{{.HostConfig.LogConfig.Type}} {{.HostConfig.LogConfig.Config}}"'
json-file map[max-file:3 max-size:10m]
$ ssh mini 'docker logs caddy 2>&1 | head -1 | cut -c1-160'
{"level":"info","ts":1787319614.32... (= 2026-08-21 ~13:40 EDT)
$ ssh mini 'docker logs caddy 2>&1 | wc -l'
19821
$ ssh mini 'docker logs caddy --since 2026-08-02T00:00:00 2>&1 | grep -c "\"level\":\"error\""'
11
```

</details>

### UL20. catalog-vhost-parity failing: 'unsloth' and 'principal-ai' vhosts missing catalog rows (known, fix-68 reopen) `known-issue`
**Host:** mini · **Component:** checks.d/git-hygiene.yaml:catalog-vhost-parity · **Auditor:** meta:git-hygiene · **Work item:** `fix-97`

Known issue: maps to fix-68 in today's baseline. Re-verified from the 10:29 EDT results.json: two live Caddy vhosts lack service-catalog.yaml rows. 'unsloth' = Unsloth Studio (lai-28, deployed 2026-08-21) missing its catalog row — this matches the memory-documented process gap 'deploys skip coverage-manifest + wiki regen'. 'principal-ai' = the other agent session's in-flight work (modified Caddyfile observed in git status of this repo + /opt/stacks) — observed in-flight drift, deliberately not filed as a violation per lane rules. The check is consumer-grade and correctly catching both. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
mini /var/lib/verification/results.json (run 2026-08-22T10:29:50-04:00): catalog-vhost-parity fail dur=0.36 "VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth'] (live Caddy vhost, no catalog row/url — add it)"
local: git status shows M foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile (in-flight session)
```

</details>

### UL21. dotfiles-content-clean cannot distinguish 'no drift' from 'chezmoi absent/broken' — silent-green edge
**Host:** mini · **Component:** checks.d/git-hygiene.yaml:dotfiles-content-clean · **Auditor:** meta:git-hygiene · **Work item:** `fix-100`

The cmd computes hunks via `chezmoi diff 2>/dev/null | grep -c '^@@'` on both mini and rig. If chezmoi is uninstalled, or `chezmoi diff` errors (missing source dir, config break), stderr is discarded, the pipe is empty, and `grep -c` prints 0 — indistinguishable from a genuinely clean state, so the check passes green forever (taxonomy class 2: green-but-broken masking). Verified live today that chezmoi IS present on both hosts (mini /usr/local/bin/chezmoi, rig /usr/bin/chezmoi), so the current pass (mini_hunks=0 rig_hunks=0 at 10:29 EDT) is genuine — but the check offers no protection against the tool itself rotting. Fix idea (NOT applied per read-only mandate): capture chezmoi's exit status before the grep, or assert `command -v chezmoi` on both legs. Check is otherwise consumer-grade (content parity, umask-aware design is sound).

<details><summary>Evidence</summary>

```
repo cmd (foss-setup/verification/checks.d/git-hygiene.yaml:203): m=$(chezmoi diff 2>/dev/null | grep -c '^@@' || true)
demo: $ printf '' | grep -c '^@@'  ->  0 (same as clean)
live: ssh mini 'command -v chezmoi' -> /usr/local/bin/chezmoi
ssh rig 'command -v chezmoi' -> /usr/bin/chezmoi
10:29 run results.json: dotfiles-content-clean pass dur=0.38 'mini_hunks=0 rig_hunks=0\nDOTFILES-CONTENT-CLEAN'
```

</details>

### UL22. git-stacks-clean and git-foss-setup-clean failing (3 dirty each) — known in-flight session drift (docker-12 / glue-08) `known-issue`
**Host:** mini · **Component:** checks.d/git-hygiene.yaml:git-stacks-clean+git-foss-setup-clean · **Auditor:** meta:git-hygiene · **Work item:** `fix-80`

Both clean-tree checks fail with 3 dirty entries each in the 10:29 EDT run, mapped in today's baseline to docker-12 (git-stacks-clean) and glue-08 (git-foss-setup-clean). This is the documented in-flight work of another agent session (modified Caddyfile + homepage services.yaml in both /opt/stacks and the mirror, plus untracked principal-ai-engineer-track site dir) — reported as observed drift per lane rules, not filed as a violation, not committed or reverted. The checks themselves are consumer-grade (direct porcelain assertion of the anti-drift invariant) and working.

<details><summary>Evidence</summary>

```
mini /var/lib/verification/results.json (run 2026-08-22T10:29:50-04:00):
git-stacks-clean fail dur=0.03 '3'
git-foss-setup-clean fail dur=0.04 '3'
local repo git status: M foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile, M foss-setup/configs/docker-stack/stacks/homepage/config/services.yaml
```

</details>

### UL23. manifest-image-purity failing: phantom triliumnext/trilium in compose-images.txt (known, fix-41 reopen) — re-verified, not worsened `known-issue`
**Host:** mini · **Component:** checks.d/git-hygiene.yaml:manifest-image-purity · **Auditor:** meta:git-hygiene · **Work item:** `fix-80`

Known issue: maps to fix-41 in today's pre-existing failure baseline. Re-verified from the 10:29 EDT results.json: still exactly one phantom — `triliumnext/trilium` remains in hosts/macmini/compose-images.txt after the 2026-08-14 Trilium retirement (data parked at mini /opt/retired/trilium-20260814), but no live top-level compose references it. Single stable phantom, no new phantoms, no unlisted live images — not silently worsened. The check itself is consumer-grade and doing its job (100%-coverage tripwire caught a missed retire-side manifest update). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
mini /var/lib/verification/results.json (run 2026-08-22T10:29:50-04:00): manifest-image-purity fail dur=0.27 'MANIFEST-PHANTOM-IMAGES: [triliumnext/trilium] in compose-images.txt but in no live top-level compose (pollution or a re...'
```

</details>

### UL24. Stale accepted-ids baseline: all 8 'permanently cookie-gated' casualties have since recovered, allowlist is now dead weight that would mask a re-stranding
**Host:** mini · **Component:** checks.d/media-aux.yaml: pinchflat-stuck-media · **Auditor:** meta:media-aux · **Work item:** `fix-100`

The check excludes ids 409/702/895/915/939/1008/1333/3076 as accepted permanent LOGIN_REQUIRED casualties, and the in-file comment asserts 'only sign-in cookies would recover them and cookies are a deliberate non-goal'. Live DB state 2026-08-22 contradicts this: all 8 rows now have media_filepath set (downloaded) and last_error NULL — total_botcheck_stuck_incl_accepted=0, meaning zero media items in the whole DB currently match the stranded predicate. YouTube evidently released the gate (or the bgutil chain, now http-1.3.1, got past it). The exclusion list is stale in the SAFE direction today, but it creates a blind spot: if any of these exact 8 ids becomes bot-check-stranded AGAIN (e.g., re-download after file loss, or YouTube re-escalation), the check silently accepts it, and the check name/comment/runbook narrative ('8 accepted', fix-67/SM20) no longer describes reality. Cheap fix when convenient: drop the id exclusion (or shrink expect to plain 0) and update the comment. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini python3 sqlite3 /opt/stacks/pinchflat/config/db/pinchflat.db:
select id, media_filepath is not null, substr(coalesce(last_error,'NULL'),1,40) from media_items where id in (409,702,895,915,939,1008,1333,3076)
accepted_ids_present=8
(409, 1, 'NULL') (702, 1, 'NULL') (895, 1, 'NULL') (915, 1, 'NULL') (939, 1, 'NULL') (1008, 1, 'NULL') (1333, 1, 'NULL') (3076, 1, 'NULL')
select count(*) ... last_error like '%Sign in to confirm%' and media_filepath is null -> total_botcheck_stuck_incl_accepted=0
```

</details>

### UL25. empty+empty still passes green although the library is now known-populated (8,364 roms) — a simultaneous two-sided wipe would be invisible
**Host:** mini · **Component:** checks.d/media-aux.yaml: romm-content-ingest · **Auditor:** meta:media-aux · **Work item:** `fix-100`

The check's else-branch emits ROMM_CONSISTENT for files=0 AND roms=0, a documented allowance from the pre-import era ('back when the shelf was bare'). The shelf has not been bare since 2026-07-20: live DB shows exactly 8,364 roms today. Under the current logic, a mounted-but-emptied share combined with a wiped/fresh romm DB (e.g., volume recreated, mariadb reinitialized) passes green — precisely the Immich-class vanished-library scenario this M18 guard exists for, just hit on both sides at once. Since the populated baseline is now stable, adding a floor (e.g., fail if roms < some sanity minimum, or f=0&&r=0 -> ROMM_BOTH_EMPTY fail) would close the blind spot at zero flap risk. Single-sided failures ARE still caught (NOT_INGESTED / VANISHED branches verified present). Mount-down correctly fails (GAMES_MOUNT_DOWN does not match ^ROMM_CONSISTENT). NAS-side find not re-walked live (NAS under heavy IO; check passed in today's 10:29 daily run — not among the 26 baseline failures). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'mountpoint /mnt/share/Games' -> /mnt/share/Games is a mountpoint
ssh mini docker exec romm-db mariadb ... 'select count(*) from roms' -> 8364
check source (media-aux.yaml lines 132-134): elif [ "$f" -eq 0 ] && [ "$r" -gt 0 ]; then echo "ROMM_LIBRARY_VANISHED..."; else echo "ROMM_CONSISTENT files=$f roms=$r"; fi  — f=0,r=0 falls to else
```

</details>

### UL26. Retire-side coverage-tripwire miss: image manifest still lists retired triliumnext/trilium `known-issue`
**Host:** mini · **Component:** compose-images.txt (image-purity manifest) · **Auditor:** cross:coverage-tripwire · **Work item:** `fix-80`

Adjacent to the container coverage manifests: manifest-image-purity FAILs because compose-images.txt still references triliumnext/trilium even though Trilium was fully retired 2026-08-14 (and is correctly ABSENT from mini.containers — the container-manifest retire leg was done). This is the mirror image of the coverage tripwire: the deploy/retire leg updated the container manifest but not the image manifest. Confirms the standing 'update the manifest on every retire' mandate was only half-applied for the Trilium retirement. Covered by fix-41 (manifest-image-purity) in today's baseline. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
results.json manifest-image-purity: status=fail output="MANIFEST-PHANTOM-IMAGES: [triliumnext/trilium] in compose-images.txt ..."
$ grep -c trilium foss-setup/verification/coverage/mini.containers → 0 (container manifest correctly clean)
```

</details>

### UL27. Secondary liveness-leaning checks — version/status scrapes standing in for consumer probes
**Host:** mini · **Component:** consumer-check coverage (mealie/tautulli/wallabag) · **Auditor:** cross:coverage-tripwire · **Work item:** `fix-100`

Beyond the flagged four, three more mini services have only a version/status-endpoint check rather than a true consumer probe: mealie (mini-mealie scrapes /api/app/about version), tautulli (mini-tautulli asserts /status result:success), wallabag (mini-wallabag greps /api/info appname). Each proves the API process answers but not the consumer function (a recipe retrievable / a Plex history row recorded / an article saved-and-readable). Lower stakes than the flagged four and each has a Homepage tile + Kuma monitor, so surface coverage is fine; only the depth is thin. Reported for completeness of the coverage cross-cut. NOT fixed per read-only mandate. Note navidrome's bare-200 mini-navidrome is NOT a gap — it is backed by 6 additional consumer checks (library-present, scan-fresh, recycle-rows, backup-armed/fresh).

<details><summary>Evidence</summary>

```
results.json check cmds:
mini-mealie: curl -sf :9000/api/app/about | grep -o '"version":"v[0-9]...'
mini-tautulli: curl -sf :8181/status | grep -o '"result": "success"'
mini-wallabag: curl -sf :8085/api/info | grep -o '"appname":"wallabag"'
```

</details>

### UL28. Three checks fail OPEN: transport/daemon failure yields empty output which the cmd converts to a passing token
**Host:** mini · **Component:** containers-health-mini / containers-health-nas / soularr-not-crashlooping · **Auditor:** meta:docker-fleet · **Work item:** `fix-100`

Structural false-pass hazard in 3 of the 9 checks. (1) containers-health-mini: if the mini docker daemon is down, both `docker ps -a` calls error to stderr, $bad is empty, and the check echoes HEALTH_OK -> false pass. (2) containers-health-nas: if ssh to NAS fails or NAS_SUDO_PASSWORD rots, the whole $( ) is empty (stderr suppressed by 2>/dev/null), $bad empty -> HEALTH_OK false pass. (3) soularr-not-crashlooping: on ssh/sudo failure grep -c counts 0 over empty input -> 'fatal_errors=0' false pass; it also cannot distinguish healthy-quiet logs from a hung/zero-output job (taxonomy 13 zero-throughput green — though import freshness is separately covered by nas-soularr-failed-imports-fresh, fix-40). Mitigation exists: in every such outage the sibling containers-manifest-* check on the same host fails CLOSED (empty container list vs manifest = loud diff), so a host/daemon/auth outage still surfaces — hence low, not medium. containers-health-rig and systemd-failed-rig are transport-fail-closed (host: rig, ssh failure = empty stdout = expect no-match = fail); only a rig-local docker-daemon error false-greens containers-health-rig. Fix pattern: assert a sentinel from the far side (e.g. require the docker/ssh call itself to echo a marker) before declaring HEALTH_OK. NOT fixed per read-only mandate. Not covered by any open task in the dedup list.

<details><summary>Evidence</summary>

```
docker-fleet.yaml containers-health-mini cmd: bad=$(docker ps -a --filter health=unhealthy ... ); if [ -z "$bad" ]; then echo HEALTH_OK; ... (no guard on docker exit status)
containers-health-nas cmd: bad=$(printf ... | ssh ... nas "sudo -S ..." 2>/dev/null); if [ -z "$bad" ]; then echo HEALTH_OK (ssh failure -> empty -> HEALTH_OK)
soularr cmd: n=$(... ssh nas "...docker logs soularr --since 2h 2>&1" 2>/dev/null | grep -c 'Fatal error'); echo "fatal_errors=$n" (ssh failure -> grep -c over empty = 0 -> pass)
check runner (checks_runner.py:101-103): ok = re.search(check["expect"], stdout, re.M) — expect only needs the token to appear in stdout, exit codes ignored when 'expect' present
```

</details>

### UL29. cwa-upstream-cve-catchup conflates transient GitHub-API failure with its 'good news, migrate off the fork' failure semantics
**Host:** mini · **Component:** cwa upstream watch (check cwa-upstream-cve-catchup) · **Auditor:** meta:reading · **Work item:** `fix-100`

The check's contract is inverted by design (fail = upstream shipped the CVE fix, time to migrate back — the name says 'fail = migrate back'). But an unauthenticated GitHub API rate-limit or outage returns JSON without tag_name → tag='' → int('') raises ValueError → prints 'UPSTREAM_CHECK_ERROR tag=…' → expect '^UPSTREAM_STALLED' misses → the check goes red with the same alert identity whose name instructs 'migrate back'. An operator triaging from the check name/alert (not the raw output line) gets the opposite of the truth on a transient API blip. Cheap hardening: retry once, or emit UPSTREAM_STALLED_UNVERIFIED on API error and let a streak-based rule catch persistent error states, or at minimum rename so the name doesn't assert what a failure means. Baseline itself verified current live: upstream crocodilestick latest release is still v4.0.6 (published 2026-02-04, stalled >6 months), so the >(4,0,6) threshold and today's UPSTREAM_STALLED 4.0.6 pass are correct. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/reading.yaml:105-121 → name: 'upstream crocodilestick CWA still stalled pre-CVE-fix (fail = migrate back)'; cmd python parses tag_name, ValueError path prints UPSTREAM_CHECK_ERROR and exits 0; expect: '^UPSTREAM_STALLED'
curl -s https://api.github.com/repos/crocodilestick/calibre-web-automated/releases/latest | python3 → tag_name: v4.0.6 | published: 2026-02-04T23:41:12Z
Today's daily results.json: cwa-upstream-cve-catchup pass 'UPSTREAM_STALLED 4.0.6'
```

</details>

### UL30. diun monitoring is liveness-only — no throughput/consumer check (mandate-2 gap)
**Host:** mini · **Component:** diun · **Auditor:** svc:diun-mini · **Work item:** `fix-100`

The only checks referencing diun are alert-diun-mini-up (cmd: docker inspect -f '{{.State.Health.Status}}' diun) and alert-diun-nas-up (docker inspect .State.Status) in checks.d/alerting.yaml — both assert container liveness only. A silently-frozen poller (container healthy but scan cron stalled / notifier endpoint rotted) would still pass these, exactly the taxonomy-13 frozen-green risk. There is no consumer-grade check asserting (a) diun scanned within ~26h ('Next run'/'Jobs completed' recency) or (b) that ntfy topic 'diun' is reachable. diun IS correctly present in coverage manifests (mini.containers + nas.containers) and has an accurate service-catalog row (Infrastructure & Ops, ui:false, notes 'Image-update notifier → ntfy'); no homepage tile is correct for a headless notifier. NOT fixed per read-only mandate. Suggested (for a future resolve): a check asserting diun's last 'Jobs completed' log line is <26h old. No open task currently covers this specifically.

<details><summary>Evidence</summary>

```
grep -rniE diun foss-setup/verification/checks.d/ => alerting.yaml:28 cmd: docker inspect -f '{{.State.Health.Status}}' diun ; alerting.yaml:40 cmd: sudo -n /usr/local/bin/docker inspect -f '{{.State.Status}}' diun
/tmp/verify-audit-uc/results.json => alert-diun-mini-up::pass (msg 'healthy'), alert-diun-nas-up::pass (msg 'running')
grep diun foss-setup/verification/coverage/ => mini.containers:10:diun, nas.containers:10:diun
```

</details>

### UL31. STILL-OPEN-VALID (lower risk): 3 docker networks still auto-assigned in 192.168 space, but none overlap VLAN 10/20 `known-issue`
**Host:** mini · **Component:** docker subnet squat / sys-docker-subnet-squat (ha-19) · **Auditor:** cross:open-queue-reality · **Work item:** `ha-19`

ha-19's original VLAN-20 collision (paperless/kometa) was fixed, but the check still fails: 3 docker bridge networks squat 192.168 space — open-terminal_default 192.168.80.0/20, scrutiny-collector_default 192.168.48.0/20, terraria_default 192.168.64.0/20. None overlap Trusted (192.168.10.0/24) or IoT VLAN20 (192.168.20.0/24), and sys-docker-vlan-overlap PASSES — so this is cosmetic/hygiene (daemon.json default-address-pools not applied to these recreated stacks), not an active collision. The remaining ha-19 UniFi work (per-device pinholes, fixed IPs, iot-local/iot-cloud groups) is separate and unprobeable from here. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
sys-docker-subnet-squat [fail]: out='3'
live: 192.168.80.0/20 open-terminal_default; 192.168.48.0/20 scrutiny-collector_default; 192.168.64.0/20 terraria_default
sys-docker-vlan-overlap [pass]
```

</details>

### UL32. runbook value 'wiki/runbooks/verification.md' does not resolve to a repo file (actual: wiki/docs/runbooks/verification.md)
**Host:** mini · **Component:** docker-fleet.yaml runbook metadata · **Auditor:** meta:docker-fleet · **Work item:** `fix-99`

All 9 checks carry runbook: wiki/runbooks/verification.md, but no foss-setup/wiki/runbooks/ directory exists — the real runbook is foss-setup/wiki/docs/runbooks/verification.md (114 lines, exists). The runbook field is carried into results/alerts as responder metadata (checks_runner.py line 229), so a responder pasting the literal path finds nothing. This is a repo-WIDE split convention, not unique to this file: ~24 checks use 'wiki/runbooks/verification.md' vs ~7 using 'wiki/docs/runbooks/verification.md' (plus rig.md 32, docker.md 27, nas.md 16 in the short form). The short form reads as the published mkdocs site path (docs/ is the served root, so wiki.tabaska.us/runbooks/verification/ works), making it ambiguous-but-resolvable by a human; still, half the fleet's runbook pointers are not literal file paths and the two conventions coexist for the SAME runbook. Cheap fix: normalize all runbook values to the wiki/docs/... repo path (or document the site-path convention in verification/README.md). No open task covers this. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ls foss-setup/wiki/runbooks/ -> No such file or directory
$ grep -c . foss-setup/wiki/docs/runbooks/verification.md -> 114
$ grep -h 'runbook:' foss-setup/verification/checks.d/*.yaml | sort | uniq -c | sort -rn | head
  32 runbook: wiki/runbooks/rig.md
  27 runbook: wiki/runbooks/docker.md
  24 runbook: wiki/runbooks/verification.md
  18 runbook: wiki/docs/runbooks/git-hygiene.md
   7 runbook: wiki/docs/runbooks/verification.md
```

</details>

### UL33. ha-19 residual: 3 docker bridge networks squat 192.168.0.0/16 (count unchanged, no routable-VLAN overlap) `known-issue`
**Host:** mini · **Component:** docker-networking · **Auditor:** triage:sys-docker-subnet-squat · **Work item:** `ha-19`

Check sys-docker-subnet-squat (task ha-19, expect ^0$) returns 3. The three offending mini docker bridge networks are open-terminal_default (192.168.80.0/20, created 2026-08-06, 1 container), scrutiny-collector_default (192.168.48.0/20, created 2026-07-23, 1 container), and terraria_default (192.168.64.0/20, created 2026-07-28, 1 container). This is the documented ha-19 open task: docker bridge nets overlapping 192.168/16 pending the IoT VLAN migration. RE-VERIFIED NOT WORSENED — the 2026-08-09 triage-2026-08-09.md already diagnosed 'Three Docker networks on mini are configured with subnets overlapping the 192.168.0.0/16 LAN range'; the count is identical (3) and open-terminal (created 2026-08-06 during the lai buildout) predates that record, so it belongs to the same known set rather than being a new squat. The check's own inline comment (system.yaml line 89) names only 2 known squats (scrutiny-collector + terraria) and omits open-terminal — minor stale-comment doc-nit, not a live regression. NO LIVE IMPACT: the CONSUMER-end crit sibling sys-docker-vlan-overlap (fix-66) PASSED with VLAN_OVERLAP_OK n=22 — none of the 22 docker subnets overlaps the routable Trusted (192.168.10.0/24) or IoT (192.168.20.0/24) VLANs, so mini smart-home/IoT routing is not blackholed. Broad-hygiene warn only. NOT fixed per read-only audit mandate; real remediation is the ha-19 IoT VLAN migration (renumber these bridges out of 192.168/16, e.g. into 172.16/12).

<details><summary>Evidence</summary>

```
$ (mini) for n in $(docker network ls -q); do sub=$(docker network inspect "$n" --format "{{range .IPAM.Config}}{{.Subnet}} {{end}}"); name=$(docker network inspect "$n" --format "{{.Name}}"); echo "$sub" | grep -q '^192\.168\.' && echo "NAME=$name SUBNET=$sub"; done
NAME=open-terminal_default SUBNET=192.168.80.0/20
NAME=scrutiny-collector_default SUBNET=192.168.48.0/20
NAME=terraria_default SUBNET=192.168.64.0/20

$ (mini) docker network inspect <each> --format 'Created={{.Created}} ... Containers={{len .Containers}}'
open-terminal_default: Created=2026-08-06 13:36:18 Subnet=192.168.80.0/20 Driver=bridge Containers=1
scrutiny-collector_default: Created=2026-07-23 15:56:39 Subnet=192.168.48.0/20 Driver=bridge Containers=1
terraria_default: Created=2026-07-28 14:03:14 Subnet=192.168.64.0/20 Driver=bridge Containers=1

# results.json (today's audit-safe run):
sys-docker-subnet-squat :: fail :: '3'   (expect ^0$)
sys-docker-vlan-overlap :: pass :: 'VLAN_OVERLAP_OK n=22'   (fix-66 crit sibling — no routable VLAN swallowed)

# history — mini /var/lib/verification/triage-2026-08-09.md line 222:
### sys-docker-subnet-squat (sev warn, task ha-19 ...)
"diagnosis": "Three Docker networks on mini are configured with subnets overlapping the 192.168.0.0/16 LAN range."  <-- count already 3 on 2026-08-09, unchanged
```

</details>

### UL34. Monitoring check mini-dockge is liveness-only (curl / -> 200), not consumer-grade
**Host:** mini · **Component:** dockge · **Auditor:** svc:dockge · **Work item:** `fix-100`

The only verification check for dockge (verification/checks.d/mini-services.yaml id: mini-dockge, task_id docker-01) asserts curl http://localhost:5001/ == 200. That confirms the SPA shell serves but does not exercise the consumer path (auth/login enforced, socket.io backend, DB reachable) — per Standing Mandate 1/2 (consumer-grade coverage) this is a minor gap. Practical risk is low: dockge is an interactive admin SPA where a 200 on / plus a healthy container is close to the consumer surface, and DB health is otherwise self-evident. NOT fixed per read-only mandate; suggest a probe hitting the login/setup-status endpoint. No open task covers this specific gap.

<details><summary>Evidence</summary>

```
checks.d/mini-services.yaml:255 id: mini-dockge / cmd: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:5001/ / expect: '^200$' / severity: warn / task_id: docker-01
```

</details>

### UL35. catalog-vhost-parity FAIL: unsloth + principal-ai live vhosts absent from service-catalog `known-issue`
**Host:** mini · **Component:** edge / service catalog parity · **Auditor:** flow:edge-dns · **Work item:** `fix-97`

KNOWN (fix-68 catalog-vhost-parity). Live Caddy serves unsloth.tabaska.us and principal-ai.tabaska.us but neither has a service-catalog.yaml row. principal-ai is the in-flight session's work (modified /opt/stacks/caddy/caddy/Caddyfile + homepage/config/services.yaml, untracked site/principal-ai-engineer-track/) -- reported as OBSERVED in-flight drift per lane-context, NOT a violation, not committed/reverted. unsloth is a genuine residual: lai-28 shipped 2026-08-19 but the catalog row was never added (process gap: deploys skip catalog/coverage/wiki regen). The uncommitted stacks tree also keeps docker-12/git-stacks-clean red. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
results.json catalog-vhost-parity (fix-68) FAIL -> VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth']
ssh mini git -C /opt/stacks/caddy status --short -> ' M caddy/Caddyfile' ' M ../homepage/config/services.yaml' '?? site/principal-ai-engineer-track/'
live caddy admin config -> 69 vhosts incl. unsloth.tabaska.us + principal-ai.tabaska.us (both serve 200 with app body)
```

</details>

### UL36. git-stacks-clean FAIL is exactly the in-flight WIP — no other unexpected /opt/stacks dirtiness `known-issue`
**Host:** mini · **Component:** git-control-plane / /opt/stacks working tree (docker-12 git-stacks-clean) · **Auditor:** flow:git-control-plane · **Work item:** `fix-80`

Spot-verified the docker-12 FAIL (3 dirty lines) is 100% attributable to the concurrent operator session flagged in lane-context: modified caddy/caddy/Caddyfile + homepage/config/services.yaml and untracked caddy/site/principal-ai-engineer-track/index.html. Nothing else is dirty in /opt/stacks. Both modified files are byte-parity with the mac repo mirror (anti-drift discipline held). Reported as observed in-flight drift per mandate — NOT filed as a violation, NOT reverted (read-only). Self-resolves when the operator commits. known_issue: docker-12 baseline (in-flight session).

<details><summary>Evidence</summary>

```
mini$ sudo git -C /opt/stacks status --porcelain:
 M caddy/caddy/Caddyfile
 M homepage/config/services.yaml
?? caddy/site/principal-ai-engineer-track/
(--untracked-files=all -> caddy/site/principal-ai-engineer-track/index.html)
sha256 parity live==mirror for both modified files (dc589bad17eacce4 / 14f3cb1a6949b3c0)
```

</details>

### UL37. catalog-vhost-parity FAIL is exactly the two known vhosts (principal-ai in-flight WIP + unsloth lai-28) missing catalog rows `known-issue`
**Host:** mini · **Component:** git-control-plane / Caddy vhost <-> service-catalog parity (fix-68) · **Auditor:** flow:git-control-plane · **Work item:** `fix-97`

catalog-vhost-parity FAIL is a doc-catalog lag, not a broken vhost. Live Caddyfile has two vhosts with no service-catalog row: principal-ai.{$DOMAIN} (line 565, the in-flight WIP static site) and unsloth.{$DOMAIN} (line 315, lai-28 Unsloth Studio, already e2e-green via results unsloth-studio-e2e). forgejo already has a catalog row (line 610). Both gaps are expected: principal-ai self-resolves when the operator commits the in-flight work; unsloth needs a catalog row added under fix-68. Not fixed (read-only). known_issue: fix-68.

<details><summary>Evidence</summary>

```
results catalog-vhost-parity: "VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth']"
mini$ sudo grep -niE 'principal|unsloth' /opt/stacks/caddy/caddy/Caddyfile -> 315: unsloth.{$DOMAIN} { ; 565: principal-ai.{$DOMAIN} {
mac$ grep -niE 'forgejo|principal|unsloth' service-catalog.yaml -> 610: - name: forgejo (no principal/unsloth rows)
```

</details>

### UL38. trilium phantom persists in origin/forgejo compose-images.txt (service genuinely retired) — downstream of the stale export checkout `known-issue`
**Host:** mini · **Component:** git-control-plane / compose-images manifest (fix-41 manifest-image-purity) · **Auditor:** flow:git-control-plane · **Work item:** `fix-80`

manifest-image-purity FAIL is real but cosmetic: the committed compose-images.txt in origin/forgejo main (ab548032) still lists triliumnext/trilium:v0.104.1, yet trilium is genuinely gone (no container, no /opt/stacks/trilium dir — retired 2026-08-14). The live-regenerated manifest in /opt/foss-setup already has NO trilium, but that clean version never gets committed (see finding above), so the phantom sticks in origin. Verified the ACTUAL service is retired, so this is stale-doc drift not a live problem. Not fixed (read-only). known_issue: fix-41.

<details><summary>Evidence</summary>

```
results manifest-image-purity: 'MANIFEST-PHANTOM-IMAGES: [triliumnext/trilium] in compose-images.txt'
mac$ grep -i trilium foss-setup/hosts/macmini/compose-images.txt (==origin ab548032) -> triliumnext/trilium:v0.104.1
mini$ sudo grep -i trilium /opt/foss-setup/.../compose-images.txt (live regen) -> NONE-in-worktree
mini$ docker ps -a --filter name=trilium -> (empty) ; ls -d /opt/stacks/trilium -> no such dir
```

</details>

### UL39. The 'in-flight' WIP is actually 5 days old (untouched since 2026-08-17 19:02 EDT) — stalled uncommitted, not active `known-issue`
**Host:** mini · **Component:** git-hygiene / /opt/stacks · **Auditor:** triage:git-stacks-clean · **Work item:** `fix-80`

All three dirty paths have mtimes of 2026-08-17 19:02 EDT, and triage history confirms git-stacks-clean first failed on the 2026-08-18 daily run (absent from triage-2026-08-17.md, present 08-18 through 08-22). The lane context describes this as work happening 'RIGHT NOW', but nothing has touched these files in 5 days. Not worsened — the entry count and file set are identical to this morning's baseline — but a live-deployed Caddy vhost + homepage tile sitting uncommitted this long is a drift-window risk: a caddy/homepage stack rebuild from git would silently drop the principal-track vhost and tile. Human follow-up: the owning session should commit+push both sides (live /opt/stacks and the repo mirror) or be declared abandoned. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'sudo stat -c "%y %n" /opt/stacks/caddy/caddy/Caddyfile /opt/stacks/homepage/config/services.yaml /opt/stacks/caddy/site/principal-ai-engineer-track'
2026-08-17 19:02:49.712652598 -0400 /opt/stacks/caddy/caddy/Caddyfile
2026-08-17 19:02:52.468767639 -0400 /opt/stacks/homepage/config/services.yaml
2026-08-17 19:02:32.455932249 -0400 /opt/stacks/caddy/site/principal-ai-engineer-track

$ ssh mini 'grep -c "git-stacks-clean" /var/lib/verification/triage-2026-08-17.md'
0
$ ssh mini 'grep -l "git-stacks-clean" /var/lib/verification/triage-*.md'
(hits: triage-2026-08-18.md, -19, -21, -22)
```

</details>

### UL40. git-stacks-clean fail = exactly the 3 known in-flight WIP entries (principal-ai-engineer-track session); nothing else dirty, no unpushed commits `known-issue`
**Host:** mini · **Component:** git-hygiene / /opt/stacks · **Auditor:** triage:git-stacks-clean · **Work item:** `fix-80`

Re-verified live 2026-08-22 evening: /opt/stacks porcelain shows precisely the known in-flight set — modified caddy/caddy/Caddyfile (+9 lines), modified homepage/config/services.yaml (+5 lines), untracked caddy/site/principal-ai-engineer-track/ (single index.html). Diffstat is insertions-only (14+, 0-), consistent with a new vhost + homepage tile for the principal-track page. sha256 of both live files byte-matches the Mac repo working-tree mirrors under foss-setup/configs/docker-stack/stacks/, so the anti-drift pairing is symmetric (same edit staged-uncommitted on BOTH sides, not one-sided drift). origin/main..HEAD is empty — zero unpushed commits; HEAD c70cb83 (2026-08-17) is pushed. Maps to task docker-12 per today's reopen bridge; per lane rules this is observed in-flight drift, NOT filed as a violation, NOT committed or reverted (read-only mandate).

<details><summary>Evidence</summary>

```
$ ssh mini 'sudo git -C /opt/stacks status --porcelain'
 M caddy/caddy/Caddyfile
 M homepage/config/services.yaml
?? caddy/site/principal-ai-engineer-track/

$ ssh mini 'sudo git -C /opt/stacks log --oneline origin/main..HEAD'
(empty, exit 0)

$ ssh mini 'sudo git -C /opt/stacks diff --stat'
 caddy/caddy/Caddyfile         | 9 +++++++++
 homepage/config/services.yaml | 5 +++++
 2 files changed, 14 insertions(+)

$ sha256 live vs Mac mirror:
MATCH  caddy/caddy/Caddyfile
MATCH  homepage/config/services.yaml

$ ssh mini 'sudo find /opt/stacks/caddy/site/principal-ai-engineer-track -maxdepth 1'
/opt/stacks/caddy/site/principal-ai-engineer-track
/opt/stacks/caddy/site/principal-ai-engineer-track/index.html
```

</details>

### UL41. Dead-man check abs-ipod-stage-rig has no alert channel assigned — a down flip pages nobody natively
**Host:** mini · **Component:** healthchecks · **Auditor:** svc:healthchecks · **Work item:** `fix-76`

15 of 16 checks are wired to the ntfy channel; abs-ipod-stage-rig (daily iPod ABS staging job, pings=31, last ping 16.7h ago) has zero channels. Self-hosted Healthchecks has no SMTP, so ntfy is the only working native alert path — if this job dies, Healthchecks flips it down silently. Backstop exists: the daily crit check alert-healthchecks-none-down enumerates ALL down checks regardless of channel, so detection is delayed up to ~24h rather than lost. Adjacent to open task fix-76 (alert delivery proof) but not covered by it — this is a channel-assignment gap, not a delivery-proof gap. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker exec healthchecks python3 /opt/healthchecks/manage.py shell -v 0 -c "from hc.api.models import Check; ns=[c.name for c in Check.objects.all() if c.channel_set.count()==0]; print(...)"'
→ no_channel=abs-ipod-stage-rig

alert-healthchecks-checks-defined probe → checks=16 ntfy=1 (only 1 ntfy channel exists; 15/16 checks attached)
```

</details>

### UL42. fix-69 mini scratch hygiene FAIL — but no auth-material component `known-issue`
**Host:** mini · **Component:** host hygiene / scratch · **Auditor:** cross:secrets-hygiene · **Work item:** `fix-96`

mini-scratch-hygiene FAILs: scratch7d=103 (threshold <=10) and staleresults14d=6. Reassuring for this lane: the secrets sub-count = 0 (no *.cookies/*.pem/id_* auth material piling in /tmp). So the failure is aged scratch/stale results, not credential leakage. Known open task fix-69 (baseline). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
# from results.json (mini-scratch-hygiene, fix-69):
output: 'secrets=0 scratch7d=103 staleresults14d=6\nHYGIENE_DIRTY'
```

</details>

### UL43. 254 aged scratch files in /tmp (fix-69 mini-scratch-hygiene) `known-issue`
**Host:** mini · **Component:** host-mini · **Auditor:** svc:host-mini · **Work item:** `fix-96`

254 files older than 24h under /tmp, including July-27/28 agent/verification leftovers (n8n.sqlite, n8n_db.sqlite, dbc.sqlite, labels.json, mr-checks.json, rigrun.json, cf.html, shot.png, etc.) — some potentially auth-material, so contents NOT read per no-secrets mandate. The 'no auth-material or aged scratch piling up in /tmp' check FAILS. Not materially worsened vs baseline. The sanctioned audit state dir /tmp/verify-audit-uc (13M, btabaska-owned, fresh Aug 23 15:18) is expected. Tracked fix-69. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
find /tmp -maxdepth 2 -mmin +1440 -type f | wc -l -> 254
find /tmp -maxdepth 1 -mmin +1440 -printf '%TY-%Tm-%Td %f\n' -> 2026-07-27 dbc.sqlite / n8n.sqlite / labels.json / mr-checks.json ...
results.json: FAIL 'mini: no auth-material or aged scratch piling up in /tmp or the verification state dir (SL40/SL41)'
```

</details>

### UL44. Kernel/libc reboot pending 45d (fix-74) — SL7 check on the 45→46d flip edge `known-issue`
**Host:** mini · **Component:** host-mini · **Auditor:** svc:host-mini · **Work item:** `fix-74`

/var/run/reboot-required present since Aug 21 06:29 for linux-image-5.15.0-190 (+186/187) and libc6; running kernel is 5.15.0-185. Reboot is deliberately operator-scheduled for the 4-7AM window (mini hosts DNS/Caddy/alerting/verification = fleet-wide outage). The SL7 guard 'mini-reboot-not-stale' passes only while uptime<=45d; live uptime is exactly 45d8h so awk floor=45 and it still returns REBOOT_OK, but it flips to REBOOT_STALE at 46d (~16h out). Known fix-74. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ls -la /var/run/reboot-required -> -rw-r--r-- root Aug 21 06:29
cat /var/run/reboot-required.pkgs -> linux-image-5.15.0-190-generic, libc6, linux-base...
check cmd (host-hygiene.yaml mini-reboot-not-stale): up=$(awk '{printf "%d",$1/86400}' /proc/uptime); [ "$up" -le 45 ] && echo REBOOT_OK || echo REBOOT_STALE  # up=45 -> OK today
```

</details>

### UL45. Three docker bridges squat 192.168.0.0/16 (ha-19), none on routable VLANs `known-issue`
**Host:** mini · **Component:** host-mini · **Auditor:** svc:host-mini · **Work item:** `ha-19`

Docker default-bridge auto-allocation put three networks inside the LAN's /16: open-terminal_default 192.168.80.0/20, scrutiny-collector_default 192.168.48.0/20, terraria_default 192.168.64.0/20. The routable VLANs are 192.168.10.x (Trusted) and 192.168.20.x (IoT) — the companion check 'no docker network overlaps a routable VLAN (10/20)' PASSES, so no live routing conflict, but the /16 overlap check fails. Tracked ha-19 (sys-docker-subnet-squat). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
for n in $(docker network ls -q); do docker network inspect -f '{{.Name}} {{range .IPAM.Config}}{{.Subnet}}{{end}}' $n; done | grep 192.168 ->
open-terminal_default 192.168.80.0/20
scrutiny-collector_default 192.168.48.0/20
terraria_default 192.168.64.0/20
results.json: FAIL 'no docker network overlaps 192.168.0.0/16'; PASS 'no docker network overlaps a routable VLAN'
```

</details>

### UL46. lidarr-artist-monitor-reconcile: 15 transient failures + missed OnFailure alerts since Aug 2 `known-issue`
**Host:** mini · **Component:** host-mini · **Auditor:** svc:host-mini · **Work item:** `fix-76`

media-07 host unit lidarr-artist-monitor-reconcile.service (fires ~q15m) failed 15x since Aug 2 with API_ERR TimeoutError / HTTP 500 from Lidarr (on NAS). It self-recovers every next run and currently succeeds (15:45:07 RECONCILE_OK flipped=0 artists=38 albums=1265), so the media-07 guard check and systemctl --failed are green. Two caveats: (1) the failures correlate with NAS I/O saturation (fix-55 storm signal, itself failing in the baseline), and (2) its OnFailure ntfy handler ALSO failed 3x ('Failed to start ntfy failure notification for lidarr-artist-monitor-reconcile.service') — those reconcile failures did not always page. Minor/self-healing. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
systemctl status lidarr-artist-monitor-reconcile -> Aug 23 15:45:07 RECONCILE_OK flipped=0 artists=38 albums=1265; status=0/SUCCESS
sudo journalctl -u lidarr-artist-monitor-reconcile --since 2026-08-02 -o cat | grep -iE 'fail|API_ERR' -> API_ERR TimeoutError: timed out / HTTP Error 500 (x15) + 'Triggering OnFailure='
journal -p err uniq: 15 'Failed to start Reconcile Lidarr...', 3 'Failed to start ntfy failure notification for lidarr-artist-monitor-reconcile.service'
```

</details>

### UL47. fix-35 residual re-verified: no new Immich asset in ~9d (7-day phone-backup dead-man tripped) — deliberate, not worsened `known-issue`
**Host:** mini · **Component:** immich / nas-immich-backup-freshness (phone-backup dead-man) · **Auditor:** triage:nas-immich-backup-freshness · **Work item:** `fix-86`

The check nas-immich-backup-freshness (task fix-35, severity warn, runs on mini against http://nas:2283) asserts the library is non-empty AND at least one asset was created within the last 7 days ('phone backup flowing'). Live re-run tonight and mini's morning daily results.json (10:29 EDT) return the IDENTICAL output: backup=STALE assets=36208 fresh_7d=0 — stable morning-to-evening, no state flip. Newest asset is IMG_1902.WEBP, uploaded (createdAt) 2026-08-14T22:05Z / taken (fileCreatedAt) 2026-08-14T18:04Z — ~9 days ago. Window brackets: createdAfter -7d and -3d both return 0, -14d returns 1 — confirming the last upload (an 08-14 web-uploader burst) has aged out of the rolling 7-day window. This exactly explains the flap: green 08-15..08-21 (burst inside window), red 08-22 onward. This is a KNOWN residual: runbook wiki/docs/runbooks/photos.md states pairing is 'deliberately pending — operator decision 2026-07-18... the alert is the reminder. Do not fix the alert by disabling the checks.' Photos land via the WEB uploader in bursts, not continuous native-app backup. Library is healthy (36208 assets). Not worsened vs history (08-14 triage carried the identical diagnosis; library count is growing). NOT fixed per read-only mandate; no action needed beyond the standing human follow-up (pair the Immich mobile app). known_issue: fix-35 (reopen bridge / expected-red per runbook).

<details><summary>Evidence</summary>

```
# check def (foss-setup/verification/checks.d/nas-services.yaml:234) — asserts createdAfter=now-7d total>0, NOT a pg dump
# live reproduction on mini (IMMICH_URL/KEY grepped from /etc/verification/env, key never printed):
now_utc=2026-08-23T19:24:23Z since_7d=2026-08-16T19:24:23Z
backup=STALE assets=36208 fresh_7d=0
# mini morning daily state /var/lib/verification/results.json (Aug 23 10:29) — same numbers:
fail backup=STALE assets=36208 fresh_7d=0
# newest asset (search/metadata size=1):
originalFileName = IMG_1902.WEBP  fileCreatedAt = 2026-08-14T18:04:41.000Z  createdAt = 2026-08-14T22:05:16.263Z
# window brackets (createdAfter -> total): -3d=0  -7d=0  -14d=1  -30d=1  -60d=1
# recent activity was an EDIT not an upload: updatedAfter -3d total=1 -> IMG_0139.JPG createdAt 2026-07-24 updatedAt 2026-08-21
# runbook: 'Pairing is deliberately pending... the alert is the reminder. Do not fix the alert by disabling the checks.'
```

</details>

### UL48. OnFailure ntfy paging absent on 5 lane units — mostly by-design or covered by consumer-end checks
**Host:** mini · **Component:** journal-reflection-reconcile / wiki-rag-sync / alert-delivery-drill / net-selfheal / apply-static-ip · **Auditor:** svc:mini-host-units · **Work item:** `fix-76` · *skeptic-confirmed*

8 of 13 lane services wire OnFailure=ntfy-notify@%n (tv-cleanup, lidarr/soularr/arr-queue/sonarr reconcilers, navidrome-scan, restic-backup, verification). Five do NOT: net-selfheal and apply-static-ip (defensible — net-selfheal only fails when the box is offline so ntfy can't deliver anyway; apply-static-ip auto-reverts to DHCP on failure), and journal-reflection-reconcile / alert-delivery-drill / wiki-rag-sync. The latter three have consumer-end audit backstops that would catch a persistent stall (journal 'no #journal memo >24h missing reflection' SM37 PASS; 'synthetic alert-delivery drill sent within 8 days' SM39 PASS; wiki RAG via ai-01), so a silent hard-failure of a frequent job would still surface within a day — but adding OnFailure to journal-reflection-reconcile and wiki-rag-sync would tighten immediate detection. Minor observation only. NOT changed per read-only mandate.

*Verify note:* Fresh probe from a different vantage (systemctl show -p OnFailure --value, vs the original systemctl cat|grep) reproduces the claim exactly: net-selfheal, apply-static-ip, journal-reflection-reconcile, alert-delivery-drill, wiki-rag-sync all exist and report OnFailure=[] (empty). The "present" side corroborates: tv-torrent-cleanup, sonarr-backlog-season-search, navidrome-scan, restic-backup, verification all carry ntfy-notify@%n. Every mitigation the finding cites also holds under fresh inspection: apply-static-ip's own Description says "auto-reverts to DHCP on failure"; net-selfheal only fires on a lost DHCP lease/route (box-offline = ntfy can't deliver anyway); and all three cited consumer-end backstops PASS live — journaling-reflection-backlog (REFLECTION_BACKLOG=0, SM37), alert-delivery-drill-fresh (drill_age_days=5 FRESH, SM39), and mini-wiki-rag-fresh/retrieval + wiki-drift (ai-01). A mini-onfailure-ntfy-delivers=NTFY_DELIVERY_OK check further proves the ntfy path itself works. Severity low is correct: no actual monitoring blind-spot exists (every gap is by-design or backstopped by a passing check); the residual is only a minor immediate-paging-vs-within-a-day tightening delta for journal-reflection-reconcile and wiki-rag-sync. Finding is accurate and honestly scoped; no grounds to refute or downgrade.

<details><summary>Evidence</summary>

```
$ for u in ...; systemctl cat $u.service | grep OnFailure -> present: tv-torrent-cleanup, lidarr-*, soularr-*, arr-queue-*, sonarr-backlog-*, navidrome-scan, restic-backup, verification | ABSENT: net-selfheal, apply-static-ip, journal-reflection-reconcile, alert-delivery-drill, wiki-rag-sync
```

</details>

### UL49. MCP agent-lane probe stops at tools/list — a Memos MCP layer that lists tools but errors on tools/call would stay green
**Host:** mini · **Component:** journaling-memos-mcp (journal-09) · **Auditor:** meta:journaling · **Work item:** `fix-100`

The helper runs the real MCP conversation (initialize -> notifications/initialized -> tools/list, asserting serverInfo.name and all 7 chat tools) plus an OWUI connection drift-gate, but never executes a tools/call (e.g. a search_memos round-trip). This is the same class as the fleet's LiteLLM prior ('/v1/models lies — completion-test lanes'): registration is not execution, and the check's own docstring notes Memos 0.30 rewrote the whole MCP implementation once already — exactly the kind of upgrade where tools could enumerate but fail on invocation. Low, not medium: the check is honest about its depth (name says 'real handshake + OWUI connection wired', not e2e), it is a genuine protocol conversation rather than liveness, the underlying Memos data path is consumer-probed elsewhere in the domain (loop-e2e writes/reads real memos), and Memos is version-pinned (0.29.1) so silent MCP-layer churn is unlikely. Suggested hardening when convenient: add a read-only tools/call search_memos (query for a known-stable memo/tag) to the helper — no mutation needed. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'cat /opt/verification/bin/journaling-memos-mcp.py' -> docstring: 'Two stages, both against real consumer surfaces: 1. A REAL MCP conversation (initialize -> notifications/initialized -> tools/list) ... 2. OWUI admin config' — no tools/call anywhere in the script
yaml expect: '^MEMOS_MCP_OK$', tier: fast, severity: warn
memos image pinned neosmemo/memos:0.29.1 (docker inspect)
```

</details>

### UL50. Running v2.4.6, upstream newest is 2.4.8 (two patch releases behind)
**Host:** mini · **Component:** kometa · **Auditor:** svc:kometa · **Work item:** `fix-103`

Every run banner logs 'Version: 2.4.6 (Docker: master) / Newest Version: 2.4.8'. No functional breakage observed (all runs clean), so this is hygiene only; image bump is a normal maintenance task, not urgent. Not covered by an open task (fix-70 is Plex-specific). NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'head -30 /opt/stacks/kometa/config/logs/meta.log | grep -E "Version"'
[2026-08-22 05:00:21,563] [INFO] | Version: 2.4.6 (Docker: master) |
[2026-08-22 05:00:21,691] [INFO] | Newest Version: 2.4.8 |
$ ssh mini 'docker ps --filter name=kometa --format "{{.Image}}"' → kometateam/kometa:v2.4.6
```

</details>

### UL51. Stale duplicate playlists in Plex from a 2026-07-10 run (DC Animated Universe, Star Trek, Star Wars)
**Host:** mini · **Component:** kometa · **Auditor:** svc:kometa · **Work item:** `fix-103`

Plex holds TWO copies of three kometa timeline playlists under the same account: 'DC Animated Universe (Timeline Order)' 537 items (live, updatedAt 2026-08-16) AND 530 items (stale, updatedAt 2026-07-10 05:03); 'Star Trek (Timeline Order)' 11 vs 10 (stale 2026-07-10); 'Star Wars (Timeline Order)' 32 vs 31 (stale 2026-07-10). All three stale copies date to the same Jul 10 05:03 run — kometa evidently recreated rather than updated that day and the orphans persist. Consumer impact: duplicate playlists with diverging counts visible in the Plex UI. Kometa only maintains the newer copies (today's run shows them 'Unchanged' at correct counts). Not covered by any open task in the dedup list. NOT fixed per read-only mandate — remediation is deleting the three stale playlist objects (updatedAt 1783674189/1783674628/1783674695) via Plex.

<details><summary>Evidence</summary>

```
$ ssh mini 'TOK=$(...); curl -s -H "X-Plex-Token: $TOK" -H "Accept: application/json" "$URL/playlists" | python3 ...'
DC Animated Universe (Timeline Order) | items: 537 | updatedAt: 1786870854
DC Animated Universe (Timeline Order) | items: 530 | updatedAt: 1783674189
Star Trek (Timeline Order) | items: 11 | updatedAt: 1784365262
Star Trek (Timeline Order) | items: 10 | updatedAt: 1783674628
Star Wars (Timeline Order) | items: 32 | updatedAt: 1786006959
Star Wars (Timeline Order) | items: 31 | updatedAt: 1783674695
$ date -r 1783674189 → 2026-07-10 05:03 EDT; date -r 1786870854 → 2026-08-16 05:00 EDT
```

</details>

### UL52. Author gate rejected a legitimate request over Greek-vs-Latin author script ('The Odyssey' by Όμηρος vs 'homer'), 2026-08-20
**Host:** mini · **Component:** libreseerr · **Auditor:** svc:libreseerr · **Work item:** `fix-103`

The only request activity in the audit window ended in a terminal error: on 2026-08-20 17:40 EDT the bmig-04 author gate refused every metadata candidate for 'The Odyssey' by 'Όμηρος' — including the correct 'The Odyssey' by homer — because the gate compares author strings without transliteration/normalization across scripts. The failure path itself worked exactly as designed (fail-loudly: WARNING logged, ntfy POST /books returned 200, request status set to terminal 'error', no phantom), and today's libreseerr-request-flow-health check confirms no mechanism/transient-cause failures — all 13 historical error requests (13/31, mostly 2026-07-28 classics with messy metadata) are content-cause gate refusals. Net effect for the consumer: a wanted book was refused on a transliteration edge. Tuning candidate (normalize author names before the gate), though low value given the catalog marks libreseerr 'Being superseded by shelfmark'. NOT fixed per read-only mandate. Not covered by an open task id.

<details><summary>Evidence</summary>

```
$ ssh mini 'docker logs libreseerr --since 2026-08-02T00:00:00 2>&1 | grep -vE "reconcile pass complete" | grep -E "^2026"'
2026-08-20 17:39:59,989 INFO readarr: Retrying book/lookup 'The Odyssey Όμηρος' (attempt 2/3): empty
2026-08-20 17:40:14,889 WARNING app: Request 'The Odyssey' failed terminally: No eligible metadata candidate for 'The Odyssey' by Όμηρος — refusing to add a different book (author gate). Rejected: 'The Odyssey' by homer: author mismatch; 'The Odyssey' by gareth hinds: author mismatch; …
2026-08-20 17:40:14,907 DEBUG urllib3.connectionpool: http://ntfy:80 "POST /books HTTP/1.1" 200 609
```

</details>

### UL53. Retired Trilium image still polluting the compose-images manifest `known-issue`
**Host:** mini · **Component:** manifest-image-purity (fix-41) / compose-images.txt · **Auditor:** cross:docs-tracker-truth · **Work item:** `fix-80`

manifest-image-purity FAILs: triliumnext/trilium is listed in compose-images.txt but present in no live top-level compose (Trilium + trilium-mcp were fully reverted 2026-08-14, notes data parked at mini /opt/retired/trilium-20260814 pending purge per CLAUDE.md). This is a docs/manifest-truth residual of the retire, not a live-service problem. NOT fixed per read-only mandate. known_issue: fix-41 in baseline (manifest-image-purity).

<details><summary>Evidence</summary>

```
results.json manifest-image-purity: FAIL task=fix-41 :: MANIFEST-PHANTOM-IMAGES: [triliumnext/trilium] in compose-images.txt but in no live top-level compose (pollution or a retired stack awaiting purge)
```

</details>

### UL54. Monitoring is liveness-only — no consumer-grade check that a recipe is actually retrievable (mandate-2 gap)
**Host:** mini · **Component:** mealie / verification · **Auditor:** svc:mealie · **Work item:** `fix-100`

The only mealie check (id mini-mealie in checks.d/mini-services.yaml, task_id docker-11) asserts /api/app/about returns a version string — this proves the FastAPI backend answers, but NOT that recipes are retrievable/renderable to a consumer. Per standing mandate 1/2 (probe the consumer end; liveness-only = gap) this is a coverage gap: a frozen or emptied recipe DB, or a broken authenticated recipe-render path, would still pass. A consumer-grade probe would need a stored API token to hit /api/recipes and assert count>=1 (auth is enforced, confirmed by the 401 above). Coverage manifest DOES list mealie (mini.containers line 20) and the catalog row is correct, so the gap is depth-of-probe, not absence. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
checks.d/mini-services.yaml id: mini-mealie cmd: curl -sf -m 8 http://localhost:9000/api/app/about | grep -o '"version":"v[0-9][^"]*"' expect: '^"version":"v[0-9]' severity: warn task_id: docker-11
audit results.json -> {"id":"mini-mealie",...,"status":"pass","output":"\"version\":\"v3.4.0\""}
grep mealie foss-setup/verification/coverage/mini.containers -> mealie (line 20)
```

</details>

### UL55. 14 of 21 checks point at runbook 'wiki/runbooks/verification.md' — no such file on disk (real file is wiki/docs/runbooks/verification.md)
**Host:** mini · **Component:** media.yaml runbook pointers · **Auditor:** meta:media · **Work item:** `fix-99`

The runbook: field is carried into results.json as a human incident pointer (checks_runner.py line 229) and never mechanically resolved, so nothing breaks in automation — but an on-call human following the pointer hits a dead repo path: foss-setup/wiki/runbooks/ does not exist; the actual file is foss-setup/wiki/docs/runbooks/verification.md. The file mixes two conventions: 14 checks use the phantom wiki/runbooks/... form while 7 use the correct on-disk wiki/docs/... form (deluge-queue-hygiene.md and services/libreseerr.md both resolve). This is fleet-wide drift, not media-specific (24 uses of wiki/runbooks/verification.md plus 32 rig.md, 27 docker.md etc. across checks.d — the wiki/runbooks form looks site-URL-shaped from before the docs/ restructure). Also advisory: media-specific runbooks exist (wiki/docs/runbooks/media-library-correctness.md, media-watchable.md) that would be more apt than the generic verification runbook for the *-in-plex and library checks. NOT fixed per read-only mandate; fix is a mechanical sed across checks.d + gen-checks-pages.py in the same commit.

<details><summary>Evidence</summary>

```
cd foss-setup && ls wiki/runbooks -> 'wiki/runbooks: NO SUCH DIR'
find wiki -name verification.md -> wiki/docs/runbooks/verification.md (and wiki/docs/roadmap/verification.md)
grep -h 'runbook:' verification/checks.d/*.yaml | sort | uniq -c | sort -rn -> 32 wiki/runbooks/rig.md, 27 wiki/runbooks/docker.md, 24 wiki/runbooks/verification.md ... 7 wiki/docs/runbooks/verification.md
grep -n runbook verification/bin/checks_runner.py -> only line 229 (field copied into results), never resolved
```

</details>

### UL56. Stale service-catalog note: claims "host-network" but metube runs on the edge bridge with a published port
**Host:** mini · **Component:** metube · **Auditor:** svc:metube · **Work item:** `fix-102`

service-catalog.yaml row for metube (port 8081, URL https://metube.tabaska.us — both correct) carries the note "One-off YouTube downloads (host-network; proxied via HOST_IP)". The "proxied via HOST_IP" half matches the live Caddyfile (reverse_proxy {$HOST_IP}:8081), but the container is NOT host-network: live compose attaches it to the external edge network and publishes 8081:8081. Docs-accuracy nit against mandate 3 (document what is running). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ sed -n '32,38p' foss-setup/configs/docker-stack/service-catalog.yaml
  - name: metube
    ...
    notes: One-off YouTube downloads (host-network; proxied via HOST_IP).
$ ssh mini cat /opt/stacks/metube/compose.yaml (excerpt)
    ports:
      - "8081:8081"
    networks:
      - edge
$ grep -A3 'metube' foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile
metube.{$DOMAIN} {
	import local_tls
	reverse_proxy {$HOST_IP}:8081
```

</details>

### UL57. Two mini host timers have no direct check (one outcome-covered, one a real gap)
**Host:** mini · **Component:** mini host timers (sonarr-backlog-season-search.timer, net-selfheal.timer) · **Auditor:** meta:coverage-diff · **Work item:** `fix-101` · *skeptic-confirmed*

`sonarr-backlog-season-search.timer` (drives the IPT season-pack backlog search per the prowlarr-id-search reconciler) has NO check verifying the timer runs or succeeds — a silent one-shot failure (taxonomy #6) would stall backlog fills; only tangentially related to fix-50 (arr-grab-source). This is a genuine gap. `net-selfheal.timer` (mini network/DNS self-heal) also has no direct check, but its OUTCOME is covered by dns-mini-internal/external/unbound-upstream (dns-01) which assert DNS actually resolves — so its silent death would surface via those; noting for completeness, not a strong gap. Both verified active in systemctl 2026-08-23. NOT fixed per read-only mandate.

*Verify note:* Fresh independent probes reproduce every load-bearing claim, and the sibling-timer pattern strengthens it. Both timers are live on mini (systemctl list-timers --all: net-selfheal ran 47s ago, sonarr-backlog-season-search next run 21min; list-unit-files: both enabled). grep of foss-setup/verification/checks.d/ returns NONE for either exact timer name. The net-selfheal 'outcome-covered' half is accurate: dns.yaml contains all three cited checks (dns-mini-internal L6, dns-mini-external L22, dns-mini-unbound-upstream L33) that assert DNS actually resolves. The sonarr half is a genuine gap and fits the fleet's OWN convention: its three sibling mini reconciler timers each carry a dedicated *-reconcile-timer-healthy check (soularr-reconcile-timer-healthy soularr-backlog.yaml:35, lidarr-reconcile-timer-healthy media.yaml:366, arr-queue-reconcile-timer-healthy media.yaml:384) that asserts `is-active --quiet <timer> && Result != failed` — sonarr-backlog-season-search.timer has no equivalent. The README confirms it is a load-bearing unit (one SeasonSearch every 2h, replaced the torn-down sweeper). One mitigating detail the finding missed: the service carries OnFailure=ntfy-notify@, so a non-zero exit pages — but that does NOT catch a stopped/disabled/masked timer (the liveness dimension the finding flags), and iptorrents-idsearch-returns-results (verify-06) only probes the Prowlarr->IPT search PATH, not whether the reconciler is running. So the timer-liveness gap is real. Not a check-bug, not stale, not operator-intent; low severity is correct (a real, convention-fitting coverage gap, not worth downgrading to info). No RTC/GPU/backup-window factors apply.

<details><summary>Evidence</summary>

```
ssh mini systemctl list-timers: sonarr-backlog-season-search.timer (last 14:16), net-selfheal.timer (last 15:28) — both active
grep -rli 'sonarr-backlog-season-search' checks.d -> NONE; 'net-selfheal' -> NONE; dns.yaml has dns-mini-internal/external/unbound-upstream (covers net-selfheal outcome)
```

</details>

### UL58. mini-reboot-not-stale is 1 day from flipping: reboot pending with uptime 44d against the 45d threshold `known-issue`
**Host:** mini · **Component:** mini-reboot-not-stale · **Auditor:** meta:host-hygiene · **Work item:** `fix-74`

Live: /var/run/reboot-required present, uptime_days=44 → check still echoes REBOOT_OK but crosses REBOOT_STALE within ~1-2 days. This is the check working exactly as designed (deliberate operator-scheduled reboot, warn-only nudge) and the pending reboot is already tracked as fix-74 (mini kernel reboot in the 4-7AM window, also a CLAUDE.md standing follow-up). Filed so the imminent new red in the nightly run is pre-classified as fix-74 and not re-triaged as a fresh failure. No threshold drift — 45d remains a sane deferral bound.

<details><summary>Evidence</summary>

```
ssh mini: [ -e /var/run/reboot-required ] → pending=yes; awk /proc/uptime → uptime_days=44
```

</details>

### UL59. Repo-mirror gap: musicseerr/.env.example tracked in /opt/stacks git but missing from foss-setup mirror
**Host:** mini · **Component:** musicseerr · **Auditor:** svc:musicseerr · **Work item:** `fix-102`

The live stack git repo tracks two files for musicseerr (compose.yaml + .env.example) but the foss-setup mirror at configs/docker-stack/stacks/musicseerr/ carries only compose.yaml. Other stacks (caddy, forgejo, journaling, paperless-ngx, pinchflat) do mirror their .env.example. compose.yaml itself is byte-identical live vs mirror, so this is a minor anti-drift bookkeeping gap, not config drift. Distinct from the known in-flight caddy/homepage WIP (docker-12). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'cd /opt/stacks && git ls-files musicseerr/'
musicseerr/.env.example
musicseerr/compose.yaml
$ ls foss-setup/configs/docker-stack/stacks/musicseerr/
compose.yaml
$ diff foss-setup/configs/docker-stack/stacks/musicseerr/compose.yaml <(ssh mini cat /opt/stacks/musicseerr/compose.yaml) && echo COMPOSE-IDENTICAL
COMPOSE-IDENTICAL
$ find foss-setup/configs/docker-stack/stacks -name .env.example | head -3
.../journaling/.env.example  .../forgejo/.env.example  .../caddy/.env.example
```

</details>

### UL60. Stale 'liveness only for now ... lands in bmig-06' comments — bmig-06 shipped 2026-07-20
**Host:** mini · **Component:** nas-rreading-glasses-hc / nas-bookshelf comments · **Auditor:** meta:nas-services · **Work item:** `fix-100`

Both check headers promise 'the full books-check migration (hardcover-token-valid Jan-1 expiry tripwire, search canaries) lands in bmig-06'. bmig-06 is DONE in progress.json and its deliverables exist in reading.yaml (hardcover-token-valid, bookshelf-foreign-records, bookshelf-foreign-grab-history, bookshelf-import-deadends, etc.), so the deferred-depth framing has been stale for a month. The checks themselves are fine as fast liveness gates given the consumer-grade siblings in reading.yaml; only the comments need updating (drop the 'for now', point at reading.yaml). Note :8789 itself has no direct consumer probe anywhere, but reading.yaml's comment documents this deliberately (token dies -> rreading-glasses-hc serves warm cache; hardcover-token-valid is the upstream tripwire), so no depth finding.

<details><summary>Evidence</summary>

```
$ python3 -c "import json;p=json.load(open('foss-setup/docs/progress.json'));print('bmig-06','DONE' if 'bmig-06' in p['done'] else 'open')"
bmig-06 DONE
$ grep -n 'id: hardcover-token-valid\|id: bookshelf-foreign-records' foss-setup/verification/checks.d/reading.yaml
185:  - id: bookshelf-foreign-records
518:  - id: hardcover-token-valid
```

</details>

### UL61. 46/3525 tracks flagged missing (grey in UI) across 4 albums — truthful residue of a NAS-side library reorg, below the mass-missing guard
**Host:** mini · **Component:** navidrome · **Auditor:** svc:navidrome · **Work item:** `fix-103`

media_file has 46 rows with missing=1 spanning 4 distinct albums (CRASH, Lana Del Ray, Minutes to Midnight, Hybrid Theory). Spot-verified truthful: the flagged 'Charli xcx/Vroom Vroom/07 Baby.mp3' is genuinely absent on the RO CIFS mount, and a properly-named 'CRASH (2022)' FLAC album (dir dated Jul 31 09:15) now holds those tracks — i.e. a Jul-31 mp3-to-FLAC re-organization on the NAS left the old mp3 rows as missing residuals, which Navidrome retains (greyed) until purged from the UI. Well under the navidrome-library-present mass-missing threshold (check PASSES, output 'PRESENT_OK missing=46/3525'), and the check design deliberately tolerates backlog/deleted albums. Cosmetic for the consumer (grey dupes beside the live FLAC copies); an operator UI purge of missing files would clean it. NOT touched per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker exec navidrome sqlite3 -readonly /data/navidrome.db "select count(*) from media_file where missing=1; select count(distinct album) from media_file where missing=1"'
→ 46 / 4  (albums: CRASH, Lana Del Ray, Minutes to Midnight, Hybrid Theory)

sample row path: Charli xcx/Vroom Vroom/07 Baby.mp3
ssh mini 'ls "/mnt/nas/music/Charli xcx/Vroom Vroom/07 Baby.mp3"' → No such file or directory (flag is truthful)
ssh mini 'ls "/mnt/nas/music/Charli xcx/"' → CRASH (2022) [dir, Jul 31 09:15] with 'Charli xcx - CRASH - 03 - Good Ones.flac' etc. (FLAC replacements present)

audit-run check: navidrome-library-present pass "PRESENT_OK missing=46/3525"
```

</details>

### UL62. Crit check opens the live navidrome.db without -readonly, unlike its sibling scan-fresh check — SQLITE_BUSY during a live scan write would false-page
**Host:** mini · **Component:** navidrome-library-present check (crit) · **Auditor:** meta:media-library-correctness · **Work item:** `fix-100`

In media-library-correctness.yaml, navidrome-library-present (severity crit) runs `docker exec navidrome sqlite3 /data/navidrome.db "select ..."` with a default read-write handle on the consumer's live DB, while the adjacent navidrome-scan-fresh check correctly uses `sqlite3 -readonly`. Two consequences: (1) if the scanner holds a write lock when the check fires (timer scans every 15m), sqlite3 can return SQLITE_BUSY — the error goes to stderr, stdout stays empty, the '^PRESENT_OK' expect cannot match, and a CRIT pages falsely (fail-closed but noisy at crit level); (2) the check takes a write-capable handle on a production DB it should never mutate. One-word fix: add -readonly to match the sibling. NOT fixed per read-only mandate. Not covered by any open task.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/media-library-correctness.yaml line 90: `docker exec navidrome sqlite3 /data/navidrome.db "select case when ..."` (no -readonly, severity: crit)
line 139: `docker exec navidrome sqlite3 -readonly /data/navidrome.db ...` (sibling check uses -readonly)
```

</details>

### UL63. Backup-consistency caveat: pinchflat SQLite DB is snapshotted hot (no pre-dump), and excludes-mini.txt carries a stale downloads path
**Host:** mini · **Component:** pinchflat · **Auditor:** svc:pinchflat · **Work item:** `fix-93`

The nightly restic run (01:30) captures /opt/stacks/pinchflat/config/db/pinchflat.db in place while the app is live — pinchflat is NOT in scripts/backup/pre-backup-db-dumps.sh (that script dumps the excluded pg/other DBs like paperless/wallabag/miniflux/healthchecks). A snapshot taken mid-write of a WAL-mode SQLite can be torn; risk is low (short writes, nightly retention, media itself re-downloadable) but a `.backup`-style dump would make restores deterministic. Also, excludes-mini.txt line 6 excludes /opt/stacks/pinchflat/downloads, a path that no longer exists — media now lives on the NAS mount /mnt/nas-youtube/pinchflat (bind target /downloads), so the exclude is dead weight (harmless, but stale doc-of-record). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
grep -n pinchflat foss-setup/scripts/backup/* -> only 'excludes-mini.txt:6:/opt/stacks/pinchflat/downloads' (no entry in pre-backup-db-dumps.sh)
ssh mini docker inspect pinchflat mounts -> '/opt/stacks/pinchflat/config -> /config' and '/mnt/nas-youtube/pinchflat -> /downloads' (no /opt/stacks/pinchflat/downloads mount)
mini live env: BACKUP_PATHS="/opt/stacks /etc /home/btabaska/.ssh ..."; restic-backup.sh:105 'restic backup ${BACKUP_PATHS}'; journalctl restic-backup Aug 22 01:34:44 'no errors were found'
```

</details>

### UL64. Backup leg covers pmtiles config, and also captures the 18GB regenerable extract (minor inconsistency with the skip-regenerable exclude policy)
**Host:** mini · **Component:** pmtiles · **Auditor:** svc:pmtiles · **Work item:** `fix-93`

pmtiles state falls under restic BACKUP_PATHS default '/home /etc /opt /var/lib/docker/volumes /srv' (so /opt/stacks/maps and its compose/scripts ARE backed up). /etc/restic/excludes.txt does NOT exclude /opt/stacks/maps, so the 18GB data/us.pmtiles CONUS extract is also captured. That extract is explicitly declared regenerable (data/ is gitignored with 'rebuild: run-extract.sh') and the excludes file states a 'Tier-1 principle: back up irreplaceable state, skip anything regenerable' while excluding smaller regenerable dirs (pinchflat downloads, wiki/site, metube state). Backing up an 18GB static, regenerable file mildly deviates from that stated principle. Harmless in practice — the file never changes so restic stores it once and incrementals won't re-upload — but a future maps/pmtiles exclude entry would align with policy. NOT fixed per read-only mandate; flagged for the operator's judgement only.

<details><summary>Evidence</summary>

```
$ sudo grep BACKUP_PATHS /opt/scripts/restic-backup.sh
DEFAULT_BACKUP_PATHS="/home /etc /opt /var/lib/docker/volumes /srv"
$ sudo grep -iE 'maps|pmtiles' /etc/restic/excludes.txt -> (no match)
$ ssh mini du -sh /opt/stacks/maps/data -> 18G
$ ls -la /opt/stacks/maps/data -> us.pmtiles 18672742435 (Aug 6)
excludes.txt header: 'Tier-1 principle: back up irreplaceable state, skip anything regenerable'
```

</details>

### UL65. verify-06 IPT imdbid-search=0 tonight was a TRANSIENT throttle, not a break — RE-VERIFIED returns 100 items; caps/budget/disable all ruled out `known-issue`
**Host:** mini · **Component:** prowlarr/IPTorrents indexer (verify-06 iptorrents-idsearch-returns-results) · **Auditor:** triage:iptorrents-idsearch-returns-results · **Work item:** `fix-100`

Tonight's audit-safe run (results.json written 2026-08-22T22:23:27 EDT) recorded ipt_idsearch_items=0, failing expect '^ipt_idsearch_items=[1-9][0-9]*$'. Root-caused as a transient, NOT a persistent regression. (1) The exact query IS logged at 2026-08-22 22:14:23.9 as an issued search to IPTorrents with IMDbId:[0133093] — Prowlarr did NOT skip the indexer, so the Prowlarr#1512 caps/skip class is ruled out. (2) imdbid IS still in IPT's cached caps (movie-search supportedParams="q,imdbid"). (3) IPT is enabled (indexer id 1 = IPTorrents) and NOT failure-disabled (indexerstatus returns empty; lifetime failedQueries=0), ruling out cookie-death/rate-disable. (4) 600/24h budget NOT exhausted at check time. (5) Re-running the exact check cmd now (from NAS, localhost:9696/1/api) returns 100 items. The probe fired 0.4s after a concurrent IPT category sweep and hit a momentary slow/empty response (the check's curl -sm 60 returns empty on a slow tracker). This check has NEVER appeared in mini triage history (/var/lib/verification/triage-*.md) — it has passed every daily run since it was added ~2026-08-11, so tonight is its first-ever failure. NOT fixed per read-only mandate; nothing to fix — path is healthy now. known_issue: driver is fix-50 IPT storm (see next finding); check task_id verify-06.

<details><summary>Evidence</summary>

```
# tonight's recorded fail (local results.json)
iptorrents-idsearch-returns-results | status=fail | output='ipt_idsearch_items=0'

# the exact probe query, logged issued (NOT skipped) at check time — nas /volume1/docker/prowlarr/config/logs/prowlarr.txt
2026-08-22 22:14:23.9|Info|ReleaseSearchService|Searching indexer(s): [IPTorrents] for Term: [] | ID(s): IMDbId:[0133093], Offset: 0, Limit: 0, Categories: []

# imdbid IS in IPT cached caps (curl localhost:9696/1/api?t=caps)
<movie-search available="yes" supportedParams="q,imdbid" />
<tv-search available="yes" supportedParams="q,season,ep,imdbid" />

# indexer id 1 = IPTorrents, enabled; indexerstatus EMPTY (not disabled)
{"id":1,"name":"IPTorrents","enable":true}
=== indexerstatus (disabled/failing) ===   <-- empty, no failing indexers

# RE-RUN of the exact check cmd now → PASS
ipt_idsearch_items=100
  <title>The Matrix 1999 1080p AV1 10bit-DKong</title>
ipt_q_matrix_items=100  (keyword control)
```

</details>

### UL66. min-ratio 0.85 tightening trigger has been met (live ratios 1.000 / 0.992) but threshold and baseline comment are stale
**Host:** mini · **Component:** radarr-movies-in-plex / sonarr-tv-in-plex · **Auditor:** meta:media · **Work item:** `fix-100`

The check comment documents 'KNOWN BASELINE 2026-07-14: movies ~0.94 (12/197 unwatchable — 7 sample-file imports, 2 .iso, 1 wrong-map, 2 mismatch), TV ~0.96' and explicitly says 'Tighten min-ratio once the sample-imports are re-grabbed.' Live results tonight: radarr COVERAGE_OK checkable=286 in_plex=286 ratio=1.000, sonarr ratio=0.992 — the sample-import backlog has been remediated, the documented tightening condition has fired, but min-ratio remains 0.85. At current state a silent regression losing up to ~15% of the movie library (or ~14% of TV) from Plex would pass hourly. The checks remain valid gross-seam-break detectors (whole-library ACL/path failures still page), so this is threshold staleness, not masking of a known failure. Suggested: raise min-ratio to ~0.95 movies / ~0.95 TV and refresh the baseline comment (library also grew 197->286 movies). NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
mini /var/lib/verification/results-media.json (2026-08-22T21:41:03-04:00):
radarr-movies-in-plex pass COVERAGE_OK kind=radarr checkable=286 in_plex=286 ratio=1.000 min=0.85 excluded_recent=1
sonarr-tv-in-plex pass COVERAGE_OK kind=sonarr checkable=132 in_plex=131 ratio=0.992 min=0.85 excluded_recent=0
media.yaml lines 263-267: 'KNOWN BASELINE 2026-07-14: movies ~0.94 ... Tighten min-ratio once the sample-imports are re-grabbed.'
```

</details>

### UL67. Stale/contradictory config comment: header warns plex-tmdb invalid, yet radarr uses it and it syncs fine
**Host:** mini · **Component:** recyclarr · **Auditor:** svc:recyclarr · **Work item:** `fix-102`

The recyclarr.yml / .example header comment states 'The earlier `plex-tmdb` value was NOT a valid key and would be skipped/error', yet radarr_main.media_naming.movie.standard is set to `plex-tmdb` and the 2026-08-23 debug log shows radarr media naming synced successfully (GET config/naming 200 → PUT config/naming/1 202 → 'Media naming is up to date!') with NO invalid-key warning in the log (grepped naming|invalid|skip|warn|error). So plex-tmdb resolves to a valid radarr movie-naming key and is applied — the header warning is stale/contradictory documentation. Purely cosmetic; sync is functionally correct. NOT fixed per read-only mandate; suggest reconciling the comment in a future edit (repo mirror + live both).

<details><summary>Evidence</summary>

```
recyclarr.yml comment: '(The earlier `plex-tmdb` value was NOT a valid key and would be skipped/error.)'
radarr config: media_naming.movie.standard: plex-tmdb
debug 2026-08-23: '[03:00:31 DBG] radarr_main: HTTP Response: 202 PUT .../api/v3/config/naming/1' → '[03:00:34 INF] radarr_main: Media naming is up to date!' (no invalid-key warning)
```

</details>

### UL68. Daily 06:01 publish POST times out client-side on 12 of 21 days (incl. today) — data lands, but a real publish failure would be indistinguishable
**Host:** mini · **Component:** scrutiny-collector · **Auditor:** svc:scrutiny-collector-mini · **Work item:** `fix-103`

The 06:00 cron run POSTs SMART to the NAS hub; on 12 of 21 days since 2026-08-02 (Aug 2,4,5,6,7,9,15,16,17,18,19,22) the collector logged 'context deadline exceeded (Client.Timeout exceeded while awaiting headers)' for the POST, then exited with 'Main: Completed' anyway. Hub-side data proves every one of those payloads actually landed (today's errored run appears in the hub as last_smart=2026-08-22T06:00:03Z and history is gap-free at +24 power-on hours/day), so the hub is accepting the write but taking >60s to send the response — consistent with NAS 06:00-window IO contention (Hyper Backup window; the lane context notes NAS under heavy IO). Consequence: the error log is a standing false-negative, and because the process reports 'Main: Completed' either way, a future genuinely-failed publish would look identical (taxonomy 6 silent-scheduled-job pattern) and nothing would page — see the companion freshness-gap finding. NOT fixed per read-only mandate; no open task covers this.

<details><summary>Evidence</summary>

```
$ ssh mini 'docker logs scrutiny-collector --since 2026-08-02T00:00:00 2>&1 | grep -c "context deadline exceeded"' → 12 (one per listed day, e.g.)
time="2026-08-22T06:01:03Z" level=error msg="An error occurred while publishing SMART data for device (0x5002538f54430ddf): Post \"http://192.168.10.4:8080/api/device/0x5002538f54430ddf/smart\": context deadline exceeded (Client.Timeout exceeded while awaiting headers)" type=metrics
time="2026-08-22T06:01:03Z" level=info msg="Main: Completed" type=metrics
Yet hub /api/summary: mini sda last_smart=2026-08-22T06:00:03Z and details history has power_on_hours 16430 (Aug 22) / 16454 (Aug 23 bucket) — no missing days.
```

</details>

### UL69. Monitoring gap: sys-disk-smart-health asserts presence+status but not freshness — a dead collector stays green indefinitely
**Host:** mini · **Component:** scrutiny-collector · **Auditor:** svc:scrutiny-collector-mini · **Work item:** `fix-101`

The only check covering this service is sys-disk-smart-health (checks.d/system.yaml:119, glue-10, warn): curl hub /api/summary, assert >=7 devices and all device_status=0. Its own comment states 'Data persists in Scrutiny's registry across restarts, so the >=7 floor is stable' — which also means a stopped/wedged collector never drops the count or flips status, so mini SMART collection could silently die and the check stays green forever (taxonomy 12/13 blind spot; per mandate 1 this is presence-liveness at the hub, not proof the collector still runs). The summary API exposes last_smart collector_date per device, so a <26h freshness assertion is straightforwardly addable. Combined with the finding above (collector logs errors even on success and exits 'Completed' on failure), there is currently no signal path that catches a dead mini collector. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/system.yaml:112-131 — comment: 'Data persists in Scrutiny's registry across restarts, so the >=7 floor is stable.'
cmd asserts only: len(s)>=7 and no device_status!=0 — no timestamp comparison, while the same /api/summary response carries per-device last_smart (e.g. mini sda 2026-08-22T06:00:03Z).
$ grep -rln scrutiny foss-setup/verification/checks.d/ → system.yaml only (no other scrutiny/collector check).
```

</details>

### UL70. External-engine failure noise: startpage persistently CAPTCHA-blocked, brave/google-cse intermittently rate-limited
**Host:** mini · **Component:** searxng · **Auditor:** svc:searxng · **Work item:** `fix-103`

Log (704K, under the 1MB/1-file cap = not rotated, so banner-at-top proves full history since the 2026-08-06 boot) holds ~196 tracebacks over ~17 days (~11/day), all EXTERNAL-engine transients: 109 SearxEngineTooManyRequestsException (mostly startpage), 54 startpage CAPTCHA redirects (suspended_time=3600), 6 DDG wt-wt CAPTCHA, 5 'google cse ... unusual traffic' rate-limits, 1 HTTP 403. These are upstream engines rejecting SearXNG, NOT an app fault — SearXNG degrades gracefully and the aggregate always returned 24-28 results in every probe (startpage/brave simply drop out of unresponsive_engines while brave+duckduckgo+google cse carry the result set). No retry storm (nowhere near the >1000-identical-line taxonomy-7 threshold), no crash loop, no app auth rot, no NUL log corruption. NOT breaking any consumer. NOT fixed per read-only mandate. Optional operator cleanup: disable the persistently-CAPTCHA'd startpage engine to reduce log noise; no task tracks this.

<details><summary>Evidence</summary>

```
sudo du -h <searxng LogPath> -> 704K  (json-file cap max-size=1m max-file=1, not rotated)
docker logs searxng | head -1 -> 'SearXNG 2026.8.4-c63835bd2' (boot banner still present = full history)
docker logs searxng -t | tail -> 2026-08-23T19:27:56Z ... SearxEngineCaptchaException (fired during this audit's own probes)

docker logs searxng --since 2026-08-02 | grep -iE 'error|too many requests|captcha|blocked' | uniq -c | sort -rn | head:
 196 Traceback (most recent call last):
 109 searx.exceptions.SearxEngineTooManyRequestsException: Too many request (suspended_time=180)
  54 SearxEngineCaptchaException: get_sc_code: got redirected to https://www.startpage.com/sp/captcha (suspended_time=3600)
   6 SearxEngineCaptchaException: CAPTCHA (wt-wt)
   5 SearxEngineTooManyRequestsException: google cse: ... unusual traffic ...
   1 SearxEngineAccessDeniedException: HTTP error 403

live probe unresponsive_engines samples: [['startpage','CAPTCHA']] and [['brave','too many requests'],['startpage','Suspended: CAPTCHA']] — yet results=27/28 still returned
```

</details>

### UL71. seerr docker json-log NUL corruption — 'docker logs --since' aborts, log history before ~2026-08-16 unreadable
**Host:** mini · **Component:** seerr · **Auditor:** svc:seerr · **Work item:** `fix-96`

Taxonomy 15: reading seerr logs with --since 2026-08-02 aborts with a NUL-character JSON parse error from the docker daemon, so only ~20000 tail lines (back to 2026-08-16T03:10Z) are readable. The truncation itself is the evidence; it also means the error-storm start date can only be bounded as 'on or before 2026-08-16'. Container has 0 restarts, so the corruption likely dates from an unclean host event. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker logs seerr --since 2026-08-02T00:00:00 2>&1 | grep -iE "error|fail|exception" | sort | uniq -c'
-> 1 error from daemon in stream: Error grabbing logs: invalid character '\x00' looking for beginning of value
retry with --tail 20000 succeeds; oldest readable line: 2026-08-16T03:10:00.007Z
```

</details>

### UL72. fix-26 REOPEN: 3 rotten seerr PROCESSING requests (2 dangling TV + 1 never-grabbed movie) — re-verified, NOT worsened since morning `known-issue`
**Host:** mini · **Component:** seerr (Overseerr) request layer / seerr-request-rot check · **Auditor:** triage:seerr-request-rot · **Work item:** `fix-90`

The warn-severity check seerr-request-rot (task_id fix-26, cmd: python3 /opt/verification/bin/request-layer-audit.py seerr) fails with SEERR_ROT 3. Independently re-verified tonight against the raw seerr/sonarr/radarr APIs (not just re-running the deployed script): (1) tv#220150 = seerr request id 32, media_status=3 (PROCESSING), externalServiceId=271; sonarr GET /api/v3/series/271 -> HTTP 404 = DANGLING. (2) tv#31654 = seerr request id 29, media_status=3, externalServiceId=269; sonarr GET /api/v3/series/269 -> HTTP 404 = DANGLING. (3) movie#20455 = seerr request id 30, externalServiceId=323 -> radarr movie 'Digimon: The Movie', isAvailable=True monitored=True hasFile=False, history_records=0, age 13.2d = NEVER-GRABBED (no obtainable release; user never told). All 3 seerr requests carry createdAt 2026-08-10 (a single request batch; series 269/271 were later deleted from Sonarr, and the Digimon movie has found no release). These are NEW instances of the fix-26 class, distinct from the New Teen Titans / Princess Bride items the original fix-26 cleaned 2026-07-17 (progress.json marks fix-26 done 2026-07-17). CLASSIFICATION: known-residual / fix-26 reopen (explicitly listed in tonight's reopen baseline). The fix-26 deliverable is a detector/tripwire (plus a libreseerr-side background reconciler); seerr has no auto-delete reconciler for dangling requests, so this check firing on accumulated operator-request debris is expected, not a code/config regression. WORSENED vs morning? NO — the 10:32 EDT 2026-08-23 daily run and the audit-snapshot both showed the same 3 (same request ids, same kinds); count stable at 3; the only delta is the never-grabbed movie aging 12d->13d (clock only, already past the 7d threshold). No 4th item, no new dangling, no status escalation. Remediation is operator deletion of seerr request ids 32/29/30 (or re-adding the deleted Sonarr series) — NOT performed per read-only audit mandate.

<details><summary>Evidence</summary>

```
# Deployed check re-run (read-only; arr keys passed inline, values not echoed)
$ ssh mini 'SONARR_API_KEY=$(grep -m1 "^SONARR_API_KEY=" /etc/verification/env|cut -d= -f2) RADARR_API_KEY=$(grep -m1 "^RADARR_API_KEY=" /etc/verification/env|cut -d= -f2) python3 /opt/verification/bin/request-layer-audit.py seerr; echo EXIT=$?'
SEERR_ROT 3: dangling:tv#220150(sonarr 271 gone); never-grabbed:movie#20455(13d, 0 history); dangling:tv#31654(sonarr 269 gone)
EXIT=1

# Independent raw-API re-verification (seerr /request + sonarr /series + radarr /movie,/history) piped over stdin
$ cat seerr-reverify.py | ssh mini 'SONARR_API_KEY=... RADARR_API_KEY=... python3 -'
total_requests_take200: 33
PROCESSING_count: 7
--- tv#220150 seerr_req_id=32 media_status=3 externalServiceId=271 createdAt=2026-08-10T14:10:32.000Z
    sonarr /series/271 -> HTTP 404 (GONE)
--- movie#20455 seerr_req_id=30 media_status=3 externalServiceId=323 createdAt=2026-08-10T14:09:40.000Z
    radarr /movie/323 title='Digimon: The Movie' isAvailable=True monitored=True hasFile=False history_records=0 age_days=13.2
--- tv#31654 seerr_req_id=29 media_status=3 externalServiceId=269 createdAt=2026-08-10T14:09:32.000Z
    sonarr /series/269 -> HTTP 404 (GONE)

# History (same 3 firing; not worsened)
$ ssh mini 'grep -i seerr-request-rot /var/lib/verification/triage-{2026-08-17,2026-08-19,2026-08-22,2026-08-23}.md'
# all four days: '### seerr-request-rot (sev warn, task fix-26 ...)' — triage JSON each day cites the identical trio 220150/31654/20455
# results.json snapshot: SEERR_ROT 3: dangling:tv#220150(sonarr 271 gone); never-grabbed:movie#20455(12d, 0 history); dangling:tv#31654(sonarr 269 gone)

# Tracker context
$ progress.json .done[fix-26] = '2026-07-17: request-layer rot reconciled end-to-end ... checks seerr-request-rot + libreseerr-request-rot green' (original cleanup of DIFFERENT items; now reopened by the 2026-08-10 batch)
```

</details>

### UL73. Known failure re-verified: seerr-request-rot still failing with the same 3 rotted requests as the morning baseline (fix-26) — not worsened `known-issue`
**Host:** mini · **Component:** seerr-request-rot · **Auditor:** meta:media · **Work item:** `fix-90`

Known issue, tracked as fix-26 (today's 10:29 EDT baseline lists seerr-request-rot under fix-26). Re-verified per lane mandate: the 21:41 EDT quick-tier run shows the identical failure with the same 3 items as the 10:29 daily run — dangling tv#220150 (sonarr series 271 deleted after request), never-grabbed movie#20455 (12d with 0 radarr history), dangling tv#31654 (sonarr series 269 deleted). Count stable across the day (3 -> 3), so this is NOT a silently-worsened residual. The check itself is healthy consumer-grade (stored request state vs live backend truth) and is doing exactly its job; the finding is the underlying request rot awaiting fix-26 remediation. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
mini /var/lib/verification/results.json (2026-08-22T10:29:50-04:00) and results-media.json (2026-08-22T21:41:03-04:00), both:
seerr-request-rot fail SEERR_ROT 3: dangling:tv#220150(sonarr 271 gone); never-grabbed:movie#20455(12d, 0 history); dangling:tv#31654(sonarr 269 gone)
```

</details>

### UL74. Catalog note undercounts beszel agents (says only mini agent feeds the hub; nas + rig also feed it)
**Host:** mini · **Component:** service-catalog · **Auditor:** svc:beszel-agent-nas · **Work item:** `fix-102`

service-catalog.yaml has one beszel row (host mini, port 8090, url https://status.tabaska.us) — correct that the nas agent needs no separate row (it has no UI). But the note reads 'beszel-agent on mini feeds it' while the hub live-shows three agents feeding it (mini/nas/rig all status=up). Minor doc incompleteness only; no functional impact. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ grep -A6 'name: beszel' service-catalog.yaml
    host: mini
    port: 8090
    url: https://status.tabaska.us
    notes: Host/container metrics hub (beszel-agent on mini feeds it; agent has no UI).
(hub systems records show mini|up, nas|up, rig|up — 3 agents)
```

</details>

### UL75. unsloth vhost live in Caddy but has no service-catalog row/url `known-issue`
**Host:** mini · **Component:** service-catalog · **Auditor:** flow:unsloth-studio · **Work item:** `fix-97`

Re-verified the pre-existing baseline fail catalog-vhost-parity (task fix-68). The catalog-vhost-parity check reports VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth'] — unsloth.tabaska.us is a live Caddy edge vhost (confirmed serving the Studio SPA above) but has no corresponding row/url in configs/docker-stack/service-catalog.yaml, so wiki/catalog parity drifts. ('principal-ai' is the other in-flight session's untracked site — out of my lane.) Consumer feature unaffected; docs/catalog gap only. NOT fixed per read-only mandate; fix = add the unsloth catalog row.

<details><summary>Evidence</summary>

```
results.json check catalog-vhost-parity: status=fail exit=1 output="VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth'] (live Caddy vhost, no catalog row/url - add it)"
(edge confirmed live: curl unsloth.tabaska.us -> 200 <title>Unsloth Studio</title>)
```

</details>

### UL76. host: url inconsistent with identical-shaped siblings using host: mini — ad-hoc --host mini runs silently skip these two
**Host:** mini · **Component:** sonarr-pipeline-health / radarr-pipeline-health · **Auditor:** meta:media · **Work item:** `fix-100`

Both pipeline-health checks declare host: url while every other check in the file — including sonarr-queue-stuck, which curls the exact same Sonarr API from the same runner — declares host: mini. checks_runner.py treats url and mini-on-runner identically at execution time (both run locally, no ssh), so scheduled runs are unaffected (--host media matches by domain; the daily sweep is unfiltered — confirmed all 21 ran tonight). The gap is ad-hoc operator filtering: run-checks.sh --host mini excludes these two checks, and --host url pulls them into an unrelated set. Cosmetic/consistency defect; fix is a two-line host: mini edit. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
media.yaml line 100 & 116: host: url (sonarr-pipeline-health, radarr-pipeline-health); line 34 etc.: host: mini for sonarr-queue-stuck hitting the same http://192.168.10.4:8989 API
checks_runner.py line 76: if host in ("local", "url") or (host == "mini" and on_runner): (same execution path)
checks_runner.py line 205: if c["host"] == args.host or c["domain"] == args.host (ad-hoc --host mini filter would exclude host:url checks)
```

</details>

### UL77. stash-serving name claims 'real consumer end' but only proves an authenticated version handshake
**Host:** mini · **Component:** stash-serving check · **Auditor:** meta:nas-services · **Work item:** `fix-100`

The check POSTs GraphQL {version{version}} with the ApiKey header — this proves app+auth+DB handshake (genuinely better than the pre-fix-62 anonymous probe, and the http_code legibility work is good), but it asserts nothing about the consumer end: no scene/library count, no stream. A Stash with a lost /volume1 media mount or an empty/wiped library passes identically. Classified intermediate, not consumer; the name/comment overstate it. Cheap upgrade: query findScenes(filter:{per_page:1}) and assert count>0, same auth, same cost.

<details><summary>Evidence</summary>

```
cmd (nas-services.yaml:151-157): curl ... -X POST http://nas:9999/graphql ... -d '{"query":"{version{version}}"}' ... grep -q '"version":"v[0-9]'
name: "stash answers its GraphQL version query with auth (:9999, real consumer end)"
```

</details>

### UL78. No Uptime-Kuma monitor for Syncthing (hub GUI or mini node)
**Host:** mini · **Component:** syncthing · **Auditor:** svc:syncthing-mini · **Work item:** `fix-79`

Uptime-Kuma (57 monitors total) has no monitor whose name, url, or hostname matches syncthing or port 8384 — neither the hub GUI (syncthing.tabaska.us) nor the mini node. Practical impact is small: three enabled consumer-grade verification checks (syncthing-hub-mesh-direct, syncthing-gui-urls, syncthing-hub-inotify-live) already alert via ntfy, and the coverage manifest lists the container, so this is a Kuma-layer completeness note rather than a real blind spot. NOT fixed per read-only mandate. Does not map to fix-79 (that task is about a Kuma down-monitor alert-delivery leg, not syncthing coverage).

<details><summary>Evidence</summary>

```
ssh mini 'docker exec uptime-kuma sh -c "mariadb -u root --socket /app/data/run/mariadb.sock kuma -N -e \"select count(*) from monitor; select name from monitor where lower(name) like \\\"%sync%\\\";\""' -> 57 (count only, zero name rows)
follow-up query: select name,url from monitor where url like '%8384%' or url like '%syncthing%' or hostname like '%syncthing%' -> (no output)
```

</details>

### UL79. Sporadic clear_recently_added_queue KeyError tracebacks (23 since 2026-08-02) — benign, no notifier consumer attached
**Host:** mini · **Component:** tautulli · **Auditor:** svc:tautulli · **Work item:** `fix-103`

23 tracebacks since Aug 2, all the recently-added queue job raising KeyError 'full_title'/'rating_key' (plus one KeyError 50049) — the known Tautulli behavior when a library item's metadata vanishes before the queue drains (logs show a ghost item: "Library item '' (65830) added to recently added queue" then removed seconds later, 2026-08-22 16:51). get_notifiers returns zero configured agents, so no notification consumer is affected; history ingest is unaffected (proven live). ~1 traceback/day = noise, not a crash loop; container RestartCount 0. Filed for the record only.

<details><summary>Evidence</summary>

```
$ ssh mini 'docker logs tautulli --since 2026-08-02T00:00:00 2>&1 | grep -iE "error|exception|traceback|failed" | sort | uniq -c | sort -rn | head -4'
     23 Traceback (most recent call last):
     13 KeyError: 'full_title'
      9 KeyError: 'rating_key'
      5 Job "clear_recently_added_queue (trigger: date[2026-08-11 17:54:04 UTC]...)" raised an exception
$ ssh mini '...cmd=get_notifiers...'
result: success   # zero notifier rows returned
```

</details>

### UL80. Verification check for Tautulli is liveness-only — no ingest-freshness (consumer) probe, frozen-poller failure mode would stay green
**Host:** mini · **Component:** tautulli · **Auditor:** svc:tautulli · **Work item:** `fix-100`

The only check is mini-tautulli in foss-setup/verification/checks.d/mini-services.yaml (line 234): curl /status and grep '"result": "success"' (severity warn, task_id media-02). That proves the web app answers, not that the Plex activity websocket/history ingest is alive — taxonomy 13 (silently-frozen poller) would remain green indefinitely. Tonight's manual API probe proves ingest is currently live (newest history row 2026-08-22 19:52 EDT), but nothing codifies that. Per mandate 2 (checks must probe the consumer end) a check asserting newest get_history row age < ~72h (Plex is watched daily) is the gap. The lane reference already flagged this service liveness-only; no open fix task covers it. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ grep -n -A6 'id: mini-tautulli' foss-setup/verification/checks.d/mini-services.yaml
234:  - id: mini-tautulli
235:    name: "tautulli /status returns application success (:8181, not just a login redirect)"
237:    cmd: >-
238:      curl -sf -m 8 http://localhost:8181/status | grep -o '"result": "success"'
$ grep -rln tautulli foss-setup/verification/checks.d/
foss-setup/verification/checks.d/mini-services.yaml   # (only file — no freshness check)
$ ssh mini python3 parse /tmp/verify-audit-uc/results.json
mini-tautulli pass "result": "success"
```

</details>

### UL81. Both tv-torrent checks guard a zero-throughput path: /mnt/share/torrents/tv is empty with no writes since 2026-07-19 — perpetually-green with no producer
**Host:** mini · **Component:** tv-share-no-ancient-leftovers + tv-cleanup-timer-armed · **Auditor:** meta:host-hygiene · **Work item:** `fix-100`

The 'consumer end' check (no entry >40d) passes vacuously: /mnt/share/torrents/tv holds 0 entries, dir mtime 2026-07-19 00:13 (fix-39 ship time), and sits on the root fs — the CIFS mounts that once fed it were deliberately disabled 2026-07-07 per fstab comments ('share gone on NAS (old-server layout) — see Plan v3 fix-10'). The cleanup script itself documents the local-on-root-LV design and has a SKIP guard, so this is knowing design, but with no producer writing there for >1 month the check can never fail (taxonomy #13 zero-throughput green) and tv-cleanup-timer-armed keeps a timer armed to prune a dir nothing fills. needs-live-verify on the producer side (whether any deluge/NAS flow still lands tv torrents at this path — out of cheap-probe scope). If the flow is confirmed retired, both checks + tv-torrent-cleanup.timer + its healthchecks dead-man should be retired or repointed together; if it is merely dormant, add a producer-freshness companion so an unmounted/emptied path cannot read as green. Not covered by an open task (fix-39 is the shipped parent; no open item tracks this decay).

<details><summary>Evidence</summary>

```
ssh mini: mountpoint_of_tv=/ (root fs); ls /mnt/share/torrents/tv | wc -l → 0; stat → tv_dir_mtime=2026-07-19 00:13:48
/etc/fstab: '# 2026-07-07 disabled: share gone on NAS (old-server layout) — see Plan v3 fix-10' (//192.168.10.4/alltorrents /mnt/share/torrents cifs …)
/usr/local/sbin/tv-torrent-cleanup.sh: '# NOTE: /mnt/share/torrents is a LOCAL directory on the root LV' + SKIP-if-missing guard
live check outputs today: stale=0 (pass), enabled=enabled:next=scheduled (pass)
```

</details>

### UL82. No check asserts DNSSEC validation — a silent validation regression would stay green
**Host:** mini · **Component:** unbound · **Auditor:** svc:unbound · **Work item:** `fix-101`

The two guarding checks (dns-mini-unbound-upstream, dns-mini-external) only assert an A record resolves. If DNSSEC validation silently degraded (trust-anchor rot, a config edit dropping auto-trust-anchor-file, harden-dnssec-stripped off), resolution would keep passing while the security property the service exists for (per its own compose header: 'recursive, validating, DNSSEC-aware') is gone. My manual probes prove it works TODAY (AD flag set; dnssec-failed.org SERVFAILs), but nothing monitors it. Suggested codification (not applied, read-only audit): add a warn check asserting dig +dnssec cloudflare.com @127.0.0.1 -p 5335 returns the ad flag, or that dnssec-failed.org returns SERVFAIL. Mitigation in place: root.key RFC5011 auto-update is demonstrably alive (mtime today 19:23).

<details><summary>Evidence</summary>

```
$ grep -A4 'id: dns-mini-unbound-upstream' foss-setup/verification/checks.d/dns.yaml
    cmd: dig +short +time=3 +tries=1 @127.0.0.1 -p 5335 example.com
    expect: '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'   # A-record only, no AD/validation assertion
(dns-mini-external likewise: dig +short @192.168.10.2 example.com, IP-regex expect)
$ ssh mini 'ls -la /opt/stacks/unbound/unbound/root.key'
-rw-r--r-- 1 btabaska btabaska 1250 Aug 22 19:23 root.key
```

</details>

### UL83. so-rcvbuf 4MB not granted at startup — kernel rmem_max caps UDP receive buffer at ~416KB
**Host:** mini · **Component:** unbound · **Auditor:** svc:unbound · **Work item:** `fix-96`

unbound.conf requests so-rcvbuf: 4m but the container startup log shows the kernel granted only 425984 bytes (host net.core.rmem_max at Ubuntu default). Purely a performance-headroom nit for query bursts — no functional impact observed (76ms uncached recursion, 1-2ms Kuma heartbeats). Fix would be a host sysctl (net.core.rmem_max) or dropping the conf line to match reality; NOT fixed per read-only mandate. Logged once at 2026-07-09 start; verbosity 0 means it will only reappear on restart.

<details><summary>Evidence</summary>

```
$ ssh mini 'docker logs unbound 2>&1 | tail -5'
[1783628999] unbound[1:0] warning: so-rcvbuf 4194304 was not granted. Got 425984. To fix: start with root permissions(linux) or sysctl bigger net.core.rmem_max(linux) or kern.ipc.maxsockbuf(bsd) values.
[1783629000] unbound[1:0] info: start of service (unbound 1.22.0).
repo conf line 46: so-rcvbuf: 4m
```

</details>

### UL84. unpackerr still running on mini despite 'retired' expectation (fix-69) — extraction working `known-issue`
**Host:** mini · **Component:** unpackerr · **Auditor:** flow:movies-tv · **Work item:** `fix-96`

Known fix-69: the unpackerr-host-retired check expects unpackerr fully decommissioned on mini, but it is still present (systemd unit + running process + installed package). This is a decommission/doc discrepancy, NOT a consumer break — in fact unpackerr is actively doing its job (unpackerr-poll-advancing PASS, polls advanced 38670→40450 across 5 apps), so extraction/import of packed grabs is functioning. The finding is that the retirement plan didn't land, not that extraction is broken. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
[22:23 run] unpackerr-host-retired: unit=1 proc=1 pkg=1 -> UNPACKERR_BACK
[22:23 run] unpackerr-poll-advancing: UNPACKERR_OK apps=5 polls=40450 (advanced from 38670)
```

</details>

### UL85. Mini unpackerr not retired (fix-69) - separate from the NAS instance that owns the [[whisparr]] block `known-issue`
**Host:** mini · **Component:** unpackerr (mini instance) · **Auditor:** flow:adult-whisparr-stash · **Work item:** `fix-96`

results.json check unpackerr-host-retired=FAIL (fix-69) on mini: unit=1 proc=1 pkg=1 -> UNPACKERR_BACK. This is a mini host-hygiene residual and is NOT the instance in this chain: the [[whisparr]] extraction is handled by the NAS unpackerr container (up 12d, polling whisparr:6969), whose conf lives at /volume1/docker/media-automation/unpackerr/unpackerr.conf. Flagged for completeness because it surfaced in this chain's check extraction; it does not affect the adult pipeline's function. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
results.json check 'unpackerr-host-retired' (mini, fix-69): output 'unit=1 proc=1 pkg=1\nUNPACKERR_BACK' (status=fail). Distinct from NAS 'unpackerr Up 12 days (healthy)' which owns the [[whisparr]] block.
```

</details>

### UL86. Host-level unpackerr resurrected by ansible-pull package-manifest drift loop — retirement applied to host but not repo `known-issue`
**Host:** mini · **Component:** unpackerr host service / ansible-pull package manifest (fix-69 SL18) · **Auditor:** triage:unpackerr-host-retired · **Work item:** `fix-96`

unpackerr-host-retired is RED (output: unit=1 proc=1 pkg=1 UNPACKERR_BACK). Root cause (precise, corrects prior triage guesses of 'manual install'): fix-69 SL18 purged unpackerr from the LIVE mini on 2026-08-03 14:33 (dpkg: purge 0.13.1-613) but never removed 'unpackerr' from the ansible base-role package manifest foss-setup/hosts/macmini/pkglist.apt-manual.txt (line 59, present in BOTH repo HEAD and the live checkout /home/btabaska/.ansible-pull/...). The next ansible-pull.timer run (glue-08 self-convergence, daily ~04:30 EDT, user btabaska) executed base-role task 'Converge explicit packages (Debian/Ubuntu)' at 2026-08-04 04:30:06 with an apt name-list that explicitly contains 'unpackerr' — reinstalling unpackerr=0.15.2-960 (dpkg install 04:30:08-10) and starting+enabling the unit. The unit has run continuously since (PID 104964, ELAPSED 19d10h). This is the exact anti-drift failure CLAUDE.md warns about (host changed, repo not). It is self-perpetuating: export-manifests.timer re-dumps installed packages back into the manifest, so a naive 'apt purge' repeat will be undone by the next pull — the real fix must remove unpackerr from pkglist.apt-manual.txt (and ensure export doesn't re-add it) in the same window as the purge. NO import race / NO double-processing: the reinstalled instance runs the STOCK DEFAULT /etc/unpackerr/unpackerr.conf (purge removed old conffiles; all [[sonarr]]/[[radarr]]/[[lidarr]]/[[readarr]] url lines commented, #[[folder]] watch commented) and has logged exactly ONE journal line ('Started') in 19 days — it polls no arr, watches no folder, extracts nothing (1.4MB RAM, 50s CPU/19d). Functional impact is nil; this is a drift-hygiene residual (check severity=warn). Known residual under fix-69 (today's baseline maps unpackerr-host-retired -> fix-69); the check has FAILED every day since 2026-08-04 (first triage file). State stable at unit=1 proc=1 pkg=1 — RE-VERIFIED, not worsened (only change vs pre-purge was a one-time version bump 0.13.1->0.15.2 at reinstall). NOT fixed per read-only audit mandate.

<details><summary>Evidence</summary>

```
$ (check cmd on mini) -> unit=1 proc=1 pkg=1 / UNPACKERR_BACK

$ ssh mini 'systemctl status unpackerr.service'
  Loaded: loaded (/lib/systemd/system/unpackerr.service; enabled; vendor preset: enabled)
  Active: active (running) since Tue 2026-08-04 04:30:10 EDT; 2 weeks 5 days ago
  Main PID: 104964 (unpackerr)

$ ssh mini 'grep unpackerr /var/log/dpkg.log*'
  2026-08-03 14:33:18 status not-installed unpackerr:amd64 <none>          # fix-69 SL18 purge
  2026-08-04 04:30:08 install unpackerr:amd64 <none> 0.15.2-960            # ansible reinstall
  2026-08-04 04:30:10 status installed unpackerr:amd64 0.15.2-960
$ ssh mini 'grep unpackerr /var/log/apt/history.log*'
  Commandline: apt-get purge -y unpackerr    Purge: unpackerr:amd64 (0.13.1-613)
  Commandline: /usr/bin/apt-get -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold install unpackerr=0.15.2-960

$ ssh mini 'journalctl -u ansible-pull.service --since 2026-08-04\ 04:00 --until 2026-08-04\ 05:00'
  Aug 04 04:30:06 macmini python3.10[104522]: ansible-ansible.builtin.apt Invoked with name=['ansible',...,'unattended-upgrades', 'unpackerr', 'unrar', 'unzip', 'wakeonlan'] state=present ...   # base_pkglist converge

$ ssh mini 'systemctl list-timers ansible-pull.timer' -> next Mon 2026-08-24 04:29:48 EDT (glue-08, daily)
$ ssh mini 'systemctl list-timers export-manifests.timer' -> enabled, last Mon 2026-08-17 04:01, next 2026-08-24 04:03 (re-capture loop)

$ grep -n unpackerr foss-setup/hosts/macmini/pkglist.apt-manual.txt
  59:unpackerr                                                              # repo HEAD still declares it
$ ssh mini 'grep -n unpackerr /home/btabaska/.ansible-pull/foss-setup/hosts/macmini/pkglist.apt-manual.txt'
  59:unpackerr                                                              # live checkout too

$ ssh mini 'sudo grep -nE "url|\[\[" /etc/unpackerr/unpackerr.conf'  (secrets stripped)
  126:[[sonarr]]   127:# url = "http://127.0.0.1:8989"                       # all urls COMMENTED = stock default
  152:[[radarr]]   153:# url = "http://127.0.0.1:7878"   262:#[[folder]]      # no watch folder = inert
$ ssh mini 'journalctl -u unpackerr.service --since 2026-08-04\ 04:30 | wc -l' -> 1   (only 'Started' — idle, no arr polling)
```

</details>

### UL87. No service-catalog.yaml row for unsloth vhost — catalog-vhost-parity fails `known-issue`
**Host:** mini · **Component:** unsloth-studio / service-catalog · **Auditor:** svc:unsloth-studio · **Work item:** `fix-97`

unsloth.tabaska.us is a live Caddy vhost (edge 200, homepage tile present) but has no row in foss-setup/configs/docker-stack/service-catalog.yaml, so catalog-vhost-parity reports VHOST-NOT-IN-CATALOG ['principal-ai','unsloth']. This is the known fix-68 reopen candidate. (principal-ai in the same output is the other agent session's in-flight WIP, not this lane.) NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ grep -in unsloth foss-setup/configs/docker-stack/service-catalog.yaml
(no match)

$ python3 <extract from mini:/tmp/verify-audit-uc/results.json>
{"id":"catalog-vhost-parity","status":"fail","task_id":"fix-68","output":"VHOST-NOT-IN-CATALOG: ['principal-ai', 'unsloth'] (live Caddy vhost, no catalog row/url)"}

$ ssh mini 'curl -s -H "Host: home.tabaska.us" localhost:3010/api/services' | grep unsloth
AI :: Unsloth Studio -> https://unsloth.tabaska.us   (homepage tile IS present)
```

</details>

### UL88. unsloth-studio missing from the DEPLOYED rig coverage manifest (repo mirror is correct) — containers-manifest-rig fails `known-issue`
**Host:** mini · **Component:** unsloth-studio / verification coverage manifest · **Auditor:** svc:unsloth-studio · **Work item:** `fix-97`

The repo mirror foss-setup/verification/coverage/rig.containers lists unsloth-studio (line 21), but the deployed copy on mini (/opt/verification/coverage/rig.containers) does not, so the containers-manifest-rig check fails (live docker ps has the container, manifest lacks it). This is the known verify-06 reopen candidate ('unsloth-studio missing from manifest'); the fix is to deploy the already-updated repo manifest to mini. Re-verified still holding in last night's run. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ python3 <extract from mini:/tmp/verify-audit-uc/results.json>
{"id":"containers-manifest-rig","status":"fail","task_id":"verify-06","output":"20a21\n> unsloth-studio"}

$ grep -n unsloth foss-setup/verification/coverage/rig.containers
21:unsloth-studio   # repo mirror HAS it; deployed /opt/verification copy does not
```

</details>

### UL89. Backup caveat: kuma's embedded MariaDB backed up as raw live datadir — no pre-backup SQL dump
**Host:** mini · **Component:** uptime-kuma · **Auditor:** svc:uptime-kuma · **Work item:** `fix-93`

uptime-kuma 2.1.1 runs embedded MariaDB (db-config.json type embedded-mariadb; mariadbd --datadir=/app/data/mariadb runs continuously inside the container). The nightly restic job includes /opt (so /opt/stacks/uptime-kuma/data/mariadb is captured), but /opt/scripts/pre-backup-db-dumps.sh dumps paperless, wallabag and miniflux only — zero references to kuma. The MariaDB datadir is therefore snapshotted while the server is writing: crash-consistent at best, with a real (if modest) restore-corruption risk for InnoDB state. Monitoring history is low-stakes data, hence low severity, but adding a `mariadb-dump kuma` line to pre-backup-db-dumps.sh (via the container socket) would make restores clean. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'cat /opt/stacks/uptime-kuma/data/db-config.json' -> {"type": "embedded-mariadb", … "dbName": "kuma"}
ssh mini 'docker exec uptime-kuma sh -c "ps aux | grep -i maria"' -> mariadbd --user=node --datadir=/app/data/mariadb --socket=/app/data/run/mariadb.sock (running since Aug14)
ssh mini 'grep -c kuma /opt/scripts/pre-backup-db-dumps.sh' -> 0
journalctl -u restic-backup.service: pre-backup hook dumps paperless.sql.gz, wallabag.sql.gz, miniflux… (no kuma)
restic includes: DEFAULT_BACKUP_PATHS="/home /etc /opt /var/lib/docker/volumes /srv"
```

</details>

### UL90. Docker json-log NUL corruption: `docker logs --since` aborts for uptime-kuma (taxonomy 15)
**Host:** mini · **Component:** uptime-kuma · **Auditor:** svc:uptime-kuma · **Work item:** `fix-96`

Attempting `docker logs uptime-kuma --since 2026-08-02T00:00:00` aborts immediately with a stream error on a NUL character, so time-windowed log reads are unusable for this container until the corrupted json-log segment rotates out. `--tail 400` works and shows only monitor-target warns (historical Rig Apollo ECONNREFUSED pre-08-16, brief MCPO/Palworld/LiteLLM pending retries), no application errors and no retry storm in the readable window. This is the fleet's known taxonomy-15 pattern (the truncation itself is the evidence) but no open task covers this specific container. NOT fixed per read-only mandate; remedy at operator convenience is a container recreate or log rotation.

<details><summary>Evidence</summary>

```
ssh mini 'docker logs uptime-kuma --since 2026-08-02T00:00:00 2>&1 | … | head'
-> error from daemon in stream: Error grabbing logs: invalid character '\x00' looking for beginning of value

retry: ssh mini 'docker logs uptime-kuma --tail 400 2>&1 | grep -aiE "error|fail|warn|…"'
-> only [MONITOR] WARN lines (Monitor #34 'Rig Apollo': Failing: connect ECONNREFUSED 192.168.10.12:47990 … last at 2026-08-16T13:33-04:00; Monitor #33 'Rig MCPO' pending retries 2026-08-19) — no app-level errors
```

</details>

### UL91. Check window under-samples a bursty nightly storm — daily 10:32 run systematically misses it
**Host:** mini · **Component:** verification check arr-sqlite-not-locked (15-min sliding window) · **Auditor:** triage:arr-sqlite-not-locked · **Work item:** `fix-100`

The regression guard counts 'database is locked' errors only in the trailing LOCK_WINDOW_MIN=15 minutes. Because the storm crests overnight (~20:00-21:00 EDT / 00-01Z) and is quiet by day, the daily 10:32 EDT run reads a quiet window and greens (fix-55 is absent from every triage-*.md and from today's morning baseline), while the evening audit-safe run at 22:23 correctly catches it. So the storm was invisible to the daily monitor and only surfaced tonight because the audit ran during a crest. Not a harness bug (the probe is correct for its window) but a coverage gap. Recommend a longer-lookback companion (e.g. locks in last 6-8h > N) or scheduling a run inside the 20:00-00:00 EDT crest so the daily monitor doesn't blind-spot the recurring storm. NOT changed (read-only).

<details><summary>Evidence</summary>

```
check def foss-setup/verification/checks.d/nas-io-storm.yaml: LOCK_WINDOW_MIN=15, LOCK_MAX=5
ssh mini: grep 'arr_locked' /var/lib/verification/triage-*.md -> (no matches: never recorded as failing in any daily 10:32 triage)
Today's failure pattern: 10:32 EDT daily=green (window 14:17-14:32Z was 0 locks) ; 22:23 EDT audit=STORM 20 ; hourly buckets confirm crest 23T00Z=107 / 01Z=105 far outside both morning windows
```

</details>

### UL92. Daily Kobo-sync check probes the BASE api_endpoint (returns {}) not the real /v1/library/sync path
**Host:** mini · **Component:** verification check cwa-kobo-sync-consumer (fix-38/fix-57) · **Auditor:** flow:books-kobo · **Work item:** `fix-100`

The daily cwa-kobo-sync-consumer check (and the vault CWA_KOBO_SYNC_URL_* it uses) hit the base Kobo api_endpoint, which returns an empty JSON object {} (3 bytes). That trivially satisfies the check's assertion (an empty dict has zero non-dict elements => DICTS_OK) and 200, so the check passes WITHOUT ever exercising an actual entitlements sync. It would only catch the fix-57 'bare string ResponseStatus' regression if that contamination surfaced on the base route, which it does not. The genuine consumer path is /v1/library/sync — which I probed directly and confirmed healthy (82 all-dict entitlements). So the feature is fine; the check's depth is the caveat. Suggest (do NOT action here) appending /v1/library/sync to the probed URLs so the daily check asserts real entitlement dicts. Read-only observation.

<details><summary>Evidence</summary>

```
$ curl base api_endpoint (both devices): http_code=200 bytes=3 top_type=dict count=0 (i.e. {})
$ curl base+/v1/library/sync (both devices): http_code=200 top_type=list count=82 all dicts
check cmd (reading.yaml): for u in $CWA_KOBO_SYNC_URL_ADMIN $CWA_KOBO_SYNC_URL_KOBO2; ... bad=[x for x in d if not isinstance(x,dict)] -> empty {} yields bad=[] => DICTS_OK
```

</details>

### UL93. Check blind spot: bad[:5] truncation with no count silently masks growth of the fix-45 residual
**Host:** mini · **Component:** verification check sonarr-unmanaged-profile (media-library-correctness.yaml) · **Auditor:** triage:sonarr-unmanaged-profile · **Work item:** `fix-100`

The check cmd prints `PROFILE_BAD ` + ','.join(bad[:5]) and never emits a total count. Because the offending list is iterated in series-id order, the 5 lowest-ID series permanently occupy the first 5 slots, so the human-readable output stayed byte-identical (same 5 cartoon names) across every daily run from at least 2026-08-04 through tonight even though the underlying population doubled (5->10) when the 2026-08-10 anime batch landed on 'Any'. The check still correctly FAILs, but its output gives no signal that the residual is worsening — a live API re-query was required to detect it. Recommend the check emit a count (e.g. 'PROFILE_BAD n=10 <names>') so trend/growth is visible in triage history without a manual live probe. Not a harness bug (the check functions); a check-quality gap to fold into the fix-45 reopen. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
$ grep -n -A9 sonarr-unmanaged-profile foss-setup/verification/checks.d/media-library-correctness.yaml
183:      print('PROFILE_OK n=0' if not bad else 'PROFILE_BAD '+','.join(bad[:5]))
184:    expect: '^PROFILE_OK'
# results.json output (tonight) == every triage entry's implied output:
  "output": "PROFILE_BAD Teen Titans Go!,Animaniacs,Freakazoid!,The Grim Adventures of Billy & Mandy,Johnny Bravo"
# vs live PROFILE1_TOTAL: 10 (see finding 1)
```

</details>

### UL94. staleresults14d=6 stale ad-hoc results-*.json side files (fix-69 SL41 class), becomes 7 on ~2026-08-28 `known-issue`
**Host:** mini · **Component:** verification state dir (/var/lib/verification) · **Auditor:** triage:mini-scratch-hygiene · **Work item:** `fix-96`

Known fix-69 residual, same check. The 6 files with rotted internal timestamps are ad-hoc suite runs from the 07-27..07-29 reality-audit era: results-journaling.json (26d), results-media-indexers.json / results-monitoring-coverage.json / results-nas.json (25d), results-git-hygiene.json / results-rig.json (24d). They were <14d old at the 08-03 SL41 cleanup so they legitimately survived, then crossed the threshold ~08-10..08-12. results-mini.json (written 2026-08-14, now 8d) will cross 14d around 2026-08-28, raising the count to 7 — this sub-metric worsens on its own with no new activity. Timer-refreshed side files (results-tier-fast/url/docker-fleet/media.json) are all 0d old, confirming the live pipeline is healthy and only orphaned one-shot outputs are stale. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'for f in /var/lib/verification/results-*.json; do ... print basename, timestamp, age; done' ->
results-docker-fleet.json 2026-08-22T21:40:25-04:00 AGE_DAYS=0
results-git-hygiene.json 2026-07-29T09:35:32-04:00 AGE_DAYS=24
results-journaling.json 2026-07-27T13:23:13-04:00 AGE_DAYS=26
results-media-indexers.json 2026-07-28T11:59:04-04:00 AGE_DAYS=25
results-media.json 2026-08-22T21:41:03-04:00 AGE_DAYS=0
results-mini.json 2026-08-14T13:42:48-04:00 AGE_DAYS=8
results-monitoring-coverage.json 2026-07-28T11:53:54-04:00 AGE_DAYS=25
results-nas.json 2026-07-28T12:44:25-04:00 AGE_DAYS=25
results-rig.json 2026-07-29T09:44:58-04:00 AGE_DAYS=24
results-tier-fast.json 2026-08-22T22:26:19-04:00 AGE_DAYS=0
results-url.json 2026-08-22T21:40:08-04:00 AGE_DAYS=0
```

</details>

### UL95. KNOWN (fix-69): auth-material / aged scratch piling up in /tmp or the verification state dir `known-issue`
**Host:** mini · **Component:** verification tier / mini scratch hygiene · **Auditor:** svc:mini-host-units · **Work item:** `fix-96` · *skeptic-confirmed*

The verification runner tier (verification/fast/quick, in this lane) is healthy — daily sweep completed cleanly, results.json fresh, all check-referenced bin scripts deployed (three verification-self checks PASS). However the audit check 'mini: no auth-material or aged scratch piling up in /tmp or the verification state dir (SL40/SL41)' FAILED — the verification state dir / /tmp scratch hygiene residual. Classified known_issue fix-69 (mini-scratch-hygiene) per baseline. Cited from the audit run rather than re-walked to stay light and read-only; touches this lane only via the verification tier's state directory.

*Verify note:* Auditor admitted they cited this from the audit run "rather than re-walked." I re-walked it live on mini (2026-08-23 17:57 EDT) with fresh independent find commands — the three legs reproduce exactly: secrets=0, scratch7d=103 (threshold <=10), staleresults14d=6 (threshold 0) -> HYGIENE_DIRTY. Genuine live-reproduced failing state, not stale/transient/wrong-vantage; correctly attributed to open task fix-69 (baseline lists mini-scratch-hygiene). One caveat, not enough to refute or downgrade: the title leads with "auth-material" but that leg is CLEAN (secrets=0) — the failure is purely the two benign housekeeping legs (103 aged agent-scratch tmp.* files + 6 stale results JSONs), zero credential exposure. Severity low stays appropriate for a genuinely-failing hygiene check on a tracked task.

<details><summary>Evidence</summary>

```
$ python3 parse /tmp/verify-audit-uc/results.json: 'fail | mini: no auth-material or aged scratch piling up in /tmp or the verification state dir (SL40/SL41) | mini'  (contrast: 'pass | verification: previous daily sweep completed cleanly', 'pass | verification: every check-referenced bin script is deployed')
```

</details>

### UL96. Stale contradictory comment on the NAS secondary-resolver checks
**Host:** mini · **Component:** verification/checks.d/dns.yaml · **Auditor:** svc:adguard-nas · **Work item:** `fix-100`

dns.yaml carries self-contradictory documentation. The file header (lines 2-4) correctly states the secondary is 'live since dns-02 closed', and the mini audit run confirms dns-nas-internal and dns-nas-external both PASS. But the inline comment above those checks (lines 43-44) still says: 'They FAIL today (connection refused) - that is correct and desired until dns-02 is redone.' That inline comment is stale and directly contradicts both the header and live state; it would mislead an operator triaging a real secondary-DNS failure. Doc drift only, no functional impact. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
checks.d/dns.yaml line 3: 'Secondary resolver: AdGuard Home on NAS (192.168.10.4:53) — live since dns-02 closed'
checks.d/dns.yaml lines 43-44: 'They FAIL today (connection refused) — that is correct and desired until dns-02 is redone.'
mini /tmp/verify-audit-uc/results.json: dns-nas-internal|pass  dns-nas-external|pass
```

</details>

### UL97. dns-mini-external: fast-tier crit with single 3s UDP try and no min_consecutive_fails — the exact flap mode fix-61 de-flapped on its sibling check
**Host:** mini · **Component:** verification/checks.d/dns.yaml (dns-mini-external) · **Auditor:** meta:dns · **Work item:** `fix-100`

dns-mini-internal carries min_consecutive_fails: 2 with an explicit SM23/fix-61 comment ('a single-UDP-try 3s dig is a crit — one blip false-paged at 13:15 then recovered'). dns-mini-external hits the same AdGuard instance from the same fast tier (~10m cadence) with the identical +time=3 +tries=1 single-UDP-try pattern, is also severity crit, and additionally depends on upstream recursion latency on cache misses — yet has no min_consecutive_fails and no retry loop. One dropped packet crit-pages immediately. fix-61 is closed, so this is an incomplete-de-flap residue, not tracked by an open task. Check itself passes live (example.com -> 172.66.147.243, 104.20.23.154). NOT fixed per read-only mandate; suggested fix is min_consecutive_fails: 2 to match its sibling.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/dns.yaml lines 22-31: dns-mini-external has tier: fast, severity: crit, cmd 'dig +short +time=3 +tries=1 @192.168.10.2 example.com', no min_consecutive_fails key (contrast lines 6-12 where dns-mini-internal sets min_consecutive_fails: 2 citing SM23/fix-61)
$ ssh mini 'dig +short +time=3 +tries=1 @192.168.10.2 example.com'
172.66.147.243
104.20.23.154
```

</details>

### UL98. dns-nas-internal: single 3s UDP try at crit against the NAS resolver — its sibling got a 3-attempt retry loop after this exact pattern double false-crit'd on 2026-07-09
**Host:** mini · **Component:** verification/checks.d/dns.yaml (dns-nas-internal) · **Auditor:** meta:dns · **Work item:** `fix-100`

The dns-nas-external comment documents that a single 3s UDP try against 192.168.10.4 false-failed the sweep twice on 2026-07-09 (dropped packet / slow cache-miss = crit page while manual 10/10 retests answered in 4ms), and that check was given a 'for i in 1 2 3 ... sleep 2' retry loop. dns-nas-internal queries the same resolver with the same un-retried single try, same severity crit, no min_consecutive_fails — same documented false-crit exposure, no de-flap. (Both are daily-tier, where the runner's min_consecutive_fails sidecar does not apply per the checks_runner.py comment 'threshold applies only to filtered runs', so the in-cmd retry loop is the applicable de-flap mechanism.) Check passes live. NOT fixed per read-only mandate; suggested fix is the same 3-attempt loop.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/dns.yaml lines 45-70: dns-nas-internal cmd 'dig +short +time=3 +tries=1 @192.168.10.4 home.tabaska.us' (no loop) vs dns-nas-external cmd 'for i in 1 2 3; do dig ... && break; sleep 2; done' with comment '3 attempts: a single 3s UDP try false-failed the sweep twice on 2026-07-09'
$ ssh mini 'dig +short +time=3 +tries=1 @192.168.10.4 home.tabaska.us'
192.168.10.2
```

</details>

### UL99. terraria-world-loaded's name pins world AnalogueCoop but the cmd accepts ANY non-empty world name
**Host:** mini · **Component:** verification/checks.d/gaming.yaml: terraria-world-loaded · **Auditor:** meta:gaming · **Work item:** `fix-100`

Check name (and comment) promise "world AnalogueCoop loaded", but the cmd only asserts world != empty and maxplayers > 0. TShock's classic data-loss mode — world file corrupt/missing, server auto-generates or falls back to a fresh world — would keep this check green while the consumer end (the friends' actual co-op world with their builds) is gone: exactly the green-but-broken class the fleet mandates against. Cheap fix when out of audit mode: assert world="AnalogueCoop" literally (the sed extraction already isolates the name). Live baseline verified today: world=AnalogueCoop, maxplayers=8, so the pin would pass immediately. NOT fixed per read-only mandate. Not covered by an open task (game-01 is the build task, closed behavior).

<details><summary>Evidence</summary>

```
repo gaming.yaml lines 186-196: world=$(echo "$s" | sed -n 's/.*"world": *"\([^"]*\)".*/\1/p'); if [ -n "$world" ] && [ "${w:-0}" -gt 0 ] ... (no name comparison)
live verify: ssh mini 'curl -s -m 8 http://127.0.0.1:7878/v2/server/status' | sed/world + grep maxplayers
world=AnalogueCoop
"maxplayers": 8
```

</details>

### UL100. Both Assist-LLM checks carry task_id ha-12, which in tasks.json is the unrelated (and not-done) Zigbee backbone task
**Host:** mini · **Component:** verification/checks.d/ha.yaml (ha-assist-rig-llm-reachable, ha-assist-conversation-e2e) · **Auditor:** meta:ha · **Work item:** `fix-100`

The two checks guard the HA Assist -> rig Ollama conversation path, but tasks.json ha-12 is 'Zigbee backbone: Mosquitto + Zigbee2MQTT + USB coordinator' (depends_on ha-04, no done-entry in progress.json). The check comment says 'added 2026-07-13, #12' — an audit finding number that was mechanically written as ha-12 (the sibling '#11' -> ha-11 happens to match its backup topic, masking the pattern). An alert or reopen-bridge event on these checks would point the operator/ledger at the wrong task. Plausible correct ids: ha-09 (Assist local voice + LLM agent) or ha-17 (LiteLLM gateway/fallback model). Passes the letter of 'task_id must exist' but fails its purpose. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ python3 (tasks.json) -> ha-12: {"id": "ha-12", "title": "Zigbee backbone: Mosquitto + Zigbee2MQTT + USB coordinator", "depends_on": ["ha-04"], ...} ; dup ha-12 count: 1 ; progress.json done-entry for ha-12: no
$ task topic search -> ha-09 'Set up local voice (Assist + Whisper + Piper); LLM agent via LiteLLM (ha-17)'; ha-17 'LiteLLM gateway + small always-on fallback model'
ha.yaml lines 215-216 and 266-267: task_id: ha-12 on both Assist checks
```

</details>

### UL101. Stale comment on journaling-memos-mcp: yaml says OWUI filter is 'search_memos+create_memo' and budget '40/40', but the deployed helper asserts the 7-tool filter (budget now 37/40)
**Host:** mini · **Component:** verification/checks.d/journaling.yaml (journal-09 comment block) · **Auditor:** meta:journaling · **Work item:** `fix-100`

The journal-09 comment in the yaml (repo line ~220: 'filtered to search_memos+create_memo; the 40/40 tool budget') predates the 2026-08-17 Memos-adoption widening. The deployed helper /opt/verification/bin/journaling-memos-mcp.py (mtime Aug 17 15:11) asserts CHAT_TOOLS = {search_memos, create_memo, get_memo, list_tags, list_memos, list_memo_comments, update_memo} — 7 tools, 'widened for note-taking 2026-08-17, budget 34/40' per its own docstring — and the fleet-mcp memory now records budget 37/40. Comment-only drift: the cmd just invokes the helper, so the check's behavior is correct and passing; the risk is a future editor 'fixing' the filter back to 2 tools based on the stale yaml comment. Cheap fix (outside this audit's read-only scope): update the comment in both repo and deployed copies in one commit (checks.d edits need gen-checks-pages.py in the same commit per fleet-mcp memory). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
repo foss-setup/verification/checks.d/journaling.yaml (journal-09 block): '# to search_memos+create_memo; the 40/40 tool budget itself is owui-mcp-tools'
ssh mini 'cat /opt/verification/bin/journaling-memos-mcp.py' -> 'filtered to 7 of 19 — search/get/list memos, list_tags, list_memo_comments, create_memo, update_memo; widened for note-taking 2026-08-17, budget 34/40' and CHAT_TOOLS = {"search_memos", "create_memo", "get_memo", "list_tags", "list_memos", "list_memo_comments", "update_memo"}
ls -la -> journaling-memos-mcp.py mtime Aug 17 15:11 (post-widening); check currently 'pass' in results-tier-fast.json
```

</details>

### UL102. fleet-fs-tools expect is a bare unanchored substring 'docker' — only check in the file without an anchored OK-token
**Host:** mini · **Component:** verification/checks.d/local-ai.yaml:fleet-fs-tools · **Auditor:** meta:local-ai · **Work item:** `fix-100`

Every other check in local-ai.yaml prints and anchors a distinctive token (expect '^SEARXNG_OK ', '^OPENZIM_OK ', etc.); fleet-fs-tools (line 144) passes on the substring 'docker' anywhere in the mcpo response body. curl -sf gates non-2xx, but mcpo/FastAPI tool-level failures can return 200 with an error payload — if that error text ever echoes the requested path context or an ssh/compose path containing 'docker' (e.g. a fleet-mcp error string quoting its config), the check false-passes while the NAS listing chain is broken. Cheap hardening: parse the JSON and assert an entry named 'docker' exists in the listing, or have the probe emit an anchored FLEET_FS_OK token. Check is otherwise genuinely consumer-grade (real mcpo->fleet-mcp->ssh->NAS /volume1 listing) and passed the 2026-08-22 10:29 run. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/local-ai.yaml lines 140-144:
      cmd: >-
        curl -sf -m 45 -X POST http://192.168.10.12:8000/fleet/list_dir
        -H 'Content-Type: application/json'
        -d '{"host":"nas","path":"/volume1"}'
      expect: 'docker'
grep "expect:" local-ai.yaml -> 25 of 26 checks use anchored '^TOKEN_OK' patterns; fleet-fs-tools is the sole bare-substring expect.
ssh mini python3 (results.json 2026-08-22T10:29:50-04:00): fleet-fs-tools pass
```

</details>

### UL103. unsloth-studio comment block spliced inside the plant-scout-preset comment; the unsloth-studio-e2e check body separates plant-scout-preset's comment from its item
**Host:** mini · **Component:** verification/checks.d/local-ai.yaml (structure, lines 719-765) · **Auditor:** meta:local-ai · **Work item:** `fix-100`

The '# plant-scout-preset (lai-22 follow-on...)' comment (lines 719-729) runs directly into the '# unsloth-studio (2026-08-17)...' comment (lines 730-740) with no blank line or separator, then the unsloth-studio-e2e check item (741-751) is inserted BETWEEN that merged comment block and the plant-scout-preset item it documents (753-765). Every other check in the file keeps comment directly above its item. This is a mis-edit hazard: a future editor updating the plant-scout comment can plausibly edit the wrong check (or a tool that pairs leading comments with items will attribute the unsloth prose to plant-scout-preset). Pure file-structure fix — move the unsloth comment+check above line 719. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/local-ai.yaml:
  719  # plant-scout-preset (lai-22 follow-on, 2026-08-17): the Plant Scout one-tap
  ...
  729  # preset natively emits exactly one identify_plant tool_call.
  730  # unsloth-studio (2026-08-17): Unsloth Studio web UI on the rig (:8210,
  ...
  741    - id: unsloth-studio-e2e
  ...
  753    - id: plant-scout-preset
```

</details>

### UL104. Hardcoded Prowlarr indexer id in URL path (/1/api) contradicts the file's own by-name doctrine — latent silent-decoupling on indexer re-add
**Host:** mini · **Component:** verification/checks.d/media-indexers.yaml :: iptorrents-idsearch-returns-results · **Auditor:** meta:media-indexers · **Work item:** `fix-100`

The cmd queries http://localhost:9696/1/api?t=movie&imdbid=tt0133093 — Prowlarr's indexer-scoped Torznab route pinned to numeric id 1 — while the bitmagnet check 20 lines up explicitly resolves its indexer by NAME because 'id can change on re-add'. Live-verified TODAY that id 1 = IPTorrents (currently correct, check passing with 100 items), so this is staleness risk, not breakage. Failure modes if IPT is ever re-added under a new id: (a) id 1 vacant -> misleading 0-items fail blamed on the search chain, or (b) id 1 inherited by a different indexer that also matches tt0133093 (The Matrix — most indexers carry it) -> the check PASSES while no longer probing IPT's caps/cookie/budget chain at all, silently un-guarding the 2026-08-11 backlog-incident class. Fix is to resolve the id by name first (the bitmagnet-torznab-probe.py pattern already exists to copy). File: /Users/brandontabaska/GitHub/Home/foss-setup/verification/checks.d/media-indexers.yaml lines 117-125. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
yaml: n=$(ssh … nas "curl -sm 60 'http://localhost:9696/1/api?t=movie&imdbid=tt0133093&apikey=$k'" …)
live indexer map (curl -H X-Api-Key http://192.168.10.4:9696/api/v1/indexer): 1 | IPTorrents | enabled: True; 8 | Bitmagnet (DHT) | enabled: True; 2 | MyAnonamouse; 6 | OnlyEncodes+ (API); 5 | RetroToon; 4 | Zenith …
results.json (2026-08-22T10:29): iptorrents-idsearch-returns-results | pass | ipt_idsearch_items=100
```

</details>

### UL105. SLOW rung of the true-state ladder conflates search ERRORS with slowness — a hard-broken Prowlarr search path would pass forever via caps liveness
**Host:** mini · **Component:** verification/checks.d/media-indexers.yaml :: bitmagnet-torznab-via-prowlarr · **Auditor:** meta:media-indexers · **Work item:** `fix-100`

bitmagnet-torznab-probe.py catches ANY exception on the scoped search and labels it 'search=timeout', then passes if the static t=caps endpoint answers (deliberate, documented de-flap for a demoted manual-only fallback). But an instant HTTP 500/401 from Prowlarr's search API — a genuinely broken search path, not load — takes the same rung and passes indefinitely, so the check's 'consumer end' name decays to caps-liveness + the separate DB-freshness check. Observed passing via SLOW in BOTH of today's observations (10:29 run and my 20:5x re-run, each 'search=timeout' after the full 30s box, endpoint=alive); NAS is under heavy IO today so load-degraded is plausible, and no streak history exists in results.json.streak.json to prove chronicity (keys absent). Suggested hardening: distinguish HTTPError/URLError-with-status from socket timeout in the except clause, and surface a SLOW-streak counter so a permanent SLOW eventually warns. Code: /Users/brandontabaska/GitHub/Home/foss-setup/verification/bin/bitmagnet-torznab-probe.py lines 81-97 ('except Exception: n = None' then why='search=timeout'). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
results.json (2026-08-22T10:29): bitmagnet-torznab-via-prowlarr | pass | BITMAGNET_PROWLARR_SLOW indexer=8 search=timeout endpoint=alive
ssh mini 'time python3 /opt/verification/bin/bitmagnet-torznab-probe.py' -> BITMAGNET_PROWLARR_SLOW indexer=8 search=timeout endpoint=alive (manual-only fallback, load-degraded — not paging) / real 0m30.373s
code: try: res=json.loads(_get(f"{PROWLARR}/api/v1/search?query=1080p&indexerIds={iid}&limit=5", key, timeout=SEARCH_TIMEOUT)); n=len(res) / except Exception: n = None  # timed out / errored under load … why = "search=timeout" if n is None else "hits=0"
```

</details>

### UL106. Throughput leg 'fetched>=1' is a lifetime counter — permanently green since first-ever fetch, cannot detect a future silent fetch stall `known-issue`
**Host:** mini · **Component:** verification/checks.d/media-subtitles.yaml:bazarr-providers-can-fetch · **Auditor:** meta:media-subtitles · **Work item:** `fix-100`

The check's consumer-end floor sums cumulative episode+movie download-history totals and asserts >=1. Live value is 689, meaning this leg has been unconditionally satisfied since 2026-08-03 and can never fire again: if Bazarr's search scheduler froze or providers silently stopped delivering (fleet failure-pattern 13, silently-frozen poller / zero-throughput green), only the weaker 'status Good' leg would remain, and 'Good' reflects not-throttled, not actual recent downloads. The check still fully covers its designed SH7 class (providers emptied / all providers dead), so this is decay at the margin, not masquerade — hence low, not medium. Natural hardening (assert a recent-window history count or wanted-backlog delta) belongs with open task fix-77 ('Drain the Bazarr subtitle backlog + optional provider-key upgrade'), which explicitly references fix-59; a freshness assertion only becomes meaningful once the backlog is being actively drained. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
checks.d/media-subtitles.yaml line 78: fetched=g('/api/episodes/history?start=0&length=1').get('total',0)+g('/api/movies/history?start=0&length=1').get('total',0);  line 79: ok=(len(ep)>=1 and len(good)>=1 and fetched>=1)
Live: SUBS providers=2 good=2 fetched=689 (cumulative total, monotonically non-decreasing)
tasks.json: fix-77 'Drain the Bazarr subtitle backlog + optional provider-key upgrade' (open, links fix-59)
```

</details>

### UL107. Accepted-count baseline drifted loose: threshold <=8 was set for a floor of 3 un-recoverable movies that no longer exist — live stranded=0, so 8 new strandings would pass silently
**Host:** mini · **Component:** verification/checks.d/media-watchable.yaml:media-extraction-backlog · **Auditor:** meta:media-watchable · **Work item:** `fix-100`

The check's in-file comment (checks.d/media-watchable.yaml lines 47-49) states 'Post-fix-27 floor is 3 honestly un-recoverable movies (2 iso-in-rar, 1 corrupt archive)' and the script default is --max 8 (floor 3 + headroom). Live-verified today: stranded=0 in both the 2026-08-22 10:29 daily sweep and the 2026-08-14 lane run — the 3-movie floor has been cleared at some point since 2026-07-17 and the comment is now factually stale. Consequence: the M60 regression guard now carries 8 items of silent headroom — up to 8 NEW rar-stranded wanted movies would accumulate before the check trips, which is exactly the slow-accumulation failure mode the check exists to catch early. Cheap fix (not applied — read-only mandate): pass --max 2 (or 3) in the cmd and refresh the comment to the new floor of 0. The check name string 'arr: <=8 wanted movies stranded' should be updated in the same edit.

<details><summary>Evidence</summary>

```
ssh mini 'grep -n "floor\|MAX\|> *[0-9]" /opt/verification/bin/arr-rar-backlog.py'
-> 45:    ap.add_argument("--max", type=int, default=8, help="floor of known un-recoverable stranded movies")
-> 81:    if n > args.max:
repo yaml line 51: name: "arr: <=8 wanted movies stranded as un-extracted rar (M60 backlog)" (cmd passes no --max, default 8 applies)
Today's sweep (results.json ts 2026-08-22T10:29:50-04:00): media-extraction-backlog | pass | RARBACKLOG_OK stranded=0 <=8
2026-08-14 lane run (results-mini.json): RARBACKLOG_OK stranded=0 <=8
yaml comment lines 47-49: 'Post-fix-27 floor is 3 honestly un-recoverable movies (2 iso-in-rar, 1 corrupt archive)'
```

</details>

### UL108. Retained /opt/stacks/meme-review dir still contradicts the stacks-orphan-dirs check; 'temporary' decommission is now ~4 weeks with no revive-or-retire decision beyond fix-69 `known-issue`
**Host:** mini · **Component:** verification/checks.d/meme-review.yaml (disposition) + stacks-orphan-dirs check · **Auditor:** meta:meme-review · **Work item:** `fix-100`

Tracked by open task fix-69 ('Fleet hygiene batch: meme-review check-vs-policy contradiction ...'). The decommission deliberately retained /opt/stacks/meme-review (data kept for revival) — verified still present on mini 2026-08-22 — which the stacks-orphan-dirs hygiene check (different file) flags as an orphan, a check-vs-policy contradiction fix-69 proposes resolving by allowlisting or archiving the dir. Related disposition gap: the yaml header calls the decommission 'temporary' (2026-07-28), but 25 days on there is no open task to either revive meme-review (which would re-enable these 3 checks) or permanently retire it (which would archive the dir and delete/tombstone the yaml); fix-69 is the only vehicle carrying that decision. Not a defect in the checks themselves — they are correctly disabled — but the file's limbo state is only resolvable through fix-69. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'ls -d /opt/stacks/meme-review'
/opt/stacks/meme-review

python3 (tasks.json scan for 'stacks-orphan-dirs'/'check-vs-policy'):
fix-69 | Fleet hygiene batch: meme-review check-vs-policy contradiction, log floods (syno... | open
fix-69 summary: "stacks-orphan-dirs flags meme-review whose data retention was deliberate — align check allowlist or archive the dir; ..."

meme-review.yaml header: "# DECOMMISSIONED 2026-07-28 (temporary): all checks below set enabled:false while the app is stopped ... Left in place (not deleted) so revival is a one-line flip."
```

</details>

### UL109. homepage-widget-errors fails OPEN: docker-logs error or missing container yields errors=0 = green
**Host:** mini · **Component:** verification/checks.d/monitoring-coverage.yaml:homepage-widget-errors · **Auditor:** meta:monitoring-coverage · **Work item:** `fix-100`

The cmd merges stderr into the grep (2>&1) and counts only EAI_AGAIN/getaddrinfo lines. If the homepage container is renamed/absent, or `docker logs --since 2h` aborts (fleet failure-pattern 15: json-log NUL corruption aborts --since), the pipeline still prints errors=0 with exit 0 and the check PASSES while completely blind. Demonstrated live against a nonexistent container name. Mitigated in practice: sibling terraria-tile-present curls :3010/api/services (fails if homepage is down) and homepage-dead-tiles fails closed on config-read error, so only the evidence-window-lost case (log read aborts while container runs) is truly uncovered. Suggested fix: assert the log stream was readable (e.g. require a sentinel line count or check docker logs exit status) before trusting the zero. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'echo "errors=$(docker logs no-such-container-xyz --since 2h 2>&1 | grep -icE \"EAI_AGAIN|getaddrinfo\")"; echo "exit=$?"'
errors=0
exit=0
-- vs. today's real run (results.json 2026-08-22T10:29:50-04:00): homepage-widget-errors | pass | errors=0
```

</details>

### UL110. terraria-tile-present asserts a bare substring over the whole services JSON, not Games-group membership
**Host:** mini · **Component:** verification/checks.d/monitoring-coverage.yaml:terraria-tile-present · **Auditor:** meta:monitoring-coverage · **Work item:** `fix-100`

Check name claims "homepage Games group still lists the Terraria server tile" but expect is just 'Terraria' anywhere in the full /api/services payload. Any other tile/description mentioning Terraria (e.g. an AMP instance tile) would keep it green after the actual Games tile is dropped — the exact services.yaml-regression class the check exists to catch. Today it is honest: live API shows exactly one Terraria occurrence and it IS in Games (verified post the in-flight services.yaml edit by the concurrent session — that edit did not drop the tile). Cheap hardening: pipe through python/jq asserting group name == Games contains service name Terraria. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'curl -s -m 8 http://localhost:3010/api/services | python3 -c ...groups containing Terraria...'
[['Games', ['Terraria']]]
-- check def expects only: expect: 'Terraria' on the raw JSON
```

</details>

### UL111. Journal-bloat checks fail OPEN if the journalctl --disk-usage parse ever breaks
**Host:** mini · **Component:** verification/checks.d/power-journal.yaml (journal-not-bloated-mini, journal-not-bloated-rig) · **Auditor:** meta:power-journal · **Work item:** `fix-100`

Both journal-not-bloated checks compute b=$(numfmt --from=iec "$u" 2>/dev/null || echo 0). If journalctl fails or its output format drifts so the regex [0-9.]+[KMGT] extracts nothing, u is empty, numfmt errors are swallowed, b falls back to 0, and 0 < 2147483648 prints 'JOURNAL_OK usage=' — which matches expect '^JOURNAL_OK'. So any parse/command failure is a silent false PASS, defeating the tripwire (this is the fleet's own taxonomy #2, green-but-broken masking, applied to the check itself). Rig is rolling-release CachyOS where journalctl output drift is plausible. Currently harmless — verified live that both hosts parse fine today (mini '1.0G', rig '1G', both formats match the regex, numfmt present at /usr/bin/numfmt on rig). Cheap hardening: guard with [ -n "$u" ] (fail closed on empty parse). NOT fixed per read-only mandate. Not covered by any open task.

<details><summary>Evidence</summary>

```
Local demonstration of the fail-open branch:
$ u=''; b=$(numfmt --from=iec "$u" 2>/dev/null || echo 0); if [ "${b:-0}" -lt 2147483648 ]; then echo "JOURNAL_OK usage=$u"; else echo "JOURNAL_BLOAT usage=$u cap=2G"; fi
JOURNAL_OK usage=
(matches expect '^JOURNAL_OK' despite zero measurement)
Live format today: ssh mini 'journalctl --disk-usage' -> 'Archived and active journals take up 1.0G in the file system.'; ssh rig -> 'Archived and active journals take up 1G in the file system.'
```

</details>

### UL112. All 5 runbook fields point at wiki/runbooks/photos.md, which does not exist as a repo file (real file is wiki/docs/runbooks/photos.md)
**Host:** mini · **Component:** verification/checks.d/rig-immich-ml.yaml · **Auditor:** meta:rig-immich-ml · **Work item:** `fix-99`

Every check in the file (and the header comment) sets runbook: wiki/runbooks/photos.md, but no wiki/runbooks/ directory exists under foss-setup/ — the actual runbook is foss-setup/wiki/docs/runbooks/photos.md. checks_runner.py (line ~229) passes the runbook string opaquely into results/alerts without resolving it, so an operator following an alert to the literal repo path hits a dead path; the string only works if mentally translated to the published mkdocs site URL (wiki.tabaska.us/runbooks/photos/, since mkdocs strips docs/). This is a fleet-wide convention split, not a photos-specific typo: ~150 checks across checks.d use the site-path style (wiki/runbooks/rig.md x32, wiki/runbooks/docker.md x27, wiki/runbooks/photos.md x7, ...) while ~90 use the repo-path style (wiki/docs/runbooks/git-hygiene.md x18, wiki/docs/runbooks/reading-cwa.md x10, ...) — whichever resolver convention is canonical, roughly half the fleet's runbook fields break it. Not covered by any open task in the dedup list. NOT fixed per read-only mandate; suggested disposition is a one-time fleet-wide normalization pass (or a runner-side prefix rewrite) rather than a per-file edit.

<details><summary>Evidence</summary>

```
ls foss-setup/wiki/runbooks/photos.md -> No such file or directory; find foss-setup/wiki -name photos.md -> wiki/docs/runbooks/photos.md, wiki/docs/roadmap/photos.md
grep -rh 'runbook:' foss-setup/verification/checks.d/*.yaml | sort | uniq -c | sort -rn | head -> 32 wiki/runbooks/rig.md / 27 wiki/runbooks/docker.md / 18 wiki/docs/runbooks/git-hygiene.md / 16 wiki/runbooks/nas.md / 7 wiki/runbooks/photos.md (both conventions coexist)
grep -n '"runbook"' foss-setup/verification/bin/checks_runner.py -> line 229: entry = {k: c.get(k) for k in ("id", "name", ..., "task_id", "runbook")} — no path resolution
```

</details>

### UL113. All 10 checks reference dead runbook paths (wrong prefix + 6 of 7 basenames don't exist)
**Host:** mini · **Component:** verification/checks.d/system.yaml (runbook: field) · **Auditor:** meta:system · **Work item:** `fix-99`

Every check points runbook: at wiki/runbooks/<x>.md, but runbooks actually live under wiki/docs/runbooks/. Worse, 6 of the 7 distinct basenames referenced here do not exist under wiki/docs/runbooks/ at all: ansible-pull.md, system.md, docker.md, network.md, home-assistant.md, seedbox.md are absent (the real files are host-hygiene.md, dns-outage.md/lan-exposure.md/reverse-proxy.md, ha-health.md, seedbox-exposure.md). Only fleet-hygiene.md exists (just with the wrong prefix). This hits crit checks too (sys-ansible-pull, sys-disk-root, sys-home-assistant, sys-docker-vlan-overlap) — so when a crit fires the operator's runbook pointer 404s. Fleet-wide pattern: 156 runbook: values across checks.d use the stale wiki/runbooks/ prefix vs 199 using the correct wiki/docs/runbooks/. Functional blast radius is limited because gen-checks-pages.py does not render the per-check runbook field as a link or validate it (README even annotates 'may not exist yet'), so this is doc-integrity drift rather than a runner break. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
ls foss-setup/wiki/docs/runbooks/ | grep -E '^(ansible-pull|system|docker|network|home-assistant|seedbox|fleet-hygiene)\.md$'
# -> fleet-hygiene.md   (only match)
grep -rhE 'runbook:' foss-setup/verification/checks.d/*.yaml | grep -c 'wiki/runbooks/'   # -> 156
grep -rhE 'runbook:' foss-setup/verification/checks.d/*.yaml | grep -c 'wiki/docs/runbooks/' # -> 199
```

</details>

### UL114. Several system checks carry semantically-wrong task_ids (triage misattribution)
**Host:** mini · **Component:** verification/checks.d/system.yaml (task_id: field) · **Auditor:** meta:system · **Work item:** `fix-100` · *skeptic-confirmed*

task_ids all exist in tasks.json (runner-valid) but four are mis-tagged, so if these checks fail the reopen/triage layer attributes them to unrelated tasks: sys-ansible-pull AND sys-failed-units -> glue-03 which is 'Set Kagi as the default search engine' (the real owner is glue-08 'Self-converging fleet with ansible-pull + roles' or fix-06 'Repair ansible-pull convergence'); sys-disk-root -> glue-04 which is 'Version-controlled dotfiles with chezmoi — MacBook bootstrap' (no disk relationship); sys-home-assistant -> ha-01 which is 'HA platform: HA Green (purchased — decision landed)', a closed procurement-decision task, not an HA-health task (fix-36 'Home Assistant health' is the functional owner). Two more are marginal: sys-tailscale-peers -> net-05 (firewall policies) and sys-docker-restart-loops -> docker-12 (Diun notifier). This is the same class as fix-62 'Check quality + coverage batch'. NOT changed per read-only mandate.

*Verify note:* Holds. system.yaml literally tags sys-ansible-pull + sys-failed-units to glue-03 (Kagi), sys-disk-root to glue-04 (chezmoi), sys-home-assistant to ha-01 (HA procurement). glue-08 (ansible-pull) exists as the obvious correct owner = slam-dunk mismatch. reopen-report.py confirms it maps each failing check's task_id straight to a reopen candidate, so a fail misattributes to the wrong done-task silently (all ids valid, not UNKNOWN). LOW is right.

<details><summary>Evidence</summary>

```
python3 (walk tasks.json):
glue-03 :: Set Kagi as the default search engine (anytime)
glue-04 :: Version-controlled dotfiles with chezmoi — MacBook bootstrap
ha-01  :: HA platform: HA Green (purchased — decision landed)
glue-08 :: Self-converging fleet with ansible-pull + roles (the set-and-forget layer)   # correct owner for sys-ansible-pull
```

</details>

### UL115. Deployed rig.containers coverage manifest lags repo by unsloth-studio (deploy-lag drift since lai-28, failing daily since 2026-08-18) `known-issue`
**Host:** mini · **Component:** verification/coverage · **Auditor:** triage:containers-manifest-rig · **Work item:** `fix-97`

verify-06 known residual, RE-VERIFIED 2026-08-22 evening and NOT worsened (still exactly one line of drift). Root cause: lai-28 commit 97a672e (2026-08-17 18:35:40 -0400) shipped unsloth-studio on rig (container created 2026-08-17 18:11 EDT, Up 5 days) and correctly added it to the repo manifest foss-setup/verification/coverage/rig.containers (+1 line, confirmed in the commit stat), but the deploy step to mini /opt/verification/coverage/ was skipped — deployed file mtime is 2026-08-16 19:19, predating lai-28, and holds 20 entries vs the repo's 21. The daily containers-manifest-rig check therefore fails with the identical diff '20a21 > unsloth-studio' every run since 2026-08-18 (triage-2026-08-18/19/21/22.md all carry the same diagnosis; no triage file exists for 08-20). This is the documented process gap (memory: orchestrator-gated — deploys skip the coverage-manifest step; standing mandate 2 coverage tripwire). Residual risk while it stays red: a genuinely rogue new rig container would blend into an already-failing check. Fix = deploy the repo file to mini (root-owned dir, needs ssh sudo tee per verification-deploy-quirk) — NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'cat /opt/verification/coverage/rig.containers' | diff - foss-setup/verification/coverage/rig.containers; echo "diff exit=$?"
20a21
> unsloth-studio
diff exit=1
$ ssh mini 'ls -la /opt/verification/coverage/rig.containers'
-rw-r--r-- 1 root root 212 Aug 16 19:19 /opt/verification/coverage/rig.containers
$ ssh rig "docker ps --format '{{.Names}}\t{{.CreatedAt}}\t{{.Status}}' | grep unsloth"
unsloth-studio	2026-08-17 18:11:00 -0400 EDT	Up 5 days
$ git log -1 --format='%h %ad %s' -- foss-setup/verification/coverage/rig.containers
97a672e 2026-08-17 18:35:40 -0400 lai-28: Unsloth Studio on the rig — web UI, llama-swap lanes, MCP tools
$ git show --stat 97a672e | grep coverage
 foss-setup/verification/coverage/rig.containers    |   1 +
tonight's run (results.json): containers-manifest-rig status=fail exit_code=1 output='20a21\n> unsloth-studio'
history: grep -l containers-manifest-rig /var/lib/verification/triage-*.md -> 2026-08-18, -19, -21, -22 (identical single-line drift each day)
```

</details>

### UL116. Same lai-28 skipped deploy left rig.ports without 8210 — explains the 8210 element of lan-listeners-drift-rig (fix-51 lane) `known-issue`
**Host:** mini · **Component:** verification/expected-listeners · **Auditor:** triage:containers-manifest-rig · **Work item:** `fix-97`

Corroborating the deploy-lag root cause: /opt/verification/assets/expected-listeners/rig.ports on mini has the identical stale mtime 2026-08-16 19:19 and lacks port 8210, while the repo copy gained '8210 # unsloth-studio' (line 27) in the same lai-28 commit 97a672e. Tonight's lan-listeners-drift-rig fail reports 'LISTENER_DRIFT=rig:8210,27036,59999' — the 8210 component is this same benign deploy lag (unsloth-studio web UI, an expected lai listener already codified in the repo baseline), not a rogue listener. Ports 27036/59999 are NOT explained by this and remain the fix-51 lane's to root-cause. Filed as cross-lane evidence, known_issue under fix-51/verify-06. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'ls -la /opt/verification/assets/expected-listeners/rig.ports; grep -n 8210 /opt/verification/assets/expected-listeners/rig.ports || echo NO_8210_DEPLOYED'
-rw-r--r-- 1 root root 1805 Aug 16 19:19 /opt/verification/assets/expected-listeners/rig.ports
NO_8210_DEPLOYED
$ grep -n 8210 foss-setup/verification/assets/expected-listeners/rig.ports
27:8210    # unsloth-studio — Unsloth Studio web UI (2026-08-17)
tonight's run (results.json): lan-listeners-drift-rig status=fail output='LISTENER_DRIFT=rig:8210,27036,59999 (NEW all-interface listener not in baseline ...)'
```

</details>

### UL117. Known residual: phantom triliumnext/trilium in compose-images.txt awaits the fix-80 commit leg, not the weekly export `known-issue`
**Host:** mini · **Component:** verification/manifest-image-purity (fix-41 class) · **Auditor:** triage:manifest-image-purity · **Work item:** `fix-80`

Check fails because origin/main foss-setup/hosts/macmini/compose-images.txt line 47 still pins triliumnext/trilium:v0.104.1 (file last touched by commit 5667fd0, lai-17, ~2026-08-06) while trilium was retired live 2026-08-14 (moved to /opt/retired/trilium-20260814 per CLAUDE.md). The weekly export on mini ALREADY regenerated a trilium-free manifest on Mon 2026-08-17 04:01:41 EDT into /opt/foss-setup/foss-setup/hosts/macmini/, but that output sits uncommitted (git status: M hosts/macmini/compose-images.txt, M hosts/macmini/systemd-timers.txt, M configs/inventory/inventory.md) and the clone HEAD f683cfd lags origin/main ab54803. The check judges a fetched origin/main clone, so it fails until the sync commit lands. This is exactly open task fix-80 ('Commit the regenerated /opt/foss-setup manifests + clear clone drift'), which also drives today's baseline glue-08 git-foss-setup-clean failure. RE-VERIFIED not worsened: identical single phantom in every triage file 2026-08-15 through 2026-08-22, and tonight's output has no MANIFEST-MISSING-IMAGES line (no live image unlisted — the 100%-coverage tripwire side is clean). NOT fixed per read-only mandate; running fix-80 (commit + push the regenerated manifests) self-clears this check.

<details><summary>Evidence</summary>

```
results.json check manifest-image-purity: status fail, output 'MANIFEST-PHANTOM-IMAGES: [triliumnext/trilium] in compose-images.txt but in no live top-level compose'
$ grep -n trilium foss-setup/hosts/macmini/compose-images.txt (local main)
47:triliumnext/trilium:v0.104.1
$ git log --oneline -1 -- foss-setup/hosts/macmini/compose-images.txt
5667fd0 lai-17: offline maps — PMTiles US extract + Photon geocoder + OSM MCP
$ ssh mini 'grep -n trilium /opt/foss-setup/foss-setup/hosts/macmini/compose-images.txt; echo grep-exit:$?; stat -c "%y %n" ...'
grep-exit:1
2026-08-17 04:01:41.515882942 -0400 /opt/foss-setup/foss-setup/hosts/macmini/compose-images.txt
$ ssh mini 'cd /opt/foss-setup/foss-setup && git status --porcelain | head; git log --oneline -1'
 M foss-setup/configs/inventory/inventory.md
 M foss-setup/hosts/macmini/compose-images.txt
 M foss-setup/hosts/macmini/systemd-timers.txt
f683cfd glue-15: clear pre-existing fleet git-hygiene regressions surfaced by glue-14
$ ssh mini 'grep -A6 manifest-image-purity /var/lib/verification/triage-2026-08-15.md'
"diagnosis": "The compose-images.txt manifest lists triliumnext/trilium, but no active Docker Compose file on mini uses it."
```

</details>

### UL118. Monitoring depth gap: only check is app-liveness (/api/info payload) — no consumer or throughput probe (mandate 2)
**Host:** mini · **Component:** wallabag · **Auditor:** svc:wallabag · **Work item:** `fix-100`

The single verification check mini-wallabag (checks.d/mini-services.yaml, task_id read-07) greps /api/info for the appname payload. That proves the PHP app answers but never touches the entry store, the OAuth/API surface, or throughput — a wedged DB or a save-pipeline break would stay green (taxonomy 2/13). Kuma monitor is plain HTTP to :8085, same depth. A consumer-grade check (e.g. authenticated GET /api/entries asserting count>=N, or the DB newest-entry/count probe this audit ran) does not exist. Not in the open-task dedup set — new gap per mandate 2. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
grep -A6 'id: mini-wallabag' foss-setup/verification/checks.d/mini-services.yaml
  cmd: curl -sf -m 8 http://localhost:8085/api/info | grep -o '"appname":"wallabag"'
  expect: '^"appname":"wallabag"$'  severity: warn  task_id: read-07
grep -ril wallabag foss-setup/verification/checks.d/ -> only mini-services.yaml (one check total)
kuma monitor: 21  Mini Wallabag  1  http  http://192.168.10.2:8085 (bare HTTP)
```

</details>

### UL119. unsloth-studio has no wiki service page (404) — downstream of fix-68 catalog gap `known-issue`
**Host:** mini · **Component:** wiki · **Auditor:** svc:wiki · **Work item:** `fix-97`

https://wiki.tabaska.us/services/unsloth-studio/ returns 404. The MkDocs service pages are generated from service-catalog.yaml (gen-wiki-services), and unsloth-studio (lai-28, landed 2026-08-19) is absent from the catalog — this is exactly the fix-68 catalog-vhost-parity failure ('VHOST-NOT-IN-CATALOG: [principal-ai, unsloth]') and the verify-06 containers-manifest-rig failure ('> unsloth-studio'). So the missing wiki page is a downstream symptom, not a wiki-generator defect: adding the catalog row (fix-68) will produce the page on next build. NOT fixed per read-only mandate. Every other sampled service page (immich, homepage index) renders 200.

<details><summary>Evidence</summary>

```
curl -sk --resolve wiki.tabaska.us:443:192.168.10.2 https://wiki.tabaska.us/services/unsloth-studio/ -> HTTP 404
results.json: catalog-vhost-parity=fail 'VHOST-NOT-IN-CATALOG: [principal-ai, unsloth]'; containers-manifest-rig=fail '> unsloth-studio'
ssh mini ls /opt/stacks/wiki/site/services/ -> no unsloth-studio dir
```

</details>

### UL120. STILL-OPEN-VALID: subtitle fetching works (689 fetched, 2 providers) but min-score cutoff raise + throttled backlog drain remains `known-issue`
**Host:** nas · **Component:** Bazarr / subtitle backlog (fix-77) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-77`

fix-59's restoration is green: providers=2 good=2, 689 subs fetched, sonarr+radarr SignalR LIVE, movies=287 series=168. The remaining fix-77 work (raise series/movie minimum-score to accept ~86-score gestdown results + run a throttled backlog batch in a 4-7AM window; optional provider key) is an optimization not measured by the liveness checks. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
bazarr-providers-can-fetch [pass]: 'BAZARR_SUBS_OK providers=2 good=2 fetched=689'
bazarr-synced-from-arrs [pass]: 'BAZARR_OK movies=287 series=168 sonarr=LIVE radarr=LIVE'
```

</details>

### UL121. Wanted-subtitle backlog re-quantified: 2154 episodes / 2 movies -- draining, NOT worsened vs baseline `known-issue`
**Host:** nas · **Component:** Bazarr wanted-subtitle backlog (fix-77) · **Auditor:** flow:subtitles · **Work item:** `fix-77`

Task asked whether the fix-77 backlog worsened. Baseline recorded in fix-77 task: '2868-episode/29-movie backlog'. Live re-quantify 2026-08-23 via Bazarr /api/episodes/wanted + /api/movies/wanted (badges corroborate): episodes=2154, movies=2. That is a DECREASE of 714 episodes and 27 movies -> the backlog is draining as intended (4-7AM throttled batches per fix-77 plan), not regressing. Providers badge=0 (no throttled/errored providers). The backlog remains large in absolute terms (2154 episodes) but is covered by OPEN task fix-77 ('Drain the Bazarr subtitle backlog + optional provider-key upgrade', host nas, depends_on fix-59) -- so known_issue. No action taken (read-only mandate); this is a re-verification data point, not a new defect.

<details><summary>Evidence</summary>

```
fix-77 tasks.json summary: '...the 2868-episode/29-movie backlog is draining...'
$ ssh mini 'KEY=$(sudo grep -oP "BAZARR_API_KEY=\K\S+" /etc/verification/env); BAZARR_API_KEY=$KEY python3 -c "...wanted..."'
WANTED_EPISODES=2154 WANTED_MOVIES=2
BADGES_WANTED_EP=2154 BADGES_WANTED_MOV=2 BADGES_PROVIDERS=0
SIGNALR sonarr=LIVE radarr=LIVE
```

</details>

### UL122. /volume1/manga (1.9G downloaded manga CBZ) is NOT in the Hyper Backup->B2 set — closes UNPROBED #737
**Host:** nas · **Component:** Hyper Backup (S3 Backup enc) include-list / /volume1/manga · **Auditor:** completeness-critic · **Work item:** `fix-93`

Closing the one UNPROBED leg (#737) that had answerable data the manga lane did not cross-reference. I read synobackup.conf first-hand: the fleet has exactly one Hyper Backup task (task_3 'S3 Backup enc') and its include list is backup_folders=["/backups","/docker","/docs","/homes","/photo"]. The Suwayomi manga content share /volume1/manga (1.9G of downloaded CBZ, per rig mount //192.168.10.4/manga) is NOT in that list, so it is NOT captured by the nightly B2 Hyper Backup. This is CONSISTENT with the fleet's media-exclusion philosophy (config backed up, bulk regenerable media excluded) — Suwayomi's config+library DB lives under /volume1/docker/suwayomi which IS backed up, so on a restore the library+sources survive and chapters are re-downloadable from sources. However, unlike music/books/games/youtube/stash/frigate/PlexMediaServer/vault, the 'manga' share is NOT in the DR notes' documented excluded/regenerable list either — it is an UNDOCUMENTED implicit exclusion. Recommend the operator either confirm manga is intentionally regenerable-tier (and add it to the documented exclude list) or add /volume1/manga to a backup task. NOT changed per read-only mandate. Not covered by an existing open task (the media-tier backup policy is a doc gap, not a tracked item).

<details><summary>Evidence</summary>

```
$ PW=... ; printf '%s\n' "$PW" | ssh nas "sudo -S sh -c 'grep -h backup_folders /var/packages/HyperBackup/etc/synobackup.conf; grep -h -E \"^\\[task_|^name=\" ...'"
backup_folders=["/backups","/docker","/docs","/homes","/photo"]
---
name=""
[task_3]
name="S3 Backup enc"
(only one task; /manga absent from include list)
# corroborated by finding #859 (same synobackup.conf grep) and #852 (DR note: excluded regenerable = music,books,games,youtube,stash,frigate,PlexMediaServer,vault — 'manga' listed in NEITHER include nor documented-exclude)
$ ssh rig 'du -sh /mnt/nas-manga' -> 1.9G  /mnt/nas-manga  (//192.168.10.4/manga -> /volume1/manga)
```

</details>

### UL123. STILL-OPEN-VALID: Kaelyn Tabaska still 0 photos/0 videos in Immich (human leg — needs her device) `known-issue`
**Host:** nas · **Component:** Immich / immich-user-zero-assets (fix-71) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-71`

fix-71 condition holds unchanged: second household user has never backed up. This is a by-design-red check that only clears when assets flow from her phone; a human-boundary leg, not agent-fixable. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
immich-user-zero-assets [fail]: out='per_user=ZERO:Kaelyn Tabaska'
```

</details>

### UL124. 3 stale duplicate franchise playlists linger in Plex beside the managed copies (housekeeping cruft, not a break)
**Host:** nas · **Component:** Plex playlists (Kometa-built, on NAS) · **Auditor:** flow:kometa · **Work item:** `fix-103`

The Plex /playlists listing shows two entries each for 'DC Animated Universe (Timeline Order)', 'Star Trek (Timeline Order)', and 'Star Wars (Timeline Order)'. The fresh/managed copies (ratingKeys 60939 leaf=537 updated 2026-08-16, 60941 leaf=11 updated 2026-07-18, 60943 leaf=32 updated 2026-08-06) match the current run summary exactly. The duplicates (ratingKeys 60940 leaf=530, 60942 leaf=10, 60944 leaf=31) are all frozen at updatedAt 2026-07-10 -- Kometa has not touched them in ~6 weeks, so they are orphaned copies (contiguous keys 60939-60945 suggest a double-create on 2026-07-10). Consumer impact: a user browsing Plex playlists sees duplicate titles, one slightly outdated (7/1/1 fewer items). Not a functional break -- both play; the correct managed playlist is present and current. NOT fixed per read-only mandate. Not covered by any open task or the pre-existing failure baseline. Recommend a human delete ratingKeys 60940/60942/60944 in the 4-7AM window and check why the 2026-07-10 run forked duplicates.

<details><summary>Evidence</summary>

```
$ curl -sm20 "$PLEX_URL/playlists?playlistType=video&X-Plex-Token=$PLEX_TOKEN" | parse title|leaf|updatedAt|ratingKey (Timeline Order only):
DC Animated Universe (Timeline Order) | leaf=537 | updated=2026-08-16T05:00:54 | key=60939
DC Animated Universe (Timeline Order) | leaf=530 | updated=2026-07-10T05:03:09 | key=60940
Star Trek (Timeline Order)            | leaf=11  | updated=2026-07-18T05:01:02 | key=60941
Star Trek (Timeline Order)            | leaf=10  | updated=2026-07-10T05:10:28 | key=60942
Star Wars (Timeline Order)            | leaf=32  | updated=2026-08-06T05:02:39 | key=60943
Star Wars (Timeline Order)            | leaf=31  | updated=2026-07-10T05:11:35 | key=60944
```

</details>

### UL125. iptorrents-idsearch-returns-results=0 is a TRANSIENT probe flap, not indexer misbehavior — IPT is healthy (100 items live, 5/600 budget used)
**Host:** nas · **Component:** Prowlarr -> IPTorrents (id=1) newznab imdbid probe (media-indexers.yaml iptorrents-idsearch-returns-results) · **Auditor:** triage:arr-grab-source-not-storming · **Work item:** `fix-100`

This is the check cross-referenced by the mission as suggesting IPT misbehavior/junk-grab risk. Root-caused: it is a single-shot flap, NOT a real failure, and there is NO junk-grab risk. Evidence trail: it returned 100 items at 10:29 this morning (PASS), 0 in tonight's audit run (FAIL), and 100 on my live re-probe just now. It has NEVER appeared in mini triage failure history since it was added 2026-08-11 (commit ffd966a note: 'live run = 100 items'), so the tt-prefixed imdbid=tt0133093 is fine. I disproved every real-fault hypothesis: (1) budget NOT exhausted — Prowlarr indexerStats show IPT used only q=5 of its 600/24h search budget in the last 24h (grabs=4, authFail=0); (2) caps fine — Prowlarr indexer id=1 IS IPTorrents and its movieSearchParams include imdbId (no ID-skip); (3) not disabled — /api/v1/indexerstatus is empty (no failing/disabled indexers). The check does a single ssh nas -> 'curl -sm 60' with no retry and treats an empty/timed-out body as items=0; under tonight's flagged heavy NAS IO load, a 60s curl timeout (slow DB scan / upstream) is the most plausible cause of the one-off 0. Self-clearing flap; check is fragile (single-shot, 60s, no retry). Not covered by an open task (the yaml task_id verify-06 tags a different check). NOT fixed per read-only mandate; candidate remediation is a retry/backoff before FAIL.

<details><summary>Evidence</summary>

```
this-morning results.json (10:29 EDT): iptorrents-idsearch-returns-results | pass | ipt_idsearch_items=100
tonight audit run: fail | ipt_idsearch_items=0
triage history grep (iptorrents-idsearch|ipt_idsearch across all /var/lib/verification/triage-*.md): 0 HITs (never failed before tonight)
$ python3 /tmp/prowlarr_budget.py  (on nas, key from config.xml)
=== indexerStats last 24h ===
  1 IPTorrents  q=5 grabs=4 rssQ=429 authFail=None avgResp=413
=== live idsearch (t=movie imdbid tt0133093 on indexer 1): items=100 ===
=== live plain text search 'matrix' on indexer 1: results=100 ===
$ python3 /tmp/prowlarr_inspect.py  (on nas)
    1 | IPTorrents | en=True | torrent | private | movieParams=['q', 'imdbId'] | tvParams=['q','season','ep','imdbId']
=== indexer status (disabled/failing) ===  (none disabled/failing)
```

</details>

### UL126. 5 monitored series on default 'Any' quality profile (fix-45) `known-issue`
**Host:** nas · **Component:** Sonarr quality profiles · **Auditor:** flow:movies-tv · **Work item:** `fix-94`

Known fix-45: 5 monitored Sonarr series are still on qualityProfileId=1 (the default/Any profile, unmanaged) — Teen Titans Go!, Animaniacs, Freakazoid!, The Grim Adventures of Billy & Mandy, Johnny Bravo. These can grab low-quality/oversized releases. Consumer impact is soft (still imports and plays). Note Animaniacs overlaps the stuck-grab item above. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
[22:23 run] sonarr /api/v3/series filter qualityProfileId==1 & monitored -> PROFILE_BAD Teen Titans Go!,Animaniacs,Freakazoid!,The Grim Adventures of Billy & Mandy,Johnny Bravo
```

</details>

### UL127. fix-55 arr 'database is locked' storm RE-OCCURRED & worsened (recurring nightly, remediation intact) `known-issue`
**Host:** nas · **Component:** arr SQLite (lidarr:8686 / radarr:7878 / whisparr:6969) · **Auditor:** triage:arr-sqlite-not-locked · **Work item:** `fix-91` · *skeptic-confirmed*

The fix-55 regression guard (arr-sqlite-not-locked) FAILED at the 22:23 EDT audit run with a genuine storm, and it is not a transient one-off: 'database is locked' errors recur in heavy nightly crests. This is the consumer-end companion to the NAS IO-pressure storm (nas-io-pressure also fired at 22:23 with load15=26.57; sibling lane owns the IO driver root-cause). fix-55 was marked DONE 2026-08-02 and is NOT in today's reopen bridge/morning baseline, so it silently re-broke = per the audit contract a new finding. Peak IO 26.57 EXCEEDS the original fix-55 storm range (17-22) = worsened. Root-cause of the LOCKS: NAS disk fsync during scheduled-task/API bursts runs slower than the arrs' SQLite busy_timeout -> SQLITE_BUSY -> 'database is locked' -> API 500s (GET /api/v1/history, GET /api/v3/movie) + failed scheduled tasks. Locking operations (by logger): CommandExecutor, TaskExtensions, EventAggregator, FetchAndParseRssService, DownloadDecisionMaker, Torznab, HousekeepingService, RefreshMovieService, RefreshAlbumService. The fix-55 workload remediation is VERIFIED STILL IN PLACE (bitmagnet DHT_CRAWLER_SCALING_FACTOR=3 live env + compose; json-file log caps max-size 10m/max-file 3) — so the recurrence is NOT config drift; an additional/larger nightly IO hog now saturates the DS920+ beyond what scaling=3 mitigates. Currently subsided (see live re-run). NOT fixed per read-only mandate; recommend REOPEN fix-55 (known_issue). known_issue=true cites fix-55.

*Severity adjusted high→low during adversarial verification.*

*Verify note:* Transient Saturday Hyper-Backup-window artifact, not a chronic HIGH worsening regression. The storm run (2026-08-22 22:23 EDT) fell on a SATURDAY — the routine weekly Synology image-backup window; the storm hog was synoimgbkptool (per companion idx22), NOT bitmagnet, so 'reopen fix-55' (bitmagnet DHT throttle) is a misattribution and irrelevant. Fresh probes ~19h later (Sun 2026-08-23 17:46 EDT; mini and NAS clocks agree = no skew, no stale cache) show full self-clear: lock count LIVE=0/0/0 status OK, io load15=10.24 status OK (<12), no backup/IO hog in D-state (only md0_raid1), and all arr WAL files checkpointed back to tiny (lidarr 57KB / radarr 225KB / whisparr2 60KB — far below the ~1.5MB healthy-by-day mark) with DBs actively writing (mtimes 17:43-17:47, not locked/write-dead). The 22:23 STORM (locks=20) genuinely occurred, so not fully REFUTED, but the peak 26.57 was a backup-crest spike, not a chronic elevated baseline; lane-context rule 'a backup-window spike that self-clears is NOT a regression' applies. Real but bounded consumer impact (arr API 500s during the ~00-01Z crest) => LOW.

<details><summary>Evidence</summary>

```
results.json (2026-08-22T22:23:20-04:00): arr-sqlite-not-locked | fail | arr_locked_last15m=20 max=5 status=STORM [lidarr=10 radarr=4 whisparr=6]; nas-io-pressure | fail | nas_io_load15=26.57 threshold=12 status=HIGH
---
Live re-run (ssh mini, 15:22 EDT, keys from /etc/verification/env via grep+eval, not sourced):
$ python3 /opt/verification/bin/nas-io-storm-probe.py locks -> arr_locked_last15m=0 max=5 status=OK [lidarr=0 radarr=0 whisparr=0]
$ python3 /opt/verification/bin/nas-io-storm-probe.py io   -> nas_io_load15=0.90 threshold=12 status=OK
---
Lock-history from arr log APIs (pageSize=250, level=error):
lidarr: error_records=250 lock_records=242 oldest=2026-08-22T02:25:19Z newest=2026-08-23T18:03:03Z
radarr: error_records=162 lock_records=127 oldest=2026-08-16T00:00:52Z newest=2026-08-23T10:15:32Z
whisparr: error_records=250 lock_records=250 (100%) oldest=2026-08-22T00:04:09Z newest=2026-08-23T07:02:24Z
FLEET locks per UTC hour: 22T23Z=52 23T00Z=107 23T01Z=105 23T02Z=39 23T03Z=30 23T04Z=5 23T07Z=11 (crest ~00-01Z = 20:00-21:00 EDT)
sample msgs: 'Request Failed. GET /api/v1/history: database is locked'; '[GET /api/v3/movie]: database is locked'; 'Couldnt rescan movie [Heathers (1989)]: database is locked'; whisparr 'Task Error: database is locked'
---
Remediation intact (ssh nas, sudo docker inspect + compose grep):
DHT_CRAWLER_SCALING_FACTOR=3
compose: '- DHT_CRAWLER_SCALING_FACTOR=3'  '# fix-55 (2026-08-02): throttle the DHT crawler'  logging max-size '10m' max-file '3'
```

</details>

### UL128. Intermittent podcast RSS fetch errors for Patreon-gated feeds (external, non-fatal)
**Host:** nas · **Component:** audiobookshelf · **Auditor:** svc:audiobookshelf · **Work item:** `fix-103`

Logs since 2026-08-02 (5032 lines, no retry storm) contain recurring PodcastManager/podcastUtils ERRORs for Patreon-hosted feeds: getaddrinfo EAI_AGAIN www.patreon.com, AxiosError timeout of 30000ms (ECONNABORTED), and 'invalid feed payload ... null' for shows Hell of Presidents, Hell on Earth, The Players Club, MinnMax Exclusive Audio, Movie Mindset, Time For My Stories. These are external content-source failures (Patreon-authenticated/rate-limited feeds + transient NAS DNS), NOT an ABS defect: the poller runs on schedule and other feeds fetch fine (The Players Club got an Aug 19 episode, Kit & Krysta an Aug 21 episode). Several of these feeds show 'No latest episode' persistently, meaning those subscriptions never yield downloads. NOT fixed per read-only mandate; flagged as a content/subscription-hygiene caveat. Not covered by an existing open task.

<details><summary>Evidence</summary>

```
$ docker logs audiobookshelf --since 2026-08-02T00:00:00 | grep -iE 'error|ECONN'
[2026-08-11 22:08:59] ERROR: [podcastUtils] getPodcastFeed Error AxiosError: getaddrinfo EAI_AGAIN www.patreon.com
[2026-08-06 01:01:28] ERROR: [podcastUtils] getPodcastFeed Error [AxiosError: timeout of 30000ms exceeded] code: 'ECONNABORTED'
[2026-08-06 01:01:28] ERROR: [PodcastManager] checkPodcastForNewEpisodes invalid feed payload for Hell on Earth ... null
# recent tail (2026-08-23) confirms poller still active but these feeds return nothing:
[2026-08-23 16:00:23] INFO: [PodcastManager] runEpisodeCheck: "Hell of Presidents" | No latest episode
[2026-08-23 16:00:43] INFO: [PodcastManager] runEpisodeCheck: "Hell on Earth" | No latest episode
```

</details>

### UL129. Recurring ffprobe 'cannot analyze this video file' errors on old junk .avi rips (~800 events)
**Host:** nas · **Component:** bazarr · **Auditor:** svc:bazarr · **Work item:** `fix-103`

docker logs since 2026-08-02 contain 3188 error-matching lines, dominated by video_analyzer:325 'BAZARR ffprobe cannot analyze this video file ... Could it be corrupted?' with CalledProcessError exit 1, repeating across [BloodLogic] Mission Hill S1 .avi files (~800 multi-line events; fresh, last seen 2026-08-23 10:17). These are old/low-quality .avi rips whose codecs ffprobe (v...) rejects, so Bazarr cannot fingerprint them to manage subtitles for those specific files. Taxonomy-8 adjacent (junk media) — a library data-quality issue, not a Bazarr fault; it does not affect healthy media (the 689-sub fetch history proves the pipeline works). No crash loop, no auth rot, no NUL-corruption (--since read cleanly). Cosmetic log noise + a handful of unmanageable episodes; not covered by an existing open task. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ nas docker logs bazarr --since 2026-08-02 | grep -ic 'error|exception|traceback|throttl|denied|429|403' -> 3188
tail: 2026-08-23 10:17:12 ERROR (video_analyzer:325) - BAZARR ffprobe cannot analyze this video file /tv/Mission Hill/Mission Hill - Season 1/... [BloodLogic].avi. Could it be corrupted?
  subprocess.CalledProcessError: Command '[/usr/bin/ffprobe ...]' returned non-zero exit status 1.  (repeats across S1E01/E03/E07)
log dir du: 664K (no bloat)
```

</details>

### UL130. fix-77 subtitle backlog still 2154 episodes wanted, but actively DRAINING (not worsened) `known-issue`
**Host:** nas · **Component:** bazarr · **Auditor:** svc:bazarr · **Work item:** `fix-77`

Re-verified the open fix-77 backlog now vs the fix-59/fix-77 baseline ('2868-episode/29-movie backlog'). Live badges: episodes_missing_subtitles=2154 (down 714 / ~25% from 2868), movies_missing_subtitles=2 (down 27 / ~93% from 29). Movie fetch history=27 exactly matches the 27 movies drained. So the backlog is draining as designed, NOT worsened — no regression. fix-77 (required:false, media-polish, depends fix-59) remains legitimately OPEN: 2154 episode subs still wanted, and its suggested levers (raise min-score cutoff for gestdown ~86-score results + throttled 4-7AM batch, optional OpenSubtitles/subsource key) are un-actioned. NOT fixed per read-only mandate. known_issue: fix-77.

<details><summary>Evidence</summary>

```
$ live badges: {"episodes": 2154, "movies": 2, ...}  (baseline per tasks.json fix-77 summary + media-subtitles.yaml comment: '2868-episode + 29-movie backlog')
Delta: episodes 2868->2154 (-714), movies 29->2 (-27); MOVIE_HISTORY=27 == movies drained
```

</details>

### UL131. Frozen-green corroborated: beets DB 0 items, no tagging in 46 days, freshness check green on log-mtime only (pattern #13) `known-issue`
**Host:** nas · **Component:** beets (YouTube-audio tagging layer) · **Auditor:** flow:music · **Work item:** `fix-89`

Corroborates the prior-audit frozen-green finding named in my chain notes. The nas-beets-ingest-fresh check passes because import.log mtime is touched daily by the 03:15 cron, but every run only logs 'skip /music/YouTube' and imports nothing. beets-youtube.db has 0 items and is frozen at 2026-07-08T10:18 (46 days). Only 2 files exist under /music/YouTube (both July 7-8), both left un-tagged (weak-match quarantine per quiet_fallback:skip). This is zero-throughput-green: the freshness check measures log mtime, not tagging throughput. Behavior is by-design (skip weak matches, never move files) and there is no new MeTube input, so no music-consumer impact — but the monitoring signal is misleading. NOT fixed per read-only mandate; recommend a throughput-based check (DB item count / max(added) age) rather than log mtime.

<details><summary>Evidence</summary>

```
sqlite3 -readonly beets-youtube.db 'select count(*),datetime(max(added)) from items;' -> 0|  (null)
ls beets-youtube.db -> 2026-07-08T10:18 (mtime 46d)
tail import.log -> repeating: 'import started <daily>' then 'skip /music/YouTube'
ls /volume1/music/YouTube -> only 'Me at the zoo.mp3' (2026-07-07), 'Numb ... Linkin Park.mp3' (2026-07-08)
config.yaml -> import: copy:no move:no quiet_fallback:skip (tag-in-place, quarantine-by-skip)
nas-beets-ingest-fresh (baseline) -> ingest=fresh (import.log -mmin -1800)
```

</details>

### UL132. Beets tags zero items and its freshness monitor green-masks that zero-throughput `known-issue`
**Host:** nas · **Component:** beets YouTube-audio tagging layer + nas-beets-ingest-fresh check (nas-30) · **Auditor:** flow:youtube · **Work item:** `fix-89`

Corroborates the 'beets frozen' known. beets daily cron DOES fire (import.log mtime 2026-08-23 03:15:33, today), so nas-beets-ingest-fresh passes (ingest=fresh). But the ONLY thing every run logs, for >=10 consecutive days (Aug 14..Aug 23), is 'import started ... / skip /music/YouTube' — zero tracks imported. beets-youtube.db mtime is frozen at Jul 8 10:18 and contains 0 items. Root cause is benign, not a crash: the source dir /volume1/music/YouTube holds only 2 files, both from Jul 7-8 ('Me at the zoo' by jawed, 'Numb (Official Music Video) [4K UPGRADE] – Linkin Park'), and both are weak MusicBrainz matches that beets quarantines-by-design (copy:no/move:no/quiet_fallback:skip). No new MeTube audio has arrived since Jul 8. So the tagging layer has produced 0 successful tags in its lifetime. The consumer is NOT broken: both tracks still reach Navidrome untagged (fromfilename) — see the separate green finding. The real defect is monitoring: nas-beets-ingest-fresh only checks import.log mtime, so it green-masks zero-throughput (taxonomy #2/#13). NOT fixed per read-only mandate; recommend the check assert a tagged-item count or newest-import delta, not just log freshness. Covered by nas-30.

<details><summary>Evidence</summary>

```
stat import.log: 2026-08-23 03:15:33 -0400 (fresh) => check passes ingest=fresh
tail import.log: 'import started Sun Aug 23 03:15:32 2026' then 'skip /music/YouTube' (identical every day Aug14..Aug23)
beets-youtube.db mtime: Jul 8 10:18 ; items count: 0
find /volume1/music/YouTube -type f => 2 files, newest 2026-07-08 10:31
```

</details>

### UL133. No Homepage tile for bookshelf while every other arr backend has one
**Host:** nas · **Component:** bookshelf/homepage · **Auditor:** svc:bookshelf · **Work item:** `fix-102`

Bookshelf has a catalog row (url https://bookshelf.tabaska.us) and a working Caddy vhost (nas-bookshelf pass 302; catalog-vhost-parity pass), but no Homepage tile. Sonarr, Radarr, Lidarr, Prowlarr, and Whisparr all render tiles; the only book-adjacent tiles are Audiobookshelf and BookLogr. Minor UX/monitoring-surface consistency gap — plausibly deliberate since bookshelf is being superseded by shelfmark as the request frontend, but worth noting. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini curl -s -H 'Host: home.tabaska.us' localhost:3010/api/services | grep name=(Sonarr|Radarr|Lidarr|Prowlarr|Whisparr|Bookshelf|Readarr)
-> Lidarr, Prowlarr, Radarr, Sonarr, Whisparr  (no Bookshelf/Readarr)
-> book-name tiles present: Audiobookshelf, BookLogr only
```

</details>

### UL134. Recurring cosmetic log noise: author display-order errors, auto-zipper 'no files to zip', startup version/permission warnings
**Host:** nas · **Component:** calibre-web-automated · **Auditor:** svc:calibre-web-automated · **Work item:** `fix-103`

Since 2026-08-02, logs carry benign-but-noisy lines and NO real failures (no crash loop, no >1000-line retry storm, no 5xx, no NUL-corruption). cps.db:1103 'Author X not found to display name in right order' recurs on library browse (08-13, 08-20) for a handful of inconsistently-entered names ('Martin, George R.R.', 'Colfer,Eoin' [missing space], 'Jacqueline, Carey' [order reversed]) — Calibre-Web can't reverse the stored 'Last, First' string and falls back to raw display; cwa-library-author-split still passes AUTHOR_SPLITS=NONE so no pipe/comma split corruption. '[cwa-auto-zipper] Failed - no files found to zip' recurs = idle zipper with nothing to zip (not a failure). '[cwa-init] Failed to fetch stable version via jq (network/timeout)' + 'could not successfully set permissions for /app/calibre-web-automated' are cosmetic LSIO startup warnings. NOT actioned per read-only mandate.

<details><summary>Evidence</summary>

```
docker logs --since 2026-08-02 | grep -iE 'error|fail':
[2026-08-20 17:39:23] ERROR {cps.db:1103} Author 'Martin, George R.R.' not found to display name in right order
... 'Colfer,Eoin' ... 'Jacqueline, Carey' ...
[cwa-auto-zipper] Failed - no files found to zip.  (x many)
[cwa-init] Failed to fetch stable version via jq (network/timeout issue)
[cwa-init] Service could not successfully set permissions for '/app/calibre-web-automated'
audit: cwa-library-author-split=pass AUTHOR_SPLITS=NONE
```

</details>

### UL135. 50h dead-man window carries a 40-day-old 'tighten to ~30h once schedule confirmed daily' TODO that was never actioned
**Host:** nas · **Component:** checks.d/backups.yaml: nas-hyperbackup-b2-fresh · **Auditor:** meta:backups · **Work item:** `fix-100` · *skeptic-confirmed*

The check comment (2026-07-13) says the -mmin -3000 (50h) window is provisional pending confirming the DSM Hyper Backup schedule is daily. Live: last_version_inodedb mtime is 2026-08-21 22:15:31 EDT (~24h old at probe time), consistent with a nightly ~22:15 run. At 50h, a crit Tier-1 offsite backup can silently miss one full night plus most of a second before alerting. The tightening needs one human glance at the DSM UI schedule (needs-live-verify: cadence inferred here from a single mtime observation, not the schedule itself — hence medium confidence). Check design itself is a sound, negative-tested intermediate dead-man; this is threshold staleness only. NOT changed per read-only mandate.

*Verify note:* Holds on independent probe. backups.yaml L70-73 has the 50h/3000m window + "tighten to ~30h" TODO; git -L 70,78 shows only commit 7184614 (2026-07-13) touched those lines = never re-tightened (~41d). Fresh NAS stat (22:24 EDT last night) confirms nightly cadence, so the tighten is warranted. Low severity apt: this crit dead-man can miss ~2 nights before firing. Not refutable.

<details><summary>Evidence</summary>

```
backups.yaml comment: 'Window 50h (3000m): ... Tighten to ~30h once the schedule is confirmed daily in the DSM UI.' (dated 2026-07-13)
$ ssh nas 'stat -c "%y %s %n" /volume1/@img_bkp_cache/ClientCache_cloud_image_aws_s3.*/last_version_inodedb'
2026-08-21 22:15:31.560979921 -0400 88739840 /volume1/@img_bkp_cache/ClientCache_cloud_image_aws_s3.L35Ey1/last_version_inodedb
Today's run: nas-hyperbackup-b2-fresh | pass | tok=ok
```

</details>

### UL136. Catalog understates beets: says ui:false/port:null but a web UI serves on :8337
**Host:** nas · **Component:** configs/docker-stack/service-catalog.yaml (beets row) · **Auditor:** svc:beets · **Work item:** `fix-102`

The service-catalog beets row records port:null, url:null, ui:false, notes 'Music tagger/importer worker - no UI'. In reality the linuxserver/beets image's always-on service is 'beet web', which serves a library browser on :8337 (published + LAN-bound host:0.0.0.0), and it is actively monitored by the nas-beets check ('curl http://nas:8337/' -> 200). The catalog entry is defensible as a background-worker description, but it is inconsistent with the monitored web endpoint - a reader/consumer would not know :8337 exists. Cosmetic/doc-accuracy only. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
service-catalog.yaml:180-187
  - name: beets
    port: null
    url: null
    ui: false
    notes: Music tagger/importer worker - no UI; ...

but live: sudo docker logs beets -> ' * Running on http://172.19.0.11:8337'
and check nas-beets (nas-services.yaml:172): curl http://nas:8337/ expect ^200$ -> pass
```

</details>

### UL137. Monitoring is liveness-only — no consumer-grade check for scan freshness or notification delivery (mandate-2 gap)
**Host:** nas · **Component:** diun / verification checks.d · **Auditor:** svc:diun-nas · **Work item:** `fix-100` · *skeptic-confirmed*

The only diun-nas check is alert-diun-nas-up (checks.d/alerting.yaml:35), which asserts `docker inspect .State.Status == running`. This is pure liveness (taxonomy 2). If the daily scan froze (poller stall) or the ntfy notification path auth-rotted (token revoked / ntfy ACL change — taxonomy 11/13), the container would stay 'running' and the check would stay GREEN while the fleet goes blind to image updates. There is no check asserting last-cron-cycle recency (e.g. a log 'Cron triggered' within 26h) or ntfy topic 'diun' message freshness. Per standing mandate 2 (100% CONSUMER-grade coverage), this is a coverage-quality gap, not a live outage — the feature is proven working today. NOT fixed per read-only mandate; recommend a scan-freshness or ntfy-topic-freshness consumer check. Note the mini sibling alert-diun-mini-up at least checks .State.Health.Status==healthy; the NAS compose defines no healthcheck so even that stronger form isn't available here.

*Verify note:* Fresh independent probe reproduced every claim. Read alerting.yaml directly: alert-diun-nas-up (L35-45) asserts only .State.Status==running (liveness); alert-diun-mini-up (L25-33) asserts .State.Health.Status==healthy. A repo-wide grep of checks.d finds ONLY these two diun IDs — no scan-freshness ("Cron triggered" recency) or ntfy-topic freshness check exists, and the coverage manifest (nas.containers/mini.containers L10) lists diun, so the mandate-2 tripwire is satisfied by the liveness check alone. Live NAS logs confirm the finding's premise both ways: diun IS running and IS a daily-cron poller (Cron triggered every day 06:30 EDT, latest 23 Aug 06:30 today, "Found 31 image(s) to analyze"), so (a) the feature is proven working today and (b) a .State.Status==running check genuinely cannot detect a stalled cron/scan (taxonomy #13) or an ntfy auth-rot — exactly the blind spot claimed. No refutation vector applies: I read source directly (right vantage), NAS log timestamps are current (no stale/RTC issue), not a check-bug, and the coverage-manifest listing is consistent with the gap rather than contradicting it. Severity stays low: honestly scoped as a coverage-quality gap (not an outage) and diun is a low-stakes advisory notifier, but it is a legitimate mandate-2 consumer-coverage gap on a genuine poller. known_issue=false stands (no open task tracks a diun consumer check).

<details><summary>Evidence</summary>

```
$ grep -n diun foss-setup/verification/checks.d/alerting.yaml
35:  - id: alert-diun-nas-up
36:    name: "Diun (NAS) container running"
40:    cmd: sudo -n /usr/local/bin/docker inspect -f '{{.State.Status}}' diun
41:    expect: '^running$'
# grep -rin diun checks.d → only alert-diun-mini-up + alert-diun-nas-up; no scan-freshness / notification-delivery check exists
```

</details>

### UL138. NAS secondary resolver has intermittent external-resolution failures (Quad9 DoH EOF flood) `known-issue`
**Host:** nas · **Component:** dns / AdGuard-NAS secondary -> Quad9 DoH · **Auditor:** flow:edge-dns · **Work item:** `fix-89`

KNOWN issue (adguard-nas Quad9 DoH EOF flood, previously found). NAS AdGuard secondary (192.168.10.4) upstream is https://dns10.quad9.net/dns-query (DoH). Internal names resolve reliably (home.tabaska.us->192.168.10.2). External resolution is intermittent: one probe returned empty on first try, then a 5-retry burst succeeded 5/5. It is a functional secondary that recovers on retry, not a hard break -- but the first-try empty confirms the EOF flood is still live. NOT fixed per read-only mandate. Contributes the DNS caveat to this lane's AMBER.

<details><summary>Evidence</summary>

```
dig +short @192.168.10.4 example.com -> (empty)  # first try
for i in 1..5: dig +short @192.168.10.4 example.com -> 172.66.147.243 / 104.20.23.154 (5/5 OK)
ssh nas sudo grep -A1 upstream_dns adguard-nas/conf/AdGuardHome.yaml -> - https://dns10.quad9.net/dns-query
# results.json dns-nas-external uses a 3x retry loop and PASSes
```

</details>

### UL139. Backup dead-man matches ANY fresh *.tar in /volume1/backups — a non-automatic tar can mask a dead 04:45 schedule; no size floor
**Host:** nas · **Component:** ha-backup-offsite-fresh (crit dead-man) · **Auditor:** meta:ha · **Work item:** `fix-100`

The check counts find /volume1/backups -maxdepth 1 -name '*.tar' -mmin -2880. The directory demonstrably accumulates non-automatic tars (Matter_Server_9.0.3_2026-07-18 add-on partial backup, acceptance-nas-offsite-verify_2026-07-13 test artifact): if the daily automatic full backup silently stopped, any manual/partial/add-on tar landing within 48h keeps the crit check green. It also accepts a 0-byte tar. Today it is legitimately green: Automatic_backup_2026.7.2_2026-08-22_04.45 (24.3 MB) landed on schedule, fresh-count 2 (Aug 22 + Aug 21), retention-3 visible. Suggested hardening (not applied — read-only): tighten the glob to 'Automatic_backup_*.tar' and add -size +1M. Env dependency NAS_SUDO_PASSWORD confirmed present in mini /etc/verification/env; stderr fully routed to /dev/null so the expect regex only sees the intended stdout token.

<details><summary>Evidence</summary>

```
$ ssh nas 'ls -lt /volume1/backups/ | head -8' -> Automatic_backup_2026.7.2_2026-08-22_04.45_00003126.tar (Aug 22 04:45, 24279040 B); ..._08-21...; ..._08-20...; Matter_Server_9.0.3_2026-07-18_21.33_37791659.tar; acceptance-nas-offsite-verify_2026-07-13_14.53_45529549.tar
$ ssh nas 'find /volume1/backups -maxdepth 1 -name "*.tar" -mmin -2880 | wc -l' -> 2
$ ssh mini 'sudo grep -c "^NAS_SUDO_PASSWORD=" /etc/verification/env' -> 1
```

</details>

### UL140. immich-user-zero-assets warn: Kaelyn Tabaska has 0 photos/0 videos — human onboarding leg (fix-71 OPEN) `known-issue`
**Host:** nas · **Component:** immich (photos.tabaska.us / nas:2283) · **Auditor:** triage:immich-user-zero-assets · **Work item:** `fix-71`

Known residual, unchanged and NOT worsened. The fix-60 per-user-zero check reports per_user=ZERO:Kaelyn Tabaska because the second household user has never had a single asset backed up. Live re-verify (2026-08-23 EDT) against Immich /api/server/statistics shows exactly 2 users: Brandon Tabaska (36,208 assets — backup flowing healthy) and Kaelyn Tabaska (0). Only one zero-asset user, the same one as every prior day. Triage-AI history recorded this identically 2026-08-03 through 2026-08-15 (diagnosis 'user Kaelyn Tabaska currently has zero photos and videos', confidence 0.9, escalate:false), after which auto-triage stopped because the human-leg task fix-71 was filed to track it. Remediation is fully a human device leg: Kaelyn opens the Immich app, signs in to her account, enables backup — this clears the by-design-red check once her assets flow. Covered by OPEN task fix-71 (mode:human, 'Kaelyn Immich onboarding — enable phone photo backup for the 2nd household user'); check origin fix-60. NOT fixed per read-only mandate + human-only remediation.

<details><summary>Evidence</summary>

```
$ python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['immich']['verify_api_key'])"  # (vault immich.verify_api_key, value not shown)
$ curl -sm 15 -H "x-api-key: $KEY" "http://192.168.10.4:2283/api/server/statistics" | python3 parse_users.py
       Brandon Tabaska photos=34866 videos=1342 total=36208
        Kaelyn Tabaska photos=0 videos=0 total=0
CHECK_RESULT: per_user=ZERO:Kaelyn Tabaska
TOTAL_USERS: 2

# tonight's audit-safe daily run (results.json): status=fail, output="per_user=ZERO:Kaelyn Tabaska"
# triage history (mini /var/lib/verification/triage-2026-08-14.md): diagnosis "user Kaelyn Tabaska currently has zero photos and videos", confidence 0.9, escalate:false
# tasks.json fix-71: OPEN, mode:human — "Kaelyn Immich onboarding — enable phone photo backup for the 2nd household user"
```

</details>

### UL141. ffmpeg SIGSEGV core dump regenerated last night — IMG_3674.mov crash still recurring (KNOWN fix-60) `known-issue`
**Host:** nas · **Component:** immich ffmpeg transcode (nas-immich-ffmpeg-nocrash, fix-60) · **Auditor:** flow:photos-ml · **Work item:** `fix-87`

Corroborated fix-60 still active and freshly recurring: exactly one ffmpeg core dump on /volume1, dated 2026-08-23T00:00:28 (~midnight last night, i.e. the nightly transcode pass), 23,283,178 bytes. The offending corrupt asset (IMG_3674.mov, asset 8a5d0a66-…) is already handled — nas-immich-corrupt-mov-quarantined PASSES (a preview row exists), and no future-dated assets. So the crash is cosmetic/residual (a single unplayable .mov segfaulting ffmpeg each night); it does NOT block smart-search or other transcodes. NOT fixed per read-only mandate. Covered by open task fix-60.

<details><summary>Evidence</summary>

```
$ ssh nas 'ls -la --time-style=+%Y-%m-%dT%H:%M:%S /volume1/@ffmpeg*core*.gz'
-rw------- root 23283178 2026-08-23T00:00:28 /volume1/@ffmpeg.synology_geminilake_920+.72806.<hash>.core.gz
baseline (nas, fix-60): nas-immich-ffmpeg-nocrash = FAIL (count 1); nas-immich-corrupt-mov-quarantined = PASS quarantined=yes; nas-immich-no-future-dates = PASS
```

</details>

### UL142. Kaelyn Tabaska user has 0 photos / 0 videos (KNOWN fix-71) `known-issue`
**Host:** nas · **Component:** immich per-user assets (immich-user-zero-assets, fix-71) · **Auditor:** flow:photos-ml · **Work item:** `fix-71`

Corroborated fix-71 still holds. server/statistics usageByUser shows Brandon Tabaska with all 34,866 photos + 1,342 videos and Kaelyn Tabaska with photos=0, videos=0. Second user has never ingested any assets. Does not affect smart-search (scoped to owner's library). NOT fixed per read-only mandate. Covered by open task fix-71.

<details><summary>Evidence</summary>

```
$ curl -sk https://immich.tabaska.us/api/server/statistics → usageByUser:
 user: Brandon Tabaska | photos 34866 | videos 1342
 user: Kaelyn Tabaska | photos 0 | videos 0
baseline (mini, fix-60/71): immich-user-zero-assets = FAIL 'per_user=ZERO:Kaelyn Tabaska'
```

</details>

### UL143. Second household user Kaelyn Tabaska has 0 assets (onboarding not done) `known-issue`
**Host:** nas · **Component:** immich per-user backup (Kaelyn) · **Auditor:** svc:immich · **Work item:** `fix-71`

usageByUser shows Kaelyn Tabaska with photos=0 videos=0 usage=0; Brandon Tabaska owns all 36208 assets. The per-user check 'every Immich user has >0 assets' fails per_user=ZERO:Kaelyn Tabaska. This is the pending Kaelyn Immich onboarding (enable her phone photo backup). NOT actioned per read-only mandate. Covered by open tasks fix-60/fix-71.

<details><summary>Evidence</summary>

```
$ curl -s -H "x-api-key: <immich.verify_api_key>" http://192.168.10.4:2283/api/server/statistics
..."userName":"Kaelyn Tabaska","photos":0,"videos":0,"usage":0...

(audit run) 'every Immich user has >0 assets' [fix-60] => fail per_user=ZERO:Kaelyn Tabaska
```

</details>

### UL144. Corrupt HEIC assets also fail nightly thumbnail generation in the same midnight Immich job (fix-60 corrupt-media cluster) `known-issue`
**Host:** nas · **Component:** immich_server (AssetGenerateThumbnails, corrupt HEIC assets) · **Auditor:** triage:nas-core-dumps · **Work item:** `fix-87`

Corroborating signal in the same 00:00 AssetGenerateThumbnails run that produced the ffmpeg SIGSEGV: two corrupt HEIC assets throw handled job errors (no core dump, container stays healthy). /data/library/admin/2019/2019-12-23/IMG_0628.heic errors with 'bad seek to 11911017', and another HEIC fails header parsing ('ipma box wants to define properties for 258 items, but the security limit has been set to 256'). These are part of the fix-60 corrupt-asset cluster feeding the nightly thumbnail job; their thumbnails/previews will be missing until the assets are repaired or excluded. Read-only observation, not repaired.

<details><summary>Evidence</summary>

```
$ ssh nas 'sudo -S /usr/local/bin/docker logs immich_server --since 30h | grep -iE "thumbnail|heic"'
08/23/2026, 12:00:13 AM ERROR (AssetGenerateThumbnails): Error: /data/library/admin/2019/2019-12-23/IMG_0628.heic: bad seek to 11911017
08/23/2026, 12:00:23 AM ERROR (AssetGenerateThumbnails): Error: Input file has corrupt header: heif: Invalid input: Security limit exceeded: ipma box wants to define properties for 258 items, but the security limit has been set to 256 items (2.1000)
```

</details>

### UL145. Recurring ffprobe failures on a few malformed FMA Brotherhood external subtitle files (data-quality, not a service fault)
**Host:** nas · **Component:** jellyfin SubtitleResolver / external subtitle files · **Auditor:** svc:jellyfin · **Work item:** `fix-103`

Log scan since 2026-08-02 (10840 lines) shows the ONLY recurring [ERR] pattern is MediaBrowser.Providers.MediaInfo.SubtitleResolver failing on two specific external subtitle files: '/tv/Full Metal Alchemist/FMA Brotherhood [57] Eternal Leave [ac3 ITA JAP] by Salvo.ass' and '[63] The Other Side of the Gate ... by Salvo.srt' — ffprobe returns 'streams and format are both null', i.e. the .srt/.ass files are malformed/empty. Repeats once per library scan cycle (a handful/day), NOT a >1000-line retry storm, no crash, no auth rot, no NUL corruption. Also benign INF: chapter-image extraction skipped for short Phineas&Ferb segments. Cosmetic; playback unaffected. NOT fixed per read-only mandate. Fix would be to remove/replace those two subtitle files (arr/library side).

<details><summary>Evidence</summary>

```
sudo docker logs jellyfin --since 2026-08-02T00:00:00 | wc -l -> 10840
grep -iE 'error|exception|fail|fatal' | tail:
[ERR] SubtitleResolver: Error getting external streams from /tv/Full Metal Alchemist/FMA Brotherhood [57] Eternal Leave [ac3 ITA JAP] by Salvo.ass
MediaBrowser.Common.FfmpegException: ffprobe failed - streams and format are both null.
(repeats for [63] ...Salvo.srt across each scan cycle)
```

</details>

### UL146. Recurring SQLite HikariCP connection-pool timeouts under NAS IO load (auth-audit-log writes dropped)
**Host:** nas · **Component:** komga · **Auditor:** svc:komga · **Work item:** `fix-91`

616 error/exception/fatal log lines since 2026-08-02 = ~154 distinct TransientDataAccessResourceException events (SqliteMainPoolRW - Connection is not available, request timed out). Dominant signature: INSERT into AUTHENTICATION_ACTIVITY (login/api-key audit log) times out (67+ events), plus one taskProcessor TASK-poll timeout. Events are spread across the window (Aug 3:4, Aug 11:42, Aug 13:20, Aug 15:16, Aug 23:28) — NOT a single >1000-line storm (taxonomy 7 not met), most recent 2026-08-23T02:03:30Z. Transient and self-recovering: RestartCount=0, no crash, and the consumer probe is fully green. Impact: some auth-audit records lost and occasional background query stalls under IO pressure; ZERO reader-facing impact. Correlates with the NAS heavy-IO condition noted fleet-wide (also surfaces as the fix-23 60s NAS timeout). NOT fixed per read-only mandate. Follow-up candidate: raise HikariCP pool size / SQLite busy_timeout, or throttle audit-log writes.

<details><summary>Evidence</summary>

```
docker logs komga --since 2026-08-02T00:00:00 | grep -icE 'error|exception|fatal' => 616 (warn=8)
uniq -c signatures: 76x 'Caused by: java.sql.SQLTransientConnectionException: SqliteMainPoolRW - Connection is not available' ; 67x 'Exception in thread task- ... insert into AUTHENTICATION_ACTIVITY ... SqliteMainPoolRW - Connection is not available' ; 1x taskProcessor SqliteTasksPoolRW timeout
docker logs --timestamps date histogram of 'Connection is not available': 2026-08-11:42 2026-08-13:20 2026-08-15:16 2026-08-23:28 (total ~154 over 21 days); latest 2026-08-23T02:03:30.574Z
```

</details>

### UL147. Fail-green substrate hazard: both absence-of-junk checks print 0 and PASS if /volume1 is unmounted or unreadable
**Host:** nas · **Component:** nas-core-dumps / nas-docker-macos-junk · **Auditor:** meta:nas-host · **Work item:** `fix-100`

nas-core-dumps runs `ls /volume1/ 2>/dev/null | grep -c 'core\.gz' || true` and nas-docker-macos-junk runs `find /volume1/docker … 2>/dev/null | wc -l` — in both, errors are suppressed, so if /volume1 vanished (RO-remount cascade, pattern 1) or /volume1/docker became unreadable, the pipeline emits '0' and the check passes green while the substrate it guards is gone. Impact is low in practice because sibling checks would fail loudly on the same event (nas-soularr-failed-imports-fresh crashes on the missing json; nas-md-arrays-healthy pages on array loss), but a stricter form would assert the directory exists first (e.g. `[ -d /volume1/docker ] || echo MISSING_ROOT`). Structural note only; both checks were green/working today. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
cmd: ls /volume1/ 2>/dev/null | grep -c 'core\.gz' || true  (empty input -> '0' -> matches expect ^0$)
cmd: find /volume1/docker -maxdepth 3 … 2>/dev/null | wc -l  (missing dir -> '0' -> matches expect ^0$)
```

</details>

### UL148. docker-health log unrotated: /var/log/nas-docker-health.log is 7.8MB / 160,078 lines and growing unbounded
**Host:** nas · **Component:** nas-docker-health log rotation · **Auditor:** svc:nas-dsm-tasks · **Work item:** `fix-96`

The task-5 script logs to /var/log/nas-docker-health.log with no logrotate policy; it has grown to 7,884,574 bytes / 160,078 lines since ~Jul 5 (~42 days at ~40 lines/run x 96 runs/day). Not a retry-storm (each run writes normal per-service OK lines, last run clean PASS) and not urgent at current growth, but there is no rotation/truncation, so it will grow without bound. Housekeeping only; NOT fixed (read-only mandate).

<details><summary>Evidence</summary>

```
$ sudo ls -la /var/log/nas-docker-health.log
-rw-r--r-- 1 root root 7884574 Aug 23 16:30 /var/log/nas-docker-health.log
$ sudo wc -l /var/log/nas-docker-health.log -> 160078
```

</details>

### UL149. fix-55 IO-storm signature actively recurring: 15-min IO load 24.21 (threshold 12, worse than the original 17-22 storm) with arr SQLite locks at the tolerance cap 5/5
**Host:** nas · **Component:** nas-io-storm checks / DS920+ IO subsystem · **Auditor:** meta:nas-io-storm · **Work item:** `fix-91` · *skeptic-confirmed*

Both fix-55 checks fired or sat at the boundary when exercised live at ~22:25 EDT: nas-io-pressure returned status=HIGH at 24.21 (quiet baseline ~2.8; the 2026-08-02 storm band was 17-22), and arr-sqlite-not-locked counted exactly 5 'database is locked' errors in the last 15 min (lidarr=2, whisparr=3) — one more lock flips STORM. The class tripwire is doing its designed job on a NEW hog class: the dominant D-state process is synoimgbkptool (Synology image-backup) plus the jbd2 journal thread, not bitmagnet (whose DHT scaling was the original fix). Load is tapering (1-min IO 16.32 < 5-min 20.00 < 15-min 23.58), consistent with a backup job winding down, but consumers are already contending — this same load is what timed out today's fix-23 nas-secret-file-perms CRIT at 60s per the baseline. nas-io-pressure passed the 10:29 daily run, so the storm arose after; expect it to FAIL (warn) on the next scheduled run. fix-55 itself is CLOSED and no open task tracks a recurrence. NOT fixed per read-only mandate — if this is a scheduled Active Backup window it may deserve either rescheduling into the 4-7AM window or an acked exception.

*Severity adjusted high→low during adversarial verification.*

*Verify note:* Transient Saturday backup-window artifact, not a high-severity chronic regression. The finding was captured 2026-08-22 22:25 EDT — a SATURDAY, the routine weekly Synology image-backup window (dominant D-state proc was synoimgbkptool). Fresh probes ~19h later (Sun 2026-08-23 17:50 EDT) show it fully self-cleared: nas_io_load15=10.14 status=OK (under threshold 12, decaying 8.45<9.51<10.13), arr_locked_last15m=0/5 status=OK across all three arrs, and synoimgbkptool is gone (only synobackupd Ss sleeping-daemon remains; D-state is just md0_raid1 + a kworker). This matches the lane-context adjudication ('routine weekly Saturday Hyper Backup window self-clears' and 'a backup-window spike that self-clears is NOT a regression'). The 24.21 was a single scheduled-backup peak, not a worsened chronic base. The finding is also mis-tagged known_issue:false: the identical event is already correctly captured as fix-55 (known_issue:true) at result index 15, and the fix-55 tripwire firing then clearing is the check working as designed. Downgraded to low: a legitimate operational note (reschedule the weekly image-backup into the 4-7AM window or ack the exception), already covered by fix-55, not a high untracked regression.

<details><summary>Evidence</summary>

```
$ ssh mini 'python3 /opt/verification/bin/nas-io-storm-probe.py io'
nas_io_load15=24.21 threshold=12 status=HIGH
$ ssh mini 'set -a; eval "$(sudo grep -E "^(LIDARR|RADARR|WHISPARR)_API_KEY=" /etc/verification/env)"; set +a; timeout 50 python3 /opt/verification/bin/nas-io-storm-probe.py locks'
arr_locked_last15m=5 max=5 status=OK [lidarr=2 radarr=0 whisparr=3]
$ ssh nas 'uptime; ps ax -o stat=,comm= | awk "$1 ~ /^D/ {print $2}" | sort | uniq -c | sort -rn | head -8'
 22:26:57 up 51 days,  6:49,  0 users,  load average: 17.20, 20.75, 24.26 [IO: 16.32, 20.00, 23.58 CPU: 0.89, 0.74, 0.67]
      1 synoimgbkptool
      1 jbd2/md0-8
```

</details>

### UL150. Intermediate probe: filter-file presence cannot detect present-but-not-loaded (pattern 9), consumer end unprobeable without sudo
**Host:** nas · **Component:** nas-syslog-geo-filter-present · **Auditor:** meta:nas-host · **Work item:** `fix-100`

The check pins the two syslog-ng filter files under /usr/local/etc/syslog-ng/patterndb.d (verified 2/2 present live) but never verifies the filter is ACTIVE: a DSM upgrade could leave the files intact while regenerating the main syslog-ng config to stop including the /usr/local tree, or restart syslog-ng without them — files-present, flood-back, check green (fleet failure pattern 9, config-edited-never-reloaded). The true consumer end (no abnormal_login.cpp geo-lookup lines in recent /var/log/messages) needs root, and the file header correctly documents the unprivileged constraint, so the naming is honest ('filter present') and this is the best available unsudoed proxy — flagging as a probe-depth ceiling, not masquerading. Only viable strengthening path would be a sudo-piped variant or a messages line-rate proxy if one exists world-readable; otherwise accept with this documented limitation.

<details><summary>Evidence</summary>

```
ssh nas '…' -> geo_filter_files=2/2 (files exist; nothing asserts syslog-ng has them loaded)
check cmd only tests: [ -f synologand-geo.conf ] && [ -f include/not2msg/synologand_geo ]
```

</details>

### UL151. fix-70 STILL OPEN and WORSENED: NAS Plex is now two upstream releases behind (10793 vs latest 10896); edge-plex-version-current passes only because a fresh release reset the 14-day grace `known-issue`
**Host:** nas · **Component:** plex-dsm · **Auditor:** svc:plex-dsm · **Work item:** `fix-70`

Live re-verify per lane notes: NAS Plex identity reports version 1.43.3.10793-cd55560bb; plex.tv downloads/5.json latest 'Synology (DSM 7.2.2+)' is 1.43.3.10896-cb3ebc72d, released 2026-08-12 (11.2 days old). fix-70's summary cited latest .10828 — upstream has since moved to .10896, so the NAS has fallen FURTHER behind (10793 -> 10828 -> 10896, ~2 releases) while pinned. edge-plex-version-current currently returns VERSION_OK:grace_10d (PASS) ONLY because the 2026-08-12 release is inside the 14-day grace window — grace expires ~2026-08-26, after which the check flips back to VERSION_STALE unless the package is updated. This is a WAN-exposed Plex (Remote Access intentional per fix-24), so it is a CVE-posture/maintenance item. Human-mode DSM Package Center update task; NOT fixed per read-only mandate. known_issue=true (fix-70).

<details><summary>Evidence</summary>

```
NAS identity -> version="1.43.3.10793-cd55560bb" (also synopkg version 1.43.3.10793-720010793)
plex.tv/api/downloads/5.json ['nas']['Synology (DSM 7.2.2+)'] -> version=1.43.3.10896-cb3ebc72d release_date=2026-08-12 age_days=11.2
audit results edge-plex-version-current -> VERSION_OK:grace_10d (pass — grace, not current)
fix-70 tasks.json summary references '.10793 vs latest .10828' (now stale — latest is .10896)
```

</details>

### UL152. Recurring SQLITE_BUSY 'database is locked' errors re-confirmed (documented 2026-08-02, still untracked)
**Host:** nas · **Component:** prowlarr SQLite (/volume1/docker/prowlarr/config/prowlarr.db) · **Auditor:** svc:prowlarr · **Work item:** `fix-91`

The --since 2026-08-02 log scan aborted (2m timeout under current NAS IO load — taxonomy-15 evidence itself); --tail 400 fallback found 12 'System.Data.SQLite.SQLiteException (0x87AF00AA): database is locked' (Busy code 5) lines. This is the exact chronic issue documented in fleet-sweep-2026-08-02.md ('Prowlarr fails HistoryService... clusters at nightly job + daytime API load contending on /volume1/docker SQLite files... No open task covers this'), now re-confirmed 3 weeks later (2026-08-23). NO current consumer impact observed (HistoryService is writing — 74231 records, newest seconds-fresh), so today these are transient/retried under the live /volume1 IO saturation. Untracked (no open task); correlates with the same NAS-IO-load root as fix-23. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
docker logs prowlarr --since 2026-08-02 -> timed out 120s (NAS IO load)
docker logs prowlarr --tail 400 | grep -icE 'Error|Fatal|exception' -> 12
sample: '[v2.4.0.5397] code = Busy (5), message = System.Data.SQLite.SQLiteException (0x87AF00AA): database is locked' x8
prior: foss-setup/docs/fleet-sweep-2026-08-02.md:108 'Prowlarr fails HistoryService... No open task covers this'
```

</details>

### UL153. IPTorrents monopolising the grab stream at 69% (fix-50 grab-storm still active) `known-issue`
**Host:** nas · **Component:** prowlarr grab stream (check arr-grab-source-not-storming, fix-50) · **Auditor:** svc:prowlarr · **Work item:** `fix-94`

Baseline fix-50 (arr-grab-source-not-storming) re-verified STILL HOLDS: the SHARE_STORM check reports IPTorrents at 69% of the last 80 grabs with auto_enabled=YES = a live auto-grab-enabled indexer dominating the grab stream (junk-grab-storm class). Matches this period's indexerstats (IPT 168 grabs). This is the likely root of the IPT ID-search-returns-0 finding above (IPT budget being burned). Known open item fix-50; warn-severity check. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
results.json: 'arr grabs: no auto-grab-enabled indexer is monopolising the grab stream (fix-50 class)' STATUS=fail OUT="SHARE_STORM top='IPTorrents (Prowlarr)' share=69% n=80 auto_enabled=YES" task=fix-50
```

</details>

### UL154. arr-grab-source-not-storming (fix-50): re-verified known residual — FALSE POSITIVE on IPTorrents as the legit primary indexer, NOT a junk-grab storm `known-issue`
**Host:** nas · **Component:** radarr/sonarr + Prowlarr (arr-grab-indexer-share.py share) · **Auditor:** triage:arr-grab-source-not-storming · **Work item:** `fix-94`

KNOWN residual, task fix-50 (baseline maps it here; failing consecutively since >=2026-08-15). RE-VERIFIED and it still holds, but the underlying condition is BENIGN, not a storm. The check fails when one auto-grab-enabled indexer holds >=60% of the last 80 grabs (40 radarr + 40 sonarr). IPTorrents holds 69% (55/80) because it is the fleet's legitimate primary English-content indexer. I pulled the actual grab titles: every IPT grab is a proper, well-labeled release from reputable groups (radarr: The Lost Boys 1987 1080p BluRay-VALUE, Matrix Resurrections PROPER-HiDt, Deadpool-iFT, Godzilla PROPER, Chinatown-CtrlHD; sonarr: Its Always Sunny S18-ETHEL, Digimon Beatbreak-SENPAI, Teen Titans Go-NOMA/MeGusta, My Adventures with Superman-EDITH) — proper quality tiers (Bluray-1080p/WEBDL-1080p/720p), English audio, NOT the Russian/Bulgarian foreign-dub re-encodes that defined the original fix-50 Bitmagnet incident. The grabs span 21 days (oldest 21.2d, newest 0.4h) — a backlog draining gradually, not an hourly storm. Share has drifted 62%(08-16)->66%(08-19)->68%(08-21/22)->70%(08-23), i.e. IPT steadily being primary as other indexers stay quiet — NOT a worsened junk condition. This is a check-DESIGN limitation: the 60% DOMINATE tripwire cannot distinguish a legit primary indexer from a runaway junk indexer. The genuine fix-50 regression guard (bitmagnet-demoted-interactive-only) is GREEN. Not fixed / not tuned per read-only mandate; candidate remediation is to exclude the operator-designated primary indexer or raise the threshold. Also observed: 13 of radarr's 40 grabs are Bitmagnet (DHT) but auto_enabled=False — benign ~20-day-old pre-demotion residue (Chinatown, Hotel Transylvania 3, Last Christmas — the exact original-incident titles), which the check author explicitly documented as benign.

<details><summary>Evidence</summary>

```
tonight: SHARE_STORM top='IPTorrents (Prowlarr)' share=69% n=80 auto_enabled=YES
this-morning /var/lib/verification/results.json (2026-08-23T10:29:25-04:00): arr-grab-source-not-storming | fail | SHARE_STORM ... share=70% n=80
$ python3 /tmp/grabhist.py  (radarr+sonarr /api/v3/history eventType=1 pageSize=40, keys from /etc/verification/env)
===== radarr: 40 recent grabs =====
   21  IPTorrents (Prowlarr)   auto_enabled=True
   13  Bitmagnet (DHT) (Prowlarr)   auto_enabled=False
    2  Zenith (Prowlarr) / 2 OnlyEncodes+ / 2 SexTorrent   auto_enabled=True
  -- oldest grab age: 21.2d  newest: 0.4h
     [IPTorrents (Pr] Bluray-1080p  14.0G  0.4h  The Lost Boys 1987 1080p BluRay H264-VALUE
     [IPTorrents (Pr] Bluray-1080p  22.8h  The Matrix Resurrections 2021 Proper 1080p BluRay ... x264-HiDt
     [IPTorrents (Pr] Bluray-1080p  Deadpool 2016 1080p BluRay x264 DTS-HD MA7 1-iFT
===== sonarr: 40 recent grabs =====
   36  IPTorrents (Prowlarr)   auto_enabled=True
    3  OnlyEncodes+ / 1 Zenith
     [IPTorrents (Pr] WEBDL-1080p  15.7h  Digimon Beatbreak 2025 S01E44 1080p CR WEB-DL AAC2 0 H 264-AnoZu
     [IPTorrents (Pr] WEBDL-1080p  Its Always Sunny in Philadelphia S18E01 1080p WEB h264-ETHEL
```

</details>

### UL155. Hardcover 429 refresh-herd throttles cold prolific-author fetches (documented/absorbed, but contributes to the canary timeout) `known-issue`
**Host:** nas · **Component:** rreading-glasses-hc -> Hardcover GraphQL · **Auditor:** svc:rreading-glasses · **Work item:** `fix-89`

Background metadata refresh batches from rreading-glasses-hc hit Hardcover's account-wide ~60/min quota and return HTTP 429, in bursts: 56 warn lines at 08-22 18:55 (incl. refresh-author-132049 = Jane Austen, the P&P author) and 8 more at 08-23 20:xx (20:27, coincident with my probing). rreading-glasses-hc ABSORBS these (retry/backoff) and still serves cached HTTP 200 to consumers — access log over the 08-22 05:33 -> 08-23 20:29 window is 114x HTTP 200 + 1x HTTP 303 with ZERO non-2xx/3xx to the consumer. This is the documented WAI refresh-herd behavior (fix-57 backoff; hardcover-token-valid check comment 'rg-hc refresh herds can 429 this briefly; one retry absorbs that'), so known_issue. Notable positive: the batch5 local-image patch is fully holding — 0 lines of 'top_level_limit_exceeded' / genuine HTTP 403 / level:error / panic / fatal in the 8000-line window (the 281 raw '403' grep hits were substring false-positives in debug numerics). The only concern is that under a prolific-author lookup the 429 backoff makes individual cold /author fetches take 1.7-14.6s, which is the mechanism behind the medium finding above. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
hc logs (ssh nas sudo docker logs rreading-glasses-hc --tail 8000): grep counts -> top_level=0 forbidden=0 level:error=0 panic=0 fatal=0 timeout=0 ; level:warn=64 (all Hardcover 429)
warn lines by hour: 56 @ 2026-08-22T18 , 8 @ 2026-08-23T20
sample: {\"time\":\"2026-08-22T18:55:00Z\",\"level\":\"warn\",\"msg\":\"problem getting work\",\"trace\":\"refresh-author-132049\",\"err\":\"getting work: returned error 429\",\"workID\":377938}
most recent: {\"time\":\"2026-08-23T20:27:46Z\",\"level\":\"warn\",\"msg\":\"batched query error\",\"err\":\"returned error 429\"}
access-log status distribution: 114 => HTTP 200 ; 1 => HTTP 303 ; 0 others
```

</details>

### UL156. Known InfluxDB timeouts under IO load corroborated in hub logs — intermittent publish retries + slow tsm1 snapshots, but SMART data currency intact `known-issue`
**Host:** nas · **Component:** scrutiny InfluxDB storage-engine (under NAS IO load) · **Auditor:** flow:disk-smart · **Work item:** `fix-91`

Corroborates the already-found scrutiny-hub InfluxDB-timeout-under-IO-load issue (flagged in my chain notes as found by another lane this audit; scrutiny is owned by glue-10). Hub logs show the storage engine struggling during heavy /volume1 IO: query 'Error exhausting result iterator error=timeout' (01:02Z), 'Write failed engine: context canceled' shard=61 (01:03Z), 'Failed to finish run error=timeout' (01:03:50Z), tsm1 cache snapshots taking 6.6-12.3s (01:13-01:14Z), and one SMART publish 'context deadline exceeded' for device 0x5000cca298c083de (nas/sata1) at 06:01:05Z during the daily sweep. Impact assessment: NONE on data currency — that same sata1 device still shows today's 06:00:05Z record with device_status 0 in /api/summary, and all 7 disks landed today's sweep; the /api/summary read path is currently fast (86-285ms, HTTP 200). The timeouts manifest as transient write retries and slow compaction, not stale/missing SMART data. Residual risk (not observed today): if a publish fully fails without a landing retry during an especially heavy IO window, a single device's daily datapoint could be skipped, and the consumer check sys-disk-smart-health uses curl -sm 10 which could flake if a read ever exceeds 10s under load. Neither occurred at probe time. NOT fixed per read-only mandate — reported for the glue-10 owner.

<details><summary>Evidence</summary>

```
PW=$(python3 -c yaml...['sudo']['nas_password']); printf '%s\n' "$PW" | ssh nas 'sudo -S docker logs scrutiny --since 24h | grep -iE influx|timeout|error|deadline|context':
 ts=2026-08-23T01:02:23Z lvl=info msg="Error exhausting result iterator" service=task-executor error=timeout
 ts=2026-08-23T01:03:29Z lvl=info msg="Write failed" service=storage-engine shard=61 error="engine: context canceled"
 ts=2026-08-23T01:03:50Z lvl=error msg="Failed to finish run" service=task-executor error=timeout
 ts=2026-08-23T01:13:40Z ... tsm1_cache_snapshot duration=9409.550ms ; 01:14:20Z duration=12259.846ms
 time=2026-08-23T06:01:05Z level=error msg="error ... publishing SMART data for device (0x5000cca298c083de): Post http://localhost:8080/api/device/0x5000cca298c083de/smart: context deadline exceeded"
contrast (data landed anyway): /api/summary sata1 0x5000cca298c083de -> collector_date 2026-08-23T06:00:05Z device_status 0
read path OK now: docker logs tail -> GET /api/summary 200 latency=87ms/285ms/94ms/284ms/86ms
```

</details>

### UL157. Catalog gap: no row for adguardhome-nas / secondary DNS resolver
**Host:** nas · **Component:** service-catalog.yaml · **Auditor:** svc:adguard-nas · **Work item:** `fix-102`

service-catalog.yaml lists only the mini primary ('adguard-home', port 53, dns.tabaska.us) and mini 'unbound' (port 5335). There is NO catalog row for the NAS secondary resolver (adguardhome-nas, 192.168.10.4:53, admin UI :3000), even though it is a live, actively-used service present in the coverage manifest (verification/coverage/nas.containers). Not caught by the known fix-68 'catalog-vhost-parity' check because the secondary intentionally has no *.tabaska.us vhost. Anti-drift / catalog-completeness gap. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ grep -iE 'adguard-nas|adguard.*nas|secondary.*dns|192.168.10.4.*dns' service-catalog.yaml  -> (no output)
$ grep -n -i adguard service-catalog.yaml
588:  - name: adguard-home   (host: mini, port 53, url: https://dns.tabaska.us)
602: unbound note
$ cat verification/coverage/nas.containers
adguardhome-nas   <-- present in coverage but absent from catalog
```

</details>

### UL158. Catalog note stale: claims 'No API key in vault - no widget' but a working stash widget exists
**Host:** nas · **Component:** service-catalog.yaml · **Auditor:** svc:stash · **Work item:** `fix-102`

service-catalog.yaml line 649 for stash says 'No API key in vault - no widget.' This is inaccurate: (a) homepage services.yaml lines 86-93 define a live 'type: stash' widget with key {{HOMEPAGE_VAR_STASH_KEY}}; (b) that env var IS populated in the homepage container (STASH_KEY_SET=yes); (c) the nas-services stash-serving check comment references vault key homepage_widgets.stash_api_key. Cosmetic documentation drift only; monitoring and the widget are fine. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
service-catalog.yaml:649 notes: 'Adult media organizer. LAN/Tailscale only. No API key in vault - no widget.'
homepage services.yaml:90-93 -> widget: {type: stash, url: http://192.168.10.4:9999, key: "{{HOMEPAGE_VAR_STASH_KEY}}"}
docker exec homepage printenv HOMEPAGE_VAR_STASH_KEY -> STASH_KEY_SET=yes
```

</details>

### UL159. Minor catalog inaccuracy: unpackerr port:null though container exposes :5656 metrics/healthcheck
**Host:** nas · **Component:** service-catalog.yaml · **Auditor:** svc:unpackerr · **Work item:** `fix-102`

service-catalog.yaml row for unpackerr has port:null, url:null, ui:false, on_demand:false. The container actually publishes a webserver on 0.0.0.0:5656 (metrics + healthcheck), consumed by the docker healthcheck, Uptime-Kuma, and the unpackerr-poll-advancing check. Because ui:false/url:null it has no vhost or homepage tile (correctly absent, no fix-68 vhost-parity impact), so this is cosmetic only — but port:5656 would be the accurate value. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/configs/docker-stack/service-catalog.yaml L196-202: name: unpackerr / category: Media Automation / host: nas / port: null / url: null / ui: false / on_demand: false
live: unpackerr.conf [webserver] listen_addr = '0.0.0.0:5656'; metrics served + probed 200 by Wget/Kuma/curl
```

</details>

### UL160. NAS diun instance not represented in service-catalog (catalog implies mini-only)
**Host:** nas · **Component:** service-catalog.yaml · **Auditor:** svc:diun-nas · **Work item:** `fix-102` · *skeptic-confirmed*

service-catalog.yaml has a single `diun` row (line 624) with host:mini, port:null, url:null, ui:false. The NAS runs a second, independently-deployed diun (own compose /volume1/docker/diun, own repo mirror configs/nas/diun/, own ntfy token ntfy.diun_nas_token) that is invisible in the catalog — a reader would conclude diun only runs on mini. The coverage manifest DOES track both (nas.containers + mini.containers both list diun), so monitoring inventory is aware; only the service-catalog under-represents it. Minor completeness/docs gap (could be by-design one-row-per-service). No Homepage tile and no Kuma monitor, both expected for a UI-less background notifier. NOT fixed per read-only mandate.

*Verify note:* Every probed fact reproduces on a fresh independent look. service-catalog.yaml has exactly ONE diun row (line 624, host:mini, port/url:null, ui:false) — grep confirms a single 'name: diun' occurrence across 85 rows. The NAS runs a real, independently-deployed diun: repo mirror configs/nas/diun/compose.yaml exists (image crazymax/diun:4.33.0, header 'Companion to mini's Diun'), and a LIVE read-only ps on the NAS shows the container Up 12 days — NOT retired, so the mini-only row genuinely under-represents it (this was the key refutation angle: had NAS diun been decommissioned, the single row would be correct). Coverage manifest tracks BOTH (nas.containers:10 + mini.containers:10) so there is no monitoring blind spot. Considered operator-intent/by-design: the catalog is deliberately one-row-per-service (all 85 names unique), and multi-host services carry their nuance in the notes field — the syncthing row (runs on 3 hosts: NAS hub + mini/rig mesh) is a single row at host:nas whose notes describe the mesh nodes. That precedent is exactly why diun's row is a legitimate low nit: unlike syncthing, diun's notes omit the NAS companion, so it deviates from the catalog's own multi-host documentation pattern. Severity low is accurate — a docs completeness gap, monitoring-aware, no operational impact.

<details><summary>Evidence</summary>

```
$ sed -n '624,632p' foss-setup/configs/docker-stack/service-catalog.yaml
  - name: diun
    category: Infrastructure & Ops
    host: mini
    port: null
    url: null
    ui: false
    notes: Image-update notifier → ntfy. No web UI.
$ grep -rn diun foss-setup/verification/coverage/ → nas.containers:10:diun  mini.containers:10:diun
$ homepage /api/services → diun tiles: NONE (expected)
```

</details>

### UL161. One indexer (RetroToon via Prowlarr) unavailable — single health warning, redundancy intact
**Host:** nas · **Component:** sonarr · **Auditor:** svc:sonarr · **Work item:** `fix-103`

Sonarr /api/v3/health reports exactly one item: IndexerStatusCheck warning 'Indexers unavailable due to failures: RetroToon (Prowlarr)'. RetroToon is a niche retro/cartoon indexer, tied to the current cartoon backfill. Redundancy is NOT compromised — sonarr-indexer-redundancy passed with searchable=5 (well above the min-3 floor). Also 27+9 'unable to parse media info' errors on a few /tv/mission*/community* files (mediainfo parse, non-blocking, files still imported). Minor. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
live /api/v3/health:
HEALTH_ITEMS 1
  - warning IndexerStatusCheck | Indexers unavailable due to failures: RetroToon (Prowlarr)
audit-run sonarr-indexer-redundancy | STATUS: pass  OUT: searchable=5
```

</details>

### UL162. Sustained + growing SQLite 'database is locked' storm with runaway 427MB WAL — failing scheduled tasks, no check covers it
**Host:** nas · **Component:** sonarr · **Auditor:** svc:sonarr · **Work item:** `fix-91` · *skeptic-confirmed*

Sonarr's error log is dominated by 'database is locked': 961 of the last 1000 error records (API total 1413), spanning 2026-08-19T00:22Z→2026-08-23T20:16Z, GROWING daily (148→198→174→210→231-by-16:18-today). Mini clock (2026-08-23T20:18Z) confirms these are current, not RTC skew. The failures hit real scheduled tasks: ProcessMonitoredDownloads, RefreshMonitoredDownloads, ImportListSync, and POST /api/v3/command. Root mechanism: sonarr.db-wal has ballooned to 427MB — LARGER than the 210MB main sonarr.db — i.e. the WAL is not being checkpointed, the classic SQLite-on-Synology-/volume1-under-heavy-IO contention pattern (taxonomy 7 retry-storm + write-contention; correlates with the NAS heavy-IO load noted fleet-wide today, e.g. fix-23 60s timeout). Consumer impact is currently DEGRADED-not-dead (imports still completing — newest 03:40Z today, during low-IO overnight; locks cluster in high-IO daytime), but the trend is worsening and unbounded WAL growth risks escalation to db corruption. NOT fixed per read-only mandate. MONITORING GAP: no check in checks.d probes sonarr's error log or db health — the existing sonarr checks (queue-stuck, pipeline-health, tv-in-plex, indexer-redundancy) all passed while this storm ran invisibly. Recommend a consumer-grade check on /api/v3/log?level=error db-lock rate + WAL size.

*Severity adjusted high→low during adversarial verification.*

*Verify note:* Transient-vs-chronic: the finding's core mechanism (runaway WAL not checkpointing, WAL>DB, corruption risk) is refuted by a fresh read — sonarr.db-wal is now 3.9MB (was 427MB at 16:20), checkpointed back down and far SMALLER than the 210MB main DB, so the checkpoint machinery works; 427MB was a transient daytime high-IO write-burst peak, not unbounded growth. The lock storm self-cleared: locks_last15min=0, locks_last60min=1 (newest 21:23Z), well under fix-55 LOCK_MAX=5; totalRecords grew only 1413->1419 in ~1h40m. Clocks cross-checked (WAL mtime 18:01 EDT = 22:01 UTC = mini 22:01 UTC, no skew). Root cause is the already-tracked fix-55 NAS-IO-pressure -> SQLITE_BUSY storm (idx 15/22, reopen candidate), not a new independent defect — finding wrongly sets known_issue:false and omits fix-55. 'No check covers it': the arr-sqlite-not-locked probe DELIBERATELY excludes sonarr ('sonarr is deliberately omitted — it never locked ... a control, not a signal'); the data does falsify that 'never locks' premise (a real low-sev nugget), but the shared storm class is already monitored via lidarr/radarr/whisparr in the same check, so only per-service sonarr attribution is missing — low impact. Degraded-not-dead (imports flowing) is acknowledged in the finding itself. Net: real phenomenon, overstated as high; corrected to low (transient IO-window artifact + minor coverage note).

<details><summary>Evidence</summary>

```
$ (5-page pull /api/v3/log?level=error)
PULLED 1000 error records; API total= 1413
SIGNATURES:
    961  database is locked
     27  unable to parse media info from file: /tv/mission
      9  unable to parse media info from file: /tv/communit
      3  import failed, path does not exist or is not acces
DB_LOCKED count_in_sample=961 oldest=2026-08-19T00:22:01Z newest=2026-08-23T20:16:58Z
   day 2026-08-20 -> 198  2026-08-21 -> 174  2026-08-22 -> 210  2026-08-23 -> 231

recent records (/api/v3/log level=error):
  2026-08-23T20:16:58Z CommandExecutor Error executing task ProcessMonitoredDownloads: database is locked
  2026-08-23T20:07:26Z CommandExecutor Error executing task ImportListSync: database is locked
  2026-08-23T20:07:37Z CommandExecutor RefreshMonitoredDownloads: database is locked

$ sudo ls -la /volume1/docker/sonarr/config/*.db*
-rwxrwxr-x sonarr.db     210726912 Aug 23 16:07
-rwxrwxr-x sonarr.db-wal 427239912 Aug 23 16:20   <-- WAL > main DB
$ ssh mini date -u => 2026-08-23T20:18:47Z (timestamps current, not skew)
```

</details>

### UL163. Cross-ref confirmed: Animaniacs sits in BOTH deluge-preimport-stuck and sonarr-unmanaged-profile — 5-series bulk-added cartoon batch on the unmanaged 'Any' profile (fix-45) `known-issue`
**Host:** nas · **Component:** sonarr (192.168.10.4:8989) quality profiles · **Auditor:** triage:deluge-preimport-stuck · **Work item:** `fix-94`

sonarr-unmanaged-profile is failing with PROFILE_BAD: Teen Titans Go!, Animaniacs, Freakazoid!, The Grim Adventures of Billy & Mandy, Johnny Bravo — all on qualityProfileId=1 ('Any'), all a batch of classic WB/Cartoon-Network animation series added around the same time (Animaniacs series 231 added 2026-06-28). This is the connection the audit asked about: the stuck Animaniacs S01 torrent is the SAME series flagged by the unmanaged-profile check. The 'Any' profile is a distinct hygiene defect (bypasses TRaSH custom-format junk-blocking) and is NOT the mechanical cause of the orphaned torrent (that was the mark-failed-without-remove workflow) — but both defects share the same origin: this cartoon batch was bulk-added outside the normal managed add flow. Two of the five are visibly generating download issues (Animaniacs orphaned pre-import; Teen Titans Go stalled grab, see separate finding). Known issue, covered by open task fix-45. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
# results.json: sonarr-unmanaged-profile = fail
PROFILE_BAD Teen Titans Go!,Animaniacs,Freakazoid!,The Grim Adventures of Billy & Mandy,Johnny Bravo
# Sonarr series record (via mini env key -> nas sonarr):
SERIES id=231 title='Animaniacs' monitored=True qualityProfileId=1 rootFolderPath=/tv added=2026-06-28T17:36:30Z
# streak (mini): sonarr-unmanaged-profile streak=11 (confirmed)
```

</details>

### UL164. test `known-issue`
**Host:** nas · **Component:** soularr · **Auditor:** triage:nas-soularr-failed-imports-fresh · **Work item:** `fix-95`

test

<details><summary>Evidence</summary>

```
test
```

</details>

### UL165. fix-40 re-verified holding: 2 stale parked failed imports (>3d), plus 2 newer within grace `known-issue`
**Host:** nas · **Component:** soularr (Soulseek->Lidarr importer) · **Auditor:** flow:music · **Work item:** `fix-95`

Re-verified the KNOWN fix-40 residual. failed_imports.json (mtime 2026-08-21T17:00) holds 4 entries; 2 are stale >3 days: 'JJK' (age 10.0d) and 'Masters of Slang' (age 8.0d) — matches this morning's baseline (stale=2:cycling=yes). Two newer entries ('Katy Bar the Door / Living Undercover', 'Countdown', both age 2.0d) are within the 3-day grace. soularr itself is healthy and cycling (soularr.log age 1.4 min; soularr-not-crashlooping fatal_errors=0). Stale count has NOT worsened since baseline. Individual-album degradation only; does not break the streaming consumer. NOT fixed (read-only).

<details><summary>Evidence</summary>

```
failed_imports.json -> entries=4
  'JJK' failed_at=2026-08-13T16:30:58 age_days=10.0
  'Masters of Slang' failed_at=2026-08-15T16:40:27 age_days=8.0
  'Katy Bar the Door / Living Undercover' failed_at=2026-08-21T16:43:58 age_days=2.0
  'Countdown' failed_at=2026-08-21T17:00:55 age_days=2.0
soularr.log age_min=1.4
baseline nas-soularr-failed-imports-fresh -> stale=2:cycling=yes JJK Masters of Slang
```

</details>

### UL166. soularr has 2 stale parked imports (JJK Masters of Slang) though the 5-min cycle is alive `known-issue`
**Host:** nas · **Component:** soularr (fix-40) · **Auditor:** svc:host-nas · **Work item:** `fix-95`

fix-40 (done 2026-07-19) check reports stale=2:cycling=yes for 'JJK Masters of Slang' — the poller cycle is alive (not frozen), but a failed import has been parked; consistent with the known fix-40 residual and worsened by the fix-55 IO/SQLite-lock storm degrading import throughput. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
verify-audit-uc/results.json -> 'soularr: no failed import parked >3 days, 5-min cycle alive (M6/M24)' task_id=fix-40 FAIL output='stale=2:cycling=yes JJK Masters of Slang'
```

</details>

### UL167. 2 soularr failed imports parked >3 days feeding lidarr (JJK Masters of Slang) `known-issue`
**Host:** nas · **Component:** soularr (lidarr import pipeline) · **Auditor:** svc:lidarr · **Work item:** `fix-95`

Adjacent to the lidarr import class: nas-soularr-failed-imports-fresh=fail stale=2 (JJK Masters of Slang), 5-min cycle still alive. This is the soularr->lidarr import leg, not lidarr core. Matches baseline fix-40 (nas-soularr-failed-imports-fresh) exactly and re-verified still holding at 22:23. Denylist itself is clean (soularr-denylist-no-ghosts DENYLIST_OK entries=4 ghosts=0), so no ghost leakage into lidarr. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
results.json@22:23: nas-soularr-failed-imports-fresh=fail => stale=2:cycling=yes JJK Masters of Slang | soularr-not-crashlooping=pass fatal_errors=0 | soularr-denylist-no-ghosts=pass entries=4 ghosts=0
```

</details>

### UL168. nas-soularr-failed-imports-fresh RED: stale=2 (JJK, Masters of Slang) >3d — known fix-40 residual, re-verified unchanged `known-issue`
**Host:** nas · **Component:** soularr / failed_imports.json (denylist) · **Auditor:** svc:soularr · **Work item:** `fix-95`

Check nas-soularr-failed-imports-fresh (fix-40, warn) fails: stale=2:cycling=yes. Live failed_imports.json holds 4 entries; 2 are aged past the 3-day threshold: id=6054 'JJK' by mgk (age 10.0d) and id=6055 'Masters of Slang' by Eminem (age 8.0d). Re-verified against the 10:29 EDT baseline — SAME two albums, NOT worsened (count still 2). These are genuinely-stuck monitored+incomplete albums, not ghosts: the fix-56 soularr-denylist-no-ghosts check passes (entries=4 ghosts=0), meaning per live Lidarr none of the 4 is complete/unmonitored/deleted, so the 6h reconciler correctly LEAVES them. The tripwire is working exactly as designed — surfacing genuinely-unsourceable albums for human triage (unmonitor/delete or accept). NOT fixed per read-only mandate; this needs a human decision. Heads-up: the 2 fresh entries (id 6059/6061, age 2.0d) will age past 3d ~Aug 24-25 and grow the stale count unless soularr sources them or they become complete/unmonitored.

<details><summary>Evidence</summary>

```
results.json (audit run): nas-soularr-failed-imports-fresh → status=fail out='stale=2:cycling=yes JJK Masters of Slang'
live failed_imports.json: id=6054 age_days=10.0 title='JJK' artist='mgk'; id=6055 age_days=8.0 title='Masters of Slang' artist='Eminem'
results.json: soularr-denylist-no-ghosts → status=pass out='DENYLIST_OK entries=4 ghosts=0'
```

</details>

### UL169. Log-noise observation: ~500 full Python tracebacks per log rotation from per-peer slskd directory fetches (not a retry storm)
**Host:** nas · **Component:** soularr.log · **Auditor:** svc:soularr · **Work item:** `fix-95`

soularr logs a full multi-line Python traceback for every unreachable/erroring Soulseek peer during a search (slskd returns 404/500 for offline peers or gone shares — e.g. users ayatoma 404, yaoverstand 500). ~500 'Traceback' lines per rotated log file. This is upstream soularr behavior (it re-raises HTTPError and logs the stack per peer instead of a one-line warning) and is cosmetic — soularr catches 'Error getting directory from user' and continues to the next candidate. Explicitly NOT taxonomy-7 retry-storm: the repeated frames are spread across weeks and 4 rotated files, each for a DIFFERENT user, well under the >1000-identical-lines threshold, and do not represent a stuck retry loop. No auth rot (no 401/403 to slskd — slskd is authenticating and returning per-peer responses). No action required; noted for completeness.

<details><summary>Evidence</summary>

```
cat soularr.log* | uniq -c | sort -rn: '503 Traceback (most recent call last):' then matching slskd_api/requests frames (502 each) across 4 rotated logs
sample: [ERROR|soularr|L373] 16:15:19 Error getting directory from user: "yaoverstand" → requests.exceptions.HTTPError: 500 Server Error for url http://100.119.134.94:5030/api/v0/users/yaoverstand/directory
grep -c '401|403' to slskd: 0
```

</details>

### UL170. Zero-throughput since 2026-07-29 (taxonomy-13 checked; explained by dormant feeder, benign)
**Host:** nas · **Component:** stash (throughput) · **Auditor:** svc:stash · **Work item:** `fix-88`

Newest scene by created_at = id 3231 @ 2026-07-29T15:44:04-04:00; most-recently-updated scene also 2026-07-29T15:45:20. No metadataScan/scan tasks in stash logs since 2026-08-02 (jobQueue null). This frozen-green pattern is EXPLAINED, not a stash fault: the upstream Whisparr feeder is dormant (history/queue both 0), so there is genuinely no new content to index. Combined with the latent chain-36 break above, the seed-13 auto-ingest pipeline is effectively idle. Stash on-demand scanning works when invoked. Reporting per mandate-13 (check newest-item + count on every green service); classified benign because the cause is upstream idleness.

<details><summary>Evidence</summary>

```
[graphql newest:findScenes(sort:created_at DESC)] -> count 3232, scenes[{id:3231,created_at:2026-07-29T15:44:04-04:00}]
[graphql recent:findScenes(sort:updated_at DESC)] -> updated_at 2026-07-29T15:45:20
[graphql jobs:jobQueue] -> null
whisparr history/queue -> 0/0
```

</details>

### UL171. UNPROBED (mutation): Stash auto-scan metadataScan 401 (seed-13) not re-probed `known-issue`
**Host:** nas · **Component:** stash metadataScan · **Auditor:** flow:adult-whisparr-stash · **Work item:** `fix-88` · *skeptic-confirmed*

The known seed-13 finding (stash auto-scan broken, metadataScan returns 401) was NOT re-probed by this lane because triggering a scan is a mutation and is not authorized in read-only mode. It remains a compounding factor: even if the Whisparr pipeline were unfrozen and files landed in /data/, Stash would not auto-index them, so nothing new would become watchable. Evidence for the acquisition side stops at the Whisparr/unpackerr boundary (both fully probed, read-only); the Stash-ingest side is cited as known-broken per seed-13 rather than re-triggered.

*Severity adjusted medium→low during adversarial verification.*

*Verify note:* Test

<details><summary>Evidence</summary>

```
Not re-probed (metadataScan is a mutation; read-only mandate). Cited from prior seed-13 finding: 'stash seed-13 auto-scan broken (metadataScan 401)'. Corroborating symptom observed read-only: Stash performer_count=0/gallery_count=0 despite 3232 scenes (organize/scrape pipeline not running).
```

</details>

### UL172. Monitoring blind spot: mesh-direct check hardcodes only rig+mini device IDs; a 4th peer (macbook) and any future peer go unvalidated for relay-vs-direct
**Host:** nas · **Component:** syncthing-hub-mesh-direct check (verification/checks.d, foss-03) · **Auditor:** flow:syncthing-mesh · **Work item:** `fix-100`

The syncthing-hub-mesh-direct check enumerates exactly two hardcoded device IDs (rig KDLS63N, mini CCBXYGN) and asserts peers_direct=2/2, so it will keep passing even if an additional configured peer connects via relay. The live hub config now has a 4th device 'macbook' (RYRBWQ6-...) sharing the 'default' folder and currently connected DIRECT (tcp-server, TLS1.3) — so today's mesh is fully healthy and this is NOT a broken consumer feature. But the check would not catch macbook (or any newly added device) falling back to relay. Recommend iterating over all rest/config/devices (excluding self) rather than a fixed ID list. NOT fixed per read-only mandate — reported only.

<details><summary>Evidence</summary>

```
ssh nas '... curl .../rest/config/devices' ->
CCBXYGN mini-node
KDLS63N cachyos
RF3KA6P nas-hub (self)
RYRBWQ6 macbook   <-- 4th peer, connected direct, NOT covered by the 2/2 hardcoded check
check cmd hardcodes: peers={"KDLS63N-...":"rig","CCBXYGN-...":"mini"} and prints 'peers_direct=%d/2'
```

</details>

### UL173. Transient arr-queue fetch errors (10 in ~22 days) under NAS IO load — benign, not a storm
**Host:** nas · **Component:** unpackerr (container) -> arr queue APIs · **Auditor:** svc:unpackerr · **Work item:** `fix-103`

10 ERROR lines total in 31945 log lines since 2026-08-02 (~1-2/day, Aug 20-23), no WARN. Two flavors: Lidarr 'invalid status code, 500 >= 300, database is locked' (momentary SQLite lock) and Sonarr/Readarr/Lidarr 'context deadline exceeded (Client.Timeout awaiting headers)' on the /api/vX/queue fetch. These are single-cycle transients that unpackerr retries the next 2m poll; the fetch counters (8634/app, all equal and advancing) confirm the vast majority of polls succeed. Correlates with the current heavy NAS IO load noted in audit context. No retry-storm (taxonomy 7 not met), no auth rot. Reported for completeness only.

<details><summary>Evidence</summary>

```
sudo docker logs unpackerr --since 2026-08-02 | grep -c ERROR -> 10 ; grep -c WARN -> 0 ; total_lines=31945
sample: '2026/08/23 03:00:38 Lidarr (http://lidarr:8686): api.Get(v1/queue): invalid status code, 500 >= 300, database is locked'
'2026/08/22 20:06:47 Sonarr (http://sonarr:8989): api.Get(v3/queue): ... context deadline exceeded'
```

</details>

### UL174. nas-worldwritable-sweep TIMEOUT is an IO-load casualty + timeout-robustness gap (walk ~122-240s vs 60s default) `known-issue`
**Host:** nas · **Component:** verification runner per-check timeout (checks_runner.py) + NAS I/O saturation · **Auditor:** triage:nas-worldwritable-sweep · **Work item:** `fix-92`

Tonight's 'TIMEOUT after 60s' is a symptom, not the check's verdict. The full two-tree walk (/volume1/docker + /volume1/scripts, no -name prefilter, so every inode is stat'd) is IO-bound and took 240s then 122s on two re-runs this session as IO load eased — well beyond the runner's default CHECK_TIMEOUT=60. The dedicated fix-55 tripwire nas-io-pressure fired HIGH at audit time (nas_io_load15=26.57 vs threshold 12; the fix-55 runbook documents the storm band as 17-22, so tonight EXCEEDED it), and Synology's IO-split load average showed the box IO-saturated not CPU-bound (IO 7.95 / CPU 0.47 at re-check). This is the identical class as sibling nas-secret-file-perms (also TIMEOUT tonight; a recurring fix-23 IO casualty per triage-2026-08-22 and -23, whose LLM-triage diagnosis is 'NAS disk I/O slow, find can't complete in the timeout window' and whose suggested fix is `timeout 300 find ...`). Timeout-robustness gap confirmed: the LIVE deployed secrets.yaml (matches repo, no drift) gives NEITHER fix-23 walk check a `timeout:` override, so both fall back to 60s — whereas the fix-55 nas-io-storm checks carry explicit `timeout: 30/40`. Recommended remediation (NOT applied, read-only): add an explicit `timeout:` (e.g. 300, mirroring the triage's own `timeout 300 find` and the fix-42 mechanism) to both fix-23 walk checks so they report their real verdict (which for this one is a genuine fail — see the world-writable finding) instead of a TIMEOUT that masks it during IO storms. known_issue: fix-23 (reopen) + fix-55 (IO storm context).

<details><summary>Evidence</summary>

```
# tonight's dedicated IO tripwire fired HIGH (scratchpad results.json):
nas-io-pressure :: fail :: nas_io_load15=26.57 threshold=12 status=HIGH        # fix-55; storm band documented 17-22
nas-secret-file-perms :: fail :: TIMEOUT after 60s                              # sibling, same class, same night

# Synology IO-split load average at re-check (IO-saturated, CPU idle):
$ ssh nas 'uptime'
 load average: 8.42, 7.41, 4.40 [IO: 7.95, 6.97, 4.01 CPU: 0.47, 0.43, 0.37]
$ ssh nas 'df -h /volume1'
 /dev/mapper/cachedev_2  14T  5.5T  8.5T  40% /volume1

# the walk completes given headroom; time scales with IO load:
worldwritable_count=1 find_exit=0 elapsed=240s   # first re-run (load easing from 26.57)
listing_exit=1 elapsed=122s                      # second re-run (load ~8)

# runner default + per-check override mechanism (fix-42); mini /opt/verification/bin/checks_runner.py:
30: CHECK_TIMEOUT = 60  # seconds per check
86: timeout_s = int(check.get("timeout", CHECK_TIMEOUT))
98: out = f"TIMEOUT after {timeout_s}s" ... exit 124

# LIVE check def on mini == repo; NO timeout: on either fix-23 walk check (fix-55 io-storm checks have 30/40):
$ ssh mini 'grep -A6 "id: nas-worldwritable-sweep" /opt/verification/checks.d/secrets.yaml'
  cmd: sh -c 'find /volume1/docker /volume1/scripts ... ! -type l -perm -0002 ... | wc -l'
  expect: '^0$'   severity: warn   task_id: fix-23      # (no timeout: field)

# yesterday/today triage of the CRIT sibling (why the sweep itself was never triaged: warn-severity):
triage-2026-08-22.md / -23.md: nas-secret-file-perms -> 'NAS disk I/O slow ... within the timeout window'; suggested `ssh nas \"timeout 300 find /volume1/docker ...\"`
```

</details>

### UL175. Stale nas-08 comment: backup-immich-dump-fresh comment claims the immich dump is broken, but it has been firing daily and the check passes `known-issue`
**Host:** nas · **Component:** verification/checks.d/backups.yaml · **Auditor:** svc:nas-dsm-tasks · **Work item:** `fix-100`

backups.yaml lines 3-4 comment the backup-immich-dump-fresh check as 'Guards reopened task nas-08. FAILS today (last dump 2026-07-02) - correct and desired until the immich dump cron on the NAS is fixed.' Live reality: the dump has been running daily (Aug 15-23 all present, newest 2026-08-23 02:31 245M) and the check PASSES in the daily run and the 22:23 audit. The immich dump cron (nas-08) is effectively RESOLVED but the repo comment/task ledger still describes it as failing-by-design. This is doc/tracker drift only — no live impact. NOT fixed (read-only audit mandate); recommend reconciling the comment and nas-08 status in tasks.json/progress.json.

<details><summary>Evidence</summary>

```
$ sed -n '3,5p' foss-setup/verification/checks.d/backups.yaml
# Guards reopened task nas-08. FAILS today (last dump 2026-07-02) - correct and
# desired until the immich dump cron on the NAS is fixed.
vs live: newest immich dump = immich-2026-08-23.sql.gz 245M @02:31 (fresh daily); audit backup-immich-dump-fresh=pass
```

</details>

### UL176. Coverage gap: the 'class canary' sweeps Radarr+Sonarr only, but whisparr is live — a whisparr hasFile item pointing at a sample/iso/rar would be invisible to the suite
**Host:** nas · **Component:** verification/checks.d/media-watchable.yaml:media-arr-file-quality · **Auditor:** meta:media-watchable · **Work item:** `fix-101`

arr-file-quality.py hardcodes exactly two apps (RADARR_URL 192.168.10.4:7878, SONARR_URL 192.168.10.4:8989) and its output confirms scope (radarr=0 sonarr=0). Yet the file's own header frames check (d) around M27 whisparr rar-stalls ('else rar'd adult grabs stall silent'), and whisparr is confirmed live on the NAS (302 login redirect at 192.168.10.4:6969 = healthy per fleet convention). The only whisparr guard is check (d), a grep for the [[whisparr]] block in unpackerr.conf — a config-presence tripwire that cannot see import-quality defects. So the exact fix-27 defect class (hasFile=True pointing at a Sample/*.avi, .iso, or un-extracted .rar) recurring in whisparr would be green everywhere: green in whisparr, unswept by (a), untouched by (d). Sonarr rar-backlog is similarly outside check (c), but that scoping is explicitly justified in-file (raw-filesystem noise exclusion), whereas the whisparr omission from (a) is unexplained — likely an oversight since the sweep pattern (one /api/v3 call) would extend trivially. Low severity: adult library, lower operator impact, and the rar-stall sub-class is at least indirectly mitigated by unpackerr itself. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'grep -n -i "whisparr\|radarr-url\|sonarr-url" /opt/verification/bin/arr-file-quality.py'
-> 81: ap.add_argument("--radarr-url", default=os.environ.get("RADARR_URL", "http://192.168.10.4:7878"))
-> 82: ap.add_argument("--sonarr-url", default=os.environ.get("SONARR_URL", "http://192.168.10.4:8989"))
-> (no whisparr hits in sweep logic; only doc mentions)
ssh mini 'curl -sm 8 -o /dev/null -w "whisparr_6969=%{http_code}\n" http://192.168.10.4:6969/'
-> whisparr_6969=302  (login redirect = healthy per lane known-normal list)
Today's sweep output: WATCHABLE_OK bad=0 radarr=0 sonarr=0 scanned_movies=287 scanned_series=132 (no whisparr column)
yaml line 63 name: "unpackerr: whisparr block present (M27 — else rar'd adult grabs stall silent)"
```

</details>

### UL177. Monitoring gap: beets checks are liveness/freshness-only, mask the empty library
**Host:** nas · **Component:** verification/checks.d/nas-services.yaml (nas-beets-ingest-fresh) · **Auditor:** svc:beets · **Work item:** `fix-100`

Both beets checks are green yet the tagging output is zero. nas-beets only asserts the web UI answers 200 on :8337; nas-beets-ingest-fresh only asserts import.log was modified in the last 30h ('find ... -mmin -1800'). Neither probes the CONSUMER end (did anything actually get tagged?). A daily run that logs only 'skip /music/YouTube' still touches import.log, so nas-beets-ingest-fresh passes forever against an empty library - exactly the green-but-broken class mandate 1/2 warns about. A consumer-grade check would assert e.g. 'beet stats' track count > 0, or count 'added' lines in import.log. Confirmed against the audit-safe run: nas-beets=pass(200), nas-beets-ingest-fresh=pass(ingest=fresh) while beet stats shows Tracks:0. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini python3 (read /tmp/verify-audit-uc/results.json)
nas-beets | pass | 200
nas-beets-ingest-fresh | pass | ingest=fresh

check def (nas-services.yaml:179-185):
  - id: nas-beets-ingest-fresh
    cmd: find /volume1/docker/beets/import.log -mmin -1800 | grep -q . && echo ingest=fresh || echo ingest=STALE
    expect: '^ingest=fresh$'

# but: beet stats -> Tracks: 0 (see prior finding) -> check green over an empty library
```

</details>

### UL178. CRIT secrets-perms check has chronically timed out for 10+ days (60s too tight) — invariant unmonitored, not a one-off IO casualty `known-issue`
**Host:** nas · **Component:** verification/checks.d/secrets.yaml :: nas-secret-file-perms (fix-23) · **Auditor:** triage:nas-secret-file-perms · **Work item:** `fix-92` · *skeptic-confirmed*

The crit check nas-secret-file-perms failed tonight with exit_code 124 / 'TIMEOUT after 60s' (duration_s 60.06). This is a KNOWN residual (fix-23; baseline explicitly lists it) but it is worse than a nightly IO-load blip: mini triage history shows the IDENTICAL timeout diagnosis every day it ran across 08-13, 08-15, 08-16, 08-17, 08-18, 08-21, 08-22, 08-23 — including quiet days with no storm. So the storm does NOT solely explain it; the durable root cause is a harness design flaw: the 60s timeout wrapper is too tight for a full-tree `find /volume1/docker \( -name @eaDir -o -name '#recycle' \) -prune -o -type f ... -perm /0044` over a large tree (29 app dirs + Synology @eaDir metadata sidecars per folder). The check does not degrade gracefully — it hard-fails on the whole crit channel. Net effect: a CRIT security invariant (no group/world-readable secret files under /volume1/docker) has produced NO real signal for 10+ consecutive days. Recommended harness fixes (NOT applied, read-only mandate): raise timeout to >=180s, and/or add -xdev + prune @eaDir earlier, and/or split per-app-dir, and/or emit a distinct 'DEGRADED/timeout' status instead of counting as a plain crit fail. known_issue:true = fix-23.

*Severity adjusted high→low during adversarial verification.*

*Verify note:* Factual core holds (the check does time out under load; 60s is fragile) but the finding's mechanism and severity are wrong. (1) NOT a fixed harness/tree-size design flaw: the identical find at the SAME load (~10) took 50.6s cold-cache but 1.18s on immediate re-run (warm cache) — the cost is cold metadata + Synology backup IO-contention (synoimgbkptool/jbd2 per finding 22), i.e. the already-tracked fix-23/fix-55 environmental root cause, not tree size. (2) NOT chronically blind: triage shows PASS on 08-14 and 08-19 (NAS was reachable those days — 3 other nas- checks evaluated on 08-14, all nas checks green on 08-19 — nas-secret-file-perms just wasn't among failures), refuting 'NO real signal for 10+ consecutive days.' (3) The security invariant is live-verified HEALTHY: find returned 0 (zero group/world-readable .env|config files). (4) The '60s wrapper' is the global checks_runner.py CHECK_TIMEOUT=60 default; this check sets no per-check timeout: — a one-line config gap, not a design flaw. Downgraded high->low: a flaky/coverage check-hardening item (raise per-check timeout / prune @eaDir) on a healthy invariant already covered by fix-23 + fix-55; not a high-severity security exposure.

<details><summary>Evidence</summary>

```
$ python3 -c 'import json;d=json.load(open("results.json"));[print(c["status"],c["exit_code"],c["duration_s"],repr(c["output"])) for c in d["checks"] if c["id"]=="nas-secret-file-perms"]'
fail 124 60.06 'TIMEOUT after 60s'

$ ssh mini 'for d in 08-13 08-15 08-16 08-17 08-18 08-21 08-22 08-23; do echo == $d; grep -A4 nas-secret-file-perms /var/lib/verification/triage-2026-$d.md | grep -i timed; done'
(all 8 days) "diagnosis": "The permission check ... timed out after 60 seconds."

check cmd (secrets.yaml:30): find /volume1/docker ( -name @eaDir -o -name '#recycle' ) -prune -o -type f ( -name '*.env' -o -name '.env' -o -name 'config.ini' -o -name 'config.xml' ) -perm /0044 -print | wc -l ; expect ^0$ ; severity crit
```

</details>

### UL179. Whisparr adult-acquisition pipeline frozen: 1055 scenes / 0 files vs Stash 3232 scenes (parity gap = 3232) `known-issue`
**Host:** nas · **Component:** whisparr -> stash pipeline · **Auditor:** flow:adult-whisparr-stash · **Work item:** `fix-88` · *skeptic-confirmed*

The Whisparr->Deluge->unpackerr[[whisparr]]->Stash automation delivers ZERO content to Stash. Whisparr (v2.2.0.108, branch v2, uses Series/Episodes model) has 1 Series (the sole site, id=3) with Monitored=0, and 1055 Episodes (scenes) of which 0 are monitored and 0 have files; EpisodeFiles table is empty, History=0, Blocklist=0, PendingReleases=0, live queue totalRecords=0, wanted/missing=0. DownloadHistory shows exactly 13 events, ALL clustered in a single ~26-second burst on 2026-07-21 19:32 (the day the series was added) and NOTHING since -- and even those 13 grabs produced 0 imported files (EpisodeFiles=0 all-time). Meanwhile Stash (nas:9999, v0.31.1) reports scene_count=3232 + image_count=1379 via authenticated GraphQL. The automation contributes 0% to Stash's 3232-scene library; those scenes were populated out-of-band (manual/historical into /data/), NOT by this chain. Failure-pattern #13 (silently-frozen poller / zero-throughput green): nas-whisparr /ping and stash-serving both PASS in the 22:23 run, masking a dead pipeline. Corroborates + quantifies the documented whisparr-frozen gap this lane was assigned. NOT fixed per read-only mandate. Whether the site was deliberately unmonitored is unclear, but the pipeline has never successfully imported a single file end-to-end.

*Severity adjusted high→low during adversarial verification.*

*Verify note:* Raw facts reproduce, but severity is wrong: this is operator-intent, not a broken/high-severity regression. (1) The single series is DELIBERATELY monitored=False with 0 monitored episodes — Whisparr never auto-grabs unmonitored content, so there is nothing to "freeze": no error signature, no failed-import backlog, no stuck queue, no storm. (2) seed-13 (the whisparr task) is done:true and NOT reopened; its own steps explicitly offer "Alternative: keep Stash manual and just add the indexers for search-only" and describe "existing Stash (v0.31.1, manual today)". The observed state (indexers wired, series unmonitored) IS the accepted search-only end-state. (3) The 13 grabs in a 26s burst on deploy-day 2026-07-21 are a one-time setup test, not a poller that later froze. (4) "parity gap = 3232" is a non-defect: Stash is manual by design and actively grown — newest scenes created 2026-07-29 (after whisparr deploy) with files at /data/ root, NOT /data/whisparr, confirming out-of-band manual population that was never whisparr's job. The "#13 silently-frozen poller masking a dead pipeline" framing fails because nothing is supposed to be flowing. nas-whisparr /ping and stash-serving pass correctly (both up). Correct classification: low/info observation ("whisparr deployed but unmonitored/search-only; Stash manual by design"), not a high-severity broken automation.

<details><summary>Evidence</summary>

```
ssh nas whisparr2.db (sudo, read-only copy): Series count=1 -> (Id=3, Monitored=0, Added='2026-07-21 19:33:27Z'); Episodes total=1055, monitored=0, hasFile(EpisodeFileId>0)=0; EpisodeFiles=0; History=0; Blocklist=0; PendingReleases=0; DownloadHistory min='2026-07-21 19:32:18Z' max='2026-07-21 19:32:44Z' count=13; DownloadClients=('Deluge',1); Indexers=3x('Torznab',1,1,1)
$ curl -s -H X-Api-Key:*** http://localhost:6969/api/v3/system/status -> appName=Whisparr version=2.2.0.108 branch=v2
$ curl .../api/v3/series -> series(count=1 id=3 monitored=False episodeFileCount=0 totalEpisodeCount=1055)
$ curl '.../api/v3/history?pageSize=1' -> totalRecords=0 ; queue -> totalRecords=0 ; wanted/missing -> totalRecords=0
$ curl -s -X POST http://localhost:9999/graphql -H 'ApiKey:***' -d '{"query":"{ stats { scene_count image_count } }"}' -> {"data":{"stats":{"scene_count":3232,"image_count":1379}}}
$ ...'{ findScenes(filter:{per_page:1}){ count } }' -> {"data":{"findScenes":{"count":3232}}}
```

</details>

### UL180. Monitoring is liveness-only (/ping) — no consumer-grade whisparr check (mandate 2 gap)
**Host:** nas · **Component:** whisparr / monitoring coverage · **Auditor:** svc:whisparr · **Work item:** `fix-100`

whisparr is in the coverage manifest (verification/coverage/nas.containers:32) and has one standing check, nas-whisparr, which curls http://nas:6969/ping asserting {"status":"OK"} (nas-services.yaml:195). That is process-liveness only — it passed green this whole time while the service has 0 files / 0 history. Per standing mandate 2, no standing check probes whisparr's consumer end (episode-file throughput / import success / hasFile-beside-metadata). Lane notes say hasFile parity is exercised by chain-36, but there is no per-service consumer check that would catch the zero-throughput dormancy. Homepage tile IS present and catalog row is correct (see info finding). Recommend a content-grade check (e.g. episodeFileCount>0 once a site is monitored, or history-freshness dead-man). Not created per read-only mandate.

<details><summary>Evidence</summary>

```
verification/checks.d/nas-services.yaml:198 cmd: curl -s -m 8 http://nas:6969/ping ; expect '"status":\s*"OK"'
verify-audit-uc results.json: id=nas-whisparr status=pass output={"status":"OK"}
grep whisparr verification/coverage/nas.containers -> line 32 (present)
```

</details>

### UL181. Orphaned 3.6GB gamefaqs .old- leftover in /volume1/zim/.incoming from the chunked-ZIM swap
**Host:** nas · **Component:** zim-download-queue / .incoming · **Auditor:** svc:kiwix · **Work item:** `fix-96`

One stale artifact sits in the download staging dir: /volume1/zim/.incoming/gamefaqs_en_all_2020-03.zim.old-20260806 (3,605,438,567 bytes, mtime Aug 6). This is the OLD pre-chunked GameFAQs subset shard, manually moved aside during the 2026-08-17 chunked rebuild (which produced the live 4.6GB gamefaqs_en_all_2020-03.zim at /volume1/zim). It is NOT a partial/resumable download (the queue only leaves partials of in-flight files, and no queue run is active), so wget -c will never touch it — it is dead reclaimable space (~3.6GB). No functional impact; /volume1 has 8.5T free. NOT fixed per read-only mandate; recommend a one-line rm during the next maintenance window. Not covered by an existing open task (fix-45 nas-core-dumps and fix-69 mini-scratch-hygiene are adjacent hygiene items but neither targets this path).

<details><summary>Evidence</summary>

```
ssh nas 'ls -la /volume1/zim/.incoming/' -> gamefaqs_en_all_2020-03.zim.old-20260806  3605438567  Aug 6 13:15 (only file in .incoming besides . and ..)
ssh nas 'ls -lt /volume1/zim/*.zim | head' -> live gamefaqs_en_all_2020-03.zim 4648911784 2026-08-17 16:49 (the chunked replacement)
ps: no active 'wget -c' queue run
```

</details>

### UL182. Media-domain check misfiled in alerting.yaml (id media-*, task_id read-14 Pinchflat, media runbook)
**Host:** repo · **Component:** checks.d/alerting.yaml: media-youtube-mounts-rw · **Auditor:** meta:alerting · **Work item:** `fix-100`

media-youtube-mounts-rw is a YouTube-pipeline mount-writability probe (task_id read-14 = 'Deploy Pinchflat', runbook wiki/runbooks/media.md) living in the alerting-chain file. Domain-scoped runs and per-file reporting (last-summary, wiki reference/checks/alerting.md) attribute it to alerting, and its dead media.md runbook (see separate finding) compounds the misfit. The probe itself is genuinely consumer-grade (real touch+rm on both mounts) and both mounts verified mounted live — the content is fine, only the placement is wrong; belongs in a media checks file.

<details><summary>Evidence</summary>

```
alerting.yaml lines 100-108: id media-youtube-mounts-rw, task_id read-14, runbook wiki/runbooks/media.md
ssh mini 'mountpoint /mnt/nas-youtube; mountpoint /mnt/nas-music-rw' -> both 'is a mountpoint'
python3 tasks.json lookup -> read-14 :: Deploy Pinchflat — archive YouTube channels into Plex
```

</details>

### UL183. Stale header comment claims the immich-dump check 'FAILS today (last dump 2026-07-02)' — dumps have been fresh daily for at least a week and nas-08 is closed
**Host:** repo · **Component:** checks.d/backups.yaml: backup-immich-dump-fresh header comment · **Auditor:** meta:backups · **Work item:** `fix-100`

Lines 3-4 say the check's failure is 'correct and desired until the immich dump cron on the NAS is fixed'. Live state: daily 256MB dumps land at 02:31 (Aug 18-22 all present), the check passes in today's run, and nas-08 is done in progress.json and NOT in the reopened ledger. The comment now inverts reality: it primes a future reader to treat a genuine backup-immich-dump-fresh failure as 'expected/desired' and dismiss a crit alert. One-line comment fix when the file is next touched (remember gen-checks-pages.py in the same commit per checks.d hygiene). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
backups.yaml lines 3-4: '# Guards reopened task nas-08. FAILS today (last dump 2026-07-02) — correct and desired # until the immich dump cron on the NAS is fixed.'
$ ssh nas 'ls -lt /volume1/docker/immich/backups | head -3' -> immich-2026-08-22.sql.gz (Aug 22 02:31, 256584329 bytes), immich-2026-08-21.sql.gz, ...
Today's run: backup-immich-dump-fresh | pass
progress.json: nas-08 done=True, not in reopened ledger
```

</details>

### UL184. Runbook wiki/runbooks/backups.md referenced by 5 checks (3 of them crit) does not exist anywhere in the repo
**Host:** repo · **Component:** checks.d/backups.yaml: runbook references · **Auditor:** meta:backups · **Work item:** `fix-99`

backup-immich-dump-fresh, restic-snapshot-fresh-mini, restic-snapshot-fresh-rig, backup-immich-dump-nonempty and nas-hyperbackup-b2-fresh all carry `runbook: wiki/runbooks/backups.md`. There is no wiki/runbooks/ directory; the real runbooks live under foss-setup/wiki/docs/runbooks/, which contains only backup-restore.md and game-backups.md — no backups.md (the only backups.md in the tree is the GENERATED checks-reference page wiki/docs/reference/checks/backups.md, which is not a runbook and must not be hand-edited). An operator paged at 3AM on the crit immich/hyperbackup checks follows a dead link. The other 8 checks correctly point at wiki/runbooks/backup-restore.md which resolves (wiki/docs/runbooks/backup-restore.md exists) — re-pointing the 5 stale refs there is the cheap fix. Wider rot outside this lane's file: wiki/runbooks/{nas,rig,docker}.md (32+27+16 references across other checks.d files) are also missing while verification.md and alerting.md exist — flagging for the meta-audit rollup. Not covered by any open task.

<details><summary>Evidence</summary>

```
$ grep -c 'wiki/runbooks/backups.md' foss-setup/verification/checks.d/backups.yaml -> 5 checks
$ ls foss-setup/wiki/docs/runbooks/ | grep -i backup -> backup-restore.md, game-backups.md (no backups.md)
$ ls foss-setup/wiki/runbooks -> No such file or directory
$ find foss-setup -name 'backups.md' -> only foss-setup/wiki/docs/reference/checks/backups.md (generated reference page)
for f in nas.md rig.md docker.md verification.md alerting.md backup-restore.md backups.md -> nas/rig/docker/backups MISSING, verification/alerting/backup-restore EXIST
```

</details>

### UL185. runbook values point at wiki/runbooks/*.md — real files live under wiki/docs/runbooks/
**Host:** repo · **Component:** runbook: field (all 6 checks) · **Auditor:** meta:secrets · **Work item:** `fix-99`

All 6 checks reference `wiki/runbooks/secrets-hygiene.md` (5x) or `wiki/runbooks/backup-restore.md` (1x, nas-ha-backup-acl). Neither path exists — `foss-setup/wiki/runbooks/` is not a directory; the real files are `foss-setup/wiki/docs/runbooks/secrets-hygiene.md` and `.../backup-restore.md`. This is HARMLESS at runtime: run-checks.sh never reads the runbook field and no doc generator renders the per-check runbook as a link (grep found zero usages), so nothing 404s — it is a stale pointer-text only. It is also a fleet-wide convention split, not unique to this file (`wiki/runbooks/` prefix used by ~hundreds of checks e.g. rig.md 32x, docker.md 27x; the correct `wiki/docs/runbooks/` form is used by others e.g. git-hygiene.md 18x). Flagging per the audit integrity rule (runbook must resolve to an existing file); fix belongs at the fleet-convention level, not this lane alone.

<details><summary>Evidence</summary>

```
$ ls wiki/runbooks/secrets-hygiene.md -> No such file or directory
$ ls wiki/docs/runbooks/secrets-hygiene.md -> exists (6.6k)
$ ls wiki/docs/runbooks/backup-restore.md -> exists (12k)
$ grep -n runbook verification/bin/run-checks.sh -> (no matches; field unused by runner)
$ grep for per-check runbook render in scripts/ -> (no matches)
```

</details>

### UL186. Stale comment says dns-nas-* checks 'FAIL today ... correct and desired until dns-02 is redone' — dns-02 is closed and both checks pass live
**Host:** repo · **Component:** verification/checks.d/dns.yaml · **Auditor:** meta:dns · **Work item:** `fix-100`

Lines 43-44 above dns-nas-internal still read: 'The two checks below guard reopened task dns-02 ... They FAIL today (connection refused) — that is correct and desired until dns-02 is redone.' This contradicts the file's own updated header (lines 3-4: 'live since dns-02 closed; these checks guard against regression') and reality: progress.json has dns-02 done=true and not in the reopened ledger, and both probes answered live from mini (nas-internal -> 192.168.10.2, nas-external -> example.com A records). Risk: a responder or triage LLM reading the yaml during a real NAS-resolver regression could dismiss the crit FAIL as 'expected/desired' state. Comment should be deleted or rewritten as history. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ python3 -c "import json; p=json.load(open('foss-setup/docs/progress.json')); print('done:', p['done'].get('dns-02')); print('reopened:', 'dns-02' in p.get('reopened',{}))"
done: True
reopened: False
$ ssh mini 'dig +short +time=3 +tries=1 @192.168.10.4 home.tabaska.us; dig +short +time=3 +tries=1 @192.168.10.4 example.com'
192.168.10.2
104.20.23.154
172.66.147.243
```

</details>

### UL187. Both game-saves checks point at a runbook file that does not exist anywhere in the repo
**Host:** repo (foss-setup) / mini runner · **Component:** verification/checks.d/game-saves.yaml · **Auditor:** meta:game-saves · **Work item:** `fix-99`

Both checks carry runbook: wiki/runbooks/rig.md. No such file resolves: foss-setup/wiki/docs/runbooks/rig.md is missing, and the only rig.md files in the wiki tree are hosts/rig.md and reference/checks/rig.md — neither mentions ludusavi. The dedicated existing runbook wiki/docs/runbooks/game-backups.md (used by 9 sibling game checks) also has zero ludusavi/game-saves/syncthing content, so there is no valid runbook target for these checks at all; nearest real docs are wiki/docs/services/syncthing.md and reference/checks/game-saves.md. checks_runner.py line 229 copies the runbook field into every result entry (and thus alert payloads), so an on-call alert for a degraded save mesh carries a dead pointer. This is part of a fleet-wide legacy 'wiki/runbooks/' prefix pattern (14 check files; rig.md referenced 32x, docker.md 27x, nas.md 16x — docker.md and nas.md are also missing from wiki/docs/runbooks/), but is filed here for this lane's file. Fix path: repoint to a real page (e.g. add a ludusavi/game-saves section to wiki/docs/runbooks/game-backups.md or hosts/rig.md and update both checks). NOT fixed per read-only mandate. Not covered by any open task (open game-* = game-04/09/14, all unrelated).

<details><summary>Evidence</summary>

```
$ grep -h 'runbook:' foss-setup/verification/checks.d/game-saves.yaml
    runbook: wiki/runbooks/rig.md   (x2)
$ for p in foss-setup/wiki/runbooks/rig.md foss-setup/wiki/docs/runbooks/rig.md; do [ -f "$p" ] && echo EXISTS: $p || echo missing: $p; done
missing: foss-setup/wiki/runbooks/rig.md
missing: foss-setup/wiki/docs/runbooks/rig.md
$ find . -name 'rig.md' -not -path './.git/*'
./foss-setup/wiki/docs/hosts/rig.md
./foss-setup/wiki/docs/reference/checks/rig.md
$ grep -ic 'ludusavi' foss-setup/wiki/docs/hosts/rig.md
0
$ grep -in 'ludusavi\|game-saves\|syncthing' foss-setup/wiki/docs/runbooks/game-backups.md
(no output)
$ sed -n '227,230p' foss-setup/verification/bin/checks_runner.py
        entry = {k: c.get(k) for k in
                 ("id", "name", "host", "domain", "cmd", "severity",
                  "task_id", "runbook")}
```

</details>

### UL188. Marinara/Lumiverse connection checks FAIL but live connections present/correct (known-stale) `known-issue`
**Host:** rig · **Component:** Marinara (:3002) & Lumiverse (:3001) in-app connection checks · **Auditor:** flow:ai-chat-serving · **Work item:** `fix-100`

rig-marinara-connections and rig-lumiverse-connections FAIL in results.json (task_id ai-01, in the pre-existing baseline). Re-verified live: connections ARE present and correct, so this is the known-stale connection-check assertion, not consumer breakage. Marinara /api/connections shows 'LiteLLM Creative | openai | https://llm.tabaska.us/v1 | goetia' plus 4 image_generation conns (NoobAI/Z-Image/CyberRealistic-NSFW/Flux.2-Klein) all on the comfyui-arbiter:8189 alias, plus OpenRouter Free. Lumiverse DB shows llm='LiteLLM Creative|https://llm.tabaska.us/v1|key1' + 4 ComfyUI image conns on arbiter. The check appears to assert exactly-3 image conns / a rigid name set; live has 4 + extra, so the assert is stale. Consumer key path independently proven: rig-llm-scoped-keys-public PASS — both frontend keys resolve via llm.tabaska.us to exactly [cydonia,dolphin-venice,goetia]; frontends up + Caddy auth-gated (rig-marinara/rig-lumiverse/rig-marinara-auth-gate PASS). RP-model completion (24B) deliberately not triggered to honor GPU-light mandate in evening (outside 01-07 window). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ curl -s http://cachyos.tailb31641.ts.net:3002/api/connections | (name|provider|baseUrl|model)
Anime Image | image_generation | http://comfyui-arbiter:8189 | NoobAI-XL-v1.1.safetensors
Realistic Image (Z-Image Turbo) | image_generation | http://comfyui-arbiter:8189 | z_image_turbo_bf16.safetensors
Realistic NSFW (CyberRealistic) | image_generation | http://comfyui-arbiter:8189 | cyberrealistic-nsfw-zimage-turbo.safetensors
Realistic Image (Flux.2 Klein) | image_generation | http://comfyui-arbiter:8189 | klein-9b-comfyui
LiteLLM Creative | openai | https://llm.tabaska.us/v1 | goetia
OpenRouter Free | openrouter | https://openrouter.ai/api/v1 | openrouter/free
[lumiverse DB] llm=LiteLLM Creative|https://llm.tabaska.us/v1|key1 ; img=4 ComfyUI conns on comfyui-arbiter:8189
[results.json] rig-llm-scoped-keys-public PASS: KEYSCOPE=cydonia,dolphin-venice,goetia (both keys)
```

</details>

### UL189. 59999 all-interface listener is MoonDeckBuddy — legitimate Moonlight/Sunshine game-streaming companion, not yet blessed in baseline `known-issue`
**Host:** rig · **Component:** MoonDeckBuddy (Moonlight/Sunshine companion) / fix-51 baseline · **Auditor:** triage:lan-listeners-drift-rig · **Work item:** `fix-98`

Port 59999 binds *:59999 and is owned by MoonDeckBuddy (pid 651837, AppImage /tmp/.mount_MoonDe.../usr/bin/MoonDeckBuddy), running 7d01h (started ~2026-08-16). MoonDeckBuddy is the host-side companion for the MoonDeck Steam-Deck Moonlight plugin; it drives Steam-game launches over the Apollo/Sunshine stream, which is already baselined on rig (47984/47989/47990/48010). This is expected gaming-streaming infrastructure, not a surprise or malicious listener. Unauthenticated on the flat LAN under the same accepted trusted-VLAN posture as the AI/GPU endpoints. Session-bound (goes away with the app), so additive-only drift won't flap. Remediation (NOT applied, read-only): add '59999 # MoonDeckBuddy — Moonlight/Sunshine companion' to rig.ports and re-deploy. Covered by the open fix-51 baseline.

<details><summary>Evidence</summary>

```
$ ssh rig 'ss -tlnp | grep -E ":59999\b"'
LISTEN 0 50 *:59999 *:* users:(("MoonDeckBuddy",pid=651837,fd=18))

$ ssh rig 'ps -o pid,comm,etime,args -p 651837'
 651837 MoonDeckBuddy 7-01:29:00 /tmp/.mount_MoonDeACcFdb/usr/bin/MoonDeckBuddy
```

</details>

### UL190. Bake-off fairness caveat: chat carries full UI capability flags; the two trial lanes carry only {vision:False}
**Host:** rig · **Component:** OWUI model records — meta.capabilities (owned by seed-owui-model-capabilities.sh) · **Auditor:** flow:chat-bakeoff · **Work item:** `fix-103`

The MCP tool belt (meta.toolIds, 8 servers) is identical across all three lanes, so the tool-belt bake-off comparison is fair. However meta.capabilities is asymmetric: `chat` has the full flag set (file_context, file_upload, web_search, image_generation, code_interpreter, terminal, citations, status_updates, usage, builtin_tools; vision:False) while chat-q38-trial and chat-gemma-26b-trial carry ONLY {vision:False}. Effect: in the OWUI UI the two trial lanes lack the native web_search / image_generation / code_interpreter / terminal / file_upload affordances that `chat` exposes (their MCP fetch/comfyui/etc. tools still function, so impact is limited). This field is owned by seed-owui-model-capabilities.sh, not the two seed scripts that define prompt+toolbelt, so it is outside the 'identical tool belt + prompt' contract this chain probes — the vision:False value is itself correct per memory plant-id-bioclip-quirks (vision truthful only on chat-vision/cydonia/dolphin-venice/goetia). Cannot determine from read-only inspection whether the asymmetry is deliberate (chat is the established production lane; trials created programmatically) or drift. NOT fixed per read-only mandate. Recommend operator decide whether the two trial lanes should get chat's capability flags for a strictly apples-to-apples UI bake-off.

<details><summary>Evidence</summary>

```
$ curl -s -H "Authorization: Bearer $K" http://localhost:3000/api/v1/models/model?id=<lane>  (meta.capabilities)
chat:                 {'file_context':True,'vision':False,'file_upload':True,'web_search':True,'image_generation':True,'code_interpreter':True,'terminal':True,'citations':True,'status_updates':True,'usage':True,'builtin_tools':True}
chat-q38-trial:       {'vision':False}
chat-gemma-26b-trial: {'vision':False}
```

</details>

### UL191. STILL-OPEN-VALID: Linux-side RTC mitigation holding (offset 0s) but durable Windows RealTimeIsUniversal fix unverifiable/undone `known-issue`
**Host:** rig · **Component:** RTC / rig-clock-sane (fix-75) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-75` · *skeptic-confirmed*

fix-64's Linux mitigation is green (rtc=UTC, ntp=yes, offset 0s). The durable Windows-side registry fix (HKLM...RealTimeIsUniversal=1) is the actual fix-75 deliverable and cannot be probed read-only (rig Windows partition not accessible; SSH is CachyOS). Human leg. NOT fixed per read-only mandate.

*Verify note:* Fresh independent probes reproduce the finding exactly. Cross-checked rig wall clock against mini's clock (hard rule #6, independent vantage rather than the check's self-report): skew=0s. Fresh `timedatectl` on rig (different command than the check one-liner) confirms Linux-side mitigation is holding: NTP synchronized yes, NTP service active, RTC in local TZ no (=UTC), and RTC time equals UTC time — i.e. offset 0s, rtc=no, ntp=yes. The durable fix is genuinely the Windows-side human leg: tasks.json fix-75 summary literally names HKLM...\TimeZoneInformation\RealTimeIsUniversal=1 as the durable deliverable, and fix-75 is an open-queue item; it cannot be probed read-only from CachyOS SSH (no Windows-partition/registry access). The finding correctly separates the check's own task_id (fix-64, the Linux mitigation, which is green) from the durable fix-75 deliverable (unverified/undone). Severity low, known_issue=true, matches lane-context known-normal ("rig Windows RTC (fix-75)" = human leg pass by design). No stale-cache / RTC-skew / vantage error to exploit — the Linux clock is truly in sync and the Windows leg is truly unverifiable read-only.

<details><summary>Evidence</summary>

```
rig-clock-sane [pass]: out='CLOCK_OK offset=0s rtc=no ntp=yes'
```

</details>

### UL192. STILL-OPEN-VALID (deferred): 15 of 19 Suwayomi library series still have 0 downloaded chapters `known-issue`
**Host:** rig · **Component:** Suwayomi/Komga manga backfill (fix-78) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-78`

Live Suwayomi (rig:4567): in_library=19, zero_downloaded=15 (was 16/19 at filing — one series backfilled, marginal). Only the 4 downloaded series reached Komga (komga check: series=4, disk_cbz=281, indexed=281 lag=0) — the parity check is green but it does NOT measure the backfill gap. Full backfill is thousands of chapters = storage/bandwidth decision deferred pending operator go on scope. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh rig 'curl -s http://192.168.10.12:4567/api/graphql {mangas(inLibrary){totalCount nodes{downloadCount}}}' -> in_library=19 zero_dl=15
komga-manga-indexed-vs-disk [pass]: 'disk_cbz=281 indexed=281 series=4 lag=0'
```

</details>

### UL193. Continue 2.0.0 exthost logs missing ort-wasm-simd-threaded.wasm (onnxruntime-web local features degraded; non-fatal)
**Host:** rig · **Component:** VSCodium remote server / Continue 2.0.0 extension (~/.vscodium-server) · **Auditor:** flow:remote-ai-coding · **Work item:** `fix-103`

The staged Continue extension (~/.vscodium-server/extensions/continue.continue-2.0.0-linux-x64) is missing its onnxruntime-web wasm asset (out/dist/ort-wasm-simd-threaded.wasm). The exthost logged 'ENOENT ... ort-wasm-simd-threaded.wasm' / 'failed to asynchronously prepare wasm' then still exited cleanly (code 0), so it is NON-FATAL — Continue's bundled local ONNX features (local embedding/reranking for @codebase indexing) are degraded, but the config routes the embed role to LiteLLM `embed` (proven working, 1024-dim above) and chat/edit/apply/autocomplete route to LiteLLM `fast`, so the core AI-coding path is unaffected. This is a real observed defect in the staged extension build, not covered by any open task. NOT fixed per the read-only audit mandate — reported only. Note this is last-session log evidence (VSCodium not currently attached; exthost exited).

<details><summary>Evidence</summary>

```
$ ssh rig 'ls -d ~/.vscodium-server/extensions/continue.continue-*'
/home/btabaska/.vscodium-server/extensions/continue.continue-2.0.0-linux-x64
$ ssh rig 'grep -iE "continue.continue|extension host" ~/.vscodium-server/.4c0b0c6...log | tail'
[15:36:24] [ExtensionHostConnection] <stderr> Aborted(Error: ENOENT: no such file or directory, open '.../continue.continue-2.0.0-linux-x64/out/dist/ort-wasm-simd-threaded.wasm')
failed to asynchronously prepare wasm: RuntimeError: Aborted(...ort-wasm-simd-threaded.wasm...)
[05:34:03] Extension Host Process exited with code: 0, signal: null.
```

</details>

### UL194. bioclip-api missing from service-catalog.yaml (lai-22 deploy never added catalog row)
**Host:** rig · **Component:** bioclip-api · **Auditor:** svc:bioclip-api · **Work item:** `fix-97`

bioclip-api (deployed 2026-08-16 as part of lai-22 plant/species ID) has no row in foss-setup/configs/docker-stack/service-catalog.yaml, while sibling internal rig AI services with no public vhost ARE cataloged (kokoro, gpu-arbiter, comfyui-mcp, playwright-mcp all appear with url None). This is a documentation/catalog completeness gap, not a functional problem — the service works and is monitored. It is NOT caught by fix-68 catalog-vhost-parity because bioclip-api has no Caddy vhost (LAN-only internal API on :8199). NOT fixed per read-only mandate. Recommend adding a host:rig row (category 'AI & Gaming', url None) to service-catalog.yaml.

<details><summary>Evidence</summary>

```
$ grep -niE 'bioclip|plant' foss-setup/configs/docker-stack/service-catalog.yaml
(no matches)

$ python3 -c 'yaml ... print host==rig rows'
kokoro | None | AI & Gaming
gpu-arbiter | None | AI & Gaming
comfyui-mcp | None | AI & Gaming
playwright-mcp | None | AI & Gaming
(bioclip-api absent)
```

</details>

### UL195. export-manifests-inventory-fresh is intermediate, not consumer: asserts a journal log line, not the inventory.md artifact, over an unbounded journal window
**Host:** rig · **Component:** checks.d/git-hygiene.yaml:export-manifests-inventory-fresh · **Auditor:** meta:git-hygiene · **Work item:** `fix-100`

The check comment claims it 'probes the CONSUMER end', but the cmd greps `journalctl -u export-manifests.service` (no --since bound) for 'Regenerating inventory.md' and takes tail -1. Two gaps: (1) a run that logs 'Regenerating inventory.md' then fails to write the file still passes — the artifact (inventory.md mtime/content) is never checked; (2) a newer run that crashes before reaching either log string leaves the old 'Regenerating' line as tail -1 and the check keeps passing on stale history until journal rotation (taxonomy class 12, stale last-success). Mitigation exists: the weekly export's healthchecks dead-man covers cadence, and a run that explicitly logs the skip IS caught (tail -1 picks it up). Suggested hardening (NOT applied per read-only mandate): stat inventory.md mtime against the last unit invocation, or bound the journalctl window to the last run. Path baseline verified live: /opt/scripts/inventory/gen-inventory-md.sh present and executable on rig. Currently passing genuinely (10:29 run: 'gen-inventory=present last-leg=Regenerating inventory.md').

<details><summary>Evidence</summary>

```
repo cmd (foss-setup/verification/checks.d/git-hygiene.yaml:330): last=$(journalctl -u export-manifests.service --no-pager 2>/dev/null | grep -Eo 'Regenerating inventory.md|skipping inventory.md refresh' | tail -1)
live: ssh rig 'test -x /opt/scripts/inventory/gen-inventory-md.sh && echo GEN-INV-PRESENT' -> GEN-INV-PRESENT
10:29 run results.json: export-manifests-inventory-fresh pass dur=0.31 'gen-inventory=present last-leg=Regenerating inventory.md\nEXPORT-MANIFESTS-INVENTORY-OK'
```

</details>

### UL196. verify-06 confirmed: unsloth-studio running on rig but absent from the coverage manifest `known-issue`
**Host:** rig · **Component:** coverage manifest (containers-manifest-rig / verify-06) · **Auditor:** svc:host-rig · **Work item:** `fix-97`

Re-verified verify-06 still holds. `docker ps -a` on rig shows unsloth-studio Up 5 days, but the coverage-manifest diff in the audit run reports it as the sole delta (`> unsloth-studio`). This is the known deployed-manifest lag from lai-28 (unsloth-studio deploy 2026-08-17 not yet added to verification/coverage). Violates standing mandate #2 (100% monitoring-coverage tripwire) at the manifest layer, though the service itself IS reachable (port 8210 answers) and has a homepage/URL. NOT fixed per read-only mandate. Covered by verify-06.

<details><summary>Evidence</summary>

```
/tmp/verify-audit-uc/results.json -> 'rig: running containers match coverage manifest' = fail
message: 20a21
> unsloth-studio
---
ssh rig 'docker ps -a' -> unsloth-studio  Up 5 days  (started 2026-08-17T22:11:05Z, restarts=0)
```

</details>

### UL197. Transient CUDA BFC allocation failures (OOM) at night-window start on 08-18 and 08-20 (self-recovered, none since)
**Host:** rig · **Component:** immich_machine_learning / GPU VRAM · **Auditor:** svc:immich-ml-rig · **Work item:** `fix-103`

6 ONNXRuntime BFC arena allocation failures ('Failed to allocate memory for requested buffer of size 7077888' ~7MB) recorded: 3 on 2026-08-18 and 3 on 2026-08-20, at the very start of the night window (the 08-20 pair at 05:15/05:25 UTC = 01:15/01:25 EDT). Root class = rig GPU VRAM contention (glue-14 / taxonomy-17): when the ML container starts at 01:00 EDT, a leftover chat/ComfyUI tenant still holds VRAM for a few minutes before eviction, so the first encode allocations fail with 500. These self-recovered and had no proven consumer impact (smart search has the NAS iGPU fallback, and the crit consumer check runs with min_consecutive_fails:2 to absorb cold-start/contention blips). Last 3 night windows (08-21/08-22/08-23) had ZERO OOMs and last night's window was clean; total error-ish log volume is 66 lines over 3 weeks (far below the >1000 retry-storm threshold). NOT fixed per read-only mandate; reported as an intermittent contention observation, not a live incident. Not tracked by a specific open task (glue-14 is closed); adjacent to the known VRAM-contention class in the lane notes.

<details><summary>Evidence</summary>

```
docker logs immich_machine_learning --since 2026-08-02 | sed 's/ANSI//' | grep 'Failed to allocate memory' | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort | uniq -c =>
      3 2026-08-18
      3 2026-08-20
sample: '2026-08-20 05:15:13 [E:onnxruntime:] Exception during initialization: bfc_arena.cc:358 ... Failed to allocate memory for requested buffer of size 7077888' -> 'ERROR Exception in ASGI application' Fail:[ONNXRuntimeError]:1:FAIL
last-night window OOM count (08-23 05:00-11:00Z): 0
nvidia-smi now (day, ML off): 1369 MiB / 24564 MiB used (card free)
total error-ish lines since 08-02: 66
```

</details>

### UL198. Two wildcard listeners on rig unblessed in BOTH repo and deployed baselines: steam :27036 and MoonDeckBuddy :59999 — need bless-or-kill triage `known-issue`
**Host:** rig · **Component:** lan-exposure/rig listeners · **Auditor:** meta:lan-exposure · **Work item:** `fix-98`

Beyond the deploy-drift 8210, listener-drift.sh flags 27036 and 59999 on rig, and neither appears in the repo rig.ports either — this is genuine untriaged exposure drift, i.e. the tripwire working as designed. Attribution (no sudo needed): 27036 = Steam client (pid 667715, user btabaska; Steam Remote Play/local-transfer discovery port), 59999 = MoonDeckBuddy (pid 651837, btabaska; Steam Deck / Moonlight streaming companion). Both are identifiable legit desktop-session software on the LAN-only gaming host, not an SM56-style rogue nc — hence low severity — but they must be either added to rig.ports (with comments) or removed from the desktop session, or lan-listeners-drift-rig stays red indefinitely and masks future rogue listeners. Covered by fix-51 in today's reopen mapping (lan-listeners-drift-rig fail). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini '/opt/verification/bin/listener-drift.sh rig'
LISTENER_DRIFT=rig:8210,27036,59999 (NEW all-interface listener not in baseline — investigate: sudo ss -tlnp | grep the port)
$ ssh rig 'ss -tlnp 2>/dev/null | grep -E ":(27036|59999) "'
LISTEN 0 128   0.0.0.0:27036  0.0.0.0:*  users:(("steam",pid=667715,fd=140))
LISTEN 0 50    *:59999        *:*        users:(("MoonDeckBuddy",pid=651837,fd=18))
$ grep -E '^(27036|59999)' foss-setup/verification/assets/expected-listeners/rig.ports
(no output — absent from repo baseline too)
```

</details>

### UL199. litellm-adjacent check fails are the KNOWN-stale ai-01 marinara/lumiverse connection-list checks — not a litellm regression `known-issue`
**Host:** rig · **Component:** litellm · **Auditor:** svc:litellm · **Work item:** `fix-100`

The only litellm-touching checks failing in today's run are rig-marinara-connections (rig.yaml:158) and rig-lumiverse-connections (rig.yaml:181), both mapped to ai-01 in the reopen bridge and flagged known-stale in lane context. Re-verified these do NOT indicate a litellm outage: the parallel check 'frontend scoped keys valid via llm.tabaska.us + scoped to exactly the RP trio' PASSED, meaning litellm's scoped-key serving of the cydonia/dolphin-venice/goetia trio to those consumers works. The failing checks only scrape the apps' in-app connection LISTS (a known-stale scraping issue), not the litellm serving path. Out-of-lane for deep re-probe (marinara/lumiverse are separate services). NOT fixed — read-only mandate.

<details><summary>Evidence</summary>

```
results.json -> 'marinara in-app connections present (LiteLLM Creative + 3 ComfyUI image conns)'=fail; 'lumiverse in-app connections present (LLM row w/ key + 3 ComfyUI image conns)'=fail; BUT 'frontend scoped keys valid via llm.tabaska.us + scoped to exactly the RP trio'=pass
```

</details>

### UL200. rig-lumiverse-connections FAIL is a STALE CHECK, not real breakage (adjudicated) `known-issue`
**Host:** rig · **Component:** lumiverse / verification check rig-lumiverse-connections · **Auditor:** svc:lumiverse · **Work item:** `fix-100`

The check is red in today's baseline (task ai-01) but the live connection state is correct and healthy. The expect regex (checks.d/rig.yaml:181) hard-requires the image conn api_url to be 'https://comfyui.tabaska.us' and the title says '3 ComfyUI image conns'. Live: 1 LLM row (LiteLLM Creative | https://llm.tabaska.us/v1 | key present) + 4 image conns all pointing at http://comfyui-arbiter:8189. Per the marinara/lumiverse-wiring memory ('image conns MUST use comfyui-arbiter:8189 alias'), the internal arbiter alias is the CORRECT current wiring -- the regex still encodes the abandoned 2026-07-18 public-gateway wiring, and a 4th conn (Realistic NSFW / CyberRealistic) was added since the '3 conns' title. Proof the live wiring works, not just exists: Weaver image-gen jobs completed through comfyui-arbiter:8189 in the logs. This is the known-stale conn check (lane context + memory: 'Marinara/Lumiverse connection-check staleness is a KNOWN stale-check issue'). Fix = update the regex (comfyui.tabaska.us -> comfyui-arbiter:8189, allow >=3 conns) + title. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
checks.d/rig.yaml:181 expect: '(?s)(?=.*LiteLLM Creative\|https://llm\.tabaska\.us/v1\|key1)(?=.*NoobAI-XL\)\|https://comfyui\.tabaska\.us)(?=.*Z-Image Turbo)(?=.*Flux\.2 Klein)'
Live check output (status=fail): 'llm=LiteLLM Creative|https://llm.tabaska.us/v1|key1\nimg=Anime Image (NoobAI-XL)|http://comfyui-arbiter:8189;Realistic Image (Z-Image Turbo)|http://comfyui-arbiter:8189;Realistic Image (Flux.2 Klein)|http://comfyui-arbiter:8189;Realistic NSFW (CyberRealistic)|http://comfyui-arbiter:8189'
-> lookahead #2 (comfyui.tabaska.us) is the sole miss; all real conns present + arbiter-wired + Weaver jobs completed.
```

</details>

### UL201. Port 59999 = MoonDeckBuddy, deliberately re-enabled 08-16 (commit 0e2ff0d, supersedes fix-64) with docs + UFW scoping + its own PASSING check — but the re-enable never added it to rig.ports, so the harness contradicts itself `known-issue`
**Host:** rig · **Component:** moondeckbuddy / lan-listener baseline (fix-51) · **Auditor:** triage:lan-listeners-drift-rig · **Work item:** `fix-98`

*:59999 is MoonDeckBuddy 1.9.2 (pid 651837, started Sun Aug 16 13:48:46 EDT, AppImage ~/Applications/MoonDeckBuddy-1.9.2-x86_64.AppImage). This is sanctioned, documented infra: commit 0e2ff0d (08-16 13:56) re-enabled it on operator request superseding the fix-64/SM14 retirement; foss-setup/configs/host/rig/moondeckbuddy/README.md documents 'API: TLS on :59999; UFW allows 192.168.10.0/24' plus systemd user units and Apollo tie-in; and gaming.yaml carries check game-moondeck-buddy which PASSES tonight (BUDDY-OK) — so one check asserts :59999 must answer while lan-listeners-drift-rig flags it as unbaselined drift. Exposure posture is better than most baselined rig ports (TLS + pairing-PIN + UFW subnet scoping vs the unauthenticated AI endpoints). Root cause: commit 0e2ff0d touched moondeckbuddy config/docs but not verification/assets/expected-listeners/rig.ports (git log confirms rig.ports untouched between 89a3eb3 08-06 and 2ab1923 08-16 19:29, neither adding 59999) — the standing mandate-2 'update coverage with every service deploy' step was skipped. Fix = add 59999 (and 27036) to repo rig.ports and sudo-deploy to mini. NOT fixed per read-only mandate. Covered by the fix-51 reopen-candidate mapping.

<details><summary>Evidence</summary>

```
$ ssh rig 'ss -tlnp | grep :59999'
LISTEN 0 50 *:59999 *:*  users:(("MoonDeckBuddy",pid=651837,fd=18))

$ ssh rig 'ps -o pid,lstart,user,cmd -p 651837'
651837 Sun Aug 16 13:48:46 2026 btabaska /tmp/.mount_MoonDeACcFdb/usr/bin/MoonDeckBuddy

$ git log --format='%h %ad %s' -- foss-setup/configs/host/rig/moondeckbuddy/ | head -1
0e2ff0d 2026-08-16 13:56:56 -0400 rig streaming: CUDA zero-copy NVENC + MoonDeckBuddy re-enabled (supersedes fix-64)

configs/host/rig/moondeckbuddy/README.md: 'API: TLS on :59999; UFW allows 192.168.10.0/24'

tonight results.json: game-moondeck-buddy pass | BUDDY-OK
```

</details>

### UL202. Anti-drift gap: live ollama override.conf (7 env vars incl KEEP_ALIVE=0) not mirrored as a file under configs/host/rig/
**Host:** rig · **Component:** ollama-shim · **Auditor:** svc:ollama-shim · **Work item:** `fix-102`

The live systemd drop-in /etc/systemd/system/ollama.service.d/override.conf sets OLLAMA_HOST=0.0.0.0:11434, OLLAMA_ORIGINS=*, OLLAMA_FLASH_ATTENTION=1, OLLAMA_KV_CACHE_TYPE=q8_0, OLLAMA_KEEP_ALIVE=0, OLLAMA_MAX_LOADED_MODELS=2, OLLAMA_NUM_PARALLEL=1. Unlike sibling rig host units (ai-stack-watchdog has both .service and .sh mirrored under configs/host/rig/ai-stack-watchdog/), this override has no repo mirror — grep for KEEP_ALIVE/OLLAMA_HOST across configs/host/rig returned nothing. Impact is minor and mitigated: (a) the load-bearing KEEP_ALIVE=0 GPU-contention policy is documented across the wiki (rollout.md, gaming.md, hosts/rig.md, server-guide.md, checks/rig.md) and enforced by check rig-ollama-keepalive; (b) the file itself is captured off-site via the /etc restic backup path. There is no live-vs-repo conflict (nothing in the repo to diff against). The known in-flight WIP drift (modified Caddyfile + homepage services.yaml) is unrelated to ollama. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh rig 'cat /etc/systemd/system/ollama.service.d/override.conf' -> 7 Environment= lines (OLLAMA_HOST, ORIGINS, FLASH_ATTENTION, KV_CACHE_TYPE, KEEP_ALIVE=0, MAX_LOADED_MODELS=2, NUM_PARALLEL=1)
grep -rlniE 'ollama|11434|KEEP_ALIVE' foss-setup/configs/host/rig/ -> NONE-IN-RIG-HOSTCFG
grep -rniE 'KEEP_ALIVE|OLLAMA_HOST' foss-setup/**/*.md -> documented in wiki rollout/gaming/rig/server-guide/checks + check rig-ollama-keepalive expects 'OLLAMA_KEEP_ALIVE=0'
```

</details>

### UL203. Coverage census gap: ollama (host systemd unit) is not enrolled in the coverage manifest (rig.containers is container-only, no rig.services file)
**Host:** rig · **Component:** ollama-shim · **Auditor:** svc:ollama-shim · **Work item:** `fix-101` · *skeptic-confirmed*

The lane-flagged coverage tripwire is real but low-impact. verification/coverage/rig.containers lists only 21 docker containers; ollama runs as a host systemd unit so it structurally cannot appear there, and unlike seedbox (which has a seedbox.services file) rig has no .services census file for host units (ai-stack-watchdog, playit-udp-guard, etc. are also absent). So ollama sits outside the coverage manifest entirely and verify-06 (containers-manifest-rig) cannot flag it. IN PRACTICE it is well-monitored: 5 checks exist and all PASSED in today's run — rig-ollama (liveness :11434, ai-01), rig-ollama-models (asserts llama3.2:3b present, ai-01), rig-ollama-keepalive (asserts OLLAMA_KEEP_ALIVE=0, game-13), plus HA consumer checks ha-assist-rig-llm-reachable (ha-12) and the full ha-assist-conversation-e2e. So this is bookkeeping (100%-coverage-manifest mandate 2) not a monitoring blind spot. Relates to the known process gap (memory: orchestrator-gated-remaining — deploys skip coverage-manifest). NOT fixed per read-only mandate.

*Verify note:* Every claim reproduces under fresh independent probes. The pivotal claim — that ollama is a host systemd unit that structurally cannot appear in a docker-container census — is verified live: `docker ps -a | grep ollama` returns nothing while `systemctl` shows `ollama.service active running` and :11434 serves models. verify-06 (containers-manifest-rig) is confirmed container-scoped (docker ps | diff rig.containers), so it can never flag a host unit. The coverage dir has no rig.services file (only seedbox.services), no ollama/11434 references, and rig.containers holds exactly 21 containers with no ollama. All 5 substitute monitoring checks (rig-ollama, rig-ollama-models, rig-ollama-keepalive, ha-assist-rig-llm-reachable, ha-assist-conversation-e2e) exist and PASS in results.json, so impact is genuinely bookkeeping-only. Severity 'low' is correct — a real mandate-2 census gap (seedbox.services proves the operator does enroll host units elsewhere) but no actual monitoring blind spot. Refutation attempts (wrong vantage / stale cache / operator-intent) all failed; the seedbox.services precedent strengthens the finding rather than refuting it. Unrelated note: containers-manifest-rig currently fails for a different reason (unsloth-studio missing), not ollama.

<details><summary>Evidence</summary>

```
grep -rniE 'ollama|11434' foss-setup/verification/coverage/ -> (no matches)
cat foss-setup/verification/coverage/rig.containers -> amp, beszel-agent, bioclip-api, ... unsloth-studio (21 containers, no ollama)
ls foss-setup/verification/coverage/ -> mini.containers, nas.containers, rig.containers, seedbox.services (no rig.services)
grep -c ollama checks in rig.yaml/ha.yaml -> rig-ollama, rig-ollama-models, rig-ollama-keepalive + ha-assist-rig-llm-reachable, ha-assist-conversation-e2e (all pass today)
```

</details>

### UL204. Anti-drift gap: rig /opt/stacks/palworld is NOT a git repo and has no mirror in the Home repo
**Host:** rig · **Component:** palworld · **Auditor:** svc:palworld · **Work item:** `fix-102`

Per CLAUDE.md 'a fix that changes a live host but not the repo creates drift.' The palworld compose+env live only on the rig host at /opt/stacks/palworld/compose.yaml; `git rev-parse` there returns NOT_A_GIT_REPO (unlike mini's /opt/stacks which is a Forgejo-mirrored repo). There is no palworld directory under foss-setup/configs/host/rig/ either, so the compose.yaml and its ~100 tuned env vars (Difficulty, rates, backup/auto-update cron, REST/RCON ports) exist nowhere in version control. If the rig disk is lost the config is unrecoverable from the repo (the SAVE data is in restic, but not the compose/env). Cannot diff live-vs-mirror because no mirror exists. Low severity (config is stable, saves are backed up), but it is a real repo-side coverage gap for a 24/7 service. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker inspect palworld --format ...compose.project.working_dir'
/opt/stacks/palworld  (config_files: /opt/stacks/palworld/compose.yaml)
$ ssh rig 'git -C /opt/stacks/palworld rev-parse --is-inside-work-tree'
NOT_A_GIT_REPO
$ grep -rni palworld foss-setup/configs/host/rig/  -> only doc mentions (idle-power-baseline.md, nas-mounts/README.md); no compose/env mirror
```

</details>

### UL205. Root cause of the 9 restarts: intermittent UE engine SIGSEGV (Signal 11) + MallocBinned2 heap-corruption fatal; auto-recovers via unless-stopped (KNOWN, monitored) `known-issue`
**Host:** rig · **Component:** palworld · **Auditor:** svc:palworld · **Work item:** `fix-103`

RestartCount=9 is CUMULATIVE over the container's 37-day life (created 2026-07-16), NOT a live crash loop. Container has been stable ~6d since StartedAt 2026-08-17T22:25:41Z (ExitCode=0, OOMKilled=false, policy unless-stopped). Not palworld-OOM (OOMKilled=false), not a host reboot (rig up 20d, booted 08-03), not an update loop (startup log shows a clean single steamcmd update+launch). The log carries 22x 'Signal 11 caught' / 'Engine crash handling finished; re-raising signal 11' plus one 'LowLevelFatalError MallocBinned2.cpp:1428 / FMallocBinned2 Attempt to realloc an unrecognized block ... canary==0x0!=0xb7' (heap corruption). Crash-report timestamps span 07-23,07-24,07-29,08-01,08-06,08-08,08-11,08-16,08-17. The crash at 20260817,182534 (Aug 17 18:25:34 EDT) matches the last container restart (StartedAt 18:25:41 EDT) — and coincides with a system-wide OOM at 18:18:03 EDT whose victim was the UNSLOTH container (pid 1902547 UID 1001), not palworld, so rig memory pressure at that moment likely tipped the crash. This is a KNOWN operator-tracked pattern: rig-host-stability.yaml:99 documents 'Palworld (engine SIGSEGV x2/4d) auto-recover via docker unless-stopped'; escalation check rig-crash-storm-quiet (fix-64) currently PASS (NO_CRASH_STORM max24h=0). NOT fixed / NOT restarted per read-only mandate — reporting only.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker inspect palworld --format ...'
State=running RestartCount=9 StartedAt=2026-08-17T22:25:41Z FinishedAt=2026-08-17T22:25:39Z ExitCode=0 OOMKilled=false Created=2026-07-16T16:52:22Z policy=unless-stopped; uptime 20 days boot 2026-08-03
$ docker logs palworld | grep -iE 'Signal 11|MallocBinned2|re-raising signal' | sort|uniq -c
 22 Engine crash handling finished; re-raising signal 11 for the default handler. Good bye.
 21 Signal 11 caught.
  1 LowLevelFatalError [File:.\Runtime/Core/Private/HAL/MallocBinned2.cpp] [Line: 1428]  FMallocBinned2 Attempt to realloc an unrecognized block ... canary == 0x0 != 0xb7
 crash ts ...20260817,182534:ERROR crash_report_exception_handler.cc
$ journalctl -k --since 2026-08-02 | grep -i oom-kill
Aug 17 18:18:03 cachyos kernel: oom-kill: ... task=unsloth,pid=1902547,uid=1001  (palworld NOT the victim)
$ audit results.json: rig-crash-storm-quiet -> pass NO_CRASH_STORM max24h=0
```

</details>

### UL206. Palworld public path: playit UDP register-error persists (known fix-34); LAN/REST path unaffected `known-issue`
**Host:** rig · **Component:** playit · **Auditor:** svc:palworld · **Work item:** `fix-103`

Palworld's public reachability (palworld.tabaska.us:1105 via playit dedicated IP 69.9.181.17) rides the playit tunnel. Morning audit shows game-playit-udp-register-errors FAIL 'REGISTER-ERRORS:1' — this is the pre-existing baseline failure fix-34. Palworld has no direct query protocol so it cannot be probed on the public UDP path (documented gaming.yaml:121); the sibling playit-java-public and playit-bedrock-public checks PASS and game-playit-bedrock-udp returns PONG, so the tunnel agent itself is up. The palworld LAN/direct path (UDP 8211 bound 0.0.0.0, REST 8212) is fully healthy per the live probe. Re-verified still holding today; no worsening observed. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ audit results.json:
game-playit-udp-register-errors -> fail | REGISTER-ERRORS:1
game-playit-bedrock-udp -> pass | PONG from 69.9.181.17
playit-java-public -> pass | Paper 26.1.2
playit-bedrock-public -> pass | Powered by AMP
$ docker inspect palworld ports -> 8211/udp 0.0.0.0, 8212/tcp 0.0.0.0, 25575/tcp 127.0.0.1
```

</details>

### UL207. KNOWN fix-34: playit UDP-claim register error recurred (REGISTER-ERRORS:1 in 24h) — re-verified, stable/not worsened, consumer path self-heals `known-issue`
**Host:** rig · **Component:** playit UDP-claim register errors (check game-playit-udp-register-errors) · **Auditor:** svc:playit · **Work item:** `fix-103`

The warn check game-playit-udp-register-errors (task_id fix-34) fails REGISTER-ERRORS:1 in the 22:23 audit run, matching this morning's failure baseline. RE-VERIFIED per lane notes: the 'got unexpected response from register request ... UdpChannelDetails' class recurs at a LOW, STABLE rate — per-UTC-day since 2026-08-02: Aug04=4, then 1-2/day (Aug05..Aug23), last 24h=1. NOT silently worsened (peak was Aug04=4; it has trended DOWN to ~1/day). Consumer impact = none: the agent self-recovers via retry before the 10-min playit-udp-guard probe catches it, so RestartCount=0 (guard has never had to restart the agent) and every guard run reports 'tunnel healthy'. By design this warn check fails on ANY recurrence ('surfaces that the class recurred at all'), so it is effectively permanently-red while the upstream class exists — that is the fix-34 residual, not a new regression. NOT fixed per read-only mandate. known_issue: fix-34.

<details><summary>Evidence</summary>

```
ssh mini python3 (results.json): 'playit agent logged no UDP-claim register errors in 24h (M30 class)' | fail | rig | msg: REGISTER-ERRORS:1
---
ssh rig 'docker logs playit --since 2026-08-02T00:00:00 2>&1 | grep "unexpected response from register" | cut -c1-10 | sort | uniq -c'
 4 2026-08-04 / 1 08-05 / 1 08-06 / 1 08-07 / 2 08-09 / 1 08-12 / 2 08-13 / 1 08-15 / 2 08-16 / 1 08-18 / 1 08-21 / 1 08-22 / 1 08-23
last 24h count=1
---
ssh rig 'docker inspect playit --format {{.RestartCount}}' -> 0
```

</details>

### UL208. playit UDP register-error recurs ~1/day (fix-34) — re-verified, self-healed, consumer unaffected `known-issue`
**Host:** rig · **Component:** playit agent (UDP channel register) · **Auditor:** flow:game-servers · **Work item:** `fix-103`

playit logged 1 'unexpected response from register request' in the last 24h at 2026-08-23T10:14:15Z (also 2026-08-21T11:23:11Z and 2026-08-22T05:14:00Z — a ~1/day cadence). This is the pre-existing fix-34 / M30 residual (baseline game-playit-udp-register-errors FAILs by design when count>0; today's count=1 = NOT worsened vs the morning baseline). The self-heal is working: playit-udp-guard.timer is active+enabled and last ran 2026-08-23 17:04:31 EDT (status=0/SUCCESS). Consumer impact is NIL right now — the Bedrock UDP RakNet ping (69.9.181.17:1111) succeeds live and BedrockConnect answers. NOT fixed per read-only mandate; classify as known reopen-candidate under fix-34.

<details><summary>Evidence</summary>

```
ssh rig "docker logs --timestamps --since 24h playit | grep 'unexpected response from register'"
2026-08-23T10:14:15Z ... ERROR ... got unexpected response from register request ... UdpChannelDetails(tunnel_addr: 69.9.181.2:5512 ...)
(prior) 2026-08-21T11:23:11Z, 2026-08-22T05:14:00Z
ssh rig: playit-udp-guard.timer timer_active=active timer_enabled=enabled; service last Deactivated successfully 2026-08-23 17:04:31 EDT status=0/SUCCESS
```

</details>

### UL209. playit UDP register-error class recurred once in 24h — known fix-34 residual at stable baseline rate, zero tunnel impact `known-issue`
**Host:** rig · **Component:** playit agent (UDP tunnels) · **Auditor:** triage:game-playit-udp-register-errors · **Work item:** `fix-103`

game-playit-udp-register-errors (warn, task fix-34) failed with REGISTER-ERRORS:1. The single error landed 2026-08-22T05:14:00Z (= 01:14 EDT; rig clock verified identical to mini, both 22:25:46 EDT — no RTC skew). The error is the documented benign M30 class: an 'unexpected response from register request' whose payload is an out-of-band UdpChannelDetails response (mismatched request id; the log line embeds an ephemeral playit channel token — redacted from evidence). Rate re-verified against the full retained container log (since 2026-07-16): 26 occurrences in ~37 days (~0.7/day, nearly all singletons; peak 4/day on Aug 4; Aug 21 also had 1) — tonight's 1 is exactly the baseline, NOT worsened. The fix-34 progress ledger itself records 'playit throws UDP-claim register errors ~daily' with playit-udp-guard as the shipped mitigation. The guard probe at 01:14:32 EDT (31s after the error) reported the tunnel healthy — no self-heal restart was needed. NOT fixed per read-only mandate; nothing to fix — this warn check is the intended recurrence tripwire for the class.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker logs --since 24h playit 2>&1 | grep -ac "unexpected response from register"'
1
$ ssh rig 'docker logs --since 24h playit 2>&1 | grep -a "unexpected response from register" | tail -1'
2026-08-22T05:14:00.411537Z ERROR playit_agent_core::agent_control::connected_control: got unexpected response from register request other=Response(ControlRpcMessage { request_id: 1, content: UdpChannelDetails(UdpChannelDetails { tunnel_addr: 69.9.181.2:5512, token: "[REDACTED]" }) })
$ ssh rig 'docker logs playit 2>&1 | grep -a "unexpected response from register" | grep -aoE "[0-9]{4}-...Z"' # full-log rate
26 total since 2026-07-16 (log start); last 5: 2026-08-15T23:12Z, 2026-08-16T03:48Z, 2026-08-16T22:23Z, 2026-08-18T13:45Z, 2026-08-21T11:23Z, 2026-08-22T05:14Z (~0.7/day, stable)
$ ssh rig 'journalctl -u playit-udp-guard.service --since "2026-08-22 00:50" --until "2026-08-22 02:00" --no-pager | grep healthy | head -3'
Aug 22 01:04:25 cachyos playit-udp-guard.sh[2126280]: tunnel healthy: bedrock.tabaska.us:1111 answered through playit
Aug 22 01:14:32 cachyos playit-udp-guard.sh[2133620]: tunnel healthy: bedrock.tabaska.us:1111 answered through playit
Aug 22 01:24:40 cachyos playit-udp-guard.sh[2140994]: tunnel healthy: bedrock.tabaska.us:1111 answered through playit
```

</details>

### UL210. Minor doc drift: compose comment cites vault path 'playit.secret_key' but the actual key is 'playit_gg.secret_key'
**Host:** rig · **Component:** playit compose secret-vault reference · **Auditor:** svc:playit · **Work item:** `fix-84`

The playit compose.yaml comment (both live and repo mirror) states the SECRET_KEY is 'also vaulted as playit.secret_key', but the vault has no top-level 'playit' section — the secret lives at 'playit_gg.secret_key'. The secret IS present live (/opt/stacks/playit/.env has SECRET_KEY) and IS recoverable (restic covers /opt/stacks/playit + the real vault key exists), so there is no functional exposure — this is a stale reference that could misdirect a restore. NOT fixed per read-only mandate. Cosmetic anti-drift nit only.

<details><summary>Evidence</summary>

```
compose comment: '# .env (not committed): SECRET_KEY ... also vaulted as playit.secret_key.'
python3 vault walk: top-level 'playit' key present: False ; KEYPATH: /playit_gg -> dict ['secret_key'] ; KEYPATH: /healthchecks/playit_udp_rig_ping_url
ssh rig 'grep -c SECRET_KEY /opt/stacks/playit/.env' -> 1
```

</details>

### UL211. Old transient exit-1 failures on record (playit-udp-guard 08-05 x3, immich-ml-window@on 08-12 x1) — recovered, no recurrence `known-issue`
**Host:** rig · **Component:** playit-udp-guard.service + immich-ml-window@on.service · **Auditor:** svc:rig-host-timers · **Work item:** `fix-103`

Journal sweep since 2026-08-02 (checklist 2). Two units logged non-zero exits earlier this month, both fully recovered with no repeat: playit-udp-guard.service failed exit-code status=1 three times on Aug 05 (18:25, 18:34, 18:45) — it has run clean every ~10min since and last exited 0 today 15:44:19. immich-ml-window@on.service failed exit-code status=1 once on Aug 12 01:00:24 — clean since, last exit 0 today 01:00:08; this class is documented known-normal (day-window VRAM contention / llama-swap yield). NOT the same as the open fix-34 finding, which is about the playit AGENT container's UDP-claim register errors ('playit agent logged no UDP-claim register errors in 24h' = fail in today's baseline) — the udp-guard TIMER that watches/restarts the agent is itself healthy. No retry-storms (>1000 lines), no NUL-corrupted log reads, no auth rot in any of the 14 units. NOT fixed per read-only mandate; nothing to fix (self-recovered).

<details><summary>Evidence</summary>

```
journalctl --since 2026-08-02 | grep 'Failed with result|Main process exited' (our units) ->
'Aug 05 18:25:36 / 18:34:20 / 18:45:57 playit-udp-guard.service: Main process exited, code=exited, status=1/FAILURE'
'Aug 12 01:00:24 immich-ml-window@on.service: Main process exited, code=exited, status=1/FAILURE'
(no export-manifests / nvidia-cdi / deadman / watchdog / restic / ansible-pull failures in range)
latest playit-udp-guard exit 0 @ 2026-08-23 15:44:19 ; latest immich-ml-window@on exit 0 @ 2026-08-23 01:00:08
```

</details>

### UL212. comfyui-stack state is not in the rig restic backup set (models deliberately excluded; connection DBs outside backup but seed-script-regenerable)
**Host:** rig · **Component:** restic backup coverage (/opt/comfyui, marinara/lumiverse conn DBs) · **Auditor:** svc:comfyui-stack · **Work item:** `fix-93`

rig BACKUP_PATHS (/etc/restic/env) = '/etc /home/btabaska /opt/stacks/palworld/... /opt/stacks/amp/... /opt/stacks/playit' + docker volumes docker_litellm_pgdata + docker_open_webui_data. /opt/comfyui (164G, of which 146G is models) is NOT in the set. Excluding the 146G of models is INTENTIONAL and correct (excludes.txt policy: 'LLM model weights ... re-downloadable ... NO'; memory confirms models are re-downloadable). The gap worth noting: the ~18G of non-model comfyui state (custom nodes, user workflows, output images) and the marinara/lumiverse connection-state SQLite DBs are also outside the backup — but the connection DBs are regenerable via seed-marinara-connections.sh / seed-lumiverse-connections.sh (rig ai-tooling repo) and the curated MCP workflows live in git (docker/comfyui-mcp/workflows). So real data-loss exposure on disk-loss = hand-generated output images + manual workflow tweaks not in git, which is acceptable for an NSFW image-gen scratch box. OWUI + LiteLLM state (image-engine config) IS backed up. Consistent with the deliberate lean Tier-1 design; no dedicated open task for comfyui backup.

<details><summary>Evidence</summary>

```
$ ssh rig 'sudo grep -E "^export (BACKUP_PATHS|RESTIC_EXCLUDE_FILE)=" /etc/restic/env'
export BACKUP_PATHS="/etc /home/btabaska /opt/stacks/palworld/game/Pal/Saved /opt/stacks/palworld/game/backups /opt/stacks/amp/config/.ampdata/instances /opt/stacks/playit /var/lib/docker/volumes/docker_litellm_pgdata /var/lib/docker/volumes/docker_open_webui_data"
export RESTIC_EXCLUDE_FILE="/etc/restic/excludes.txt"

$ ssh rig 'sudo du -sh /opt/comfyui /opt/comfyui/models'
164G  /opt/comfyui
146G  /opt/comfyui/models

excludes.txt: 'Keep it LEAN Tier-1: worlds, saves and configs YES; re-downloadable game binaries, server jars, LLM model weights and media NO.'  (no comfyui/models line -> /opt/comfyui simply not in BACKUP_PATHS)
```

</details>

### UL213. Three rig host units have no verification check — the monitors' own health is unmonitored `known-issue`
**Host:** rig · **Component:** rig host timers (pcie-aer-monitor.timer, snapper-cleanup.timer, nvidia-cdi-refresh.service) · **Auditor:** meta:coverage-diff · **Work item:** `fix-101`

Non-container audit surface gap. `pcie-aer-monitor.timer` (watches GPU PCIe AER errors) has no check confirming it is armed/fresh — if the monitor dies silently, GPU-bus errors go unalerted; the outcome is only PARTIALLY covered by rig-crash-storm-quiet (generic journal-noise scan, fix-64). `snapper-cleanup.timer` (btrfs snapshot pruning) has no check — silent failure = snapshot accumulation / disk fill. `nvidia-cdi-refresh.service` has zero coverage anywhere; it maps to open task fix-81 (nvidia-cdi reboot survival). All three verified enabled/active in systemctl on rig 2026-08-23. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh rig systemctl list-timers: pcie-aer-monitor.timer (last 15:27), snapper-cleanup.timer (last 14:38) — both active
grep -rli 'pcie-aer-monitor' checks.d -> NONE; 'snapper' -> NONE; 'nvidia-cdi'/'cdi-refresh' -> NONE across all 41 yaml
```

</details>

### UL214. Catalog notes credit only the mini agent as feeding the Beszel hub; rig (and nas) agents also feed it
**Host:** rig · **Component:** service-catalog · **Auditor:** svc:beszel-agent-rig · **Work item:** `fix-102`

service-catalog.yaml has one beszel row (the hub: host mini, port 8090, url https://status.tabaska.us) with notes 'Host/container metrics hub (beszel-agent on mini feeds it; agent has no UI).' The hub actually ingests from three agents (mini, nas, rig — all up in the systems table), so the note undersells the fleet coverage. The rig agent itself has no UI and rig config is doc-only, so it does not warrant its own catalog row — this is a documentation-precision nit, not a functional gap. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
service-catalog.yaml:554-560 name: beszel / host: mini / port: 8090 / url: https://status.tabaska.us / notes: 'Host/container metrics hub (beszel-agent on mini feeds it; agent has no UI).'
hub systems table: mini|up, nas|up, rig|up (all three agents reporting)
```

</details>

### UL215. Catalog documents only the original 3 image models; live ComfyUI now serves a larger deliberate NSFW model set
**Host:** rig · **Component:** service-catalog.yaml comfyui entry (line 437) · **Auditor:** svc:comfyui-stack · **Work item:** `fix-102`

service-catalog.yaml line 437 says ComfyUI serves '3 image models — Z-Image Turbo / NoobAI-XL / Flux.2 Klein'. All 3 documented models ARE still present, so the rig-comfyui check correctly passes — but the live model set has grown substantially with deliberate operator additions (pornmasterAnime, ltx2310eros, pornmasterKrea2, cyberrealistic-nsfw-zimage, moody-real/moody-wild zimage variants) tracked in memory (pornmaster-comfyui-models, local-ltx23-video). This is minor documentation drift (understatement), not a functional issue. Also note the comfyui container runs the floating tag mmartial/comfyui-nvidia-docker:latest rather than a digest pin (running comfyui_version 0.28.0) — deliberate per memory 'native 0.28 nodes (don't bump image)', so reproducibility rests on the last-pulled image + the pinned ai-tooling repo, not the tag. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
catalog line 437: 'serving 3 image models — Z-Image Turbo / NoobAI-XL / Flux.2 Klein'

$ ssh rig 'curl -s http://localhost:8188/object_info/CheckpointLoaderSimple'
['NoobAI-XL-v1.1.safetensors','ltx2310eros_v14.safetensors','pornmasterAnime_ilV5.safetensors']
$ ssh rig 'curl -s http://localhost:8188/object_info/UNETLoader'
['cyberrealistic-nsfw-zimage-turbo.safetensors','moody-real-zimage-turbo.safetensors','moody-wild-nsfw-zimage-base.safetensors','pornmasterKrea2_v2Turbo_fp8.safetensors','z_image_turbo_bf16.safetensors']

$ ssh rig 'docker ps' -> comfyui  Up 6 days  mmartial/comfyui-nvidia-docker:latest
```

</details>

### UL216. Port 27036 = Steam client Remote Play listener, running since the 08-16 MoonDeckBuddy re-enable session — expected gaming infra, never codified in any baseline `known-issue`
**Host:** rig · **Component:** steam / lan-listener baseline (fix-51) · **Auditor:** triage:lan-listeners-drift-rig · **Work item:** `fix-98`

ss -tlnp attributes 0.0.0.0:27036 to process 'steam' pid 667715, user btabaska, started Sun Aug 16 14:00:43 EDT — 4 minutes after commit 0e2ff0d ('MoonDeckBuddy re-enabled', 08-16 13:56) and 12 minutes after MoonDeckBuddy itself, i.e. part of the same operator game-streaming session. 27036 is the standard Steam Remote Play discovery/streaming port the Steam client opens automatically; the Steam client is required on the rig for the MoonDeck streaming path (Buddy launches Steam games), so the listener is expected operator state, not rogue. It appears nowhere in the repo except progress.json's lai-21 note, which already triaged it as 'Steam 27036/59999, pre-existing, NOT-lai-21'. First flagged 08-17 (first daily run after the processes started). Operator decision needed: bless 27036 in rig.ports (repo + deployed) with a comment, or disable Remote Play in Steam settings (MoonDeck uses Moonlight/Apollo, not Steam Remote Play, so 27036 is incidental). NOT fixed per read-only mandate. Covered by the fix-51 reopen-candidate mapping in today's baseline.

<details><summary>Evidence</summary>

```
$ ssh rig 'ss -tlnp | grep :27036'
LISTEN 0 128 0.0.0.0:27036 0.0.0.0:*  users:(("steam",pid=667715,fd=140))

$ ssh rig 'ps -o pid,lstart,user,cmd -p 667715'
667715 Sun Aug 16 14:00:43 2026 btabaska /home/btabaska/.local/share/Steam/ubuntu12_32/steam -srt-logger-opened

mini triage history: triage-2026-08-17.md 'Two new TCP listeners on rig (ports 27036 and 59999)…' (first appearance; 08-06 drift was 5000/8880, since baselined)

progress.json lai-21: 'lan-listeners-drift-rig (Steam 27036/59999, pre-existing)'
```

</details>

### UL217. 27036 all-interface listener is the Steam client Remote Play/In-Home Streaming discovery port — legitimate gaming session, not yet blessed in baseline `known-issue`
**Host:** rig · **Component:** steam client (Remote Play) / fix-51 baseline · **Auditor:** triage:lan-listeners-drift-rig · **Work item:** `fix-98`

Port 27036 binds 0.0.0.0 and is owned by the Steam client (pid 667715, user btabaska, /home/btabaska/.local/share/Steam/ubuntu12_32/steam), running 7d01h (started ~2026-08-16). This is Steam's Remote Play / In-Home Streaming CM-discovery TCP port — expected gaming infrastructure on a rig that already baselines Apollo/Sunshine game-streaming (47984-48010). It is a benign user-session listener, NOT a rogue/nc-class listener (contrast SM56). It is unauthenticated on the flat LAN, same accepted-risk posture as the other rig endpoints (trusted VLAN, pending ha-19 IoT segmentation). Because it is session-bound (disappears when Steam closes) the additive-only drift script will not flap on its removal. Remediation (NOT applied, read-only): add '27036 # steam — Remote Play/In-Home Streaming discovery' to rig.ports and re-deploy. Covered by the open fix-51 baseline.

<details><summary>Evidence</summary>

```
$ ssh rig 'ss -tlnp | grep -E ":27036\b"'
LISTEN 0 128 0.0.0.0:27036 0.0.0.0:* users:(("steam",pid=667715,fd=140))

$ ssh rig 'ps -o pid,comm,etime,args -p 667715'
 667715 steam 7-01:17:03 /home/btabaska/.local/share/Steam/ubuntu12_32/steam -srt-logger-opened
```

</details>

### UL218. fix-78 backlog re-verified: 15 library series with 0 downloaded chapters (was 16 — not worsened) `known-issue`
**Host:** rig · **Component:** suwayomi · **Auditor:** svc:suwayomi · **Work item:** `fix-78`

Of 19 library series, 15 have downloadCount=0 despite having chapters listed from source (e.g. Berserk 403 listed/0 downloaded, Welcome to Demon School! Iruma-kun 552/0, No Guard Wife 181/0). The download queue is STOPPED and empty, and lastFetchedAt for all backlog series is 2026-07-25..07-28 (no library update/fetch has run since late July, so despite AUTO_DOWNLOAD_CHAPTERS=true nothing has been auto-grabbed). This is the fix-78 manga-backfill backlog. Re-verified per lane instruction: count is 15 now vs the fix-78 baseline of 16 — slightly IMPROVED, NOT worsened, so no escalation. The 4 remaining series ARE fully downloaded (281 chapters) and reach Komga, proving the pipeline itself works; the backlog is undownloaded content, not a broken chain. known_issue: fix-78 (open).

<details><summary>Evidence</summary>

```
$ curl ...4567/api/graphql -d '{mangas(condition:{inLibrary:true}){nodes{title downloadCount chapters{totalCount} lastFetchedAt}}}'
total_in_library=19  series_with_0_downloaded=15  series_with_0_chapters_listed=0
total_downloaded_chapters=281  total_chapters_listed=2056
  0dl chapters=403 lastFetch=2026-07-28 | Berserk
  0dl chapters=552 lastFetch=2026-07-26 | Welcome to Demon School! Iruma-kun
  0dl chapters=181 lastFetch=2026-07-26 | No Guard Wife
  ... (15 total)
$ curl ...4567/api/graphql -d '{downloadStatus{state queue{...}}}'
{"data":{"downloadStatus":{"state":"STOPPED","queue":[]}}}
```

</details>

### UL219. rig 8210 (unsloth-studio) is repo-blessed but the deployed /opt/verification baseline is stale — drift check FAILs spuriously on 8210 `known-issue`
**Host:** rig · **Component:** verification deploy-sync / rig.ports baseline (fix-51 / verify-06-adjacent) · **Auditor:** cross:lan-exposure · **Work item:** `fix-97`

8210 is a legitimate service: docker container unsloth-studio (Up 5 days) publishing 0.0.0.0:8210->8000/tcp, added to the REPO baseline foss-setup/verification/assets/expected-listeners/rig.ports on 2026-08-17. But the copy deployed on the mini runner at /opt/verification/assets/expected-listeners/rig.ports still has 27 ports and lacks 8210, so listener-drift.sh flags 8210 as drift every day. This is a repo->deployed sync gap (taxonomy #9 config-edited-never-reloaded), isolated to rig 8210 only — mini.ports and nas.ports are byte-identical repo-vs-deployed. Remediation = scp the current repo rig.ports to /opt/verification/assets/expected-listeners/ (per verification-deploy-quirk: root-owned dir needs ssh sudo tee, and scp fails silently). This is the known 'deployed-baseline-stale' item called out in the lane brief; folds under fix-51. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker ps --format "{{.Names}}\t{{.Ports}}\t{{.Status}}" | grep 8210'
unsloth-studio  22/tcp, 8888/tcp, 0.0.0.0:8210->8000/tcp, [::]:8210->8000/tcp  Up 5 days

$ diff <(repo rig.ports ports)  <(ssh mini deployed rig.ports ports)
14d13
< 8210        # present in repo baseline, absent in deployed
# mini.ports & nas.ports diffs: IDENTICAL
```

</details>

### UL220. Known-failing check re-verified: 1 playit UDP-claim register error in last 24h (fix-34 residual, not worsened) `known-issue`
**Host:** rig · **Component:** verification/checks.d/gaming.yaml: game-playit-udp-register-errors · **Auditor:** meta:gaming · **Work item:** `fix-103`

This check is in today's 10:29 EDT failure baseline mapped to fix-34. Re-verified live this evening: exactly 1 'unexpected response from register' line in the playit agent's last 24h of logs — the M30 class recurred once, matching the historical ~daily UDP-claim breakage the check was built to surface. Not silently worsened (single occurrence, not a retry storm), and the consumer end is covered by the separate game-playit-bedrock-udp RakNet probe (crit, not in today's failure list, so the public Bedrock join path recovered — consistent with the on-rig playit-udp-guard.timer 10-min self-heal described in the file header). Check design remains justified as an intermediate class guard: Palworld's UDP tunnel has no query protocol to probe directly. known_issue: fix-34.

<details><summary>Evidence</summary>

```
ssh rig 'n=$(docker logs --since 24h playit 2>&1 | grep -ac "unexpected response from register"); echo "register-errors=$n"'
register-errors=1
```

</details>

### UL221. agent-memory-plugin MEMORY.md leg is a one-time-success latch — a dead write path after the first successful write is invisible forever
**Host:** rig · **Component:** verification/checks.d/local-ai.yaml:agent-memory-plugin · **Auditor:** meta:local-ai · **Work item:** `fix-100`

The check (lines 603-622) validates plugin presence, structural wiring, TS syntax, and that at least one well-formed dated '## ... (idle|compacting)' section exists in the newest memory-dir MEMORY.md. The last leg proves the write path ran end-to-end ONCE ever; there is no freshness assert, so if the session.idle/compacting hooks silently stop firing (opencode upgrade changing the plugin API, summarizer LiteLLM key rot), the check stays green indefinitely on the historical artifact. Freshness is viable here: opencode-run-probe drives a real opencode session on the rig daily at 07:15, so asserting the newest dated section (or file mtime) is within ~7-14 days would not flap. The GPU-safety rationale for making no model call remains sound — this is about the artifact-age assert only, not probe depth of the summarizer. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/local-ai.yaml lines 613-617:
      f=$(ls -t "$D"/*.md 2>/dev/null | head -1);
      if [ -z "$f" ]; then echo MEM_NO_FILE; exit 0; fi;
      sec=$(grep -cE "^## .*\((idle|compacting)\)$" "$f" ...);
      bul=$(grep -cE "^- " "$f" ...);
(no mtime/date-recency test anywhere in the cmd)
ssh rig ls -la ~/.config/opencode/plugins/memory.ts -> -rw-r--r-- 8923 Aug 6 15:43 (plugin present); check passed 2026-08-22 10:29 run
```

</details>

### UL222. Launch-chain assertion incomplete: cores asserted but the retroarch binary that loads them is not
**Host:** rig · **Component:** verification/checks.d/retro-emulation.yaml:18 (rig-esde-romm-library) · **Auditor:** meta:retro-emulation · **Work item:** `fix-100`

The check's name claims 'has all launch cores', and it asserts the six *_libretro.so files — but ES-DE launches ROMs via `retroarch -L <core>.so <rom>`, and the check never asserts the retroarch binary itself (nor any ES-DE-side config beyond `command -v es-de`). If retroarch were removed/broken (e.g. a CachyOS package removal or a rolling-release update failure) while the .so files remained, every system would be un-launchable yet the check stays green — exactly the failure mode the header says it guards against. Currently benign: /usr/bin/retroarch verified present live, so this is a probe-depth completeness gap, not a live failure. Cheap fix when next touching the file: add `command -v retroarch` beside the es-de existence test. NOT fixed per read-only mandate. Not covered by any open task.

<details><summary>Evidence</summary>

```
checks.d/retro-emulation.yaml cmd asserts only: command -v es-de; ls ~/ROMs/nes; [ -e /usr/lib/libretro/${core}_libretro.so ] for 6 cores; per-platform counts — no retroarch assertion.
ssh rig 'command -v retroarch || echo NO-RETROARCH-BINARY' → /usr/bin/retroarch (present today)
```

</details>

### UL223. rig-ml-window-catchup-clean passes vacuously if immich-ml-window@.service is ever renamed or removed
**Host:** rig · **Component:** verification/checks.d/rig-host-stability.yaml:rig-ml-window-catchup-clean · **Auditor:** meta:rig-host-stability · **Work item:** `fix-100`

The cmd is `systemctl is-failed immich-ml-window@on.service` with only the literal 'failed' treated as red. Verified live on rig that a nonexistent unit also reports 'inactive' (rc=4) — indistinguishable from the healthy state the check accepts (state=inactive). If the unit template is renamed/retired without updating this check, it goes permanently green. Today it is NOT vacuous: the template exists (`immich-ml-window@.service static`, verified live) and is-failed returns 'inactive'. Hardening suggestion for a future session (NOT fixed per read-only mandate): additionally assert the template exists, e.g. `systemctl list-unit-files 'immich-ml-window@*' --no-legend | grep -q .`. Companion behavioral coverage (container OFF by day) lives in rig-immich-ml.yaml (nas-32), which softens but does not eliminate the gap — that check watches the container, not this unit.

<details><summary>Evidence</summary>

```
$ ssh rig 'systemctl is-failed immich-ml-window@on.service; systemctl list-unit-files "immich-ml-window@*" --no-legend'
inactive
immich-ml-window@.service static -
$ ssh rig 'systemctl is-failed no-such-unit-xyz@on.service; echo rc=$?'
inactive
rc=4   # deleted unit == healthy unit as far as this check can see
```

</details>

### UL224. 30/32 rig checks reference a nonexistent runbook path wiki/runbooks/rig.md
**Host:** rig · **Component:** verification/checks.d/rig.yaml — runbook field (30 of 32 checks) · **Auditor:** meta:rig · **Work item:** `fix-99`

There is no wiki/runbooks/ directory anywhere in the repo (0 md files under that path). The real rig runbooks live under wiki/docs/runbooks/ — rig-host-stability.md, rig-btrfs-readonly-recovery.md, wake-the-rig.md — and there is NO rig.md at either wiki/runbooks/ or wiki/docs/runbooks/. The 2 fix-20 checks correctly use wiki/docs/runbooks/rig-btrfs-readonly-recovery.md (exists). So every alert from the other 30 rig checks points the operator at a missing runbook. This is a fleet-wide convention defect (wiki/runbooks/docker.md, nas.md, dns.md, backups.md are all similarly dead — only verification.md/alerting.md happen to have a docs/runbooks/ twin); gen-checks-pages.py does not render per-check runbook as a wiki link, so the impact is limited to alert-payload metadata, hence low. NOT fixed per read-only mandate. known_issue: not tracked by any open task.

<details><summary>Evidence</summary>

```
find . -path '*/wiki/runbooks/*' -name '*.md' | wc -l -> 0
ls wiki/runbooks/rig.md -> No such file or directory ; ls wiki/docs/runbooks/rig.md -> No such file or directory
ls wiki/docs/runbooks/ | grep -i rig -> rig-btrfs-readonly-recovery.md, rig-host-stability.md, wake-the-rig.md
grep 'runbook:' rig.yaml | sort | uniq -c -> 30 wiki/runbooks/rig.md ; 2 wiki/docs/runbooks/rig-btrfs-readonly-recovery.md
```

</details>

### UL225. Checks whose own comments call a failure an 'incident' are severity:warn, not crit
**Host:** rig · **Component:** verification/checks.d/rig.yaml — rig-ollama/rig-litellm/rig-open-webui/rig-ai-e2e · **Auditor:** meta:rig · **Work item:** `fix-100` · *skeptic-confirmed*

The file header and the inline trailing comments on rig-ollama (L25), rig-litellm (L35), rig-open-webui (L45), and rig-ai-e2e (L502) all read 'rig is 24/7 — failure here is an incident', yet all four are severity:warn. Only rig-suspend-masked and rig-root-fs-writable are crit (30 warn / 2 crit total). If crit pages and warn is ntfy-only in this fleet's alert tiering, then the very checks the file labels 'incident' will not page. May be an intentional choice (warn still alerts), so filing low with medium confidence — the internal inconsistency (comment says incident, severity says warn) is real; the notification impact is unverified. NOT changed per read-only mandate.

*Verify note:* Independently re-verified every literal claim against rig.yaml. The four named checks all carry the exact "rig is 24/7 — failure here is an incident" comment while being severity:warn; only rig-suspend-masked and rig-root-fs-writable are crit; tally is exactly 30 warn / 2 crit. Config inconsistency is real. Finding is honestly self-hedged (low, medium-confidence, notification impact unverified) so no downgrade warranted. Could not refute — facts hold exactly.

<details><summary>Evidence</summary>

```
grep 'severity:' rig.yaml | sort | uniq -c -> 30 warn, 2 crit
Inline comments L25/L35/L45/L502: 'rig is 24/7 — failure here is an incident' on severity:warn checks
```

</details>

### UL226. Stale check: expect regex demands https://comfyui.tabaska.us but conns correctly use comfyui-arbiter:8189 (ai-01) `known-issue`
**Host:** rig · **Component:** verification/checks.d/rig.yaml (rig-marinara-connections, rig-lumiverse-connections) · **Auditor:** triage:rig-marinara-connections · **Work item:** `fix-100`

HARNESS-BUG / KNOWN-STALE (task ai-01; flagged in lane baseline as reopen candidate and in the marinara-lumiverse-wiring memory as 'conn checks known-stale'). The check's expect regex (authored 2026-07-18, comment says conns 'still point at the public gateways') asserts image connections point at https://comfyui.tabaska.us. Since then the wiring was intentionally changed so all image conns use the internal docker alias http://comfyui-arbiter:8189 (memory: 'image conns MUST use comfyui-arbiter:8189 alias'). Every OTHER token the regex requires is present live; the ONLY failing lookahead in BOTH checks is the comfyui URL. This is therefore a stale check expectation, not broken connections. Marinara fail-streak = 284 (in confirmed set); lumiverse = 12; both failed in yesterday's daily results.json too — long-standing and unchanged, NOT worsened. NOT fixed per read-only mandate: remediation is a repo-side edit to the two expect regexes (swap the comfyui.tabaska.us assertion for comfyui-arbiter:8189), which also requires re-running gen-checks-pages.py in the same commit and scp of the yaml to /opt/verification/checks.d/. Verdict on the mission question: STALE CHECK (harness finding), the conns are healthy.

<details><summary>Evidence</summary>

```
$ ssh rig 'curl -s -m8 http://cachyos.tailb31641.ts.net:3002/api/connections' | python3 (names|provider|baseUrl):
 Anime Image | image_generation | http://comfyui-arbiter:8189 | NoobAI-XL-v1.1.safetensors
 Realistic Image (Z-Image Turbo) | image_generation | http://comfyui-arbiter:8189
 Realistic NSFW (CyberRealistic) | image_generation | http://comfyui-arbiter:8189
 Realistic Image (Flux.2 Klein) | image_generation | http://comfyui-arbiter:8189
 LiteLLM Creative | openai | https://llm.tabaska.us/v1 | goetia
 OpenRouter Free | openrouter | https://openrouter.ai/api/v1
---
lumiverse DB read: llm=LiteLLM Creative|https://llm.tabaska.us/v1|key1 ; img=Anime Image (NoobAI-XL)|http://comfyui-arbiter:8189;Realistic Image (Z-Image Turbo)|http://comfyui-arbiter:8189;Realistic Image (Flux.2 Klein)|http://comfyui-arbiter:8189;Realistic NSFW (CyberRealistic)|http://comfyui-arbiter:8189
---
check expect (rig.yaml:161): (?s)(?=.*LiteLLM Creative)(?=.*https://llm\.tabaska\.us/v1)(?=.*Anime Image)(?=.*Z-Image Turbo)(?=.*Flux\.2 Klein)(?=.*https://comfyui\.tabaska\.us)  <-- last lookahead is the only unmatched one
check expect (rig.yaml:181): ...(?=.*NoobAI-XL\)\|https://comfyui\.tabaska\.us)...  <-- same stale URL
---
streak file: rig-marinara-connections = 284 (in 'confirmed'); rig-lumiverse-connections = 12; yesterday /var/lib/verification/results.json both = fail
```

</details>

### UL227. Two ai-01 conn checks fail on a STALE assertion — expect old comfyui.tabaska.us URL vs the correct comfyui-arbiter:8189 alias (consumer state is correct) `known-issue`
**Host:** rig · **Component:** verification/checks.d/rig.yaml (rig-marinara-connections, rig-lumiverse-connections) · **Auditor:** flow:ai-image-gen · **Work item:** `fix-100`

Both connection checks were RED in the 2026-08-22 daily run, and I confirmed the failure is entirely a stale check assertion, NOT a broken connection. rig-marinara-connections regex requires (?=.*https://comfyui\.tabaska\.us) and rig-lumiverse-connections regex requires the literal 'NoobAI-XL)|https://comfyui.tabaska.us'. But the connections were correctly migrated to the take-turns GPU-arbiter alias http://comfyui-arbiter:8189 (the intended architecture per memory 'image conns MUST use comfyui-arbiter:8189 alias'), so the lookaheads for the old comfyui.tabaska.us URL never match and the checks fail. The check NAMES also say '3 ComfyUI image conns' while live has 4 (a CyberRealistic/Flux.2 conn was added). Live connections are present, complete, point to the arbiter, and reference models that all exist (see green finding) — so the consumer feature is CORRECT and the CHECKS are stale. This is the KNOWN-STALE ai-01 conn-check issue (lane-context + memory marinara/lumiverse conn checks known-stale). Maps to reopen candidate ai-01. Fix = update both regexes to expect comfyui-arbiter:8189 (or comfyui\.tabaska\.us OR comfyui-arbiter) and the 4-connection set. NOT fixed per read-only mandate; reported for the fix queue.

<details><summary>Evidence</summary>

```
$ grep -A6 'id: rig-marinara-connections' foss-setup/verification/checks.d/rig.yaml
    name: "marinara in-app connections present (LiteLLM Creative + 3 ComfyUI image conns)"
    expect: '(?s)(?=.*LiteLLM Creative)(?=.*https://llm\.tabaska\.us/v1)(?=.*Anime Image)(?=.*Z-Image Turbo)(?=.*Flux\.2 Klein)(?=.*https://comfyui\.tabaska\.us)'
    task_id: ai-01
$ grep -A6 'id: rig-lumiverse-connections' foss-setup/verification/checks.d/rig.yaml
    name: "lumiverse in-app connections present (LLM row w/ key + 3 ComfyUI image conns)"
    expect: '(?s)...(?=.*NoobAI-XL\)\|https://comfyui\.tabaska\.us)(?=.*Z-Image Turbo)(?=.*Flux\.2 Klein)'

LIVE (both frontends): every ComfyUI conn baseUrl = http://comfyui-arbiter:8189 (NOT comfyui.tabaska.us) -> lookahead fails -> check reports fail while feature is correct. Live count = 4 ComfyUI conns, not 3.
results.json: rig-marinara-connections status=fail, rig-lumiverse-connections status=fail (both exit_code 0, assertion-only fail).
```

</details>

### UL228. ollama-shim rationale cites retired Obsidian consumers; shim still carries orphaned tag:fast + nomic-embed-text
**Host:** rig · **Component:** verification/checks.d/rig.yaml — rig-ollama (L17) + rig-ollama-models (L50) · **Auditor:** meta:rig · **Work item:** `fix-100` · *skeptic-confirmed*

Comments (L13-16, L47-49) justify the :11434 shim as serving HA Assist (llama3.2:3b), Obsidian AI Tagger (tag:fast), and Obsidian Smart Connections (nomic-embed-text). Obsidian was DROPPED 2026-08-17 (Memos is sole notetaking, lai-24) and is on the audit's retired/do-not-probe list. The check's actual assertion (expect llama3.2:3b) is still valid for HA Assist so there is no functional break, but the shim retains two models purely for a retired consumer and the check rationale is stale doc. Recommend confirming HA Assist still rides llama3.2:3b, then pruning tag:fast/nomic-embed-text and refreshing the comments. NOT fixed per read-only mandate. known_issue: not directly tracked.

*Verify note:* All three claims reproduced by fresh independent probes, no refutation angle survives. (1) rig.yaml L13-16 verbatim attributes tag:fast to "Obsidian AI Tagger" and nomic-embed-text to "Obsidian Smart Connections"; L18 name = "HA Assist + Obsidian compat" — same stale rationale also in Caddyfile:273 and wiki/architecture/local-ai-build.md:42. Obsidian was retired 2026-08-17 (lane-context retired/do-not-probe list confirms), so the comments are genuinely stale, not operator-intent. (2) Fresh /api/tags (HTTP 200) shows all 3 models still resident (nomic-embed-text, tag:fast, llama3.2:3b; modified 2026-07-16, never re-touched). (3) Truly orphaned — the one refutable angle: no rig container env references nomic/:11434, and the only repo references to the two models are the shim's own Obsidian-attributed docs (a prior operator finding even notes nomic-embed-text was superseded by Qwen3-Embedding-0.6B). Check assertion (expect llama3.2:3b) still valid — model resident, HA Assist consumer intact. No functional break, so low severity is correct and unchanged. No RTC skew: mini and rig clocks matched exactly (both Sun Aug 23 09:52:30 PM UTC 2026) at probe time.

<details><summary>Evidence</summary>

```
rig curl :11434/api/tags -> llama3.2:3b, nomic-embed-text:latest, tag:fast (all 3 still resident)
MEMORY/Trilium note: 'Obsidian dropped too -> Memos sole notetaking (lai-24)'; audit context retired list includes Obsidian
```

</details>

### UL229. rig syncthing user-service has no coverage-manifest entry (manifests track containers only)
**Host:** rig · **Component:** verification/coverage · **Auditor:** svc:syncthing-rig · **Work item:** `fix-101` · *skeptic-confirmed*

Per mandate 2 (100% monitoring coverage manifest), 'syncthing' is listed in coverage/mini.containers and coverage/nas.containers (both run it as a Docker container) but NOT in coverage/rig.containers, and there is no coverage/rig.services analog for user systemd services (only seedbox has a *.services manifest). The rig node is therefore invisible to the manifest-parity checks even though it is a real always-on mesh node. Effective monitoring is still strong (4 passing consumer checks above), so this is a structural manifest gap, not a live outage. NOT fixed per read-only mandate. No open task tracks this.

*Verify note:* Fresh probe upholds every claim. syncthing in mini/nas .containers, absent from rig.containers; coverage dir has only 4 files, seedbox alone has a *.services manifest. Independently confirmed rig runs syncthing as an ACTIVE user systemd service (not a container), so containers-manifest-rig parity structurally can't see it and no rig.services manifest exists. Low is correct: consumer checks (syncthing-hub-mesh-direct) still monitor the node; this is a manifest structural gap, not an outage.

<details><summary>Evidence</summary>

```
$ grep -rin syncthing foss-setup/verification/coverage/ ->
  nas.containers:30:syncthing
  mini.containers:43:syncthing
$ ls foss-setup/verification/coverage/ -> mini.containers nas.containers rig.containers seedbox.services
$ grep -in sync foss-setup/verification/coverage/rig.containers -> (no match)
```

</details>

### UL230. stale check `known-issue`
**Host:** rig · **Component:** verification/rig-lumiverse-connections · **Auditor:** triage:rig-lumiverse-connections · **Work item:** `fix-100`

expect regex asserts old comfyui.tabaska.us URL; live is comfyui-arbiter:8189

<details><summary>Evidence</summary>

```
live img all 4 = http://comfyui-arbiter:8189
```

</details>

### UL231. No freshness assertion in the check pair — zero-throughput ludusavi leaves both checks green while saves silently freeze (taxonomy pattern 13)
**Host:** rig + nas · **Component:** verification/checks.d/game-saves.yaml · **Auditor:** meta:game-saves · **Work item:** `fix-100`

The pair covers timer-death (check 2) and replication completeness (check 1), but neither asserts recency. Failure scenario the pair cannot see: ludusavi exits 0 while backing up nothing new (game-root/manifest config rot, or games moved), so ludusavi-backup.service Result stays 'success', the timer stays active, and the hub reports 100% in-sync — of permanently stale files. Additionally, systemctl show -p Result returns the default 'success' for a service that has never run since the user session started, so a broken OnCalendar after a session restart would also pass. Live state today is healthy (backup ran 22:05:02 EDT, hub stateChanged 22:12:25 — replication propagated within minutes at a ~2h cadence; rig clock exactly matches mini, so no RTC-skew false signal), so this is a check-design gap, not an active failure. Cheap hardening: assert LastTriggerUSec within ~3h in check 2, or assert newest-file mtime in the game-saves folder. Filed low (not medium liveness-masquerade — the file header honestly frames check 2 as a mechanism guard and check 1 is genuinely consumer-grade). Not covered by any open task; game-12 is done.

<details><summary>Evidence</summary>

```
$ ssh rig 'systemctl --user is-active ludusavi-backup.timer; systemctl --user show ludusavi-backup.service -p Result --value; systemctl --user show ludusavi-backup.timer -p LastTriggerUSec -p NextElapseUSecRealtime; date'
active
success
LastTriggerUSec=Sat 2026-08-22 22:05:02 EDT
NextElapseUSecRealtime=Sun 2026-08-23 00:01:50 EDT
Sat Aug 22 10:15:37 PM EDT 2026
$ ssh mini date
Sat Aug 22 10:15:37 PM EDT 2026
# neither cmd in game-saves.yaml references any timestamp/mtime/LastTrigger — grep 'LastTrigger\|mtime\|stateChanged' game-saves.yaml → no matches in either cmd
```

</details>

### UL232. fix-25 deluge-preimport-stuck holds: 1 item stuck (TV, not music) — music queue clean `known-issue`
**Host:** seedbox · **Component:** Deluge (shared arr download client) · **Auditor:** flow:music · **Work item:** `fix-73`

Deluge is the shared download client for the whole arr fleet incl. Lidarr; noting for chain completeness. The fix-25 baseline check remains failing with 1 stuck pre-import item: '[sonarr] Animaniacs S01 1080p HMAX WEB-DL ... x264-D00oo00M' — a Sonarr/TV item, NOT a music grab. The Lidarr side of Deluge is clean (Lidarr queue=0; seedbox-arr-deluge-e2e test=200). So this known residual does not affect the music chain, but the shared client carries the stuck TV payload. NOT fixed (read-only).

<details><summary>Evidence</summary>

```
baseline deluge-preimport-stuck (seedbox) -> PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M
Lidarr /queue -> queue=0 ; seedbox-arr-deluge-e2e -> 200
```

</details>

### UL233. 1 deluge grab stuck pre-import: Animaniacs S01 (fix-25/73), unchanged `known-issue`
**Host:** seedbox · **Component:** Deluge pre-import (seedbox) · **Auditor:** flow:movies-tv · **Work item:** `fix-73`

Known fix-25/fix-73 stuck grab, re-verified live: exactly ONE torrent stuck in the pre-import state — '[sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M' — identical to tonight's 22:23 baseline. Not worsened (still 1, not growing). The rest of the deluge→NAS→import pipeline is flowing (arr-grabbed-not-imported GRABS_OK checked=53; radarr imported <1h ago). deluge-console info did not return the torrent's ratio/age in a light probe, so exact stall-age not re-quantified, but count is stable. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
[live 16:49 EDT] ssh seedbox ~/venvs/deluge/bin/python ~/scripts/deluge-preimport-stuck.py -> PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M
[22:23 run] deluge-preimport-stuck: identical single item
```

</details>

### UL234. Related stalled grab NOT caught by preimport-stuck: 'Teen Titans Go S06E32' at 0% for 231h in the 'sonarr' label (progress<99.9 -> below the check's threshold)
**Host:** seedbox · **Component:** deluge / sonarr download (Teen Titans Go) · **Auditor:** triage:deluge-preimport-stuck · **Work item:** `fix-73` · *skeptic-confirmed*

While enumerating pre-import-labeled torrents, found 'Teen Titans Go S06E32 Justice Leagues Next Top Talent Idol S' in label='sonarr', progress=0.0, state=Downloading, age 231.2h (~9.6d), tracker=empirehost.me. Because deluge-preimport-stuck only flags torrents at progress>=99.9 (by design — it guards the completed-but-unimported case), this dead 0%-progress grab is invisible to it, and it is still shown as status=downloading in the Sonarr queue (id 1531220303, seriesId 155) rather than being timed out as stalled. Teen Titans Go is also on the unmanaged 'Any' profile (same cartoon batch), reinforcing that the batch is producing multiple download-pipeline issues. This is a low-severity stalled-download observation adjacent to fix-25/fix-50; not clearly covered by an existing check on the pre-import path. NOT fixed per read-only mandate.

*Verify note:* Tried to refute; all three legs hold on fresh independent probe. (1) Check code line 39 `if progress<99.9: continue` — a 0% torrent is structurally invisible, by design. (2) Live deluge: the Teen Titans Go grab still at prog=0.0/Downloading, now aged 234.1h (up from 231.2h = genuinely dead, not slow), only sub-99.9% sonarr torrent. (3) Sonarr queue: exact id 1531220303 seriesId 155 status=downloading, and it is the ONLY queue item. Low severity apt: single dead cartoon-batch grab in a real coverage blind-spot. No downgrade.

<details><summary>Evidence</summary>

```
# deluge read-only status query:
age_h=231.2 label=sonarr prog=0.0 state=Downloading tracker=empirehost.me
  name=Teen Titans Go S06E32 Justice Leagues Next Top Talent Idol S
# Sonarr queue confirms still 'downloading' after ~9.6d:
QUEUE id=1531220303 seriesId=155 status=downloading trackedState=downloading title='Teen Titans Go S06E32...'
```

</details>

### UL235. deluge-preimport-stuck still failing (sonarr Animaniacs) — adjacent, does not touch the books chain `known-issue`
**Host:** seedbox · **Component:** deluge pre-import (fix-25 / fix-73) — media path, NOT shelfmark-mam · **Auditor:** flow:shelfmark-mam · **Work item:** `fix-73`

Re-verified from tonight's audit-safe run (results.json 2026-08-22 22:23): deluge-preimport-stuck=fail with 'PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL...'. This is the TV/*arr download-then-import path, a DIFFERENT chain from shelfmark-mam. The books equivalent (books-preimport-unimported, fix-57) is green (checked=0), so no shelfmark/books torrent is stuck. Covered by open tasks fix-25 (deluge-preimport-stuck) and fix-73 (deluge stuck grab). Included only to document that I verified it does not affect my chain; not fixed (read-only) and belongs to the media lane.

<details><summary>Evidence</summary>

```
results.json deluge-preimport-stuck: status=fail task=fix-25 out='PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M'
results.json books-preimport-unimported: status=pass task=fix-57 out='BOOKS_PREIMPORT_OK checked=0' (books path clean)
```

</details>

### UL236. STILL-OPEN-VALID + ITEM CHURNED: stuck grab is now 'Animaniacs S01' (not the filed 'Only Murders S02E05') `known-issue`
**Host:** seedbox · **Component:** deluge preimport / deluge-preimport-stuck (fix-73) · **Auditor:** cross:open-queue-reality · **Work item:** `fix-73`

The originally-filed stuck grab (Only Murders in the Building S02E05) has cleared, but a NEW item is now wedged in the deluge pre-import label: [sonarr] Animaniacs S01 1080p HMAX WEB-DL. Count stable at 1 (not numerically worsened). Almost certainly the media-09 re-grab for the corrupt-RAR Animaniacs — cross-links fix-73<->media-09. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh seedbox '~/venvs/deluge/bin/python ~/scripts/deluge-preimport-stuck.py' ->
'PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M'
(daily-run same item; task filed item = Only Murders S02E05)
```

</details>

### UL237. deluge-preimport-stuck FAIL — 1 completed sonarr grab >48h still in pre-import label (fix-25 residual, re-verified live) `known-issue`
**Host:** seedbox · **Component:** deluge preimport pipeline (sonarr) · **Auditor:** svc:seedbox-glue · **Work item:** `fix-73`

Re-verified fix-25 baseline residual live (not just from results.json). One torrent is 100% complete but has sat >48h in a pre-import Deluge label without sonarr importing/relabeling it: 'Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M'. Taxonomy-4 (grabbed-but-never-imported) at the source. Single item, warn-severity; the on-demand repair tool for this class is deluge-relabel-imported.py (run from a LAN workstation per README). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh seedbox '~/venvs/deluge/bin/python ~/scripts/deluge-preimport-stuck.py' -> PREIMPORT_STUCK 1: [sonarr] Animaniacs S01 1080p HMAX WEB-DL DD2 0 x264-D00oo00M
audit results.json: deluge-preimport-stuck = fail (same item)
checks.d/seedbox.yaml:123 expect ^PREIMPORT_OK task_id fix-25
```

</details>

### UL238. STILL-OPEN-VALID + now ACTIONABLE: zero readarr torrents remain on betty, but 'readarr' still in ARR_LABELS (repo + live) `known-issue`
**Host:** seedbox · **Component:** deluge-reaper ARR_LABELS (media-10) · **Auditor:** cross:open-queue-reality · **Work item:** `media-10`

The prerequisite is met — deluge on betty now shows zero readarr-labeled torrents (last one drained past the 14d reap). But the cleanup itself is undone: 'readarr' is still in ARR_LABELS in both the repo (configs/host/seedbox/deluge-reaper.py:20) and the live seedbox copy (~/scripts/deluge-reaper.py). The task action (remove 'readarr', update README, redeploy) is now safe and due. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh seedbox: readarr-labeled torrents query -> (empty)
repo deluge-reaper.py:20 ARR_LABELS = {...'readarr'...}
seedbox ~/scripts/deluge-reaper.py:20 still contains 'readarr'
```

</details>

### UL239. seedbox-extracted-reaped: 2 files >7d survive in ~/media/extracted despite daily reaper `known-issue`
**Host:** seedbox · **Component:** extracted-leftover reaper (cron 05:30) · **Auditor:** svc:host-seedbox · **Work item:** `fix-95`

Two files (Sex.Life.2021.S02E01 / S02E05, both mtime 2026-08-15, ~8d old) remain in ~/media/extracted although the 05:30 daily cron 'find media/extracted -type f -mtime +7 -delete' should have removed them this morning. Dramatically improved vs the original fix-45 problem (139G accumulated) — dir is now 14G with only 2 stragglers — so the reaper mostly works, but 2 files persisting past the boundary suggests either a silent cron failure (the find has NO error redirect → mail-only, taxonomy 6) or the extracted copies being re-created by an active seed. NOT fixed per read-only mandate. Covered by open task fix-45 (in today's baseline); not worsened.

<details><summary>Evidence</summary>

```
ssh seedbox 'find media/extracted -type f -mtime +7 | wc -l' => 2
find ... -printf: 2026-08-15 media/extracted/Sex.Life.2021.S02E01.HDR.2160p.WEB.h265-EDITH.mkv ; 2026-08-15 ...S02E05...
du -sh media/extracted => 14G
crontab: 30 5 * * * find /home/hd34/btabaska/media/extracted -type f -mtime +7 -delete; ...  (no stderr redirect)
mini audit: fail seedbox: no extracted leftovers older than 7d
```

</details>

### UL240. seedbox-extracted-reaped FAIL — 2 leftovers >7d (14G); recurring off-by-one -mtime +7 boundary race (fix-45 residual, benign/self-healing) `known-issue`
**Host:** seedbox · **Component:** extracted-reaper cron / seedbox-extracted-reaped check · **Auditor:** svc:seedbox-glue · **Work item:** `fix-95`

Re-verified fix-45 residual. Live: exactly 2 files remain in ~/media/extracted, both from Aug 15 (Sex.Life.2021.S02E01 6.5GB @16:01, S02E05 6.8GB @18:35), 14G total; these are the ENTIRE contents of the dir (find -type f = 2). Root cause is a design off-by-one: BOTH the 05:30 reap cron (`find ... -mtime +7 -delete`) AND the check (`find ... -mtime +7 | wc -l`, expect 0) use `-mtime +7`, which GNU find only matches at >=8 complete 24h periods. A file that crosses the 8-day mark AFTER 05:30 on a given day is not reaped until the NEXT 05:30, so the continuously-running check reports it as a leftover for up to ~24h. That is exactly the current state (files hit 8d ~Aug 23 16:01 seedbox time; cron will delete them Aug 24 05:30). NOT the 139G accumulation of original fix-45 — the reaper mechanism is healthy: audit-run saw 5 leftovers, the Aug 23 05:30 cron reaped 3 (>=8d) leaving these 2 (dir mtime Aug 23 05:30 confirms cron fired). NOT worsened. NOT fixed per read-only mandate. Durable fix = reap cron use -mtime +6 (or check -mtime +8) so no file lingers past the 7d the check enforces.

<details><summary>Evidence</summary>

```
$ ssh seedbox 'find ~/media/extracted -type f -mtime +7 | wc -l' -> 2
$ ssh seedbox 'ls -la ~/media/extracted/' -> drwxr-xr-x . Aug 23 05:30 (dir mtime=cron ran); -rw Aug 15 16:01 Sex.Life.2021.S02E01.HDR.2160p...mkv (6953258251); -rw Aug 15 18:35 ...S02E05...mkv (7322640732)
$ ssh seedbox 'du -sh ~/media/extracted' -> 14G
audit results.json: seedbox-extracted-reaped = fail, output: 5
crontab: 30 5 * * * find /home/hd34/btabaska/media/extracted -type f -mtime +7 -delete
checks.d/seedbox.yaml:160 cmd: find media/extracted -type f -mtime +7 | wc -l  expect ^0$
```

</details>

### UL241. seedbox-extracted-reaped still failing (5 stale files) — adjacent, does not touch the books chain `known-issue`
**Host:** seedbox · **Component:** media/extracted reaper (fix-45) — media path, NOT shelfmark-mam · **Auditor:** flow:shelfmark-mam · **Work item:** `fix-95`

Re-verified from tonight's audit-safe run: seedbox-extracted-reaped=fail, 5 files under media/extracted older than 7 days. This is the media extraction-reaper path, not the books/shelfmark copy path (shelfmark copies epubs seed-preserving straight from the rslave mount to /books; it never uses media/extracted). Covered by open task fix-45. Included to document non-impact on my chain; not fixed (read-only).

<details><summary>Evidence</summary>

```
results.json seedbox-extracted-reaped: status=fail task=fix-45 cmd='find media/extracted -type f -mtime +7 | wc -l' out='5'
```

</details>

### UL242. Leaked Deluge RPC probe process running ~21 days (stuck in reactor.run())
**Host:** seedbox · **Component:** orphaned process (our uid) · **Auditor:** svc:host-seedbox · **Work item:** `fix-95`

An orphaned one-off Deluge RPC query (bash heredoc → venv python, PID 3108605, elapsed 21-02:05:16 → started ~2026-08-02) has been hung in twisted reactor.run() for ~21 days on this shared host. Its on_status callback references an unquoted name t.get(progress,0) (should be 'progress'), which raises inside the callback so client.disconnect()/reactor.stop() are never reached — the reactor never exits and the process holds an open RPC connection to deluged:3254 indefinitely. This IS one of our processes (uid btabaska), but it is a leaked probe from a prior agent session, not part of the service. Resource impact is small (0.0% CPU, ~41MB RSS) but it is an orphan/connection leak. NOT killed per read-only mandate — REPORT only. Not covered by any open task.

<details><summary>Evidence</summary>

```
ps -u btabaska: 3108604 bash 21-02:05:16 ; 3108605 python 21-02:05:16
cat /proc/3108604/cmdline: /bin/bash -c ~/venvs/deluge/bin/python - <<PYEOF ... if 'adrift' in name.lower() or 'konkoly' ... print(f"[{lab}] {t.get(progress,0):.0f}% ...") ... client.connect("127.0.0.1",3254) ... reactor.run()
cat /proc/3108605/cwd -> /home/hd34/btabaska
```

</details>

### UL243. DRIFT: deluge-relabel-imported.py in repo mirror but absent from live ~/scripts
**Host:** seedbox · **Component:** repo mirror vs live (configs/host/seedbox) · **Auditor:** svc:host-seedbox · **Work item:** `fix-95`

The repo mirror foss-setup/configs/host/seedbox/deluge-relabel-imported.py (md5 09ebb1c3...) has no counterpart on the box — it is not in ~/scripts and 'find ~ -name deluge-relabel-imported.py' returns nothing, and it is not referenced by crontab. The other 4 scripts (reaper, preimport-stuck, payload-audit, bookshelf-preimport) match the repo md5-for-md5, and the ~/.startup/deluge launcher matches the repo exactly (incl. the fix-69 -L error flag). Relabeling to *-imported labels IS still happening (label.conf mtime today 21:55; reaper log operates over *-imported labels), evidently now via the arr apps' Post-Import Category rather than this helper. Anti-drift: repo carries a script not deployed live — either dead repo cruft to prune or a mechanism that was removed live without updating the repo. Not covered by an open task.

<details><summary>Evidence</summary>

```
ssh seedbox 'md5sum ~/scripts/*.py' => 4 files, NO deluge-relabel-imported.py; 'find ~ -maxdepth 3 -name deluge-relabel-imported.py' => (empty)
repo md5sum: 09ebb1ce3516924333074b7fc7587ffd foss-setup/configs/host/seedbox/deluge-relabel-imported.py
ssh seedbox 'ls ~/.config/deluge': label.conf mtime 2026-08-23 21:55 (relabeling active)
launcher + other 4 scripts: md5 identical live vs repo
```

</details>

### UL244. fix-45 residual RE-VERIFIED, not worsened: extracted reaper alive, 2 leftovers in the -mtime +7 fencepost window (audit 5 -> live 2) `known-issue`
**Host:** seedbox · **Component:** seedbox-extracted-reaped (verification check, task fix-45) · **Auditor:** triage:seedbox-extracted-reaped · **Work item:** `fix-95`

Known residual documented in wiki/docs/runbooks/fleet-hygiene.md and in tonight's baseline (lane-context line 106: fix-45 -> seedbox-extracted-reaped). Check `find media/extracted -type f -mtime +7 | wc -l` expects ^0$; audit captured 5, live now returns 2 (stable x3). Root mechanism is a benign timing/fencepost race, NOT a dead reaper and NOT unreapable files: (1) the 05:30 extracted-reaper cron is present and byte-identical to the repo manifest (README/fleet-hygiene); (2) the `~/media/extracted` directory mtime is `Aug 23 05:30`, proving the reaper ran and deleted files TODAY. `find -mtime +7` matches floor(age/86400) > 7, i.e. age >= 8 days. The 2 survivors (Sex.Life.2021.S02E01 mtime Aug 15 16:01, S02E05 mtime Aug 15 18:35) were floor-age 7 days at the 05:30 pass (7.56d / 7.45d -> floor 7 -> correctly skipped) and had aged to floor 8 by check time (~8.2d -> flagged). At the next 05:30 pass (Aug 24) both cross floor 8 and get deleted -> self-healing. Because the reaper samples at 05:30 and the check samples later in the day, every extracted file necessarily gets a ~1-day window where the check flags it before the morning reaper's next pass reaps it; this window IS the entire residual. Total leftover ~14.3 GB (6.95GB + 7.32GB), clears tomorrow 05:30. Not worsened vs the audit (improved 5->2). NOT fixed per read-only mandate; no action required — the check is transiently-noisy-by-design (a durable fix, out of scope, would be to loosen the check to -mtime +8 or add a small grace so the reaper always leads the check).

<details><summary>Evidence</summary>

```
$ ssh seedbox 'date; find media/extracted -type f -mtime +7 | wc -l'
Sun Aug 23 09:31:32 PM CEST 2026
2   (re-run x3 -> 2,2,2)

$ find media/extracted -type f -mtime +7 -printf '%TY-%Tm-%Td %TH:%TM  %u:%g  %m  %10s  %p\n'
2026-08-15 18:35  btabaska:hd34  644  7322640732  media/extracted/Sex.Life.2021.S02E05.HDR.2160p.WEB.h265-EDITH.mkv
2026-08-15 16:01  btabaska:hd34  644  6953258251  media/extracted/Sex.Life.2021.S02E01.HDR.2160p.WEB.h265-EDITH.mkv

$ ls -la media/extracted   (only these 2 files exist; dir mtime = reaper's cron time)
drwxr-xr-x 2 btabaska hd34      12288 Aug 23 05:30 .
-rw-r--r-- 1 btabaska hd34 6953258251 Aug 15 16:01 Sex.Life.2021.S02E01.HDR.2160p.WEB.h265-EDITH.mkv
-rw-r--r-- 1 btabaska hd34 7322640732 Aug 15 18:35 Sex.Life.2021.S02E05.HDR.2160p.WEB.h265-EDITH.mkv

$ crontab -l   (extracted reaper line present, matches configs/host/seedbox/README.md manifest)
30 5 * * * find /home/hd34/btabaska/media/extracted -type f -mtime +7 -delete; find /home/hd34/btabaska/media/extracted -mindepth 1 -type d -empty -delete

Fencepost math (age = now - mtime, floor to days):
  05:30 Aug 23 reaper pass: S02E01 7.56d, S02E05 7.45d -> floor 7 -> NOT matched by +7 -> skipped
  21:31 Aug 23 check:       S02E01 8.23d, S02E05 8.12d -> floor 8 -> matched -> count 2
  05:30 Aug 24 reaper pass: both floor 8 -> matched -> DELETED (self-heal)
```

</details>

### UL245. Hygiene finds pass vacuously if their target directory disappears (green-when-watched-thing-gone)
**Host:** seedbox · **Component:** seedbox-extracted-reaped / seedbox-tmp-arr-junk (find vacuous-pass) · **Auditor:** meta:seedbox · **Work item:** `fix-100`

Both checks are `find <dir> ... 2>/dev/null | wc -l` with expect '^0$'. If the target directory is ever renamed/removed, find errors to stderr (suppressed), wc -l prints 0, and the check PASSES — masking the structural change rather than surfacing it (taxonomy #13). Verified both targets currently EXIST (~/media/extracted, ~/tmp) so the checks are meaningful right now, but the blind spot is real. A cheap hardening would assert the dir exists (e.g. `[ -d media/extracted ] || echo NO_DIR`). Low priority. Not fixed — read-only.

<details><summary>Evidence</summary>

```
cmd(9): find media/extracted -type f -mtime +7 2>/dev/null | wc -l   expect '^0$'
cmd(10): find tmp -maxdepth 1 \( -name '*_update' -o -name '*_backup' \) 2>/dev/null | wc -l   expect '^0$'
ssh seedbox: EXISTS:media/extracted  EXISTS:tmp  (both present now; if absent -> suppressed error, wc=0 -> vacuous PASS)
```

</details>

### UL246. Hardcoded 100G headroom threshold assumes quota -s always reports in G — latent unit-mixing bug
**Host:** seedbox · **Component:** seedbox-quota-headroom (quota -s unit fragility) · **Auditor:** meta:seedbox · **Work item:** `fix-100`

The cmd parses `quota -s` with awk (u=$2+0;s=$3+0;h=$4+0;hr=h-u) and compares hr>100, treating the literal 100 as gigabytes. `quota -s` (human-readable) picks a per-value unit, so the arithmetic and the 100 constant are only correct while every value lands in G. Verified live it currently works (space 1321G, soft 2862G, hard 2909G -> u=1321 s=2862 h=2909 hr=1588 -> QUOTA_OK). Should usage ever climb high enough that quota -s switches used/soft/hard to T units, hr would be ~1.x and hr>100 would read false -> premature QUOTA_LOW; that mis-fire is in the SAFE direction (false warning, never a missed alert), and u<s still holds cross-unit. Real latent fragility worth a durable-fix note; low priority because it currently passes and fails safe. Not fixed — read-only.

<details><summary>Evidence</summary>

```
ssh seedbox 'quota -s' ->
     Filesystem   space   quota   limit   grace   files ...
     /dev/sdal1   1321G   2862G   2909G           54482 ...
awk: u=1321 s=2862 h=2909 hr=1588 -> (u<s && hr>100) TRUE -> QUOTA_OK (all values in G; threshold semantics break only if quota -s switches to T)
```

</details>

### UL247. Catalog lists Deluge port 8112 — another tenant's port per the host doc (should be 5945) `known-issue`
**Host:** seedbox · **Component:** service-catalog.yaml · **Auditor:** svc:host-seedbox · **Work item:** `fix-102` · *skeptic-confirmed*

The service-catalog.yaml deluge row records port: 8112. Per wiki/docs/hosts/seedbox.md and the fix-21 lockdown, deluge-web binds 127.0.0.1:5945 and :8112 is ANOTHER tenant's Deluge on this shared box (it was the source of a former false-green Kuma monitor). The catalog port field is therefore stale/incorrect. Functionally harmless (the Homepage tile and Kuma use the deluge.tabaska.us vhost, both verified present, not the port), but it is inaccurate documentation. Covered by open task fix-68 (catalog-vhost-parity, in today's baseline).

*Verify note:* Fresh independent probe from the true vantage (live `ss -ltnp` on the seedbox itself, plus the deluge web.conf) reproduces the defect exactly. Our deluge-web binds 127.0.0.1:5945 and deluged 127.0.0.1:3254; the web config port is literally 5945. The catalog row (service-catalog.yaml:215) records port 8112. 0.0.0.0:8112 IS live on the box but bound by a process with no pid visible to our unprivileged SSH user = another tenant's Deluge on the shared host, matching seedbox.md L45-46. Severity low is correct and unchanged: the port field is not consumed by the fix-68 catalog-vhost-parity check (which keys on the vhost URL, verified in catalog-vhost-parity.py), so this is pure stale documentation, functionally harmless. known_issue=true / fix-68 attribution verified. No wrong-vantage, stale-cache, RTC, GPU-window, or operator-intent escape hatch applies.

<details><summary>Evidence</summary>

```
grep service-catalog.yaml: name: deluge / host: seedbox / port: 8112 / url: https://deluge.tabaska.us
wiki/docs/hosts/seedbox.md: 'deluge-web 5945 ... deluge.tabaska.us -> :5945 — it had been proxying :8112, which is another tenant's Deluge'
seedbox-loopback-binds check (pass): 3254/5945/5030 bound 127.0.0.1 only
```

</details>

### UL248. Catalog port field stale: deluge row says port 8112 but web listens on 5945 (RPC 3254)
**Host:** seedbox · **Component:** service-catalog.yaml deluge row · **Auditor:** svc:deluge · **Work item:** `fix-102`

Minor doc/catalog accuracy drift. The service-catalog deluge row records port: 8112 (the deluge-web upstream default), but the live web UI listens on 5945 (web.conf 'port':5945; Caddy reverse_proxy {$SEEDBOX_IP}:5945; homepage widget url http://100.119.134.94:5945) and the daemon RPC is on 3254 (core.conf 'daemon_port':3254). The url field (deluge.tabaska.us) is correct and serves 200, and the category (Media Automation) is fine. Adjacent to fix-68 (catalog-vhost-parity) but that check is about vhost coverage, not port accuracy — likely untracked. NOT edited (read-only mandate).

<details><summary>Evidence</summary>

```
service-catalog.yaml: - name: deluge / category: Media Automation / host: seedbox / port: 8112 / url: https://deluge.tabaska.us
core.conf: "daemon_port":3254 ; web.conf: "port": 5945 ; Caddyfile:509 reverse_proxy {$SEEDBOX_IP}:5945
```

</details>

### UL249. Downloads staging dir accumulating (69 album dirs + growing failed_imports) — downstream Soularr/reaper, not slskd core `known-issue`
**Host:** seedbox · **Component:** slskd-download-cleanup · **Auditor:** svc:slskd · **Work item:** `fix-95`

slskd downloads land in /home/hd34/btabaska/files/slskd. Observed 69 leftover album directories (mostly dated Jul 10, some Aug 11-21) plus a failed_imports/ subtree with recent entries (Beyoncé 2026-08-21 23:00, Rise Against 2026-08-21 22:43, Eminem 2026-08-15, Lana Del Rey 2026-08-13). This is Soularr's post-import cleanup / failed-import domain, NOT slskd's function (slskd's job — download the files — is working, files present on disk). Correlates with today's baseline fails: seedbox-extracted-reaped=fail(5) [fix-45] and nas-soularr-failed-imports-fresh [fix-40]. Re-verified still holding this evening. NOT fixed per read-only mandate; flagged so the slskd-adjacent accumulation is not lost, attributed to the correct owner.

<details><summary>Evidence</summary>

```
$ ssh seedbox 'ls /home/hd34/btabaska/files/slskd | wc -l' -> 69 dirs
$ find files/slskd/failed_imports -type f -printf '%TY-%Tm-%Td %TH:%TM %p\n' | sort -r | head
2026-08-21 23:00 .../Beyoncé - Countdown (2011)/... .flac
2026-08-21 22:43 .../Rise Against - Katy Bar the Door.../... .flac
# audit results.json: seedbox-extracted-reaped -> fail | 5
```

</details>

### UL250. seed-01 disable rationale LAPSED — seedbox SSH now reachable from the runner host; check should be revived
**Host:** seedbox · **Component:** verification/sys-seedbox-ssh (system.yaml) · **Auditor:** triage:skips · **Work item:** `fix-100`

sys-seedbox-ssh (system.yaml:65-73) ships enabled:false with rationale 'seedbox: SSH blocked by provider network ACL — no probe path from the LAN. Re-enable if/when an API or SSH route exists.' That rationale no longer holds. The check is host:local, so it executes on the verification runner host (mini) as User=btabaska (confirmed via `systemctl cat verification-fast.service` -> ExecStart=/opt/verification/bin/run-checks.sh, User=btabaska). Replicating that exact context — ssh to mini as btabaska, then the literal check cmd `ssh -o BatchMode=yes -o ConnectTimeout=8 seedbox 'echo seedbox-ok'` — returns `seedbox-ok` exit 0. The seedbox is reachable over its tailnet path (100.119.134.94 / betty.bysh.me) from mini now. So the check would PASS if enabled and currently provides ZERO liveness monitoring of the sole download client's host. Recommendation: flip enabled:true (severity is info in the check, so reviving simply restores coverage). NOT fixed per read-only mandate. Note: `sudo ssh seedbox` as root on mini failed with 'Host key verification failed' (root's known_hosts), but that is irrelevant — the runner runs as btabaska, whose path works.

<details><summary>Evidence</summary>

```
$ ssh mini whoami
btabaska
$ ssh mini "systemctl cat verification-fast.service | grep -E 'User=|ExecStart'"
User=btabaska
ExecStart=/opt/verification/bin/run-checks.sh --tier fast --notify
$ ssh mini "ssh -o BatchMode=yes -o ConnectTimeout=8 seedbox 'echo seedbox-ok'; echo exit:$?"
seedbox-ok
exit:0
# from the Mac too:
$ ssh -o BatchMode=yes -o ConnectTimeout=15 seedbox 'echo seedbox-ok; hostname'
seedbox-ok
betty.bysh.me
# checks.d rationale still claims it is blocked:
system.yaml:66  name: "seedbox reachable over SSH (disabled: SSH blocked by ACL)"
system.yaml:73  enabled: false   # SSH blocked by ACL — skip until a probe path exists
```

</details>

### UL251. Extracted leftovers >7d persist in ~/media/extracted (fix-45; partially reaped 5→2) `known-issue`
**Host:** seedbox · **Component:** ~/media/extracted reaper · **Auditor:** svc:deluge · **Work item:** `fix-95`

fix-45 residual (seedbox-extracted-reaped). Two extracted files older than 7d remain in ~/media/extracted; the 22:23 audit reported 5, so the reaper cleared 3 but the condition still holds. Tangential to deluge core but in seedbox scope. NOT cleaned (read-only mandate).

<details><summary>Evidence</summary>

```
seedbox$ find ~/media/extracted -maxdepth 1 -mtime +7 ->
/home/hd34/btabaska/media/extracted/Sex.Life.2021.S02E05.HDR.2160p.WEB.h265-EDITH.mkv
/home/hd34/btabaska/media/extracted/Sex.Life.2021.S02E01.HDR.2160p.WEB.h265-EDITH.mkv
audit fix-45 check status=fail msg=5
```

</details>

## INFO (571)

### UI1. UNPROBED: Steam Deck RetroDECK leg — deck SSH unreachable (SteamOS SSH disabled/off), human-boundary pass-by-design `known-issue`
**Host:** deck · **Component:** Steam Deck RetroDECK sync (manual human worker) · **Auditor:** flow:retro

### UI2. RetroDECK worker script has no repo mirror — lives only on the Deck (anti-drift gap)
**Host:** deck · **Component:** retrodeck-sync worker script (anti-drift) · **Auditor:** flow:retro · *skeptic-confirmed*

### UI3. Diun actively scanning on both hosts — image-update alerting alive
**Host:** fleet · **Component:** Diun image-update scanner (mini + NAS) · **Auditor:** flow:monitoring-alerting

### UI4. GREEN: no zero-coverage roster service and no untouched host surface — audit is service-complete
**Host:** fleet · **Component:** audit-coverage-completeness (roster diff + named-services + host-surfaces) · **Auditor:** completeness-critic

### UI5. GREEN: manifest + health + systemd tripwire verified end-to-end on mini/nas/seedbox; live==manifest, no undeclared deploys
**Host:** fleet · **Component:** coverage-manifest tripwire (green legs) · **Auditor:** cross:coverage-tripwire

### UI6. Coverage-tripwire cross-cut: 107 manifest entries across 4 surfaces reconciled against live reality — surface intact, 3 gap classes
**Host:** fleet · **Component:** coverage-manifests · **Auditor:** cross:coverage-tripwire

### UI7. GREEN: monitoring+alerting chain verified working end-to-end for the consumer
**Host:** fleet · **Component:** monitoring-alerting chain (ntfy / Healthchecks / Kuma / Beszel / Diun / off-mini dead-man) · **Auditor:** flow:monitoring-alerting

### UI8. GREEN: Assist conversation answers e2e via rig Ollama — closes the documented gap live
**Host:** ha · **Component:** HA Assist conversation agent -> rig Ollama (conversation.rig_ollama_assist) · **Auditor:** flow:home-assistant

### UI9. GREEN: 73 Hue light entities, availability within accepted baseline; API auth valid
**Host:** ha · **Component:** Hue integration + API auth + entity availability · **Auditor:** flow:home-assistant

### UI10. HA off-eMMC (NAS) backup leg verified fresh + ACL-protected end-to-end
**Host:** ha · **Component:** backup-leg · **Auditor:** svc:ha-integrations

### UI11. GREEN: HA consumer paths proven working end-to-end (frontend, REST, Assist LLM, presence, live state machine)
**Host:** ha · **Component:** ha-core · **Auditor:** svc:ha-core

### UI12. GREEN: off-eMMC (NAS) HA backup dead-man fresh <48h + ACL locked down
**Host:** ha · **Component:** ha-core/backup · **Auditor:** svc:ha-core

### UI13. DRIFT probe N/A by design: repo mirror is .example-only; live config on appliance
**Host:** ha · **Component:** ha-core/config-mirror · **Auditor:** svc:ha-core

### UI14. UNPROBED: RestartCount / StartedAt / host resource stats (supervisor endpoints 401, appliance not shellable)
**Host:** ha · **Component:** ha-core/telemetry · **Auditor:** svc:ha-core

### UI15. Disable still justified: HACS final leg (GitHub device-login) is inherently human and ha-04 remains open — but it has sat 25 days `known-issue`
**Host:** ha · **Component:** ha-hacs-loaded (enabled:false) · **Auditor:** meta:ha

### UI16. Verified working end to end: all thresholds/pins in ha.yaml re-validated against live state tonight
**Host:** ha · **Component:** ha.yaml live-baseline verification (GREEN) · **Auditor:** meta:ha

### UI17. Heads-up: update.terminal_ssh_update pending 3 days (10.3.0->10.4.0) — trips the 21-day guard ~2026-09-09 if the update round is not applied `known-issue`
**Host:** ha · **Component:** home-assistant updates (ha-updates-pending) · **Auditor:** triage:ha-updates-pending

### UI18. Home Assistant PROVEN working end-to-end (config, Assist LLM, proxy, presence)
**Host:** ha · **Component:** host-ha · **Auditor:** svc:host-ha

### UI19. Off-eMMC backup dead-man (crit) green — NAS backup < 48h
**Host:** ha · **Component:** host-ha · **Auditor:** svc:host-ha

### UI20. UNPROBED: HA core log sweep and host resource usage (SSH refused, REST endpoints unavailable)
**Host:** ha · **Component:** host-ha · **Auditor:** svc:host-ha

### UI21. Hue integration verified working end-to-end (66/73 lights live, IoT path open)
**Host:** ha · **Component:** hue · **Auditor:** svc:ha-integrations

### UI22. Monitoring + catalog coverage confirmed (consumer-grade checks, Homepage tile, catalog row); HA error_log clean
**Host:** ha · **Component:** monitoring-catalog · **Auditor:** svc:ha-integrations

### UI23. KNOWN (fix-36): HA updates pending >=21d re-verified STILL failing — core 26d, OS 22d, matter 25d (plus new terminal_ssh 4d) `known-issue`
**Host:** ha · **Component:** updates · **Auditor:** svc:ha-integrations

### UI24. ha-04 disable rationale HOLDS — HACS still not loaded (human GitHub device-login pending) `known-issue`
**Host:** ha · **Component:** verification/ha-hacs-loaded (ha.yaml) · **Auditor:** triage:skips

### UI25. GREEN: HA Assist conversation path verified live end-to-end
**Host:** ha+rig · **Component:** HA Assist -> rig ollama shim (:11434 llama3.2:3b) · **Auditor:** flow:ai-chat-serving

### UI26. VERIFIED WORKING E2E: phone→Immich→ML→smart search returns real semantic-ranked results via public vhost
**Host:** immich.tabaska.us (→mini→nas) · **Component:** immich smart-search / CLIP ML (immich-smart-search-consumer, nas-32) · **Auditor:** flow:photos-ml

### UI27. Reality-check totals: 25 open items probed, 3 fixed-but-open, 1 worsened, 17 still-valid, 5 not-built
**Host:** local · **Component:** open-queue/reality-check · **Auditor:** cross:open-queue-reality

### UI28. GREEN: Mac repo dirty set matches the known in-flight session WIP exactly — nothing extra `known-issue`
**Host:** mac · **Component:** Mac repo /Users/brandontabaska/GitHub/Home working tree · **Auditor:** triage:git-foss-setup-clean

### UI29. UNPROBED: interactive editor keystroke->completion leg (human/GUI); all prerequisites verified
**Host:** mac · **Component:** VSCodium GUI attach (rig-code Remote-SSH) -> in-editor completion · **Auditor:** flow:remote-ai-coding

### UI30. UNPROBED (by design, not a gap): a live opencode completion was not executed from the Mac shell
**Host:** mac · **Component:** opencode run (Mac shell) · **Auditor:** flow:opencode-memory

### UI31. Mac opencode.json fork divergence is limited to sanctioned Mac-only additions (no drift finding)
**Host:** mac · **Component:** opencode.json Mac fork · **Auditor:** flow:opencode-memory

### UI32. VERIFIED: opencode 1.18.10 + memory plugin + skills parity proven end-to-end across Mac and rig
**Host:** mac+rig · **Component:** opencode / DIY memory plugin / skills bundle · **Auditor:** flow:opencode-memory

### UI33. Two flagged "stale" dead-man checks re-verified as FALSE-STALE (weekly cadence / self-recovered) — root-caused
**Host:** mini · **Component:** Healthchecks dead-man (export-manifests-rig/-mini, tv-torrent-cleanup) · **Auditor:** flow:monitoring-alerting

### UI34. Homepage monitoring tiles error-free (href-only external tiles, by design)
**Host:** mini · **Component:** Homepage monitoring tiles (:3010/api/services) · **Auditor:** flow:monitoring-alerting

### UI35. UNPROBED: live MeTube->beets->Navidrome fresh-download leg not exercised; MeTube yt-dlp is stale
**Host:** mini · **Component:** MeTube (docker-02) — live download leg · **Auditor:** flow:youtube

### UI36. REGISTERED-NOT-BUILT (all 5): Memos->OWUI RAG lane + migrations + corpora + gamefaqs-semantic + memory-polish not implemented `known-issue`
**Host:** mini · **Component:** Memos-RAG lane (lai-23, lai-24, lai-25, lai-26, lai-27) · **Auditor:** cross:open-queue-reality

### UI37. GREEN: YouTube audio is present and playable in the Navidrome consumer (untagged)
**Host:** mini · **Component:** Navidrome (music-03 / fix-49) — YouTube-audio consumer end · **Auditor:** flow:youtube

### UI38. VERIFIED: OWUI tool budget 37/40, headroom 3 (within cap)
**Host:** mini · **Component:** OWUI MCP tool budget · **Auditor:** flow:ai-ops-agent

### UI39. STILL-OPEN-VALID (DEFERRED, known): mwoffliner still Cloudflare-403'd; blocked-mode scaffolding green as designed `known-issue`
**Host:** mini · **Component:** StrategyWiki ZIM / strategywiki-zim-present (lai-15) · **Auditor:** cross:open-queue-reality

### UI40. fix-79 down Kuma monitor NOT currently reproducing — status page clean, not worsened `known-issue`
**Host:** mini · **Component:** Uptime Kuma /status/fleet down monitor (fix-79) · **Auditor:** flow:monitoring-alerting

### UI41. FIXED-but-open: all Kuma monitors up (down=0) — recommend closing fix-79 `known-issue`
**Host:** mini · **Component:** Uptime-Kuma / alert-kuma-none-down (fix-79) · **Auditor:** cross:open-queue-reality

### UI42. GREEN: monitoring, catalog, and dashboard legs all present and consumer-grade
**Host:** mini · **Component:** adguard-home · **Auditor:** svc:adguard-home

### UI43. GREEN: primary DNS verified working end-to-end (resolution + live throughput)
**Host:** mini · **Component:** adguard-home · **Auditor:** svc:adguard-home

### UI44. Live-only config still true (AdGuardHome.yaml untracked) — documented risk, mitigated by nightly restic `known-issue`
**Host:** mini · **Component:** adguard-home · **Auditor:** svc:adguard-home

### UI45. Log sweep clean since 2026-08-02 — only benign client TCP resets and one unbound upstream timeout
**Host:** mini · **Component:** adguard-home · **Auditor:** svc:adguard-home

### UI46. GREEN: OWUI web-search chain proven end-to-end (fresh backend hops + passing consumer checks)
**Host:** mini · **Component:** ai-web-search chain (SearXNG -> OWUI web search -> reranker -> grounded answer) · **Auditor:** flow:ai-web-search

### UI47. fix-76 device-receipt is the human leg — server-side delivery + off-mini dead-man both proven `known-issue`
**Host:** mini · **Component:** alert delivery to physical device (fix-76) · **Auditor:** flow:monitoring-alerting

### UI48. Tonight's audit contributed ZERO to the failing counts; it deposited exactly 2 /tmp entries that age into the check ~2026-08-30
**Host:** mini · **Component:** audit self-accounting · **Auditor:** triage:mini-scratch-hygiene

### UI49. GREEN verified: backups fresh, bucket policy intact, new uploads auto-locking, ops key still least-privilege
**Host:** mini · **Component:** backups/restic+B2 siblings · **Auditor:** triage:b2-restic-immutable

### UI50. GREEN: BedrockConnect console-join path verified working end to end
**Host:** mini · **Component:** bedrock-connect · **Auditor:** svc:bedrock-connect

### UI51. GREEN: BedrockConnect console-join serverlist answers RakNet on mini:19132
**Host:** mini · **Component:** bedrock-connect · **Auditor:** flow:game-servers

### UI52. GREEN: Beszel hub + all 3 fleet agents verified working end to end (consumer probe)
**Host:** mini · **Component:** beszel · **Auditor:** svc:beszel

### UI53. GREEN: logs clean since 2026-08-02; no drift; restic backup leg covers beszel_data; monitoring + catalog rows all present
**Host:** mini · **Component:** beszel · **Auditor:** svc:beszel

### UI54. Observation: no Beszel monitor on the published Uptime-Kuma 'fleet' status page
**Host:** mini · **Component:** beszel · **Auditor:** svc:beszel

### UI55. GREEN: POT provider verified end-to-end — server/plugin versions match (1.3.1) in both consumers, outcome guard clean
**Host:** mini · **Component:** bgutil-pot · **Auditor:** svc:bgutil-pot

### UI56. GREEN: zero drift, catalog row correct, coverage manifest present, backup leg proven, stateless footprint
**Host:** mini · **Component:** bgutil-pot · **Auditor:** svc:bgutil-pot

### UI57. UNPROBED: fresh live POT generation not re-triggered
**Host:** mini · **Component:** bgutil-pot · **Auditor:** svc:bgutil-pot

### UI58. Unpinned :latest image is a latent server/plugin version-skew hazard on container recreation
**Host:** mini · **Component:** bgutil-pot · **Auditor:** svc:bgutil-pot · *skeptic-confirmed*

### UI59. VERIFIED e2e: BookLogr SPA->API cross-origin reading chain works for the consumer
**Host:** mini · **Component:** booklogr · **Auditor:** flow:reading-web

### UI60. UNPROBED: dedicated Uptime-Kuma monitor not separately verified
**Host:** mini · **Component:** booklogr (Uptime-Kuma) · **Auditor:** svc:booklogr

### UI61. BookLogr consumer chain verified working end to end (SPA->bundle->cross-origin API v1.11.1 + auth-gated /v1)
**Host:** mini · **Component:** booklogr (booklogr-web + booklogr-api) · **Auditor:** svc:booklogr

### UI62. VERIFIED WORKING E2E: form submit -> labeled Forgejo issue -> self-cleaned
**Host:** mini · **Component:** bug-intake (bug-01) household Report-a-Problem form · **Auditor:** flow:bug-intake-triage

### UI63. GREEN: every hardcoded baseline in the file re-verified live — form id, form field, Homepage tile, ntfy ACL string, buguser token, runner env vars, zero probe residue
**Host:** mini · **Component:** bug-intake baselines (live re-verification) · **Auditor:** meta:bug-intake

### UI64. UNPROBED (by design): actual notification PUSH not exercised — sentinel suppresses it to avoid buzzing the operator
**Host:** mini · **Component:** bug-intake notify DELIVERY (ntfy push / Discord push) · **Auditor:** flow:bug-intake-triage

### UI65. ntfy notify-leg credential valid + write ACL intact; Discord deliberately descoped (empty)
**Host:** mini · **Component:** bug-intake notify leg (fix-67) ntfy 'bugs' + Discord descope · **Auditor:** flow:bug-intake-triage

### UI66. Backup leg present: /opt/stacks/journaling swept into restic (B2), last run success — fix-22 immutability is the separate known CRIT `known-issue`
**Host:** mini · **Component:** bug-triage-evidence · **Auditor:** svc:bug-triage-evidence

### UI67. Structural read-only ceiling confirmed LIVE (docker.sock RW=false, cap_drop ALL, read-only rootfs, no-new-privileges)
**Host:** mini · **Component:** bug-triage-evidence · **Auditor:** svc:bug-triage-evidence

### UI68. VERIFIED end-to-end: read-only evidence sidecar serves real docker+HTTP evidence to n8n (consumer path live), e2e triage green
**Host:** mini · **Component:** bug-triage-evidence · **Auditor:** svc:bug-triage-evidence

### UI69. GREEN: 10/10 diverse vhost consumer probes pass with app-specific bodies (incl. cross-host proxies to NAS and rig)
**Host:** mini · **Component:** caddy · **Auditor:** svc:caddy

### UI70. GREEN: container stable, running config current vs on-disk (69==69 hosts), actively serving, zero drift live-vs-mirror
**Host:** mini · **Component:** caddy · **Auditor:** svc:caddy

### UI71. Observed in-flight WIP from concurrent session: principal-ai vhost added, already reloaded and serving, mirror in sync `known-issue`
**Host:** mini · **Component:** caddy · **Auditor:** svc:caddy

### UI72. Upstream 5xx passed through faithfully (not caddy defects): homepage 502 burst Aug 21 + Lidarr widget 500s Aug 22 — for homepage/lidarr lanes
**Host:** mini · **Component:** caddy · **Auditor:** svc:caddy

### UI73. Observed in-flight drift: principal-ai vhost is another session's uncommitted WIP (live since at least 08-18), not filed as a violation `known-issue`
**Host:** mini · **Component:** caddy / principal-ai vhost · **Auditor:** triage:catalog-vhost-parity

### UI74. GREEN: both flagged vhosts verified serving end-to-end through the Caddy edge; check output matches live state exactly (no harness bug) `known-issue`
**Host:** mini · **Component:** caddy edge / check harness · **Auditor:** triage:catalog-vhost-parity

### UI75. certbot.timer is vestigial (manages 0 certificates); no TLS cert-expiry check exists (probes use curl -k)
**Host:** mini · **Component:** certbot.timer / TLS certificate expiry · **Auditor:** meta:coverage-diff

### UI76. File summary: 9 checks (0 consumer / 4 intermediate / 5 liveness / 0 disabled) — honest blanket-liveness layer, integrity clean, 8/9 passing live
**Host:** mini · **Component:** checks.d/docker-fleet.yaml · **Auditor:** meta:docker-fleet

### UI77. File summary: 16 checks, 15 consumer-grade / 1 intermediate / 0 liveness / 0 disabled — structurally sound, deployed copy byte-identical
**Host:** mini · **Component:** checks.d/git-hygiene.yaml · **Auditor:** meta:git-hygiene

### UI78. File summary: 4 checks — 3 consumer-grade, 1 intermediate, 0 liveness-only, 0 disabled; integrity clean; mini+nas drift and booklogr posture verified green live
**Host:** mini · **Component:** checks.d/lan-exposure.yaml · **Auditor:** meta:lan-exposure

### UI79. File summary: 2 checks, 1 consumer-grade + 1 intermediate-by-design, 0 liveness, 0 disabled; integrity fully clean and both probes exercised live end-to-end
**Host:** mini · **Component:** checks.d/nas-io-storm.yaml · **Auditor:** meta:nas-io-storm

### UI80. File summary: 2 checks, 1 consumer-grade + 1 liveness closer-alive, 0 disabled — all integrity items pass
**Host:** mini · **Component:** checks.d/soularr-backlog.yaml (fix-56 SM29 dead-letter closer) · **Auditor:** meta:soularr-backlog

### UI81. Lane totals: 2 confirmed exposures + 4 known/parity gaps; 3 green legs
**Host:** mini · **Component:** cross:secrets-hygiene lane summary · **Auditor:** cross:secrets-hygiene

### UI82. diun-mini verified working end-to-end: daily scans + ntfy notification delivery proven
**Host:** mini · **Component:** diun · **Auditor:** svc:diun-mini

### UI83. Primary resolver chain works end to end with DNSSEC validation
**Host:** mini · **Component:** dns / AdGuard->Unbound recursion · **Auditor:** flow:edge-dns

### UI84. VERIFIED clean: no docker subnet overlaps a routable VLAN (fix-66 crit path) `known-issue`
**Host:** mini · **Component:** docker-networking · **Auditor:** triage:sys-docker-subnet-squat

### UI85. Dockge compose-UI verified working end to end (serves + auth enforced)
**Host:** mini · **Component:** dockge · **Auditor:** svc:dockge

### UI86. No config drift; catalog / coverage-manifest / homepage tile all correct
**Host:** mini · **Component:** dockge · **Auditor:** svc:dockge

### UI87. No errors/crash-loops in logs since 2026-08-02; idle-by-design (interactive UI)
**Host:** mini · **Component:** dockge · **Auditor:** svc:dockge

### UI88. State (/opt/stacks/dockge/data) is inside the restic B2 backup set `known-issue`
**Host:** mini · **Component:** dockge · **Auditor:** svc:dockge

### UI89. 13 sampled vhosts serve app-specific bodies; live config matches disk (no edited-but-never-reloaded)
**Host:** mini · **Component:** edge / Caddy reverse proxy · **Auditor:** flow:edge-dns

### UI90. No RFC1918 leak and no public exposure of internal vhosts (off-net NXDOMAIN)
**Host:** mini · **Component:** edge / public DNS hygiene · **Auditor:** flow:edge-dns

### UI91. FIXED-but-open: /etc etckeeper repo is now CLEAN — recommend closing fix-72 `known-issue`
**Host:** mini · **Component:** etckeeper / git-etckeeper-clean (fix-72) · **Auditor:** cross:open-queue-reality

### UI92. Verified alive end to end: weekly export-manifests pipeline healthy on mini AND rig — 'export dead' hypothesis debunked
**Host:** mini · **Component:** export-manifests.timer / healthchecks dead-man · **Auditor:** triage:manifest-image-purity

### UI93. Minor observation: speaches server runs at log_level=debug (verbose json-log, not a fault)
**Host:** mini · **Component:** faster-whisper · **Auditor:** svc:faster-whisper

### UI94. VERIFIED WORKING END TO END: STT transcription for journaling + OWUI voice proven at the consumer end
**Host:** mini · **Component:** faster-whisper · **Auditor:** svc:faster-whisper

### UI95. Backup + monitoring + catalog coverage all present and correct
**Host:** mini · **Component:** forgejo · **Auditor:** svc:forgejo

### UI96. Forgejo git control plane verified working end-to-end (consumer probe passed)
**Host:** mini · **Component:** forgejo · **Auditor:** svc:forgejo

### UI97. Push-freshness parity confirmed: Forgejo == GitHub == local at ab54803 (ai-03 mirror-lag class currently GREEN)
**Host:** mini · **Component:** forgejo · **Auditor:** svc:forgejo

### UI98. Green confirmation: frigate staged-never-deployed, absent from all hosts as expected
**Host:** mini · **Component:** frigate · **Auditor:** svc:frigate

### UI99. GREEN: /opt/stacks push hygiene intact aside from the known WIP — no unpushed commits, no stashes, no stray dirty files
**Host:** mini · **Component:** git-hygiene / /opt/stacks · **Auditor:** triage:git-stacks-clean

### UI100. In-flight concurrent session drift observed (Caddyfile + homepage services.yaml + untracked principal-ai site) — NOT filed as a violation `known-issue`
**Host:** mini · **Component:** git-stacks-clean (docker-12) / git-foss-setup-clean (glue-08) · **Auditor:** cross:docs-tracker-truth

### UI101. GREEN: HA API answers end-to-end THROUGH Caddy (taxonomy-10 proxy-path clear)
**Host:** mini · **Component:** ha.tabaska.us edge (Caddy reverse proxy -> HA :8123, trusted_proxies) · **Auditor:** flow:home-assistant

### UI102. Green confirmation: dead-man oracle verified working end to end — 16/16 checks up, zero down, ping ingestion live to the minute
**Host:** mini · **Component:** healthchecks · **Auditor:** svc:healthchecks

### UI103. Green confirmation: no drift, backup leg intact (nightly pg dump + restic), full monitoring/catalog coverage
**Host:** mini · **Component:** healthchecks · **Auditor:** svc:healthchecks

### UI104. Root-caused: the two 'stale-but-up' checks are weekly cron-kind checks, both in-window, both underlying jobs alive — false alarm
**Host:** mini · **Component:** healthchecks · **Auditor:** svc:healthchecks

### UI105. UNPROBED: ntfy notification delivery on an actual down flip `known-issue`
**Host:** mini · **Component:** healthchecks · **Auditor:** svc:healthchecks

### UI106. GREEN: container DNS wiring correct per homepage-widget-wiring memory (NAS .4 primary)
**Host:** mini · **Component:** homepage · **Auditor:** svc:homepage

### UI107. GREEN: container healthy, zero restarts, clean logs last 48h, trivial resource footprint
**Host:** mini · **Component:** homepage · **Auditor:** svc:homepage

### UI108. GREEN: dashboard verified end-to-end — 11 widget proxies return live upstream data, no dead tiles, edge vhost serves full JSON
**Host:** mini · **Component:** homepage · **Auditor:** svc:homepage

### UI109. GREEN: monitoring, backup, and catalog legs all present — consumer-grade checks included
**Host:** mini · **Component:** homepage · **Auditor:** svc:homepage

### UI110. Observed in-flight WIP drift (known): services.yaml + Caddyfile modified uncommitted on both live and repo mirror, in lockstep `known-issue`
**Host:** mini · **Component:** homepage · **Auditor:** svc:homepage

### UI111. UNPROBED: shared audit verification results file absent — direct probes substituted
**Host:** mini · **Component:** homepage · **Auditor:** svc:homepage

### UI112. Green: mini host foundation verified working end-to-end
**Host:** mini · **Component:** host-mini · **Auditor:** svc:host-mini

### UI113. In-flight WIP drift observed (Caddyfile + homepage services.yaml + principal-ai-engineer-track) `known-issue`
**Host:** mini · **Component:** host-mini · **Auditor:** svc:host-mini

### UI114. Observed in-flight session drift touching the Homepage monitoring surface `known-issue`
**Host:** mini · **Component:** in-flight session drift (observed, not filed) · **Auditor:** cross:coverage-tripwire

### UI115. CONFIRMED live: Memos native transcription (journal-08) and Memos MCP agent surface (journal-09) both green
**Host:** mini · **Component:** journal-08 / journal-09 Memos AI legs · **Auditor:** cross:docs-tracker-truth

### UI116. 4 transient Plex-connection tracebacks since Aug 2, each auto-recovered within ~2.5 minutes — no action needed
**Host:** mini · **Component:** kometa · **Auditor:** svc:kometa

### UI117. GREEN: fix-37/fix-67 auth-rot residual quantified at ZERO — no real HTTP 401/403 in any of the 10 retained daily logs `known-issue`
**Host:** mini · **Component:** kometa · **Auditor:** svc:kometa

### UI118. GREEN: kometa verified end-to-end — 19/19 daily runs finished, playlists/collections live in Plex with exact count match
**Host:** mini · **Component:** kometa · **Auditor:** svc:kometa

### UI119. UNPROBED: Uptime-Kuma monitor list (sqlite3 unavailable in container) — not applicable to headless kometa anyway
**Host:** mini · **Component:** kometa · **Auditor:** svc:kometa

### UI120. VERIFIED e2e: scheduled Kometa batch builds Plex collections/playlists with correct item counts (documented consumer-end gap CLOSED)
**Host:** mini · **Component:** kometa -> Plex (NAS) collections/playlists · **Auditor:** flow:kometa

### UI121. Re-quantified: IMDb-list 403 issue NOT present -- 6 lists processed clean, zero HTTP 401/403
**Host:** mini · **Component:** kometa IMDb-list fetch (fix-37/fix-67) · **Auditor:** flow:kometa

### UI122. CONFIRMED live: all 5 plant-id consumer probes green (bioclip genus, chat-vision, plant-scout preset, e2e, UI path)
**Host:** mini · **Component:** lai-22 plant/species ID (BioCLIP 2 + identify_plant + chat-vision) · **Auditor:** cross:docs-tracker-truth

### UI123. GREEN: mini all-interface listeners match baseline exactly (36/36), zero drift
**Host:** mini · **Component:** lan-exposure / listener-drift (fix-51) · **Auditor:** cross:lan-exposure

### UI124. GREEN: consumer request-layer verified end to end (login → request list → search)
**Host:** mini · **Component:** libreseerr · **Auditor:** svc:libreseerr

### UI125. GREEN: gunicorn WORKER TIMEOUT guard (fix-48) intact — zero timeouts and zero Caddy 5xx since 2026-08-02
**Host:** mini · **Component:** libreseerr · **Auditor:** svc:libreseerr

### UI126. GREEN: zero config drift, backup/monitoring/catalog all in place; homepage tile absence is deliberate
**Host:** mini · **Component:** libreseerr · **Auditor:** svc:libreseerr

### UI127. Observed in-flight WIP (not filed): new 'Principal AI Engineer Track' homepage tile in AI group `known-issue`
**Host:** mini · **Component:** litellm · **Auditor:** svc:litellm

### UI128. GREEN: mealie recipe stack healthy end-to-end (backend + Caddy proxy + SPA + DB-backed recipe)
**Host:** mini · **Component:** mealie · **Auditor:** svc:mealie

### UI129. UNPROBED: authenticated recipe-render path + Uptime-Kuma monitor presence
**Host:** mini · **Component:** mealie · **Auditor:** svc:mealie

### UI130. Zero-throughput / near-empty adoption: 1 recipe, 1 user, 0 meal plans, 0 shopping lists (frozen since 2026-07-22) — user-driven, NOT a defect
**Host:** mini · **Component:** mealie · **Auditor:** svc:mealie

### UI131. GREEN: no config drift, restic backup covers mealie (fresh 13h), catalog + homepage tile correct
**Host:** mini · **Component:** mealie / config + backup + catalog · **Auditor:** svc:mealie

### UI132. Verified working: all hardcoded thresholds/baselines re-checked live and accurate (navidrome 46/3525 missing, scan 13.5m fresh, unmapped exactly at 39/13)
**Host:** mini · **Component:** media-library-correctness baselines · **Auditor:** meta:media-library-correctness

### UI133. BACKUP leg confirmed: /opt/stacks/meme-review/data covered by restic (last run exit 0), WAL captured alongside DB
**Host:** mini · **Component:** meme-review · **Auditor:** svc:meme-review

### UI134. State precision: container fully removed (docker rm), not merely 'stopped/retained' as documented
**Host:** mini · **Component:** meme-review · **Auditor:** svc:meme-review

### UI135. VERIFIED: meme-review cleanly decommissioned-retained end to end (all markers consistent)
**Host:** mini · **Component:** meme-review · **Auditor:** svc:meme-review

### UI136. GREEN: memos journal->reflection loop proven end-to-end (consumer path)
**Host:** mini · **Component:** memos (journaling stack) · **Auditor:** svc:memos

### UI137. GREEN: restic-backed + consumer-grade monitoring + homepage tile
**Host:** mini · **Component:** memos backup + monitoring coverage · **Auditor:** svc:memos

### UI138. GREEN: compose live==repo, catalog row correct (no drift)
**Host:** mini · **Component:** memos config drift / catalog · **Auditor:** svc:memos

### UI139. GREEN: clean logs since 2026-08-02, low footprint, no restart/OOM
**Host:** mini · **Component:** memos logs + resources · **Auditor:** svc:memos

### UI140. GREEN: drift-free mirror, restic-backed state, full monitoring coverage (3 consumer-grade checks + Homepage tile + Kuma monitor + catalog row)
**Host:** mini · **Component:** metube · **Auditor:** svc:metube

### UI141. GREEN: metube consumer chain proven end-to-end (download completed 2026-08-15, file present at NAS destination, POT provider reachable)
**Host:** mini · **Component:** metube · **Auditor:** svc:metube

### UI142. Observation: baked-in nightly yt-dlp is the 2026-07-06 build (image built 2026-07-09); still proven working 2026-08-15
**Host:** mini · **Component:** metube · **Auditor:** svc:metube

### UI143. GREEN: every mini host unit healthy end-to-end — state, logs, throughput, tiers all verified
**Host:** mini · **Component:** mini host units (all 15 timers/services) · **Auditor:** svc:mini-host-units

### UI144. GREEN: consumer feature proven end-to-end — poller live, articles flowing, 0 parsing errors, vhost serving app
**Host:** mini · **Component:** miniflux · **Auditor:** svc:miniflux

### UI145. GREEN: logs clean since 2026-08-02 — 0 ERROR lines, only transient webcomic fetch timeouts; rig 401 probes ceased Aug 15
**Host:** mini · **Component:** miniflux · **Auditor:** svc:miniflux

### UI146. GREEN: monitoring/catalog complete — coverage manifest, 2 consumer-grade checks, Homepage tile, active Kuma monitor, catalog row
**Host:** mini · **Component:** miniflux · **Auditor:** svc:miniflux

### UI147. GREEN: no config drift — live compose identical to repo mirror; backup leg verified via nightly pg_dump inside restic set
**Host:** mini · **Component:** miniflux · **Auditor:** svc:miniflux

### UI148. VERIFIED e2e: Miniflux 49 feeds fresh + articles flowing (no frozen-poller / zero-throughput)
**Host:** mini · **Component:** miniflux · **Auditor:** flow:reading-web

### UI149. 3 transient Lidarr 500s on /api/v1/history in last 12h under current NAS IO load; retries succeed `known-issue`
**Host:** mini · **Component:** musicseerr · **Auditor:** svc:musicseerr

### UI150. GREEN: request->Lidarr delivery chain verified end to end; state/backup/monitoring/catalog all in order
**Host:** mini · **Component:** musicseerr · **Auditor:** svc:musicseerr

### UI151. Historical: Lidarr circuit breaker opened repeatedly during a single 2026-08-11 window; fully recovered
**Host:** mini · **Component:** musicseerr · **Auditor:** svc:musicseerr

### UI152. UNPROBED: authenticated in-app API surface (/api/status/lidarr/connection etc.)
**Host:** mini · **Component:** musicseerr · **Auditor:** svc:musicseerr

### UI153. UNPROBED: live music request submission not exercised (read-only mandate)
**Host:** mini · **Component:** musicseerr -> Lidarr request submission · **Auditor:** flow:music

### UI154. Consumer feature PROVEN end-to-end: journal reflection loop + household bug intake both fire real automations
**Host:** mini · **Component:** n8n · **Auditor:** svc:n8n

### UI155. Container healthy, restart-clean, resource-light; logs clean since 08-02
**Host:** mini · **Component:** n8n · **Auditor:** svc:n8n

### UI156. Monitoring + catalog coverage present and consumer-grade
**Host:** mini · **Component:** n8n · **Auditor:** svc:n8n

### UI157. No config/workflow drift; state inside integrity-checked restic backup
**Host:** mini · **Component:** n8n · **Auditor:** svc:n8n

### UI158. UNPROBED: Uptime-Kuma monitor for n8n not verified
**Host:** mini · **Component:** n8n · **Auditor:** svc:n8n

### UI159. Zero-throughput probe CLEARED: 0% failure rate across 122 executions, newest today
**Host:** mini · **Component:** n8n · **Auditor:** svc:n8n

### UI160. GREEN: Navidrome verified working end to end (authenticated Subsonic API + fresh scan + live library throughput)
**Host:** mini · **Component:** navidrome · **Auditor:** svc:navidrome

### UI161. GREEN: full coverage — 7 consumer-grade checks, coverage manifest, Homepage tile, Kuma monitor, catalog row, and a double backup leg all verified
**Host:** mini · **Component:** navidrome · **Auditor:** svc:navidrome

### UI162. Alert transport PROVEN end-to-end: verification topic delivered today's real failure alert to an authed subscriber
**Host:** mini · **Component:** ntfy · **Auditor:** svc:ntfy

### UI163. Auth posture correct: anonymous publish AND read denied (403), ACL least-privilege
**Host:** mini · **Component:** ntfy · **Auditor:** svc:ntfy

### UI164. Cross-lane note: transport surfaced 2 NEW failures this morning outside the audit baseline
**Host:** mini · **Component:** ntfy · **Auditor:** svc:ntfy

### UI165. State/logs/drift/resources/backup/monitoring/catalog all clean
**Host:** mini · **Component:** ntfy · **Auditor:** svc:ntfy

### UI166. GREEN verified: ntfy deny-all is global — anon publish 403 on every alert topic
**Host:** mini · **Component:** ntfy-anon-publish-denied · **Auditor:** meta:secrets

### UI167. GREEN: OWUI-proxied code execution proven working end-to-end
**Host:** mini · **Component:** open-terminal · **Auditor:** svc:open-terminal

### UI168. GREEN: auth enforced + sandbox isolation intact (arbitrary-code-exec service)
**Host:** mini · **Component:** open-terminal · **Auditor:** svc:open-terminal

### UI169. GREEN: no config drift, backed up, monitored, cataloged
**Host:** mini · **Component:** open-terminal · **Auditor:** svc:open-terminal

### UI170. UNPROBED: an LLM autonomously invoking run_command inside a live OWUI chat turn
**Host:** mini · **Component:** open-terminal / OWUI code-exec (lai-09) · **Auditor:** flow:owui-code-exec

### UI171. VERIFIED end-to-end: OWUI runs real Python on the mini open-terminal sandbox
**Host:** mini · **Component:** open-terminal / OWUI code-exec (lai-09) · **Auditor:** flow:owui-code-exec

### UI172. GREEN: consumer feature proven end-to-end — full-text search grounded, PDF download serves, proxy path works
**Host:** mini · **Component:** paperless · **Auditor:** svc:paperless

### UI173. UNPROBED: live OCR ingestion of a NEW document (consume-dir drop / mail import)
**Host:** mini · **Component:** paperless · **Auditor:** svc:paperless

### UI174. Zero-throughput observation: newest document added 2026-07-22 (31 days), but pipeline provably alive — idle by input, not frozen
**Host:** mini · **Component:** paperless · **Auditor:** svc:paperless

### UI175. GREEN: backup leg verified — consistent nightly pg_dump + restic snapshot fresh as of 2026-08-22 01:34
**Host:** mini · **Component:** paperless (backup leg) · **Auditor:** svc:paperless

### UI176. Photon US offline geocoder verified working end-to-end (consumer probe + audit-uc + drift-free + monitored)
**Host:** mini · **Component:** photon (maps stack) · **Auditor:** svc:photon

### UI177. Zero-throughput taxonomy #13 CLEARED — static index is on-demand by design, not a frozen poller
**Host:** mini · **Component:** photon (maps stack) · **Auditor:** svc:photon

### UI178. 14G Photon index volume is outside the restic backup set — reconstructible-by-design, not a data-loss gap
**Host:** mini · **Component:** photon (maps stack) / restic backup · **Auditor:** svc:photon

### UI179. VERIFIED e2e: Photon offline US geocoder returns accurate coords for multiple real towns
**Host:** mini · **Component:** photon / Caddy maps.tabaska.us/geocode (lai-17) · **Auditor:** flow:offline-maps

### UI180. 35 undownloaded items are all members-only or removed videos — external limitation, not a pipeline fault
**Host:** mini · **Component:** pinchflat · **Auditor:** svc:pinchflat

### UI181. GREEN: pinchflat verified end-to-end — archiving pipeline working, monitored, backed up, zero drift
**Host:** mini · **Component:** pinchflat · **Auditor:** svc:pinchflat

### UI182. fix-37/67 bot-check residual RE-VERIFIED and improved: zero bot-check-stranded media remain (was 8 accepted) `known-issue`
**Host:** mini · **Component:** pinchflat · **Auditor:** svc:pinchflat

### UI183. GREEN + IMPROVED: bgutil-pot version match confirmed and bot-strand fully cleared `known-issue`
**Host:** mini · **Component:** pinchflat bgutil POT provider (fix-37/fix-67) · **Auditor:** flow:youtube

### UI184. No config drift; monitoring, homepage, catalog and coverage all in place
**Host:** mini · **Component:** pmtiles · **Auditor:** svc:pmtiles

### UI185. Offline US basemap serves real vector tiles end-to-end via localhost and maps.tabaska.us vhost — verified working
**Host:** mini · **Component:** pmtiles · **Auditor:** svc:pmtiles

### UI186. State stable and logs clean since 2026-08-02
**Host:** mini · **Component:** pmtiles · **Auditor:** svc:pmtiles

### UI187. VERIFIED e2e: offline US PMTiles basemap serves real vector tiles through Caddy
**Host:** mini · **Component:** pmtiles / Caddy maps.tabaska.us (lai-17) · **Auditor:** flow:offline-maps

### UI188. Coverage-manifest omission is by-design (no persistent container) — compensated by dead-man + catalog + host-hygiene allowlist
**Host:** mini · **Component:** recyclarr · **Auditor:** svc:recyclarr

### UI189. GREEN: deliberate sonarr quality-sync disable confirmed matching live behavior
**Host:** mini · **Component:** recyclarr · **Auditor:** svc:recyclarr

### UI190. GREEN: weekly TRaSH sync proven working end-to-end (ran today, both *arr instances synced)
**Host:** mini · **Component:** recyclarr · **Auditor:** svc:recyclarr

### UI191. GREEN: zero drift, secrets hygiene clean, backup leg confirmed
**Host:** mini · **Component:** recyclarr · **Auditor:** svc:recyclarr

### UI192. GREEN + FIRST-EVER RESTORE DRILL: file restored from mini B2 repo is byte-identical to source
**Host:** mini · **Component:** restic / B2 restore path (documented gap: no restore drill ever) · **Auditor:** flow:backups-restore-drill

### UI193. GREEN: restic snapshots landing daily on both mini and rig, newest <16h old
**Host:** mini · **Component:** restic mini+rig B2 freshness / cadence · **Auditor:** flow:backups-restore-drill

### UI194. Backup repo immutability is a known CRIT baseline (fix-22) affecting open-terminal's backup leg `known-issue`
**Host:** mini · **Component:** restic-backup · **Auditor:** svc:open-terminal

### UI195. GREEN: restic backup leg fresh, integrity-clean, unit files covered, marker + dead-man current
**Host:** mini · **Component:** restic-backup.service/.timer (+marker) · **Auditor:** svc:mini-host-units

### UI196. GREEN: RomM consumer feature verified working end-to-end (proxy heartbeat, live DB library, RA enabled, rig ES-DE, CIFS consistency)
**Host:** mini · **Component:** romm (RomM ROM manager) · **Auditor:** svc:romm

### UI197. VERIFIED: RomM library consistent with live NAS ROM store, RetroAchievements on (dead-CIFS tripwire clear)
**Host:** mini · **Component:** romm / NAS CIFS Games share · **Auditor:** flow:retro

### UI198. Log volume: 31,162 of 39,490 lines since 2026-08-02 are 'GET / 200' monitor polls (~1/min) — noise, not a retry storm
**Host:** mini · **Component:** romm nginx access log · **Auditor:** svc:romm

### UI199. Zero-throughput probe: newest rom scan 2026-07-21 (33 days ago) — expected for a static on-demand ROM library, NOT frozen-green
**Host:** mini · **Component:** romm scan freshness · **Auditor:** svc:romm

### UI200. GREEN: collector proven working end-to-end — mini disk fresh in NAS hub with daily continuity
**Host:** mini · **Component:** scrutiny-collector · **Auditor:** svc:scrutiny-collector-mini

### UI201. Known: scrutiny-collector_default bridge squats 192.168.48.0/20 (ha-19) `known-issue`
**Host:** mini · **Component:** scrutiny-collector · **Auditor:** svc:scrutiny-collector-mini

### UI202. GREEN: SearXNG metasearch verified working end-to-end for all consumers
**Host:** mini · **Component:** searxng · **Auditor:** svc:searxng

### UI203. No Uptime-Kuma monitor confirmed for SearXNG (SQLite-stored; unverifiable read-only) — minor, coverage otherwise strong
**Host:** mini · **Component:** searxng · **Auditor:** svc:searxng

### UI204. GREEN: ntfy anon-publish denied (403); vault-lint clean; .env.example parity holds on mini/rig/NAS
**Host:** mini · **Component:** secrets / ntfy access control + vault lint + env parity · **Auditor:** cross:secrets-hygiene

### UI205. Green confirmation: seerr healthy end-to-end — state, request pipeline (24/33 delivered), vhost, drift, backup, catalog, and full monitoring coverage all verified
**Host:** mini · **Component:** seerr · **Auditor:** svc:seerr

### UI206. seerr v3.2.0 pinned; upstream reports updateAvailable:true
**Host:** mini · **Component:** seerr · **Auditor:** svc:seerr

### UI207. GREEN: denylist reconciler + ghost/crashloop checks all pass in audit run
**Host:** mini · **Component:** soularr-denylist-reconcile (fix-56 closer) + docker-fleet check · **Auditor:** svc:soularr

### UI208. GREEN: mesh node verified end-to-end — direct TCP to hub, 0 folder errors, fresh scans, real sync throughput
**Host:** mini · **Component:** syncthing · **Auditor:** svc:syncthing-mini

### UI209. GREEN: no drift, quiet logs, lean resources, backup + coverage + catalog + homepage all in place
**Host:** mini · **Component:** syncthing · **Auditor:** svc:syncthing-mini

### UI210. GREEN: backup leg confirmed — /opt/stacks/tautulli inside the live restic BACKUP_PATHS, daily timer active, not excluded
**Host:** mini · **Component:** tautulli · **Auditor:** svc:tautulli

### UI211. GREEN: consumer feature proven end-to-end — history ingest live (newest row tonight 19:52 EDT), API + Caddy vhost both serve real data, zero drift
**Host:** mini · **Component:** tautulli · **Auditor:** svc:tautulli

### UI212. GREEN: monitoring/catalog presence complete — coverage manifest, Homepage tile+widget, active Kuma monitor, correct catalog row, audit-run check pass
**Host:** mini · **Component:** tautulli · **Auditor:** svc:tautulli

### UI213. Terraria co-op server PROVEN joinable end-to-end (state, REST world-state, wire handshake, fresh saves, monitoring, catalog all green)
**Host:** mini · **Component:** terraria · **Auditor:** svc:terraria

### UI214. UNPROBED: Tailscale/internet friend-reach (game-04) and a real end-client block-place not exercised
**Host:** mini · **Component:** terraria · **Auditor:** svc:terraria

### UI215. World save is in the restic backup set (service success), but B2 immutability guarantee is the known-open CRIT fix-22 `known-issue`
**Host:** mini · **Component:** terraria · **Auditor:** svc:terraria

### UI216. GREEN: Terraria join handshake + TShock REST world proven
**Host:** mini · **Component:** terraria / tshock · **Auditor:** flow:game-servers

### UI217. GREEN: tv-torrent-cleanup 'last pinged 08-16' root-caused — correctly-functioning WEEKLY dead-man, not a fault
**Host:** mini · **Component:** tv-torrent-cleanup.timer/.service · **Auditor:** svc:mini-host-units

### UI218. GREEN: unbound recursion + DNSSEC validation + AdGuard consumer chain proven end to end
**Host:** mini · **Component:** unbound · **Auditor:** svc:unbound

### UI219. UNPROBED: unbound internal cache/qps statistics — remote-control not enabled
**Host:** mini · **Component:** unbound · **Auditor:** svc:unbound

### UI220. GREEN: zero config drift — 26 deployed unit/script files SHA256 byte-identical to repo mirror
**Host:** mini · **Component:** unit-file drift (all lane units) · **Auditor:** svc:mini-host-units

### UI221. GREEN: uptime-kuma verified working end-to-end (engine, status page, vhost, notifications, backup, coverage)
**Host:** mini · **Component:** uptime-kuma · **Auditor:** svc:uptime-kuma

### UI222. fix-79 re-verified: down monitor was Rig Apollo (#34, rig :47990), down 08-03 to 08-16, RECOVERED — down=0 today, not worsened `known-issue`
**Host:** mini · **Component:** uptime-kuma · **Auditor:** svc:uptime-kuma

### UI223. Full 363/377 → 358/388 reconciliation: +11 checks (13 added / 2 removed), −5 pass, all deltas explained, zero unexplained flips `known-issue`
**Host:** mini · **Component:** verification / baseline-delta reconciliation · **Auditor:** triage:baseline-delta

### UI224. GREEN: checks.d 41/41 byte-identical repo↔deployed; all four live docker rosters exact-match their repo manifests (zero drift)
**Host:** mini · **Component:** verification asset parity (checks.d + live rosters) · **Auditor:** meta:coverage-diff

### UI225. UNPROBED: HACS-loaded check is disabled (SKIPPED) — not probed this run
**Host:** mini · **Component:** verification check ha-hacs-loaded (ha-04) · **Auditor:** flow:home-assistant

### UI226. File summary: 7 checks (2 consumer, 4 intermediate, 1 liveness, 0 disabled); integrity fully clean; deployed copy identical to repo; all 7 passed today's 10:29 EDT run
**Host:** mini · **Component:** verification/checks.d/bug-intake.yaml · **Auditor:** meta:bug-intake

### UI227. File summary: 6 checks — 5 consumer-grade, 1 intermediate, 0 liveness, 0 disabled; all 6 probes re-verified green live; integrity clean except runbook paths
**Host:** mini · **Component:** verification/checks.d/dns.yaml · **Auditor:** meta:dns

### UI228. Check green-but-counting-down: exposed Plex build 1.43.3.10793 is one behind latest Synology release 1.43.3.10896 (10.4 days old); the 14-day grace expires ~2026-08-26 and the warn will fire — underlying condition is open task fix-70 `known-issue`
**Host:** mini · **Component:** verification/checks.d/edge.yaml — edge-plex-version-current · **Auditor:** meta:edge

### UI229. File summary: 6 checks, 4 consumer-grade / 2 intermediate / 0 liveness / 0 disabled; integrity fully clean; all 6 re-verified green live from the off-net vantage this evening
**Host:** mini · **Component:** verification/checks.d/edge.yaml · **Auditor:** meta:edge

### UI230. Lane summary: 11 checks — 7 consumer-grade, 3 intermediate-by-design, 1 liveness, 0 disabled; integrity fully clean, all baselines verified live
**Host:** mini · **Component:** verification/checks.d/gaming.yaml (whole file) · **Auditor:** meta:gaming

### UI231. ha.yaml: 12 checks — 7 consumer, 4 intermediate, 1 liveness-only, 1 disabled; structure sound, deployed copy identical to repo
**Host:** mini · **Component:** verification/checks.d/ha.yaml (file meta-audit summary) · **Auditor:** meta:ha

### UI232. File summary: 10 checks — 8 consumer-grade, 2 intermediate, 0 liveness-only, 0 disabled; integrity clean
**Host:** mini · **Component:** verification/checks.d/host-hygiene.yaml · **Auditor:** meta:host-hygiene

### UI233. GREEN verified: 6 of 10 checks re-run live and passing with non-stale baselines
**Host:** mini · **Component:** verification/checks.d/host-hygiene.yaml · **Auditor:** meta:host-hygiene

### UI234. File summary: 14 checks — 5 consumer / 6 intermediate / 3 liveness / 0 disabled; all green, integrity clean, baselines re-verified live
**Host:** mini · **Component:** verification/checks.d/journaling.yaml · **Auditor:** meta:journaling

### UI235. File summary: 26 checks — 20 consumer-grade, 6 justified-intermediate, 0 liveness-only, 0 disabled; all integrity gates pass and all 26 green at today's 10:29 run
**Host:** mini · **Component:** verification/checks.d/local-ai.yaml (whole file) · **Auditor:** meta:local-ai

### UI236. File summary: 6 checks, 4 consumer-grade / 2 intermediate / 0 liveness / 0 disabled — all live-verified passing
**Host:** mini · **Component:** verification/checks.d/media-aux.yaml · **Auditor:** meta:media-aux

### UI237. File summary: 5 checks — 3 consumer-grade, 2 intermediate, 0 liveness-only, 0 disabled; all integrity gates pass; repo and live copies identical
**Host:** mini · **Component:** verification/checks.d/media-indexers.yaml · **Auditor:** meta:media-indexers

### UI238. File summary: 9 checks, 6 consumer-grade, 3 intermediate-by-design, 0 liveness, 0 disabled — structurally sound
**Host:** mini · **Component:** verification/checks.d/media-library-correctness.yaml · **Auditor:** meta:media-library-correctness

### UI239. File summary: 2 checks (1 consumer, 1 intermediate, 0 liveness-only, 0 disabled) — both green live, integrity clean
**Host:** mini · **Component:** verification/checks.d/media-subtitles.yaml · **Auditor:** meta:media-subtitles

### UI240. File summary: 4 checks, 3 consumer-grade, 1 intermediate-by-design, 0 liveness-only, 0 disabled — all green in today's daily sweep, zero repo/deploy drift
**Host:** mini · **Component:** verification/checks.d/media-watchable.yaml · **Auditor:** meta:media-watchable

### UI241. File summary: 21 checks, 12 consumer / 7 intermediate / 2 justified-liveness, 0 disabled, deploy parity confirmed, 20/21 passing live
**Host:** mini · **Component:** verification/checks.d/media.yaml · **Auditor:** meta:media

### UI242. File summary: 3 checks, all enabled:false (justified decommission), 2 consumer + 1 intermediate, zero liveness decay, integrity clean
**Host:** mini · **Component:** verification/checks.d/meme-review.yaml · **Auditor:** meta:meme-review

### UI243. File summary: 28 checks — 5 consumer-grade, 11 intermediate, 12 liveness, 0 disabled; structure clean, repo==deployed, all live baselines re-verified green
**Host:** mini · **Component:** verification/checks.d/mini-services.yaml · **Auditor:** meta:mini-services

### UI244. File summary: 9 checks, 5 consumer-grade / 4 intermediate / 0 liveness-only / 0 disabled — integrity clean
**Host:** mini · **Component:** verification/checks.d/monitoring-coverage.yaml · **Auditor:** meta:monitoring-coverage

### UI245. GREEN confirmation: all 9 monitoring-coverage checks passed today's 10:29 EDT run, key baselines re-verified live tonight
**Host:** mini · **Component:** verification/checks.d/monitoring-coverage.yaml · **Auditor:** meta:monitoring-coverage

### UI246. File summary: 24 checks — 6 consumer, 5 intermediate, 12 liveness (10 deliberate fast-gates), 1 disabled; structural integrity clean
**Host:** mini · **Component:** verification/checks.d/nas-services.yaml · **Auditor:** meta:nas-services

### UI247. File summary: 1 check total — 0 consumer-grade, 0 intermediate, 1 liveness-grade (TCP port-open), 0 disabled
**Host:** mini · **Component:** verification/checks.d/network.yaml · **Auditor:** meta:network

### UI248. Verified green end to end live: probe passes from mini, baseline IP 192.168.20.100 still is the real Hue bridge, repo/deployed parity holds
**Host:** mini · **Component:** verification/checks.d/network.yaml — net-trusted-to-iot-reachable · **Auditor:** meta:network

### UI249. File summary: 3 checks, all consumer-grade, all enabled, integrity clean
**Host:** mini · **Component:** verification/checks.d/power-journal.yaml · **Auditor:** meta:power-journal

### UI250. GREEN: all 3 fix-31 checks verified live end to end (nut retired, journals under cap, cap conf present)
**Host:** mini · **Component:** verification/checks.d/power-journal.yaml · **Auditor:** meta:power-journal

### UI251. File summary: 30 checks — 20 consumer-grade, 9 honest intermediate guards, 1 liveness-leaning, 0 disabled; integrity fully clean and all 30 passing in today's daily run
**Host:** mini · **Component:** verification/checks.d/reading.yaml · **Auditor:** meta:reading

### UI252. File summary: 1 check, consumer-grade, 0 disabled, integrity clean
**Host:** mini · **Component:** verification/checks.d/retro-emulation.yaml · **Auditor:** meta:retro-emulation

### UI253. Lane summary: 5 enabled checks, 1 consumer + 4 intermediate, 0 liveness-only, 0 disabled — all live-verified healthy
**Host:** mini · **Component:** verification/checks.d/rig-immich-ml.yaml · **Auditor:** meta:rig-immich-ml

### UI254. File summary: 10 checks, 2 consumer / 2 intermediate / 5 liveness / 1 disabled — consumer-grade checks verified green live
**Host:** mini · **Component:** verification/checks.d/system.yaml · **Auditor:** meta:system

### UI255. File audit: 2/2 consumer-grade checks, integrity intact, no defects
**Host:** mini · **Component:** verification/checks.d/verification-env-integrity.yaml · **Auditor:** meta:verification-env-integrity

### UI256. verification-self.yaml healthy: 7 checks (3 consumer / 4 intermediate / 0 liveness), integrity clean, all pass live
**Host:** mini · **Component:** verification/checks.d/verification-self.yaml · **Auditor:** meta:verification-self

### UI257. GREEN sub-metric secrets=0 (cookie class not recurred) + 1-of-103 count noise from snapd system dir /tmp/snap-private-tmp `known-issue`
**Host:** mini · **Component:** verification/host-hygiene check precision · **Auditor:** triage:mini-scratch-hygiene

### UI258. meme-review-01 disable rationale HOLDS — service fully decommissioned (no container, vhost commented out) `known-issue`
**Host:** mini · **Component:** verification/meme-review-{api-health,spa-served,auth-wall} (meme-review.yaml) · **Auditor:** triage:skips

### UI259. Green confirmation: backup leg verified — /opt/stacks in restic set plus consistent mariadb-dump fresh today
**Host:** mini · **Component:** wallabag · **Auditor:** svc:wallabag

### UI260. Green confirmation: wallabag stack healthy end to end — app serves through vhost, DB holds fully-scraped article content
**Host:** mini · **Component:** wallabag · **Auditor:** svc:wallabag

### UI261. UNPROBED: authenticated OAuth/API leg (token grant + entry read as the logged-in consumer)
**Host:** mini · **Component:** wallabag · **Auditor:** svc:wallabag

### UI262. Zero-throughput observation: newest entry 16 days old, 1 user, 0 of 22 entries archived — idle by design, not frozen
**Host:** mini · **Component:** wallabag · **Auditor:** svc:wallabag

### UI263. Wiki consumer feature proven: current service pages + search served end to end
**Host:** mini · **Component:** wiki · **Auditor:** svc:wiki

### UI264. Backup leg correct: source in git dual-remote, generated site deliberately excluded from restic `known-issue`
**Host:** mini · **Component:** wiki-backup · **Auditor:** svc:wiki

### UI265. Served site is current with repo HEAD; no build drift
**Host:** mini · **Component:** wiki-build-currency · **Auditor:** svc:wiki

### UI266. wiki->OWUI RAG sync timer healthy: clean daily runs, exit 0, 369 docs tracked
**Host:** mini · **Component:** wiki-rag-sync.timer · **Auditor:** svc:wiki

### UI267. GREEN: existing-library Kobo + KOReader sync proven working end-to-end
**Host:** mini+nas · **Component:** books-kobo chain (libreseerr->Bookshelf->rreading-glasses-hc->Prowlarr->Deluge->readarr-copy-to-cwa-ingest->Calibre->Kobo/KOSync) · **Auditor:** flow:books-kobo

### UI268. GREEN: YouTube video chain proven working end-to-end to the Plex consumer
**Host:** mini+nas · **Component:** pinchflat / bgutil-pot / nas-youtube mount / DSM ACE / Plex section 4 · **Auditor:** flow:youtube

### UI269. GREEN: music streaming proven end-to-end on both consumers with real audio bytes; full acquisition chain live
**Host:** mini+nas+rig · **Component:** music chain (Navidrome/Plex/rig-ALAC + musicseerr/Lidarr/slskd/soularr) · **Auditor:** flow:music

### UI270. GREEN: request-to-play movies/TV proven working end to end
**Host:** mini+nas+seedbox · **Component:** movies-tv chain (Seerr→arr→Prowlarr→Deluge→NAS mount→unpackerr→import→Plex/Jellyfin) · **Auditor:** flow:movies-tv

### UI271. VERIFIED WORKING E2E: synthetic report -> rig-generated diagnosis comment + triaged label -> self-cleaned
**Host:** mini+rig · **Component:** bug-triage (bug-02) read-only auto-triage loop (mini observes -> rig reasons) · **Auditor:** flow:bug-intake-triage

### UI272. Journaling reflection loop VERIFIED working end-to-end (consumer-proven, loop-guarded, self-cleaning)
**Host:** mini+rig · **Component:** journaling (Memos #journal -> n8n /webhook/journal -> faster-whisper -> rig dolphin-venice-24b -> reflection comment) · **Auditor:** flow:journaling

### UI273. Core git control plane VERIFIED working end-to-end (dual-remote parity, Forgejo serving, byte-parity discipline)
**Host:** mini+rig+mac · **Component:** git-control-plane / dual-remote mirror + Forgejo + anti-drift · **Auditor:** flow:git-control-plane

### UI274. Eight services have only liveness-plus coverage (backend payload asserted, but no deep consumer-function probe)
**Host:** mini,nas,rig · **Component:** thin liveness-plus services (mealie, wallabag, tautulli, stash, metube, flaresolverr, diun, rreading-glasses-hc/db) · **Auditor:** meta:coverage-diff · *skeptic-confirmed*

### UI275. VERIFIED: wiki->OWUI RAG chain works end-to-end, retrieval gap holds closed
**Host:** mini,rig · **Component:** wiki-rag (wiki site -> wiki-rag-sync.timer -> OWUI homelab-wiki knowledge collection) · **Auditor:** flow:wiki-rag

### UI276. Listener-drift sweep totals: mini+nas clean, rig has 3 benign attributed deltas, zero rogue listeners `known-issue`
**Host:** mini,rig,nas · **Component:** lan-exposure / listener-drift (fix-51) · **Auditor:** cross:lan-exposure

### UI277. SUMMARY: 8/8 recent done-marked check families re-verified GREEN live; 3 docs/manifest-truth gaps (all reopen-covered); tracker math coherent
**Host:** multi · **Component:** docs-tracker-truth lane summary · **Auditor:** cross:docs-tracker-truth

### UI278. CONFIRMED: tracker JSONs arithmetically coherent, wiki generated pages in sync, _meta.updated is current (NOT stale)
**Host:** multi · **Component:** tracker arithmetic + integrity + wiki-drift + _meta currency · **Auditor:** cross:docs-tracker-truth

### UI279. RE-VERIFIED GREEN: perms invariant holds on all sampled high-risk secret files (cheap spot-stat, no full find) `known-issue`
**Host:** nas · **Component:** /volume1/docker secret config files (mylar3, soularr, immich, arr suite, syncthing) · **Auditor:** triage:nas-secret-file-perms

### UI280. Subtitle chain verified working end-to-end (arrs -> Bazarr -> provider -> .srt on disk)
**Host:** nas · **Component:** Bazarr (192.168.10.4:6767) subtitle pipeline · **Auditor:** flow:subtitles

### UI281. UNPROBED: provider live subtitle-search (deliberately, rate-limited)
**Host:** nas · **Component:** Bazarr provider live-search · **Auditor:** flow:subtitles

### UI282. GREEN: fix-50 core fix HOLDS — Bitmagnet DHT remains demoted to interactive-only in both radarr and sonarr `known-issue`
**Host:** nas · **Component:** Bitmagnet (DHT) demotion guard (arr-grab-indexer-share.py demoted) · **Auditor:** triage:arr-grab-source-not-storming

### UI283. GREEN (with caveat): book metadata search verified working end-to-end — returns canonical Austen work, just slowly `known-issue`
**Host:** nas · **Component:** Bookshelf book/lookup metadata search (C2 canary path) · **Auditor:** triage:metadata-search-canary

### UI284. DSM 7.2.2-72806 update 5 (built 2025-11-10), package auto-update disabled (deliberate)
**Host:** nas · **Component:** DSM update posture · **Auditor:** svc:nas-dsm-tasks

### UI285. GREEN: HA offsite backup fresh — daily tar landing, newest ~16h old
**Host:** nas · **Component:** HA off-eMMC backup dead-man (/volume1/backups on NAS) · **Auditor:** flow:home-assistant

### UI286. GREEN: HA config backup landed off-eMMC on NAS ~12.4h ago, correct owner
**Host:** nas · **Component:** Home Assistant offsite backup tar (ha-11 / fix-53) · **Auditor:** flow:backups-restore-drill

### UI287. GREEN: Hyper Backup completing to Backblaze B2 within window; daily + weekly-integrity tasks enabled
**Host:** nas · **Component:** Hyper Backup (S3 Backup enc, DSM tasks id=11/id=12) · **Auditor:** svc:nas-dsm-tasks

### UI288. GREEN: the 80 IPT-dominated grabs are LEGIT content, not junk — mission junk-grab-risk hypothesis disproven
**Host:** nas · **Component:** IPTorrents grab stream (mission question: junk vs legit) · **Auditor:** triage:arr-grab-source-not-storming

### UI289. GREEN: Immich DB dump fresh, non-truncated, rotation bounded
**Host:** nas · **Component:** Immich Postgres pg_dump (nas-08 / fix-60) · **Auditor:** flow:backups-restore-drill

### UI290. GREEN(with caveat): last Hyper Backup session committed ~18.7h ago; session-result log not locatable
**Host:** nas · **Component:** NAS Hyper Backup -> B2 (nas-02) · **Auditor:** flow:backups-restore-drill

### UI291. IO storm confirmed tonight (load 11.87 / IO 11.15) — real aggravator but not sole cause of the timeout
**Host:** nas · **Component:** NAS IO load (environmental aggravator) · **Auditor:** triage:nas-secret-file-perms

### UI292. New check iptorrents-idsearch-returns-results (added 08-11) fails tonight (0 items, 60s) but passed this morning (100 items) — likely NAS-IO-starved Prowlarr, re-verify vs IPT budget/cookie `known-issue`
**Host:** nas · **Component:** Prowlarr / IPTorrents indexer (verify-06) · **Auditor:** triage:baseline-delta · *skeptic-confirmed*

### UI293. KNOWN/expected: StrategyWiki ZIM deferred (Cloudflare blocks mwoffliner) — blocked-mode check green `known-issue`
**Host:** nas · **Component:** StrategyWiki ZIM (lai-15) · **Auditor:** svc:kiwix

### UI294. GREEN: secondary DNS consumer feature verified working end-to-end; container/monitoring/backup/drift all clean
**Host:** nas · **Component:** adguardhome-nas · **Auditor:** svc:adguard-nas

### UI295. Downstream imports/queues NOT lock-blocked right now — storm self-heals between crests `known-issue`
**Host:** nas · **Component:** arr download queues + soularr (downstream consumers) · **Auditor:** triage:arr-sqlite-not-locked

### UI296. Audiobooks library holds a single deploy-day item; audiobook half of the service is effectively unused
**Host:** nas · **Component:** audiobookshelf · **Auditor:** svc:audiobookshelf

### UI297. Audiobookshelf verified working end-to-end (podcast auto-download + authed library API), drift-free, backed up, monitored
**Host:** nas · **Component:** audiobookshelf · **Auditor:** svc:audiobookshelf

### UI298. Media trees (podcasts/audiobooks) are outside the Tier-1 B2 backup set; only config+metadata is backed up
**Host:** nas · **Component:** audiobookshelf · **Auditor:** svc:audiobookshelf

### UI299. GREEN: backed up, monitored with consumer-grade checks, catalog correct
**Host:** nas · **Component:** backup / monitoring / catalog coverage · **Auditor:** svc:rreading-glasses

### UI300. CWA library share /volume1/books (1.5G incl. metadata.db catalog) is OUTSIDE the offsite Hyper Backup->B2 include set
**Host:** nas · **Component:** backup-coverage / calibre-web-automated · **Auditor:** svc:calibre-web-automated · *skeptic-confirmed*

### UI301. GREEN: no config drift, backup leg + monitoring + catalog all correct
**Host:** nas · **Component:** bazarr · **Auditor:** svc:bazarr

### UI302. GREEN: subtitle consumer chain proven end-to-end (arr-sync + providers + fetch)
**Host:** nas · **Component:** bazarr · **Auditor:** svc:bazarr

### UI303. Transient gestdown HTTPError auto-disable/re-enable = expected free-provider rate-limiting
**Host:** nas · **Component:** bazarr · **Auditor:** svc:bazarr

### UI304. UNPROBED: could not confirm /volume1/docker/beets is in a HyperBackup include list
**Host:** nas · **Component:** beets backup leg (/volume1/docker) · **Auditor:** svc:beets

### UI305. GREEN: container healthy, web UI serving, daily job fresh, config matches repo, non-destructive intact
**Host:** nas · **Component:** beets container + config · **Auditor:** svc:beets

### UI306. GREEN: nas agent healthy + hub shows fresh nas metrics end-to-end
**Host:** nas · **Component:** beszel-agent · **Auditor:** svc:beszel-agent-nas

### UI307. GREEN: no config drift + backup + monitoring/coverage all present
**Host:** nas · **Component:** beszel-agent · **Auditor:** svc:beszel-agent-nas

### UI308. GREEN: DHT crawler ingesting healthily — zero-throughput ruled out (taxonomy 13)
**Host:** nas · **Component:** bitmagnet · **Auditor:** svc:bitmagnet

### UI309. GREEN: monitoring + catalog + homepage coverage complete (mandate 2)
**Host:** nas · **Component:** bitmagnet · **Auditor:** svc:bitmagnet

### UI310. GREEN: registered+demoted in Prowlarr (fix-50 holds), caps/GraphQL alive, containers healthy, no drift
**Host:** nas · **Component:** bitmagnet · **Auditor:** svc:bitmagnet

### UI311. GREEN: DHT crawler verified ingesting at healthy rate — 2426 new torrents in 30 min at today's run
**Host:** nas · **Component:** bitmagnet / bitmagnet-dht-ingesting · **Auditor:** meta:media-indexers

### UI312. GREEN: fix-55 bitmagnet workload-reduction is holding — chronic NAS IO baseline ~3.0 vs pre-fix 17-22 `known-issue`
**Host:** nas · **Component:** bitmagnet DHT crawler / fix-55 remediation · **Auditor:** triage:nas-io-pressure

### UI313. UNPROBED: backup leg for the 28G postgres data dir not verified
**Host:** nas · **Component:** bitmagnet-postgres · **Auditor:** svc:bitmagnet

### UI314. GREEN: core book-automation pipeline verified end-to-end (container, imports→Calibre, guards, metadata token, mirror parity)
**Host:** nas · **Component:** bookshelf · **Auditor:** svc:bookshelf

### UI315. UNPROBED: Hyper Backup per-folder include of /volume1/docker/bookshelf/config not directly readable (DSM-internal)
**Host:** nas · **Component:** bookshelf · **Auditor:** svc:bookshelf

### UI316. Zero grabs/imports since 2026-07-20 but poller is ALIVE — not a frozen-poller stall (taxonomy 13 cleared)
**Host:** nas · **Component:** bookshelf · **Auditor:** svc:bookshelf

### UI317. GREEN: CWA proven working end-to-end — library serving + Kobo/KOReader sync + covers backfilled + ingest healthy, no drift
**Host:** nas · **Component:** calibre-web-automated · **Auditor:** svc:calibre-web-automated

### UI318. Library idle since 2026-08-03 (on-demand, NOT frozen-green) + running deliberate digest-pinned new-usemame fork v4.0.7
**Host:** nas · **Component:** calibre-web-automated · **Auditor:** svc:calibre-web-automated

### UI319. OBSERVED (not a defect): another audit lane's recursive grep over /volume1/docker/bitmagnet is stuck in D-state, adding to IO pressure
**Host:** nas · **Component:** concurrent audit-lane process observed · **Auditor:** svc:host-nas

### UI320. GREEN: diun-nas image-update→ntfy pipeline verified working end to end
**Host:** nas · **Component:** diun · **Auditor:** svc:diun-nas

### UI321. GREEN: fix-23 leaked-file + blast-radius guards intact — only the /volume1/docker share-root bit regressed
**Host:** nas · **Component:** fix-23 core secrets-hygiene remediation (health.env / ntfy deny-all / mylar3 umask / /volume1/scripts) · **Auditor:** triage:nas-worldwritable-sweep

### UI322. GREEN: FlareSolverr healthy and actively consumed by Prowlarr
**Host:** nas · **Component:** flaresolverr (media-automation compose, :8191) · **Auditor:** svc:prowlarr

### UI323. Empty staged /volume1/frigate dir persists on NAS (historical NAS-frigate consideration)
**Host:** nas · **Component:** frigate · **Auditor:** svc:frigate

### UI324. GREEN: NAS still serving all consumers — RAID healthy, Hyper Backup->B2 fresh, immich DB dump <26h, containers match manifest, no restart loops
**Host:** nas · **Component:** host-nas green confirmations (state / backup / RAID / DSM) · **Auditor:** svc:host-nas

### UI325. Immich pg_dump DB-backup leg is HEALTHY — mission's 'silent scheduled-job death' hypothesis DISPROVEN
**Host:** nas · **Component:** immich / DSM scheduled task id=9 'Immich DB dump' (pg_dump backup leg) · **Auditor:** triage:nas-immich-backup-freshness

### UI326. GREEN: DB dump fresh + off-site B2 covers photo library; full monitoring + catalog coverage
**Host:** nas · **Component:** immich backup leg + monitoring coverage + catalog · **Auditor:** svc:immich

### UI327. GREEN: primary user Immich backup flowing end-to-end; no worsening of zero-asset set `known-issue`
**Host:** nas · **Component:** immich per-user backup · **Auditor:** triage:immich-user-zero-assets

### UI328. VERIFIED: immich Postgres dumps are fresh — fix-35 'STALE' is an ingestion-not-dump misnomer
**Host:** nas · **Component:** immich pg dump backups (backup-immich-dump-fresh, nas-08) · **Auditor:** flow:photos-ml

### UI329. Cross-lane note: immich phone-backup/user-assets failing starves ML of NEW work, but ML search over existing library works `known-issue`
**Host:** nas · **Component:** immich phone backup (upstream of ML lane) · **Auditor:** svc:immich-ml-rig

### UI330. GREEN: consumer feature proven — smart search returns 100 grounded results via vhost
**Host:** nas · **Component:** immich smart search (ML encode + vector search) · **Auditor:** svc:immich

### UI331. GREEN: all 4 containers healthy 12d, v3.0.3 parity across server/openvino/cuda, zero compose drift
**Host:** nas · **Component:** immich stack state + version parity + config drift · **Auditor:** svc:immich

### UI332. GREEN: Immich DB dump firing daily, fresh and non-truncated (zero-throughput probe clean)
**Host:** nas · **Component:** immich-db-dump (DSM task id=9) · **Auditor:** svc:nas-dsm-tasks

### UI333. GREEN: Jellyfin serves populated Movies+TV libraries and streams a title end-to-end
**Host:** nas · **Component:** jellyfin (media-05) · **Auditor:** svc:jellyfin

### UI334. Backup leg covered: /volume1/docker in Hyper Backup 'docker' protected share -> B2 `known-issue`
**Host:** nas · **Component:** jellyfin backup leg · **Auditor:** svc:jellyfin

### UI335. UNPROBED: config-dir du timed out under NAS heavy-IO load
**Host:** nas · **Component:** jellyfin config dir size · **Auditor:** svc:jellyfin

### UI336. GREEN: no drift, cataloged, monitored (consumer-grade), Homepage tile present
**Host:** nas · **Component:** jellyfin config drift / monitoring / catalog · **Auditor:** svc:jellyfin

### UI337. GREEN: library actively growing — NOT a frozen poller (taxonomy 13 ruled out)
**Host:** nas · **Component:** jellyfin library scanner · **Auditor:** svc:jellyfin

### UI338. GREEN: Jellyfin library parity with Plex met (Jellyfin >= Plex on both movies and episodes)
**Host:** nas · **Component:** jellyfin vs Plex parity · **Auditor:** svc:jellyfin

### UI339. GREEN: kiwix config is inside the Hyper Backup->B2 set and the backup is fresh; ZIM corpus excluded by design
**Host:** nas · **Component:** kiwix backup leg · **Auditor:** svc:kiwix

### UI340. GREEN: full monitoring/catalog/homepage coverage — 3 consumer-grade checks, manifest entry, correct tile
**Host:** nas · **Component:** kiwix monitoring + catalog + homepage · **Auditor:** svc:kiwix

### UI341. GREEN: kiwix consumer end proven working end-to-end — real search + article fetch on 3 ZIMs, 34-book library, vhost path
**Host:** nas · **Component:** kiwix-serve (ZIM library) · **Auditor:** svc:kiwix

### UI342. VERIFIED end-to-end: kiwix Wikipedia consumer path (search + article body fetch)
**Host:** nas · **Component:** kiwix-serve (wikipedia_en_all_maxi_2026-02 ZIM) @ 192.168.10.4:8092 · **Auditor:** flow:offline-zim

### UI343. Backup leg confirmed: /volume1/docker in Hyper Backup 'S3 Backup enc' (config+SQLite DB covered)
**Host:** nas · **Component:** komga · **Auditor:** svc:komga

### UI344. GREEN: Komga comics/manga reader verified working end-to-end (page stream + OPDS + indexing)
**Host:** nas · **Component:** komga · **Auditor:** svc:komga

### UI345. No new content indexed since 2026-08-03 — upstream acquisition stall (fix-78); Komga side clean `known-issue`
**Host:** nas · **Component:** komga · **Auditor:** svc:komga

### UI346. UNPROBED: Uptime-Kuma monitor presence for Komga not verified
**Host:** nas · **Component:** komga · **Auditor:** svc:komga

### UI347. GREEN: nas all-interface listeners match baseline exactly (46/46), zero drift
**Host:** nas · **Component:** lan-exposure / listener-drift (fix-51) · **Auditor:** cross:lan-exposure

### UI348. Drift/backup/monitoring/catalog legs all clean
**Host:** nas · **Component:** lidarr · **Auditor:** svc:lidarr

### UI349. Lidarr music-automation consumer feature verified working end-to-end
**Host:** nas · **Component:** lidarr · **Auditor:** svc:lidarr

### UI350. UNPROBED: Uptime-Kuma monitor presence not separately confirmed
**Host:** nas · **Component:** lidarr · **Auditor:** svc:lidarr

### UI351. FIXED-but-open: extraction backlog stranded=0 and ~180GB redundant RARs reclaimed — recommend closing media-09 `known-issue`
**Host:** nas · **Component:** media extraction backlog (media-09) · **Auditor:** cross:open-queue-reality

### UI352. GREEN: no config drift; local interim image codified; resources nominal `known-issue`
**Host:** nas · **Component:** media-automation compose / repo mirror / resources · **Auditor:** svc:rreading-glasses

### UI353. UNPROBED depth note: Hyper Backup per-session RESULT read from Log Center DB not attempted (binary sqlite); consumer coverage otherwise adequate
**Host:** nas · **Component:** monitoring coverage (nas-dsm-tasks) · **Auditor:** svc:nas-dsm-tasks

### UI354. GREEN: Mylar3 comics-acquisition chain proven working end to end
**Host:** nas · **Component:** mylar3 · **Auditor:** svc:mylar3

### UI355. GREEN: fix-23/fix-53 credential-perms posture intact (config.ini 0600, dirs 755)
**Host:** nas · **Component:** mylar3 · **Auditor:** svc:mylar3

### UI356. No config drift; backup + monitoring + catalog all present
**Host:** nas · **Component:** mylar3 · **Auditor:** svc:mylar3

### UI357. UNPROBED: Uptime-Kuma monitor presence for mylar3
**Host:** nas · **Component:** mylar3 · **Auditor:** svc:mylar3

### UI358. Zero-throughput probe: idle-by-design, not frozen (poller alive today)
**Host:** nas · **Component:** mylar3 · **Auditor:** svc:mylar3

### UI359. beets ingest freshness is mtime-only — a daily import that errors every run stays green
**Host:** nas · **Component:** nas-beets-ingest-fresh check · **Auditor:** meta:nas-services · *skeptic-confirmed*

### UI360. GREEN: docker-health task running every 15min, all 10 monitored ports PASS, self-recovery intact, no storm
**Host:** nas · **Component:** nas-docker-health (DSM task id=5) · **Auditor:** svc:nas-dsm-tasks

### UI361. GREEN verified: health.env is 600 root:root (fix-23 M7 regression file)
**Host:** nas · **Component:** nas-health-env-perms · **Auditor:** meta:secrets

### UI362. GREEN verified: mylar3 container entrypoint sets umask 077 (fix-53 structural fix intact)
**Host:** nas · **Component:** nas-mylar3-umask-guard · **Auditor:** meta:secrets

### UI363. GREEN: four pinned baselines verified live, all match their expect strings exactly
**Host:** nas · **Component:** nas-timezone-eastern / nas-md-arrays-healthy / nas-syslog-geo-filter-present / nas-adguard-client-attribution · **Auditor:** meta:nas-host

### UI364. UNPROBED: two NAS checks not run live (read-only + light-touch mandate)
**Host:** nas · **Component:** nas-worldwritable-sweep, nas-ha-backup-acl · **Auditor:** meta:secrets

### UI365. Backup leg: Plex appdata is excluded from off-site Hyper Backup by documented design (regenerable media tier); HB itself is running fresh
**Host:** nas · **Component:** plex-dsm · **Auditor:** svc:plex-dsm

### UI366. Plex media server verified working end-to-end for its consumer (all 11 consumer checks + 3 edge checks green, library fresh, newest item is a real playable file)
**Host:** nas · **Component:** plex-dsm · **Auditor:** svc:plex-dsm

### UI367. UNPROBED: Uptime-Kuma monitor presence for Plex (secondary — verification runner already provides 14 checks)
**Host:** nas · **Component:** plex-dsm · **Auditor:** svc:plex-dsm

### UI368. GREEN: Prowlarr indexer-management + search consumer path proven working end-to-end
**Host:** nas · **Component:** prowlarr (media-automation compose, :9696) · **Auditor:** svc:prowlarr

### UI369. GREEN re-verify: IPT imdbid backlog-search chain is healthy end-to-end right now (100 hits, caps intact, indexer enabled, budget under limit)
**Host:** nas · **Component:** prowlarr -> IPTorrents ID-search consumer chain · **Auditor:** triage:iptorrents-idsearch-returns-results

### UI370. GREEN: Prowlarr->IPTorrents imdbid search chain verified working end to end — 100 items at today's run, Bitmagnet also still registered by name
**Host:** nas · **Component:** prowlarr / iptorrents-idsearch-returns-results · **Auditor:** meta:media-indexers

### UI371. GREEN: backup leg, catalog row, homepage tiles, coverage manifest all present
**Host:** nas · **Component:** prowlarr backup + catalog + homepage coverage · **Auditor:** svc:prowlarr

### UI372. Backup leg present via DSM Hyper Backup; fleet-wide immutability gap (fix-22) applies; exact include-list not enumerated `known-issue`
**Host:** nas · **Component:** radarr · **Auditor:** svc:radarr

### UI373. GREEN: radarr movie pipeline verified working end-to-end (state + throughput + Plex parity + bazarr)
**Host:** nas · **Component:** radarr · **Auditor:** svc:radarr

### UI374. Known-normal re-verified: bitmagnet RSS + automatic-search DISABLED in radarr (fix-50 deliberate demoted state) `known-issue`
**Host:** nas · **Component:** radarr · **Auditor:** svc:radarr

### UI375. Monitoring + catalog + drift confirmations clean (Kuma monitor UNPROBED)
**Host:** nas · **Component:** radarr · **Auditor:** svc:radarr

### UI376. GREEN: fix-50 demotion regression guard verified live — Bitmagnet RSS and automatic search disabled in both arrs
**Host:** nas · **Component:** radarr+sonarr / bitmagnet-demoted-interactive-only · **Auditor:** meta:media-indexers

### UI377. GREEN: metadata provider + postgres healthy end-to-end (token valid, cache warm, patch holding)
**Host:** nas · **Component:** rreading-glasses-hc + rreading-glasses-db · **Auditor:** svc:rreading-glasses

### UI378. GREEN: Scrutiny SMART-health hub verified end-to-end — 7/7 fleet disks fresh today, all SMART-passing
**Host:** nas · **Component:** scrutiny · **Auditor:** svc:scrutiny-hub

### UI379. GREEN: no config drift; catalog, coverage manifest, consumer check, and homepage tile all present/correct
**Host:** nas · **Component:** scrutiny · **Auditor:** svc:scrutiny-hub

### UI380. UNPROBED (partial): live Hyper Backup include-list not enumerable — but config is git-reconstitutable and runtime state is disposable
**Host:** nas · **Component:** scrutiny · **Auditor:** svc:scrutiny-hub

### UI381. Fleet SMART health monitoring verified working end-to-end — 7 disks, all 3 collectors fresh today, zero failures
**Host:** nas · **Component:** scrutiny (glue-10 sys-disk-smart-health) · **Auditor:** flow:disk-smart

### UI382. GREEN (re-verified): all NAS app secret configs are 600 owner-only + health.env 600 root:root
**Host:** nas · **Component:** secrets perms · **Auditor:** cross:secrets-hygiene

### UI383. GREEN: no config drift, backed up, monitored, cataloged; rshared boot-persistence armed
**Host:** nas · **Component:** shelfmark · **Auditor:** svc:shelfmark

### UI384. GREEN: shelfmark healthy 12d + MAM→CWA-ingest path proven intact (mount rshared, /books writable, orchestrator running)
**Host:** nas · **Component:** shelfmark · **Auditor:** svc:shelfmark

### UI385. UNPROBED: search-results consumer UI could not be driven read-only (auth-gated SPA; login + grab out of scope)
**Host:** nas · **Component:** shelfmark · **Auditor:** svc:shelfmark

### UI386. GREEN: MAM session valid, no re-auth storm (cookie lives in Prowlarr, indexer authenticating fresh today)
**Host:** nas · **Component:** shelfmark / prowlarr-MAM · **Auditor:** svc:shelfmark

### UI387. Chain is demand-driven and currently quiescent — most recent proven grab is 2026-07-28 (not breakage)
**Host:** nas · **Component:** shelfmark download orchestrator (bmig-06) · **Auditor:** flow:shelfmark-mam

### UI388. GREEN: Sonarr TV-automation consumer chain verified working end-to-end (throughput + Plex coverage + state + drift + backup + catalog + monitoring)
**Host:** nas · **Component:** sonarr · **Auditor:** svc:sonarr

### UI389. Related download/request-layer rot touching Sonarr series (cross-lane, known fix-25/fix-26) `known-issue`
**Host:** nas · **Component:** sonarr · **Auditor:** svc:sonarr

### UI390. GREEN: soularr Lidarr↔slskd bridge verified working end-to-end
**Host:** nas · **Component:** soularr · **Auditor:** svc:soularr

### UI391. GREEN: mini soularr-denylist-reconcile unit is healthy; the failing 'soularr' audit check is the separate NAS backlog (fix-40) `known-issue`
**Host:** nas · **Component:** soularr (NAS app) vs soularr-denylist-reconcile (mini unit) — disambiguation · **Auditor:** svc:mini-host-units

### UI392. GREEN: coverage, consumer-grade checks, backup leg, catalog, and config all correct
**Host:** nas · **Component:** soularr — monitoring / catalog / backup / drift posture · **Auditor:** svc:soularr

### UI393. GREEN: Stash consumer feature proven end-to-end (browse + stream + DB)
**Host:** nas · **Component:** stash · **Auditor:** svc:stash

### UI394. GREEN: Stash serves existing library (3232 scenes) via authenticated GraphQL
**Host:** nas · **Component:** stash · **Auditor:** flow:adult-whisparr-stash

### UI395. GREEN: Stash app-state (DB+blobs+config) is inside the Hyper Backup -> B2 set
**Host:** nas · **Component:** stash (backup leg) · **Auditor:** svc:stash

### UI396. Log sweep since 2026-08-02: clean except 3 transient SQLite locks + 69 benign 404s
**Host:** nas · **Component:** stash (logs) · **Auditor:** svc:stash

### UI397. GREEN: monitoring coverage present and consumer-grade
**Host:** nas · **Component:** stash (monitoring) · **Auditor:** svc:stash

### UI398. Confirmed known-DEFERRED: strategywiki ZIM absent, blocked-mode check green (expected) `known-issue`
**Host:** nas · **Component:** strategywiki ZIM (lai-15) — openZIM offline library · **Auditor:** flow:offline-zim

### UI399. UNPROBED: NAS-side /volume1/manga CBZ backup coverage not verified
**Host:** nas · **Component:** suwayomi · **Auditor:** svc:suwayomi

### UI400. VERIFIED: Syncthing no-cloud mesh fully direct end-to-end — game-saves 100% on rig, zero relay, watchers live
**Host:** nas · **Component:** syncthing (NAS hub, foss-03 / game-12) · **Auditor:** flow:syncthing-mesh

### UI401. GREEN: no-cloud sync mesh proven end-to-end — both peers direct LAN, folders idle/error-free, game-saves fresh
**Host:** nas · **Component:** syncthing (hub) · **Auditor:** svc:syncthing-hub

### UI402. Backup leg live: /volume1/docker/syncthing under the 'docker' Hyper Backup share; job ran last night `known-issue`
**Host:** nas · **Component:** syncthing backup leg (Hyper Backup -> B2) · **Auditor:** svc:syncthing-hub

### UI403. GREEN: live compose == repo mirror, tiny footprint
**Host:** nas · **Component:** syncthing config / drift + resources · **Auditor:** svc:syncthing-hub

### UI404. GREEN: clean log sweep since 2026-08-02 — no crash loop, no retry storm, no NUL corruption
**Host:** nas · **Component:** syncthing logs / stability · **Auditor:** svc:syncthing-hub

### UI405. GREEN: consumer-grade monitoring, catalog row, and Homepage tile all present and correct
**Host:** nas · **Component:** syncthing monitoring + catalog + homepage · **Auditor:** svc:syncthing-hub

### UI406. GREEN: 14 DSM scheduled tasks enumerated; all lane-relevant tasks enabled and crontab-wired
**Host:** nas · **Component:** synoschedule task inventory · **Auditor:** svc:nas-dsm-tasks

### UI407. GREEN: NAS unpackerr extractor proven working end-to-end for the arr stack
**Host:** nas · **Component:** unpackerr (container) · **Auditor:** svc:unpackerr

### UI408. GREEN: NAS unpackerr container is the real, healthy extractor and is unaffected by the mini host zombie `known-issue`
**Host:** nas · **Component:** unpackerr NAS container (the real extractor) · **Auditor:** triage:unpackerr-host-retired

### UI409. GREEN: unpackerr [[whisparr]] block correctly wired and actively polling (starved, not broken)
**Host:** nas · **Component:** unpackerr [[whisparr]] block · **Auditor:** flow:adult-whisparr-stash

### UI410. File summary: 8 enabled checks, 7 consumer-grade, 1 intermediate, 0 liveness-only, 0 disabled; integrity fully clean
**Host:** nas · **Component:** verification/checks.d/nas-host.yaml · **Auditor:** meta:nas-host

### UI411. fix-35 nas-immich-mobile-paired disable rationale HOLDS — retired proxy, superseded by an active outcome check `known-issue`
**Host:** nas · **Component:** verification/nas-immich-mobile-paired (nas-services.yaml) · **Auditor:** triage:skips

### UI412. GREEN: whisparr up 12d, healthy, no drift, backed up, cataloged, tile present
**Host:** nas · **Component:** whisparr / service health + wiring · **Auditor:** svc:whisparr

### UI413. GREEN: both game-saves checks verified working end to end live — mesh 26/26 files, rig 100%, backup fired tonight and propagated
**Host:** nas + rig · **Component:** verification/checks.d/game-saves.yaml · **Auditor:** meta:game-saves

### UI414. Audiobooks->iPod chain verified working end-to-end: ABS libraries serve real items, rig RO-CIFS + daily stage healthy and fresh
**Host:** nas+rig · **Component:** Audiobookshelf + iPod ABS staging pipeline (read-16 / read-19) · **Auditor:** flow:audiobooks-ipod

### UI415. VERIFIED e2e: MAM grab reaches CWA library, seed-preserving; fragile mount-propagation anti-drift point holds live
**Host:** nas+seedbox · **Component:** shelfmark / MAM / seedbox rslave mount / CWA ingest (bmig-06) · **Auditor:** flow:shelfmark-mam

### UI416. sync.yaml meta-audit: 3 checks, all consumer/intermediate, all pass live, zero integrity defects
**Host:** nas,mini · **Component:** verification/checks.d/sync.yaml (foss-03 Syncthing mesh) · **Auditor:** meta:sync

### UI417. secrets.yaml meta-audit: 6 checks, all enabled, no liveness decay
**Host:** nas/mini · **Component:** verification/checks.d/secrets.yaml · **Auditor:** meta:secrets

### UI418. File summary: 15 checks — 6 consumer / 6 intermediate / 3 liveness / 0 disabled; integrity clean; every live-verifiable baseline re-verified and HOLDS
**Host:** repo · **Component:** checks.d/alerting.yaml (file summary) · **Auditor:** meta:alerting

### UI419. File summary: 13 checks, 0 disabled — 4 consumer / 8 intermediate / 1 liveness; integrity clean except 5 dead runbook refs; 12/13 passing today
**Host:** repo · **Component:** checks.d/backups.yaml (whole file) · **Auditor:** meta:backups

### UI420. File summary: 2 checks — 1 consumer-grade, 1 intermediate, 0 liveness-only, 0 disabled
**Host:** repo (foss-setup) · **Component:** verification/checks.d/game-saves.yaml · **Auditor:** meta:game-saves

### UI421. GREEN: AMP MinecraftCross01 backups fresh + ReplacePolicy correct (H10 root cause avoided)
**Host:** rig · **Component:** AMP LocalFileBackupPlugin · **Auditor:** flow:game-servers

### UI422. GREEN: AMP hourly world zip fresh + non-DoNothing policy; ludusavi timer alive + saves 100% on NAS hub
**Host:** rig · **Component:** AMP game-server backups + ludusavi->syncthing mesh (fix-34 / game-12) · **Auditor:** flow:backups-restore-drill

### UI423. VERIFIED end-to-end: `fast` completion via opencode key returns non-empty content (closes the documented gap)
**Host:** rig · **Component:** Continue.dev -> LiteLLM (remote-ai-coding consumer inference) · **Auditor:** flow:remote-ai-coding

### UI424. UNPROBED: Continue.dev IDE end not reachable from audit host; backend coding lane is up
**Host:** rig · **Component:** Continue.dev IDE client (VSCodium) · **Auditor:** flow:ai-chat-serving

### UI425. VERIFIED: ES-DE on rig reads the same NAS ROM library via ~/ROMs symlinks, all cores present
**Host:** rig · **Component:** ES-DE / RetroArch launcher over NAS CIFS symlinks · **Auditor:** flow:retro

### UI426. opencode key scope = FULL catalog (broad); per-key scoping enforced (verify key + OWUI key correctly denied)
**Host:** rig · **Component:** LiteLLM per-key model scoping · **Auditor:** flow:remote-ai-coding

### UI427. GREEN: virtual-key completions on utility AND fast serve real content; VRAM yields
**Host:** rig · **Component:** LiteLLM virtual-key gateway (:4000) -> llama-swap lanes; GPU yield · **Auditor:** flow:ai-chat-serving

### UI428. UNPROBED: fresh in-OWUI single-completion grounding (REST path is websocket-limited)
**Host:** rig · **Component:** OWUI 0.11 chat completions REST vs websocket native-tool execution · **Auditor:** flow:ai-web-search

### UI429. GREEN: 3-way chat bake-off proven end-to-end — identical prompt+toolbelt, all three complete grounded at max_tokens 32768
**Host:** rig · **Component:** OWUI 3-way chat bake-off (chat / chat-q38-trial / chat-gemma-26b-trial) · **Auditor:** flow:chat-bakeoff

### UI430. GREEN: rig↔mini clock offset is 0s right now; Linux RTC/NTP healthy (fix-75 is the Windows dual-boot leg only) `known-issue`
**Host:** rig · **Component:** RTC / clock (fix-75, SM33) · **Auditor:** svc:host-rig

### UI431. Image-gen consumer path verified wired end-to-end through the arbiter (terminal gen the only unprobed leg)
**Host:** rig · **Component:** ai-image-gen chain (marinara/lumiverse -> gpu-arbiter:8189 -> ComfyUI) · **Auditor:** flow:ai-image-gen

### UI432. Every rig host timer is enabled, firing on schedule, and exiting 0 with fresh last-runs — verified end to end
**Host:** rig · **Component:** all rig timer-services (12 active + moondeckbuddy daemon) · **Auditor:** svc:rig-host-timers

### UI433. AMP game panel + Minecraft server PROVEN working end-to-end (panel, API, live SLP)
**Host:** rig · **Component:** amp · **Auditor:** svc:amp

### UI434. AMP state is inside a fresh restic backup set; monitoring/catalog/homepage all present
**Host:** rig · **Component:** amp · **Auditor:** svc:amp

### UI435. Container logs clean since 2026-08-02 — no crash/auth/retry-storm; one cosmetic APK-repo DNS warning at boot
**Host:** rig · **Component:** amp · **Auditor:** svc:amp

### UI436. Hourly backup subsystem healthy — fresh zips, policy=ReplaceOldest (H10/fix-34 regression holds) `known-issue`
**Host:** rig · **Component:** amp · **Auditor:** svc:amp

### UI437. GREEN: streaming control plane ready (Apollo serverinfo + session + MoonDeck TLS)
**Host:** rig · **Component:** apollo (sunshine) + moondeckbuddy · **Auditor:** flow:game-servers

### UI438. UNPROBED: actual Moonlight/MoonDeck video stream is a human leg
**Host:** rig · **Component:** apollo/moondeck streaming (video plane) · **Auditor:** flow:game-servers

### UI439. Backup + monitoring legs confirmed present for the rig agent
**Host:** rig · **Component:** beszel-agent · **Auditor:** svc:beszel-agent-rig

### UI440. Config matches repo mirror (no drift); .env vault-derived and correctly uncommitted
**Host:** rig · **Component:** beszel-agent · **Auditor:** svc:beszel-agent-rig

### UI441. VERIFIED WORKING END TO END: rig agent streaming fresh system+container telemetry to the Beszel hub
**Host:** rig · **Component:** beszel-agent · **Auditor:** svc:beszel-agent-rig

### UI442. Monitoring is consumer-grade and green; in coverage manifest
**Host:** rig · **Component:** bioclip-api · **Auditor:** svc:bioclip-api

### UI443. No live/repo drift; state backed up via restic
**Host:** rig · **Component:** bioclip-api · **Auditor:** svc:bioclip-api

### UI444. VERIFIED WORKING END TO END: live classify returns correct genus (Taraxacum) with full taxonomy, CPU by design
**Host:** rig · **Component:** bioclip-api · **Auditor:** svc:bioclip-api

### UI445. GREEN: image-gen backend proven working end-to-end at the deepest non-destructive depth — arbiter proxies, all documented models present, MCP tools live, both frontends wired to the arbiter
**Host:** rig · **Component:** comfyui + gpu-arbiter + comfyui-mcp (consumer probe) · **Auditor:** svc:comfyui-stack

### UI446. GREEN: all 3 containers stable (RestartCount=0, no OOM), logs clean since 2026-08-02, no config drift
**Host:** rig · **Component:** container state / logs / drift · **Auditor:** svc:comfyui-stack

### UI447. Zero config drift on priority units, unit files inside restic backup set + git, consumer-grade monitoring present (except nvidia-cdi)
**Host:** rig · **Component:** drift + backup + monitoring (checklist 4/6/7/8) · **Auditor:** svc:rig-host-timers

### UI448. es-de-sync is NOT a systemd unit on rig — lane list misnomer; ES-DE library is live NAS/RomM-sourced (retro-05 pass)
**Host:** rig · **Component:** es-de-sync (lane unit-list entry) · **Auditor:** svc:rig-host-timers

### UI449. export-manifests 'last ping 08-17 / 5+ days stale' is EXPECTED weekly cadence, NOT a failure — HC monitor is green
**Host:** rig · **Component:** export-manifests.timer/service (PRIORITY root-cause) · **Auditor:** svc:rig-host-timers

### UI450. GREEN: no rogue/nc-class listener on rig — all three drift ports attributed to legitimate owners (SM56 tripwire behaving correctly) `known-issue`
**Host:** rig · **Component:** fix-51 lan-listeners-drift-rig — re-verification · **Auditor:** triage:lan-listeners-drift-rig

### UI451. CONFIRMED live: fleet-mcp read-only fs trio (list_dir/find_files/disk_usage) and the 37-tool OWUI budget
**Host:** rig · **Component:** fleet-fs trio (lai-04 follow-on, ab54803) + owui-mcp-tools budget · **Auditor:** cross:docs-tracker-truth

### UI452. Backup leg confirmed: code + config + unit in rig restic (last run clean)
**Host:** rig · **Component:** fleet-mcp · **Auditor:** svc:fleet-mcp

### UI453. Log classification: 3 benign ASGI errors at deploy restart, 406s are the codified liveness probe
**Host:** rig · **Component:** fleet-mcp · **Auditor:** svc:fleet-mcp

### UI454. No drift: service tree clean at shipped commit, fully pushed to both remotes
**Host:** rig · **Component:** fleet-mcp · **Auditor:** svc:fleet-mcp

### UI455. Registry bookkeeping gap: fleet-mcp absent from service-catalog.yaml and any coverage manifest
**Host:** rig · **Component:** fleet-mcp · **Auditor:** svc:fleet-mcp · *skeptic-confirmed*

### UI456. fleet-mcp read-only inspection tools verified working end to end
**Host:** rig · **Component:** fleet-mcp · **Auditor:** svc:fleet-mcp

### UI457. read-only-by-design safety model confirmed in code (names/sizes/mtimes only, never file contents)
**Host:** rig · **Component:** fleet-mcp · **Auditor:** svc:fleet-mcp

### UI458. VERIFIED: fs trio returns names/metadata only, never file contents; read-only by design
**Host:** rig · **Component:** fleet-mcp fs trio (list_dir/find_files/disk_usage) · **Auditor:** flow:ai-ops-agent

### UI459. OBSERVATION: mcpo publishes 14 fleet tools but OWUI counts fleet=12 (2 not surfaced to chat)
**Host:** rig · **Component:** fleet-mcp tool exposure (mcpo vs OWUI) · **Auditor:** flow:ai-ops-agent

### UI460. UNPROBED: real image generation not exercised — GPU busy, authorized one-shot gen SKIPPED per rules
**Host:** rig · **Component:** gpu-arbiter :8189 /api/prompt (terminal image generation) · **Auditor:** flow:ai-image-gen

### UI461. GREEN: no failed units / crash-loops, root+/home RW-proven, disk 38%, GPU free by day, and the host's consumer features answer end-to-end
**Host:** rig · **Component:** host integrity + AI/game consumer endpoints · **Auditor:** svc:host-rig

### UI462. UNPROBED (by design): physical iPod libgpod push not exercised -- iPod not mounted, manual human hop passes by design
**Host:** rig · **Component:** iPod Classic libgpod push (final hop) · **Auditor:** flow:audiobooks-ipod

### UI463. UNPROBED: actual end-to-end image generation not exercised (owned by chain 21; heavy model load out of read-only scope)
**Host:** rig · **Component:** image generation execution path · **Auditor:** svc:comfyui-stack

### UI464. immich-ml has no restic-backed state by design; config recoverable from git mirror, weights re-downloadable
**Host:** rig · **Component:** immich-ml backup posture · **Auditor:** svc:immich-ml-rig

### UI465. GREEN: Immich ML consumer feature proven end-to-end on both backends; timers, versions, config, monitoring all correct
**Host:** rig · **Component:** immich-ml-rig / immich smart search · **Auditor:** svc:immich-ml-rig

### UI466. Known-normal: immich-ml Exited(143) by day is the designed 01-07 EDT GPU window, not a fault `known-issue`
**Host:** rig · **Component:** immich_machine_learning (night-window GPU gate) · **Auditor:** svc:host-rig

### UI467. GREEN: probe verified end to end live — stage healthy, no repo/live drift, producer dead-man up
**Host:** rig · **Component:** ipod-abs-stage-fresh · **Auditor:** meta:ipod-abs-sync

### UI468. Container state + logs clean since 2026-08-02 (no crash loop, no retry storm, no errors)
**Host:** rig · **Component:** kokoro · **Auditor:** svc:kokoro

### UI469. Kokoro TTS consumer path verified end-to-end (synthesis + OWUI voice round-trip)
**Host:** rig · **Component:** kokoro · **Auditor:** svc:kokoro

### UI470. No config drift; monitored, cataloged; stateless so no restic data leg required
**Host:** rig · **Component:** kokoro · **Auditor:** svc:kokoro

### UI471. CONFIRMED live: OWUI is 0.11.0, healthy, and serving at ai.tabaska.us
**Host:** rig · **Component:** lai-21 OpenWebUI 0.11.0 · **Auditor:** cross:docs-tracker-truth

### UI472. CONFIRMED live: Unsloth Studio e2e green (web UI + llama-swap lane + MCP tools) — service works, only its docs legs lag
**Host:** rig · **Component:** lai-28 Unsloth Studio · **Auditor:** cross:docs-tracker-truth

### UI473. GREEN: zero rogue listeners on rig — live all-interface set is exactly deployed-baseline + the 3 attributed sanctioned ports; drift unchanged since 08-18; mini and NAS baselines clean; clocks verified in sync `known-issue`
**Host:** rig · **Component:** lan-listener drift tripwire (fix-51) · **Auditor:** triage:lan-listeners-drift-rig

### UI474. CONSUMER PROVEN: virtual-key (DB-auth) completion returns non-empty grounded content end-to-end
**Host:** rig · **Component:** litellm · **Auditor:** svc:litellm

### UI475. Monitoring + catalog + coverage correct (mandate 2 satisfied); no dedicated homepage tile by design
**Host:** rig · **Component:** litellm · **Auditor:** svc:litellm

### UI476. No config drift; state inside restic backup set
**Host:** rig · **Component:** litellm · **Auditor:** svc:litellm

### UI477. State + logs healthy: no crash loop, no auth rot, no retry storm since 2026-08-02
**Host:** rig · **Component:** litellm · **Auditor:** svc:litellm

### UI478. DB fresh, not frozen (taxonomy 13 clear) + resources nominal
**Host:** rig · **Component:** litellm-db · **Auditor:** svc:litellm

### UI479. Benign recurring proxy connection-refused during swap windows (not a storm, not a broken lane)
**Host:** rig · **Component:** llama-swap · **Auditor:** svc:llama-swap

### UI480. Single resolved qwen3.8-27b 'exited prematurely' cluster on 2026-08-18 (night VRAM contention, known-normal)
**Host:** rig · **Component:** llama-swap · **Auditor:** svc:llama-swap

### UI481. llama-swap consumer path verified working end-to-end (day-window, live)
**Host:** rig · **Component:** llama-swap · **Auditor:** svc:llama-swap

### UI482. Known-normal: 63 llama-server coredumps clustered on Aug 06 (dev/VRAM contention), sporadic since; palworld SIGSEGV ~weekly but container healthy `known-issue`
**Host:** rig · **Component:** llama-swap / llama-server + palworld (coredumps) · **Auditor:** svc:host-rig

### UI483. All 12 non-iptorrents checks added since baseline PASS tonight; 6 baseline fails recovered incl. the Aug-6 CRIT arr-grabbed-not-imported `known-issue`
**Host:** rig · **Component:** local-AI stack + baseline recoveries (green confirmations) · **Auditor:** triage:baseline-delta

### UI484. Expected log noise — do NOT re-file: SSRF notification-refused + ACM paywall PDF 403s
**Host:** rig · **Component:** local-deep-research · **Auditor:** svc:local-deep-research

### UI485. GREEN: cited deep-research consumer feature proven end-to-end (35 sources) — SearXNG+coder-strong chain live
**Host:** rig · **Component:** local-deep-research · **Auditor:** svc:local-deep-research

### UI486. UNPROBED: Uptime-Kuma monitor presence for LDR not individually verified
**Host:** rig · **Component:** local-deep-research · **Auditor:** svc:local-deep-research

### UI487. VERIFIED e2e: LDR completes cited SearXNG+coder-strong research runs, retrievable at the consumer end
**Host:** rig · **Component:** local-deep-research (ldr.tabaska.us, rig:5000, task lai-08) · **Auditor:** flow:local-deep-research

### UI488. GREEN: game-save backup chain fresh and fully replicated
**Host:** rig · **Component:** ludusavi + syncthing game-saves mesh · **Auditor:** flow:game-servers

### UI489. VERIFIED (adjacent): game-saves Syncthing mesh 100% replicated + ludusavi backup timer healthy
**Host:** rig · **Component:** ludusavi game-saves mesh (adjacent) · **Auditor:** flow:retro

### UI490. GREEN: lumiverse consumer path verified end-to-end (vhost gate + LLM key + image gen)
**Host:** rig · **Component:** lumiverse · **Auditor:** svc:lumiverse

### UI491. No config drift: compose digest pin == running image, repo clean
**Host:** rig · **Component:** lumiverse · **Auditor:** svc:lumiverse

### UI492. UNPROBED: live RP chat-completion round-trip through lumiverse's own virtual key not forced (day-window GPU contention)
**Host:** rig · **Component:** lumiverse · **Auditor:** svc:lumiverse

### UI493. GREEN: marinara/lumiverse connections verified functional end-to-end (arbiter alias resolves + answers) `known-issue`
**Host:** rig · **Component:** marinara + lumiverse in-app connections (ai-01 consumer end) · **Auditor:** triage:rig-marinara-connections

### UI494. GREEN: comfyui-arbiter:8189 alias reachable from inside marinara; ComfyUI + all 3 models loaded
**Host:** rig · **Component:** marinara -> gpu-arbiter image-gen path · **Auditor:** svc:marinara

### UI495. GREEN: primary RP-chat consumer path proven working end to end
**Host:** rig · **Component:** marinara LLM RP chat (LiteLLM Creative connection) · **Auditor:** svc:marinara

### UI496. GREEN: marinara data volume inside a verified nightly restic set `known-issue`
**Host:** rig · **Component:** marinara backup leg (restic -> Backblaze B2) · **Auditor:** svc:marinara

### UI497. GREEN: container healthy, no restart/crash loop, logs clean since 2026-08-02
**Host:** rig · **Component:** marinara container state + logs · **Auditor:** svc:marinara

### UI498. UNPROBED: real image generation not executed (deliberate blind spot + read-only mandate)
**Host:** rig · **Component:** marinara image generation (end-to-end pixels) · **Auditor:** svc:marinara

### UI499. GREEN: coverage manifest, catalog row, and homepage tile all present and correct
**Host:** rig · **Component:** marinara monitoring / catalog / homepage · **Auditor:** svc:marinara

### UI500. Config drift-free and backed up (restic + dual git remote); monitoring + catalog in place
**Host:** rig · **Component:** mcpo · **Auditor:** svc:mcpo

### UI501. Log sweep since 08-02: 52 errors, all bounded/caller-side, 0 in last 24h
**Host:** rig · **Component:** mcpo · **Auditor:** svc:mcpo

### UI502. mcpo tool bridge verified working end-to-end for its OWUI consumers
**Host:** rig · **Component:** mcpo · **Auditor:** svc:mcpo

### UI503. GREEN: Minecraft Bedrock public join path proven (RakNet over playit UDP)
**Host:** rig · **Component:** minecraft-bedrock / playit UDP · **Auditor:** flow:game-servers

### UI504. GREEN: Minecraft Java public join path proven end-to-end
**Host:** rig · **Component:** minecraft-java / playit / AMP MinecraftCross01 · **Auditor:** flow:game-servers

### UI505. UNPROBED: nvidia-cdi-refresh reboot-survival — unit correctly armed, but cannot be exercised read-only (no reboot since install) `known-issue`
**Host:** rig · **Component:** nvidia-cdi-refresh.service (fix-81) · **Auditor:** svc:rig-host-timers

### UI506. Clean logs + healthy dead-man + backup leg confirmed (config in B2 snapshot)
**Host:** rig · **Component:** ollama-shim · **Auditor:** svc:ollama-shim

### UI507. UNPROBED: HA's own vantage into rig:11434 (HA is LAN-only, SSH refused)
**Host:** rig · **Component:** ollama-shim · **Auditor:** svc:ollama-shim

### UI508. VERIFIED WORKING END TO END: HA Assist conversation + direct llama3.2:3b generate through rig ollama shim
**Host:** rig · **Component:** ollama-shim · **Auditor:** svc:ollama-shim

### UI509. Adjacent rig-AI check fails are KNOWN baseline, not OWUI defects `known-issue`
**Host:** rig · **Component:** open-webui · **Auditor:** svc:open-webui

### UI510. GREEN: Open-WebUI consumer stack proven working end-to-end
**Host:** rig · **Component:** open-webui · **Auditor:** svc:open-webui

### UI511. GREEN: backup leg proven — OWUI volume in latest off-site restic snapshot
**Host:** rig · **Component:** open-webui · **Auditor:** svc:open-webui

### UI512. GREEN: model roster correct — chat lanes present, removed coder lanes absent, no drift
**Host:** rig · **Component:** open-webui · **Auditor:** svc:open-webui

### UI513. GREEN: monitoring, coverage, catalog, and Homepage tile all present & consumer-grade
**Host:** rig · **Component:** open-webui · **Auditor:** svc:open-webui

### UI514. Intermittent per-chat file-upload embedding failures (chromadb 'Collection does not exist')
**Host:** rig · **Component:** open-webui · **Auditor:** svc:open-webui · *skeptic-confirmed*

### UI515. VERIFIED end-to-end: openzim-mcp multi-term zim_search + zim_get read-discipline on chunked gamefaqs ZIM (cap live, paging signposted)
**Host:** rig · **Component:** openzim-mcp 2.5.5 via mcpo @ 192.168.10.12:8000/openzim/ → NAS zim CIFS RO mount (gamefaqs_en_all_2020-03 chunked ZIM) · **Auditor:** flow:offline-zim

### UI516. UNPROBED: reranker=engaged marker not observable via the mcpo zim_search JSON response
**Host:** rig · **Component:** openzim-mcp reranker extra (fastembed cross-encoder) via mcpo zim_search · **Auditor:** flow:offline-zim

### UI517. VERIFIED e2e: rig ai-ops-agent chain works end-to-end (OWUI/ops-agent -> mcpo -> fleet-mcp)
**Host:** rig · **Component:** ops-agent / fleet-mcp / mcpo · **Auditor:** flow:ai-ops-agent

### UI518. Backup leg confirmed: app-level hourly tar.gz (fresh) + restic->Backblaze B2 covering /opt (last-success today)
**Host:** rig · **Component:** palworld · **Auditor:** svc:palworld

### UI519. GREEN: Palworld REST proven live; 9 restarts triaged as HISTORICAL, not an active crash loop
**Host:** rig · **Component:** palworld · **Auditor:** flow:game-servers

### UI520. GREEN: Palworld dedicated server verified working end-to-end (live player, sim advancing, saves+backups fresh)
**Host:** rig · **Component:** palworld · **Auditor:** svc:palworld

### UI521. Log hygiene: 238k mostly-benign REST-access lines + 259 'Failed to flush log to FIFO' warnings (cosmetic, not a retry storm)
**Host:** rig · **Component:** palworld · **Auditor:** svc:palworld

### UI522. Monitoring + catalog + homepage coverage all present (consumer-grade, not liveness-only)
**Host:** rig · **Component:** palworld · **Auditor:** svc:palworld

### UI523. VERIFIED working end-to-end: Plant Scout consumer chain proven hop-by-hop
**Host:** rig · **Component:** plant-scout (bioclip-api + OWUI chat-vision + identify_plant + Plant Scout preset) · **Auditor:** flow:plant-scout

### UI524. GREEN: playit public game tunnel proven working end-to-end (Java + Bedrock via 69.9.181.17)
**Host:** rig · **Component:** playit tunnel agent (public game access) · **Auditor:** svc:playit

### UI525. GREEN: playit-udp-guard timer active and healthy; Bedrock lane verified unaffected end-to-end `known-issue`
**Host:** rig · **Component:** playit-udp-guard + Bedrock/Java public lanes · **Auditor:** triage:game-playit-udp-register-errors

### UI526. GREEN: playit-udp-guard healthy every 10 min, no config drift, backed up, and consumer-grade monitoring in place
**Host:** rig · **Component:** playit-udp-guard self-heal timer + backup + monitoring + drift · **Auditor:** svc:playit

### UI527. Consumer feature PROVEN working end-to-end (browser MCP for OWUI agentic browsing)
**Host:** rig · **Component:** playwright-mcp · **Auditor:** svc:playwright-mcp

### UI528. Monitoring, catalog, coverage, and backup all in place
**Host:** rig · **Component:** playwright-mcp · **Auditor:** svc:playwright-mcp

### UI529. No config drift: running image digest matches pinned compose; ai-tooling repo clean + pushed to both remotes
**Host:** rig · **Component:** playwright-mcp · **Auditor:** svc:playwright-mcp

### UI530. GREEN: rig backup leg proven fresh and drift-free (restic B2 snapshot <26h, byte-matches source, reboot-durable marker)
**Host:** rig · **Component:** restic -> B2 backup leg · **Auditor:** svc:host-rig

### UI531. UNPROBED: night rig-cuda CLIP encode path not directly exercised (day window, container deliberately down)
**Host:** rig · **Component:** rig immich_machine_learning night-window encode (rig-immich-ml-window, nas-32) · **Auditor:** flow:photos-ml

### UI532. GREEN: every hardcoded baseline in the check verified live and holds
**Host:** rig · **Component:** rig-esde-romm-library check baselines · **Auditor:** meta:retro-emulation

### UI533. Monitoring + catalog + no-drift confirmations all green
**Host:** rig · **Component:** scrutiny-collector · **Auditor:** svc:scrutiny-collector-rig

### UI534. VERIFIED WORKING E2E: all 3 rig NVMe SMART readings land fresh in the NAS Scrutiny hub, all SMART-passing
**Host:** rig · **Component:** scrutiny-collector · **Auditor:** svc:scrutiny-collector-rig

### UI535. Suwayomi manga acquisition chain verified working end to end
**Host:** rig · **Component:** suwayomi · **Auditor:** svc:suwayomi

### UI536. Syncthing rig node verified working end to end: game-saves 100% replicated to NAS hub over direct LAN (no relay)
**Host:** rig · **Component:** syncthing-rig · **Auditor:** svc:syncthing-rig

### UI537. natEnabled=True triggers STUN external-address resolution — benign, no cloud data path
**Host:** rig · **Component:** syncthing-rig · **Auditor:** svc:syncthing-rig

### UI538. rig syncthing config + game-saves are inside the succeeding restic->B2 backup set `known-issue`
**Host:** rig · **Component:** syncthing-rig backup leg · **Auditor:** svc:syncthing-rig

### UI539. All four consumer-grade syncthing checks pass in the audit-safe run; homepage tile present
**Host:** rig · **Component:** syncthing-rig monitoring · **Auditor:** svc:syncthing-rig

### UI540. GREEN: Unsloth Studio consumer chat proven end-to-end (login + qwen3.8-27b completion + DB config gate)
**Host:** rig · **Component:** unsloth-studio · **Auditor:** svc:unsloth-studio

### UI541. Mitigation verified: unsloth-studio is monitored end-to-end despite the stale coverage manifest — unsloth-studio-e2e passing tonight
**Host:** rig · **Component:** unsloth-studio · **Auditor:** triage:containers-manifest-rig

### UI542. Single startup-day SIGKILL of the studio process is the known LTX-validator OOM (by design), not a crash loop
**Host:** rig · **Component:** unsloth-studio · **Auditor:** svc:unsloth-studio

### UI543. VERIFIED e2e: Unsloth Studio login + External llama_cpp provider chat rides llama-swap qwen3.8-27b
**Host:** rig · **Component:** unsloth-studio · **Auditor:** flow:unsloth-studio

### UI544. File summary: 1 check, consumer-grade, no liveness decay, no disabled checks
**Host:** rig · **Component:** verification/checks.d/ipod-abs-sync.yaml · **Auditor:** meta:ipod-abs-sync

### UI545. File summary: 6 checks — 4 consumer, 2 intermediate, 0 liveness-only, 0 disabled; all 6 verified green live; integrity clean
**Host:** rig · **Component:** verification/checks.d/rig-host-stability.yaml · **Auditor:** meta:rig-host-stability

### UI546. Coverage note: no dedicated recurring verification check for the 3 chat bake-off lanes (only the coder lineup has a 'bake-off' check)
**Host:** rig · **Component:** verification/checks.d/rig.yaml — bake-off consumer coverage · **Auditor:** flow:chat-bakeoff

### UI547. rig.yaml audit summary — 32 checks, liveness cleanly paired with consumer probes, all green live except the 2 stale ai-01 conn checks
**Host:** rig · **Component:** verification/checks.d/rig.yaml (whole file) · **Auditor:** meta:rig

### UI548. GREEN: OWUI chat serving path verified end-to-end; coder lanes correctly absent
**Host:** rig+mini · **Component:** OWUI chat -> LiteLLM (openwebui key) -> llama-swap · **Auditor:** flow:ai-chat-serving

### UI549. Voice TTS->STT round-trip verified working end-to-end (consumer proven, fresh probe)
**Host:** rig+mini · **Component:** voice (Kokoro TTS + faster-whisper STT + OWUI audio, lai-10) · **Auditor:** flow:voice-tts-stt

### UI550. Manga+comics reading chain verified working end-to-end (Komga page-stream + OPDS + both acquisition feeders)
**Host:** rig+nas+mini · **Component:** komga / suwayomi / mylar3 (reading chain) · **Auditor:** flow:manga-comics

### UI551. GREEN: scripts match repo (no drift), crontab matches README manifest, coverage+catalog+homepage all present
**Host:** seedbox · **Component:** anti-drift / monitoring / catalog · **Auditor:** svc:seedbox-glue

### UI552. Deluge runtime state (label.conf, session.state) is not in any restic/HyperBackup set — only automation scripts are in git
**Host:** seedbox · **Component:** backup coverage / config-as-code · **Auditor:** svc:deluge

### UI553. GREEN: arr↔Deluge download/import chain proven working end-to-end
**Host:** seedbox · **Component:** deluge (arr download-client + import pipeline) · **Auditor:** svc:deluge

### UI554. GREEN: off-site torrent + Soulseek pipeline proven end-to-end
**Host:** seedbox · **Component:** deluge / slskd (consumer path) · **Auditor:** svc:host-seedbox

### UI555. 3 orphaned .torrent state files (148 in state/ vs 145 loaded) matching startup 'not in torrents loading list' warnings
**Host:** seedbox · **Component:** deluge state dir · **Auditor:** svc:deluge

### UI556. reaper .err carries an Aug-11 pyOpenSSL GEN_EMAIL traceback — transient, reaper healthy since
**Host:** seedbox · **Component:** deluge-reaper (cron 05:00) · **Auditor:** svc:host-seedbox

### UI557. GREEN: reaper healthy — daily runs through Aug 23, 0 eligible today, log clean; stale Aug 11 pyOpenSSL error not recurring
**Host:** seedbox · **Component:** deluge-reaper cron (torrent age>=14d) · **Auditor:** svc:seedbox-glue

### UI558. GREEN: 14d deluge reaper verified working end-to-end — self-clean is NOT broken (directly answers the audit's 'self-clean not working?' hypothesis) `known-issue`
**Host:** seedbox · **Component:** deluge-reaper.py (self-clean cron) · **Auditor:** triage:deluge-preimport-stuck

### UI559. Seedbox admin + retired ports all closed on its public IP
**Host:** seedbox · **Component:** edge / seedbox public lockdown · **Auditor:** flow:edge-dns

### UI560. Two hung Deluge client probe processes lingering since Aug02 (~3 weeks, 0:00 CPU)
**Host:** seedbox · **Component:** leftover probe processes · **Auditor:** svc:deluge

### UI561. slskd Soulseek daemon verified working end-to-end (Connected+LoggedIn, live throughput, consumer check green)
**Host:** seedbox · **Component:** slskd · **Auditor:** svc:slskd

### UI562. slskd state/config not in any backup set — by design (transient staging, config reproducible via install script)
**Host:** seedbox · **Component:** slskd-backup · **Auditor:** svc:slskd

### UI563. No config drift; monitoring, catalog, homepage tile, and exposure lockdown all correct
**Host:** seedbox · **Component:** slskd-drift-monitoring-catalog · **Auditor:** svc:slskd

### UI564. Log errors since Aug 02 are all normal Soulseek P2P churn — no retry storm, auth rot, or crash loop
**Host:** seedbox · **Component:** slskd-logs · **Auditor:** svc:slskd

### UI565. slskd update available 0.25.1.0 -> 0.26.0 (informational, no functional impact)
**Host:** seedbox · **Component:** slskd-version · **Auditor:** svc:slskd

### UI566. UNPROBED depth: auth keys clean (3x ED25519); backup = repo mirror (no root/restic by design)
**Host:** seedbox · **Component:** ssh auth posture / backup leg · **Auditor:** svc:host-seedbox

### UI567. GREEN: tailnet path + Deluge/slskd consumers proven end-to-end; quota, log, payload all healthy
**Host:** seedbox · **Component:** tailscaled + tailnet consumer path / quota / deluged log / payload audit · **Auditor:** svc:seedbox-glue

### UI568. File audit: 13 checks, 9 consumer-grade, 1 honest liveness tripwire, 0 disabled — integrity clean
**Host:** seedbox · **Component:** verification/checks.d/seedbox.yaml · **Auditor:** meta:seedbox

### UI569. Plex reachable from the public internet with the pinned server identity
**Host:** seedbox->nas · **Component:** edge / Plex remote access · **Auditor:** flow:edge-dns

### UI570. WAN attack surface minimal end-to-end: only 32400/Plex open from external vantage
**Host:** seedbox/mini · **Component:** edge / WAN exposure · **Auditor:** flow:edge-dns

### UI571. Crit check is liveness-only — HTTP 200 on HA root, no consumer-end probe `known-issue`
**Host:** url · **Component:** sys-home-assistant · **Auditor:** meta:system · *skeptic-confirmed*


---

## Appendix — refuted candidates (11)

> Candidates raised by a lane but dropped after adversarial verification with fresh probes. Logged for auditability.

- **nas/flow:movies-tv**: IPTorrents ID-search returns 0 items (verify-06) — Prowlarr caps quirk, not blocking grabs — _refuted:_ Root-cause mechanism refuted (check-bug/transient, not a defect). The finding blames a PERMANENT "Prowlarr caps quirk" (imdbid not translated -> indexer skipped), but the identical imdbid=tt0133093 search returns 100 items live right now and returned 100 this morning (per sibling #19) — a caps-translation quirk could never yield 100 items. The real cause is a transient NAS-IO-storm timeout: the fa
- **nas/flow:books-kobo**: Import drought: newest Calibre book is 2026-08-03 (~20 days), consistent with degraded metadata lookup — _refuted:_ The bare fact reproduces (newest book by timestamp = "Adrift" 2026-08-03, sole library /volume1/books/metadata.db, no wrong-vantage escape) but the FINDING — an "import drought" indicating "degraded metadata lookup / plausibly downstream of bmig-06 flakiness," flagged as a fault to watch — does not hold up. Refutation basis (operator-intent / known-normal quiet input, not a defect): (1) The CWA (c
- **rig/flow:ai-web-search**: openzim reranker in-band marker not surfaced through the mcpo structured-JSON path — _refuted:_ Wrong-vantage / check-bug: the auditor probed zim_search — a dedicated advanced tool that does NOT rerank at all (results have keys path/title/snippet only, no rerank_score; two live zim_search calls added ZERO reranker events to telemetry) — and generalized "no marker here" to "the tripwire can't be observed via the mcpo/openzim consumer path." Fresh probe on the tool that ACTUALLY reranks (simpl
- **nas/cross:coverage-tripwire**: rreading-glasses pair has liveness-only check and no Homepage/Kuma surface — _refuted:_ Check-bug-vs-real-breakage + operator-intent. The finding's core impact claim — a silently-degraded rreading-glasses metadata endpoint would pass its 200 check while returning empty metadata — is false: that exact failure mode is guarded by dedicated bmig-06 consumer-depth checks, not just the nas-rreading-glasses-hc liveness probe. metadata-search-canary does a real book/lookup through the rg-hc-
- **nas/cross:secrets-hygiene**: /volume1/docker is 0777 world-writable (fix-23 regression persists) — _refuted:_ known-normal DSM Synology-ACL quirk. The POSIX mode 777 is real and reproduces, but it is the DSM shared-folder display default (books/music/homes ALL show identical 777), not a docker-specific regression. The trailing "+" means the folder is ACL-managed, and on DSM the synoacl is authoritative over the POSIX bits. Fresh synoacltool probe shows everyone::allow:r-x---a-R-c--:fd-- = read+traverse ON
- **seedbox/triage:seedbox-extracted-reaped**: TANGENTIAL: separate 05:00 deluge queue reaper last logged a pyOpenSSL crash on Aug 11 (not the extracted reaper; does n — _refuted:_ Finding's raw facts (err mtime Aug 11 05:00, 4006B, crash traceback, crontab line) all reproduce, but its actual concern — reaper may be silently broken / not running — is false. It never checked the script's own stdout log. deluge-reaper.log shows successful runs EVERY day Aug 12-23 (incl. today 05:00), connecting to deluge and REMOVING eligible torrents. Aug 11 crash was from SYSTEM python OpenS
- **rig/meta:alerting**: severity=warn understates what the check guards — its own comment says failure means 'the fleet has NO off-mini pager' ( — _refuted:_ Operator-intent / by-design, and the notification-impact premise is materially wrong. (1) Raw facts hold — alert-offmini-deadman-armed is severity:warn (alerting.yaml L156), its comment does say the SH19 no-off-mini-pager line (L143-146), and alert-healthchecks-none-down is crit (L75). But (2) warn here is a deliberate, CONSISTENT policy: all four fix-63 alerting-plane-resilience checks (offmini-d
- **mini/meta:reading**: Supply-chain tamper tripwire is severity:warn — a TAG_REPOINTED fire (active tamper attempt on the pseudonymous fork ima — _refuted:_ Operator-intent + factually-wrong premise + self-refuting. (1) The headline claim "would not page" is false: in checks_runner.py the paging set page_new/transition is ALL new failures filtered only by acks, NOT by severity — a new warn failure of cwa-ghcr-tag-digest-drift sends an ntfy naming the check id ("NEW failures (N): <ids>"). Severity changes ONLY the ntfy Priority header ("high" if crit e
- **mini/svc:recyclarr**: No repo verification check asserts sync-content success; sole alert path is the self-hosted healthchecks dead-man — _refuted:_ Wrong vantage / incomplete-grep. The finding grepped checks.d for the literal string "recyclarr" and concluded the only repo coverage is alerting.yaml sec-03's dead-man COUNT (alert-healthchecks-checks-defined) plus a host-hygiene allowlist. It missed the sibling check in the same file/task: alert-healthchecks-none-down (alerting.yaml:66-78, enabled:true, severity:CRIT, task sec-03), which does NO
- **nas/svc:kiwix**: Private custom-built GameFAQs ZIM lives only on the unbacked-up single-disk /volume1/zim — rebuild-from-scrape is the on — _refuted:_ The finding's two severity-driving claims both fail a fresh cross-host probe. (1) "Lives only in /volume1/zim" is false: a byte-identical full copy of the ZIM (4648911784 bytes, matching the NAS file exactly) sits on rig at /home/btabaska/scratch/lai-14-gamefaqs/out/gamefaqs_en_all_2020-03.zim — on rig's own /dev/nvme2n1p2 (separate host, separate physical disk, 1.2T free), not the NAS single disk
- **nas/svc:mylar3**: Homepage tile is href-only; catalog notes claim an API-key widget — _refuted:_ Check-bug (wrong-key misread), not a real doc-vs-live discrepancy. The finding claims the live /api/services Mylar3 entry is href-only with no widget block, but a fresh probe (reproduced with the author's exact Host: home.tabaska.us header) shows the entry carries a plural widgets array containing a mylar-type widget (service_name Mylar3, hide_errors false, index 0). The author searched only for t

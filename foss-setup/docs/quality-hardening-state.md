# Quality-hardening workstream — state

**Started:** 2026-07-13 (btabaska personal Claude account taking over the homelab).
**Mandate (user):** the tracker/monitoring reports "green / 100%" but real features are broken in live use — a **quality/testing gap**, not just a backlog gap. Fix each broken stack **as a whole** with the loop: **diagnose fully → fix (repo-first) → validate the real end-to-end journey → write a regression test that fails if it breaks again.** Quality over speed. Treat existing "done"/green claims as *liveness*, not *correctness*. See memory [[monitoring-vs-reality-quality-gap]].

**User decisions in effect:**
- AI-stack SPOF (rig-only, no fallback) = **accepted** (not a task; only the HA-Assist endpoint fix #12 remains).
- NAS parity = **backlog/later**, no new spend now (#19).
- Credential rotations = **deferred** until the build phase is done; exposure accepted for velocity (#18).
- Network is **already VLAN-segmented** (Trusted/IoT/Cameras/Work/Guest + zone firewall + light device migration) — earlier "flat /24" read was wrong; #15 is a re-audit, not a build.

**Working style / access:**
- Secrets: `foss-setup/.handoff-secrets.yaml` (gitignored). Host sudo + HA token + Plex/Lidarr/etc. keys live there.
- mini has **passwordless sudo**; NAS sudo needs the vault password (`<vault: sudo.nas_password>`); NAS `docker` = `/usr/local/bin/docker`, `synoacltool` = `/usr/syno/bin/synoacltool`.
- Repo-first: edit `foss-setup/…`, deploy live, validate, commit to `origin` (GitHub `btabaska/home-config`) **and** `./foss-setup/scripts/docs/publish-deploy.sh` (subtree → forgejo `home/homelab`, hosts ansible-pull from it).
- Verification framework: checks in `foss-setup/verification/checks.d/*.yaml`, primitives in `verification/bin/`, deployed to mini `/opt/verification/`, env in mini `/etc/verification/env`, run hourly via `verification-quick`, page via ntfy. Validate each new check live **and negative-test it**.
- `scp` to the NAS fails (sftp closed) — deploy to NAS via base64-over-ssh. `scp` to mini works.
- `sqlite3` CLI is absent in some app containers (musicseerr) — read their DBs with the container's `python3`.

---

## Completed stacks (2026-07-13)

Each: fixed + validated end-to-end + hardened with a negative-tested regression check, committed to both remotes.

| Stack | Root cause | Fix | Regression check(s) | Commit |
|---|---|---|---|---|
| **Pinchflat → Plex** (#1, test #9) | `/volume1/youtube` share missing the `user:PlexMediaServer` ACL entry → Plex couldn't read it → 0 items despite 1363 files | `synoacltool -add` the ACE + `-enforce-inherit`; scan → 0→1363 items | `pinchflat-plex-visible` (crit, disk-vs-Plex coverage) + `plex-youtube-readable` (crit, ACL invariant) | `21020ba` / fj `69fa7f5` |
| **Libreseerr → CWA** (#2, test #7) | Readarr→CWA copy script trimmed paths with `xargs` → busybox xargs strips apostrophes → every apostrophe title dropped | pure-bash trim + normalized fallback in `scripts/media/readarr-copy-to-cwa-ingest.sh`; reprocessed 5 stuck books (CWA 52→57) | `readarr-cwa-copy-drops` (crit) + `cwa-ingest-not-stuck` (warn) | `e7d27b8` / fj `592c9c9` |
| **MusicSeerr requests** (#3, test #8) | 3 Owl City albums left `monitored:False` in Lidarr by a batch add edge case → phantom "Downloading 0%"; page/API were healthy | Lidarr monitor + AlbumSearch; 2 grabbed+imported, 1 (no release) monitored-and-waiting | `musicseerr-phantom-requests` (warn, request `downloading` while unmonitored in Lidarr) | `2ba35f8` / fj `cb39a8e` |

Memory written: [[nas-plex-share-acl]], [[libreseerr-edition-selection]] (extended), [[musicseerr-phantom-requests]], [[monitoring-vs-reality-quality-gap]].

**The reusable pattern that emerged (this IS the seed of the acceptance-test framework #5):** outcome-level checks that compare **producer output** (files on disk / requests made) to **consumer visibility** (items served in Plex/CWA/Navidrome), reading state directly (filesystem, app DB, downstream API) rather than trusting container liveness. All live in `checks.d/media.yaml`; each is negative-tested.

---

## Task board (19 tasks; IDs match the session task list)

**Done:** #1 Pinchflat→Plex · #2 Libreseerr→CWA · #3 MusicSeerr · #5 acceptance-test framework design doc (`wiki/docs/runbooks/acceptance-testing.md`) · #7 book acceptance test · #8 album acceptance test · #9 pinchflat acceptance test.

**Blocked on live Plex:** #6 movie/TV→Plex acceptance check and #10 done-audit — Plex on the NAS is returning **HTTP 503 to all clients** (metadata-analysis storm on §4/YouTube, triggered by today's 1363-item Pinchflat ingest; process up, worker pool saturated). Can't live-validate/negative-test a Plex journey while Plex 503s. **User decision 2026-07-13: let Plex drain on its own** (no restart). Resume when Plex serves 200 (re-check `pinchflat-plex-visible`). Memory [[plex-bulk-ingest-analysis-storm]].

**Automation:** the remaining work is broken into ordered handoff prompts in `docs/prompts/` and tracked by `docs/prompts/HANDOFF-QUEUE.md`. Paste `docs/prompts/00-MASTER.md` into a fresh session — it does the next eligible queue item, checks it off, commits, and stops; re-run to advance. `needs-user`/`collaborative` items pause the loop.

**Next up (recommended order):**
1. **#5 Design the e2e acceptance-test framework** — formalize the pattern above into a documented framework + journey catalog. *Prompt ready: `docs/prompts/01-acceptance-test-framework.md`.*
2. **#6 Acceptance test: movie/TV request → served in Plex** (blocked by #5).
3. **#10 Re-audit the 140/223 "done" for real correctness** (blocked by #6; treat green as liveness-only, re-verify user-facing services).

**Reliability / DR (P1–P2):** ✅ #11 HA backups (DONE 2026-07-13) · ✅ #12 HA-Assist endpoint (DONE 2026-07-13) · #13 close ansible backup SOPS gate (**BLOCKED [~]** — see below) · ✅ #14 verify NAS Tier-1→B2 nas-02 (**DONE 2026-07-13**).

**#14 (queue item 03, part 2) — DONE 2026-07-13:** re-probe resolved the doc contradiction in favor of reality — the NAS Tier-1 Hyper Backup → B2 task **"S3 Backup 1"** is alive and succeeding (target S3-compat `s3.us-east-005.backblazeb2.com`/`bucket-hyper-backup`/`TabaskaNAS_1.hbk`; selects `/backups /docker /docs /homes /photo` = **all shares that hold real data** — `vault`+`appdata` are empty 28K shells superseded by `/docker` (18G); last successful version **2026-07-12 19:28**, integrity check 07-11, smart-recycle rotation, notify on). **nas-02 closed** in `progress.json` (140→141) + `backup-restore.md` updated. New negative-tested dead-man **`nas-hyperbackup-b2-fresh`** (crit, 50h, `backups.yaml`) on the mtime of the client image cache's `last_version_inodedb` (rewritten only on a completed version; world-readable so the non-sudo runner user reads it) — deployed to mini `/opt/verification`, confirmed picked up by the daily `verification.service` sweep, negative-tested (fresh→ok; `-mmin -1` and a bogus path both →BAD). ✅ **Client-side encryption RESOLVED 2026-07-13:** the operator re-created the task with client-side encryption ON — **"S3 Backup enc"** → `TabaskaNAS_2.hbk`, `enable_data_encrypt=true` (+ TLS in transit); first full encrypted backup completed 13:45; the dead-man `nas-hyperbackup-b2-fresh` re-armed against the new cache (pass). Key in vault `hosts.nas.hyperbackup_password` (+ Bitwarden). The old unencrypted `S3 Backup 1` / `TabaskaNAS_1.hbk` was **deleted 2026-07-13** — only the encrypted task remains; the dead-man now tracks it exclusively.

**#13 (queue item 03, part 1) — BLOCKED [~] 2026-07-13:** the ansible `backup` role skips (no SOPS secret) so a rebuild wouldn't re-arm restic — but live probing showed the gap is deeper and closing it safely needs the user + is too risky for one autonomous pass on the **single off-site DR path**: (a) the role **diverged** from the curated live setup (live = `scripts/backup/restic-backup.sh` + `/etc/restic/env` + Healthchecks ping + ntfy + pre-backup DB dumps; role = a *different* inline unit) → seeding the secret naively **clobbers** live DR; (b) `sops`+`age` binaries are **missing on both hosts** (the `community.sops` lookup can't decrypt); (c) the **rig has no ansible at all** (pull path unvalidatable there); (d) the age-key **save is a user step**. Restic dead-man for mini+rig already exists and is live-FRESH (mini 17.7h / rig 13.8h) so the #13 harden is pre-satisfied. Full next-step plan in `docs/prompts/HANDOFF-QUEUE.md` item 03 + `03-dr-reproducibility.md`. Memory [[dr-reproducibility-gap]].

**#11/#12 (queue item 02) — DONE 2026-07-13:** re-probe showed HA backups were still eMMC-only (`hassio.local`), and HA Assist had **no** LLM agent at all (the "mini:4000 LiteLLM" target was always a phantom — LiteLLM/Ollama are rig-only). Fixed: (a) dedicated least-priv Synology SMB user `ha-backup` + Supervisor CIFS mount `nas_backups`→`//192.168.10.4/backups` (agent `hassio.nas_backups`), **daily 04:45 automatic ENCRYPTED backups to both agents, retention 3**; validated a triggered backup landed encrypted on the NAS (`/volume1/backups/…tar`, 7-member listable archive = restore path). Key in vault `hosts.ha.backup_password` (+ Bitwarden TODO). (b) HA native `ollama` integration → **rig Ollama `192.168.10.12:11434`**, agent `conversation.rig_ollama_assist` (llama3.2:3b); a live `/api/conversation/process` returned a real completion. Default pipeline left on the intent engine to preserve device control. New negative-tested checks in `ha.yaml`: `ha-backup-offsite-fresh` (crit dead-man) + `ha-assist-rig-llm-reachable` (warn). Stdlib HA WS client committed at `scripts/ha/haws.py`. Memory [[ha-control-plane]] updated.

**Infrastructure / planning (P3):** ✅ #15 network re-audit (**DONE 2026-07-13**) · #16 DNS tail dns-03/04/05 (unblocked by #15; needs-user UniFi UI) · ✅ #17 roadmap prune (**DONE 2026-07-13**, walked with the user).

**#17 (queue item 07) — DONE 2026-07-13 (roadmap prune, user-walked):** reconciled `progress.json` to real intent. **Closed 5** tracker-drift items verified live-done (ha-05 Hue [14 light entities], ha-11 HA backups [queue 02], ha-16 HomeKit Bridge [`HASS Bridge:21064` loaded], dns-04 DNS outage runbook+verify script, nas-00e NAS music mount `/mnt/nas/music`) → **141→146**. **Retired 7** (ha-03 HAOS-in-VM → superseded by HA Green; ha-17 LiteLLM fallback → AI-SPOF accepted; game-01 → AMP-on-rig; game-04 → playit; nas-06 2nd off-site; nas-03 Tier-2 HDD; nas-30 beets). **Deferred 4** (optional, no active plan): ha-08, ha-13, game-12, game-14. **Kept as planned:** docker-14, read-11 + all Bucket-D tracks. **ai-01 KEPT + EXPANDED** into its own initiative — a first-class local-AI SWE/Q&A build (OWUI + opencode, skills library, home-ops agents); scoping doc `docs/local-ai-build-plan.md`, **deep research commissioned**.

**#15 (queue item 04) — DONE 2026-07-13:** the "flat /24" model was already known-wrong; this re-audit **confirmed** the segmentation. The operator **confirmed the subnets + zone-firewall rules are implemented as directed and declined UniFi controller/SSH access**, so the router is not machine-audited. Fleet-side corroboration (no router touched): all six gateway SVIs answer (`192.168.{1,10,20,30,40,50}.1`) → Default/Trusted/IoT/Cameras/Work/Guest all exist; Trusted=192.168.10.0/24 (all managed hosts); IoT=192.168.20.0/24 (Hue `.20.100`); **Trusted→IoT allow verified** (Hue reachable). Corrected `configs/network/vlan-zone-firewall-plan.md` (subnets marked confirmed-real; appended a #16/#4 follow-up list) and memory [[mini-dhcp-lease-outage]] (mini static-IP **was applied 2026-07-10** — `dhcp4:false`, static fail-open DNS — so the 24h-lease outage class is closed; side effect: mini can't fleet-verify DHCP hand-out anymore). New negative-tested invariant `net-trusted-to-iot-reachable` (warn, `network.yaml`). Router-internal specifics (exact ZBF policy order/`any`-scope leftovers, per-VLAN mDNS-proxy toggles, IGMP-snooping state) are operator-confirmed only → precise follow-ups feed #16 and #4. **#4 gate:** which VLAN the HomePods are on (Trusted=native mDNS with HA; IoT=needs mDNS proxy for `_hap._tcp.local` + IGMP off + firewall allow).

**Re-sequenced:** #4 HomePod ↔ HA HomeKit hub — was behind #15; **#15 now done so #4 is unblocked** (queue item 06, needs-user): the map exists, remaining gate = which VLAN the HomePods are on + mDNS-proxy/IGMP state (operator UI) + an on-device Apple Home add-hub check.

**Deferred/backlog:** #18 credential rotations (after build phase) · #19 NAS parity (later, no spend).

---

## Operational cheatsheet (so a fresh session is self-sufficient)

**Host access (SSH aliases over Tailscale):** `ssh nas` (DSM; sudo needs vault pw `<vault: sudo.nas_password>`), `ssh mini` (Ubuntu; **passwordless sudo**), `ssh rig` (CachyOS), `ssh seedbox` (betty; no root).
- **HA has NO ssh** — not a tailnet node. Drive it via REST at `http://192.168.10.50:8123`, token in vault `hosts.ha.api_token` (see [[ha-control-plane]]).
- NAS specifics: `docker` = `/usr/local/bin/docker`; `synoacltool` = `/usr/syno/bin/synoacltool`; **`sqlite3` CLI absent in app containers** → read their DBs with the container's `python3`.
- NAS ssh prints a post-quantum banner — strip it: `| grep -v 'post-quantum\|store now\|may need\|openssh.com\|WARNING'`.

**Memory:** `MEMORY.md` auto-loads each session; the `[[slug]]` notes referenced here are recalled automatically — but verify a named file/flag still exists before acting on it.

**Check schema** (`foss-setup/verification/checks.d/*.yaml`):
```yaml
- id: <slug>
  name: "<what it proves>"
  host: mini                 # where cmd runs (mini | url | ...)
  cmd: >-                    # shell; vars from /etc/verification/env are in scope
    ... ; echo tok=ok || echo tok=BAD
  expect: '^tok=ok$'         # regex stdout must match to PASS
  severity: warn             # warn | crit
  task_id: verify-06
  runbook: wiki/runbooks/verification.md
  enabled: true
```

**Run a single check exactly as the runner does** (as btabaska on mini, env loaded):
```bash
ssh mini 'set -a; . <(sudo cat /etc/verification/env); set +a; <the check cmd>'
```
Then **negative-test**: force the underlying outcome broken and confirm the check FAILs (non-zero / non-matching), then restore. A check isn't done until it's negative-tested.

**Deploy:**
- mini (scp works): `scp f mini:/tmp/ && ssh mini 'sudo install -m 0755 /tmp/f /opt/verification/bin/f'` (yaml: `-m 0644` → `/opt/verification/checks.d/`).
- NAS (scp/sftp BLOCKED — use base64): `B64=$(base64 < f | tr -d '\n'); ssh nas "echo '<vault: sudo.nas_password>' | sudo -S -p '' bash -c 'echo $B64 | base64 -d > /path && chmod 0755 /path'"`.
- env additions: `printf 'KEY=val\n' | ssh mini 'sudo tee -a /etc/verification/env'` (guard first with `sudo grep -q '^KEY='`).
- ship: `git add … && git commit && git push origin main && ./foss-setup/scripts/docs/publish-deploy.sh`.

**Facts for #6 (movie/TV):** Plex `http://192.168.10.4:32400` (token in env `PLEX_TOKEN`), sections **Movies=1, TV Shows=2, Music=3, YouTube=4**. Sonarr nas:8989, Radarr nas:7878, Lidarr nas:8686, Readarr nas:8787, CWA nas:8083, Navidrome mini:4533. API keys in `/etc/verification/env` (`SONARR_API_KEY`/`RADARR_API_KEY`/`LIDARR_API_KEY`/`PLEX_*`) and vault `arr_api_keys.*`. `media.yaml` currently has **11 checks**.

**Task state:** the live session TaskList does NOT persist across sessions — **this doc's task board is authoritative**; update it here as tasks complete. Recreate session tasks from it if you want a live board.

## Notes / loose ends
- MusicSeerr "Maybe I'm Dreaming" (2008) is monitored but has no torrent release — legitimately waiting (Soulseek/RSS), not a phantom; the check ignores it.
- Naamah trilogy files are metadata-mislabeled by Readarr (separate pre-existing bug, see [[libreseerr-edition-selection]]) — not the apostrophe bug.
- The giant `docs/handoff-rollout-state.md` is shared with a concurrent account; this workstream is tracked here instead to avoid conflicts.
- **Plex 503 (open, 2026-07-13):** Plex is returning HTTP 503 to all clients — worker pool saturated by a `none`-agent metadata-analysis storm on §4 (YouTube), a side effect of the 1363-item Pinchflat ACL fix. Process is "running" (liveness green); `pinchflat-plex-visible` correctly fails `PLEX_UNREACHABLE`. Backlog drains but glacially. User chose **let it drain** (no restart). This blocks #6/#10. Diagnosis + candidate "Plex-responsive" check in memory [[plex-bulk-ingest-analysis-storm]]. Framework anti-pattern ("producer flood → consumer storm") captured in the acceptance-testing runbook.

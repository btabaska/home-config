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
- mini has **passwordless sudo**; NAS sudo needs the vault password (`Wbef#90332`); NAS `docker` = `/usr/local/bin/docker`, `synoacltool` = `/usr/syno/bin/synoacltool`.
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

**Done:** #1 Pinchflat→Plex · #2 Libreseerr→CWA · #3 MusicSeerr · #7 book acceptance test · #8 album acceptance test · #9 pinchflat acceptance test.

**Next up (recommended order):**
1. **#5 Design the e2e acceptance-test framework** — formalize the pattern above into a documented framework + journey catalog. *Prompt ready: `docs/prompts/acceptance-test-framework.md`.*
2. **#6 Acceptance test: movie/TV request → served in Plex** (blocked by #5).
3. **#10 Re-audit the 140/223 "done" for real correctness** (blocked by #6; treat green as liveness-only, re-verify user-facing services).

**Reliability / DR (P1–P2):** #11 HA backups (HIGH) · #12 HA-Assist endpoint mini:4000→rig llm.tabaska.us · #13 close ansible backup SOPS gate · #14 verify NAS Tier-1→B2 (nas-02).

**Infrastructure / planning (P3):** #15 re-audit real VLAN/zone-firewall/device-migration state · #16 DNS tail dns-03/04/05 (blocked by #15) · #17 walk unbuilt roadmap & prune (review together).

**Re-sequenced:** #4 HomePod ↔ HA HomeKit hub — **moved behind #15** (blocked by #15); needs the VLAN/mDNS map + an on-device Apple Home check.

**Deferred/backlog:** #18 credential rotations (after build phase) · #19 NAS parity (later, no spend).

---

## Notes / loose ends
- MusicSeerr "Maybe I'm Dreaming" (2008) is monitored but has no torrent release — legitimately waiting (Soulseek/RSS), not a phantom; the check ignores it.
- Naamah trilogy files are metadata-mislabeled by Readarr (separate pre-existing bug, see [[libreseerr-edition-selection]]) — not the apostrophe bug.
- The giant `docs/handoff-rollout-state.md` is shared with a concurrent account; this workstream is tracked here instead to avoid conflicts.

# TODOs — open action items (all-sessions reference)

**What this is:** a lightweight, always-current list of the items that are
**blocked, parked, or waiting on the operator** — forked from the formal plan so
any Claude session can see "what's actually outstanding" at a glance without
re-deriving it. The **authoritative** sources remain:
- `foss-setup/docs/prompts/HANDOFF-QUEUE.md` — the ordered work queue (the loop driver)
- `foss-setup/docs/quality-hardening-state.md` — the task board + completion log
- `foss-setup/docs/prompts/00-MASTER.md` — the automation prompt

Keep this in sync when an item's state changes. Last updated: **2026-07-13**.

---

## ⏳ Waiting on the operator (blocks the autonomous loop)

- [ ] **Verify the encrypted NAS Hyper Backup** — operator is re-creating the
  Tier-1→B2 task with client-side encryption ON (steps 1–7 done 2026-07-13; first
  full backup running). **When it completes green, ping a session** to: confirm
  `enable_data_encrypt=true` on the live task, confirm `nas-hyperbackup-b2-fresh`
  re-arms against the new client cache, then delete the old unencrypted
  `S3 Backup 1` task + its `TabaskaNAS_1.hbk` folder in B2.
  ⚠️ **Operator action:** save the passphrase (vault `hosts.nas.hyperbackup_password`)
  to Bitwarden **and** paper — losing it = the backup is unrecoverable.

- [ ] **Confirm the HA backup key is in Bitwarden** — vault `hosts.ha.backup_password`
  (from queue item 02). Required for HA restore.

- [ ] **#13 — ansible restic SOPS gate (DR reproducibility)** — queue item 03,
  left `[~]`. Needs operator: go-ahead to converge the single off-site DR path,
  the age-key **save** (Bitwarden + paper), and an OK to install `sops` from its
  GitHub release `.deb` on mini. Full safe-resume plan in `03-dr-reproducibility.md`
  (rewrite role to match live → install sops/age → age key → check-diff-until-no-op
  → one real converge). **Do not seed the SOPS secret before the role is aligned.**

- [ ] **#16 — DNS tail (dns-03/04/05)** — queue item 05, needs-user. Confirm in the
  UniFi UI the DHCP DNS chain `192.168.10.2, .4, .1` (in order) on each client VLAN
  (Trusted/IoT/Guest/Work). dns-05 (NAT :53 redirect) stays deferred until dns-03
  is proven on all VLANs. (mini can't fleet-verify this — it's static now.)

- [ ] **#4 — HomePod ↔ HA HomeKit hub** — queue item 06, needs-user (now unblocked
  by the #15 audit). Gate: **which VLAN the HomePods are on.** Trusted → native
  mDNS with HA works; IoT → enable Gateway mDNS proxy for `_hap._tcp.local` on
  BOTH Trusted+IoT, IGMP snooping off, + a firewall allow. Then an on-device Apple
  Home add-hub check. See `configs/network/mdns-multicast-checklist.md`.

## 🤝 Collaborative (needs a working session with the operator)

- [ ] **#17 — Walk & prune the unbuilt roadmap** — queue item 07, `07-roadmap-prune.md`.
  Review the not-yet-built roadmap together and cut/keep/defer each item.

## 🗓️ Deferred / backlog (do not auto-start)

- **#18 credential rotations** — deferred until the operator says the build phase is
  done (also: `sudo.nas_password` sits in git history — rotate here).
- **#19 NAS parity** — backlog, no new spend now.
- **Plex 503 (open):** analysis-storm draining glacially (1026→730 live as of
  2026-07-13); operator chose let-it-drain (no restart). Blocks #6/#10 (queue item 01).

---

_Autonomous queue status as of 2026-07-13: **drained** — every remaining queue item
is needs-user or collaborative. Re-running `00-MASTER.md` will report this until the
operator unblocks one of the above._

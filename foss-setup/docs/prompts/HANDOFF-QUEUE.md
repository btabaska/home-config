# Handoff queue

Ordered work queue for the quality/reliability workstream. The `00-MASTER` prompt
drives this: a fresh session does the **next unchecked item whose deps are all
checked and that is marked `autonomous`**, checks it off, commits, and stops.
Items marked `needs-user` or `collaborative` PAUSE the loop (report to the user).

Status: `[ ]` pending · `[x]` done · `[~]` in progress / partial (see note).

- [ ] **01** — Acceptance-test framework + movie/TV test + done-audit (#5/#6/#10) · **autonomous** · deps: none · `01-acceptance-test-framework.md`
- [ ] **02** — HA reliability: backups + Assist endpoint (#11/#12) · **autonomous** (saving the backup encryption key may need the user) · deps: none · `02-ha-reliability.md`
- [ ] **03** — DR reproducibility: ansible SOPS gate + NAS Tier-1→B2 verify (#13/#14) · **autonomous** (saving the age key may need the user) · deps: none · `03-dr-reproducibility.md`
- [ ] **04** — Network re-audit vs plan (#15) · **autonomous** (may need UniFi UI confirmation) · deps: none · `04-network-reaudit.md`
- [ ] **05** — DNS-chain tail dns-03/04/05 (#16) · **needs-user** (manual UniFi DHCP/UI) · deps: 04 · `05-dns-tail.md`
- [ ] **06** — HomePod ↔ HA HomeKit hub (#4) · **needs-user** (on-device Apple Home) · deps: 04 · `06-homepod-ha.md`
- [ ] **07** — Walk & prune the unbuilt roadmap (#17) · **collaborative** (user decisions) · deps: none · `07-roadmap-prune.md`

Not queued (do not auto-start):
- **#18** credential rotations — **deferred** until the user says the build phase is done. (Also: `sudo.nas_password` sits in git history — rotate it here.)
- **#19** NAS parity — **backlog**, no new spend now.

_Completion log (append one line per finished item):_
- (none yet)

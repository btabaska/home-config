# Handoff 03 — DR reproducibility (#13 ansible backup SOPS gate, #14 NAS Tier-1→B2)

Prereqs: read `foss-setup/docs/quality-hardening-state.md` + memory [[homelab-rollout-context]]. Loop: diagnose → fix/verify → validate → harden → commit origin + publish-deploy.

## #13 — Close the ansible `backup` role SOPS gate (sec-03)
restic→B2 is **live and healthy** on mini + rig via direct systemd timers (`restic-backup.timer`, last runs SUCCESS), BUT the ansible `backup` role is gated on a missing SOPS/age secret so it **skips** — meaning a rebuild-from-ansible would NOT re-arm restic. That's the gap: DR isn't reproducible.

Do:
1. Read the `backup` role + `group_vars` to see exactly which SOPS/age-encrypted secret it expects and where.
2. Provision it: create/locate the **age key**, store it in **Vaultwarden + a printed copy** *(minting/saving the key may need the user — generate, wire, and tell them to save it)*, and add the SOPS-encrypted secret file the role consumes (restic repo password + B2 creds from vault `backblaze_b2.*`).
3. Validate: run an ansible-pull converge (or `ansible-pull ... --tags backup`) on a host and confirm the role no longer skips and re-arms the restic timer/config. Do NOT clobber the working live timers — verify idempotence first (check mode / diff).

Harden: the restic dead-man checks already exist (`backups.yaml`); confirm they cover mini+rig and page if a run is missed. Add one if missing; negative-test.

## #14 — Verify NAS Tier-1 Hyper Backup → B2 (nas-02)
The handoff log is self-contradictory: one place calls NAS Tier-1 HyperBackup→B2 the "one true pending item (nas-02)", another says it ran 07-08 covering Immich/docs/homes. Resolve it against reality.

Do:
1. On `nas` (DSM), inspect Hyper Backup: is there a Tier-1→B2 task? Its last-success time, coverage (Immich photos+DB, docs, homes, HA config, compose `.env`s), schedule, client-side encryption.
2. If it exists and succeeds → close nas-02 (update `docs/progress.json` + docs). If missing/failing → that's the real gap; set it up or flag precisely.

Harden: a dead-man / freshness check that the NAS Tier-1→B2 job succeeded within its window (Hyper Backup log or a Healthchecks ping). Negative-test.

Done-criteria: ansible can reproduce restic on a rebuild (age key saved), NAS Tier-1→B2 status is verified and nas-02 closed-or-opened truthfully, both guarded by freshness checks. Commit; check item 03 off; update the task board.

---

## Progress 2026-07-13 (live-probed)

**#14 DONE.** NAS Tier-1 Hyper Backup → B2 verified live + `nas-02` closed truthfully + dead-man `nas-hyperbackup-b2-fresh` added and negative-tested. Details in `quality-hardening-state.md` and `HANDOFF-QUEUE.md` item 03. One user-facing caveat: the Hyper Backup task has **client-side encryption OFF** (`enable_data_encrypt=false`) — decide whether to re-create it with encryption (destructive re-upload).

**#13 STILL OPEN — read before resuming.** Live probing found the gap is deeper than "seed the SOPS secret", so it was **not** closed this pass (unsafe to converge the single DR path without the user):

1. **The role diverged from live.** Live restic on mini+rig is the curated script setup: `/opt/scripts/restic-backup.sh` (from `scripts/backup/restic-backup.sh`) sourcing `/etc/restic/env`, unit `restic-backup.service` with `OnFailure=ntfy-notify@`, a `restic-backup.service.d/healthchecks.conf` per-host ping drop-in, `restic-backup.timer` at 01:30, per-host `excludes-<host>.txt`, and (mini) a `PRE_BACKUP_SCRIPT` DB-dump hook. The ansible `backup` role writes a *different* self-contained unit (`/etc/restic/backup.env`, inline `restic backup`, timer at 02:30, none of the extras). **Seeding the secret as-is → next `ansible-pull` overwrites the tuned live units = DR clobber.** Fix: rewrite the role to install the real `scripts/backup/*` artifacts (per-host bits via `host_vars/macmini.yml` + `host_vars/cachyos.yml`: excludes file, Healthchecks UUID [mini `f5a8ca3e-7ce6-4117-aa51-c8a6ca3fb6a7`, rig `3cb03834-c6fd-4bd1-a334-38658a80f444`], pre-backup hook on mini only).
2. **`sops` + `age` binaries are missing on both hosts.** `community.sops` collection is present on mini (2.4.0) but the lookup needs the `sops` binary (+ `age`) to decrypt — neither exists. rig has neither either. A reproducible rebuild must install them: `age` is in apt (Ubuntu universe) and pacman; `sops` is **not** in Ubuntu apt (install a release `.deb` — a supply-chain step, get user ack) and is in the Arch repos for rig.
3. **The rig has no ansible at all** — `command -v ansible-pull` is empty, yet `ansible-pull.timer` is `enabled` (so it silently fails). The pull path can't be validated on rig until ansible is bootstrapped there (separate gap; note it, don't necessarily fix it in this item).
4. **Age key: generate + wire is autonomous; SAVING to Bitwarden + paper is the user's step.** Encode the SAME live values so DR restores the existing repos: put each host's exact `/etc/restic/env` into a per-host SOPS-encrypted file the role consumes (the live env keys are RESTIC_REPOSITORY, B2_ACCOUNT_ID, B2_ACCOUNT_KEY, RESTIC_PASSWORD, BACKUP_PATHS, RESTIC_EXCLUDE_FILE, [mini] PRE_BACKUP_SCRIPT, KEEP_*, PRUNE_WEEKDAY, [rig] NTFY_URL, NTFY_TOKEN).

**Safe resume order:** rewrite+commit the role with the gate still closed (no secret → role keeps skipping → zero live impact) → install sops/age → generate/place age key (+ tell user to save it) → seed per-host SOPS envs → `ansible-pull --tags backup --check --diff` on mini until it reports a **no-op vs live** → one real converge to prove idempotent re-arm → then rig. **Never seed the secret before the role is aligned to live.**

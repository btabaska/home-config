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

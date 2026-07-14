# Operations — Ansible & convergence

> Two levers over the fleet: the `glue-07` manual push (run one command across every box) and the `glue-08` `ansible-pull` self-convergence layer that heals drift on a timer.

_Source: `foss-setup/configs/ansible/README.md` · migrated + validated 2026-07-14_

Ansible is the layer that makes host state **executable and self-converging**
instead of documented-and-hoped. Source lives at `foss-setup/configs/ansible/`.
Agentless: Ansible connects over SSH/Tailscale using the `~/.ssh/config` aliases
(net-14) or Tailscale SSH (net-13), run from the Mac mini or a laptop. It
**complements** the automatic per-host `unattended-upgrades` in sec-05 (those
keep each box current on its own) — Ansible is for pushing a deliberate change
everywhere at once, or (via pull) for continuously re-asserting defined state.

!!! note "Validated against live mini + rig (2026-07-14)"
    `ansible-pull.timer` is `enabled` and `active (waiting)` on **both** hosts.
    Mini: next trigger `Wed 2026-07-15 04:44 UTC`, service drop-in
    `ansible-pull.service.d/healthchecks.conf` present (`ExecStartPost` curls
    `http://192.168.10.2:8001/ping/bb50a004-…` — the dead-man ping). Rig: next
    trigger `Wed 2026-07-15 04:41 EDT`, last run `status=0/SUCCESS`. Mini's last
    run (2026-07-14 04:42 UTC) **FAILED** at `base : Install unattended-upgrades`
    on exactly the releaseinfo-change class below — this time the `ondrej/php`
    PPA changed its `Label` from `Use https://packages.sury.org/php/ instead` to
    `PPA for PHP` (`status=2`). Confirms both the Healthchecks wiring and the
    apt-releaseinfo troubleshooting row. Live `ExecStart` matches the documented
    invocation (`-d ~/.ansible-pull --accept-host-key --connection local --diff`).

## The architecture: ansible-pull

There is no central push server. Each managed host **pulls** the deploy repo
and converges itself:

```
home-config (GitHub, full repo)
   └─ scripts/docs/publish-deploy.sh          # git subtree split of foss-setup/
        └─ Forgejo home/homelab (on mini)     # the deploy repo
             └─ ansible-pull (per host, systemd timer)
                  clone → ~/.ansible-pull → site.yml against itself
```

- **Unit**: `configs/ansible/ansible-pull.service` — runs
  `ansible-pull -U git@forgejo:home/homelab.git -i configs/ansible/inventory.ini
  --limit $(hostname -s) --connection local --diff configs/ansible/site.yml`.
  `--check` was deliberately removed 2026-07-07: with it, the fleet only
  *reported* drift and never converged (the audit's P0-2).
- **Timer**: daily ~04:20 **UTC** ± jitter on the mini (~04:40 ET on the
  rig), `Persistent=true` — the same `OnCalendar` pattern on every host, the
  rig included (24/7 as of 2026-07-08, so no wake-gating; `Persistent=true`
  is just the generic catch-up for any missed window).
- **State**: deployed and green on **both mini and rig** (glue-08 closed;
  each dead-manned in Healthchecks: `ansible-pull-mini`, `ansible-pull-rig`).
  First green converge mini 2026-07-07 (ok=34 failed=0); re-fixed 2026-07-09
  after an apt releaseinfo change (see Troubleshooting).

## What the roles do

| Role | Owns |
|---|---|
| `base` | Packages, unattended-upgrades, pkglist manifests, sysctl, the boring host baseline |
| `docker` | Docker engine, `daemon.json` log rotation (10m×3), the external `edge` network |
| `tailscale` | Install + join (skips `tailscale up` when already connected) |
| `backup` | restic via ansible — **gated on the SOPS secret existing** (sec-03 open, so the role skips). The *live* restic timers on mini+rig were hand-deployed from `scripts/backup/` and are dead-manned in Healthchecks |
| ~~`sbom`~~ | **RETIRED 2026-07-09** (user decision; Syft OOM'd the 8 GB mini) — removed from `site.yml` so convergence won't redeploy it |
| `state` | etckeeper, chezmoi invocation, cron/timer exports |

Playbooks for deliberate fleet-wide pushes: `playbooks/patch.yml`
(apt `safe-upgrade` / pacman `-Syu`), `reboot.yml` (controlled, one host at a
time), `audit.yml` (package/version drift → `./audit/<host>.txt`) — all run
manually from the MacBook or mini.

**Deliberately NOT Ansible-managed**: the NAS (DSM appliance), HA (no shell),
the gateway (GUI-only), the seedbox OS (no root — user-space only). Don't
automate the un-automatable. Patch those via their own UIs (see
`reference/network/ssh-maintenance-access.md`).

## The push lever (glue-07): manual fleet commands

`glue-08` (pull) is the self-converging half; `glue-07` is the **push** half —
*you* run `patch`/`reboot`/`audit` when you want to. Both share the same
`inventory.ini`, SSH path, and Forgejo control repo. Push-side layout:

```
ansible/
├── ansible.cfg          # uses ~/.ssh/config, serialized + readable output
├── inventory.ini        # the fleet, grouped by OS family (debian / arch)
└── playbooks/
    ├── patch.yml        # security/package updates (apt safe-upgrade / pacman -Syu)
    ├── reboot.yml       # controlled, one-host-at-a-time reboots
    └── audit.yml        # package/version drift -> ./audit/<host>.txt
```

Setup (control node — Mac mini or laptop):

```bash
sudo apt install -y ansible          # or: pipx install ansible
ansible-galaxy collection install community.general ansible.posix
# edit inventory.ini so each ansible_host matches a configs/network/ssh-config.example alias
```

Use:

```bash
cd configs/ansible

# is everything reachable over the tailnet?
ansible all -i inventory.ini -m ping

# dry-run a patch, then apply (one host at a time)
ansible-playbook -i inventory.ini playbooks/patch.yml --check
ansible-playbook -i inventory.ini playbooks/patch.yml

# reboot only what needs it, serialized
ansible-playbook -i inventory.ini playbooks/reboot.yml

# collect drift reports under ./audit/
ansible-playbook -i inventory.ini playbooks/audit.yml
```

For a true one-off, a plain
`for h in nas mini rig; do ssh "$h" '<cmd>'; done` loop is fine — reach for
Ansible once you're repeating yourself.

**Push notes:**

- The **rig is 24/7** (decision 2026-07-08) and always reachable. If it's down
  that's an incident — recover with `scripts/gaming/wake-rig.sh` (game-08).
  Exclude any host with `--limit '!<host>'`.
- Commit the `configs/ansible/` folder to the Forgejo control repo (glue-05).
  The `audit/` output is throwaway — add it to `.gitignore`.

## The publish flow (repo → fleet)

```bash
# after committing to home-config:
./foss-setup/scripts/docs/publish-deploy.sh
```

It runs `git subtree split --prefix=foss-setup` and pushes the result to
Forgejo `home/homelab` `main` (deterministic → fast-forwards). Hosts pick it
up on their next timer fire. After a `--force` publish, refresh host clones:
`ssh mini 'rm -rf ~/.ansible-pull'`.

## Run a manual converge

```bash
ssh mini 'sudo systemctl start ansible-pull.service'
ssh mini 'journalctl -u ansible-pull.service -n 60 --no-pager'
# look for: ok=N changed=M failed=0
```

Dry-run first when nervous: add `--check --diff` to the ansible-pull
invocation by hand (never bake `--check` back into the unit). To converge one
host from the control node instead (push style):

```bash
ansible-galaxy install -r requirements.yml      # pinned collections
ansible-playbook site.yml --check --diff        # preview — changes nothing
ansible-playbook site.yml --limit macmini       # converge one host now
```

## Pull-side layout, secrets & scaffolds

Beyond the push files above, the pull layer (glue-08) adds:

```
ansible/
├── site.yml                 # desired state — push AND ansible-pull both use this
├── requirements.yml         # pinned collections (+ community.sops for secrets)
├── group_vars/
│   ├── all.yml              # non-secret knobs; SOPS lookups for secrets
│   └── on_demand.yml        # the rig: wake-gating instead of a wall clock
├── roles/                   # base, docker, tailscale, backup, state (sbom RETIRED)
├── ansible-pull.service     # systemd unit: clone repo + run site.yml on localhost
├── ansible-pull.timer       # schedule (wall clock; rig can use a wake hook)
├── .ansible-lint            # CI lint profile
└── ci-ansible-lint.example.yml  # drop into .forgejo/workflows/
```

### Secrets

No `ansible-vault`. `community.sops` reads the **same SOPS + age** files as
glue-06, so the only secret store is the age key already in Proton Pass plus a
printed copy. Example lookup in a role/var:

```yaml
restic_password: "{{ lookup('community.sops.sops', 'secrets/restic.sops.env', age_keyfile=sops_age_keyfile) }}"
```

See `operations/secrets.md` for the vault policy.

### Scaffolds

The roles are working **scaffolds**: a few vars in `group_vars/all.yml` (pinned
tool versions, the chezmoi repo) and the `files/`, `secrets/`, and
`hosts/<box>/pkglist.txt` paths are yours to fill in. Run
`ansible-playbook site.yml --check --diff` and `ansible-lint` to see what each
role would do before it touches a host.

### What it buys you

- **Drift heals itself** — `ansible-pull` auto-applies OS security patches under
  the same "no blind updates" rule as Diun / sec-05 (with `--diff` the journal
  still shows every change).
- **`restore.md` becomes executable** — most of the sbom-05 runbook collapses to
  *reinstall OS → install ansible → `ansible-pull` → restore data from Restic*,
  and the quarterly VM drill runs the **real** `site.yml` so it can't rot.
- **Still appliance-aware** — NAS/HA/Dream Wall stay out of the inventory and
  keep their native backups (sec-05 / sbom-03).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Could not match supplied host pattern` | hostname ≠ inventory name — check `inventory.ini` vs `hostname -s` |
| Fetch fails | Forgejo down on the mini, or deploy key not registered |
| `apt-get update` fails on a PPA "Label"/releaseinfo change | Upstream repo metadata changed (bit glue-08, 2026-07-09) — one manual `apt-get update --allow-releaseinfo-change`, then converges are green again |
| backup role skips/hard-stops | SOPS secret missing — the role gates on it; see `operations/secrets.md` |
| Converge green but box drifted | Someone changed the host by hand — the fix goes in the repo, not the host |
| Converge restarts docker (bounces every container ~1 min) | A `daemon.json` change landed (log caps, address pools) — expected once per change, idempotent after |

---

[← Home](../index.md)

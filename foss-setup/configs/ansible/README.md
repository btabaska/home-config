# Ansible fleet maintenance (glue-07)

Run **one command across every box** instead of SSHing into each one. Agentless:
Ansible just connects over SSH/Tailscale using your `~/.ssh/config` aliases
(net-14) or Tailscale SSH (net-13). Run it from the Mac mini or your laptop.

This is the **manual** fleet lever. It complements — does not replace — the
automatic per-host `unattended-upgrades` in **sec-05**: unattended-upgrades keeps
each box current on its own; Ansible is for pushing a deliberate change
everywhere at once. For a true one-off, a plain
`for h in nas mini rig; do ssh "$h" '<cmd>'; done` loop is fine — reach for
Ansible once you're repeating yourself.

## Layout

```
ansible/
├── ansible.cfg          # uses ~/.ssh/config, serialized + readable output
├── inventory.ini        # the fleet, grouped by OS family (debian / arch)
├── playbooks/
│   ├── patch.yml        # security/package updates (apt safe-upgrade / pacman -Syu)
│   ├── reboot.yml       # controlled, one-host-at-a-time reboots
│   └── audit.yml        # package/version drift -> ./audit/<host>.txt
└── README.md
```

## Setup

```bash
sudo apt install -y ansible          # or: pipx install ansible
# collections used by the playbooks:
ansible-galaxy collection install community.general ansible.posix
```

Edit `inventory.ini` so each `ansible_host` matches an alias in
`configs/network/ssh-config.example`.

## Use

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

## Notes

- The **rig is 24/7** (decision 2026-07-08) and always reachable. If it's down,
  that's an incident — recover with `scripts/gaming/wake-rig.sh` (game-08).
  Exclude any host with `--limit '!<host>'`.
- The **NAS (DSM)** and **Home Assistant (HAOS)** are intentionally out of scope
  — patch them via their own UIs (see `../network/ssh-maintenance-access.md`).
- Commit this folder to the Forgejo control repo (glue-05). The `audit/` output
  is throwaway — add it to `.gitignore`.

---

## glue-08 — the self-converging layer (PULL)

`glue-07` (above) is the **push lever**: *you* run `patch`/`reboot`/`audit` when
you want to. `glue-08` adds the **pull layer** so each box converges **itself**
on a timer — the genuinely "set it and forget it, replicable across devices"
half. They share the same inventory, SSH path, and control repo.

### Extra layout

```
ansible/
├── site.yml                 # desired state of the fleet (push AND ansible-pull use this)
├── requirements.yml         # pinned collections (+ community.sops for secrets)
├── group_vars/
│   ├── all.yml              # non-secret knobs; SOPS lookups for secrets
│   └── on_demand.yml        # the rig: wake-gating instead of a wall clock
├── roles/
│   ├── base/               # admin user + key, unattended-upgrades, sysctl, package convergence
│   ├── docker/             # engine + sec-04 log caps + the shared 'edge' network
│   ├── tailscale/          # tailscale up --ssh with net-13 tags
│   ├── backup/             # restic timer (rig-wake-gated)
│   ├── sbom/               # Syft/Grype + the sbom-02 nightly units
│   └── state/              # installs + bootstraps etckeeper and chezmoi themselves
├── ansible-pull.service     # systemd unit: clone repo + run site.yml on localhost
├── ansible-pull.timer       # schedule (wall clock on always_on; wake hook on the rig)
├── .ansible-lint            # CI lint profile
└── ci-ansible-lint.example.yml  # drop into the repo's .forgejo/workflows/
```

### Use

```bash
ansible-galaxy install -r requirements.yml

# preview convergence — changes nothing
ansible-playbook site.yml --check --diff

# converge one host now (push)
ansible-playbook site.yml --limit macmini

# turn on self-convergence (pull) on each host
sudo cp ansible-pull.service ansible-pull.timer /etc/systemd/system/
sudo systemctl enable --now ansible-pull.timer
```

### Secrets

No `ansible-vault`. `community.sops` reads the **same SOPS + age** files from
glue-06, e.g.:

```yaml
restic_password: "{{ lookup('community.sops.sops', 'secrets/restic.sops.env', age_keyfile=sops_age_keyfile) }}"
```

so the only secret store is the age key already in Proton Pass + a printed copy.

### What it buys you

- **Drift heals itself.** `ansible-pull` runs `--check` for config (reports drift
  to ntfy) and auto-applies only OS security patches — same "no blind updates"
  rule as Diun / sec-05. Flip off `--check` per run once you trust it.
- **`restore.md` becomes executable.** Most of the sbom-05 runbook collapses to
  *reinstall OS → install ansible → `ansible-pull` → restore data from Restic*,
  and the quarterly VM drill runs the **real** `site.yml` so it can't rot.
- **Still appliance-aware.** NAS/HA/Dream Wall stay out of the inventory and keep
  their native backups (sec-05 / sbom-03).

> These roles are working **scaffolds**: a couple of vars in `group_vars/all.yml`
> (pinned `syft`/`grype` versions, the chezmoi repo) and the `files/`,
> `secrets/`, and `hosts/<box>/pkglist.txt` paths are yours to fill in. Run
> `ansible-playbook site.yml --check --diff` and `ansible-lint` to see what each
> would do before it touches a host.

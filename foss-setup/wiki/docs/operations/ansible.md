# Operations — Ansible & convergence

Ansible is the layer that makes host state **executable and self-converging**
instead of documented-and-hoped. Source lives at `foss-setup/configs/ansible/`.

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
- **Timer**: daily 04:20 ± 30 min jitter, `Persistent=true` — the same
  `OnCalendar` schedule on every host, the rig included (it runs 24/7 as of
  2026-07-08, so no wake-gating; `Persistent=true` is just the generic
  catch-up for any missed window, e.g. after downtime).
- **State**: first fully green converge on the mini 2026-07-07
  (ok=34 failed=0, apply mode). Rig deployment pending (glue-08 — gated on
  the rig sudo password and its Forgejo deploy key).

## What the roles do

| Role | Owns |
|---|---|
| `base` | Packages, unattended-upgrades, pkglist manifests, sysctl, the boring host baseline |
| `docker` | Docker engine, `daemon.json` log rotation (10m×3), the external `edge` network |
| `tailscale` | Install + join (skips `tailscale up` when already connected) |
| `backup` | restic jobs — **gated on the SOPS secret existing** (pending: B2/sec-03) |
| `sbom` | Nightly Syft SBOM generation + upload to Dependency-Track, manifest exports |
| `state` | etckeeper, chezmoi invocation, cron/timer exports |

Playbooks for deliberate fleet-wide pushes: `playbooks/patch.yml`,
`reboot.yml`, `audit.yml` (run manually from the MacBook or mini).

**Deliberately NOT Ansible-managed**: the NAS (DSM appliance), HA (no shell),
the gateway (GUI-only), the seedbox OS (no root — user-space only). Don't
automate the un-automatable.

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
invocation by hand (never bake `--check` back into the unit).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Could not match supplied host pattern` | hostname ≠ inventory name — check `inventory.ini` vs `hostname -s` |
| Fetch fails | Forgejo down on the mini, or deploy key not registered |
| backup/sbom role hard-stops | SOPS secret missing — roles gate on it; see [Secrets](secrets.md) |
| Converge green but box drifted | Someone changed the host by hand — the fix goes in the repo, not the host |

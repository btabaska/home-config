# 9. Fleet automation with Ansible (make the runbooks executable)

Sections 7 (set-and-forget) and 8 (inventory) get you *rebuildable* — config-as-code, manifests, chezmoi, etckeeper, per-host `restore.md`. But most of that is **descriptive** or **hand-run**. Ansible turns it **executable and self-converging**: one idempotent definition of every fully-owned host, applied the same way, on a schedule, with drift you can preview.

The discipline: an Ansible run is **idempotent**, and `--check --diff` *shows* exactly what would change before anything does — the same "no blind auto-updates" philosophy as Section 7 (set-and-forget), applied to host config.

> **Live status:** Ansible convergence is deployed and green on the mini + rig — `ansible-pull` converges `ok=30 failed=0`, fleet pings green (`glue-08` re-closed 2026-07-09). Note that after the SBOM retirement the **`sbom` role was removed from `site.yml`** (won't redeploy the abandoned pipeline), and `fix-19` restored `default-address-pools` in `daemon.json` + the docker role.

## Where Ansible fits (and where it deliberately doesn't)

| Layer | Owner | Ansible's role |
|---|---|---|
| **OS / host state** (packages, Docker engine, `daemon.json`, `edge` network, unattended-upgrades, NUT client, sysctl, SSH hardening, timers) | **Ansible** | Sets and enforces it, fleet-wide |
| **`/etc` change audit** | **etckeeper** | Ansible *sets* canonical `/etc`; etckeeper *records* the change (incl. metadata) |
| **User dotfiles (`~`)** | **chezmoi** | Ansible *installs and invokes* chezmoi; it doesn't duplicate `~` templating |
| **Container runtime/lifecycle** | **Komodo / Dockge** | Ansible does host prep + first bring-up; the chosen tool owns the day-to-day loop |
| **Secrets at rest** | **SOPS + age** | Ansible *consumes* them via `community.sops` — no second secret system |

What Ansible should **not** manage:

- **DS920+ / DSM** — DSM owns its config DB and **resets `sshd_config`/system files on updates**. Keep **DSM Configuration Backup + Hyper Backup** as its restore path; at most point a nightly Syft run at it *(the Syft pipeline is now disabled — so effectively just the native backups)*.
- **HAOS** — no general shell/Python to converge. Keep HA's **own backups + the Git `/config` add-on**.
- **Dream Wall / UniFi** — no Ansible control surface worth trusting; the ZBF migration is one-way GUI work. Keep the **`.unf` export**.
- **Managed seedbox** — usually jailed/no root; manage only the **user-space** you control.

**So Ansible's real fleet is the boxes you own at the OS level: the CachyOS rig + the Mac mini (+ the seedbox's user-space).** The NAS, HA, and UniFi keep their native backup/restore.

## The container split (resolve the overlap with Section 7)

Don't have two tools racing to `docker compose up`:

- **If you run Komodo** (Git-driven, multi-server): let **Komodo own the compose deploy loop**; Ansible only lays the foundation (Docker engine, `daemon.json` log rotation, the `edge` network, SOPS-templated `.env` files).
- **If you stay on Dockge** (manual UI, single host): Ansible can also **push the compose stacks** and template `.env` from SOPS.

Either way Ansible owns the host *underneath* the containers; only one tool owns the containers.

## The control node and where it all lives

Ansible lives **inside the same Forgejo control repo** from Section 8 (inventory) — a `git clone` of `homelab/` gives both the state *and* the engine. Run it from the **always-on Mac mini** (+ your laptop). Layout:

```
homelab/
  ansible/
    ansible.cfg
    requirements.yml        # pinned collections (community.docker, community.general,
                            #   community.sops, ansible.posix) + roles
    inventory.ini           # the fleet, by ssh-config alias (net-14)
    group_vars/
      all.yml
      on_demand.yml         # rig (historical name — rig is 24/7 now, no wake-gating)
    site.yml                # push + ansible-pull entrypoint
    playbooks/
      patch.yml             # rolling OS security updates
      reboot.yml            # controlled, ordered reboots
      audit.yml             # package/version drift vs. the Section 8 manifests
    roles/
      base/ docker/ tailscale/ backup/ state/    # (sbom/ removed after retirement)
  ...
```

Inventory groups by OS family *and* power tier:

```ini
# inventory.ini — ssh-config aliases (net-14), grouped by OS family + power tier
[debian]
macmini  ansible_host=mini
seedbox  ansible_host=seedbox

[arch]
cachyos  ansible_host=rig

[fleet:children]      # site.yml targets `hosts: fleet`
debian
arch

[always_on]
macmini
seedbox

[on_demand]           # the rig — historical group name; runs 24/7 now
cachyos

[docker_hosts]        # gets the docker role; seedbox excluded (managed/jailed)
macmini
```

It reuses the **`~/.ssh/config` aliases** from Section 7 (set-and-forget) (each `ansible_host` resolves over **Tailscale MagicDNS + key-less Tailscale SSH**) — no new access layer. `fleet` is what `site.yml` converges; `docker_hosts` gates the `docker` role.

> **Live caveat:** the **rig had no Ansible installed at all** at last DR probe (its pull path is unvalidatable there) — a known gap in the DR-reproducibility work (`#13`, blocked). The mini pull path converges green.

## Push vs. pull — the actual set-and-forget decision

Use **both**:

- **`ansible-pull` on a systemd timer per host = the set-and-forget default.** Each box periodically clones the control repo and **converges itself**. No central scheduler, keeps working if the mini is down, naturally corrects drift.
- **Push (`ansible-playbook` from the mini/laptop) = orchestration that needs ordering.** Rolling patches with `serial: 1`, reboot + health gate, coordinated multi-host redeploys.

The safe default (mirrors Section 7's "no blind updates"): run pull in **`--check` (report-only) for *config*** — ping **ntfy** on drift, wait for your deliberate push — while **auto-applying only OS security patches** (same scope as `unattended-upgrades`).

## Secrets — reuse SOPS + age, don't add ansible-vault

The `community.sops` collection reads your existing SOPS+age files directly via `age_keyfile`, so the **age key already in Proton Pass + printed** is the *only* secret store:

```yaml
# group_vars/all.yml
sops_age_keyfile: /home/admin/.config/sops/age/keys.txt

# in a role, template a stack's .env from a SOPS-encrypted file:
- name: Render Seerr .env from SOPS
  ansible.builtin.copy:
    dest: /opt/stacks/seerr/.env
    content: "{{ lookup('community.sops.sops', 'secrets/seerr.env.sops', age_keyfile=sops_age_keyfile) }}"
    mode: '0600'
```

> **Live caveat:** `sops` + `age` **binaries are missing on both hosts**, so the `community.sops` lookup can't decrypt yet — the reason the ansible `backup` role skips and the `#13` DR-reproducibility harden is blocked. See memory `dr-reproducibility-gap`.

## The roles to build

- **`base`** — admin user + ed25519 key, timezone/locale, `unattended-upgrades`, sysctl, and **package convergence from the manifests** (`community.general.pacman` / `ansible.builtin.apt` fed by the exported lists). The manifest becomes the *enforcer*, not just a record.
- **`docker`** — engine + compose plugin, the **`daemon.json` log-rotation caps**, and `docker network create edge` (idempotent).
- **`tailscale`** — install + `tailscale up --ssh` with `tag:server` tags.
- **`backup`** — Restic install + the systemd timer (plain timers everywhere).
- ~~**`sbom`**~~ — **removed** after the SBOM retirement so convergence won't redeploy it.
- **`monitoring`** *(planned — not yet in `site.yml`)* — would install the Beszel agent; for now agents are deployed by hand.
- **`state`** — installs/bootstraps **etckeeper and chezmoi** (`chezmoi init --apply`).

## This is what finally makes `restore.md` real

With Ansible, **`hosts/<box>/restore.md` becomes (or wraps) `site.yml`**: reinstall the OS, install `git`/`ansible`, `git clone` the control repo, `ansible-pull` (or `ansible-playbook site.yml --limit <box>`), restore data from Restic — done. The **quarterly throwaway-VM drill** runs the *actual* playbook so the runbook can't drift from reality. *(That drill capstone — `glue-06`/`sbom-05` — is currently deferred.)*

Keep it honest with cheap CI in Forgejo Actions: **`ansible-lint`** and **`ansible-playbook --check --diff`** on every push.

## Bottom line

Ansible doesn't replace anything in Sections 7-8 — it **operationalizes** them. chezmoi owns `~`, etckeeper audits `/etc`, Dockge runs containers, SOPS+age holds secrets, and the NAS/HA/UniFi keep native backups. Ansible is the idempotent engine that installs and wires all of it the same way on the rig and the Mac mini, on a timer, with previewable drift.

---
[← index](index.md)

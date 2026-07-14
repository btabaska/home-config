# 8. Inventory, SBOMs & rebuildable state

By the end of this build you run ~25 services across 4-5 boxes (NAS, Mac mini, rig, HA, Dream Wall) plus an off-site seedbox. [Section 6](backup.md) saves your **data**; [Section 7](set-and-forget.md)'s config-as-code saves your **compose files**. This section closes the last two gaps:

1. A live inventory that answers "what's installed, on which host, what version, and is any of it now vulnerable?"
2. Complete state-in-Git — `/etc`, dotfiles, cron/timers, app configs, device exports — so a wiped box is a `git clone` + restore away.

> ## ⚠️ Major correction — the SBOM / Dependency-Track centerpiece is RETIRED
>
> This section's headline feature — a continuously-monitored **OWASP Dependency-Track** dashboard fed by nightly **Syft** SBOMs — was **retired by user decision (2026-07-09 → 2026-07-11)**:
>
> - **Judged overkill for a home network**, and **syft was OOM'ing the 8 GB Mac mini** nightly.
> - **All Dependency-Track containers were removed from the NAS** (`compose down`); the Kuma monitor, Caddy vhost, Homepage tile, and NAS container-manifest entries were all removed. **Confirmed live 2026-07-14: no Dependency-Track on the NAS.**
> - The `sbom` **Ansible role was removed** from `site.yml` and the nightly SBOM timers **disabled** on the mini + rig, so convergence won't redeploy it. The never-deployed `dependency-track` / `sbom` stack dirs and scripts were **deleted**.
> - Syft/Grype binaries may still exist, but there is **no active SBOM → DT pipeline**.
>
> **What survives from this section:** the **state-in-Git / rebuildable-host** half — etckeeper, chezmoi, the Forgejo control repo, the per-host manifest exports, and the restore runbooks. Read the CVE/supply-chain framing below as *history/rationale*, not an active pipeline; the durable takeaway (**pin versions, verify digests, keep an inventory**) still holds.

## Why "SBOM" was the frame (history)

An **SBOM (Software Bill of Materials)** is a machine-readable list of every component/version inside software. The 2026 supply-chain reality made this concrete: the **TeamPCP campaign (March 2026)** poisoned the Trivy scanner and cascaded into the `litellm` PyPI package via stolen CI credentials — tracked as **CVE-2026-33634 (CVSS 9.4), added to CISA's KEV catalog**. The lesson for a set-and-forget box: **pin versions, verify signatures/digests, and keep an inventory** so "was I exposed, and where?" is a seconds-long question. *(This lesson stands even though the DT dashboard was abandoned.)*

## ~~The centerpiece: a continuously-monitored SBOM dashboard (OWASP Dependency-Track)~~ — RETIRED

*(Kept for history.)* The plan called for **Dependency-Track v5 ("Hyades")** on the **NAS** (Java API server + frontend + Postgres, ~4 GB+), making each host/stack a DT "project" with nightly Syft uploads. This is the feature that was **retired in full** — see the banner above.

## ~~Generating the SBOMs — Syft + Grype~~ — pipeline disabled

*(Kept for history.)* **Syft (Anchore)** generated CycloneDX SBOMs from images *and* whole filesystems; **Grype** scanned them. The nightly per-host systemd timer would `syft dir:/ …` + `syft <image> …`, upload to DT, and also export the plain human manifests. **The DT upload half is gone; the plain-manifest export half is still useful** (below) as an offline inventory + rebuild aid.

## The control repo: state-in-Git, structured for restore

A single **private** repo — self-hosted **Forgejo/Gitea** (or private GitHub) — as the source of truth, structured so each host has an obvious restore path:

```
homelab/
  hosts/
    cachyos/    # pacman + AUR lists, /etc snapshot ref, restore.md
    macmini/    # apt manual list, /etc ref, restore.md
    ds920/      # DSM config export, package list, restore.md
    ha/         # HA /config (YAML, automations, dashboards)
  stacks/       # every docker-compose.yml + .env.example, per service
  network/      # UniFi .unf exports
  ansible/      # inventory + fleet-maintenance playbooks (patch, reboot, audit)
  inventory.md  # auto-generated: what / where / version / status
  secrets/      # SOPS + age encrypted
```

## Backing up configs, scripts, cron jobs & dotfiles (per host)

- **`/etc` → etckeeper.** Puts `/etc` in Git, **auto-commits on every apt/pacman operation**, preserves file **metadata** (permissions that matter for `/etc/shadow`). Add a **`systemd.path` unit watching `/etc`** for near-real-time commits, set **`PUSH_REMOTE`** to the control repo. **Warning: `/etc` contains real secrets — this remote MUST be private and ideally encrypted.** Works on CachyOS (pacman hooks) and Ubuntu (apt hooks).
- **Dotfiles (`~`) → chezmoi.** Track `~/.config`, shell/theme, editor config, with **templating + built-in `age` encryption** and the `~/.zshrc.local` override pattern. A rig rebuild becomes `chezmoi init --apply <repo>`. Keep the files next to the compose files in the same control repo.
- **Cron + systemd timers.** etckeeper captures `/etc/cron.d`, `/etc/cron.*`, `/etc/systemd/system`; the nightly job also exports **per-user crontabs**, `systemctl list-timers`, and `~/.config/systemd/user/`.
- **Home Assistant.** Its own full backups go to the NAS ([Section 3](smart-home.md)) — also put `/config` under Git via the Git pull/push add-on or a commit job. (And the **backup encryption key** goes in the password manager.)
- **UniFi Dream Wall.** Pull the **`.unf`** export into `network/` on a schedule.
- **DS920+ / DSM.** DSM is locked down — don't fight it with etckeeper. Use **Control Panel → Update & Restore → Configuration Backup** on a schedule + Hyper Backup's config export + the installed-package list.
- **Docker volumes / databases.** [Section 6](backup.md) owns the **data**; the control repo owns the **recipe**. Together: `git clone` + `docker compose up` + restore the volume = the service is back.

## Secrets, the right way

`/etc` and dotfiles inevitably contain secrets, so a private remote alone isn't enough:

1. The control-repo remote is **private** (self-hosted Forgejo on the NAS/Mac mini, or private GitHub).
2. Encrypt the sensitive bits **at rest** with **SOPS + age** (or git-crypt); chezmoi has native `age` encryption for the dotfile half.

Keep the **age/SOPS key in your password manager + a printed copy** — the same discipline [Section 6](backup.md) demands. (A backup you can't decrypt after the fire is not a backup.)

## The "at a glance" dashboard

- ~~Dependency-Track *is* the software-inventory dashboard.~~ **Retired** — see banner.
- **Homepage** ([Section 7](set-and-forget.md)) rolls up **Beszel** (health) + **Uptime Kuma** (uptime). *(The DT risk-widget is gone.)*
- **`inventory.md`**, auto-generated from the plain manifests, makes the repo itself a readable "what / where / version / status" table — useful precisely when the dashboards are down.
- **Alerts via ntfy:** the nightly manifest job pings ntfy on failure; **Diun** covers "a new image is available."

## Restore runbook (the thing that makes it real)

Each `hosts/<box>/restore.md` is a short, *tested* checklist. Generic shape:

1. Reinstall the OS → install `git`, `restic`, `chezmoi`.
2. `git clone` the control repo. Restore `/etc` files **selectively** from etckeeper history — **don't blanket-checkout an old tree into a live `/etc`**; restore the files you need, then re-run `etckeeper init`.
3. Reinstall packages from the manifest (`pacman -S --needed - < pkglist`; `xargs -a aptlist apt install`).
4. `chezmoi init --apply` for dotfiles; reinstate cron/user timers.
5. `docker compose up -d` per stack; restore volumes/DBs from Restic.
6. Re-join Tailscale; confirm green in Homepage / Beszel.

**Drill it quarterly in a throwaway VM.** **Status:** the bare-OS rebuild drill + per-host restore runbooks (`glue-06` / `sbom-05`) are **deferred** (DR-validation capstone parked). Restic dead-man checks for mini + rig are already live and FRESH, so the day-to-day backup arming is covered.

## Where it all runs (power-aware)

- **Mac mini (always-on, ~12 W):** Forgejo (control-repo remote) + the nightly orchestration + the light web stack.
- **Each host:** etckeeper + the manifest/cron exporters, fired by systemd timers. *(Syft/Grype + DT upload was here — now disabled.)*
- **NAS:** DSM Configuration Backup + the Restic repo + HA backup archives. *(It was also slated to host Dependency-Track + Frigate + Paperless; DT is retired, Frigate is deferred, Paperless is not yet deployed.)*

---
[← index](index.md)

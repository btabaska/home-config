# Restore Runbook — `<HOSTNAME>` (template)

> Generic, per-host bare-metal restore procedure. Copy to
> `hosts/<hostname>/restore-runbook.md` and fill in the `<...>` placeholders for
> that box (disk layout, stacks present, repo URLs, Tailscale tag, etc.).
>
> **Drill this quarterly in a throwaway VM.** A restore procedure you've never
> run is a wish, not a backup. Spin up a disposable VM, follow these steps end to
> end, confirm the host comes back green, then delete the VM. Note anything that
> drifted and fix this runbook.

## Prerequisites (have these before you start)

- [ ] Restic repo password (from your password manager **and** on paper).
- [ ] B2 / Storage Box credentials (`/etc/restic/b2.env` contents).
- [ ] SSH key / access to the **private** Forgejo control repo and the per-host
      `/etc` repo (etckeeper PUSH_REMOTE).
- [ ] Tailscale auth key (or ability to log in to re-authenticate the node).
- [ ] This runbook + `configs/inventory/inventory.md` for the host.

---

## 1. Reinstall the OS

Install the same distro/version the host ran (see `inventory.md` → Host row):
`<Ubuntu 24.04 LTS | CachyOS rolling | ...>`. Match disk layout / filesystem
(`<ext4 | btrfs | zfs>`) and hostname **exactly** (`hostnamectl set-hostname <hostname>`)
— manifests and Restic tags are keyed on `hostname -s`.

## 2. Install the bootstrap tools

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y git restic
# Arch/CachyOS
sudo pacman -Sy --needed git restic
# chezmoi (used in step 6)
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$HOME/.local/bin"
```

## 3. Clone the control repo

```bash
sudo mkdir -p /opt && cd /opt
git clone <git@forgejo.tabaska.us:homelab/foss-setup.git> foss-setup
```

This gives you the compose stacks, scripts, and this runbook back on the box.

## 4. Restore `/etc` — SELECTIVELY (do not blanket-checkout)

Clone the host's **private** `/etc` etckeeper repo somewhere scratch and copy
back **only** the files you actually need:

```bash
git clone <git@forgejo.tabaska.us:homelab/etc-<hostname>.git> /tmp/etc-restore
```

> ⚠️ **Do NOT** `git checkout` or rsync the whole tree into the live `/etc`.
> A fresh install already has working `passwd`/`shadow`/`fstab`/machine-id/host
> keys; clobbering them can lock you out or break boot. Cherry-pick specific
> configs you customized, e.g.:

```bash
sudo cp /tmp/etc-restore/systemd/system/<your-unit>.service /etc/systemd/system/
sudo cp /tmp/etc-restore/<service>/<config> /etc/<service>/
# diff first if unsure:  sudo diff /tmp/etc-restore/<f> /etc/<f>
```

Re-run `etckeeper-setup.sh` afterward to re-establish versioning on the new `/etc`.

## 5. Replay the package manifest

```bash
# Ubuntu/Debian
sudo apt-get update
xargs -a hosts/<hostname>/pkglist.apt-manual.txt sudo apt-get install -y

# Arch/CachyOS (repo packages)
sudo pacman -S --needed - < hosts/<hostname>/pkglist.pacman-explicit.txt
# AUR/foreign packages (with your AUR helper)
paru -S --needed - < hosts/<hostname>/pkglist.aur.txt

# Flatpak apps
awk 'NR>1{print $1}' hosts/<hostname>/flatpak.txt | xargs -r -n1 flatpak install -y flathub
```

## 6. Restore dotfiles with chezmoi

```bash
chezmoi init --apply <git@forgejo.tabaska.us:homelab/dotfiles.git>
```

(See `scripts/dotfiles/bootstrap-dotfiles.sh` for the wrapped, idempotent version.)

## 7. Reinstate cron jobs and systemd timers

```bash
# crontabs (per user) — review hosts/<hostname>/crontabs.txt then reinstall:
crontab hosts/<hostname>/<user>.crontab   # if you split them out

# systemd timers shipped from the repo (inventory, sbom, backups):
sudo install -D -m 0755 scripts/inventory/sbom-nightly.sh      /opt/scripts/inventory/sbom-nightly.sh
sudo install -D -m 0755 scripts/inventory/export-manifests.sh  /opt/scripts/inventory/export-manifests.sh
sudo cp scripts/inventory/*.service scripts/inventory/*.timer  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sbom-nightly.timer export-manifests.timer
# Cross-check against the captured list:
cat hosts/<hostname>/systemd-timers.txt
```

Re-run `scripts/inventory/etckeeper-setup.sh` here too if you didn't in step 4.

## 8. Bring up the Docker stacks

```bash
# Install Docker if this host runs containers:
sudo ./scripts/setup/install-docker-ubuntu.sh   # Ubuntu
docker network create edge                       # shared reverse-proxy network

sudo mkdir -p /opt/stacks
sudo cp -r configs/docker-stack/stacks/* /opt/stacks/
for d in /opt/stacks/*/; do
  cd "$d"
  [[ -f .env.example && ! -f .env ]] && cp .env.example .env && echo "EDIT SECRETS: $d.env"
done
# After filling in every .env (compare pinned tags to hosts/<hostname>/compose-images.txt):
for d in /opt/stacks/*/; do (cd "$d" && docker compose up -d); done
```

Bring **caddy** + **ntfy** up first, then **adguard/dockge/beszel/uptime-kuma**,
then app stacks, then **diun** last (see `configs/docker-stack/README.md`).

## 9. Restore volumes / databases from Restic

```bash
sudo ENV_FILE=/etc/restic/b2.env restic snapshots
# Restore bind-mount data + named volumes for this host's latest snapshot:
sudo ENV_FILE=/etc/restic/b2.env restic restore latest \
  --host <hostname> --target / \
  --include /opt/stacks --include /var/lib/docker/volumes
```

For Postgres-backed stacks (Miniflux, Dependency-Track) prefer a logical dump
restore if you have one; otherwise the volume restore above brings back the
`./db` bind mount. Restart the affected stacks after restoring (`docker compose
restart`).

## 10. Re-join Tailscale

```bash
sudo tailscale up --ssh --hostname <hostname> --advertise-tags=<tag:server>
tailscale status
```

(See `scripts/network/tailscale-install-up.sh`.)

## 11. Confirm GREEN

- [ ] **Beszel** (`status.<domain>`): host + agent reporting, metrics flowing.
- [ ] **Uptime Kuma** (`uptime.<domain>`): all monitors for this host green.
- [ ] **Dependency-Track** (`deptrack.<domain>`): `host:<hostname>` project
      present and a fresh BOM uploaded (trigger `sbom-nightly.service` manually:
      `sudo systemctl start sbom-nightly.service`).
- [ ] Spot-check the key apps load over Caddy/HTTPS.

---

### Drill log

| date | drilled by | VM/host | result | notes |
|------|-----------|---------|--------|-------|
| YYYY-MM-DD | | throwaway VM | pass/fail | |

> Quarterly cadence. If a step failed or drifted, fix it here immediately while
> it's fresh.

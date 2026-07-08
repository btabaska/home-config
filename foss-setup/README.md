# foss-setup — Going Analogue: a FOSS homelab, as code

This is the **config-as-code companion** to *Going Analogue: A FOSS Computing
Setup* — the reference build for moving off the Apple/iOS ecosystem onto your own
hardware. The prose guide explains *why*; this repo holds the *how*: every Docker
Compose file, config template, and idempotent setup script needed to stand the
whole thing up — and to **rebuild it in an hour** when a disk dies or you migrate
a host.

> **The one habit that makes it all work:** everything here lives in Git. Disk
> dies or you migrate → `git clone` + fill in `.env` + `docker compose up -d` and
> you're back. That turns a homelab from *fragile* into *disposable-and-
> rebuildable*. See `configs/git/repo-structure.md`.

---

## The hardware this targets

| Tier | Host | Role |
|---|---|---|
| Always-on | **DS920+ NAS** | three Basic volumes (~42 TB): Vol 1 Music/Books/Tier1/Docker, Vol 2 Movies, Vol 3 TV; Immich, Plex, CWA, *arr stack, backups |
| Always-on | **Mac mini → Ubuntu Server** (~12W) | the Docker stack, light game servers |
| Always-on | **UniFi Dream Wall** | router + firewall + switch + WiFi + controller |
| Always-on (24/7 since 2026-07-08) | **CachyOS rig** (3090 Ti / 12700K) | local LLM, game streaming, heavy game servers; WoL kept as recovery only |
| Off-site | **Managed seedbox** | the whole P2P download stack, invisible to the ISP |

---

## Repository layout

```
foss-setup/
├── README.md                  # you are here
├── docs/                      # the generated HTML guide (built by the orchestrator)
├── configs/                   # DECLARATIVE desired state — compose files + app config
│   ├── network/               # UniFi VLAN/firewall/mDNS plans + SSH access (Tailscale SSH ACL, ssh config)
│   ├── ansible/               # fleet maintenance: inventory + patch/reboot/audit playbooks
│   ├── docker-stack/          # the Mac mini stack; mirrors /opt/stacks 1:1 (Dockge)
│   │   ├── stacks/<svc>/       # seerr, miniflux, navidrome, caddy, adguard, dockge,
│   │   │                       #   beszel, uptime-kuma, ntfy, diun
│   │   └── alternatives/       # pihole (vs adguard), dockhand (vs dockge)
│   ├── nas/                   # Synology containers: immich, calibre-web-automated + backup
│   ├── homeassistant/         # HA config, automations, Midea/Nest setup, backups
│   ├── seedbox/               # *arr wiring, rclone, provider comparison, decommission
│   ├── inventory/             # SBOM/inventory layer (Phase 4): inventory.md, Dependency-Track Homepage widget, etckeeper + restore-runbook template
│   └── git/                   # Forgejo (self-hosted forge) + repo-structure + secrets
├── scripts/                   # IMPERATIVE, idempotent (set -euo pipefail) setup
│   ├── network/               # tailscale install / verify-direct / connectivity
│   ├── setup/                 # host baselines: docker, NUT client, HAOS VM, desktop
│   ├── dotfiles/              # chezmoi bootstrap + quickstart
│   ├── backup/                # restic, borgmatic, restore-test
│   ├── media/                 # seedbox sync, iPod tools, tailscale verify
│   ├── reading/               # KOReader/CWA/Wallabag wiring, syncthing
│   ├── inventory/             # SBOM generation/export: Syft+Grype, manifest exports, the SBOM systemd timer/units
│   └── gaming/                # WoL, GPU power tune, Apollo (Sunshine fork), LinuxGSM
```

**Two kinds of content, deliberately separated:**
- **`configs/`** = declarative state. Checked in verbatim; this is what
  `docker compose up` consumes.
- **`scripts/`** = imperative, idempotent bootstrap. Every script is
  `set -euo pipefail` and safe to re-run; they take a bare host to the point
  where the configs can be applied.

---

## How to use the HTML guide (`docs/`)

`docs/` holds a single self-contained HTML build of the full *Going Analogue*
guide — open `docs/index.html` in any browser, no server needed. It's the
human-readable narrative (the *why* and the decisions); this repo's `configs/`
and `scripts/` are the machine-actionable *how* it points at. Read the relevant
section in the HTML, then run the matching script / bring up the matching stack.

---

## Phased rollout

Do a phase before starting the next — each one leaves you strictly better off.

- **Phase 1 — Foundation (network, access, safety net).** UniFi segmentation +
  zone-based firewall (`configs/network/`), Tailscale everywhere
  (`scripts/network/`) — including **key-less Tailscale SSH + a `~/.ssh/config`
  fallback** for easy, secure maintenance access to every box
  (`scripts/network/tailscale-ssh-enable.sh`,
  `configs/network/ssh-maintenance-access.md`) — backups + a tested restore
  (`scripts/backup/`), and **UPS power resilience**
  (`scripts/setup/nut-client-ubuntu.sh`). The **dotfiles + browser/office desktop
  baseline** can also be done here (or anytime) — they're independent of the
  servers.
- **Phase 2 — De-cloud the essentials.** Home Assistant
  (`configs/homeassistant/`), the off-site seedbox pipeline (`configs/seedbox/`,
  `scripts/media/`), Immich (`configs/nas/immich/`).
- **Phase 3 — The analogue media stack.** Calibre-Web-Automated + KOReader +
  Syncthing (`configs/nas/calibre-web-automated/`, `scripts/reading/`), iPod via
  Rhythmbox/libgpod (`scripts/media/`), Miniflux + Navidrome
  (`configs/docker-stack/stacks/`).
- **Phase 4 — Glue & polish.** The management layer — Dockge/Dockhand, Beszel,
  Uptime Kuma, ntfy, Caddy, AdGuard (`configs/docker-stack/`) — **config-as-code
  in Git** via Forgejo (`configs/git/`), and **fleet maintenance with Ansible**
  (`configs/ansible/`) to patch/reboot/audit every box in one command. This is
  where the whole repo becomes rebuildable.
- **Phase 5 — Play.** Game servers (LinuxGSM/Pelican) and Apollo + Moonlight
  streaming (Apollo is a maintained Sunshine fork — headless/virtual-display +
  per-client perms suit the 24/7 rig), with GPU/idle-power tuning (`scripts/gaming/`;
  Wake-on-LAN stays set up as recovery tooling only).

---

## The set-and-forget philosophy

This build optimizes for **quiet until something needs you**, not for novelty.

1. **Config-as-code in Git.** All compose files + configs are versioned, so any
   host is reproducible. Secrets and runtime state stay *out* of Git (`.env.example`
   templates + a secrets manager + separate backups).
2. **Pin versions, never `:latest`.** Every image is pinned. Updates are
   *notify-only* (Diun → ntfy); you bump tags deliberately after reading release
   notes. No 3am surprise breakage from a blind auto-pull.
3. **Right host for the job.** Cheap always-on gear (~$150/yr total) runs the light
   24/7 services; the power-hungry rig **also runs 24/7** (decision 2026-07-08:
   ~130W idle ≈ $23/mo accepted for availability; idle-power tuning open). WoL is
   recovery tooling only — an unreachable rig is an incident, not expected sleep.
4. **3-2-1 backups, with a tested restore.** RAID is not a backup. Tier-1
   irreplaceable data goes off-site; an *untested* backup is just a hope.
5. **Power resilience.** UPS on the NAS + Ubuntu box + Dream Wall; the NAS does a
   graceful USB shutdown, the Ubuntu box listens over the network via **NUT** so a
   brief fiber-outage flicker never corrupts a DB mid-write.
6. **Rebuild drill.** Prove "rebuild in an hour" *once* on a clean VM, before the
   disk actually dies — that's how you find the gaps while it's still cheap.

---

## Quick start (per host)

```bash
# 1. Clone this repo onto the host (or into /opt/stacks on the Ubuntu box)
git clone <your-forgejo-or-github-url> foss-setup && cd foss-setup

# 2. Run the relevant idempotent baseline from scripts/setup/, e.g.:
sudo ./scripts/setup/install-docker-ubuntu.sh           # Ubuntu Docker host
sudo NAS_IP=192.168.10.4 ./scripts/setup/nut-client-ubuntu.sh   # UPS monitoring
./scripts/setup/cachyos-desktop-baseline.sh             # CachyOS browser+office

# 3. Bring up a stack: copy the env template, fill secrets, then up
cd configs/docker-stack/stacks/<svc>
cp .env.example .env && ${EDITOR:-nano} .env
docker compose up -d
```

See each folder's own `README.md` / `*.md` for the specifics.

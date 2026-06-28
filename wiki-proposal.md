# Wiki Proposal — *Going Analogue* Operations Manual

A single, locally-hosted source of truth for **running and maintaining** the
homelab: a man-page-style user guide that sits alongside the existing
`foss-setup/` repo and is served from the Mac mini over your LAN/Tailscale.

This document is a **proposal only** — nothing is built yet. It defines the
tooling, the page structure, how content maps from what already exists, the
authoring conventions, the maintenance workflow, and a phased build plan.

---

## 1. What this wiki is (and isn't)

| | |
|---|---|
| **Is** | The day-2 *operations manual*. "How do I run / check / fix / update X." Stable reference, man-page tone, one page per service and per script. |
| **Isn't** | The *rollout tracker* (`docs/index.html` already does that — 134 tasks, checkbox progress) or the *narrative* (the *why*). The wiki **links out** to both rather than duplicating them. |

The split mirrors the one you already drew in `README.md`: `configs/` =
declarative, `scripts/` = imperative. The wiki is the **third leg — operational**:
how to *operate* the thing the other two stand up.

Guiding principle: the wiki is **generated from the repo wherever possible**, so
it can't drift. Hand-written prose only where judgment is needed (runbooks,
troubleshooting, architecture).

---

## 2. Tooling decision — MkDocs Material in Docker, behind Caddy

Per your constraint ("hostable on the local network from the Mac mini via
Docker"), the recommendation is **MkDocs + Material theme**, served as a
container in your existing `docker-stack`, routed through Caddy like every other
service.

Why this over the alternatives:

- **Markdown source, Git-native.** Pages live in the same repo (`foss-setup/wiki/`),
  versioned with everything else. Fits the config-as-code ethos exactly — a wiki
  edit is a commit, same as a compose bump.
- **Built-in full-text search**, instant nav, dark theme that matches the
  existing `index.html` palette (you're already on a GitHub-dark look).
- **Static output.** `mkdocs build` emits plain HTML; no runtime dependency, no
  database. Caddy serves the static folder — fast and disposable-rebuildable.
- **First-class admonitions, tabs, code copy, keyboard shortcuts** — ideal for
  man-page-style reference (warning blocks for one-way doors like ZBF, tabbed
  per-host commands, etc.).
- **Plays with your automations.** You already generate/patch `index.html` with
  Python; the same pattern generates Markdown reference pages from scripts and
  compose files (see §5).

### Hosting shape (sketch — to be finalized at build time)

Two viable patterns, both Docker on the Mac mini:

**A. Build + serve static (recommended).** A one-shot builder container runs
`mkdocs build` into a volume; Caddy serves the static site. Rebuild on commit
(Forgejo webhook or the same Ansible pull you already run). Zero moving parts at
runtime.

**B. Live server.** `squidfunk/mkdocs-material serve` container with
auto-reload — nice while authoring, heavier to leave running. Good for the
build-out phase, switch to A for steady state.

```
configs/docker-stack/stacks/wiki/
├── compose.yaml        # mkdocs-material (build) + tie-in to caddy network
├── .env.example
└── (source lives in foss-setup/wiki/, mounted read-only)
```

Caddy route: `wiki.<your-domain-or-tailnet>` → static folder. Access scoped the
same way your other internal services are (Tailscale + LAN), so it's reachable
from any device on the tailnet without exposing it publicly.

---

## 3. Information architecture

Top-level sections map to **how you actually reach for docs in an emergency**:
by host, by service, by task. Tracks/tiers from `index.html` inform the grouping
but the wiki is organized for *lookup*, not *sequence*.

```
Home
├── Overview
│   ├── What this is / how to use the wiki
│   ├── Architecture at a glance      (the 5 hosts, the data flow diagram)
│   ├── Host inventory                (DS920+, Mac mini/Ubuntu, Dream Wall,
│   │                                  CachyOS, seedbox — specs, roles, IPs/VLANs)
│   ├── Conventions & glossary        (SYNC/ASYNC, version-pinning, .env policy)
│   └── Links out: Rollout tracker (index.html) · Narrative guide · Validation report
│
├── Hosts                              (one operational page per box)
│   ├── NAS (DS920+)                   storage schema, volumes, Container Manager
│   ├── Ubuntu Docker host             /opt/stacks, Dockge, power budget
│   ├── UniFi Dream Wall               VLANs, zone-based firewall, backups
│   ├── CachyOS rig                    on-demand, WoL, GPU tuning, streaming
│   └── Seedbox                        off-site stack, rclone mounts
│
├── Services                           (THE CORE — one man-page per service)
│   ├── Networking & Access
│   │   ├── Tailscale (SSH, ACLs, direct-path verify)
│   │   ├── Caddy (reverse proxy)
│   │   ├── AdGuard / Unbound (DNS)
│   │   └── SSH maintenance access
│   ├── Media
│   │   ├── Plex · Tautulli · Kometa · Maintainerr
│   │   ├── *arr suite (Sonarr/Radarr/Lidarr/Readarr/Bazarr/Prowlarr)
│   │   ├── Recyclarr · Tdarr · Unpackerr
│   │   ├── slskd + soularr · qbittorrent/VPN
│   │   └── Pinchflat / MeTube
│   ├── Photos & Reading
│   │   ├── Immich
│   │   ├── Calibre-Web-Automated + KOReader + Syncthing
│   │   └── Wallabag · Miniflux · Navidrome
│   ├── Smart Home
│   │   └── Home Assistant (Midea/ESPHome, Nest SDM, automations, backups)
│   ├── Apps & Productivity
│   │   ├── Paperless-ngx · Mealie · Forgejo (git) · LiteLLM
│   ├── Monitoring & Ops
│   │   ├── Dockge/Dockhand · Beszel · Uptime Kuma · ntfy · Diun
│   │   └── Healthchecks · Frigate
│   └── Each service page = the man-page template in §4
│
├── Operations (runbooks)             (hand-written; judgment lives here)
│   ├── Backups & restore             restic, borgmatic, restore-test, 3-2-1
│   ├── Rebuild-in-an-hour drill      the headline promise, step by step
│   ├── Updates & version bumps       Diun notify → read notes → bump tag → up
│   ├── Fleet maintenance (Ansible)   patch / reboot / audit playbooks
│   ├── Power / UPS (NUT)             graceful shutdown chain
│   ├── Inventory & SBOM              Syft/Grype, etckeeper, Dependency-Track
│   ├── Secrets & .env policy         what stays out of Git, where it lives
│   └── Adding a new service          the standard "stand up a stack" recipe
│
├── Scripts reference                 (AUTO-GENERATED — one entry per script)
│   ├── network/ · setup/ · backup/ · media/ · reading/ · inventory/ · gaming/
│   └── Each = NAME / SYNOPSIS / DESCRIPTION / ENV / EXAMPLES / SEE ALSO
│
├── Troubleshooting                   (symptom → cause → fix, cross-linked)
│   ├── "Service won't start" · "No remote access" · "Backup failed"
│   ├── "Media not importing" · "DNS broken" · per-host gotchas
│   └── One-way doors & footguns      (ZBF migration, etc.)
│
└── Maintenance calendar              daily/weekly/monthly/quarterly checklist
```

---

## 4. The man-page template (per service / per script)

Every reference page follows a fixed skeleton so you always know where to look.
Modeled on a Unix man page, adapted for a service:

```
# <service>            one-line role

NAME           what it is, in a sentence
HOST           which box it runs on  ·  URL  ·  VLAN
SYNOPSIS       the canonical commands (up / down / logs / restart)
DESCRIPTION    what it does here and how it fits the stack
CONFIG         source of truth path (configs/.../compose.yaml),
               key .env vars, pinned image tag
DEPENDS ON     upstream services (DNS, Caddy, NAS mount, VPN...)
DATA & STATE   volumes, where its DB/state lives, what's backed up
OPERATIONS     start/stop, update procedure, health check
TROUBLESHOOT   top 3–5 failure modes → fixes (links to Troubleshooting)
SEE ALSO       related services, the narrative section, upstream docs
```

Material renders the SYNOPSIS as a copy-button code block, DEPENDS ON as chips,
and footguns as `!!! warning` admonitions. Consistent, scannable, fast under
pressure.

---

## 5. How content maps from what already exists

The repo is ~80% of the wiki already — most pages are *assembled*, not written
from scratch.

| Source in repo | Becomes |
|---|---|
| `configs/docker-stack/stacks/<svc>/compose.yaml` + `.env.example` | The CONFIG / DATA / DEPENDS-ON fields of each **Service** page (parse image tag, ports, volumes, env keys). |
| `scripts/**/*.sh` header comments (you already write rich `# What it does` blocks) | The **Scripts reference** man-pages — NAME/SYNOPSIS/DESC/ENV/EXAMPLES extracted from the comment header + `set` flags. |
| `scripts/**/*.md` (quickstarts: chezmoi, koreader, linuxgsm, ipod, immich-go) | Folded into the matching Service/Operations page or kept as-is. |
| `configs/network/*.md` (firewall, VLAN, mDNS, SSH) | The **Dream Wall** host page + Networking services. |
| `configs/nas/*`, `nas-storage-schema.md` | The **NAS** host page (volume schema, the three-Basic-volume layout). |
| `configs/inventory/*`, `restore-runbook-template.md` | **Operations → Inventory/SBOM** and the restore runbook. |
| `game-servers-guide.md` (4.7k words) | **Services → Gaming** + CachyOS host page. |
| `foss-setup-plan-2.md` (18k words) | Mined for DESCRIPTION prose and architecture; **not** copied wholesale — it's the planning narrative. |
| `foss-setup-validation-report.md` | Seeds **Troubleshooting** + known-gaps notes. |
| `docs/index.html` taskData (134 tasks, links/`docs[]`) | Cross-links: each task's `docs[]` URLs and `verify` blocks feed SEE-ALSO and health checks. The wiki **links to** the tracker, doesn't absorb it. |

**Auto-generation:** extend the pattern you already use in
`scripts/docs/*.py`. Two small generators:

1. `gen-script-pages.py` — walk `scripts/`, parse each header comment block into a
   Markdown man-page. (~60 scripts → ~60 pages, zero hand-writing.)
2. `gen-service-pages.py` — walk `configs/**/compose.yaml`, emit the CONFIG/DATA
   skeleton per service; you fill the prose DESCRIPTION/TROUBLESHOOT by hand.

These run in CI / on commit, so the reference half of the wiki **regenerates from
the repo** and can't go stale — same philosophy as your existing HTML patchers.

---

## 6. Maintenance workflow (so it stays true)

1. **Source of truth is the repo, not the wiki.** Change a compose file → the
   service page's CONFIG block regenerates. The wiki never *holds* config, it
   *reflects* it.
2. **Edit = commit.** Wiki pages are Markdown in `foss-setup/wiki/`; changes go
   through Git/Forgejo like everything else.
3. **Rebuild on push.** Forgejo webhook (or the Ansible pull cadence) triggers
   `mkdocs build`; Caddy serves the new static site. No manual deploy.
4. **A "docs" check in the rebuild drill.** Add one line to the rebuild-in-an-hour
   runbook: bring the wiki up too, proving it's part of the disposable set.
5. **Stale-link guard.** `mkdocs build --strict` fails on broken internal links,
   so refactors can't silently rot the nav.

---

## 7. Build plan (phased, mirrors your rollout style)

- **Phase 0 — Skeleton.** `mkdocs.yml`, Material theme tuned to the dark palette,
  the section tree from §3 as empty stubs, Docker/Caddy hosting working on the
  Mac mini. *Outcome: an empty but live, LAN-reachable wiki.*
- **Phase 1 — Auto-generate the reference half.** Write the two generators (§5);
  Scripts reference + Service CONFIG skeletons populate themselves. *Outcome: ~120
  reference pages with zero prose written.*
- **Phase 2 — Runbooks.** Hand-write Operations (backups/restore, rebuild drill,
  updates, fleet maintenance, secrets). This is the high-value human writing.
- **Phase 3 — Host + architecture pages, diagrams, glossary.** Pull from the NAS
  schema, network docs, game guide.
- **Phase 4 — Troubleshooting + maintenance calendar.** Mine the validation report
  and your own scar tissue; cross-link symptom → service → fix.
- **Phase 5 — Wire the loop.** Webhook/Ansible auto-rebuild, `--strict` link
  check, add the wiki to the rebuild drill.

---

## 8. Open decisions for you

1. **Source location** — `foss-setup/wiki/` inside the existing repo (recommended,
   one clone rebuilds everything) vs. a separate repo.
2. **Hosting pattern** — static build + Caddy (steady state) vs. live `mkdocs
   serve` (authoring). Suggest: live during Phases 0–4, static after.
3. **Access scope** — Tailnet-only, LAN-only, or both. Suggest: both, no public
   exposure.
4. **How much auto-gen vs. hand prose** — comfortable with the two-generator
   approach, or prefer fully hand-written pages for control?
5. **Diagrams** — Mermaid (text-as-code, fits the ethos) for the architecture and
   data-flow diagrams?

Tell me which way you land on these and I'll move to Phase 0 (skeleton +
Docker/Caddy hosting) whenever you're ready.

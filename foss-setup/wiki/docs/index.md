# Going Analogue — Homelab Manual

This wiki is the **operations manual** for the tabaska.us homelab: how to run,
check, fix, update, and rebuild everything. It is written for two readers —
the human operator, and **future AI agents** working a session against this
fleet. If you are an agent: read this page, then [Operations → Tracker &
AI sessions](operations/tracker.md) before touching anything.

## What this homelab is

A **local-first** setup: moving off the Apple/iCloud ecosystem onto owned
hardware — photos (Immich), media (Plex + the *arr pipeline), reading
(Miniflux/Wallabag/CWA), documents (Paperless-ngx), recipes (Mealie), smart
home (Home Assistant), local LLMs (rig), self-hosted git (Forgejo). Local-first
is the principle, not a purity test: **Obsidian Sync, Backblaze B2, and
Tailscale** are the deliberate cloud exceptions.

Three documents divide the world:

| Document | Role |
|---|---|
| `foss-setup-plan-2.md` (repo root) | The **why** — the full design narrative |
| `foss-setup/docs/index.html` | The **what/when** — Plan v3 rollout tracker, 194 tasks in 8 staged runs |
| **This wiki** (`foss-setup/wiki/`) | The **how to operate** — stable reference + runbooks |

Guiding rule: the wiki is **generated from the repo wherever possible** so it
can't drift ([Services](services/index.md) pages are machine-generated from
compose files). Hand-written prose lives only where judgment is needed.

## The map — hosts

| Host | Alias / IP | Role | Power | Managed by |
|---|---|---|---|---|
| [mini](hosts/mini.md) | `mini` · 192.168.10.2 | Ubuntu Docker host — the always-on web/management stack, Caddy, primary DNS, Forgejo | 24/7 (~12 W) | ansible-pull + Dockge |
| [nas](hosts/nas.md) | `nas` · 192.168.10.4 | Synology DS920+ — storage, Immich, Plex, CWA, *arr stack, secondary DNS | 24/7 | DSM UI (Container Manager) |
| [rig](hosts/rig.md) | `rig` · 192.168.10.12 | CachyOS — local LLMs, Sunshine streaming, heavy game servers | 24/7 (~130 W idle; WoL kept for recovery) | ansible-pull (pending: glue-08) |
| [seedbox](hosts/seedbox.md) | `seedbox` (Betty) | Off-site Bytesized box — Deluge + slskd, all P2P off the home network | Managed 24/7 | user-space only (no root) |
| [gateway](hosts/gateway.md) | 192.168.10.1 | UniFi Dream Wall — routing, VLANs, firewall, WiFi, DHCP | 24/7 | UniFi GUI only |
| [home-assistant](hosts/home-assistant.md) | 192.168.10.50 | HA Green — smart-home hub | 24/7 (~3 W) | HA itself (appliance) |

See [Network](network.md) for VLANs, the DNS chain, Tailscale, and the
`*.tabaska.us` wildcard.

## The map — where everything lives

| Repo | Where | What it is |
|---|---|---|
| **GitHub `btabaska/home-config`** | `origin` of `~/Documents/Home` | The **full** planning repo: plan, tracker, `foss-setup/` configs+scripts+this wiki |
| **Forgejo `home/homelab`** (on mini) | published subtree | The **deploy repo** = the `foss-setup/` subtree; hosts run `ansible-pull` against it. Published via `scripts/docs/publish-deploy.sh` |
| **Forgejo `home/docker-stacks`** | `/opt/stacks` on mini | The **live** compose state actually running on the mini |

Flow: edit in `home-config` → `publish-deploy.sh` fast-forwards Forgejo
`home/homelab` → hosts converge via ansible-pull. `/opt/stacks` is the live
mirror of the mini's stacks and must stay committed (a dirty `/opt/stacks`
means a rebuild would not reproduce the running mini).

**Secrets** live ONLY in `foss-setup/.handoff-secrets.yaml` (gitignored,
chmod 600). Nothing else — no doc, no commit, no chat transcript — may contain
a credential. See [Secrets policy](operations/secrets.md).

## How this wiki is built

- Source: `foss-setup/wiki/` (Markdown, MkDocs Material).
- Service pages are generated: `python3 foss-setup/scripts/docs/gen-wiki-services.py`.
- Build + deploy: `foss-setup/scripts/docs/build-wiki.sh` (dockerized pinned
  build on the mini → static site at `/opt/stacks/wiki/site`, served by Caddy
  at <https://wiki.tabaska.us>).
- A change to a service ⇒ regenerate + redeploy the wiki in the same session
  (drift check pending: wiki-05).

# Inventory — macmini (sample)

> **Auto-generated** by `scripts/inventory/gen-inventory-md.sh` (invoked nightly/
> weekly by `export-manifests.sh` via `export-manifests.timer`).
> **Do not edit by hand** — your changes will be overwritten. Adjust the generator
> or the source manifests under `hosts/<hostname>/` instead.
>
> This committed copy is a *sample* showing the shape; the real file is rewritten
> on each host from its own manifests.
>
> Generated: 2026-06-26T03:30:11-04:00

## Host

| what | where | version | status |
|------|-------|---------|--------|
| OS | macmini | Ubuntu 24.04.2 LTS | active |
| Kernel | macmini | 6.8.0-51-generic | active |

## Software & services

| what | where | version | status |
|------|-------|---------|--------|
| apt manual packages | `hosts/macmini/` | 142 pkgs | tracked |
| AUR/foreign packages | `hosts/macmini/pkglist.aur.txt` | 0 pkgs | tracked |
| Flatpak apps | `hosts/macmini/flatpak.txt` | 0 apps | tracked |
| Compose images (pinned) | `/opt/stacks` | 13 images | pinned |
| Running containers | docker | 13 up | active |
| systemd timers | `hosts/macmini/systemd-timers.txt` | 4 active | scheduled |

## Pinned container images

| image:tag | source |
|-----------|--------|
| `adguard/adguardhome:v0.107.77` | /opt/stacks |
| `caddy:2.11.4-alpine` | /opt/stacks |
| `crazymax/diun:4.33.0` | /opt/stacks |
| `dependencytrack/apiserver:5.6.0` | /opt/stacks |
| `dependencytrack/frontend:5.6.0` | /opt/stacks |
| `ghcr.io/seerr-team/seerr:v3.2.0` | /opt/stacks |
| `henrygd/beszel:0.18.7` | /opt/stacks |
| `henrygd/beszel-agent:0.18.7` | /opt/stacks |
| `louislam/dockge:1.5.0` | /opt/stacks |
| `louislam/uptime-kuma:2.1.1` | /opt/stacks |
| `miniflux/miniflux:2.3.0` | /opt/stacks |
| `postgres:17-alpine` | /opt/stacks |
| `binwiederhier/ntfy:v2.19.2` | /opt/stacks |

---

_See `hosts/macmini/` for the raw manifests (package lists, crontabs, timers).
Restore procedure: `configs/inventory/restore-runbook-template.md`._

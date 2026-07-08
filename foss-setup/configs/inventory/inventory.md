# Inventory — macmini

> **Auto-generated** by `scripts/inventory/gen-inventory-md.sh` (invoked nightly/
> weekly by `export-manifests.sh` via `export-manifests.timer`).
> **Do not edit by hand** — your changes will be overwritten. Adjust the generator
> or the source manifests under `hosts/macmini/` instead.
>
> Generated: 2026-07-06T04:15:31+00:00

## Host

| what | where | version | status |
|------|-------|---------|--------|
| OS | macmini | Ubuntu 22.04.3 LTS | active |
| Kernel | macmini | 5.15.0-185-generic | active |

## Software & services

| what | where | version | status |
|------|-------|---------|--------|
| apt manual packages | `hosts/macmini/` | 74 pkgs | tracked |
| AUR/foreign packages | `hosts/macmini/pkglist.aur.txt` | 0 pkgs | tracked |
| Flatpak apps | `hosts/macmini/flatpak.txt` | 0 apps | tracked |
| Compose images (pinned) | `/opt/stacks` | 39 images | pinned |
| Running containers | docker | 38 up | active |
| systemd timers | `hosts/macmini/systemd-timers.txt` | 18 active | scheduled |

## Pinned container images

| image:tag | source |
|-----------|--------|
| `adguard/adguardhome:v0.107.77` | /opt/stacks |
| `apache/tika:3.2.1.0-full` | /opt/stacks |
| `binwiederhier/ntfy:v2.19.2` | /opt/stacks |
| `codeberg.org/forgejo/forgejo:15.0.1` | /opt/stacks |
| `crazymax/diun:4.33.0` | /opt/stacks |
| `deluan/navidrome:0.62.0` | /opt/stacks |
| `dependencytrack/apiserver:5.0.2` | /opt/stacks |
| `dependencytrack/frontend:5.0.1` | /opt/stacks |
| `ghcr.io/berriai/litellm:v1.88.2` | /opt/stacks |
| `ghcr.io/blakeblackshear/frigate:0.17.1` | /opt/stacks |
| `ghcr.io/gethomepage/homepage:v1.13.2` | /opt/stacks |
| `ghcr.io/habirabbu/musicseerr:v1.4.2` | /opt/stacks |
| `ghcr.io/haveagitgat/tdarr:2.78.01` | /opt/stacks |
| `ghcr.io/hotio/bazarr:latest` | /opt/stacks |
| `ghcr.io/hotio/radarr:latest` | /opt/stacks |
| `ghcr.io/hotio/sabnzbd:latest` | /opt/stacks |
| `ghcr.io/hotio/sonarr:latest` | /opt/stacks |
| `ghcr.io/kieraneglin/pinchflat:v2025.6.6` | /opt/stacks |
| `ghcr.io/maintainerr/maintainerr:3.15.3` | /opt/stacks |
| `ghcr.io/mealie-recipes/mealie:v3.4.0` | /opt/stacks |
| `ghcr.io/paperless-ngx/paperless-ngx:2.20.11` | /opt/stacks |
| `ghcr.io/recyclarr/recyclarr:7.4.2` | /opt/stacks |
| `ghcr.io/recyclarr/recyclarr:8.4.0` | /opt/stacks |
| `ghcr.io/seerr-team/seerr:v3.2.0` | /opt/stacks |
| `ghcr.io/tautulli/tautulli:v2.17.2` | /opt/stacks |
| `ghcr.io/zamnzim/libreseerr:latest` | /opt/stacks |
| `gotenberg/gotenberg:8.21` | /opt/stacks |
| `healthchecks/healthchecks:v3.10` | /opt/stacks |
| `henrygd/beszel:0.18.7` | /opt/stacks |
| `henrygd/beszel-agent:0.18.7` | /opt/stacks |
| `kometateam/kometa:v2.3.1` | /opt/stacks |
| `louislam/dockge:1.5.0` | /opt/stacks |
| `louislam/uptime-kuma:2.1.1` | /opt/stacks |
| `mariadb:11.4` | /opt/stacks |
| `miniflux/miniflux:2.3.1` | /opt/stacks |
| `mvance/unbound:1.22.0` | /opt/stacks |
| `postgres:17-alpine` | /opt/stacks |
| `redis:7-alpine` | /opt/stacks |
| `wallabag/wallabag:2.6.14` | /opt/stacks |

---

_See `hosts/macmini/` for the raw manifests (package lists, crontabs, timers).
Restore procedure: `configs/inventory/restore-runbook-template.md`._

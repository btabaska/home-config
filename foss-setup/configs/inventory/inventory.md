# Inventory — macmini

> **Auto-generated** by `scripts/inventory/gen-inventory-md.sh` (invoked nightly/
> weekly by `export-manifests.sh` via `export-manifests.timer`).
> **Do not edit by hand** — your changes will be overwritten. Adjust the generator
> or the source manifests under `hosts/macmini/` instead.
>
> Generated: 2026-08-06T09:17:36-04:00

## Host

| what | where | version | status |
|------|-------|---------|--------|
| OS | macmini | Ubuntu 22.04.3 LTS | active |
| Kernel | macmini | 5.15.0-185-generic | active |

## Software & services

| what | where | version | status |
|------|-------|---------|--------|
| apt manual packages | `hosts/macmini/` | 62 pkgs | tracked |
| AUR/foreign packages | `hosts/macmini/pkglist.aur.txt` | 0 pkgs | tracked |
| Flatpak apps | `hosts/macmini/flatpak.txt` | 0 apps | tracked |
| Compose images (pinned) | `/opt/stacks` | 45 images | pinned |
| Running containers | docker | 48 up | active |
| systemd timers | `hosts/macmini/systemd-timers.txt` | 29 active | scheduled |

## Pinned container images

| image:tag | source |
|-----------|--------|
| `adguard/adguardhome:v0.107.77` | /opt/stacks |
| `apache/tika:3.2.1.0-full` | /opt/stacks |
| `binwiederhier/ntfy:v2.19.2` | /opt/stacks |
| `brainicism/bgutil-ytdlp-pot-provider:latest` | /opt/stacks |
| `codeberg.org/forgejo/forgejo:15.0.1` | /opt/stacks |
| `crazymax/diun:4.33.0` | /opt/stacks |
| `deluan/navidrome:0.62.0` | /opt/stacks |
| `ghcr.io/analogj/scrutiny@sha256:e0d55d2742017c7025e491e05eb516bc71758c575f7e0bfefe34f9ce13aced89` | /opt/stacks |
| `ghcr.io/blakeblackshear/frigate:0.17.1` | /opt/stacks |
| `ghcr.io/gethomepage/homepage:v1.13.2` | /opt/stacks |
| `ghcr.io/habirabbu/musicseerr:v1.4.2` | /opt/stacks |
| `ghcr.io/mealie-recipes/mealie:v3.4.0` | /opt/stacks |
| `ghcr.io/paperless-ngx/paperless-ngx:2.20.11` | /opt/stacks |
| `ghcr.io/recyclarr/recyclarr:8.4.0` | /opt/stacks |
| `ghcr.io/seerr-team/seerr:v3.2.0` | /opt/stacks |
| `ghcr.io/speaches-ai/speaches:0.8.3-cpu@sha256:21e3df06d842fb7802ab470dd77c25f0e8c0d22950e8d8c6ae886e851af53ef8` | /opt/stacks |
| `ghcr.io/tautulli/tautulli:v2.17.2` | /opt/stacks |
| `ghcr.io/zamnzim/libreseerr@sha256:820134e44279c964ddf54090ab45b444a28e7f562256baaadf20fffaf36911f3` | /opt/stacks |
| `gotenberg/gotenberg:8.21` | /opt/stacks |
| `healthchecks/healthchecks:v3.10` | /opt/stacks |
| `henrygd/beszel:0.18.7` | /opt/stacks |
| `henrygd/beszel-agent:0.18.7` | /opt/stacks |
| `kometateam/kometa:v2.4.6` | /opt/stacks |
| `louislam/dockge:1.5.0` | /opt/stacks |
| `louislam/uptime-kuma:2.1.1` | /opt/stacks |
| `mariadb:11` | /opt/stacks |
| `mariadb:11.4` | /opt/stacks |
| `metube-bgutil:local` | /opt/stacks |
| `miniflux/miniflux:2.3.1` | /opt/stacks |
| `mozzo/booklogr:v1.11.1` | /opt/stacks |
| `mozzo/booklogr-web:v1.11.1` | /opt/stacks |
| `mvance/unbound:1.22.0` | /opt/stacks |
| `n8nio/n8n:2.32.2@sha256:119afa425cc1ac3e62823c65aae16fcee409ef4c94555ebab3a9dff6eccb9073` | /opt/stacks |
| `neosmemo/memos:0.29.1@sha256:3e1253477066eb2aefa91145f7f9038bb931ed88c8a3ee05310a933594cdba7d` | /opt/stacks |
| `pinchflat-bgutil:local` | /opt/stacks |
| `postgres:17-alpine` | /opt/stacks |
| `python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de` | /opt/stacks |
| `redis:7-alpine` | /opt/stacks |
| `rommapp/romm:4.9.2` | /opt/stacks |
| `ryshe/terraria:tshock-1.4.5.6-6.1.0` | /opt/stacks |
| `searxng/searxng:2026.8.4-c63835bd2` | /opt/stacks |
| `strausmann/minecraft-bedrock-connect:latest` | /opt/stacks |
| `syncthing/syncthing:2.1.2@sha256:4464f4161dd0251e20d46bb3aec83363db75d80cef1abdd5d5fd4054b04a004d` | /opt/stacks |
| `triliumnext/trilium:v0.104.1` | /opt/stacks |
| `wallabag/wallabag:2.6.14` | /opt/stacks |

---

_See `hosts/macmini/` for the raw manifests (package lists, crontabs, timers).
Restore procedure: `configs/inventory/restore-runbook-template.md`._

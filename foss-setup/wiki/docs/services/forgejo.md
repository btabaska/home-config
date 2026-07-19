# forgejo

Forgejo — self-hosted Git forge (the "rebuild in an hour" backbone)

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | https://git.tabaska.us |
| **Source** | `foss-setup/configs/docker-stack/stacks/forgejo/docker-compose.yml` |
| **Notes** | Git forge / control repo. SSH on host :2222. Container port 3000. |
| **Upstream docs** | <https://forgejo.org/docs/latest/admin/installation/docker/> · <https://forgejo.org/docs/latest/admin/config-cheat-sheet/> · <https://forgejo.org/docs/latest/admin/release-schedule/> |

## About

Forgejo is a self-hosted Git forge running on the always-on Mac mini (`192.168.10.2`) at https://git.tabaska.us, fronted by Caddy on the shared external `edge` docker network. Its compose is mirrored at `foss-setup/configs/docker-stack/stacks/forgejo/docker-compose.yml` (deployed to `/opt/stacks/forgejo` on the host; until fix-41 2026-07-19 the mirror hid at `configs/git/` — a path nothing else used, so the 2026-07-16 drift audit reported the deploy control plane as having NO repo mirror (M48) when it was actually byte-identical) and pairs `codeberg.org/forgejo/forgejo:15.0.1` (pinned to the 15.0 LTS, supported until 2027-07-15) with a `postgres:17-alpine` backend; the web UI is published on host `:3030` (avoiding AdGuard's `:3000`) and git-over-SSH on host `:2222` (host `:22` is the box's own sshd). Beyond being a code host it is the deploy control plane: `publish-deploy.sh` pushes `main` to GitHub and to the `forgejo:home/homelab` repo, which every host then `ansible-pull`s against. Since 2026-07-14 `home/homelab` holds the FULL planning repo (root = `Home/`, the pre-2026-07-14 `git subtree split` flow is retired), so hosts consume `foss-setup/`-prefixed paths (`foss-setup/configs/`, `foss-setup/scripts/`, ...). Critical app.ini settings (DB, domain, SSH port, LFS, `DISABLE_REGISTRATION=true`, `REQUIRE_SIGNIN_VIEW=true`) are injected via `FORGEJO__*` env vars from `.env` rather than a tracked app.ini. Rebuild story since fix-41: the full live `.env` (including `FORGEJO_DB_PASSWORD`) is captured in the gitignored vault at `forgejo.env` and the web admin credential (`btabaska`) at `forgejo.admin_user`/`admin_password`, so a dead mini rebuilds from GitHub mirror + vault with no archaeology; the `stack-mirror-drift` verification check alerts if this (or any) live mini stack ever diverges from its repo mirror again.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `forgejo` | `codeberg.org/forgejo/forgejo:15.0.1` | `3030:3000`, `${FORGEJO_SSH_PORT:-2222}:22` |
| `db` | `postgres:17-alpine` | — |

## Volumes

| Service | Volume |
|---|---|
| `forgejo` | `./data/forgejo:/data` |
| `forgejo` | `/etc/localtime:/etc/localtime:ro` |
| `forgejo` | `/etc/timezone:/etc/timezone:ro` |
| `db` | `./data/db:/var/lib/postgresql/data` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `FORGEJO_UID`
- `FORGEJO_GID`
- `FORGEJO_DB_PASSWORD`
- `FORGEJO_DOMAIN`
- `FORGEJO_ROOT_URL`
- `FORGEJO_SSH_PORT`
- `FORGEJO_DISABLE_REGISTRATION`
- `FORGEJO_REQUIRE_SIGNIN`

## Troubleshooting

- **After a force-push that replaces the home/homelab lineage (e.g. the 2026-07-14 subtree->full-repo topology switch), host ansible-pull clones diverge and stop fast-forwarding.** — Refresh the stale clone so it re-clones on the next timer fire: rm -rf ~/.ansible-pull on mini AND rig. Normal publishes are plain fast-forward pushes and need no cleanup.
- **Bind-mounted ./data/forgejo ends up root-owned or Forgejo can't write to /data.** — The container chowns /data to USER_UID/USER_GID on start; set FORGEJO_UID / FORGEJO_GID in /opt/stacks/forgejo/.env to the host user's real id -u / id -g (1000/1000) so the bind mount is owned correctly, then docker compose up -d.
- **Major-version bump (e.g. 15.x -> 16.x) risks breaking the instance.** — Only patch bumps within 15.0.x are safe/auto (Diun notifies). A major requires a manual, human-verified upgrade: read the Forgejo release notes first, back up ./data/db and ./data/forgejo, then pull. See https://forgejo.org/docs/latest/admin/release-schedule/.
- **Admin password unknown / vault entry missing or stale.** — Re-mint it in the container and re-vault — the CLI refuses to run as root, so exec as the app UID: ssh mini 'docker exec -u 1000 forgejo forgejo admin user change-password -u btabaska -p NEWPW --must-change-password=false', then verify consumer-end with basic-auth against https://git.tabaska.us/api/v1/user (expect is_admin true) and store user+password in the vault under forgejo. This is the fix-23/fix-41 procedure; git pushes are unaffected (ssh-key auth).
- **git push to forgejo from the mini fails with permission/auth errors when run as root.** — Root on the mini has no `forgejo` ssh alias — push as btabaska (this bites scripts run under sudo; drop privileges for the push step). The same rule is why the stack-mirror-drift check does its clone/fetch unprivileged and only runs the comparison under sudo.

## Operations

```bash
ssh mini 'cd /opt/stacks/forgejo && docker compose ps'
ssh mini 'cd /opt/stacks/forgejo && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/forgejo && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*

# Repo structure, branching & secrets

> Config-as-code layout for the homelab: how the repo is shaped so a dead disk or host migration is `git clone` → fill in `.env` → `docker compose up -d`, not an afternoon of archaeology.

_Source: `foss-setup/configs/git/repo-structure.md` · migrated + validated 2026-07-14_

The whole point: recovery is **`git clone` → fill in `.env` → `docker compose up -d`**. This page describes how to lay the repo out so it stays true.

The repo is self-hosted on **Forgejo** (see `foss-setup/configs/git/docker-compose.yml`) on the Mac mini, **and** mirrored to a **private GitHub repo**. Self-hosting keeps everything on your own metal; the private GitHub repo is the zero-maintenance off-site copy. Forgejo is primary, the GitHub mirror is the off-site copy (Forgejo can push-mirror automatically). This is the belt-and-suspenders setup.

!!! note "Validated against live repo (2026-07-14)"
    `git remote -v` at repo root (`/Users/brandontabaska/Documents/Home`) confirms **two remotes**, exactly the dual-remote model this doc prescribes:
    ```
    forgejo  git@forgejo:home/homelab.git      (fetch/push)
    origin   git@github.com:btabaska/home-config.git  (fetch/push)
    ```
    `main`, `remotes/forgejo/main`, and `remotes/origin/main` all exist. There is also a local `forgejo-main` branch and two `claude/*` feature branches.

---

## Recommended layout

The actual repo is the model. Note the real on-disk shape differs slightly from the idealized tree in the source: the git root is `/Users/brandontabaska/Documents/Home` (a `Home` monorepo) and the homelab lives in `foss-setup/` inside it.

The idealized shape that makes "rebuild in an hour" real:

```
foss-setup/
├── README.md                     # what this is + phased rollout
├── configs/                      # declarative state: compose files + app config
│   ├── docker-stack/             # Mac mini stack (mirrors /opt/stacks 1:1)
│   │   ├── stacks/<svc>/compose.yaml + .env.example
│   │   └── .gitignore            # ignores **/.env, data dirs
│   ├── nas/                      # Synology container configs (Immich, CWA, ...)
│   ├── network/                  # UniFi plans + SSH access (Tailscale SSH ACL, ssh config)
│   ├── ansible/                  # fleet maintenance: inventory + patch/reboot/audit playbooks
│   ├── homeassistant/            # HA configuration.yaml.example, automations
│   └── git/                      # Forgejo (this folder)
├── scripts/                      # imperative setup: idempotent bootstrap scripts
│   ├── setup/                    # host baselines (docker, NUT, desktop, HAOS)
│   ├── dotfiles/                 # chezmoi bootstrap
│   ├── backup/ network/ media/ reading/ gaming/
└── docs/                         # the generated HTML guide
```

!!! note "Validated against live repo (2026-07-14)"
    `ls foss-setup/` top level: `configs docs hosts README.md scripts verification wiki` (the doc's tree predates the `wiki/`, `hosts/`, and `verification/` dirs; `docs/` still exists).
    `ls foss-setup/configs/` shows more subdirs than the doc's tree: `ansible docker-stack gaming git homeassistant host inventory nas network seedbox systemd`.
    `foss-setup/configs/git/` contains `docker-compose.yml` and this source doc `repo-structure.md`.

### Two kinds of content, kept apart
- **`configs/`** = *declarative desired state* (compose files, Caddyfiles, HA YAML). Checked in verbatim. This is what `docker compose up` consumes.
- **`scripts/`** = *imperative, idempotent* setup. Every script is `set -euo pipefail`, safe to re-run, and does install-if-missing. These bootstrap a bare host to the point where the `configs/` can be applied.

### One folder per service, every folder self-contained
Each service lives in its own directory with its `compose.yaml` and a `.env.example`. That mirrors the **Dockge** convention (`/opt/stacks/<name>/`) so the manager discovers each stack, and it means any one service can be understood, backed up, or moved on its own.

!!! note "Validated against live mini (2026-07-14)"
    `ls /opt/stacks/` on the mini shows one directory per service, Dockge-style: `adguard backups bedrock-connect beszel bgutil-pot caddy dependency-track diun dockge forgejo frigate healthchecks homepage kometa libreseerr litellm maintainerr mealie metube miniflux musicseerr navidrome ntfy paperless-ngx pinchflat recyclarr romm seerr tautulli tdarr unbound uptime-kuma wallabag wiki`.

---

## The golden rule: configs in Git, **state and secrets out**

Three categories, three fates:

| Category | Examples | Goes in Git? | How it's recovered |
|---|---|---|---|
| **Config** | `compose.yaml`, `Caddyfile`, `*.example`, scripts | ✅ yes | `git clone` |
| **Secrets** | `.env`, API tokens, passwords, TLS keys | ❌ never | secrets manager (below) |
| **State/data** | Postgres dirs, `caddy_data`, photo library, DBs | ❌ never | backups (Restic/Borg) |

`git clone` restores config. Your **backup tooling** restores state. Your **secrets manager** restores secrets. Don't conflate them — a repo that contains secrets is a leak waiting to happen, and a repo bloated with state is unclonable.

---

## Secrets handling

**Never commit `.env`.** The pattern used throughout this repo:

1. Commit a **`.env.example`** template with every key present and dummy/empty values + comments on how to generate each one.
2. `.gitignore` the real files. A repo-root `.gitignore` should contain at least:

   ```gitignore
   # secrets
   **/.env
   .env
   *.key
   *.pem
   # runtime state (back up separately, don't version)
   **/data/
   **/db/
   **/conf/
   ```

3. Store the **real secret values** in a secrets manager so a fresh clone can be re-hydrated:
   - **Proton Pass** (you already pay for it) — paste each box's `.env` as a secure note, or store individual secrets. Zero new infra. *Recommended.*
   - **chezmoi + age** — if a secret belongs next to a dotfile, let chezmoi manage it encrypted (see `scripts/dotfiles/chezmoi-quickstart.md`). Good for personal machine secrets (SSH keys, tokens), not shared service `.env`s.
   - **SOPS + age** — if you want encrypted secrets *committed to the repo itself* (decryptable only with your age key). The power-user option; the age private key lives in your password manager, never in Git.

> Minimum viable + set-and-forget: `.env.example` in Git + the real `.env` contents in **Proton Pass**. Reach for SOPS only if you want one-command, fully-encrypted-in-repo restores.

!!! note "Validated against live repo (2026-07-14)"
    The `.env.example` convention is real and pervasive: **45** `*.example` files exist under `foss-setup/configs/` (e.g. `configs/git/.env.example`, `configs/nas/immich/.env.example`, `configs/seedbox/.env.example`, `configs/gaming/palworld/.env.example`).
    The actual repo-root `.gitignore` (`/Users/brandontabaska/Documents/Home/.gitignore`) is stricter than the template above — it also ignores the handoff secrets file and the migration snapshot:
    ```gitignore
    # macOS
    .DS_Store
    **/.DS_Store
    # Secrets — never commit
    .env
    **/.env
    .handoff-secrets.yaml
    **/.handoff-secrets.yaml
    # Runtime state / bind-mount data (back up separately, don't version)
    **/data/
    **/db/
    **/redis/
    **/cache/
    # Local server migration snapshot (contains Plex tokens, API keys, indexer cookies)
    migration-snapshot/
    __pycache__/
    ```
    The `docker-stack` sub-`.gitignore` (`foss-setup/configs/docker-stack/.gitignore`) is more granular still — it ignores live `**/config/*` but whitelists starter files (`!**/config/*.example`, `!**/config/services.yaml`, `!**/config/widgets.yaml`, `!**/config/settings.yaml`, `!**/config/bookmarks.yaml`, `!**/config/docker.yaml`) plus `**/.admin-password`, `**/images/`, `**/work/`, `**/lib/`, `**/beszel_data/`, `**/beszel_agent_data/`, `**/beszel_socket/`.

---

## Branching model (keep it boring)

A homelab is not a 12-person team. Optimize for "what was running last week" and "undo", not for elaborate flow:

- **`main` = what is (or should be) deployed.** Trunk-based. Commit small, commit often. Every commit is a restore point.
- **Short-lived branches for risky changes** (a major Immich bump, a firewall rework). Branch → test → merge to `main` → deploy. Delete the branch.
- **Tag milestones** you might want to roll back to: `git tag phase4-complete`, `git tag pre-immich-v3`. Tags are free, named restore points.
- **Commit messages that say *why*** ("pin immich to v3.0.1 after v3.1 broke ML") — your future self at 2am is the only reviewer.

!!! note "Validated against live repo (2026-07-14)"
    Trunk-based is real: work happens on `main`. Feature work uses short-lived `claude/*` branches (`claude/ha-device-integration-apple-home-4b702f`, `claude/libreseerr-diagnosis-34241d`). **No git tags exist yet** — `git tag` returns empty, so the "tag milestones" habit is aspirational, not yet in practice.

### The "rebuild in an hour" drill (do it once, for real)
1. `git clone <repo>` onto a clean host (or a VM).
2. Run the relevant `scripts/setup/*.sh` (idempotent) to install Docker etc.
3. `cp .env.example .env` per stack, paste secrets from Proton Pass.
4. Restore state dirs from your latest backup (Restic/Borg).
5. `docker compose up -d`.

If that works end-to-end, your homelab is genuinely disposable. If it doesn't, you found the gap *before* the disk died.

---

## What to actually put under version control

✅ **Commit:** all `compose.yaml` / `docker-compose.yml`, `Caddyfile`, `.env.example` templates, HA `configuration.yaml`/`automations.yaml` (sanitized), all `scripts/`, UniFi/NUT/config *exports* (with secrets stripped), this documentation.

❌ **Never commit:** real `.env`, private keys/certs, Postgres/SQLite data directories, media libraries, the HA `secrets.yaml`, the HA backup encryption key, NUT `upsd.users` passwords, Forgejo `app.ini` (it contains the generated `SECRET_KEY`/`INTERNAL_TOKEN` — keep those env-driven or in your secrets manager).

---

## Forgejo (the self-hosted forge itself)

Forgejo is Phase 4 infra and runs on the always-on Mac mini. It is the "rebuild in an hour" backbone. Config lives at `foss-setup/configs/git/docker-compose.yml`; deployed at `/opt/stacks/forgejo/` on the mini.

### Version policy (pinned, never `:latest`)
- `forgejo` → `15.0.x` (15.0 is the current LTS, supported until **2027-07-15**)
- `postgres` → `17-alpine`

Forgejo majors (X → X+1) require a manual, human-verified upgrade and may have breaking changes — read the release notes before bumping. Patch bumps within 15.0.x are safe; **Diun** notifies when one lands. Release schedule: https://forgejo.org/docs/latest/admin/release-schedule/

### Key config (from `docker-compose.yml`)

| Setting | Value | Notes |
|---|---|---|
| Image | `codeberg.org/forgejo/forgejo:15.0.1` | container name `forgejo` |
| DB image | `postgres:17-alpine` | container name `forgejo_db` |
| Web UI | host `3030` → container `3000` | `3030` avoids AdGuard's `:3000` setup wizard; front with Caddy in prod |
| Git-over-SSH | host `${FORGEJO_SSH_PORT:-2222}` → container `22` | advertised via `FORGEJO__server__SSH_PORT` so clone URLs are correct |
| Data volume | `./data/forgejo:/data` | bind-mounted; `.gitignore`d |
| DB volume | `./data/db:/var/lib/postgresql/data` | bind-mounted; `.gitignore`d |
| Networks | `edge` (external, shared w/ Caddy) + `forgejo` (bridge) | drop `edge` and the `3030` port if reaching Forgejo only over Tailscale/LAN |
| Restart | `unless-stopped` | both services |

The container `chown`s `/data` to `USER_UID=${FORGEJO_UID:-1000}` / `USER_GID=${FORGEJO_GID:-1000}` on start — match a real host user (`id -u` / `id -g`) so the bind-mounted `./data` is owned correctly.

`app.ini` is generated on first boot; critical bits are kept in version control / `.env` via env keys instead of an untracked `app.ini`:

```yaml
- FORGEJO__database__DB_TYPE=postgres
- FORGEJO__database__HOST=db:5432
- FORGEJO__database__NAME=forgejo
- FORGEJO__database__USER=forgejo
- FORGEJO__database__PASSWD=${FORGEJO_DB_PASSWORD}
- FORGEJO__server__DOMAIN=${FORGEJO_DOMAIN:-git.local}
- FORGEJO__server__ROOT_URL=${FORGEJO_ROOT_URL:-http://localhost:3030/}
- FORGEJO__server__SSH_DOMAIN=${FORGEJO_DOMAIN:-git.local}
- FORGEJO__server__SSH_PORT=${FORGEJO_SSH_PORT:-2222}
- FORGEJO__server__LFS_START_SERVER=true
- FORGEJO__service__DISABLE_REGISTRATION=${FORGEJO_DISABLE_REGISTRATION:-true}
- FORGEJO__service__REQUIRE_SIGNIN_VIEW=${FORGEJO_REQUIRE_SIGNIN:-true}
```

Lock the instance down after creating the admin account on first run. Single-user homelab: leave `DISABLE_REGISTRATION` true and just make your one account.

Healthchecks: Forgejo `curl -fsS http://localhost:3000/api/healthz` (interval 30s, start_period 60s); db `pg_isready -U forgejo`.

!!! note "Validated against live mini (2026-07-14)"
    `docker ps` on the mini shows both containers running: `forgejo` on `codeberg.org/forgejo/forgejo:15.0.1` and `forgejo_db` on `postgres:17-alpine`. Image tag matches the compose pin exactly.

---

## Mirroring (off-site copy of the repo itself)

The config repo is Tier-1 irreplaceable data. Protect it like everything else:
- In Forgejo: **Settings → Repository → Mirror Settings → push mirror** to a private GitHub/Codeberg repo. Now the rebuild instructions survive even if the Mac mini and its backups are both gone.
- It's also automatically swept up by the Tier-1 Restic/Kopia → B2 job, since the Forgejo data dir lives on the always-on box.

!!! note "Validated against live repo (2026-07-14)"
    The mirror is real and configured as the `origin` GitHub remote (`git@github.com:btabaska/home-config.git`) alongside the `forgejo` remote (`git@forgejo:home/homelab.git`). Both track `main`.

---

[← Operations](index.md)

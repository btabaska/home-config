# Config-as-code: repo structure, branching & secrets

> The whole point: when a disk dies or you migrate a host, recovery is
> **`git clone` → fill in `.env` → `docker compose up -d`** — not an afternoon of
> archaeology. This file describes how to lay that repo out so it stays true.

Self-host the repo on **Forgejo** (this folder's `docker-compose.yml`) on the
Mac mini, *or* push to a **private GitHub repo**. Either works. Self-hosting keeps
everything on your own metal; a private GitHub repo is the zero-maintenance
fallback. **Do both** if you want belt-and-suspenders: Forgejo as primary, a
GitHub mirror as the off-site copy (Forgejo can push-mirror automatically).

---

## Recommended layout

This very repo (`foss-setup/`) is the model. The shape that makes "rebuild in an
hour" real:

```
foss-setup/
├── README.md                     # what this is + phased rollout
├── configs/                      # declarative state: compose files + app config
│   ├── docker-stack/             # Mac mini stack (mirrors /opt/stacks 1:1)
│   │   ├── stacks/<svc>/compose.yaml + .env.example
│   │   └── .gitignore            # ignores **/.env, data dirs
│   ├── nas/                      # Synology container configs (Immich, CWA, ...)
│   ├── network/                  # UniFi VLAN/firewall plans (docs + exports)
│   ├── homeassistant/            # HA configuration.yaml.example, automations
│   └── git/                      # Forgejo (this folder)
├── scripts/                      # imperative setup: idempotent bootstrap scripts
│   ├── setup/                    # host baselines (docker, NUT, desktop, HAOS)
│   ├── dotfiles/                 # chezmoi bootstrap
│   ├── backup/ network/ media/ reading/ gaming/
└── docs/                         # the generated HTML guide
```

### Two kinds of content, kept apart
- **`configs/`** = *declarative desired state* (compose files, Caddyfiles, HA
  YAML). Checked in verbatim. This is what `docker compose up` consumes.
- **`scripts/`** = *imperative, idempotent* setup. Every script is `set -euo
  pipefail`, safe to re-run, and does install-if-missing. These bootstrap a bare
  host to the point where the `configs/` can be applied.

### One folder per service, every folder self-contained
Each service lives in its own directory with its `compose.yaml` and a
`.env.example`. That mirrors the **Dockge** convention (`/opt/stacks/<name>/`) so
the manager discovers each stack, and it means any one service can be understood,
backed up, or moved on its own.

---

## The golden rule: configs in Git, **state and secrets out**

Three categories, three fates:

| Category | Examples | Goes in Git? | How it's recovered |
|---|---|---|---|
| **Config** | `compose.yaml`, `Caddyfile`, `*.example`, scripts | ✅ yes | `git clone` |
| **Secrets** | `.env`, API tokens, passwords, TLS keys | ❌ never | secrets manager (below) |
| **State/data** | Postgres dirs, `caddy_data`, photo library, DBs | ❌ never | backups (Restic/Borg, Section 6) |

`git clone` restores config. Your **backup tooling** restores state. Your
**secrets manager** restores secrets. Don't conflate them — a repo that contains
secrets is a leak waiting to happen, and a repo bloated with state is unclonable.

---

## Secrets handling

**Never commit `.env`.** The pattern used throughout this repo:

1. Commit a **`.env.example`** template with every key present and dummy/empty
   values + comments on how to generate each one.
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

3. Store the **real secret values** in a secrets manager so a fresh clone can be
   re-hydrated:
   - **Proton Pass** (you already pay for it) — paste each box's `.env` as a
     secure note, or store individual secrets. Zero new infra. *Recommended.*
   - **chezmoi + age** — if a secret belongs next to a dotfile, let chezmoi
     manage it encrypted (see `scripts/dotfiles/chezmoi-quickstart.md`). Good for
     personal machine secrets (SSH keys, tokens), not shared service `.env`s.
   - **SOPS + age** — if you want encrypted secrets *committed to the repo
     itself* (decryptable only with your age key). The power-user option; the age
     private key lives in your password manager, never in Git.

> Minimum viable + set-and-forget: `.env.example` in Git + the real `.env`
> contents in **Proton Pass**. Reach for SOPS only if you want one-command,
> fully-encrypted-in-repo restores.

---

## Branching model (keep it boring)

A homelab is not a 12-person team. Optimize for "what was running last week" and
"undo", not for elaborate flow:

- **`main` = what is (or should be) deployed.** Trunk-based. Commit small, commit
  often. Every commit is a restore point.
- **Short-lived branches for risky changes** (a major Immich bump, a firewall
  rework). Branch → test → merge to `main` → deploy. Delete the branch.
- **Tag milestones** you might want to roll back to: `git tag phase4-complete`,
  `git tag pre-immich-v3`. Tags are free, named restore points.
- **Commit messages that say *why*** ("pin immich to v3.0.1 after v3.1 broke ML")
  — your future self at 2am is the only reviewer.

### The "rebuild in an hour" drill (do it once, for real)
1. `git clone <repo>` onto a clean host (or a VM).
2. Run the relevant `scripts/setup/*.sh` (idempotent) to install Docker etc.
3. `cp .env.example .env` per stack, paste secrets from Proton Pass.
4. Restore state dirs from your latest backup (Restic/Borg).
5. `docker compose up -d`.

If that works end-to-end, your homelab is genuinely disposable. If it doesn't,
you found the gap *before* the disk died.

---

## What to actually put under version control

✅ **Commit:** all `compose.yaml` / `docker-compose.yml`, `Caddyfile`, `.env.example`
templates, HA `configuration.yaml`/`automations.yaml` (sanitized), all
`scripts/`, UniFi/NUT/config *exports* (with secrets stripped), this
documentation.

❌ **Never commit:** real `.env`, private keys/certs, Postgres/SQLite data
directories, media libraries, the HA `secrets.yaml`, the HA backup encryption
key, NUT `upsd.users` passwords, Forgejo `app.ini` (it contains the generated
`SECRET_KEY`/`INTERNAL_TOKEN` — keep those env-driven or in your secrets manager).

---

## Mirroring (off-site copy of the repo itself)

Your config repo is Tier-1 irreplaceable data. Protect it like everything else:
- In Forgejo: **Settings → Repository → Mirror Settings → push mirror** to a
  private GitHub/Codeberg repo. Now the rebuild instructions survive even if the
  Mac mini and its backups are both gone.
- It's also automatically swept up by the Tier-1 Restic/Kopia → B2 job, since the
  Forgejo data dir lives on the always-on box.

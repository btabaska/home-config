# foss-setup — subtree rules

The repo-root `CLAUDE.md` (`../CLAUDE.md`) holds fleet access, secrets handling,
anti-drift ownership, and standing mandates — read it first. This file adds the rules
specific to this subtree. (Hermes auto-injects this file when a session starts touching
`foss-setup/` files; other agents should pick it up hierarchically.)

## Layout

- `configs/` — live-host config mirrors: `docker-stack/stacks/<app>` (mini `/opt/stacks`),
  `nas/` (NAS `/volume1/docker`), `host/rig/` (rig units/config).
- `docs/` — tracker source of truth (`tasks.json`, `progress.json`) + planning docs.
- `wiki/` — generated mkdocs site. `scripts/` — generation, verification, and ops scripts.
- `verification/` — `checks.d/*.yaml` checks, `coverage/` manifest, runner support.

## Hard rules

1. **Never hand-edit generated outputs**: root `todo.md`, tracker/roadmap pages, and
   generated `wiki/docs/**/*.md`. Edit the source and regenerate:
   - `python3 scripts/docs/gen-todo.py` + `scripts/docs/gen-roadmap-pages.py` (tracker)
   - `scripts/docs/build-wiki.sh` (wiki — dockerized mkdocs on the mini, `--strict`)
2. **Same-commit regeneration**: a source change and its regenerated output must land in
   the same commit (the publish `wiki-drift` gate refuses otherwise).
3. **New verification check** = a yaml in `verification/checks.d/` with `cmd`, `task_id`,
   and a `runbook` that resolves to a real wiki page. Deploy by scp'ing it to mini
   `/opt/verification/checks.d/`.
4. **Coverage tripwire**: every service deploy or retire updates
   `verification/coverage/`.
5. **Secrets**: `.handoff-secrets.yaml` here is gitignored — read via python + yaml,
   reference by key path, never paste values into chat, commits, or docs.
6. **Concurrent agent sessions happen**: `git pull` before committing, re-read files
   before editing, and expect intentional `/opt/stacks` drift from other sessions.

# Runbook — Update images

Policy: **no blind auto-updates, ever.** Every image is pinned to an exact
tag; updates happen deliberately, on your schedule, with release notes read.
Watchtower-style "always pull latest" is banned (it's how a set-and-forget
box breaks at 3 a.m.).

## The flow

```
Diun notices a new tag → ntfy pushes to your phone → you read release notes
→ bump the pin in git → commit → publish → pull+up on the host → verify
```

1. **Diun** (on the mini, `configs/docker-stack/stacks/diun/`) watches every
   running container's image and posts to the ntfy topic `diun` when a new
   version appears. This is *awareness*, not action.
2. **Read the release notes.** Especially for the breaking-change projects:
   Immich (majors), Postgres (majors change data paths), Caddy, the *arrs.
3. **Bump the pin in the repo** — the compose file in
   `configs/docker-stack/stacks/<name>/compose.yaml` (or `configs/nas/<name>/`),
   e.g. `miniflux/miniflux:2.3.1 → 2.3.2`. Update the header comment if the
   version is named there. **The repo is the source of truth — never bump
   only on the host.**
4. **Commit + publish**: commit to `home-config`, run
   `scripts/docs/publish-deploy.sh`, and mirror the change into
   `/opt/stacks/<name>/compose.yaml` (commit that repo too).
5. **Apply on the host**:

    ```bash
    ssh mini "cd /opt/stacks/<name> && docker compose pull && docker compose up -d"
    # NAS stacks: Container Manager → project → Action → Clean & rebuild
    ```

6. **Verify**: service answers, logs clean, no crash loop:

    ```bash
    ssh mini "cd /opt/stacks/<name> && docker compose ps && docker compose logs --tail 20"
    curl -s -o /dev/null -w '%{http_code}\n' https://<name>.tabaska.us
    ```

7. **Wiki**: regenerate service pages (the pin is on the page) —
   `python3 scripts/docs/gen-wiki-services.py && bash scripts/docs/build-wiki.sh`.

## Rollback

The previous pin is one `git revert` away; `docker compose up -d` with the
old tag restores it (DB-migrating apps like Immich may not roll back cleanly
— that's why step 2 exists).

## Special cases

- **Immich**: pinned via `IMMICH_VERSION` in `.env` on the NAS; DB/Redis
  images are digest-pinned to match the release — bump them together from the
  release's compose.
- **Caddy**: custom-built image (Cloudflare DNS module) — bump the base in
  `stacks/caddy/Dockerfile`, `docker compose build`.
- **OS packages** are separate: unattended-upgrades (security-only) on
  Ubuntu, pacman on your cadence on the rig, DSM its own updater.

## Verify (the meta-check)

Repo pin == running container:

```bash
ssh mini 'docker inspect <container> --format "{{.Config.Image}}"'
```

matches the compose file in git. Drift here is exactly what the audit keeps
finding — close the loop every time.

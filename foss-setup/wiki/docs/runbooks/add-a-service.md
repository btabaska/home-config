# Runbook — Add a service

The full loop for standing up a new service on the mini. **A service isn't
"added" until every step is done** — half-done services are how Caddy vhosts
for dead containers and undocumented ports accumulate.

## The checklist

```text
[ ] 1. Stack dir        configs/docker-stack/stacks/<name>/compose.yaml
[ ] 2. Pin the image    exact tag (never :latest, never :release)
[ ] 3. .env.example     every required var, placeholder values only
[ ] 4. Caddy vhost      <name>.tabaska.us in caddy/Caddyfile
[ ] 5. Homepage entry   homepage config (group, icon, URL)
[ ] 6. Wiki regen       gen-wiki-services.py + build-wiki.sh
[ ] 7. Verification     health probe (Uptime Kuma now; checks.d when it lands)
[ ] 8. Commit + deploy  repo commit, publish, compose up on the mini
```

## Step by step

1. **Stack dir.** New directory `configs/docker-stack/stacks/<name>/` with
   `compose.yaml`. Header comment: one-line role + `Docs: <upstream url>`
   (the wiki generator reads it). Join the external `edge` network so Caddy
   can reach it by container name. Check `free -m` on the mini first — 8 GB
   is a hard ceiling; heavy things go elsewhere ([mini](../hosts/mini.md)).
2. **Pin the image.** Exact upstream tag (e.g. `miniflux/miniflux:2.3.1`).
   Diun will watch it from there ([Update images](update-images.md)).
3. **`.env.example`.** Every variable the compose file references, with
   placeholders and a comment linking upstream config docs. Real values go
   in `.env` on the host only, sourced from the vault
   ([Secrets policy](../operations/secrets.md)).
4. **Caddy vhost.** In `configs/docker-stack/stacks/caddy/caddy/Caddyfile`:

    ```caddyfile
    <name>.{$DOMAIN} {
        import cloudflare_tls
        reverse_proxy <container>:<port>
    }
    ```

    No AdGuard change needed — the `*.tabaska.us` wildcard rewrite already
    points at the mini. (NAS/rig services: proxy by IP env var instead.)

5. **Homepage entry** in the homepage stack's `services.yaml` — friendly
   name, icon, `https://<name>.tabaska.us`, widget if one exists.
6. **Wiki regen.**

    ```bash
    python3 foss-setup/scripts/docs/gen-wiki-services.py
    bash foss-setup/scripts/docs/build-wiki.sh
    ```

7. **Verification check.** Add an Uptime Kuma monitor for the URL now; when
   the verification framework lands (pending: verify-01), add a
   `checks.d/<name>.yaml` probe (cmd/expect/severity/runbook) instead.
8. **Commit + deploy.** Commit the repo (config + homepage + generated wiki
   pages in the same commit), `publish-deploy.sh`, then on the mini:
   `/opt/stacks/<name>` — copy the stack, fill `.env`, `docker compose up -d`,
   commit `/opt/stacks` too.

## Verify

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<name>.tabaska.us   # 200/302
ssh mini "cd /opt/stacks/<name> && docker compose ps"                # healthy
ssh mini "cd /opt/stacks && git status --short"                      # clean
```

Plus: tile visible on Homepage, page present on the wiki's
[Services index](../services/index.md).

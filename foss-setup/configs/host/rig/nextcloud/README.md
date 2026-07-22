# Nextcloud (EVAL) — rig `/opt/stacks/nextcloud`

Status: **evaluation only** (deployed 2026-07-22, task `cloud-01`). We previously decided
against Nextcloud; this is a fresh eval to decide keep-vs-remove. Not hardened, not backed
up, not fully monitored yet — those are the `cloud-03`…`cloud-10` follow-up tasks, gated on
the eval-decision task `cloud-02`.

## Shape

- **Host:** rig (CachyOS `192.168.10.12`), rootful Docker, `/opt/stacks/nextcloud/`.
- **Containers:** `nextcloud` (apache image), `nextcloud-db` (MariaDB LTS), `nextcloud-redis`.
- **Network/volumes:** its OWN internal bridge + three NAMED volumes (`nextcloud_app`,
  `nextcloud_db`, `nextcloud_data`) — nothing on the shared `edge` net, no scattered bind
  mounts, so teardown is clean.
- **Exposure:** publishes `11000:80` (plain HTTP) on the rig. TLS terminates on the
  **Mac-mini Caddy** — vhost `cloud.tabaska.us` → `reverse_proxy {$RIG_IP}:11000`. Real
  Let's Encrypt cert via the mini's Cloudflare DNS-01 setup. No inbound port on the rig.
- **Accounts:** two admins — `btabaska` (created on install via env) and `Kaevis` (display
  name "Kaelyn", created post-install via `occ`, added to the `admin` group). Passwords in
  the vault under `nextcloud.*`.

## Deploy / operate

```bash
# bring up (from the stack dir on the rig)
ssh rig 'cd /opt/stacks/nextcloud && docker compose up -d'

# occ (admin CLI) always runs as www-data
ssh rig 'docker exec -u www-data nextcloud php occ status'
ssh rig 'docker exec -u www-data nextcloud php occ user:list'
```

## Remove (minimal-effort teardown — see `cloud-10`)

1. `ssh rig 'cd /opt/stacks/nextcloud && docker compose down -v'` (removes containers + named volumes)
2. `ssh rig 'rm -rf /opt/stacks/nextcloud'`
3. Delete the `cloud.tabaska.us` block from the mini Caddyfile
   (`/opt/stacks/caddy/caddy/Caddyfile` + repo mirror), then
   `ssh mini 'docker exec caddy caddy validate --config /etc/caddy/Caddyfile && docker exec caddy caddy reload --config /etc/caddy/Caddyfile'`
4. Delete the `Nextcloud` tile from `homepage/config/services.yaml` (live + repo mirror).
5. Remove the `nextcloud:` block from the vault (`.handoff-secrets.yaml`) + its `.example` placeholder.
6. Retire the verification/coverage entry (once `cloud-04` adds one) and delete the `cloud-*` tasks.

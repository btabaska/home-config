# Monitoring coverage — liveness vs reality

What to do when a `monitoring-coverage` check fires (ntfy topic `verification`).

These checks exist because the 2026-07-16 audit (task **fix-29**) found the whole
monitoring layer reporting green while the things it "watched" were functionally
dead: a homepage tile pinging a retired container, a Kuma monitor with no alert
channel, unpackerr invisible to every external monitor, a beszel email path that
silently dropped every alert, and — during the read-only-root incident — the AI
stack's own liveness probes staying `up` while every real client got 503. Every
check here deliberately probes the **consumer end**, not liveness.

Source checks: `verification/checks.d/monitoring-coverage.yaml`. Findings closed:
M17, M21, M57, L28, L94.

---

## `homepage-dead-tiles` failed (warn) — a tile points at a nonexistent container

Output `DEAD_TILES=<kind:host,…>`. A homepage tile's `siteMonitor`/`widget.url`
is a bare docker-DNS name (e.g. `http://maintainerr:6246`) with no running
container behind it, so homepage throws `getaddrinfo EAI_AGAIN` on every render
(the original M17: 264 errors in 96h from the retired Maintainerr tile).

1. Find the tile: `grep -n <host> /opt/stacks/homepage/config/services.yaml`.
2. If the service was **retired**, delete the tile block. If it **moved hosts**,
   repoint `siteMonitor`/`url` at its IP/FQDN (bare names only resolve to
   containers on homepage's own docker network).
3. Mirror the edit to `configs/docker-stack/stacks/homepage/config/services.yaml`
   **and** commit the `/opt/stacks` copy (Forgejo `home/docker-stacks`).
4. `docker restart homepage` and re-run the check.

## `homepage-widget-errors` failed (warn) — dashboard rendered DNS errors in 2h

Consumer-end confirmation of the above: homepage logged `EAI_AGAIN`/`getaddrinfo`
while serving the dashboard. Usually the same root cause as `homepage-dead-tiles`;
if that one is green, look for a tile whose bare name resolves intermittently.
`docker logs homepage --since 2h | grep -iE 'EAI_AGAIN|getaddrinfo'`.

## `kuma-all-monitors-notified` failed (crit) — a monitor can go down silently

Output `unlinked=<n>`: `n` active Uptime-Kuma monitors have no
`monitor_notification` row, so an outage produces no ntfy alert (M21: the NAS
Whisparr monitor shipped this way). Self-heal:

```bash
bash /opt/stacks/uptime-kuma/bootstrap-nas-monitors.sh   # idempotent; links all
```

The `link_all_notifications` step attaches the `ntfy → homelab-alerts` channel to
every active monitor. If it warns `no active ntfy notification found`, the ntfy
channel itself was deleted in the Kuma UI — recreate it (Settings → Notifications)
first. New monitors must be added via that script (not the UI) so they inherit
the link automatically.

## `unpackerr-poll-advancing` failed (warn) — unpackerr up but not extracting

Two failure shapes:

- `UNPACKERR_UNREACHABLE` / `apps=0<5` — the metrics port (NAS `5656`) is
  unreachable, or unpackerr isn't reaching the Starr apps. Check the container:
  `ssh nas 'sudo /usr/local/bin/docker ps | grep unpackerr'`; confirm the port is
  published (`configs/nas/media-automation/docker-compose.yml` → `ports: 5656`).
- `UNPACKERR_WEDGED … frozen …s — poll loop stalled` — the process answers but
  its poll counter (`unpackerr_app_queue_fetch_total`) hasn't advanced in >5 min.
  This is the 2026-07-10 "up but wedged two days" class that liveness missed.
  Restart it: `ssh nas 'cd /volume1/docker/media-automation && sudo /usr/local/bin/docker compose restart unpackerr'`
  then watch `curl http://192.168.10.4:5656/metrics | grep fetch_total` climb.

State file: `/var/lib/verification/unpackerr-fetch.state` (timestamp + counter).

## `beszel-notify-coherent` failed (warn) — a notification channel has no transport

Output `BESZEL_COHERENT_FAIL <id>:dead-email` — a beszel user has an email
destination but the hub has no `SMTP_*` env, so email alerts drop silently (L28).
Either configure SMTP (add `SMTP_*` to the beszel container env — then email is a
live path and the check passes) or strip the dead destination:

```bash
BESZEL_ADMIN_USER=… BESZEL_ADMIN_PASSWORD=… \
  bash foss-setup/scripts/beszel/fix-notify-channels.sh   # idempotent
```

`no working webhook channel` means the ntfy webhook was removed too — beszel would
then alert nowhere (though `alert-beszel-none-down` still catches beszel-down from
the mini sweep). Re-add the ntfy webhook in the beszel UI.

## `rig-litellm-consumer-e2e` failed (warn) — virtual-key clients can't complete

The consumer-end counterpart to the liveness-only `rig-litellm` ("401 without
key = up"). Output `LITELLM_CONSUMER_FAIL …` means a **virtual key** could not get
a real completion — the exact M57 failure (503 `no_db_connection` for every client
while `/health/liveliness` stayed 200 because `litellm-db` was down).

1. Is the key DB up? `ssh rig 'docker ps | grep litellm-db'` — LiteLLM stores
   virtual keys in Postgres; if it's down/corrupt, all non-master keys 503.
2. Reproduce: `ssh rig 'set -a; . ~/.config/fleet-mcp/env; set +a; curl -s
   http://localhost:4000/v1/chat/completions -H "Authorization: Bearer
   $LITELLM_VERIFY_KEY" -d "{\"model\":\"utility\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}"'`.
3. If the `verify-probe` key was lost (DB reset), remint it (least-privilege,
   `utility` model only) and re-store it:

```bash
ssh rig 'MK=$(docker inspect litellm --format "{{range .Config.Env}}{{println .}}{{end}}" | sed -n "s/^LITELLM_MASTER_KEY=//p")
  curl -s http://localhost:4000/key/generate -H "Authorization: Bearer $MK" \
    -H "Content-Type: application/json" \
    -d "{\"key_alias\":\"verify-probe\",\"models\":[\"utility\"],\"max_budget\":5}"'
# put the returned key in rig ~/.config/fleet-mcp/env as LITELLM_VERIFY_KEY
# and in vault ai_stack.litellm_verify_key
```

---

**Principle (standing mandate #1):** every liveness signal on this fleet must be
paired with a consumer-end probe. When you add a new service, don't ship a
"container healthy / 200 OK" check alone — probe the thing a user or downstream
actually consumes, the way these checks do.
